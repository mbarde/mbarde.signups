# -*- coding: utf-8 -*-
from collective.easyform.api import get_schema
from mbarde.signups import _
from plone import api
from plone.i18n.normalizer.interfaces import IIDNormalizer
from zope.component import getUtility

import transaction


def replaceCustomMailPlaceholders(
    text, personName, signupSheetTitle, signupSheetURL, slotTitle, extraInfoStr, userURL=""
):
    return (
        text.replace("$$name$$", personName)
        .replace("$$title$$", signupSheetTitle)
        .replace("$$url$$", signupSheetURL)
        .replace("$$slot$$", slotTitle)
        .replace("$$data$$", extraInfoStr)
        .replace("$$user_url$$", userURL)
    )


def appendAuthenticatedSuffix(message, person, signupSheet, slotTitle, extraInfoStr):
    if not person.signedUpWhileLoggedIn:
        return message

    suffix = signupSheet.emailSuffixAuthenticated
    if not suffix:
        return message

    suffix = replaceCustomMailPlaceholders(
        suffix,
        person.Title(),
        signupSheet.Title(),
        signupSheet.absolute_url(),
        slotTitle,
        extraInfoStr,
        signupSheet.absolute_url() + "/@@show-reservations",
    )
    return message + "\n\n" + suffix


def getAllExtraFields(signupSheet):
    result = []

    extraFormReference = signupSheet.extraFieldsForm
    if extraFormReference is None:
        return result

    formObj = extraFormReference.to_object
    if formObj is None:
        return result

    schema = get_schema(formObj)
    for fieldName in schema:
        widget = schema.get(fieldName)
        item = {}
        item["name"] = fieldName
        item["label"] = widget.title
        item["description"] = widget.description
        item["required"] = widget.required
        result.append(item)

    return result


# ID of UTPerson objects is based on persons email
def emailToPersonId(email):
    normalizer = getUtility(IIDNormalizer)
    return normalizer.normalize(email)


# plone user to personId
def ploneUserToPersonId(user):
    if api.portal.get_registry_record("plone.use_email_as_login"):
        # case: email = username
        email = user.getUserName()
    else:
        try:
            email = user.getProperty("email")
        except ValueError:
            # in case property `email` does not exist
            email = ""
    return emailToPersonId(email)


# Content-type subscribers in this addon (see the various `autoSetID`
# functions) rename freshly added/modified objects to a computed, human
# readable id (e.g. based on a date or time range). Doing that rename
# synchronously - while still inside the IObjectAdded/IObjectModified event
# notification - can crash code that, right after triggering that event,
# looks the object up again by its *original* id. This is exactly what
# OFS' copy/paste machinery does (OFS.CopySupport._pasteObjects calls
# `self._getOb(id)` again right after `self._setObject(id, ob)` returns),
# so copying/pasting a UTDay or UTTimeslot raised an AttributeError because
# the object had already been moved to its new id by then.
# Deferring the actual rename via a "before commit" hook lets any such
# caller finish its own work first (using the original id), while the
# rename still happens within the same transaction, before it is committed.
def deferRename(obj, newId):
    transaction.get().addBeforeCommitHook(_renameNow, args=(obj, newId))


def _renameNow(obj, newId):
    if obj.getId() == newId:
        return
    api.content.rename(obj=obj, new_id=newId, safe_id=True)
    obj.reindexObject()


def translateReviewState(state):
    mappings = {
        "signedup": _("Signed Up"),
        "signedoff": _("Signed Off"),
        "unconfirmed": _("Waiting for confirmation"),
        "waiting": _("Waiting List"),
    }
    if state not in mappings:
        return state
    return mappings[state]
