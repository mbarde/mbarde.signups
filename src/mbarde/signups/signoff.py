# -*- coding: utf-8 -*-
# Stateless, unguessable "sign off without logging in" links, offered via
# the $$sign_off_url$$ placeholder (see
# utils.replaceCustomMailPlaceholders and ut_signup_sheet.py's mailsettings
# fieldset).
#
# This mirrors the HMAC-signing approach `otp.py` uses for email
# verification, with two differences dictated by this token needing to
# stay valid far longer than a 15-minute OTP:
#
# - it is bound to the UTPerson's UID, not to its content path. A
#   timeslot's (or day's) id - and therefore the person's path - can
#   change later (e.g. autoSetID disambiguating a duplicated slot, see
#   utils.deferRename), which would silently break a path-based link.
# - it is verified against every secret still in the keyring, not just
#   the current one, so it survives a manual secret rotation
#   (Products.CMFPlone's "Create new secret"/"Clear all secrets" in the
#   ZMI) during however long the link needs to stay useful. This mirrors
#   what plone.protect's own CSRF authenticator does, for the same
#   reason (plone.protect.authenticator._verify_request).
#
# The security of this link does not depend on it being hard to *find*
# (e.g. on rate-limiting requests) - it depends on it being
# computationally infeasible to *forge*: the signature is a 256-bit
# HMAC-SHA256, so guessing or tampering with one is not a realistic
# attack regardless of request volume.
from plone import api
from plone.keyring.interfaces import IKeyManager
from plone.uuid.interfaces import IUUID
from zope.component import getUtility

import base64
import hashlib
import hmac
import json
import urllib.parse

# "to be used with anonymous users" (see plone.keyring.keymanager.
# KeyManager) - kept separate from the "_forms" ring plone.protect uses
# for session-bound CSRF tokens, since these tokens outlive any session.
_RING = "_anon"


class InvalidSignOffToken(Exception):
    """The token is malformed, or its signature does not match any
    secret currently in the keyring."""


def _signingSecret():
    return getUtility(IKeyManager).secret(ring=_RING).encode("utf-8")


def _candidateSecrets():
    return [key.encode("utf-8") for key in getUtility(IKeyManager)[_RING] if key]


def createSignOffToken(person):
    """Build a signed, unguessable token that lets whoever holds it -
    and only them - sign `person` off later, regardless of its current
    review state (unconfirmed/waiting/signedup all allow the "signoff"
    transition, see ut_person_workflow).
    """
    payload = {"personUID": IUUID(person)}
    body = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8"))
    signature = hmac.new(_signingSecret(), body, hashlib.sha256).hexdigest()
    return (body + b"." + signature.encode("utf-8")).decode("utf-8")


def resolvePersonFromSignOffToken(token):
    """Verify `token` and return the UTPerson it refers to, or `None`
    if that person no longer exists (e.g. it was already purged by
    utils.purgeExpiredPersonalData). Raises InvalidSignOffToken if the
    token itself is malformed or its signature doesn't check out.

    Looks the person up with an unrestricted catalog search
    deliberately: the token itself *is* the authorization here - an
    anonymous/external visitor holding a valid token has no "View"
    permission on the UTPerson object otherwise (see
    ut_person_workflow's permission-maps), so a restricted lookup
    would incorrectly fail for exactly the people this is meant for.
    """
    try:
        bodyB64, signature = token.encode("utf-8").split(b".", 1)
    except (ValueError, AttributeError):
        raise InvalidSignOffToken("Malformed token.")

    signatureMatches = any(
        hmac.compare_digest(
            hmac.new(secret, bodyB64, hashlib.sha256).hexdigest(),
            signature.decode("utf-8"),
        )
        for secret in _candidateSecrets()
    )
    if not signatureMatches:
        raise InvalidSignOffToken("Signature mismatch.")

    try:
        payload = json.loads(base64.urlsafe_b64decode(bodyB64).decode("utf-8"))
        personUID = payload["personUID"]
    except (ValueError, TypeError, KeyError):
        raise InvalidSignOffToken("Malformed token.")

    catalog = api.portal.get_tool("portal_catalog")
    brains = catalog.unrestrictedSearchResults(portal_type="UTPerson", UID=personUID)
    if len(brains) != 1:
        return None
    return brains[0]._unrestrictedGetObject()


def buildSignOffUrl(signupSheet, person):
    token = createSignOffToken(person)
    return signupSheet.absolute_url() + "/@@direct-signoff?token=" + urllib.parse.quote(token)
