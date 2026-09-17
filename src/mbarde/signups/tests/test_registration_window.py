# -*- coding: utf-8 -*-
"""Tests for UTTimeslot's registration window, driven by the IPublication
behavior's effective/expiration dates:

1. expires set, still in the future -> "Signup open until X" shown
   alongside the normal, still-selectable slot.
2. expires set, in the past -> "(expired)" ("abgelaufen") shown, as before.
3. effective set, still in the future -> signup blocked (front- and
   backend) and "Signup opens on X" shown instead.
4. Backend: signup is only accepted while now is within
   [effective, expires] (if set).
"""

from datetime import date
from datetime import time
from datetime import timedelta
from DateTime import DateTime
from mbarde.signups.testing import MBARDE_SIGNUPS_INTEGRATION_TESTING  # noqa
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID

import unittest


class RegistrationWindowLogicTest(unittest.TestCase):

    layer = MBARDE_SIGNUPS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.portal_types = self.portal.portal_types
        self.sheet = api.content.create(
            container=self.portal, type="UTSignupSheet", id="sheet1", contactInfo=""
        )
        day_id = self.portal_types.constructContent("UTDay", self.sheet, "d1", title="Day 1")
        self.day = self.sheet[day_id]
        self.day.date = date.today() + timedelta(days=1)
        ts_id = self.portal_types.constructContent(
            "UTTimeslot",
            self.day,
            "t1",
            title="T1",
            startTime=time(10, 0),
            endTime=time(12, 0),
            maxCapacity=5,
        )
        self.timeslot = self.day[ts_id]

    def test_defaults_are_open_with_no_labels(self):
        self.assertFalse(self.timeslot.isRegistrationExpired())
        self.assertFalse(self.timeslot.isRegistrationNotYetOpen())
        self.assertTrue(self.timeslot.isRegistrationOpen())
        self.assertEqual(self.timeslot.getRegistrationEffectiveLabel(), "")
        self.assertEqual(self.timeslot.getRegistrationExpiresLabel(), "")

    def test_expires_in_future_is_open(self):
        self.timeslot.expiration_date = DateTime() + 1
        self.assertFalse(self.timeslot.isRegistrationExpired())
        self.assertTrue(self.timeslot.isRegistrationOpen())

    def test_expires_in_past_is_expired_and_not_open(self):
        self.timeslot.expiration_date = DateTime() - 1
        self.assertTrue(self.timeslot.isRegistrationExpired())
        self.assertFalse(self.timeslot.isRegistrationOpen())

    def test_effective_in_future_is_not_yet_open(self):
        self.timeslot.effective_date = DateTime() + 1
        self.assertTrue(self.timeslot.isRegistrationNotYetOpen())
        self.assertFalse(self.timeslot.isRegistrationOpen())
        self.assertFalse(self.timeslot.isRegistrationExpired())

    def test_effective_in_past_is_open(self):
        self.timeslot.effective_date = DateTime() - 1
        self.assertFalse(self.timeslot.isRegistrationNotYetOpen())
        self.assertTrue(self.timeslot.isRegistrationOpen())

    def test_label_formatting(self):
        self.timeslot.effective_date = DateTime(2027, 3, 1, 8, 0)
        self.timeslot.expiration_date = DateTime(2027, 3, 15, 14, 30)
        self.assertEqual(self.timeslot.getRegistrationEffectiveLabel(), "01.03.2027 08:00")
        self.assertEqual(self.timeslot.getRegistrationExpiresLabel(), "15.03.2027 14:30")


class RegistrationWindowRenderingTest(unittest.TestCase):

    layer = MBARDE_SIGNUPS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.portal_types = self.portal.portal_types
        self.sheet = api.content.create(
            container=self.portal,
            type="UTSignupSheet",
            id="sheet1",
            contactInfo="",
            allowSignupForExternals=True,
        )
        day_id = self.portal_types.constructContent("UTDay", self.sheet, "d1", title="Day 1")
        self.day = self.sheet[day_id]
        self.day.date = date.today() + timedelta(days=1)
        ts_id = self.portal_types.constructContent(
            "UTTimeslot",
            self.day,
            "t1",
            title="T1",
            startTime=time(10, 0),
            endTime=time(12, 0),
            maxCapacity=5,
        )
        self.timeslot = self.day[ts_id]

    def _render(self):
        return self.sheet.restrictedTraverse("@@view")()

    def test_no_dates_set_shows_plain_selection(self):
        html = self._render()
        self.assertIn('name="slotSelection"', html)
        self.assertNotIn("Signup opens on", html)
        self.assertNotIn("Signup open until", html)
        self.assertNotIn("expired", html)

    def test_future_expires_shows_hint_and_stays_selectable(self):
        self.timeslot.expiration_date = DateTime(2027, 3, 15, 14, 30)
        html = self._render()
        self.assertIn('name="slotSelection"', html)
        self.assertIn("Signup open until", html)
        self.assertIn("15.03.2027 14:30", html)

    def test_past_expires_shows_expired_and_hides_selection(self):
        self.timeslot.expiration_date = DateTime() - 1
        html = self._render()
        self.assertNotIn('name="slotSelection"', html)
        self.assertIn("expired", html)

    def test_future_effective_blocks_selection_and_shows_opens_on(self):
        self.timeslot.effective_date = DateTime(2027, 3, 1, 8, 0)
        html = self._render()
        self.assertNotIn('name="slotSelection"', html)
        self.assertIn("Signup opens on", html)
        self.assertIn("01.03.2027 08:00", html)


class RegistrationWindowBackendEnforcementTest(unittest.TestCase):
    """The template hides the form/inputs outside the registration window,
    but that alone doesn't stop a request posted directly to
    @@submit-user-selection - verify UTDay.getTimeSlot()'s server-side
    check independently of the UI.
    """

    layer = MBARDE_SIGNUPS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.portal_types = self.portal.portal_types
        self.sheet = api.content.create(
            container=self.portal,
            type="UTSignupSheet",
            id="sheet1",
            contactInfo="",
            allowSignupForExternals=True,
            enableEmailVerificationForExternals=False,
        )
        day_id = self.portal_types.constructContent("UTDay", self.sheet, "d1", title="Day 1")
        self.day = self.sheet[day_id]
        self.day.date = date.today() + timedelta(days=1)
        ts_id = self.portal_types.constructContent(
            "UTTimeslot",
            self.day,
            "t1",
            title="T1",
            startTime=time(10, 0),
            endTime=time(12, 0),
            maxCapacity=5,
        )
        self.timeslot = self.day[ts_id]

    def _submit(self, email="jane@example.org"):
        self.request.form.update(
            {
                "inputPrename": "Jane",
                "inputSurname": "Doe",
                "inputEmail": email,
                "slotSelection": self.timeslot.getIDLabel(),
            }
        )
        view = self.sheet.unrestrictedTraverse("@@submit-user-selection")
        return view()

    def test_submission_accepted_within_window(self):
        self.timeslot.reindexObject()
        self._submit()
        self.assertIn("jane-example-org", self.timeslot.objectIds())

    def test_submission_rejected_when_expired(self):
        self.timeslot.expiration_date = DateTime() - 1
        self.timeslot.reindexObject()
        html = self._submit()
        self.assertNotIn("jane-example-org", self.timeslot.objectIds())
        self.assertIn("unable to register", html.lower())

    def test_submission_rejected_when_not_yet_open(self):
        self.timeslot.effective_date = DateTime() + 1
        self.timeslot.reindexObject()
        html = self._submit()
        self.assertNotIn("jane-example-org", self.timeslot.objectIds())
        self.assertIn("unable to register", html.lower())
