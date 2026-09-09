# -*- coding: utf-8 -*-
from mbarde.signups import _
from mbarde.signups.utils import appendAuthenticatedSuffix
from mbarde.signups.utils import replaceCustomMailPlaceholders
from plone import api
from Products.CMFPlone.interfaces import ILanguage
from Products.validation import validation
from zope.i18n import translate


# send notification to user and manager (if `notifyContactInfo` is set)
def sendSignupNotificationEmail(person):
    isEmail = validation.validatorFor("isEmail")

    timeSlot = person.aq_parent
    day = timeSlot.aq_parent
    signupSheet = day.aq_parent

    lang = ILanguage(signupSheet).get_language()
    if len(lang) == 0:
        lang = "en"

    contactInfo = signupSheet.contactInfo
    extraInfoStr = person.getExtraInfoAsString()
    fromEmail = signupSheet.contactInfo

    # mail to person who signed up
    if isEmail(person.email) != 1:
        return

    url = signupSheet.absolute_url()
    toEmail = person.email

    subject = replaceCustomMailPlaceholders(
        signupSheet.emailConfirmationSubject,
        person.Title(),
        signupSheet.Title(),
        url,
        timeSlot.getLabel(),
        extraInfoStr,
        url + "/@@view-my-signups",
    )
    message = replaceCustomMailPlaceholders(
        signupSheet.emailConfirmationContent,
        person.Title(),
        signupSheet.Title(),
        url,
        timeSlot.getLabel(),
        extraInfoStr,
        url + "/@@view-my-signups",
    )
    message = appendAuthenticatedSuffix(
        message, person, signupSheet, timeSlot.getLabel(), extraInfoStr
    )

    api.portal.send_email(recipient=toEmail, sender=fromEmail, subject=subject, body=message)

    # mail to contact person of the signup sheet
    if signupSheet.notifyContactInfo and len(contactInfo) > 0 and isEmail(contactInfo):
        url = signupSheet.absolute_url()
        toEmail = contactInfo
        subject = (
            signupSheet.Title()
            + " - "
            + translate(_("Registration Notification"), target_language=lang)
        )

        message = translate(_("Hello"), target_language=lang) + ",\n\n"
        message += (
            translate(
                _("This message is to notify you that someone signed up for:"), target_language=lang
            )
            + "\n"
        )
        message += timeSlot.getLabel() + "\n\n"

        message += translate(_("Name"), target_language=lang) + ": " + person.Title() + "\n"
        message += translate(_("E-Mail"), target_language=lang) + ": " + person.email + "\n\n"

        if len(extraInfoStr) > 0:
            message += translate(_("Additional information"), target_language=lang) + "\n"
            message += extraInfoStr + "\n\n"

        message += "\nURL: " + person.absolute_url() + "\n\n"

        api.portal.send_email(recipient=toEmail, sender=fromEmail, subject=subject, body=message)


# send notification to user and manager (if `notifyContactInfo` is set)
def sendWaitingListConfirmationEmail(person):
    isEmail = validation.validatorFor("isEmail")

    timeSlot = person.aq_parent
    day = timeSlot.aq_parent
    signupSheet = day.aq_parent

    lang = ILanguage(signupSheet).get_language()
    if len(lang) == 0:
        lang = "en"

    extraInfoStr = person.getExtraInfoAsString()
    contactInfo = signupSheet.contactInfo
    fromEmail = signupSheet.contactInfo

    if isEmail(person.email) != 1:
        return

    url = signupSheet.absolute_url()
    toEmail = person.email

    subject = replaceCustomMailPlaceholders(
        signupSheet.emailWaitinglistSubject,
        person.Title(),
        signupSheet.Title(),
        url,
        timeSlot.getLabel(),
        extraInfoStr,
        url + "/@@view-my-signups",
    )
    message = replaceCustomMailPlaceholders(
        signupSheet.emailWaitinglistContent,
        person.Title(),
        signupSheet.Title(),
        url,
        timeSlot.getLabel(),
        extraInfoStr,
        url + "/@@view-my-signups",
    )
    message = appendAuthenticatedSuffix(
        message, person, signupSheet, timeSlot.getLabel(), extraInfoStr
    )

    api.portal.send_email(recipient=toEmail, sender=fromEmail, subject=subject, body=message)

    # mail to contact person of the signup sheet
    if signupSheet.notifyContactInfo and len(contactInfo) > 0 and isEmail(contactInfo):
        toEmail = contactInfo
        subject = (
            signupSheet.Title()
            + " - "
            + translate(_("Waiting List Notification"), target_language=lang)
        )

        message = translate(_("Hello"), target_language=lang) + ",\n\n"
        message += (
            translate(
                _("A new signup has been added to the waiting list for:"), target_language=lang
            )
            + "\n"
        )
        message += timeSlot.getLabel() + "\n\n"

        message += translate(_("Name"), target_language=lang) + ": " + person.Title() + "\n"
        message += translate(_("E-Mail"), target_language=lang) + ": " + person.email + "\n\n"

        if len(extraInfoStr) > 0:
            message += translate(_("Additional information"), target_language=lang) + "\n"
            message += extraInfoStr + "\n\n"

        message += "\nURL: " + person.absolute_url() + "\n\n"

        api.portal.send_email(recipient=toEmail, sender=fromEmail, subject=subject, body=message)


# send notification to user
def sendSignOffNotification(person):
    isEmail = validation.validatorFor("isEmail")
    timeSlot = person.aq_parent
    day = timeSlot.aq_parent
    signupSheet = day.aq_parent

    extraInfoStr = person.getExtraInfoAsString()

    # mail to person who signed up
    if isEmail(person.email) != 1:
        return

    url = signupSheet.absolute_url()
    toEmail = person.email
    fromEmail = signupSheet.contactInfo

    subject = replaceCustomMailPlaceholders(
        signupSheet.emailCancelSubject,
        person.Title(),
        signupSheet.Title(),
        url,
        timeSlot.getLabel(),
        extraInfoStr,
        url + "/@@view-my-signups",
    )
    message = replaceCustomMailPlaceholders(
        signupSheet.emailCancelContent,
        person.Title(),
        signupSheet.Title(),
        url,
        timeSlot.getLabel(),
        extraInfoStr,
        url + "/@@view-my-signups",
    )
    message = appendAuthenticatedSuffix(
        message, person, signupSheet, timeSlot.getLabel(), extraInfoStr
    )

    api.portal.send_email(recipient=toEmail, sender=fromEmail, subject=subject, body=message)


def attemptToFillEmptySpot(obj):
    timeSlot = obj.aq_parent
    day = timeSlot.aq_parent
    signupSheet = day.aq_parent

    if signupSheet.enableAutoMovingUpFromWaitingList:
        # to make sure timeslot.getNumberOfAvailableSlots() returns current value
        obj.reindexObject()

        if timeSlot.getNumberOfAvailableSlots() > 0:
            portal_catalog = api.portal.get_tool("portal_catalog")
            query = {
                "portal_type": "UTPerson",
                "review_state": "waiting",
                "sort_on": "Date",
                "sort_order": "ascending",
            }
            brains = portal_catalog.unrestrictedSearchResults(query, path=timeSlot.getPath())
            if len(brains) > 0:
                person = brains[0]._unrestrictedGetObject()
                api.content.transition(obj=person, transition="signup")
                person.reindexObject()


# send out a notification based on workflow transition event
def sendNotification(obj, event):
    if event.transition and event.transition.id == "signup":
        sendSignupNotificationEmail(obj)

    if event.transition and event.transition.id == "putOnWaitingList":
        sendWaitingListConfirmationEmail(obj)

    if event.transition and event.transition.id == "signoff":
        sendSignOffNotification(obj)
        if event.old_state.id == "signedup":
            attemptToFillEmptySpot(obj)
