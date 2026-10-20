# -*- coding: utf-8 -*-
"""Disabling a timeslot's waiting list while people are still on it is
rejected - managers have to sign them up or sign them off manually first.
"""

from datetime import date
from datetime import time
from datetime import timedelta
from mbarde.signups.content.ut_timeslot import IUTTimeslot
from mbarde.signups.testing import MBARDE_SIGNUPS_INTEGRATION_TESTING  # noqa
from mbarde.signups.tests.test_capacity_reduction import _Data
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from z3c.form.interfaces import IErrorViewSnippet
from zope.i18n import translate
from zope.interface import Invalid

import unittest


class DisableWaitingListTest(unittest.TestCase):

    layer = MBARDE_SIGNUPS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

        sheet = api.content.create(
            container=self.portal, type="UTSignupSheet", id="sheet1", contactInfo=""
        )
        self.day = api.content.create(
            container=sheet, type="UTDay", id="d1", date=date.today() + timedelta(days=1)
        )
        self.timeslot = api.content.create(
            container=self.day,
            type="UTTimeslot",
            id="t1",
            startTime=time(10, 0),
            endTime=time(12, 0),
            maxCapacity=1,
            allowWaitingList=True,
        )

    def _createPerson(self, personId, transition):
        person = api.content.create(
            container=self.timeslot,
            type="UTPerson",
            id=personId,
            email=personId + "@example.org",
            prename="P",
            surname=personId,
        )
        api.content.transition(obj=person, transition=transition)
        return person

    def _validate(self, context, allowWaitingList):
        data = _Data(
            context, maxCapacity=self.timeslot.maxCapacity, allowWaitingList=allowWaitingList
        )
        errors = []
        try:
            IUTTimeslot.validateInvariants(data, errors)
        except Invalid:
            pass
        return [translate(e.args[0], context=self.request) for e in errors]

    def test_disabling_with_people_waiting_is_invalid(self):
        self._createPerson("a", "signup")
        self._createPerson("b", "putOnWaitingList")
        self._createPerson("c", "putOnWaitingList")

        messages = self._validate(self.timeslot, allowWaitingList=False)

        self.assertEqual(len(messages), 1)
        self.assertIn("can't disable the waiting list", messages[0])
        self.assertIn("still 2 people on it", messages[0])

    def test_disabling_with_empty_waiting_list_is_valid(self):
        self._createPerson("a", "signup")
        self.assertEqual(self._validate(self.timeslot, allowWaitingList=False), [])

    def test_only_waiting_persons_count(self):
        self._createPerson("a", "signup")
        self._createPerson("off", "signoff")
        self.assertEqual(self._validate(self.timeslot, allowWaitingList=False), [])

    def test_keeping_waiting_list_enabled_is_valid(self):
        self._createPerson("a", "signup")
        self._createPerson("b", "putOnWaitingList")
        self.assertEqual(self._validate(self.timeslot, allowWaitingList=True), [])

    def test_already_disabled_waiting_list_does_not_block_editing(self):
        # e.g. people put on the waiting list before the transition guards
        # existed - editing other fields of such a slot must still work
        self._createPerson("a", "signup")
        self._createPerson("b", "putOnWaitingList")
        self.timeslot.allowWaitingList = False

        self.assertEqual(self._validate(self.timeslot, allowWaitingList=False), [])

    def test_add_form_context_is_ignored(self):
        # in the add form the invariant's context is the parent UTDay
        self.assertEqual(self._validate(self.day, allowWaitingList=False), [])

    def test_can_disable_after_resolving_waiting_list(self):
        b = self._createPerson("b", "putOnWaitingList")
        self.assertNotEqual(self._validate(self.timeslot, allowWaitingList=False), [])

        api.content.transition(obj=b, transition="signoff")

        self.assertEqual(self._validate(self.timeslot, allowWaitingList=False), [])

    def test_edit_form_rejects_disabling_with_people_waiting(self):
        self._createPerson("a", "signup")
        self._createPerson("b", "putOnWaitingList")

        view = self.timeslot.unrestrictedTraverse("@@edit")
        view.update()
        formData = {w.name: w.value for w in view.form_instance.widgets.values()}
        # request.form is set directly (bypassing ZPublisher), so the
        # unchecked checkbox is expressed via its empty-marker only
        formData.pop("form.widgets.allowWaitingList", None)
        formData["form.widgets.allowWaitingList-empty-marker"] = "1"
        formData["form.buttons.save"] = "Save"
        self.request.form.update(formData)

        freshView = self.timeslot.unrestrictedTraverse("@@edit")
        freshView()

        self.assertTrue(self.timeslot.allowWaitingList)
        messages = [
            translate(e.message, context=self.request)
            for e in freshView.form_instance.widgets.errors
            if IErrorViewSnippet.providedBy(e)
        ]
        self.assertEqual(len(messages), 1)
        self.assertIn("still 1 people on it", messages[0])
