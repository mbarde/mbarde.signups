# -*- coding: utf-8 -*-
from datetime import date
from mbarde.signups.content.ut_signup_sheet import IUTSignupSheet  # NOQA E501
from mbarde.signups.testing import MBARDE_SIGNUPS_INTEGRATION_TESTING  # noqa
from plone import api
from plone.api.exc import InvalidParameterError
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.dexterity.interfaces import IDexterityFTI
from zope.component import createObject
from zope.component import queryUtility
from zope.i18n import translate
from zope.i18nmessageid import Message
from zope.interface import Invalid

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

    def test_lockPersonalData_rejected_when_externals_allowed(self):
        obj = api.content.create(
            container=self.portal,
            type="UTSignupSheet",
            id="ut_signup_sheet",
            allowSignupForExternals=True,
            lockPersonalData=True,
        )
        with self.assertRaises(Invalid):
            IUTSignupSheet.validateInvariants(obj)

    def test_lockPersonalData_allowed_when_externals_disabled(self):
        obj = api.content.create(
            container=self.portal,
            type="UTSignupSheet",
            id="ut_signup_sheet",
            allowSignupForExternals=False,
            lockPersonalData=True,
        )
        # should not raise
        IUTSignupSheet.validateInvariants(obj)

    def test_getDaysGroupedByMonth_month_name_is_translatable(self):
        # a real translation (e.g. into German) needs a compiled .mo
        # catalog, which - unlike the site's own runtime, where
        # zope_i18n_compile_mo_files handles it - isn't built as part of
        # running the tests (.mo files are gitignored build artifacts, see
        # README). So rather than asserting an actual translated string
        # (which would only pass locally if a stale compiled catalog
        # happens to already be lying around), assert the message is
        # correctly *shaped* to be translated: this is what guards against
        # a regression back to strftime()'s untranslatable raw string,
        # which is what this method used to return.
        sheet = api.content.create(
            container=self.portal,
            type="UTSignupSheet",
            id="ut_signup_sheet",
            contactInfo="",
        )
        portal_types = self.portal.portal_types
        day_id = portal_types.constructContent("UTDay", sheet, "d1", title="Day 1")
        sheet[day_id].date = date(2027, 3, 15)

        _days, keys, monthNames = sheet.getDaysGroupedByMonth()
        monthName = monthNames[keys[0]]

        self.assertIsInstance(monthName, Message)
        self.assertEqual(monthName.domain, "mbarde.signups")
        self.assertEqual(monthName, "March")
        # falls back to the msgid itself when no catalog/translation is found
        self.assertEqual(translate(monthName, target_language="en"), "March")
