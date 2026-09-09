# -*- coding: utf-8 -*-
from datetime import date
from mbarde.signups.content.ut_timeslot import IUTTimeslot  # NOQA E501
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


class UTTimeslotIntegrationTest(unittest.TestCase):

    layer = MBARDE_SIGNUPS_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        portal_types = self.portal.portal_types
        parent_id = portal_types.constructContent(
            "UTDay",
            self.portal,
            "ut_timeslot",
            title="Parent container",
        )
        self.parent = self.portal[parent_id]

    def test_ct_ut_timeslot_schema(self):
        fti = queryUtility(IDexterityFTI, name="UTTimeslot")
        schema = fti.lookupSchema()
        self.assertEqual(IUTTimeslot, schema)

    def test_ct_ut_timeslot_fti(self):
        fti = queryUtility(IDexterityFTI, name="UTTimeslot")
        self.assertTrue(fti)

    def test_ct_ut_timeslot_factory(self):
        fti = queryUtility(IDexterityFTI, name="UTTimeslot")
        factory = fti.factory
        obj = createObject(factory)

        self.assertTrue(
            IUTTimeslot.providedBy(obj),
            "IUTTimeslot not provided by {0}!".format(
                obj,
            ),
        )

    def test_ct_ut_timeslot_adding(self):
        setRoles(self.portal, TEST_USER_ID, ["Contributor"])
        maxCapacity = 42
        # use plone.dexterity's own content-creation helper (rather than
        # api.content.create()/portal_types.constructContent()) since it
        # already knows how to safely fetch the object after autoSetID
        # renames it while it is still being added (see
        # ut_timeslot.autoSetID)
        obj = createContentInContainer(
            self.parent,
            "UTTimeslot",
            id="ut_timeslot",
            maxCapacity=maxCapacity,
        )

        self.assertEqual(obj.getNumberOfAvailableSlots(), maxCapacity)
        self.assertFalse(obj.isFull())

        self.assertTrue(
            IUTTimeslot.providedBy(obj),
            "IUTTimeslot not provided by {0}!".format(
                obj.id,
            ),
        )

    def test_get_label_with_hidden_date_time(self):
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        signupSheet = createContentInContainer(
            self.portal,
            "UTSignupSheet",
            id="ut_signup_sheet",
            title="Signup sheet",
            contactInfo="manager@example.org",
            hideDateTime=True,
        )
        day = createContentInContainer(
            signupSheet,
            "UTDay",
            id="ut_day",
            date=date.today(),
        )
        namedSlot = createContentInContainer(
            day,
            "UTTimeslot",
            id="named_slot",
            name="Consulting hour",
        )
        unnamedSlot = createContentInContainer(
            day,
            "UTTimeslot",
            id="unnamed_slot",
        )

        self.assertEqual(namedSlot.getLabel(), "Consulting hour")
        # `name` is optional - must not raise even when it was never set;
        # falls back to the signup sheet's own title instead
        self.assertEqual(unnamedSlot.getLabel(), "Signup sheet")

        # showSlotNames=False always falls back to the signup sheet's
        # title, even for a slot that does have its own name set
        signupSheet.showSlotNames = False
        self.assertEqual(namedSlot.getLabel(), "Signup sheet")

    def test_ct_ut_timeslot_globally_not_addable(self):
        setRoles(self.portal, TEST_USER_ID, ["Contributor"])
        fti = queryUtility(IDexterityFTI, name="UTTimeslot")
        self.assertFalse(fti.global_allow, "{0} is globally addable!".format(fti.id))

    def test_ct_ut_timeslot_filter_content_type_true(self):
        setRoles(self.portal, TEST_USER_ID, ["Contributor"])
        fti = queryUtility(IDexterityFTI, name="UTTimeslot")
        portal_types = self.portal.portal_types
        parent_id = portal_types.constructContent(
            fti.id,
            self.portal,
            "ut_timeslot_id",
            title="UTTimeslot container",
        )
        self.parent = self.portal[parent_id]
        with self.assertRaises(InvalidParameterError):
            api.content.create(
                container=self.parent,
                type="Document",
                title="My Content",
            )
