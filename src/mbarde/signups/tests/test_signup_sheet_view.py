# -*- coding: utf-8 -*-
from mbarde.signups.testing import MBARDE_SIGNUPS_INTEGRATION_TESTING  # noqa
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID

import unittest


class SignupSheetViewEditLinksTest(unittest.TestCase):

    layer = MBARDE_SIGNUPS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.sheet = api.content.create(
            container=self.portal, type="UTSignupSheet", id="sheet1", contactInfo=""
        )

    def _view(self):
        return api.content.get_view(name="view", context=self.sheet, request=self.request)

    def test_global_manager_sees_edit_links(self):
        self.assertTrue(self._view().showEditLinks())

    def test_local_manager_sees_edit_links(self):
        # Manager only on the signup sheet (e.g. via sharing), not globally
        setRoles(self.portal, TEST_USER_ID, ["Member"])
        self.sheet.manage_setLocalRoles(TEST_USER_ID, ["Manager"])
        self.assertTrue(self._view().showEditLinks())

    def test_member_does_not_see_edit_links(self):
        setRoles(self.portal, TEST_USER_ID, ["Member"])
        # creating the sheet made the test user its Owner, which also grants
        # the permission
        self.sheet.manage_delLocalRoles([TEST_USER_ID])
        self.assertFalse(self._view().showEditLinks())
