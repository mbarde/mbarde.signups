# -*- coding: utf-8 -*-
"""Tests for the $$sign_off_url$$ feature: an unguessable, signed link
that lets a person cancel their own registration without logging in
(see signoff.py and browser/view_directsignoff.py).
"""

from datetime import date
from datetime import time
from datetime import timedelta
from mbarde.signups import signoff
from mbarde.signups.testing import MBARDE_SIGNUPS_INTEGRATION_TESTING  # noqa
from mbarde.signups.utils import emailToPersonId
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.uuid.interfaces import IUUID

import email
import unittest


class SignOffTokenTest(unittest.TestCase):
    """Unit tests for the token itself, independent of the view."""

    layer = MBARDE_SIGNUPS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

        self.sheet, self.day, self.timeslot, self.person = createFullStack(self.portal)

    def test_roundtrip_resolves_the_right_person(self):
        token = signoff.createSignOffToken(self.person)
        resolved = signoff.resolvePersonFromSignOffToken(token)
        self.assertEqual(IUUID(resolved), IUUID(self.person))

    def test_tampered_signature_is_rejected(self):
        token = signoff.createSignOffToken(self.person)
        body, _signature = token.split(".")
        forged = body + ".0" * 32

        with self.assertRaises(signoff.InvalidSignOffToken):
            signoff.resolvePersonFromSignOffToken(forged)

    def test_tampered_payload_is_rejected(self):
        # swap in a different person's token body but keep *a* valid
        # signature shape - must not be accepted as if unmodified
        token = signoff.createSignOffToken(self.person)
        _body, signature = token.split(".")
        forged = "not-a-real-payload." + signature

        with self.assertRaises(signoff.InvalidSignOffToken):
            signoff.resolvePersonFromSignOffToken(forged)

    def test_malformed_token_is_rejected(self):
        with self.assertRaises(signoff.InvalidSignOffToken):
            signoff.resolvePersonFromSignOffToken("not-a-token-at-all")

    def test_empty_token_is_rejected(self):
        with self.assertRaises(signoff.InvalidSignOffToken):
            signoff.resolvePersonFromSignOffToken("")

    def test_token_for_deleted_person_resolves_to_none(self):
        token = signoff.createSignOffToken(self.person)
        api.content.delete(obj=self.person)

        self.assertIsNone(signoff.resolvePersonFromSignOffToken(token))

    def test_url_points_at_direct_signoff_view_with_token(self):
        url = signoff.buildSignOffUrl(self.sheet, self.person)
        self.assertTrue(url.startswith(self.sheet.absolute_url() + "/@@direct-signoff?token="))


class DirectSignOffViewTest(unittest.TestCase):

    layer = MBARDE_SIGNUPS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

        self.sheet, self.day, self.timeslot, self.person = createFullStack(self.portal)
        self.view = self.sheet.unrestrictedTraverse("@@direct-signoff")

    def _get(self, token):
        self.request.other["method"] = "GET"
        self.request.form["token"] = token
        return self.view.directSignOff()

    def _post(self, token):
        self.request.other["method"] = "POST"
        self.request.form["token"] = token
        return self.view.directSignOff()

    def test_get_shows_confirmation_without_changing_state(self):
        token = signoff.createSignOffToken(self.person)
        self._get(token)

        self.assertIsNone(self.view.error)
        self.assertFalse(self.view.alreadySignedOff)
        self.assertEqual(api.content.get_state(self.person), "unconfirmed")

    def test_post_signs_off_from_unconfirmed(self):
        token = signoff.createSignOffToken(self.person)
        self._post(token)

        self.assertEqual(api.content.get_state(self.person), "signedoff")

    def test_post_signs_off_from_waiting(self):
        api.content.transition(obj=self.person, transition="putOnWaitingList")
        token = signoff.createSignOffToken(self.person)
        self._post(token)

        self.assertEqual(api.content.get_state(self.person), "signedoff")

    def test_post_signs_off_from_signedup(self):
        api.content.transition(obj=self.person, transition="signup")
        token = signoff.createSignOffToken(self.person)
        self._post(token)

        self.assertEqual(api.content.get_state(self.person), "signedoff")

    def test_second_post_is_idempotent(self):
        token = signoff.createSignOffToken(self.person)
        self._post(token)
        self.assertEqual(api.content.get_state(self.person), "signedoff")

        self._post(token)
        self.assertEqual(api.content.get_state(self.person), "signedoff")
        self.assertTrue(self.view.alreadySignedOff)

    def test_get_after_signoff_reports_already_cancelled(self):
        token = signoff.createSignOffToken(self.person)
        self._post(token)

        self._get(token)
        self.assertTrue(self.view.alreadySignedOff)

    def test_invalid_token_shows_friendly_error_and_does_not_crash(self):
        self._get("garbage")
        self.assertIsNotNone(self.view.error)
        self.assertEqual(api.content.get_state(self.person), "unconfirmed")

    def test_token_for_deleted_person_shows_friendly_error(self):
        token = signoff.createSignOffToken(self.person)
        api.content.delete(obj=self.person)

        self._get(token)
        self.assertIsNotNone(self.view.error)

    def test_manager_gets_notified_on_self_service_signoff_via_link(self):
        self.sheet.notifyContactInfo = True
        self.sheet.contactInfo = "manager@example.org"

        token = signoff.createSignOffToken(self.person)
        self._post(token)

        # one email to the person (via the generic "signoff" workflow
        # subscriber) and - because this was a *self-service*
        # cancellation - one to the manager (see
        # sendCancellationNotificationToManager's docstring)
        messages = []
        for message in self.portal.MailHost.messages:
            if isinstance(message, bytes):
                message = message.decode("utf-8")
            messages.append(message)
        self.assertEqual(len(messages), 2)

        managerMessages = [m for m in messages if "To: manager@example.org" in m]
        self.assertEqual(len(managerMessages), 1)
        self.assertIn("Cancellation", managerMessages[0])


class SignOffPlaceholderTest(unittest.TestCase):
    """$$sign_off_url$$ must be substituted in exactly the three
    specified templates, and nowhere else."""

    layer = MBARDE_SIGNUPS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

        self.sheet, self.day, self.timeslot, self.person = createFullStack(
            self.portal,
            emailConfirmationContent="Hi $$name$$! Cancel: $$sign_off_url$$",
            emailWaitForConfirmationContent="Hi $$name$$! Cancel: $$sign_off_url$$",
            emailWaitinglistContent="Hi $$name$$! Cancel: $$sign_off_url$$",
            emailCancelContent="Hi $$name$$! Cancel: $$sign_off_url$$",
        )

    def _messages(self):
        # each of these call sites also sends a *separate* notification
        # to the manager (hand-built, never using $$sign_off_url$$ at
        # all) - don't assume ordering, just look at everything that
        # got sent. Decode each raw MIME message to its actual plain-text
        # body - quoted-printable encoding would otherwise mangle (wrap
        # and "=3D"-escape) the "=" and "?" characters in the URL.
        result = []
        for raw in self.portal.MailHost.messages:
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            body = email.message_from_string(raw).get_payload(decode=True)
            result.append(body.decode("utf-8"))
        return result

    def _anyMessageContains(self, text):
        return any(text in message for message in self._messages())

    def test_placeholder_substituted_on_signup_confirmation(self):
        api.content.transition(obj=self.person, transition="signup")
        self.assertTrue(self._anyMessageContains("/@@direct-signoff?token="))
        self.assertFalse(self._anyMessageContains("$$sign_off_url$$"))

    def test_placeholder_substituted_on_waiting_list_confirmation(self):
        api.content.transition(obj=self.person, transition="putOnWaitingList")
        self.assertTrue(self._anyMessageContains("/@@direct-signoff?token="))
        self.assertFalse(self._anyMessageContains("$$sign_off_url$$"))

    def test_placeholder_substituted_on_wait_for_confirmation_email(self):
        # this one is sent directly by SubmitSelection, not via a
        # workflow-transition subscriber - exercise it through the real
        # signup flow instead of a bare transition
        self.sheet.signupsRequireConfirmation = True
        self.sheet.allowSignupForExternals = True

        request = self.layer["request"]
        request.form.update(
            {
                "inputPrename": "Jane",
                "inputSurname": "Doe",
                "inputEmail": "jane2@example.org",
                "slotSelection": self.timeslot.getIDLabel(),
            }
        )
        view = self.sheet.unrestrictedTraverse("@@submit-user-selection")
        view()

        self.assertTrue(self._anyMessageContains("/@@direct-signoff?token="))
        self.assertFalse(self._anyMessageContains("$$sign_off_url$$"))

    def test_placeholder_not_substituted_on_cancellation_email(self):
        # the placeholder was deliberately left out of this call site -
        # like $$user_url$$ on the OTP email, it resolves to an empty
        # string there rather than a working link (there would be
        # nothing left to cancel - the registration is already gone)
        api.content.transition(obj=self.person, transition="signoff")
        self.assertFalse(self._anyMessageContains("$$sign_off_url$$"))
        self.assertFalse(self._anyMessageContains("/@@direct-signoff?token="))
        self.assertTrue(self._anyMessageContains("Hi Jane Doe! Cancel: "))


# create full `stack`: [Signup Sheet] -> [Day] -> [Timeslot] -> [Person]
def createFullStack(portal, **sheetOverrides):
    sheetData = {
        "contactInfo": "manager@example.org",
        "notifyContactInfo": True,
        "allowSignupForExternals": True,
    }
    sheetData.update(sheetOverrides)

    sheet = api.content.create(
        container=portal, type="UTSignupSheet", id="ut_signup_sheet", **sheetData
    )
    day = api.content.create(
        container=sheet,
        type="UTDay",
        id="ut_day",
        date=date.today() + timedelta(days=1),
    )
    timeslot = api.content.create(
        container=day,
        type="UTTimeslot",
        id="ut_timeslot",
        startTime=time(10, 0),
        endTime=time(12, 0),
        maxCapacity=5,
    )
    email = "person@example.org"
    person = api.content.create(
        container=timeslot,
        type="UTPerson",
        id=emailToPersonId(email),
        email=email,
        prename="Jane",
        surname="Doe",
    )
    person.title = "{0} {1}".format(person.prename, person.surname)
    person.reindexObject()

    return sheet, day, timeslot, person
