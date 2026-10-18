# -*- coding: utf-8 -*-
"""Tests for SubmitSelection, focused on server-side enforcement of settings
that the form only used to respect client-side (`allowSignupForExternals`,
`lockPersonalData`).
"""

from AccessControl.unauthorized import Unauthorized
from datetime import date
from datetime import time
from datetime import timedelta
from mbarde.signups.testing import MBARDE_SIGNUPS_FUNCTIONAL_TESTING  # noqa
from mbarde.signups.testing import MBARDE_SIGNUPS_INTEGRATION_TESTING  # noqa
from plone import api
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.registry.interfaces import IRegistry
from zope.component import getUtility

import transaction
import unittest


class LockPersonalDataSubmitTest(unittest.TestCase):

    layer = MBARDE_SIGNUPS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

        api.user.create(
            email="member@example.org",
            username="jdoe",
            password="secret1234",
            properties={"location": "Jane", "home_page": "Doe"},
        )
        registry = getUtility(IRegistry)
        registry["mbarde.signups.member_property_prename"] = "location"
        registry["mbarde.signups.member_property_surname"] = "home_page"

        self.sheet = api.content.create(
            container=self.portal,
            type="UTSignupSheet",
            id="sheet1",
            allowSignupForExternals=False,
            lockPersonalData=True,
            signupsRequireConfirmation=False,
            contactInfo="",
        )
        portal_types = self.portal.portal_types
        day_id = portal_types.constructContent("UTDay", self.sheet, "d1", title="Day 1")
        day = self.sheet[day_id]
        day.date = date.today() + timedelta(days=1)
        ts_id = portal_types.constructContent(
            "UTTimeslot",
            day,
            "t1",
            title="T1",
            startTime=time(10, 0),
            endTime=time(12, 0),
            maxCapacity=5,
        )
        self.timeslot = day[ts_id]

    def tearDown(self):
        logout()
        login(self.portal, TEST_USER_NAME)

    def test_forged_personal_data_is_ignored_when_locked(self):
        logout()
        login(self.portal, "jdoe")

        self.request.form.update(
            {
                "inputPrename": "Forged",
                "inputSurname": "Attacker",
                "inputEmail": "attacker@evil.example",
                "slotSelection": self.timeslot.getIDLabel(),
            }
        )

        view = self.sheet.unrestrictedTraverse("@@submit-user-selection")
        view()

        person = self.timeslot["member-example-org"]
        self.assertEqual(person.prename, "Jane")
        self.assertEqual(person.surname, "Doe")
        self.assertEqual(person.email, "member@example.org")
        # the forged email must not have been used as the person's identity
        self.assertNotIn("attacker-evil-example", self.timeslot.objectIds())

    def test_own_data_is_used_when_locked_and_request_matches(self):
        logout()
        login(self.portal, "jdoe")

        self.request.form.update(
            {
                "inputPrename": "Jane",
                "inputSurname": "Doe",
                "inputEmail": "member@example.org",
                "slotSelection": self.timeslot.getIDLabel(),
            }
        )

        view = self.sheet.unrestrictedTraverse("@@submit-user-selection")
        view()

        person = self.timeslot["member-example-org"]
        self.assertEqual(person.prename, "Jane")
        self.assertEqual(person.surname, "Doe")


class AllowSignupForExternalsEnforcementTest(unittest.TestCase):
    """`allowSignupForExternals` used to only hide the signup form for
    anonymous users in the template - submitting directly to
    `@@submit-user-selection` was never actually checked server-side.
    """

    layer = MBARDE_SIGNUPS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

        self.sheet = api.content.create(
            container=self.portal,
            type="UTSignupSheet",
            id="sheet1",
            allowSignupForExternals=False,
            # isolate the allowSignupForExternals check from the OTP
            # verification flow, which is tested separately elsewhere
            enableEmailVerificationForExternals=False,
            signupsRequireConfirmation=False,
            contactInfo="",
        )
        portal_types = self.portal.portal_types
        day_id = portal_types.constructContent("UTDay", self.sheet, "d1", title="Day 1")
        day = self.sheet[day_id]
        day.date = date.today() + timedelta(days=1)
        ts_id = portal_types.constructContent(
            "UTTimeslot",
            day,
            "t1",
            title="T1",
            startTime=time(10, 0),
            endTime=time(12, 0),
            maxCapacity=5,
        )
        self.timeslot = day[ts_id]

    def tearDown(self):
        logout()
        login(self.portal, TEST_USER_NAME)

    def test_anonymous_submission_rejected_when_externals_disallowed(self):
        logout()

        self.request.form.update(
            {
                "inputPrename": "Anon",
                "inputSurname": "Ymous",
                "inputEmail": "anon@example.org",
                "slotSelection": self.timeslot.getIDLabel(),
            }
        )

        view = self.sheet.unrestrictedTraverse("@@submit-user-selection")
        with self.assertRaises(Unauthorized):
            view()

        self.assertNotIn("anon-example-org", self.timeslot.objectIds())

    def test_anonymous_submission_allowed_when_externals_allowed(self):
        self.sheet.allowSignupForExternals = True
        logout()

        self.request.form.update(
            {
                "inputPrename": "Anon",
                "inputSurname": "Ymous",
                "inputEmail": "anon@example.org",
                "slotSelection": self.timeslot.getIDLabel(),
            }
        )

        view = self.sheet.unrestrictedTraverse("@@submit-user-selection")
        view()

        self.assertIn("anon-example-org", self.timeslot.objectIds())

    def test_logged_in_submission_allowed_regardless_of_setting(self):
        api.user.create(email="member@example.org", username="jdoe", password="secret1234")
        logout()
        login(self.portal, "jdoe")

        self.request.form.update(
            {
                "inputPrename": "Jane",
                "inputSurname": "Doe",
                "inputEmail": "member@example.org",
                "slotSelection": self.timeslot.getIDLabel(),
            }
        )

        view = self.sheet.unrestrictedTraverse("@@submit-user-selection")
        view()

        self.assertIn("member-example-org", self.timeslot.objectIds())


class DuplicateTimeslotSignupTest(unittest.TestCase):
    """Regression test for
    https://github.com/mbarde/mbarde.signups/issues/30.

    Duplicating a UTTimeslot (e.g. via Plone's "Duplicate" action) without
    changing its start/end time leaves the copy with an id ending in "-1",
    because `ut_timeslot.autoSetID` computes the same "natural" id for both
    siblings and `api.content.rename(..., safe_id=True)` disambiguates the
    collision. That "-1" id never stops colliding with the original, so
    *every* future edit of either slot (e.g. a new signup, which fires
    `IObjectModified` on the parent timeslot via `notifyContainerModified`)
    re-triggers `autoSetID` and schedules another rename attempt.

    That rename used to run under whatever security manager happened to be
    active when the transaction committed - for a real anonymous/external
    signup, that is the anonymous user, who has no permission to add
    content to the UTDay, so the rename blew up the *entire* request with
    `OFS.CopySupport.CopyError: Insufficient privileges` (see
    `utils._renameNow`).

    This needs FUNCTIONAL_TESTING rather than INTEGRATION_TESTING because
    the bug is specifically about what happens on a real
    `transaction.commit()` - that's when the before-commit hook that
    performs the deferred rename actually fires.
    """

    layer = MBARDE_SIGNUPS_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

        self.sheet = api.content.create(
            container=self.portal,
            type="UTSignupSheet",
            id="sheet1",
            allowSignupForExternals=True,
            enableEmailVerificationForExternals=False,
            signupsRequireConfirmation=False,
            contactInfo="",
        )
        portal_types = self.portal.portal_types
        day_id = portal_types.constructContent("UTDay", self.sheet, "d1", title="Day 1")
        self.day = self.sheet[day_id]
        self.day.date = date.today() + timedelta(days=1)
        ts_id = portal_types.constructContent(
            "UTTimeslot",
            self.day,
            "t1",
            title="T1",
            startTime=time(10, 0),
            endTime=time(12, 0),
            maxCapacity=5,
        )
        self.timeslot = self.day[ts_id]
        # commit so the before-commit-hook-driven autoSetID rename of "t1"
        # to its natural id ("10-00-12-00") actually runs
        transaction.commit()
        self.timeslot = self.day[self.timeslot.getId()]

        # duplicate it exactly like Plone's "Duplicate" action would -
        # copy it and paste it back into the very same UTDay, without
        # changing its start/end time
        cb_copy_data = self.day.manage_copyObjects(ids=[self.timeslot.getId()])
        self.day.manage_pasteObjects(cb_copy_data)
        transaction.commit()

        otherIds = [i for i in self.day.objectIds() if i != self.timeslot.getId()]
        assert len(otherIds) == 1, self.day.objectIds()
        self.duplicate = self.day[otherIds[0]]
        assert self.duplicate.getId().endswith("-1"), self.duplicate.getId()

    def tearDown(self):
        logout()
        login(self.portal, TEST_USER_NAME)

    def _signupAnonymously(self, email):
        logout()
        self.request.form.update(
            {
                "inputPrename": "Jane",
                "inputSurname": "Doe",
                "inputEmail": email,
                "slotSelection": self.duplicate.getIDLabel(),
            }
        )
        view = self.sheet.unrestrictedTraverse("@@submit-user-selection")
        view()
        # this is where the deferred rename used to blow up with
        # `CopyError: Insufficient privileges` under the anonymous user
        transaction.commit()

    def test_anonymous_signup_for_duplicated_slot_does_not_crash(self):
        self._signupAnonymously("jane@example.org")

        self.duplicate = self.day[self.duplicate.getId()]
        self.assertIn("jane-example-org", self.duplicate.objectIds())
        # the id must still be the disambiguated one, not drifted back
        # towards the original's id
        self.assertEqual(self.duplicate.getId(), "10-00-12-00-1")

    def test_repeated_signups_keep_the_disambiguated_id_stable(self):
        self._signupAnonymously("jane@example.org")
        self.duplicate = self.day[self.duplicate.getId()]

        self._signupAnonymously("john@example.org")
        self.duplicate = self.day[self.duplicate.getId()]

        self.assertEqual(
            sorted(self.duplicate.objectIds()),
            ["jane-example-org", "john-example-org"],
        )
        self.assertEqual(self.duplicate.getId(), "10-00-12-00-1")

        # the original slot must be completely unaffected
        original = self.day[self.timeslot.getId()]
        self.assertEqual(original.getId(), "10-00-12-00")
        self.assertEqual(list(original.objectIds()), [])
