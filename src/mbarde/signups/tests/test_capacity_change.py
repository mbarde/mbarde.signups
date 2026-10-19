# -*- coding: utf-8 -*-
"""GitHub issue #32, case A: increasing a timeslot's capacity while
people are on the waiting list should automatically sign up as many of
them as now fit, oldest-waiting (by creation date) first.
"""

from datetime import date
from datetime import time
from datetime import timedelta
from DateTime import DateTime
from mbarde.signups.testing import MBARDE_SIGNUPS_INTEGRATION_TESTING  # noqa
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from zope.lifecycleevent import modified

import unittest


class PromoteFromWaitingListOnCapacityIncreaseTest(unittest.TestCase):

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
            maxCapacity=1,
            allowWaitingList=True,
        )

    def _createWaitingPerson(self, personId, email, createdDelta):
        person = api.content.create(
            container=self.timeslot,
            type="UTPerson",
            id=personId,
            email=email,
            prename="P",
            surname=personId,
        )
        api.content.transition(obj=person, transition="putOnWaitingList")
        # set a deterministic, distinct creation date rather than
        # relying on real-clock gaps between fast test calls
        person.creation_date = DateTime() + createdDelta
        person.reindexObject()
        return person

    def _editCapacity(self, newCapacity):
        self.timeslot.maxCapacity = newCapacity
        modified(self.timeslot)

    def _fillOriginalCapacity(self):
        # setUp's maxCapacity is 1 - occupy it, so later increasing it
        # actually frees up only the number of *new* slots being tested,
        # rather than also counting slack that was already there
        filler = api.content.create(
            container=self.timeslot,
            type="UTPerson",
            id="filler",
            email="filler@example.org",
            prename="F",
            surname="Iller",
        )
        api.content.transition(obj=filler, transition="signup")
        return filler

    def test_increasing_capacity_promotes_oldest_waiting_person_first(self):
        self._fillOriginalCapacity()
        older = self._createWaitingPerson("older", "older@example.org", -2)
        newer = self._createWaitingPerson("newer", "newer@example.org", -1)

        # touch "older"'s unrelated field *after* creation, to prove the
        # promotion order is based on creation date, not modification
        # date (see _promoteFromWaitingList's docstring in subscribers.py)
        older.surname = "OlderButModifiedLater"
        older.reindexObject()

        self._editCapacity(2)  # frees exactly one new slot

        self.assertEqual(api.content.get_state(older), "signedup")
        self.assertEqual(api.content.get_state(newer), "waiting")

    def test_increasing_capacity_by_more_than_one_promotes_multiple(self):
        first = self._createWaitingPerson("first", "first@example.org", -3)
        second = self._createWaitingPerson("second", "second@example.org", -2)
        third = self._createWaitingPerson("third", "third@example.org", -1)

        self._editCapacity(3)

        self.assertEqual(api.content.get_state(first), "signedup")
        self.assertEqual(api.content.get_state(second), "signedup")
        self.assertEqual(api.content.get_state(third), "signedup")

    def test_increasing_capacity_only_promotes_as_many_as_now_fit(self):
        self._fillOriginalCapacity()
        first = self._createWaitingPerson("first", "first@example.org", -2)
        second = self._createWaitingPerson("second", "second@example.org", -1)

        self._editCapacity(2)  # only one new slot opens, not two

        self.assertEqual(api.content.get_state(first), "signedup")
        self.assertEqual(api.content.get_state(second), "waiting")

    def test_disabled_auto_move_up_does_not_promote(self):
        self.sheet.enableAutoMovingUpFromWaitingList = False
        waiting = self._createWaitingPerson("waiting", "waiting@example.org", -1)

        self._editCapacity(5)

        self.assertEqual(api.content.get_state(waiting), "waiting")

    def test_editing_an_unrelated_field_with_no_free_capacity_does_not_promote(self):
        signedUp = api.content.create(
            container=self.timeslot,
            type="UTPerson",
            id="signedup",
            email="signedup@example.org",
            prename="S",
            surname="U",
        )
        api.content.transition(obj=signedUp, transition="signup")
        waiting = self._createWaitingPerson("waiting", "waiting@example.org", -1)

        self.timeslot.name = "Renamed"
        modified(self.timeslot)

        self.assertEqual(api.content.get_state(waiting), "waiting")

    def test_adding_a_child_person_alone_does_not_double_promote(self):
        # adding/removing a UTPerson fires IContainerModifiedEvent on the
        # timeslot too (a subtype of IObjectModifiedEvent) - make sure
        # that alone doesn't also run the capacity-increase promotion
        # logic a second time on top of whatever already handled it
        waiting = self._createWaitingPerson("waiting", "waiting@example.org", -1)

        # capacity 1, nobody signed up yet - plenty of room, but the
        # person being added is the trigger itself, not an edit
        self.assertEqual(api.content.get_state(waiting), "waiting")


class AttemptToFillEmptySpotOrderingTest(unittest.TestCase):
    """attemptToFillEmptySpot (triggered by a signoff, not by editing the
    timeslot) shares _promoteFromWaitingList with the case-A subscriber
    above - confirm its promotion order is also by creation date, not
    modification date.
    """

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
            maxCapacity=1,
            allowWaitingList=True,
        )

    def test_signoff_promotes_the_longest_waiting_person_by_creation_date(self):
        signedUp = api.content.create(
            container=self.timeslot,
            type="UTPerson",
            id="signedup",
            email="signedup@example.org",
            prename="S",
            surname="U",
        )
        api.content.transition(obj=signedUp, transition="signup")

        older = api.content.create(
            container=self.timeslot,
            type="UTPerson",
            id="older",
            email="older@example.org",
            prename="O",
            surname="lder",
        )
        api.content.transition(obj=older, transition="putOnWaitingList")
        older.creation_date = DateTime() - 2
        older.reindexObject()

        newer = api.content.create(
            container=self.timeslot,
            type="UTPerson",
            id="newer",
            email="newer@example.org",
            prename="N",
            surname="ewer",
        )
        api.content.transition(obj=newer, transition="putOnWaitingList")
        newer.creation_date = DateTime() - 1
        newer.reindexObject()

        # touch "older"'s unrelated field *after* creation - the
        # pre-fix "Date" sort would have reordered the queue here
        older.surname = "OlderButModifiedLater"
        older.reindexObject()

        api.content.transition(obj=signedUp, transition="signoff")

        self.assertEqual(api.content.get_state(older), "signedup")
        self.assertEqual(api.content.get_state(newer), "waiting")
