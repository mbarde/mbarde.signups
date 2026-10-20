# -*- coding: utf-8 -*-
from datetime import date
from datetime import time
from datetime import timedelta
from DateTime import DateTime
from mbarde.signups.testing import MBARDE_SIGNUPS_INTEGRATION_TESTING  # noqa
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID

import re
import unittest


class TimeslotViewPersonGroupsTest(unittest.TestCase):

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
        self.timeslot = api.content.create(
            container=day,
            type="UTTimeslot",
            id="t1",
            startTime=time(10, 0),
            endTime=time(12, 0),
            maxCapacity=5,
            allowWaitingList=True,
        )

    def _createPerson(self, personId, transitions=(), createdDelta=0):
        person = api.content.create(
            container=self.timeslot,
            type="UTPerson",
            id=personId,
            email=personId + "@example.org",
            prename="P",
            surname=personId,
        )
        for transition in transitions:
            api.content.transition(obj=person, transition=transition)
        person.creation_date = DateTime() + createdDelta
        person.reindexObject()
        return person

    def _render(self):
        return self.timeslot.unrestrictedTraverse("@@view")()

    def _section(self, html, state):
        """html from the given group's heading up to the next group heading"""
        match = re.search(
            r'<h3 id="persons-%s">(.*?)(?=<h3 id="persons-|$)' % state, html, re.DOTALL
        )
        return match.group(1) if match else None

    def test_persons_are_listed_in_their_state_group(self):
        # sign off before anyone is waiting, otherwise the freed spot
        # would auto-promote the waiting person
        self._createPerson("signedoff", ["signup", "signoff"])
        self._createPerson("signedup", ["signup"])
        self._createPerson("waiting", ["putOnWaitingList"])
        self._createPerson("unconfirmed")

        html = self._render()

        for state in ("signedup", "waiting", "unconfirmed", "signedoff"):
            section = self._section(html, state)
            self.assertIsNotNone(section, state)
            self.assertIn("(%s)" % state, section)
            for other in {"signedup", "waiting", "unconfirmed", "signedoff"} - {state}:
                self.assertNotIn("(%s)" % other, section)

    def test_groups_appear_in_order(self):
        # sign off before anyone is waiting, otherwise the freed spot
        # would auto-promote the waiting person
        self._createPerson("signedoff", ["signup", "signoff"])
        self._createPerson("signedup", ["signup"])
        self._createPerson("waiting", ["putOnWaitingList"])
        self._createPerson("unconfirmed")

        html = self._render()

        positions = [
            html.index('id="persons-%s"' % state)
            for state in ("signedup", "waiting", "unconfirmed", "signedoff")
        ]
        self.assertEqual(positions, sorted(positions))

    def test_signed_up_badge_shows_capacity(self):
        self._createPerson("a", ["signup"])
        self._createPerson("b", ["signup"])

        self.assertIn("2 / 5", self._section(self._render(), "signedup"))

    def test_waiting_list_is_ordered_by_creation_date(self):
        self._createPerson("newer", ["putOnWaitingList"], createdDelta=-1)
        self._createPerson("older", ["putOnWaitingList"], createdDelta=-2)

        section = self._section(self._render(), "waiting")
        self.assertLess(section.index("(older)"), section.index("(newer)"))

    def test_empty_unconfirmed_and_signedoff_groups_are_hidden(self):
        self._createPerson("a", ["signup"])

        html = self._render()

        self.assertIsNotNone(self._section(html, "signedup"))
        self.assertIsNotNone(self._section(html, "waiting"))
        self.assertIsNone(self._section(html, "unconfirmed"))
        self.assertIsNone(self._section(html, "signedoff"))

    def test_empty_waiting_list_is_hidden_when_not_allowed(self):
        self.timeslot.allowWaitingList = False

        html = self._render()

        self.assertIsNotNone(self._section(html, "signedup"))
        self.assertIsNone(self._section(html, "waiting"))

    def _hint(self):
        html = self._render()
        match = re.search(r'id="free-places-while-waiting"[^>]*>(.*?)</div>', html, re.DOTALL)
        return match.group(1).strip() if match else None

    def test_hint_when_places_free_while_people_are_waiting(self):
        # e.g. a manager moved a signed-up person to the waiting list (which
        # promotes nobody) but didn't reduce the capacity afterwards
        moved = self._createPerson("moved", ["signup"])
        self._createPerson("waiting", ["putOnWaitingList"])
        api.content.transition(obj=moved, transition="putOnWaitingList")

        hint = self._hint()

        self.assertIsNotNone(hint)
        self.assertIn("free places (5)", hint)
        self.assertIn("waiting list (2)", hint)

    def test_no_hint_when_slot_is_full(self):
        self.timeslot.maxCapacity = 1
        self._createPerson("signedup", ["signup"])
        self._createPerson("waiting", ["putOnWaitingList"])

        self.assertIsNone(self._hint())

    def test_no_hint_without_people_waiting(self):
        self._createPerson("signedup", ["signup"])

        self.assertIsNone(self._hint())
