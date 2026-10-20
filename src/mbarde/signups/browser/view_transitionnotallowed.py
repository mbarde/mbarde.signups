# -*- coding: utf-8 -*-
from plone.app.content.browser.contents import ContentsBaseAction
from Products.Five import BrowserView
from Products.statusmessages.interfaces import IStatusMessage
from zope.i18n import translate

import json


class TransitionNotAllowedView(BrowserView):
    """Exception view for mbarde.signups.transitionguards.TransitionNotAllowed

    Instead of Plone's generic error page, show the reason as a status
    message on the person the transition was attempted on (e.g. after
    clicking a state in the toolbar or a button in the person view).
    """

    def __call__(self):
        exception = self.context
        message = translate(exception.message, context=self.request)

        if isinstance(self.request.get("PUBLISHED"), ContentsBaseAction):
            return self._folderContentsResponse(message)

        IStatusMessage(self.request).addStatusMessage(message, "error")
        # lock: without it the response for the exception still ends up
        # with status 500 (+ Location header), so browsers don't redirect
        self.request.response.redirect(exception.person.absolute_url(), lock=True)
        return message

    def _folderContentsResponse(self, message):
        """The folder contents actions (e.g. @@fc-paste when pasting a cut
        person into another slot) are called via AJAX and expect the same
        JSON answer their views return themselves - a redirect to an HTML
        page would fail silently there."""
        response = self.request.response
        # lock: the response for the exception has already been set to 500
        response.setStatus(200, lock=True)
        response.setHeader("Content-Type", "application/json; charset=utf-8")
        return json.dumps({"status": "warning", "msg": message})
