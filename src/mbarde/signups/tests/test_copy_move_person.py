# -*- coding: utf-8 -*-
from datetime import date
from datetime import time
from datetime import timedelta
from mbarde.signups.testing import MBARDE_SIGNUPS_FUNCTIONAL_TESTING  # noqa
from mbarde.signups.testing import MBARDE_SIGNUPS_INTEGRATION_TESTING  # noqa
from mbarde.signups.transitionguards import MoveNotAllowed
from OFS.CopySupport import CopyError
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.app.testing import TEST_USER_ID
from plone.protect.authenticator import createToken
from plone.testing.zope import Browser
from plone.uuid.interfaces import IUUID
from Products.statusmessages.interfaces import IStatusMessage

import json
import transaction
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


def _createSheetWithTwoSlots(portal):
    sheet = api.content.create(container=portal, type="UTSignupSheet", id="sheet1", contactInfo="")
    day = api.content.create(
        container=sheet, type="UTDay", id="d1", date=date.today() + timedelta(days=1)
    )
    slots = [
        api.content.create(
            container=day,
            type="UTTimeslot",
            id=slotId,
            startTime=time(10, 0),
            endTime=time(12, 0),
            maxCapacity=5,
        )
        for slotId in ("a", "b")
    ]
    person = api.content.create(
        container=slots[0],
        type="UTPerson",
        id="jane",
        email="jane@example.org",
        prename="Jane",
        surname="Doe",
    )
    api.content.transition(obj=person, transition="signup")
    return sheet, day, slots, person


class MovePersonTest(unittest.TestCase):

    layer = MBARDE_SIGNUPS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.sheet, self.day, (self.slotA, self.slotB), self.person = _createSheetWithTwoSlots(
            self.portal
        )

    def test_moving_person_to_other_slot_is_refused(self):
        with self.assertRaises(MoveNotAllowed) as cm:
            api.content.move(source=self.person, target=self.slotB)

        self.assertEqual(cm.exception.message, "error_move_person_to_other_slot")
        self.assertEqual(cm.exception.person, self.person)
        self.assertEqual(list(self.slotA.objectIds()), ["jane"])
        self.assertEqual(list(self.slotB.objectIds()), [])

    def test_moving_whole_slot_to_other_day_keeps_its_persons(self):
        otherDay = api.content.create(
            container=self.sheet, type="UTDay", id="d2", date=date.today() + timedelta(days=2)
        )

        moved = api.content.move(source=self.slotA, target=otherDay)

        self.assertEqual(list(moved.objectIds()), ["jane"])
        self.assertEqual(api.content.get_state(moved["jane"]), "signedup")

    def test_renaming_person_is_allowed(self):
        api.content.rename(obj=self.person, new_id="jane-renamed")
        self.assertEqual(list(self.slotA.objectIds()), ["jane-renamed"])

    def test_deleting_person_is_allowed(self):
        api.content.delete(obj=self.person)
        self.assertEqual(list(self.slotA.objectIds()), [])


class MovePersonThroughUITest(unittest.TestCase):
    """Cut & paste through the toolbar and folder contents: the paste is
    refused and nothing is moved"""

    layer = MBARDE_SIGNUPS_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        _sheet, _day, (slotA, slotB), person = _createSheetWithTwoSlots(self.portal)
        transaction.commit()
        # ids get normalized on commit, so look things up by UID later
        self.slotAUID, self.slotBUID, self.personUID = (
            IUUID(slotA),
            IUUID(slotB),
            IUUID(person),
        )

        self.browser = Browser(self.layer["app"])
        self.browser.handleErrors = True
        self.browser.raiseHttpErrors = False
        self.browser.addHeader(
            "Authorization", "Basic {0}:{1}".format(SITE_OWNER_NAME, SITE_OWNER_PASSWORD)
        )
        with api.env.adopt_user(username=SITE_OWNER_NAME):
            self.token = createToken()

    def _get(self, uid):
        return api.content.get(UID=uid)

    def _cutPerson(self):
        self.browser.open(
            "{0}/object_cut?_authenticator={1}".format(
                self._get(self.personUID).absolute_url(), self.token
            )
        )

    def _assertNotMoved(self):
        transaction.begin()
        person = self._get(self.personUID)
        self.assertEqual(person.aq_parent.UID(), self.slotAUID)
        self.assertEqual(list(self._get(self.slotBUID).objectIds()), [])
        self.assertEqual(api.content.get_state(person), "signedup")

    def test_toolbar_paste_is_refused_with_message(self):
        self._cutPerson()

        self.browser.open(
            "{0}/object_paste?_authenticator={1}".format(
                self._get(self.slotBUID).absolute_url(), self.token
            )
        )

        self.assertEqual(self.browser.headers["Status"], "200 OK")
        self.assertEqual(self.browser.url, self._get(self.personUID).absolute_url())
        self.assertIn("moved to another slot", self.browser.contents)
        self._assertNotMoved()

    def _pasteViaFolderContents(self, headers=()):
        slotB = self._get(self.slotBUID)
        for name, value in headers:
            self.browser.addHeader(name, value)
        self.browser.post(
            "{0}/@@fc-paste".format(slotB.absolute_url()),
            "folder={0}&_authenticator={1}".format(
                "/".join(slotB.getPhysicalPath()[2:]), self.token
            ),
        )

    def _assertFolderContentsAnswer(self):
        # same answer the folder contents actions give themselves, so its
        # JavaScript shows the message (a redirect failed silently there)
        self.assertEqual(self.browser.headers["Status"], "200 OK")
        self.assertTrue(self.browser.headers["Content-Type"].startswith("application/json"))
        answer = json.loads(self.browser.contents)
        self.assertEqual(answer["status"], "warning")
        self.assertIn("moved to another slot", answer["msg"])
        # no status message cookie left over for the next page load
        self.assertNotIn("statusmessages", self.browser.cookies)

    def test_folder_contents_paste_button_is_refused_with_json_message(self):
        # the toolbar's paste button uses jQuery.ajax
        self._cutPerson()
        self._pasteViaFolderContents([("X-Requested-With", "XMLHttpRequest")])

        self._assertFolderContentsAnswer()
        self._assertNotMoved()

    def test_folder_contents_row_paste_is_refused_with_json_message(self):
        # the paste action in a row's menu uses fetch() (no X-Requested-With)
        self._cutPerson()
        self._pasteViaFolderContents()

        self._assertFolderContentsAnswer()
        self._assertNotMoved()
