# -*- coding: utf-8 -*-
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from mbarde.signups.testing import MBARDE_SIGNUPS_INTEGRATION_TESTING  # noqa
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID

import unittest


class PersonViewConsentTest(unittest.TestCase):

    layer = MBARDE_SIGNUPS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        pt = self.portal.portal_types
        sheet = api.content.create(
            container=self.portal, type="UTSignupSheet", id="sheet1", contactInfo=""
        )
        day = sheet[pt.constructContent("UTDay", sheet, "d1", title="Day 1")]
        day.date = date.today() + timedelta(days=1)
        slot = day[
            pt.constructContent(
                "UTTimeslot",
                day,
                "t1",
                title="Slot 1",
                startTime=time(10, 0),
                endTime=time(12, 0),
                maxCapacity=5,
            )
        ]
        pt.constructContent(
            "UTPerson",
            slot,
            "jane-example-org",
            title="Jane",
            email="jane@example.org",
            prename="Jane",
            surname="Doe",
        )
        self.person = slot["jane-example-org"]

    def _render(self):
        return self.person.unrestrictedTraverse("@@view")()

    def test_no_consent_rows_without_consent(self):
        html = self._render()
        self.assertNotIn("Consent to data usage declaration given at", html)
        self.assertNotIn("Data usage declaration text (at time of consent)", html)

    def test_consent_rows_displayed(self):
        self.person.dataUsageConsentGivenAt = datetime(2026, 9, 21, 14, 30)
        self.person.dataUsageDeclarationTextSnapshot = "<p>We store your <b>data</b>.</p>"
        html = self._render()
        self.assertIn("Consent to data usage declaration given at", html)
        self.assertIn("Data usage declaration text (at time of consent)", html)
        self.assertIn("Sep 21, 2026 02:30 PM", html)
        self.assertIn("<p>We store your <b>data</b>.</p>", html)
