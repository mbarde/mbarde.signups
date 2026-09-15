# -*- coding: utf-8 -*-
"""Tests for the data usage declaration (GDPR consent) fields on
IUTSignupSheet and the consent evidence they cause to be recorded on
UTPerson.
"""

from datetime import date
from datetime import time
from datetime import timedelta
from mbarde.signups.testing import MBARDE_SIGNUPS_INTEGRATION_TESTING  # noqa
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.textfield.value import RichTextValue

import unittest


class DataUsageDeclarationTest(unittest.TestCase):

    layer = MBARDE_SIGNUPS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

    def _createSheet(self, declarationText=None, consentRequired=True):
        declaration = (
            RichTextValue(raw=declarationText, mimeType="text/plain", outputMimeType="text/html")
            if declarationText
            else None
        )
        sheet = api.content.create(
            container=self.portal,
            type="UTSignupSheet",
            id="sheet1",
            contactInfo="",
            signupsRequireConfirmation=False,
            enableEmailVerificationForExternals=False,
            allowSignupForExternals=True,
            dataUsageDeclaration=declaration,
            dataUsageDeclarationConsentRequired=consentRequired,
        )
        portal_types = self.portal.portal_types
        day_id = portal_types.constructContent("UTDay", sheet, "d1", title="Day 1")
        day = sheet[day_id]
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
        return sheet, day[ts_id]

    def _submit(self, sheet, timeslot, agree):
        form = {
            "inputPrename": "Jane",
            "inputSurname": "Doe",
            "inputEmail": "jane@example.org",
            "slotSelection": timeslot.getIDLabel(),
        }
        if agree:
            form["agreeDataUsage"] = "1"
        self.request.form.update(form)
        view = sheet.unrestrictedTraverse("@@submit-user-selection")
        view()

    def test_signup_rejected_without_consent_when_required(self):
        sheet, timeslot = self._createSheet("We use your data for X.", consentRequired=True)
        self._submit(sheet, timeslot, agree=False)
        self.assertNotIn("jane-example-org", timeslot.objectIds())

    def test_signup_accepted_with_consent_when_required(self):
        sheet, timeslot = self._createSheet("We use your data for X.", consentRequired=True)
        self._submit(sheet, timeslot, agree=True)
        person = timeslot["jane-example-org"]
        self.assertIsNotNone(person.dataUsageConsentGivenAt)
        self.assertEqual(person.dataUsageDeclarationTextSnapshot, sheet.dataUsageDeclaration.output)

    def test_signup_accepted_without_consent_when_not_required(self):
        sheet, timeslot = self._createSheet("We use your data for X.", consentRequired=False)
        self._submit(sheet, timeslot, agree=False)
        person = timeslot["jane-example-org"]
        self.assertIsNone(person.dataUsageConsentGivenAt)
        self.assertIsNone(person.dataUsageDeclarationTextSnapshot)

    def test_no_consent_evidence_recorded_without_a_declaration(self):
        # consentRequired defaults to True, but with no declaration text
        # there is nothing to consent to
        sheet, timeslot = self._createSheet(declarationText=None, consentRequired=True)
        self._submit(sheet, timeslot, agree=False)
        person = timeslot["jane-example-org"]
        self.assertIsNone(person.dataUsageConsentGivenAt)
        self.assertIsNone(person.dataUsageDeclarationTextSnapshot)

    def test_snapshot_is_unaffected_by_later_edits_to_the_declaration(self):
        sheet, timeslot = self._createSheet("Original wording.", consentRequired=True)
        self._submit(sheet, timeslot, agree=True)
        person = timeslot["jane-example-org"]
        originalSnapshot = person.dataUsageDeclarationTextSnapshot

        sheet.dataUsageDeclaration = RichTextValue(
            raw="Edited wording.", mimeType="text/plain", outputMimeType="text/html"
        )

        self.assertEqual(person.dataUsageDeclarationTextSnapshot, originalSnapshot)
        self.assertIn("Original wording", person.dataUsageDeclarationTextSnapshot)
