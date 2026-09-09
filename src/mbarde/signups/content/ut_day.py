# -*- coding: utf-8 -*-
from datetime import date as dateClass
from datetime import datetime
from datetime import timedelta
from DateTime import DateTime
from mbarde.signups import _
from mbarde.signups.utils import deferRename
from plone import api
from plone.dexterity.content import Container
from plone.dexterity.utils import createContentInContainer
from plone.i18n.normalizer.interfaces import IIDNormalizer
from plone.locking.interfaces import ILockable
from plone.supermodel import model
from zope import schema
from zope.component import getUtility
from zope.interface import implementer


class IUTDay(model.Schema):

    date = schema.Date(title=_("Date"), required=True)


@implementer(IUTDay)
class UTDay(Container):

    def getTimeSlots(self):
        brains = api.content.find(context=self, portal_type="UTTimeslot", depth=1)

        timeSlots = []
        for brain in brains:
            timeSlots.append(brain.getObject())

        timeSlots = sorted(timeSlots, key=lambda slot: slot.startTime)

        return timeSlots

    def getTimeSlot(self, timeslotId, checkExpirationDate=False):
        brains = api.content.find(context=self, portal_type="UTTimeslot", depth=1, id=timeslotId)
        if len(brains) == 0:
            raise ValueError("The TimeSlot {0} was not found.".format(timeslotId))

        if checkExpirationDate:
            now = DateTime()
            if not brains[0].expires > now:
                raise ValueError("The TimeSlot {0} was not found.".format(timeslotId))

        timeSlot = brains[0].getObject()
        return timeSlot

    def createSequentialTimeSlots(
        self, startTime, duration, count, maxCapacity=1, allowWaitingList=False
    ):
        """Create ``count`` timeslots of ``duration`` minutes each, one
        right after the other, starting at ``startTime``.

        This is meant to make it easy to fill a day with a series of
        equally sized, back-to-back timeslots (e.g. 4 timeslots of 15
        minutes each for consulting hours) instead of adding them one by
        one.

        :param startTime: datetime.time - start of the first timeslot
        :param duration: int - length of each timeslot in minutes
        :param count: int - number of timeslots to create
        :param maxCapacity: int - max capacity to set on each new timeslot
        :param allowWaitingList: bool - allow waiting list on each new timeslot
        :returns: list of the created UTTimeslot objects
        """
        if duration < 1:
            raise ValueError(_("Timeslot duration must be at least 1 minute."))
        if count < 1:
            raise ValueError(_("Number of timeslots must be at least 1."))

        delta = timedelta(minutes=duration)
        current = datetime.combine(dateClass.today(), startTime)

        createdTimeSlots = []
        for _i in range(count):
            slotStartTime = current.time()
            current += delta
            slotEndTime = current.time()

            timeSlot = createContentInContainer(
                self,
                "UTTimeslot",
                startTime=slotStartTime,
                endTime=slotEndTime,
                maxCapacity=maxCapacity,
                allowWaitingList=allowWaitingList,
            )
            createdTimeSlots.append(timeSlot)

        return createdTimeSlots


# set id & title on creation and modification
def autoSetID(day, event):
    if not hasattr(day, "date") or day.date is None:
        return

    title = day.date.strftime("%d.%m.%Y")
    normalizer = getUtility(IIDNormalizer)
    newId = normalizer.normalize(title)
    if title != day.title or newId != day.id:
        lockable = ILockable(day)
        if lockable.locked():
            if not lockable.can_safely_unlock():
                # can not modify locked object
                return
            lockable.unlock()
        day.title = title
        if newId != day.id:
            deferRename(day, newId)
        else:
            day.reindexObject()
