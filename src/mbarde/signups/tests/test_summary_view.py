# -*- coding: utf-8 -*-
from datetime import date
from datetime import time
from datetime import timedelta
from mbarde.signups.testing import MBARDE_SIGNUPS_INTEGRATION_TESTING  # noqa
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID

import unittest


class ManagerSummaryViewTest(unittest.TestCase):

    layer = MBARDE_SIGNUPS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.sheet = api.content.create(
            container=self.portal, type="UTSignupSheet", id="sheet1", contactInfo=""
        )
        day = api.content.create(
            container=self.sheet, type="UTDay", id="d1", date=date.today() + timedelta(days=1)
        )
        for slotId, startHour in (("t1", 10), ("t2", 11)):
            api.content.create(
                container=day,
                type="UTTimeslot",
                id=slotId,
                startTime=time(startHour, 0),
                endTime=time(startHour + 1, 0),
                maxCapacity=5,
            )

    def test_accordion_items_open_independently(self):
        # without data-bs-parent, Bootstrap doesn't collapse the other
        # items when one is opened - managers can keep several slots open
        html = self.sheet.unrestrictedTraverse("@@manager-summary")()

        self.assertIn('id="slots-accordion"', html)
        self.assertEqual(html.count("accordion-collapse"), 2)
        self.assertNotIn("data-bs-parent", html)

    def test_open_items_are_not_highlighted(self):
        # Bootstrap's .accordion-button:not(.collapsed) colors open items via
        # these variables - the summary sets them to the closed-item values
        html = self.sheet.unrestrictedTraverse("@@manager-summary")()

        self.assertIn("--bs-accordion-active-bg: var(--bs-accordion-btn-bg);", html)
        self.assertIn("--bs-accordion-active-color: var(--bs-accordion-btn-color);", html)
        self.assertIn("--bs-accordion-btn-active-icon: var(--bs-accordion-btn-icon);", html)
