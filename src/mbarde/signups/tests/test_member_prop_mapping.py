# -*- coding: utf-8 -*-
from mbarde.signups.testing import MBARDE_SIGNUPS_INTEGRATION_TESTING  # noqa
from mbarde.signups.utils import getEmailOfPloneUser
from mbarde.signups.utils import getPrenameOfPloneUser
from mbarde.signups.utils import getSurnameOfPloneUser
from plone import api
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.registry.interfaces import IRegistry
from zope.component import getUtility

import unittest


class MemberPropertyMappingSettingsTest(unittest.TestCase):

    layer = MBARDE_SIGNUPS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.registry = getUtility(IRegistry)

    def test_settings_registered_with_expected_defaults(self):
        # email pre-fill/matching keeps working out of the box, prename and
        # surname are opt-in since Plone has no standard property for them
        self.assertEqual(self.registry["mbarde.signups.member_property_email"], "email")
        self.assertEqual(self.registry["mbarde.signups.member_property_prename"], "")
        self.assertEqual(self.registry["mbarde.signups.member_property_surname"], "")


class MemberPropertyResolutionTest(unittest.TestCase):
    """`getEmailOfPloneUser`/`getPrenameOfPloneUser`/`getSurnameOfPloneUser`
    just take a Plone user object, so these are exercised directly against
    a member - no need for an actual logged-in request here.

    Note: vanilla Plone has no standard "prename"/"surname" member
    properties (only a combined "fullname"), so `location`/`home_page`
    stand in for whatever real property a site's member schema extension
    (e.g. via a PAS plugin) would provide.
    """

    layer = MBARDE_SIGNUPS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.member = api.user.create(
            email="member@example.org",
            username="jdoe",
            password="secret1234",
            properties={"location": "Jane", "home_page": "Doe"},
        )
        self.user = self.member.getUser()
        self.registry = getUtility(IRegistry)

    def _setMapping(self, prenameProperty="", surnameProperty="", emailProperty="email"):
        self.registry["mbarde.signups.member_property_prename"] = prenameProperty
        self.registry["mbarde.signups.member_property_surname"] = surnameProperty
        self.registry["mbarde.signups.member_property_email"] = emailProperty

    def test_email_resolved_by_default(self):
        self.assertEqual(getEmailOfPloneUser(self.user), "member@example.org")

    def test_prename_and_surname_empty_until_mapped(self):
        self.assertEqual(getPrenameOfPloneUser(self.user), "")
        self.assertEqual(getSurnameOfPloneUser(self.user), "")

    def test_prename_and_surname_resolved_once_mapped(self):
        self._setMapping(prenameProperty="location", surnameProperty="home_page")
        self.assertEqual(getPrenameOfPloneUser(self.user), "Jane")
        self.assertEqual(getSurnameOfPloneUser(self.user), "Doe")

    def test_unmapped_email_property_falls_back_to_empty(self):
        self._setMapping(emailProperty="")
        self.assertEqual(getEmailOfPloneUser(self.user), "")

    def test_email_as_login_name_ignores_property_mapping(self):
        self.registry["plone.use_email_as_login"] = True
        self._setMapping(emailProperty="")
        # with use_email_as_login on, a member registered without an
        # explicit username logs in with (and is identified by) their email
        member = api.user.create(email="other@example.org", password="secret1234")
        self.assertEqual(getEmailOfPloneUser(member.getUser()), "other@example.org")


class SignupSheetViewPrefillTest(unittest.TestCase):

    layer = MBARDE_SIGNUPS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        api.user.create(
            email="member@example.org",
            username="jdoe",
            password="secret1234",
            properties={"location": "Jane", "home_page": "Doe"},
        )
        registry = getUtility(IRegistry)
        registry["mbarde.signups.member_property_prename"] = "location"
        registry["mbarde.signups.member_property_surname"] = "home_page"
        portal_types = self.portal.portal_types
        sheet_id = portal_types.constructContent(
            "UTSignupSheet",
            self.portal,
            "anmeldung",
            title="Anmeldung",
        )
        self.sheet = self.portal[sheet_id]

    def tearDown(self):
        logout()
        login(self.portal, TEST_USER_NAME)

    def test_fields_prefilled_for_logged_in_user(self):
        logout()
        login(self.portal, "jdoe")
        # the view's own permission requirements aren't the point of this
        # test, so bypass them rather than granting jdoe extra roles/state
        view = self.sheet.unrestrictedTraverse("@@view")
        self.assertEqual(view.getCurrentUserPrename(), "Jane")
        self.assertEqual(view.getCurrentUserSurname(), "Doe")
        self.assertEqual(view.getCurrentUserEmail(), "member@example.org")

    def test_fields_empty_for_anonymous(self):
        logout()
        view = self.sheet.unrestrictedTraverse("@@view")
        self.assertEqual(view.getCurrentUserPrename(), "")
        self.assertEqual(view.getCurrentUserSurname(), "")
        self.assertEqual(view.getCurrentUserEmail(), "")
