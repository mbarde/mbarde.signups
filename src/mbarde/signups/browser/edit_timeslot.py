# -*- coding: utf-8 -*-
# Overrides the stock Dexterity edit form for UTTimeslot specifically, to
# confirm with the manager before reducing maxCapacity below the number
# of people already signed up.
from mbarde.signups import _
from plone import api
from plone.dexterity.browser.edit import DefaultEditForm
from plone.dexterity.events import EditFinishedEvent
from plone.dexterity.interfaces import IDexterityEditForm
from plone.z3cform import layout
from Products.statusmessages.interfaces import IStatusMessage
from z3c.form import button
from z3c.form.field import Fields
from zope.event import notify
from zope.interface import classImplements
from zope.schema import Bool

confirmReduceCapacityField = Bool(
    __name__="confirmReduceCapacity",
    title=_("Confirm capacity reduction"),
    description=_(
        "Check this and save again if you are reducing the maximum "
        "capacity below the number of people currently signed up, to "
        "confirm you understand the consequences for them."
    ),
    required=False,
    default=False,
)


def _moveExcessToWaitingList(timeSlot, excess):
    for person in timeSlot.getMostRecentlySignedUpPersons(excess):
        api.content.transition(obj=person, transition="putOnWaitingList")
        person.reindexObject()


class UTTimeslotEditForm(DefaultEditForm):
    def updateFields(self):
        super().updateFields()
        self.fields += Fields(confirmReduceCapacityField)

    @button.buttonAndHandler(_("Save"), name="save")
    def handleApply(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        confirmed = data.pop("confirmReduceCapacity", False)
        newCapacity = data["maxCapacity"]
        newAllowWaitingList = data["allowWaitingList"]
        currentlySignedUp = self.context.getNumberOfSignedUpPersons()
        excess = currentlySignedUp - newCapacity

        if excess > 0 and newAllowWaitingList and not confirmed:
            self.status = _(
                "warning_capacity_reduction_to_waiting",
                default=(
                    "Reducing the maximum capacity to ${newCapacity} will move "
                    "${excess} of the ${current} people currently signed up to "
                    "the waiting list (the most recently signed-up ones). "
                    "Check the confirmation box below and save again to proceed."
                ),
                mapping={
                    "newCapacity": newCapacity,
                    "excess": excess,
                    "current": currentlySignedUp,
                },
            )
            return

        self.applyChanges(data)
        IStatusMessage(self.request).addStatusMessage(self.success_message, "info")

        if excess > 0 and newAllowWaitingList:
            _moveExcessToWaitingList(self.context, excess)

        self.request.response.redirect(self.nextURL())
        notify(EditFinishedEvent(self.context))


UTTimeslotEditView = layout.wrap_form(UTTimeslotEditForm)
classImplements(UTTimeslotEditView, IDexterityEditForm)
