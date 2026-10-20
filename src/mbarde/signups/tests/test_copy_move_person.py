# -*- coding: utf-8 -*-
from datetime import date
from datetime import time
from datetime import timedelta
from mbarde.signups.testing import MBARDE_SIGNUPS_INTEGRATION_TESTING  # noqa
from OFS.CopySupport import CopyError
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.protect.authenticator import createToken
from Products.statusmessages.interfaces import IStatusMessage

import unittest


class CopyPersonTest(unittest.TestCase):

    layer = MBARDE_SIGNUPS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        sheet = api.content.create(
            container=self.portal, type="UTSignupSheet", id="sheet1", contactInfo=""
        )
        day = api.content.create(
            container=sheet, type="UTDay", id="d1", date=date.today() + timedelta(days=1)
        )
        self.slotA = self._createSlot(day, "a")
        self.slotB = self._createSlot(day, "b")
        self.person = api.content.create(
            container=self.slotA,
            type="UTPerson",
            id="jane",
            email="jane@example.org",
            prename="Jane",
            surname="Doe",
        )

    def _createSlot(self, day, slotId):
        return api.content.create(
            container=day,
            type="UTTimeslot",
            id=slotId,
            startTime=time(10, 0),
            endTime=time(12, 0),
            maxCapacity=5,
        )

    def test_person_is_not_copyable(self):
        self.assertFalse(self.person.cb_isCopyable())
        with self.assertRaises(CopyError):
            self.slotA.manage_copyObjects([self.person.getId()])

    def test_api_copy_is_refused(self):
        with self.assertRaises(CopyError):
            api.content.copy(source=self.person, target=self.slotB)
        self.assertEqual(list(self.slotB.objectIds()), [])

    def test_toolbar_copy_shows_message(self):
        self.request.form["_authenticator"] = createToken()
        view = self.person.restrictedTraverse("@@object_copy")
        view()

        messages = [m.message for m in IStatusMessage(self.request).show()]
        self.assertTrue(any("not copyable" in str(m) for m in messages), messages)
        self.assertNotIn("__cp", self.request.response.cookies)

    def test_person_is_still_moveable(self):
        # renames (autoSetID/deferRename) go through the same check
        self.assertTrue(self.person.cb_isMoveable())

    def test_rename_still_works(self):
        api.content.rename(obj=self.person, new_id="jane-renamed")
        self.assertIn("jane-renamed", self.slotA)


class CopyContainerDropsPersonsTest(unittest.TestCase):
    """Copying a sheet / day / slot copies its structure, but not the
    people signed up for it"""

    layer = MBARDE_SIGNUPS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.sheet = api.content.create(
            container=self.portal, type="UTSignupSheet", id="sheet1", contactInfo=""
        )
        self.day = api.content.create(
            container=self.sheet, type="UTDay", id="d1", date=date.today() + timedelta(days=1)
        )
        self.slot = api.content.create(
            container=self.day,
            type="UTTimeslot",
            id="t1",
            startTime=time(10, 0),
            endTime=time(12, 0),
            maxCapacity=5,
            allowWaitingList=True,
        )
        for personId, transition in (("a", "signup"), ("b", "putOnWaitingList"), ("c", None)):
            person = api.content.create(
                container=self.slot,
                type="UTPerson",
                id=personId,
                email=personId + "@example.org",
                prename="P",
                surname=personId,
            )
            if transition:
                api.content.transition(obj=person, transition=transition)

    def _personBrains(self, container):
        catalog = api.portal.get_tool("portal_catalog")
        return catalog.unrestrictedSearchResults(
            portal_type="UTPerson", path="/".join(container.getPhysicalPath())
        )

    def _assertOriginalUntouched(self):
        self.assertEqual(sorted(self.slot.objectIds()), ["a", "b", "c"])
        self.assertEqual(api.content.get_state(self.slot["a"]), "signedup")
        self.assertEqual(len(self._personBrains(self.slot)), 3)

    def test_copied_sheet_has_structure_but_no_persons(self):
        copy = api.content.copy(source=self.sheet, target=self.portal, id="sheet2")

        copiedSlots = [slot for day in copy.objectValues() for slot in day.objectValues()]
        self.assertEqual(len(copiedSlots), 1)
        self.assertEqual(copiedSlots[0].maxCapacity, 5)
        self.assertEqual(list(copiedSlots[0].objectIds()), [])
        self.assertEqual(len(self._personBrains(copy)), 0)
        self._assertOriginalUntouched()

    def test_copied_day_has_no_persons(self):
        copy = api.content.copy(source=self.day, target=self.sheet, id="d2")

        self.assertEqual([list(slot.objectIds()) for slot in copy.objectValues()], [[]])
        self.assertEqual(len(self._personBrains(copy)), 0)
        self._assertOriginalUntouched()

    def test_copied_slot_has_no_persons(self):
        # via the clipboard, like the toolbar / folder contents do
        clipboard = self.day.manage_copyObjects([self.slot.getId()])
        result = self.day.manage_pasteObjects(clipboard)
        copy = self.day[result[0]["new_id"]]

        self.assertEqual(list(copy.objectIds()), [])
        self.assertEqual(copy.getNumberOfSignedUpPersons(), 0)
        self.assertEqual(copy.getNumberOfAvailableSlots(), 5)
        self._assertOriginalUntouched()

    def test_copied_slot_accepts_new_persons(self):
        copy = api.content.copy(source=self.slot, target=self.day, id="t2")

        person = api.content.create(
            container=copy,
            type="UTPerson",
            id="a",
            email="a@example.org",
            prename="P",
            surname="a",
        )
        api.content.transition(obj=person, transition="signup")
        self.assertEqual(list(copy.objectIds()), ["a"])
        self.assertEqual(copy.getNumberOfSignedUpPersons(), 1)
