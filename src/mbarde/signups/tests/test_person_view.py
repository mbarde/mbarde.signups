# -*- coding: utf-8 -*-
from datetime import date
from datetime import time
from datetime import timedelta
from mbarde.signups.testing import MBARDE_SIGNUPS_INTEGRATION_TESTING  # noqa
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from urllib.parse import parse_qs
from urllib.parse import urlparse
from zExceptions import Forbidden

import re
import unittest


class PersonViewTest(unittest.TestCase):

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
        self.timeslot = api.content.create(
            container=day,
            type="UTTimeslot",
            id="t1",
            startTime=time(10, 0),
            endTime=time(12, 0),
            maxCapacity=1,
        )
        self.person = self._createPerson("jane")

    def _createPerson(self, personId):
        # new persons start in the "unconfirmed" state
        return api.content.create(
            container=self.timeslot,
            type="UTPerson",
            id=personId,
            email=personId + "@example.org",
            prename="P",
            surname=personId,
        )

    def _actionsSection(self):
        """only the button container - the toolbar's state menu elsewhere
        on the page links to content_status_modify as well"""
        html = self.person.unrestrictedTraverse("@@view")()
        match = re.search(r'<div[^>]*id="person-actions"[^>]*>(.*?)</div>', html, re.DOTALL)
        return match.group(1) if match else None

    def test_buttons_shown_for_unconfirmed_person(self):
        self.timeslot.allowWaitingList = True
        self.assertEqual(api.content.get_state(self.person), "unconfirmed")

        section = self._actionsSection()

        self.assertIsNotNone(section)
        self.assertIn("content_status_modify?workflow_action=signup", section)
        self.assertIn("content_status_modify?workflow_action=putOnWaitingList", section)
        self.assertIn("_authenticator=", section)
        self.assertNotIn("already full", section)

    def test_no_waiting_list_button_when_slot_has_no_waiting_list(self):
        self.timeslot.allowWaitingList = False

        section = self._actionsSection()

        self.assertIn("workflow_action=signup", section)
        self.assertNotIn("putOnWaitingList", section)

    def test_buttons_not_shown_in_other_states(self):
        self.timeslot.allowWaitingList = True
        api.content.transition(obj=self.person, transition="signup")
        self.assertIsNone(self._actionsSection())

        api.content.transition(obj=self.person, transition="putOnWaitingList")
        self.assertIsNone(self._actionsSection())

        api.content.transition(obj=self.person, transition="signoff")
        self.assertIsNone(self._actionsSection())

    def test_confirm_disabled_when_slot_is_full_and_waiting_list_suggested(self):
        self.timeslot.allowWaitingList = True
        other = self._createPerson("other")
        api.content.transition(obj=other, transition="signup")

        section = self._actionsSection()

        self.assertIn("disabled", section)
        self.assertNotIn("workflow_action=signup", section)
        self.assertIn("workflow_action=putOnWaitingList", section)
        self.assertIn("already full", section)
        self.assertIn("waiting list", section)

    def test_confirm_disabled_when_slot_is_full_without_waiting_list(self):
        self.timeslot.allowWaitingList = False
        other = self._createPerson("other")
        api.content.transition(obj=other, transition="signup")

        section = self._actionsSection()

        self.assertIn("disabled", section)
        self.assertNotIn("content_status_modify", section)
        self.assertIn("already full", section)
        self.assertNotIn("waiting list", section)

    def test_link_target_confirms_the_signup(self):
        view = self.person.unrestrictedTraverse("@@view")
        url = urlparse(view.getConfirmSignupUrl())
        params = parse_qs(url.query)
        self.assertEqual(
            url.path, urlparse(self.person.absolute_url()).path + "/content_status_modify"
        )
        self.assertEqual(params["workflow_action"], ["signup"])

        # without the CSRF token from the link the request is refused
        with self.assertRaises(Forbidden):
            self.person.restrictedTraverse("content_status_modify")(workflow_action="signup")
        self.assertEqual(api.content.get_state(self.person), "unconfirmed")

        self.request.form["_authenticator"] = params["_authenticator"][0]
        self.person.restrictedTraverse("content_status_modify")(workflow_action="signup")

        self.assertEqual(api.content.get_state(self.person), "signedup")

    def test_waiting_list_link_target_puts_person_on_waiting_list(self):
        self.timeslot.allowWaitingList = True
        view = self.person.unrestrictedTraverse("@@view")
        params = parse_qs(urlparse(view.getPutOnWaitingListUrl()).query)
        self.assertEqual(params["workflow_action"], ["putOnWaitingList"])

        self.request.form["_authenticator"] = params["_authenticator"][0]
        self.person.restrictedTraverse("content_status_modify")(workflow_action="putOnWaitingList")

        self.assertEqual(api.content.get_state(self.person), "waiting")

    def _stateRowClass(self):
        html = self.person.unrestrictedTraverse("@@view")()
        match = re.search(r'<tr[^>]*id="person-state"[^>]*>', html)
        classMatch = re.search(r'class="([^"]*)"', match.group(0))
        return classMatch.group(1) if classMatch else ""

    def test_state_row_is_colored_like_the_summary(self):
        # same colors as view_summary.pt / the timeslot view's person lists
        self.timeslot.allowWaitingList = True
        self.assertEqual(self._stateRowClass(), "table-warning")

        api.content.transition(obj=self.person, transition="signup")
        self.assertEqual(self._stateRowClass(), "table-success")

        api.content.transition(obj=self.person, transition="putOnWaitingList")
        self.assertEqual(self._stateRowClass(), "table-info")

        api.content.transition(obj=self.person, transition="signoff")
        self.assertEqual(self._stateRowClass(), "table-danger")
