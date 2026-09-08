# -*- coding: utf-8 -*-
from datetime import datetime
from io import StringIO
from lxml import etree
from mbarde.signups import _
from mbarde.signups.utils import translateReviewState
from plone import api
from plone.dexterity.browser.view import DefaultView
from plone.protect.utils import addTokenToUrl
from Products.CMFPlone.resources import add_bundle_on_request
from Products.Five import BrowserView

import re


class UTSignupSheetView(DefaultView):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        # load JS resources
        add_bundle_on_request(self.request, "mbarde.signups")
        return super(UTSignupSheetView, self).__call__()

    def showEditLinks(self):
        return api.user.has_permission("mbarde.signups: Manage Schedule")

    def renderExtraForm(self):
        portal = api.portal.get()

        form = self.context.extraFieldsForm
        if form is None:
            return ""
        formObj = form.to_object

        formPath = "/".join(formObj.getPhysicalPath())
        formView = portal.restrictedTraverse(formPath + "/@@embedded")

        formHTML = formView()

        # remove form controls (submit button)
        parser = etree.HTMLParser()
        tree = etree.parse(StringIO(formHTML), parser)
        els = tree.xpath("//div[@class='formControls']")
        if len(els) > 0:
            el = els[0]
            el.getparent().remove(el)
        formHTML = etree.tostring(tree, encoding="unicode")

        # remove form opening and closing tag, submit button and h-tags with content
        # (since we want to embed input fields into existing form)
        # also replace class 'blurrable' since this toggles inline_validation.js
        # which does not work here
        toRemove = ["<form.*?>", "</form.*?>", "<h[1-9]>.*</h[1-9]>", "blurrable"]
        formHTML = re.sub("|".join(toRemove), "", formHTML)
        return formHTML


class ShowReservationsView(BrowserView):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        if api.user.is_anonymous():
            came_from = self.context.absolute_url() + "/@@show-reservations"
            self.request.response.redirect(
                api.portal.get().absolute_url() + "/login_form?came_from=" + came_from
            )
        else:
            # load JS resources
            add_bundle_on_request(self.request, "mbarde.signups")
            return super(ShowReservationsView, self).__call__()


class ManagerSummaryView(BrowserView):

    def getReviewState(self, obj):
        return api.content.get_state(obj)

    def getReviewStateTitle(self, obj):
        state = api.content.get_state(obj)
        return translateReviewState(state)

    def getRemoveAllUrl(self):
        url = self.context.absolute_url() + "/remove-all-persons"
        return addTokenToUrl(url)

    def removeAllPersons(self):
        count = self.context.removeAllPersons()
        api.portal.show_message(
            message=_("Successfully removed ${count} persons.", mapping={"count": count}),
            request=self.request,
            type="info",
        )
        return self.request.response.redirect(self.context.absolute_url() + "/manager-summary")


class UTDayView(DefaultView):
    pass


class CreateSequentialTimeslotsView(BrowserView):

    def __call__(self):
        request = self.request
        redirectUrl = self.context.absolute_url()

        try:
            startTime = datetime.strptime(request.form.get("startTime", ""), "%H:%M").time()
            duration = int(request.form.get("timeslotDuration", ""))
            count = int(request.form.get("numberOfTimeslots", ""))
        except (TypeError, ValueError):
            api.portal.show_message(
                message=_(
                    "Please provide a valid starting time, timeslot duration and number "
                    "of timeslots."
                ),
                request=request,
                type="error",
            )
            return request.response.redirect(redirectUrl)

        try:
            createdTimeSlots = self.context.createSequentialTimeSlots(startTime, duration, count)
        except ValueError as error:
            api.portal.show_message(message=str(error), request=request, type="error")
            return request.response.redirect(redirectUrl)

        api.portal.show_message(
            message=_(
                "Successfully created ${count} timeslots.",
                mapping={"count": len(createdTimeSlots)},
            ),
            request=request,
            type="info",
        )
        return request.response.redirect(redirectUrl)


class UTTimeslotView(DefaultView):
    pass


class UTPersonView(DefaultView):

    def getCurrentState(self):
        state = api.content.get_state(self.context)
        if state == "signedup":
            return (_("Signed Up"), "bg-success")
        elif state == "unconfirmed":
            return (_("Waiting for confirmation"), "bg-warning")
        elif state == "signedoff":
            return (_("Signed off"), "bg-danger")
        elif state == "waiting":
            return (_("Waiting List"), "bg-info")
