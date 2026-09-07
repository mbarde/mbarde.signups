# -*- coding: utf-8 -*-
from DateTime import DateTime
from mbarde.signups import _
from mbarde.signups.utils import deferRename
from mbarde.signups.utils import emailToPersonId
from mbarde.signups.utils import ploneUserToPersonId
from plone import api
from plone.dexterity.content import Container
from plone.i18n.normalizer.interfaces import IIDNormalizer
from plone.locking.interfaces import ILockable
from plone.supermodel import model
from zope import schema
from zope.component import getUtility
from zope.interface import implementer


class IUTTimeslot(model.Schema):

    startTime = schema.Time(title=_("Start Time"), required=True)

    endTime = schema.Time(title=_("End Time"), required=True)

    name = schema.TextLine(title=_("Name"), description=_("Optional name"), required=False)

    maxCapacity = schema.Int(
        title=_("Max capacity"), description=_("The max number of people"), required=True, default=1
    )

    allowWaitingList = schema.Bool(
        title=_("Allow Waiting List"),
        description=_(
            "Check if you want to allow signups to waiting list once max capacity is reached"
        ),
        required=False,
    )


@implementer(IUTTimeslot)
class UTTimeslot(Container):

    def getLabel(self):
        parentDay = self.aq_parent
        signupSheet = parentDay.aq_parent
        if signupSheet.hideDateTime:
            return self.getName()
        else:
            return "{0} @ {1}".format(parentDay.Title(), self.Title())

    def getIDLabel(self):
        parentDay = self.aq_parent
        return "{0} @ {1}".format(parentDay.id, self.id)

    def getTimeRange(self):
        return "{0} - {1}".format(str(self.getStartTime()), str(self.getEndTime()))

    def getPersons(self):
        brains = self.portal_catalog.unrestrictedSearchResults(
            portal_type="UTPerson", path=self.getPath()
        )
        return [brain.getObject() for brain in brains]

    def getNumberOfAvailableSlots(self):
        brains = self.portal_catalog.unrestrictedSearchResults(
            portal_type="UTPerson", review_state="signedup", path=self.getPath()
        )
        numberOfPeopleSignedUp = len(brains)
        return max(0, self.maxCapacity - numberOfPeopleSignedUp)

    def getCurrentUserSignUpState(self):
        curUser = api.user.get_current()
        personId = ploneUserToPersonId(curUser)

        # no need to make use of unrestrictedSearchResults since owner
        # should be allowed to access his own person object
        if not hasattr(self, personId):
            return False

        person = getattr(self, personId)
        return api.content.get_state(person)

    def getPeople(self, sortByStatus=False, filterByStatus=False):
        if filterByStatus:
            brains = api.content.find(
                context=self, portal_type="UTPerson", review_state=filterByStatus, depth=1
            )
        else:
            brains = api.content.find(context=self, portal_type="UTPerson", depth=1)

        people = [brain.getObject() for brain in brains]
        if sortByStatus:
            sortOrder = {"signedoff": 3, "waiting": 2, "unconfirmed": 1, "signedup": 0}
            people.sort(key=lambda p: sortOrder[api.content.get_state(obj=p)])

        return people

    def isFull(self):
        return self.getNumberOfAvailableSlots() == 0 and not self.allowWaitingList

    def isUserSignedUpForThisSlot(self, email):
        personId = emailToPersonId(email)
        brains = self.portal_catalog.unrestrictedSearchResults(
            portal_type="UTPerson", review_state="signedup", id=personId, path=self.getPath()
        )
        return len(brains) != 0

    def isRegistrationExpired(self):
        now = DateTime()
        return self.expires() <= now

    def getPath(self):
        return "/".join(self.getPhysicalPath())

    def getStartTime(self):
        if self.startTime is None:
            return "00:00"
        return self.startTime.strftime("%H:%M")

    def getEndTime(self):
        if self.endTime is None:
            return "00:00"
        return self.endTime.strftime("%H:%M")


# set id & title on creation and modification
def autoSetID(timeslot, event):
    if timeslot.startTime is None or timeslot.endTime is None:
        return

    title = timeslot.getTimeRange()
    normalizer = getUtility(IIDNormalizer)
    newId = normalizer.normalize(title)
    if title != timeslot.title or newId != timeslot.id:
        lockable = ILockable(timeslot)
        if lockable.locked():
            if not lockable.can_safely_unlock():
                # can not modify locked object
                return
            lockable.unlock()
        timeslot.title = title
        if newId != timeslot.id:
            deferRename(timeslot, newId)
        else:
            timeslot.reindexObject()
