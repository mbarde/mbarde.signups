# -*- coding: utf-8 -*-
"""Confirms signups in one UTSignupSheet can never be confused with
signups in a *different* UTSignupSheet for the same person/email, even
when both sheets are siblings under the same parent folder.

UTPerson ids are derived deterministically from the email address
(emailToPersonId), so the same email produces the *same* id string in
every sheet - the only thing preventing a mix-up is that every lookup
that matters (countSlotsByEmail, isUserSignedUpForThisSlot,
getSlotsOfCurrentUser, ...) is scoped by path (explicitly, or via
`api.content.find(context=self, ...)`, which plone.api implements by
restricting the catalog query's path to `self`'s own physical path) to
the specific sheet/day/timeslot in question, never queried portal-wide.

getCurrentUserSignUpState is the one exception worth calling out
separately: it doesn't use the catalog at all, just plain
hasattr/getattr on the timeslot object. Since Zope's Acquisition makes
attribute lookups fall through to parent containers, this is at least
*structurally* capable of picking up an unrelated object from
somewhere above the timeslot in the containment hierarchy - this test
confirms that in practice, with two sibling sheets, it still resolves
independently per sheet (each sheet's own Day/Timeslot nesting means
a person's id is never a direct child of anything the two sheets
actually share).
"""

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

import unittest


class CrossSheetIsolationTest(unittest.TestCase):

    layer = MBARDE_SIGNUPS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

        self.sheetA, self.slotA = self._buildSheet("sheetA", "slotA")
        self.sheetB, self.slotB = self._buildSheet("sheetB", "slotB")

        self.email = "jane@example.org"
        api.user.create(email=self.email, username="janedoe", password="secret1234")

    def tearDown(self):
        logout()
        login(self.portal, TEST_USER_NAME)

    def _buildSheet(self, sheetId, slotId):
        sheet = api.content.create(
            container=self.portal,
            type="UTSignupSheet",
            id=sheetId,
            allowSignupForExternals=True,
            allowSignupForMultipleSlots=False,
            signupsRequireConfirmation=False,
            contactInfo="",
        )
        portal_types = self.portal.portal_types
        day = api.content.create(
            container=sheet, type="UTDay", id="d1", date=date.today() + timedelta(days=1)
        )
        timeslotId = portal_types.constructContent(
            "UTTimeslot",
            day,
            slotId,
            title="T",
            startTime=time(10, 0),
            endTime=time(12, 0),
            maxCapacity=5,
        )
        return sheet, day[timeslotId]

    def _submit(self, sheet, slot):
        self.request.form.update(
            {
                "inputPrename": "Jane",
                "inputSurname": "Doe",
                "inputEmail": self.email,
                "slotSelection": slot.getIDLabel(),
            }
        )
        view = sheet.unrestrictedTraverse("@@submit-user-selection")
        view()
        return view

    def test_signing_up_in_one_sheet_does_not_block_or_leak_into_another(self):
        viewA = self._submit(self.sheetA, self.slotA)
        self.assertEqual(viewA.results[0]["status"], "signedup")

        # the same email, in a *different* sheet that also disallows
        # multiple signups - must not be blocked by sheet A's record
        viewB = self._submit(self.sheetB, self.slotB)
        self.assertEqual(viewB.results[0]["status"], "signedup")

        personA = self.slotA["jane-example-org"]
        personB = self.slotB["jane-example-org"]
        self.assertNotEqual(personA.getPhysicalPath(), personB.getPhysicalPath())

    def test_countSlotsByEmail_is_scoped_per_sheet(self):
        self._submit(self.sheetA, self.slotA)
        self._submit(self.sheetB, self.slotB)

        self.assertEqual(self.sheetA.countSlotsByEmail(self.email), 1)
        self.assertEqual(self.sheetB.countSlotsByEmail(self.email), 1)

    def test_isUserSignedUpForThisSlot_is_scoped_per_sheet(self):
        self._submit(self.sheetA, self.slotA)

        self.assertTrue(self.slotA.isUserSignedUpForThisSlot(self.email))
        self.assertFalse(self.slotB.isUserSignedUpForThisSlot(self.email))

    def test_getCurrentUserSignUpState_does_not_leak_across_sheets(self):
        # this one matters specifically because it's a plain
        # hasattr/getattr lookup, not a catalog query - see module
        # docstring
        self._submit(self.sheetA, self.slotA)
        personA = self.slotA["jane-example-org"]

        logout()
        login(self.portal, "janedoe")
        try:
            self.assertEqual(self.slotA.getCurrentUserSignUpState(), "signedup")
            self.assertFalse(self.slotB.getCurrentUserSignUpState())

            api.content.transition(obj=personA, transition="signoff")
            self.assertEqual(self.slotA.getCurrentUserSignUpState(), "signedoff")
            # sheet B was never touched and must still report "no signup"
            self.assertFalse(self.slotB.getCurrentUserSignUpState())
        finally:
            logout()

    def test_getSlotsOfCurrentUser_only_shows_that_sheets_own_slots(self):
        self._submit(self.sheetA, self.slotA)
        self._submit(self.sheetB, self.slotB)

        login(self.portal, "janedoe")
        try:
            self.assertEqual(
                [slot.getId() for slot in self.sheetA.getSlotsOfCurrentUser()], ["slotA"]
            )
            self.assertEqual(
                [slot.getId() for slot in self.sheetB.getSlotsOfCurrentUser()], ["slotB"]
            )
        finally:
            logout()
