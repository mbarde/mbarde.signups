# -*- coding: utf-8 -*-
from Acquisition import aq_base
from collective.easyform.api import get_schema
from datetime import date
from mbarde.signups import _
from plone import api
from plone.i18n.normalizer.interfaces import IIDNormalizer
from zope.component import getUtility

import re
import transaction

# matches the "-1", "-2", ... suffix `api.content.rename(..., safe_id=True)`
# appends to disambiguate an id that is already taken by another object
_SAFE_ID_SUFFIX = re.compile(r"^-[0-9]+$")


def replaceCustomMailPlaceholders(
    text,
    personName,
    signupSheetTitle,
    signupSheetURL,
    slotTitle,
    extraInfoStr,
    userURL="",
    signOffUrl="",
):
    return (
        text.replace("$$name$$", personName)
        .replace("$$title$$", signupSheetTitle)
        .replace("$$url$$", signupSheetURL)
        .replace("$$slot$$", slotTitle)
        .replace("$$data$$", extraInfoStr)
        .replace("$$user_url$$", userURL)
        .replace("$$sign_off_url$$", signOffUrl)
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
        signupSheet.absolute_url() + "/@@view-my-signups",
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


# best-effort value of a member property (empty string if unset/unnamed)
def getMemberPropertyValue(user, propertyName):
    if not propertyName:
        return ""
    try:
        return user.getProperty(propertyName) or ""
    except ValueError:
        # in case that property does not exist
        return ""


# best-effort email address of a Plone user (may be empty if none is set)
def getEmailOfPloneUser(user):
    if api.portal.get_registry_record("plone.use_email_as_login"):
        # case: email = username
        return user.getUserName()
    propertyName = api.portal.get_registry_record("mbarde.signups.member_property_email")
    return getMemberPropertyValue(user, propertyName)


# best-effort prename of a Plone user (may be empty if not configured/unset)
def getPrenameOfPloneUser(user):
    propertyName = api.portal.get_registry_record("mbarde.signups.member_property_prename")
    return getMemberPropertyValue(user, propertyName)


# best-effort surname of a Plone user (may be empty if not configured/unset)
def getSurnameOfPloneUser(user):
    propertyName = api.portal.get_registry_record("mbarde.signups.member_property_surname")
    return getMemberPropertyValue(user, propertyName)


# plone user to personId
def ploneUserToPersonId(user):
    return emailToPersonId(getEmailOfPloneUser(user))


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

    currentId = obj.getId()
    occupant = obj.aq_parent._getOb(newId, None)
    if occupant is not None and aq_base(occupant) is not aq_base(obj):
        # `newId` already belongs to a *different* sibling - e.g. two
        # UTTimeslots/UTDays that still have the exact same start/end time
        # or date (most commonly: a slot/day was just duplicated and its
        # time/date has not been changed yet). If `obj` already went
        # through this exact disambiguation before (its id is `newId`
        # plus a numeric suffix), there is nothing new to resolve here -
        # retrying the rename on every future edit would just hit the
        # same collision again and again, so stop instead of scheduling
        # this rename forever.
        suffix = currentId[len(newId) :]
        if currentId.startswith(newId) and _SAFE_ID_SUFFIX.match(suffix):
            return

    # IObjectModifiedEvent is also triggered when a child is created.
    # So when a user signs up for a slot and the slots needs to be renamed here,
    # this might result correctly in `CopyError: Insufficient privileges`,
    # when the user is not a manager of the signup sheet
    with api.env.adopt_roles(["Manager"]):
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


def purgeExpiredPersonalData(dryRun=True):
    today = date.today()
    catalog = api.portal.get_tool("portal_catalog")
    results = []

    sheetBrains = catalog.unrestrictedSearchResults(portal_type="UTSignupSheet")
    for sheetBrain in sheetBrains:
        sheet = sheetBrain.getObject()
        afterDays = sheet.autoDeletePersonalDataAfterDays
        if afterDays is None:
            continue

        for day in sheet.getDays(onlyIncludeUpcomingDays=False):
            if (today - day.date).days < afterDays:
                continue

            personBrains = catalog.unrestrictedSearchResults(
                portal_type="UTPerson", path="/".join(day.getPhysicalPath())
            )
            if not personBrains:
                continue

            if not dryRun:
                for personBrain in personBrains:
                    api.content.delete(obj=personBrain.getObject(), check_linkintegrity=False)

            results.append(
                {
                    "sheet": sheet.absolute_url(1),
                    "day": day.id,
                    "count": len(personBrains),
                }
            )

    return results
