# -*- coding: utf-8 -*-
from datetime import date
from mbarde.signups import _
from mbarde.signups.utils import emailToPersonId
from mbarde.signups.utils import getAllExtraFields
from mbarde.signups.utils import ploneUserToPersonId
from plone import api
from plone.app.textfield import RichText
from plone.app.vocabularies.catalog import CatalogSource
from plone.dexterity.content import Container
from plone.supermodel import model
from z3c.relationfield.schema import RelationChoice
from zope import schema
from zope.interface import implementer


class IUTSignupSheet(model.Schema):

    text = RichText(
        title=_("Text"),
        description=_("This (formatted) text will be displayed above the form."),
        required=False,
    )

    contactInfo = schema.TextLine(
        title=_("Contact information"),
        description=_("Contact information for the manager of the signup sheet."),
        required=True,
    )

    notifyContactInfo = schema.Bool(
        title=_("Send notification mails to contact info"),
        description=_(
            "Send notifications to the mail address provided in the contact info field on new signups or cancellations."  # noqa: E501
        ),
        default=True,
        required=False,
    )

    signupsRequireConfirmation = schema.Bool(
        title=_("Manager has to confirm signups"),
        description=_("Signups have to be confirmed by the manager (can also be rejected)."),
        default=False,
        required=False,
    )

    allowSignupForExternals = schema.Bool(
        title=_("Allow signup for external user"),
        description=_("Allow signup for users which do not have an university account."),
        default=False,
        required=False,
    )

    enableEmailVerificationForExternals = schema.Bool(
        title=_("Email verification for external users"),
        description=_(
            "Anyone who is not currently logged in has to verify their email address with a one-time code before their signup is completed.",  # noqa: E501
        ),
        default=True,
        required=False,
    )

    allowSignupForMultipleSlots = schema.Bool(
        title=_("Allow signup for multiple slots"),
        description=_("Allow the user to signup for more than one slot."),
        default=False,
        required=False,
    )

    enableAutoMovingUpFromWaitingList = schema.Bool(
        title=_("Automatic move up from waiting list"),
        description=_(
            "If a signup is cancelled, the first person on the waiting list (sorted by date) is automatically signed up."  # noqa: E501
        ),
        default=True,
        required=False,
    )

    showSlotNames = schema.Bool(
        title=_("Show individual time slot names"),
        description=_("Whether or not to show individual slot names."),
        default=True,
        required=False,
    )

    hideAvailability = schema.Bool(
        title=_("Hide availability"),
        description=_("Hide how many persons can sign up for a slot."),
        default=False,
        required=False,
    )

    hideDateTime = schema.Bool(
        title=_("Hide date and time"),
        description=_("For signups that are not bound to a certain time slot."),
        default=False,
        required=False,
    )

    extraFieldsForm = RelationChoice(
        title=_("Additional form"),
        description=_("Additional form to be filled in for registration."),
        source=CatalogSource(portal_type=["EasyForm"]),
        required=False,
    )

    model.fieldset(
        "mailsettings",
        label=_("Mail settings"),
        description=_(
            "Following placeholders can be used:<br/>$$name$$ -> Full name of user<br/>$$title$$ -> Title of the signup sheet<br/>$$url$$ -> URL of the signup sheet<br/>$$slot$$ -> Date and time of slot (name of slot if date and time hid)<br/>$$data$$ -> Additional data (see 'additional form')<br/>$$code$$ -> One-time verification code (only available for the email verification email)"  # noqa: E501
        ),
        fields=[
            "emailOtpSubject",
            "emailOtpContent",
            "emailConfirmationSubject",
            "emailConfirmationContent",
            "emailWaitForConfirmationSubject",
            "emailWaitForConfirmationContent",
            "emailWaitinglistSubject",
            "emailWaitinglistContent",
            "emailCancelSubject",
            "emailCancelContent",
        ],
    )

    # email verification (OTP) email
    emailOtpSubject = schema.TextLine(
        title=_("Email verification email subject"),
        description=_(
            "This email will be send to verify the email address of a user who is not "
            "logged in (if field 'Email verification for external users' is set)."
        ),
        required=True,
        default="$$title$$ - Your verification code",
    )

    emailOtpContent = schema.Text(
        title=_("Email Verification Email Content"),
        required=True,
        default=(
            "Hello $$name$$,\n\n"
            "Please use the following code to verify your email address and complete "
            "your signup:\n\n"
            "$$code$$\n\n"
            "This code is valid for 15 minutes."
        ),
    )

    # confirmation email
    emailConfirmationSubject = schema.TextLine(
        title=_("Confirmation email subject"),
        description=_("This email will be send on successful registration."),
        required=True,
        default="$$title$$ - Registration Confirmation",
    )

    emailConfirmationContent = schema.Text(
        title=_("Confirmation Email Content"),
        required=True,
        default=(
            "Hello $$name$$,\n\n"
            "This message is to confirm that you have been signed up for:\n"
            "$$slot$$\n\n"
            "$$data$$\n\n"
            "$$url$$"
        ),
    )

    # wait for confirmation email
    emailWaitForConfirmationSubject = schema.TextLine(
        title=_("Wait for confirmation email subject"),
        description=_(
            'This email will be send when user registered for a timeslot and a confirmation is required (if field "Manager has to confirm signups" is set).'  # noqa: E501
        ),
        required=True,
        default="$$title$$ - Wait For Confirmation",
    )

    emailWaitForConfirmationContent = schema.Text(
        title=_("Wait for confirmation email content"),
        required=True,
        default=(
            "Hello $$name$$,\n\n"
            "You signed up for following slot:\n"
            "$$slot$$\n"
            "You will receive another email as soon as your registration has been "
            "confirmed (or rejected).\n\n"
            "$$data$$\n\n"
            "$$url$$"
        ),
    )

    # waiting list email
    emailWaitinglistSubject = schema.TextLine(
        title=_("Waitinglist email subject"),
        description=_("This email will be send on registration for the waitinglist."),
        required=True,
        default="$$title$$ - Waiting List Confirmation",
    )

    emailWaitinglistContent = schema.Text(
        title=_("Waitinglist Email Content"),
        required=True,
        default=(
            "Hello $$name$$,\n\n"
            "This message is to confirm that you have been added to the waiting list "
            "for:\n"
            "$$slot$$\n\n"
            "$$data$$\n\n"
            "$$url$$"
        ),
    )

    # cancellation email
    emailCancelSubject = schema.TextLine(
        title=_("Cancellation email subject"),
        description=_("This email will be send on a registration cancellation."),
        required=True,
        default="$$title$$ - Cancellation Notification",
    )

    emailCancelContent = schema.Text(
        title=_("Cancellation email content"),
        required=True,
        default=(
            "Hello $$name$$,\n\n"
            "Following slot has been cancelled:\n"
            "$$slot$$\n\n"
            "$$data$$\n\n"
            "$$url$$"
        ),
    )


@implementer(IUTSignupSheet)
class UTSignupSheet(Container):

    def countSlots(self):
        brains = api.content.find(context=self, portal_type="UTTimeslot")
        return len(brains)

    def getSlotsBrainsByPersonId(self, personId, reviewState):
        if reviewState:
            brains = self.portal_catalog.unrestrictedSearchResults(
                portal_type="UTPerson", id=personId, review_state=reviewState, path=self.getPath()
            )
        else:
            brains = self.portal_catalog.unrestrictedSearchResults(
                portal_type="UTPerson", id=personId, path=self.getPath()
            )
        return brains

    def countSlotsByEmail(self, email, reviewState=False):
        personId = emailToPersonId(email)
        brains = self.getSlotsBrainsByPersonId(personId, reviewState)
        return len(brains)

    def getSlotsOfCurrentUser(self, reviewState=False):
        if api.user.is_anonymous():
            return []

        user = api.user.get_current()
        personId = ploneUserToPersonId(user)
        brains = self.getSlotsBrainsByPersonId(personId, reviewState)

        slots = []
        today = date.today()
        for brain in brains:
            person = brain.unrestrictedTraverse(brain.getPath())

            timeSlot = person.aq_parent
            day = timeSlot.aq_parent
            if day.date >= today:
                slots.append(timeSlot)

        return slots

    def countSlotsOfCurrentUser(self, review_state=False):
        return len(self.getSlotsOfCurrentUser())

    def isCurrentUserLoggedIn(self):
        return not api.user.is_anonymous()

    def getCurrentUsername(self):
        return api.user.get_current().getUserName()

    # Return a string containig the person's email-address as a sentence
    def getContactInfoAsSentence(self):
        return self.contactInfo.replace("@", " at ")

    def getDay(self, dayId):
        brains = api.content.find(context=self, portal_type="UTDay", id=dayId)
        if len(brains) == 0:
            raise ValueError("The date {0} was not found.".format(dayId))
        return brains[0].getObject()

    def getDays(self, onlyIncludeUpcomingDays=True):
        brains = api.content.find(context=self, portal_type="UTDay", depth=1)
        if len(brains) == 0:
            return []

        results = []
        today = date.today()
        for brain in brains:
            day = brain.getObject()
            if not onlyIncludeUpcomingDays or day.date >= today:
                results.append(day)

        return results

    # Returns tuple with three elements:
    # [0] -> dictionary where key is month and value is list of days in this month
    # [1] -> sorted list of keys (to make sure that March is displayed before April etc.)
    # [2] -> dictionary containing the (untranslated) abbreviated month name, e.g. 'Mar'
    #        (wrapping this in `_()` cannot be picked up by i18ndude, since it can only
    #        extract literal strings passed to `_()`, not the runtime result of
    #        strftime() - so it would never actually be translatable)
    def getDaysGroupedByMonth(self):
        days = self.getDays()
        result = dict()
        mTrans = dict()

        for day in days:
            # use integer coded month as key since it is easier to sort automatically
            # february 2019: 201902
            # december 2018: 201812
            monthStr = str(day.date.month)
            if len(monthStr) < 2:
                monthStr = "0" + monthStr
            key = str(day.date.year) + monthStr

            if key in result:
                result[key].append(day)
            else:
                result[key] = [day]
                # abbreviated month name, e.g. 'Mar' (see note above)
                mTrans[key] = day.date.strftime("%b")

        keys = sorted(result.keys())

        return (result, keys, mTrans)

    def removeAllPersons(self):
        brains = self.portal_catalog.unrestrictedSearchResults(
            portal_type="UTPerson", path=self.getPath()
        )
        for brain in brains:
            api.content.delete(obj=brain.getObject(), check_linkintegrity=False)
        return len(brains)

    def getExtraFields(self):
        return getAllExtraFields(self)

    def getExtraFieldsVocabulary(self):
        extra_fields = getAllExtraFields(self)
        vocab = []
        for field in extra_fields:
            vocab.append((field["name"], field["label"]))
        return vocab

    def getPath(self):
        path = self.getPhysicalPath()
        return "/".join(path)
