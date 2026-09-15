# -*- coding: utf-8 -*-
from mbarde.signups import _
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper
from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.z3cform import layout
from zope import schema
from zope.interface import Interface


class IMbardeSignupsControlPanel(Interface):

    member_property_prename = schema.TextLine(
        title=_("Member property for prename"),
        description=_(
            "member_property_prename_description",
            default="Name of the member property to pre-fill a logged-in "
            "user's prename with. Leave empty to not pre-fill it.",
        ),
        required=False,
        default="",
    )

    member_property_surname = schema.TextLine(
        title=_("Member property for surname"),
        description=_(
            "member_property_surname_description",
            default="Name of the member property to pre-fill a logged-in "
            "user's surname with. Leave empty to not pre-fill it.",
        ),
        required=False,
        default="",
    )

    member_property_email = schema.TextLine(
        title=_("Member property for email address"),
        description=_(
            "member_property_email_description",
            default="Name of the member property to pre-fill a logged-in "
            "user's email address with. Also used to recognize a "
            "logged-in user's own reservations (unless the site is "
            "configured to use the email address as login name, in "
            "which case the login name is used instead). Leave empty "
            "to not pre-fill it.",
        ),
        required=False,
        default="email",
    )


class MbardeSignupsControlPanel(RegistryEditForm):
    schema = IMbardeSignupsControlPanel
    schema_prefix = "mbarde.signups"
    label = _("mbarde.signups Settings")
    description = _(
        "member_property_mapping_description",
        default="Map Plone member properties to the personal info fields of "
        "the signup form (prename, surname, email address), so a logged-in "
        "user's own data is used to pre-fill those fields by default.",
    )


MbardeSignupsControlPanelView = layout.wrap_form(MbardeSignupsControlPanel, ControlPanelFormWrapper)
