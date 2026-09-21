# -*- coding: utf-8 -*-
from mbarde.signups.content.ut_signup_sheet import _mailDefaultFactory
from mbarde.signups.testing import MBARDE_SIGNUPS_INTEGRATION_TESTING  # noqa
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID

import unittest


class MailDefaultFactoryTest(unittest.TestCase):

    layer = MBARDE_SIGNUPS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

    def test_factory_with_non_adaptable_context(self):
        # e.g. TypeSchemaContext when editing fields in dexterity types control panel
        factory = _mailDefaultFactory("Signup successful")
        self.assertEqual(str(factory(object())), "Signup successful")

    def test_type_fields_editor_renders(self):
        request = self.layer["request"]
        types = self.portal.restrictedTraverse("@@dexterity-types")
        typeContext = types.publishTraverse(request, "UTSignupSheet")
        html = typeContext.restrictedTraverse("@@fields")()
        self.assertIn("contactInfo", html)
