# -*- coding: utf-8 -*-
"""GitHub issue #32, case B.1: reducing a timeslot's capacity below the
number of people already signed up must first warn the manager and
require confirmation, then move the excess (most recently signed-up
first) to the waiting list - only when the slot still allows one.
"""

from datetime import date
from datetime import time
from datetime import timedelta
from DateTime import DateTime
from mbarde.signups.testing import MBARDE_SIGNUPS_INTEGRATION_TESTING  # noqa
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from zope.i18n import translate

import unittest


class CapacityReductionWarningTest(unittest.TestCase):

    layer = MBARDE_SIGNUPS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

        self.sheet = api.content.create(
            container=self.portal, type="UTSignupSheet", id="sheet1", contactInfo=""
        )
        self.day = api.content.create(
            container=self.sheet, type="UTDay", id="d1", date=date.today() + timedelta(days=1)
        )
        self.timeslot = api.content.create(
            container=self.day,
            type="UTTimeslot",
            id="t1",
            startTime=time(10, 0),
            endTime=time(12, 0),
            maxCapacity=5,
            allowWaitingList=True,
        )

    def _signUp(self, personId, createdDelta=0):
        person = api.content.create(
            container=self.timeslot,
            type="UTPerson",
            id=personId,
            email=personId + "@example.org",
            prename="P",
            surname=personId,
        )
        api.content.transition(obj=person, transition="signup")
        person.creation_date = DateTime() + createdDelta
        person.reindexObject()
        return person

    def _submitEdit(self, maxCapacity=None, allowWaitingList=None, confirm=False):
        view = self.timeslot.unrestrictedTraverse("@@edit")
        # render once to get the current, correctly-formatted widget
        # values for the fields this particular test isn't changing
        view.update()
        widgets = view.form_instance.widgets
        formData = {widget.name: widget.value for widget in widgets.values()}

        formData["form.widgets.maxCapacity"] = str(
            maxCapacity if maxCapacity is not None else self.timeslot.maxCapacity
        )

        # Note: ":list" is a *ZPublisher* marshalling directive that only
        # applies to the literal query string/POST body - it tells
        # ZPublisher to collect "foo:list" into request.form["foo"] as a
        # list. Since this test sets request.form directly (bypassing
        # ZPublisher), that marshalling never happens - so the plain
        # field name must be set to an already-marshalled list directly.
        effectiveAllowWaitingList = (
            allowWaitingList if allowWaitingList is not None else self.timeslot.allowWaitingList
        )
        formData.pop("form.widgets.allowWaitingList-empty-marker", None)
        if effectiveAllowWaitingList:
            formData["form.widgets.allowWaitingList"] = ["selected"]
        else:
            formData.pop("form.widgets.allowWaitingList", None)
            formData["form.widgets.allowWaitingList-empty-marker"] = "1"

        formData.pop("form.widgets.confirmReduceCapacity-empty-marker", None)
        if confirm:
            formData["form.widgets.confirmReduceCapacity"] = ["selected"]
        else:
            formData.pop("form.widgets.confirmReduceCapacity", None)
            formData["form.widgets.confirmReduceCapacity-empty-marker"] = "1"

        formData["form.buttons.save"] = "Save"

        self.request.form.update(formData)
        freshView = self.timeslot.unrestrictedTraverse("@@edit")
        freshView()
        return freshView.form_instance

    def test_reducing_capacity_without_confirmation_does_not_apply_and_warns(self):
        self._signUp("a", -2)
        self._signUp("b", -1)

        form = self._submitEdit(maxCapacity=1, confirm=False)

        self.assertEqual(self.timeslot.maxCapacity, 5, "capacity must not have been changed yet")
        status = translate(form.status, context=self.request)
        self.assertIn("1", status)  # new capacity
        self.assertIn("2", status)  # how many would be affected
        self.assertEqual(api.content.get_state(self.timeslot["a"]), "signedup")
        self.assertEqual(api.content.get_state(self.timeslot["b"]), "signedup")

    def test_confirmed_reduction_moves_newest_signed_up_to_waiting(self):
        older = self._signUp("older", -2)
        newer = self._signUp("newer", -1)

        self._submitEdit(maxCapacity=1, confirm=True)

        self.assertEqual(self.timeslot.maxCapacity, 1)
        self.assertEqual(api.content.get_state(older), "signedup")
        self.assertEqual(api.content.get_state(newer), "waiting")

    def test_confirmed_reduction_moves_exactly_the_excess(self):
        a = self._signUp("a", -4)
        b = self._signUp("b", -3)
        c = self._signUp("c", -2)
        d = self._signUp("d", -1)

        self._submitEdit(maxCapacity=2, confirm=True)

        self.assertEqual(api.content.get_state(a), "signedup")
        self.assertEqual(api.content.get_state(b), "signedup")
        self.assertEqual(api.content.get_state(c), "waiting")
        self.assertEqual(api.content.get_state(d), "waiting")

    def test_reduction_within_capacity_needs_no_confirmation(self):
        self._signUp("a")
        self._signUp("b")

        self._submitEdit(maxCapacity=2, confirm=False)

        self.assertEqual(self.timeslot.maxCapacity, 2)
        self.assertEqual(api.content.get_state(self.timeslot["a"]), "signedup")
        self.assertEqual(api.content.get_state(self.timeslot["b"]), "signedup")

    def test_increasing_capacity_needs_no_confirmation_and_still_promotes_waiting(self):
        self._signUp("a")
        waiting = api.content.create(
            container=self.timeslot,
            type="UTPerson",
            id="waiting",
            email="waiting@example.org",
            prename="W",
            surname="Aiting",
        )
        api.content.transition(obj=waiting, transition="putOnWaitingList")

        self._submitEdit(maxCapacity=2, confirm=False)

        self.assertEqual(self.timeslot.maxCapacity, 2)
        self.assertEqual(api.content.get_state(waiting), "signedup")

    def test_reducing_capacity_without_waiting_list_is_not_touched_here(self):
        # case B.2 (sign off instead, when no waiting list is allowed)
        # is a separate change - for now this combination must behave
        # exactly as it always has: the edit goes through, nobody moves
        self._signUp("a", -2)
        self._signUp("b", -1)

        self._submitEdit(maxCapacity=1, allowWaitingList=False, confirm=False)

        self.assertEqual(self.timeslot.maxCapacity, 1)
        self.assertEqual(api.content.get_state(self.timeslot["a"]), "signedup")
        self.assertEqual(api.content.get_state(self.timeslot["b"]), "signedup")
