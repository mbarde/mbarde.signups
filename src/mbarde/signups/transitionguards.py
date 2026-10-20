# -*- coding: utf-8 -*-
"""Application-level guards for UTPerson workflow transitions.

The workflow itself has no (permission or expression) guards on most
transitions on purpose - see the comment above the "signup" transition in
ut_person_workflow/definition.xml. These checks are about whether a
transition makes sense given the configuration of the containing time
slot, independent of who triggers it (manager via the toolbar or a
button, self-service signup or auto-promotion from the waiting list).

Moving a person into another slot (cut & paste) is refused here as well,
since it would bypass all of these checks for the target slot.
"""

from Acquisition import aq_base
from mbarde.signups import _
from zope.interface import implementer
from zope.interface import Interface


class ITransitionNotAllowed(Interface):
    """Marker for the exception view (see browser/configure.zcml)"""


@implementer(ITransitionNotAllowed)
class TransitionNotAllowed(Exception):
    """Raised before a UTPerson transition that conflicts with the slot's
    configuration - aborts the transition (and the whole transaction)"""

    def __init__(self, messageOrOriginal, person=None):
        # CMFCore's WorkflowTool re-raises exceptions from a transition as
        # `ExceptionClass(originalException)` - copy over what we need
        if isinstance(messageOrOriginal, TransitionNotAllowed):
            person = messageOrOriginal.person
            messageOrOriginal = messageOrOriginal.message
        super().__init__(messageOrOriginal)
        self.message = messageOrOriginal
        self.person = person


def _signupError(timeSlot):
    if timeSlot.getNumberOfAvailableSlots() > 0:
        return None
    return _(
        "error_transition_signup_slot_full",
        default=(
            "This slot is already full (max capacity: ${maxCapacity}). "
            "Increase its capacity or sign off someone else first."
        ),
        mapping={"maxCapacity": timeSlot.maxCapacity},
    )


def _putOnWaitingListError(timeSlot):
    if timeSlot.allowWaitingList:
        return None
    return _(
        "error_transition_waiting_list_not_allowed",
        default="This slot does not allow a waiting list.",
    )


def _reactivateError(timeSlot):
    # a reactivated (= unconfirmed) person does not occupy a place yet, but
    # in a full slot without waiting list they could neither be confirmed
    # nor put on the waiting list afterwards - same rule as for a new
    # self-service signup (see view_submitselection.py)
    if timeSlot.allowWaitingList or timeSlot.getNumberOfAvailableSlots() > 0:
        return None
    return _(
        "error_transition_reactivate_slot_full",
        default=(
            "This slot is already full and does not allow a waiting list. "
            "Increase its capacity or sign off someone else first."
        ),
    )


GUARDS = {
    "signup": _signupError,
    "putOnWaitingList": _putOnWaitingListError,
    "reactivate": _reactivateError,
}


def guardTransition(person, event):
    """IBeforeTransitionEvent subscriber for UTPerson"""
    if event.transition is None:
        # initial state on creation, no transition
        return
    guard = GUARDS.get(event.transition.id)
    if guard is None:
        return
    message = guard(person.aq_parent)
    if message is not None:
        raise TransitionNotAllowed(message, person)


class MoveNotAllowed(TransitionNotAllowed):
    """Raised before a UTPerson gets moved into another time slot - handled
    by the same exception view as TransitionNotAllowed"""


def refuseMoveToOtherSlot(person, event):
    """IObjectWillBeMovedEvent subscriber for UTPerson"""
    if event.object is not person:
        # dispatched from a moved parent (a whole slot/day/sheet is moved):
        # the person stays in its slot, so that's fine
        return
    if event.oldParent is None or event.newParent is None:
        # being added or deleted
        return
    if aq_base(event.oldParent) is aq_base(event.newParent):
        # renamed within its slot (e.g. autoSetID/deferRename)
        return
    raise MoveNotAllowed(
        _(
            "error_move_person_to_other_slot",
            default=(
                "People can't be moved to another slot. Sign them off "
                "and sign them up in the other slot instead."
            ),
        ),
        person,
    )
