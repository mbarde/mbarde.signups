# -*- coding: utf-8 -*-
"""GitHub issue #32, case B: reducing a timeslot's capacity below the
number of people already signed up is rejected - managers have to move
the excess to the waiting list or sign them off manually first.
"""

from datetime import date
from datetime import time
from datetime import timedelta
from mbarde.signups.content.ut_timeslot import IUTTimeslot
from mbarde.signups.testing import MBARDE_SIGNUPS_INTEGRATION_TESTING  # noqa
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from z3c.form.interfaces import IErrorViewSnippet
from zope.i18n import translate
from zope.interface import Invalid

import unittest


class _Data(object):
    """Mimics the z3c.form Data object invariants are validated against"""

    def __init__(self, context, **kwargs):
        self.__context__ = context
        self.__dict__.update(kwargs)


class CapacityReductionTest(unittest.TestCase):

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

    def _signUp(self, personId):
        person = api.content.create(
            container=self.timeslot,
            type="UTPerson",
            id=personId,
            email=personId + "@example.org",
            prename="P",
            surname=personId,
        )
        api.content.transition(obj=person, transition="signup")
        return person

    def _validate(self, context, maxCapacity, allowWaitingList=True):
        data = _Data(context, maxCapacity=maxCapacity, allowWaitingList=allowWaitingList)
        errors = []
        try:
            IUTTimeslot.validateInvariants(data, errors)
        except Invalid:
            pass
        return [translate(e.args[0], context=self.request) for e in errors]

    def test_reducing_below_signups_is_invalid(self):
        for personId in ("a", "b", "c"):
            self._signUp(personId)

        with self.assertRaises(Invalid):
            IUTTimeslot.validateInvariants(
                _Data(self.timeslot, maxCapacity=1, allowWaitingList=True)
            )

        messages = self._validate(self.timeslot, 1)
        self.assertEqual(len(messages), 1)
        self.assertIn("reduce the capacity to 1", messages[0])
        self.assertIn("already 3 signups", messages[0])
        self.assertIn("move 2 people to the waiting list", messages[0])

    def test_message_without_waiting_list_only_mentions_signoff(self):
        self._signUp("a")
        self._signUp("b")

        messages = self._validate(self.timeslot, 1, allowWaitingList=False)
        self.assertEqual(len(messages), 1)
        self.assertIn("sign off 1 people", messages[0])
        self.assertNotIn("waiting list", messages[0])

    def test_reducing_to_exactly_the_number_of_signups_is_valid(self):
        self._signUp("a")
        self._signUp("b")
        self.assertEqual(self._validate(self.timeslot, 2), [])

    def test_only_signedup_persons_count(self):
        self._signUp("a")
        # sign off first - otherwise freeing the spot would promote "waiting"
        signedOff = self._signUp("off")
        api.content.transition(obj=signedOff, transition="signoff")
        waiting = api.content.create(
            container=self.timeslot,
            type="UTPerson",
            id="waiting",
            email="waiting@example.org",
            prename="W",
            surname="Aiting",
        )
        api.content.transition(obj=waiting, transition="putOnWaitingList")

        self.assertEqual(self._validate(self.timeslot, 1), [])

    def test_add_form_context_is_ignored(self):
        # in the add form the invariant's context is the parent UTDay
        self.assertEqual(self._validate(self.day, 1), [])

    def test_manager_can_move_signedup_person_to_waiting_list_then_reduce(self):
        self._signUp("a")
        b = self._signUp("b")
        self.assertNotEqual(self._validate(self.timeslot, 1), [])

        api.content.transition(obj=b, transition="putOnWaitingList")

        self.assertEqual(api.content.get_state(b), "waiting")
        self.assertEqual(self._validate(self.timeslot, 1), [])

    def test_increasing_capacity_is_valid(self):
        self._signUp("a")
        self._signUp("b")
        self.assertEqual(self._validate(self.timeslot, 10), [])

    def test_missing_capacity_is_left_to_field_validation(self):
        # maxCapacity is required - an empty value is reported by the
        # field itself, the invariant must not crash on it
        self._signUp("a")
        self.assertEqual(self._validate(self.timeslot, None), [])

    def _submitEdit(self, maxCapacity, allowWaitingList=True):
        view = self.timeslot.unrestrictedTraverse("@@edit")
        # render once to get the current widget values for unchanged fields
        view.update()
        formData = {w.name: w.value for w in view.form_instance.widgets.values()}
        formData["form.widgets.maxCapacity"] = str(maxCapacity)
        # request.form is set directly (bypassing ZPublisher), so the
        # checkbox value has to be an already-marshalled list
        formData.pop("form.widgets.allowWaitingList-empty-marker", None)
        if allowWaitingList:
            formData["form.widgets.allowWaitingList"] = ["selected"]
        else:
            formData.pop("form.widgets.allowWaitingList", None)
            formData["form.widgets.allowWaitingList-empty-marker"] = "1"
        formData["form.buttons.save"] = "Save"
        self.request.form.update(formData)

        freshView = self.timeslot.unrestrictedTraverse("@@edit")
        freshView()
        return freshView.form_instance

    def _formErrorMessages(self, form):
        return [
            translate(e.message, context=self.request)
            for e in form.widgets.errors
            if IErrorViewSnippet.providedBy(e)
        ]

    def test_edit_form_rejects_reduction_below_signups(self):
        self._signUp("a")
        self._signUp("b")

        form = self._submitEdit(1)

        self.assertEqual(self.timeslot.maxCapacity, 5)
        messages = self._formErrorMessages(form)
        self.assertEqual(len(messages), 1)
        self.assertIn("reduce the capacity to 1", messages[0])
        self.assertIn("move 1 people to the waiting list", messages[0])
        self.assertEqual(api.content.get_state(self.timeslot["a"]), "signedup")
        self.assertEqual(api.content.get_state(self.timeslot["b"]), "signedup")

    def test_edit_form_uses_submitted_allow_waiting_list_value(self):
        # waiting list is switched off in the same edit - the message must
        # not suggest moving people to a waiting list that won't exist
        self._signUp("a")
        self._signUp("b")

        form = self._submitEdit(1, allowWaitingList=False)

        self.assertEqual(self.timeslot.maxCapacity, 5)
        self.assertTrue(self.timeslot.allowWaitingList)
        messages = self._formErrorMessages(form)
        self.assertEqual(len(messages), 1)
        self.assertIn("sign off 1 people", messages[0])
        self.assertNotIn("waiting list", messages[0])

    def test_edit_form_accepts_reduction_down_to_signups(self):
        self._signUp("a")
        self._signUp("b")

        form = self._submitEdit(2)

        self.assertEqual(self._formErrorMessages(form), [])
        self.assertEqual(self.timeslot.maxCapacity, 2)
        self.assertEqual(api.content.get_state(self.timeslot["a"]), "signedup")
        self.assertEqual(api.content.get_state(self.timeslot["b"]), "signedup")
