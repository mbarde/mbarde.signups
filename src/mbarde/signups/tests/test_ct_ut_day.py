# -*- coding: utf-8 -*-
from datetime import date
from mbarde.signups.content.ut_day import IUTDay  # NOQA E501
from mbarde.signups.testing import MBARDE_SIGNUPS_INTEGRATION_TESTING  # noqa
from plone import api
from plone.api.exc import InvalidParameterError
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.dexterity.interfaces import IDexterityFTI
from plone.dexterity.utils import createContentInContainer
from zope.component import createObject
from zope.component import queryUtility

import unittest

try:
    from plone.dexterity.schema import portalTypeToSchemaName
except ImportError:
    # Plone < 5
    from plone.dexterity.utils import portalTypeToSchemaName  # noqa: F401


class UTDayIntegrationTest(unittest.TestCase):

    layer = MBARDE_SIGNUPS_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        portal_types = self.portal.portal_types
        parent_id = portal_types.constructContent(
            "UTSignupSheet",
            self.portal,
            "ut_day",
            title="Parent container",
        )
        self.parent = self.portal[parent_id]

    def test_ct_ut_day_schema(self):
        fti = queryUtility(IDexterityFTI, name="UTDay")
        schema = fti.lookupSchema()
        self.assertEqual(IUTDay, schema)

    def test_ct_ut_day_fti(self):
        fti = queryUtility(IDexterityFTI, name="UTDay")
        self.assertTrue(fti)

    def test_ct_ut_day_factory(self):
        fti = queryUtility(IDexterityFTI, name="UTDay")
        factory = fti.factory
        obj = createObject(factory)

        self.assertTrue(
            IUTDay.providedBy(obj),
            "IUTDay not provided by {0}!".format(
                obj,
            ),
        )

    def test_ct_ut_day_adding(self):
        setRoles(self.portal, TEST_USER_ID, ["Contributor"])
        today = date.today()
        # use plone.dexterity's own content-creation helper (rather than
        # api.content.create()/portal_types.constructContent()) since it
        # already knows how to safely fetch the object after autoSetID
        # renames it while it is still being added (see ut_day.autoSetID)
        obj = createContentInContainer(
            self.parent,
            "UTDay",
            id="ut_day",
            date=today,
        )

        self.assertTrue(
            IUTDay.providedBy(obj),
            "IUTDay not provided by {0}!".format(
                obj.id,
            ),
        )

        self.assertEqual(obj.getTimeSlots(), [])

    def test_ct_ut_day_globally_not_addable(self):
        setRoles(self.portal, TEST_USER_ID, ["Contributor"])
        fti = queryUtility(IDexterityFTI, name="UTDay")
        self.assertFalse(fti.global_allow, "{0} is globally addable!".format(fti.id))

    def test_ct_ut_day_filter_content_type_true(self):
        setRoles(self.portal, TEST_USER_ID, ["Contributor"])
        fti = queryUtility(IDexterityFTI, name="UTDay")
        portal_types = self.portal.portal_types
        parent_id = portal_types.constructContent(
            fti.id,
            self.portal,
            "ut_day_id",
            title="UTDay container",
        )
        self.parent = self.portal[parent_id]
        with self.assertRaises(InvalidParameterError):
            api.content.create(
                container=self.parent,
                type="Document",
                title="My Content",
            )
