# -*- coding: utf-8 -*-
from Products.Five import BrowserView
from Products.statusmessages.interfaces import IStatusMessage
from zope.i18n import translate


class TransitionNotAllowedView(BrowserView):
    """Exception view for mbarde.signups.transitionguards.TransitionNotAllowed

    Instead of Plone's generic error page, show the reason as a status
    message on the person the transition was attempted on (e.g. after
    clicking a state in the toolbar or a button in the person view).
    """

    def __call__(self):
        exception = self.context
        message = translate(exception.message, context=self.request)
        IStatusMessage(self.request).addStatusMessage(message, "error")
        # lock: without it the response for the exception still ends up
        # with status 500 (+ Location header), so browsers don't redirect
        self.request.response.redirect(exception.person.absolute_url(), lock=True)
        return message
