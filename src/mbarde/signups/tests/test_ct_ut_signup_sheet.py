# -*- coding: utf-8 -*-
from mbarde.signups.content.ut_signup_sheet import IUTSignupSheet  # NOQA E501
from mbarde.signups.testing import MBARDE_SIGNUPS_INTEGRATION_TESTING  # noqa
from plone import api
from plone.api.exc import InvalidParameterError
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.dexterity.interfaces import IDexterityFTI
from zope.component import createObject
from zope.component import queryUtility

import unittest

try:
    from plone.dexterity.schema import portalTypeToSchemaName
except ImportError:
    # Plone < 5
    from plone.dexterity.utils import portalTypeToSchemaName  # noqa: F401


class UTSignupSheetIntegrationTest(unittest.TestCase):

    layer = MBARDE_SIGNUPS_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

    def test_ct_ut_signup_sheet_schema(self):
        fti = queryUtility(IDexterityFTI, name="UTSignupSheet")
        schema = fti.lookupSchema()
        self.assertEqual(IUTSignupSheet, schema)

    def test_ct_ut_signup_sheet_fti(self):
        fti = queryUtility(IDexterityFTI, name="UTSignupSheet")
        self.assertTrue(fti)

    def test_ct_ut_signup_sheet_factory(self):
        fti = queryUtility(IDexterityFTI, name="UTSignupSheet")
        factory = fti.factory
        obj = createObject(factory)

        self.assertTrue(
            IUTSignupSheet.providedBy(obj),
            "IUTSignupSheet not provided by {0}!".format(
                obj,
            ),
        )

    def test_ct_ut_signup_sheet_adding(self):
        setRoles(self.portal, TEST_USER_ID, ["Contributor"])
        obj = api.content.create(
            container=self.portal,
            type="UTSignupSheet",
            id="ut_signup_sheet",
        )

        self.assertTrue(
            IUTSignupSheet.providedBy(obj),
            "IUTSignupSheet not provided by {0}!".format(
                obj.id,
            ),
        )

    def test_ct_ut_signup_sheet_globally_addable(self):
        setRoles(self.portal, TEST_USER_ID, ["Contributor"])
        fti = queryUtility(IDexterityFTI, name="UTSignupSheet")
        self.assertTrue(fti.global_allow, "{0} is not globally addable!".format(fti.id))

    def test_ct_ut_signup_sheet_filter_content_type_true(self):
        setRoles(self.portal, TEST_USER_ID, ["Contributor"])
        fti = queryUtility(IDexterityFTI, name="UTSignupSheet")
        portal_types = self.portal.portal_types
        parent_id = portal_types.constructContent(
            fti.id,
            self.portal,
            "ut_signup_sheet_id",
            title="UTSignupSheet container",
        )
        self.parent = self.portal[parent_id]
        with self.assertRaises(InvalidParameterError):
            api.content.create(
                container=self.parent,
                type="Document",
                title="My Content",
            )
