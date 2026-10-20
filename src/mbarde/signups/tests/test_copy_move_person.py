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
