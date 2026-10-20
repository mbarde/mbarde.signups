# -*- coding: utf-8 -*-
from datetime import date
from datetime import time
from datetime import timedelta
from mbarde.signups.testing import MBARDE_SIGNUPS_FUNCTIONAL_TESTING  # noqa
from mbarde.signups.testing import MBARDE_SIGNUPS_INTEGRATION_TESTING  # noqa
from mbarde.signups.transitionguards import TransitionNotAllowed
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.app.testing import TEST_USER_ID
from plone.protect.authenticator import createToken
from plone.testing.zope import Browser
from plone.uuid.interfaces import IUUID
from urllib.error import HTTPError

import transaction
import unittest


def _createStack(portal, maxCapacity=1, allowWaitingList=False):
    sheet = api.content.create(container=portal, type="UTSignupSheet", id="sheet1", contactInfo="")
    day = api.content.create(
        container=sheet, type="UTDay", id="d1", date=date.today() + timedelta(days=1)
    )
    return api.content.create(
        container=day,
        type="UTTimeslot",
        id="t1",
        startTime=time(10, 0),
        endTime=time(12, 0),
        maxCapacity=maxCapacity,
        allowWaitingList=allowWaitingList,
    )


def _createPerson(timeSlot, personId, transitions=()):
    person = api.content.create(
        container=timeSlot,
        type="UTPerson",
        id=personId,
        email=personId + "@example.org",
        prename="P",
        surname=personId,
    )
    for transition in transitions:
        api.content.transition(obj=person, transition=transition)
    return person


class TransitionGuardsTest(unittest.TestCase):

    layer = MBARDE_SIGNUPS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.timeslot = _createStack(self.portal)

    def _fillTimeslot(self):
        _createPerson(self.timeslot, "filler", ["signup"])

    def assertRefused(self, person, transition, messageId):
        stateBefore = api.content.get_state(person)
        with self.assertRaises(TransitionNotAllowed) as cm:
            api.content.transition(obj=person, transition=transition)
        self.assertEqual(cm.exception.message, messageId)
        self.assertEqual(cm.exception.person, person)
        self.assertEqual(api.content.get_state(person), stateBefore)

    # signup

    def test_signup_refused_when_slot_is_full(self):
        self._fillTimeslot()
        person = _createPerson(self.timeslot, "jane")

        self.assertRefused(person, "signup", "error_transition_signup_slot_full")
        self.assertEqual(self.timeslot.getNumberOfSignedUpPersons(), 1)

    def test_signup_refused_from_every_source_state_when_full(self):
        self.timeslot.allowWaitingList = True
        signedOff = _createPerson(self.timeslot, "off", ["signoff"])
        waiting = _createPerson(self.timeslot, "waiting", ["putOnWaitingList"])
        self._fillTimeslot()

        self.assertRefused(signedOff, "signup", "error_transition_signup_slot_full")
        self.assertRefused(waiting, "signup", "error_transition_signup_slot_full")

    def test_signup_allowed_while_slot_has_room(self):
        person = _createPerson(self.timeslot, "jane")
        api.content.transition(obj=person, transition="signup")
        self.assertEqual(api.content.get_state(person), "signedup")

    # putOnWaitingList

    def test_put_on_waiting_list_refused_without_waiting_list(self):
        signedUp = _createPerson(self.timeslot, "signedup", ["signup"])
        unconfirmed = _createPerson(self.timeslot, "unconfirmed")
        signedOff = _createPerson(self.timeslot, "off", ["signoff"])

        for person in (signedUp, unconfirmed, signedOff):
            self.assertRefused(
                person, "putOnWaitingList", "error_transition_waiting_list_not_allowed"
            )

    def test_put_on_waiting_list_allowed_with_waiting_list(self):
        self.timeslot.allowWaitingList = True
        person = _createPerson(self.timeslot, "jane")
        api.content.transition(obj=person, transition="putOnWaitingList")
        self.assertEqual(api.content.get_state(person), "waiting")

    # reactivate

    def test_reactivate_refused_when_full_without_waiting_list(self):
        person = _createPerson(self.timeslot, "jane", ["signoff"])
        self._fillTimeslot()

        self.assertRefused(person, "reactivate", "error_transition_reactivate_slot_full")

    def test_reactivate_allowed_when_full_with_waiting_list(self):
        self.timeslot.allowWaitingList = True
        person = _createPerson(self.timeslot, "jane", ["signoff"])
        self._fillTimeslot()

        api.content.transition(obj=person, transition="reactivate")
        self.assertEqual(api.content.get_state(person), "unconfirmed")

    def test_reactivate_allowed_while_slot_has_room(self):
        person = _createPerson(self.timeslot, "jane", ["signoff"])

        api.content.transition(obj=person, transition="reactivate")
        self.assertEqual(api.content.get_state(person), "unconfirmed")

    # unguarded

    def test_signoff_is_never_refused(self):
        self._fillTimeslot()
        person = _createPerson(self.timeslot, "jane")
        api.content.transition(obj=person, transition="signoff")
        self.assertEqual(api.content.get_state(person), "signedoff")


class TransitionNotAllowedViewTest(unittest.TestCase):
    """A refused transition triggered through the browser (toolbar state
    menu / person view buttons) shows the reason instead of an error page"""

    layer = MBARDE_SIGNUPS_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.app = self.layer["app"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.timeslot = _createStack(self.portal)
        _createPerson(self.timeslot, "filler", ["signup"])
        self.person = _createPerson(self.timeslot, "jane")
        transaction.commit()
        # ids get normalized on commit, so look the person up by UID later
        self.personUID = IUUID(self.person)

        self.browser = Browser(self.app)
        self.browser.handleErrors = False
        self.browser.addHeader(
            "Authorization", "Basic {0}:{1}".format(SITE_OWNER_NAME, SITE_OWNER_PASSWORD)
        )

    def _person(self):
        return api.content.get(UID=self.personUID)

    def _transitionUrl(self, transition):
        # plone.protect tokens are bound to the user they were created for
        with api.env.adopt_user(username=SITE_OWNER_NAME):
            token = createToken()
        return "{0}/content_status_modify?workflow_action={1}&_authenticator={2}".format(
            self.person.absolute_url(), transition, token
        )

    def test_refused_transition_redirects_back_with_message(self):
        self.browser.handleErrors = True
        try:
            self.browser.open(self._transitionUrl("signup"))
        except HTTPError:
            self.fail("refused transition should not end in an error page")

        self.assertEqual(self.browser.url, self.person.absolute_url())
        self.assertIn("This slot is already full", self.browser.contents)
        transaction.begin()
        self.assertEqual(api.content.get_state(self._person()), "unconfirmed")

    def test_allowed_transition_still_works(self):
        self.browser.open(self._transitionUrl("signoff"))

        transaction.begin()
        self.assertEqual(api.content.get_state(self._person()), "signedoff")
