# -*- coding: utf-8 -*-
from plone import api
from plone.app.contenttypes.testing import PLONE_APP_CONTENTTYPES_FIXTURE
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import MOCK_MAILHOST_FIXTURE
from plone.app.testing import PloneSandboxLayer
from plone.testing import z2

import mbarde.signups


class MbardeSignupsLayer(PloneSandboxLayer):

    defaultBases = (PLONE_APP_CONTENTTYPES_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # Load any other ZCML that is required for your tests.
        # The z3c.autoinclude feature is disabled in the Plone fixture base
        # layer.
        self.loadZCML(package=mbarde.signups)

    def setUpPloneSite(self, portal):
        applyProfile(portal, "mbarde.signups:default")

        api.portal.set_registry_record("plone.email_from_address", "noreply@example.com")
        api.portal.set_registry_record("plone.email_from_name", "Plone Site")


MBARDE_SIGNUPS_FIXTURE = MbardeSignupsLayer()


MBARDE_SIGNUPS_INTEGRATION_TESTING = IntegrationTesting(
    bases=(MBARDE_SIGNUPS_FIXTURE, MOCK_MAILHOST_FIXTURE),
    name="MbardeSignupsLayer:IntegrationTesting",
)


MBARDE_SIGNUPS_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(MBARDE_SIGNUPS_FIXTURE, MOCK_MAILHOST_FIXTURE),
    name="MbardeSignupsLayer:FunctionalTesting",
)


MBARDE_SIGNUPS_ACCEPTANCE_TESTING = FunctionalTesting(
    bases=(
        MBARDE_SIGNUPS_FIXTURE,
        REMOTE_LIBRARY_BUNDLE_FIXTURE,
        z2.ZSERVER_FIXTURE,
    ),
    name="MbardeSignupsLayer:AcceptanceTesting",
)
