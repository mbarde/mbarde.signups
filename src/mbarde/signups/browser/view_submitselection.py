# -*- coding: utf-8 -*-
from mbarde.signups import _
from mbarde.signups import otp
from mbarde.signups.utils import emailToPersonId
from mbarde.signups.utils import replaceCustomMailPlaceholders
from plone import api
from plone.memoize import instance
from Products.CMFPlone.interfaces import ILanguage
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ZopeTwoPageTemplateFile
from Products.validation import validation
from z3c.caching.purge import Purge
from zope.component import getMultiAdapter
from zope.event import notify
from zope.i18n import translate


class SubmitSelection(BrowserView):

    resultTemplate = ZopeTwoPageTemplateFile("templates/view_submitselection.pt")
    otpTemplate = ZopeTwoPageTemplateFile("templates/view_verifyemail.pt")

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @instance.memoize
    def extra_fields(self):
        return self.context.getExtraFieldsVocabulary()

    def submitUserSelection(self):
        self.results = list()

        portal_state = getMultiAdapter((self.context, self.request), name="plone_portal_state")
        self.currentLanguage = portal_state.language()

        self.getUserInput()

        self.agreeDataUsage = len(self.request.get("agreeDataUsage", "").strip()) > 0
        self.prename = self.request.get("inputPrename", "").strip()
        self.surname = self.request.get("inputSurname", "").strip()
        self.email = self.request.get("inputEmail", "").strip()

        if self.areAnyRequiredFieldsEmpty() or not self.isAtLeastOneSlotSelected():
            return self.resultTemplate()

        # anyone who is not currently logged in has to verify they actually
        # control the email address they entered before their signup is
        # finalized - even if it happens to match an existing account
        if self.context.enableEmailVerificationForExternals and api.user.is_anonymous():
            return self.startEmailVerification()

        for slotIDLabel in self.selectedSlots:
            self.getSlotAndSignUserUpForIt(slotIDLabel)

        return self.resultTemplate()

    def getExtraFieldsData(self):
        data = {}
        for fieldName, label in self.extra_fields():
            data[fieldName] = getattr(self, fieldName, "")
        return data

    def startEmailVerification(self):
        self.otpCode = otp.generateOtpCode()

        payload = {
            "email": self.email,
            "prename": self.prename,
            "surname": self.surname,
            "agreeDataUsage": self.agreeDataUsage,
            "extraFields": self.getExtraFieldsData(),
            "selectedSlots": self.selectedSlots,
            "language": self.currentLanguage,
        }
        self.token = otp.createToken(payload, self.otpCode)

        self.sendOtpEmail()

        return self.otpTemplate()

    def sendOtpEmail(self):
        lang = self.currentLanguage or "en"
        signupSheet = self.context
        contactInfo = signupSheet.contactInfo
        url = signupSheet.absolute_url()
        personName = "{0} {1}".format(self.prename, self.surname)
        slotLabel = ", ".join(self.selectedSlots)

        subject = signupSheet.emailOtpSubject
        if subject is None or len(subject) == 0:
            subject = "{0} - {1}".format(
                signupSheet.Title(), translate(_("Your verification code"), target_language=lang)
            )
        else:
            subject = replaceCustomMailPlaceholders(
                subject, personName, signupSheet.Title(), url, slotLabel, ""
            ).replace("$$code$$", self.otpCode)

        content = signupSheet.emailOtpContent
        if content is not None and len(content) > 0:
            message = replaceCustomMailPlaceholders(
                content, personName, signupSheet.Title(), url, slotLabel, ""
            ).replace("$$code$$", self.otpCode)
        else:
            # default message if no content has been specified
            message = (
                translate(_("Hello"), target_language=lang)
                + " "
                + self.prename
                + " "
                + self.surname
                + ",\n\n"
            )
            message += (
                translate(
                    _(
                        "Please use the following code to verify your email address and "
                        "complete your signup:"
                    ),
                    target_language=lang,
                )
                + "\n\n"
            )
            message += self.otpCode + "\n\n"
            message += (
                translate(_("This code is valid for 15 minutes."), target_language=lang) + "\n\n"
            )

            if len(contactInfo) > 0:
                message += (
                    translate(_("If you have any questions please contact:"), target_language=lang)
                    + " "
                    + contactInfo
                    + "\n\n"
                )

        api.portal.send_email(
            recipient=self.email, sender=contactInfo, subject=subject, body=message
        )

    def getUserInput(self):
        for fieldName, label in self.extra_fields():
            value = self.request.get("form.widgets." + fieldName, "")

            # if value is a list/tuple (i.e. multiple select field)
            # we need to convert it to string before storing
            if isinstance(value, list) or isinstance(value, tuple):
                value = ", ".join([i for i in value if len(i.strip()) > 0])
            else:
                value = str(value)

            setattr(self, fieldName, value)

        self.selectedSlots = self.request.get("slotSelection", None)

        if type(self.selectedSlots) is not list:
            self.selectedSlots = [self.selectedSlots]

    def isAtLeastOneSlotSelected(self):
        return self.selectedSlots != [None]

    def areAnyRequiredFieldsEmpty(self):
        return len(self.getListOfEmptyRequiredFields()) > 0

    def getListOfEmptyRequiredFields(self):
        fields = self.context.getExtraFields()

        requiredExtraFields = []
        emptyRequiredFields = []

        for field in fields:
            if field["required"]:
                requiredExtraFields.append(field)

        for field in requiredExtraFields:
            if len(getattr(self, field["name"], "")) < 1:
                emptyRequiredFields.append(field["label"])

        if getattr(self.context, "dataUsageDeclaration", False) and getattr(
            self.context, "dataUsageDeclarationConsentRequired", True
        ):
            if self.agreeDataUsage is False:
                emptyRequiredFields.append(
                    translate(
                        _("fieldName_agreeDataUsageDeclaration"),
                        target_language=self.currentLanguage,
                    )
                )

        fields = [("prename", "Prename"), ("surname", "Surname"), ("email", "Your email address")]
        for name, label in fields:
            if len(getattr(self, name)) < 1:
                emptyRequiredFields.append(
                    translate(_(label), target_language=self.currentLanguage)
                )

        return emptyRequiredFields

    def getSlotAndSignUserUpForIt(self, slotIDLabel):
        status = "error"
        error = ""

        allowSignupForMultipleSlots = self.context.allowSignupForMultipleSlots

        date, time = slotIDLabel.split(" @ ")
        day = self.context.getDay(date)
        timeSlot = day.getTimeSlot(time, True)
        slotTitleLabel = timeSlot.getLabel()
        allowWaitingList = timeSlot.allowWaitingList
        numberOfAvailableSlots = timeSlot.getNumberOfAvailableSlots()

        if (not allowSignupForMultipleSlots) and self.context.countSlotsByEmail(self.email) > 0:
            error = _("You are already signed up for a slot in this signup sheet.")

        elif timeSlot.isUserSignedUpForThisSlot(self.email):
            error = _("You are already signed up for this slot.")

        elif allowWaitingList or numberOfAvailableSlots > 0:
            person = self.createPersonObject(timeSlot)

            if numberOfAvailableSlots > 0:
                if self.context.signupsRequireConfirmation:
                    if self.isEmailValid():
                        self.sendWaitForConfirmationEmail(self.context, slotTitleLabel, person)
                        status = "unconfirmed"
                else:
                    # sign up user directly if there are available slots and
                    # no confirmation by the manager is required
                    self.signupPerson(person)
                    status = "signedup"
            else:
                self.putPersonOnWaitingList(person)
                status = "waiting"

            # purge signup view to make sure everybody sees updated info
            notify(Purge(self.context))
        else:
            error = _("The slot you selected is already full. Please select a different one.")

        result = dict()
        result["slotLabel"] = slotTitleLabel
        result["status"] = status
        result["error"] = error
        self.results.append(result)

    def createPersonObject(self, container):
        # do not use api.content.create() since we bypass security here
        # to avoid permitting any permissions for anonymous
        portal_types = api.portal.get_tool("portal_types")
        type_info = portal_types.getTypeInfo("UTPerson")
        personId = emailToPersonId(self.email)
        newPerson = type_info._constructInstance(container, personId)

        newPerson.email = self.email
        newPerson.title = "{0} {1}".format(self.prename, self.surname)
        newPerson.prename = self.prename
        newPerson.surname = self.surname

        # also store names of extra fields to be able to read them out even
        # if extra field form changes (used in timeslotperson_view)
        extraFieldNames = []
        for fieldName, label in self.extra_fields():
            setattr(newPerson, fieldName, getattr(self, fieldName))
            extraFieldNames.append(fieldName)
        setattr(newPerson, "extraFieldNames", extraFieldNames)
        newPerson.reindexObject()

        return newPerson

    def signupPerson(self, person):
        api.content.transition(person, "signup")
        person.reindexObject()

    def putPersonOnWaitingList(self, person):
        api.content.transition(person, "putOnWaitingList")
        person.reindexObject()

    def isEmailValid(self):
        isEmail = validation.validatorFor("isEmail")
        return isEmail(self.email) == 1

    def sendWaitForConfirmationEmail(self, signupSheet, slotTitleLabel, person):
        url = signupSheet.absolute_url()

        lang = ILanguage(signupSheet).get_language()
        if len(lang) == 0:
            lang = "en"

        extraInfoStr = ""
        for fieldStr, fieldTrans in self.extra_fields():
            value = getattr(self, fieldStr, "")
            if len(value) > 0:
                extraInfoStr += "{0}: {1}\n".format(
                    translate(fieldTrans, target_language=lang), value
                )

        # mail to person who signed up to waiting list
        contactInfo = signupSheet.contactInfo
        toEmail = self.email
        fromEmail = signupSheet.contactInfo

        subject = replaceCustomMailPlaceholders(
            signupSheet.emailWaitForConfirmationSubject,
            person.Title(),
            signupSheet.Title(),
            url,
            slotTitleLabel,
            extraInfoStr,
        )
        message = replaceCustomMailPlaceholders(
            signupSheet.emailWaitForConfirmationContent,
            person.Title(),
            signupSheet.Title(),
            url,
            slotTitleLabel,
            extraInfoStr,
        )

        api.portal.send_email(recipient=toEmail, sender=fromEmail, subject=subject, body=message)

        # mail to contact person of the signup sheet
        isEmail = validation.validatorFor("isEmail")
        if signupSheet.notifyContactInfo and len(contactInfo) > 0 and isEmail(contactInfo):
            toEmail = contactInfo
            fromEmail = signupSheet.contactInfo

            subject = "{0} - {1}".format(
                signupSheet.Title(), translate(_("Wait For Confirmation"), target_language=lang)
            )

            message = translate(_("Hello"), target_language=lang) + ",\n\n"
            message += (
                translate(_("A new signup is waiting for confirmation"), target_language=lang)
                + " ("
                + person.absolute_url()
                + "):\n"
            )  # noqa: E501
            message += slotTitleLabel + "\n"
            message += translate(_("Name"), target_language=lang) + ": " + person.Title() + "\n"
            message += translate(_("E-Mail"), target_language=lang) + ": " + self.email + "\n\n"

            if len(extraInfoStr) > 0:
                message += (
                    translate(_("Additional information"), target_language=lang) + "\n"
                )  # noqa: E501
                message += extraInfoStr + "\n\n"

            message += "\nURL: " + person.absolute_url() + "\n\n"

            api.portal.send_email(
                recipient=toEmail, sender=fromEmail, subject=subject, body=message
            )

    def hasAtLeastOneError(self):
        for result in self.results:
            if len(result["error"]) > 0:
                return True

        if self.areAnyRequiredFieldsEmpty():
            return True

        if not self.isAtLeastOneSlotSelected():
            return True

        return False
