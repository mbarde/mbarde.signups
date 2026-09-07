# -*- coding: utf-8 -*-
from DateTime import DateTime
from mbarde.signups import _
from mbarde.signups.utils import deferRename
from plone import api
from plone.dexterity.content import Container
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
            raise ValueError(_("The TimeSlot {0} was not found.".format(timeslotId)))

        if checkExpirationDate:
            now = DateTime()
            if not brains[0].expires > now:
                raise ValueError(_("The TimeSlot {0} was not found.".format(timeslotId)))

        timeSlot = brains[0].getObject()
        return timeSlot


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
