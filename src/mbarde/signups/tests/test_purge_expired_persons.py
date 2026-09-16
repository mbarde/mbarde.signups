# -*- coding: utf-8 -*-
"""Tests for the GDPR auto-deletion (storage limitation) purge logic - see
IUTSignupSheet.autoDeletePersonalDataAfterDays and
mbarde.signups.utils.purgeExpiredPersonalData.
"""

from datetime import date
from datetime import time
from datetime import timedelta
from mbarde.signups.testing import MBARDE_SIGNUPS_INTEGRATION_TESTING  # noqa
from mbarde.signups.utils import purgeExpiredPersonalData
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID

import unittest


class PurgeExpiredPersonalDataTest(unittest.TestCase):

    layer = MBARDE_SIGNUPS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.portal_types = self.portal.portal_types

    def _createSheetWithDay(self, sheetId, daysAgo, autoDeleteAfterDays):
        sheet = api.content.create(
            container=self.portal,
            type="UTSignupSheet",
            id=sheetId,
            contactInfo="",
            autoDeletePersonalDataAfterDays=autoDeleteAfterDays,
        )
        day_id = self.portal_types.constructContent("UTDay", sheet, "d1", title="Day 1")
        day = sheet[day_id]
        day.date = date.today() - timedelta(days=daysAgo)
        ts_id = self.portal_types.constructContent(
            "UTTimeslot",
            day,
            "t1",
            title="T1",
            startTime=time(10, 0),
            endTime=time(12, 0),
            maxCapacity=5,
        )
        timeslot = day[ts_id]
        self.portal_types.constructContent(
            "UTPerson",
            timeslot,
            "jane-example-org",
            title="Jane Doe",
            email="jane@example.org",
            prename="Jane",
            surname="Doe",
        )
        return sheet, day, timeslot

    def test_disabled_by_default_leaves_everything_alone(self):
        sheet, day, timeslot = self._createSheetWithDay(
            "sheet1", daysAgo=100, autoDeleteAfterDays=None
        )
        results = purgeExpiredPersonalData(dryRun=False)
        self.assertEqual(results, [])
        self.assertIn("jane-example-org", timeslot.objectIds())

    def test_day_not_yet_past_threshold_is_kept(self):
        sheet, day, timeslot = self._createSheetWithDay("sheet1", daysAgo=5, autoDeleteAfterDays=10)
        results = purgeExpiredPersonalData(dryRun=False)
        self.assertEqual(results, [])
        self.assertIn("jane-example-org", timeslot.objectIds())

    def test_day_past_threshold_is_deleted(self):
        sheet, day, timeslot = self._createSheetWithDay(
            "sheet1", daysAgo=15, autoDeleteAfterDays=10
        )
        results = purgeExpiredPersonalData(dryRun=False)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["count"], 1)
        self.assertEqual(results[0]["day"], "d1")
        self.assertNotIn("jane-example-org", timeslot.objectIds())

    def test_zero_days_deletes_as_soon_as_day_has_passed(self):
        sheet, day, timeslot = self._createSheetWithDay("sheet1", daysAgo=1, autoDeleteAfterDays=0)
        results = purgeExpiredPersonalData(dryRun=False)
        self.assertEqual(len(results), 1)
        self.assertNotIn("jane-example-org", timeslot.objectIds())

    def test_dry_run_reports_but_does_not_delete(self):
        sheet, day, timeslot = self._createSheetWithDay(
            "sheet1", daysAgo=15, autoDeleteAfterDays=10
        )
        results = purgeExpiredPersonalData(dryRun=True)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["count"], 1)
        # nothing actually deleted
        self.assertIn("jane-example-org", timeslot.objectIds())

    def test_multiple_sheets_only_configured_ones_are_processed(self):
        _, _, expiredTimeslot = self._createSheetWithDay(
            "sheet-expiring", daysAgo=15, autoDeleteAfterDays=10
        )
        _, _, untouchedTimeslot = self._createSheetWithDay(
            "sheet-disabled", daysAgo=100, autoDeleteAfterDays=None
        )
        results = purgeExpiredPersonalData(dryRun=False)
        self.assertEqual(len(results), 1)
        self.assertNotIn("jane-example-org", expiredTimeslot.objectIds())
        self.assertIn("jane-example-org", untouchedTimeslot.objectIds())
