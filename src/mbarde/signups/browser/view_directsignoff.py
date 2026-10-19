# -*- coding: utf-8 -*-
from mbarde.signups import _
from mbarde.signups import signoff
from mbarde.signups.browser.view_cancelreservation import signOffPerson
from plone import api
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ZopeTwoPageTemplateFile
from z3c.caching.purge import Purge
from zope.event import notify


class DirectSignOff(BrowserView):
    """Lets a signed-up person cancel their own registration straight
    from a link in their confirmation/wait-for-confirmation/waiting-list
    email, without having to log in first (see
    utils.replaceCustomMailPlaceholders and the $$sign_off_url$$
    placeholder).

    GET only renders a confirmation page - it never writes to the
    database, so an email client or security gateway that prefetches
    links to scan them can't accidentally cancel anything. The actual
    cancellation only happens on the POST from that confirmation page's
    own form.
    """

    template = ZopeTwoPageTemplateFile("templates/view_directsignoff.pt")

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.person = None
        self.error = None
        self.alreadySignedOff = False

    def directSignOff(self):
        token = self.request.get("token", "")

        try:
            self.person = signoff.resolvePersonFromSignOffToken(token)
        except signoff.InvalidSignOffToken:
            self.error = _("This link is invalid.")
            return self.template()

        if self.person is None:
            self.error = _(
                "This registration could not be found. It may have already been removed."
            )
            return self.template()

        if self.request.method == "POST":
            signOffPerson(self.person)
            notify(Purge(self.context))

        self.alreadySignedOff = api.content.get_state(obj=self.person) == "signedoff"

        return self.template()

    def getSlotLabel(self):
        return self.person.aq_parent.getLabel()
