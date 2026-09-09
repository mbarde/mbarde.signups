# -*- coding: utf-8 -*-
from mbarde.signups import _
from mbarde.signups.utils import ploneUserToPersonId
from plone import api
from Products.CMFPlone.interfaces import ILanguage
from Products.Five import BrowserView
from Products.validation import validation
from z3c.caching.purge import Purge
from zope.event import notify
from zope.i18n import translate


class CancelReservation(BrowserView):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    # notification for manager at this point (and not in subscribers.py)
    # since we only want to inform the manager if user signed off on his own
    def sendCancellationNotification(
        self, timeSlot, email, fullname, extraInfoStr, isOnWaitingList
    ):
        day = timeSlot.aq_parent
        signupSheet = day.aq_parent

        contactInfo = signupSheet.contactInfo
        isEmail = validation.validatorFor("isEmail")
        if not signupSheet.notifyContactInfo or not isEmail(contactInfo) or len(contactInfo) < 1:
            return

        lang = ILanguage(signupSheet).get_language()
        if len(lang) == 0:
            lang = "en"

        toEmail = contactInfo
        fromEmail = signupSheet.contactInfo
        subject = (
            signupSheet.Title()
            + " - "
            + translate(_("Cancellation Notification"), target_language=lang)
        )

        message = translate(_("Hello"), target_language=lang) + ",\n\n"

        if isOnWaitingList:
            message += (
                translate(
                    _("A signup has been cancelled from the waiting list of following slot:"),
                    target_language=lang,
                )
                + "\n"
            )  # noqa: E501
        else:
            message += (
                translate(_("Following slot has been cancelled:"), target_language=lang) + "\n"
            )
        message += timeSlot.getLabel() + "\n\n"

        message += translate(_("Name"), target_language=lang) + ": " + fullname + "\n"
        message += translate(_("E-Mail"), target_language=lang) + ": " + email + "\n\n"

        if len(extraInfoStr) > 0:
            message += translate(_("Additional information"), target_language=lang) + "\n"
            message += extraInfoStr + "\n\n"

        api.portal.send_email(recipient=toEmail, sender=fromEmail, subject=subject, body=message)

    def cancelReservation(self):
        if api.user.is_anonymous():
            came_from = self.context.absolute_url() + "/@@show-reservations"
            return self.request.response.redirect(
                api.portal.get().absolute_url() + "/login_form?came_from=" + came_from
            )

        selectedSlots = self.request.get("selectedSlot", None)
        if type(selectedSlots) is not list:
            selectedSlots = [selectedSlots]

        if selectedSlots != [None]:
            for slot in selectedSlots:
                self.signOffCurrentUserFromSlot(slot)

        # purge request to refresh view for everyone
        notify(Purge(self.context))

        self.request.response.redirect(self.context.absolute_url() + "/@@show-reservations")

    def signOffCurrentUserFromSlot(self, slot):
        curUser = api.user.get_current()
        personId = ploneUserToPersonId(curUser)

        date, time = slot.split(" @ ")
        day = self.context.getDay(date)
        timeSlot = day.getTimeSlot(time)

        # get person object brain to check if he/she is on waiting list or not
        # to be able to include this infromation in the mail to the manager
        timeSlotPath = "/".join(timeSlot.getPhysicalPath())
        brains = self.context.portal_catalog.unrestrictedSearchResults(
            portal_type="UTPerson", id=personId, path=timeSlotPath
        )
        person = brains[0].unrestrictedTraverse(brains[0].getPath())

        extraInfoStr = person.getExtraInfoAsString()

        state = api.content.get_state(obj=person)

        if state == "signedoff":
            return  # user is already signedoff

        isOnWaitingList = False
        if state == "waiting":
            isOnWaitingList = True

        api.content.transition(obj=person, transition="signoff")
        person.reindexObject()

        self.sendCancellationNotification(
            timeSlot, person.email, person.Title(), extraInfoStr, isOnWaitingList
        )
