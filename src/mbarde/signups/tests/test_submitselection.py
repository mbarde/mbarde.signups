# -*- coding: utf-8 -*-
"""Tests for SubmitSelection, focused on server-side enforcement of settings
that the form only used to respect client-side (`allowSignupForExternals`,
`lockPersonalData`).
"""

from AccessControl.unauthorized import Unauthorized
from datetime import date
from datetime import time
from datetime import timedelta
from mbarde.signups.testing import MBARDE_SIGNUPS_INTEGRATION_TESTING  # noqa
from plone import api
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.registry.interfaces import IRegistry
from zope.component import getUtility

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
