# -*- coding: utf-8 -*-
"""Tests for the $$sign_off_url$$ feature: an unguessable, signed link
that lets a person cancel their own registration without logging in
(see signoff.py and browser/view_directsignoff.py).
"""

from datetime import date
from datetime import time
from datetime import timedelta
from mbarde.signups import otp
from mbarde.signups import signoff
from mbarde.signups.testing import MBARDE_SIGNUPS_INTEGRATION_TESTING  # noqa
from mbarde.signups.utils import emailToPersonId
from plone import api
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.keyring.interfaces import IKeyManager
from plone.uuid.interfaces import IMutableUUID
from plone.uuid.interfaces import IUUID
from zope.component import getUtility

import base64
import email
import hashlib
import hmac
import json
import unittest
import unittest.mock


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


class SignOffTokenRobustnessTest(unittest.TestCase):
    """Edge cases and hardening around token verification itself."""

    layer = MBARDE_SIGNUPS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

        self.sheet, self.day, self.timeslot, self.person = createFullStack(self.portal)

    def test_survives_the_persons_path_changing(self):
        # the whole point of binding to the UID rather than the path
        # (see signoff.py's module docstring, and GitHub issue #30) -
        # rename the timeslot (which moves the person underneath it to
        # a new path) and confirm the token still resolves correctly
        token = signoff.createSignOffToken(self.person)

        api.content.rename(obj=self.timeslot, new_id="renamed-slot", safe_id=True)

        resolved = signoff.resolvePersonFromSignOffToken(token)
        self.assertIsNotNone(resolved)
        self.assertEqual(IUUID(resolved), IUUID(self.person))
        self.assertIn("renamed-slot", "/".join(resolved.getPhysicalPath()))

    def test_survives_ordinary_key_rotation(self):
        token = signoff.createSignOffToken(self.person)

        getUtility(IKeyManager).rotate(ring="_anon")

        resolved = signoff.resolvePersonFromSignOffToken(token)
        self.assertEqual(IUUID(resolved), IUUID(self.person))

    def test_rejected_once_its_signing_secret_is_fully_retired(self):
        token = signoff.createSignOffToken(self.person)

        manager = getUtility(IKeyManager)
        ringSize = len(manager["_anon"])
        for _i in range(ringSize):
            manager.rotate(ring="_anon")

        with self.assertRaises(signoff.InvalidSignOffToken):
            signoff.resolvePersonFromSignOffToken(token)

    def test_malformed_base64_body_with_a_genuinely_valid_signature_is_rejected_cleanly(self):
        # can only happen if the body is corrupted *after* signing (or
        # by a bug), since an attacker without the secret cannot
        # produce a matching signature for an arbitrary body - but the
        # decode step must still fail closed rather than crash
        secret = getUtility(IKeyManager).secret(ring="_anon").encode("utf-8")
        body = b"not-valid-base64!!!"
        signature = hmac.new(secret, body, hashlib.sha256).hexdigest()
        forged = (body + b"." + signature.encode("utf-8")).decode("utf-8")

        with self.assertRaises(signoff.InvalidSignOffToken):
            signoff.resolvePersonFromSignOffToken(forged)

    def test_garbage_signature_encoding_is_rejected_cleanly(self):
        token = signoff.createSignOffToken(self.person)
        body, _signature = token.split(".")
        forged = body + ".%%%not-hex-at-all%%%"

        with self.assertRaises(signoff.InvalidSignOffToken):
            signoff.resolvePersonFromSignOffToken(forged)

    def test_excessively_long_token_is_rejected_before_expensive_processing(self):
        oversized = "a" * 50000 + "." + "b" * 64

        with unittest.mock.patch("mbarde.signups.signoff.hmac.new") as hmacNew:
            with self.assertRaises(signoff.InvalidSignOffToken):
                signoff.resolvePersonFromSignOffToken(oversized)
            hmacNew.assert_not_called()

        # sanity check: a normal-sized (if invalid) token *does* reach
        # the HMAC step, so the assertion above is actually meaningful
        with unittest.mock.patch("mbarde.signups.signoff.hmac.new", wraps=hmac.new) as hmacNew:
            with self.assertRaises(signoff.InvalidSignOffToken):
                signoff.resolvePersonFromSignOffToken("short.invalid")
            hmacNew.assert_called()

    def test_malformed_uid_in_an_otherwise_validly_signed_token_is_rejected(self):
        secret = getUtility(IKeyManager).secret(ring="_anon").encode("utf-8")
        body = base64.urlsafe_b64encode(json.dumps({"personUID": "not-a-real-uid"}).encode("utf-8"))
        signature = hmac.new(secret, body, hashlib.sha256).hexdigest()
        forged = (body + b"." + signature.encode("utf-8")).decode("utf-8")

        with self.assertRaises(signoff.InvalidSignOffToken):
            signoff.resolvePersonFromSignOffToken(forged)

    def test_duplicate_uid_fails_safe_and_logs_an_integrity_error(self):
        # Plone's UUIDIndex is itself a unique-value index and actively
        # refuses to index a second object under an already-used UID
        # (logging its own error and keeping only the first), so a
        # genuine duplicate can't actually be produced through ordinary
        # content creation/reindexing - confirmed by trying exactly
        # that here first. Exercise the defensive ">1 brains" branch
        # directly instead, in case it's ever reached via some other
        # path (a migration, a lower-level ZODB operation, ...).
        duplicate = api.content.create(
            container=self.timeslot,
            type="UTPerson",
            id="duplicate-person",
            email="duplicate@example.org",
            prename="Dup",
            surname="Licate",
        )
        IMutableUUID(duplicate).set(IUUID(self.person))
        duplicate.reindexObject()
        catalog = api.portal.get_tool("portal_catalog")
        self.assertEqual(
            len(catalog.unrestrictedSearchResults(portal_type="UTPerson", UID=IUUID(self.person))),
            1,
            "Plone's UUIDIndex was expected to refuse the duplicate - "
            "if this now fails, the real (non-mocked) duplicate-UID "
            "case may finally be reachable and should be tested as such",
        )

        token = signoff.createSignOffToken(self.person)
        fakeBrains = [unittest.mock.Mock(), unittest.mock.Mock()]

        with unittest.mock.patch.object(
            catalog, "unrestrictedSearchResults", return_value=fakeBrains
        ):
            with unittest.mock.patch("mbarde.signups.signoff.logger") as logger:
                resolved = signoff.resolvePersonFromSignOffToken(token)

        self.assertIsNone(resolved)
        logger.error.assert_called_once()
        for brain in fakeBrains:
            brain._unrestrictedGetObject.assert_not_called()

    def test_token_not_usable_against_the_otp_endpoint(self):
        # both signoff.py and otp.py sign a payload and read it back
        # from a request parameter literally named "token" - make sure
        # one can't be replayed against the other's verifier. They use
        # independently generated secrets (different keyring rings),
        # so this should already be structurally impossible.
        signOffToken = signoff.createSignOffToken(self.person)

        with self.assertRaises(otp.InvalidToken):
            otp.parseToken(signOffToken)

    def test_otp_token_not_usable_against_the_direct_signoff_endpoint(self):
        otpToken = otp.createToken({"email": self.person.email}, "123456")

        with self.assertRaises(signoff.InvalidSignOffToken):
            signoff.resolvePersonFromSignOffToken(otpToken)


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

    def test_post_with_invalid_token_does_not_sign_off(self):
        # "POST without valid confirmation" - a POST by itself proves
        # nothing; it still needs a token that actually verifies
        self._post("garbage")
        self.assertIsNotNone(self.view.error)
        self.assertEqual(api.content.get_state(self.person), "unconfirmed")

    def test_post_with_missing_token_does_not_sign_off(self):
        self.request.other["method"] = "POST"
        self.request.form.pop("token", None)
        self.view.directSignOff()

        self.assertIsNotNone(self.view.error)
        self.assertEqual(api.content.get_state(self.person), "unconfirmed")

    def test_anonymous_caller_with_invalid_token_cannot_sign_off(self):
        logout()
        try:
            self._post("garbage")
            self.assertIsNotNone(self.view.error)
            self.assertEqual(api.content.get_state(self.person), "unconfirmed")
        finally:
            login(self.portal, TEST_USER_NAME)

    def test_valid_token_grants_no_lasting_permission_to_the_anonymous_caller(self):
        # using the token must not, as a side effect, grant the caller
        # any standing local role/permission on the person object - it
        # should only perform the one specific transition and nothing
        # more. Must be checked as a genuinely anonymous caller, not
        # the Manager test user setUp() elevates to.
        from AccessControl import getSecurityManager

        token = signoff.createSignOffToken(self.person)
        # the object was created by the Manager test user in setUp()
        # (and so already carries *that* user's own "Owner" local role,
        # same as any normal content creation would) - what matters
        # here is that the anonymous caller doesn't pick up a role of
        # their own merely by using the token
        rolesBeforeSignOff = dict(self.person.get_local_roles())

        logout()
        try:
            self._post(token)
            self.assertEqual(api.content.get_state(self.person), "signedoff")

            sm = getSecurityManager()
            self.assertFalse(sm.checkPermission("Modify portal content", self.person))
            self.assertEqual(dict(self.person.get_local_roles()), rolesBeforeSignOff)
            self.assertNotIn("Anonymous User", dict(self.person.get_local_roles()))
        finally:
            login(self.portal, TEST_USER_NAME)

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
        allowWaitingList=True,
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
