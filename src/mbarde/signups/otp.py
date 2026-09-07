# -*- coding: utf-8 -*-
# Stateless one-time-code (OTP) email verification for external signups.
#
# Nothing about a pending signup is ever stored server-side. Instead, the
# whole pending submission (name, email, extra fields, chosen slots, a hash
# of the generated code, an expiry timestamp and an attempt counter) is
# packed into a single tamper-proof token which is handed to the browser as
# a hidden form field. The only way to complete the signup is to submit that
# exact token back together with the plaintext code that was emailed to the
# address in it - the server never needs to remember anything in between.
#
# The token is HMAC-signed with Plone's own rotating secret (the same
# mechanism `plone.protect` uses for CSRF tokens), so the client can read it
# but cannot forge or tamper with it - e.g. it cannot extend the expiry,
# reset the attempt counter, or change which email address the code was
# sent to.
from plone.keyring.interfaces import IKeyManager
from zope.component import getUtility

import base64
import hashlib
import hmac
import json
import secrets
import time

OTP_LENGTH = 6
OTP_TTL_SECONDS = 15 * 60
OTP_MAX_ATTEMPTS = 5


class InvalidToken(Exception):
    """The token is malformed or its signature does not match."""


class TokenExpired(Exception):
    """The token was valid but has expired."""


class TooManyAttempts(Exception):
    """The token has already been used for too many failed attempts."""


def _secret():
    keyManager = getUtility(IKeyManager)
    return keyManager.secret().encode("utf-8")


def generateOtpCode():
    return "".join(secrets.choice("0123456789") for _ in range(OTP_LENGTH))


def _hashCode(code):
    return hmac.new(_secret(), code.encode("utf-8"), hashlib.sha256).hexdigest()


def _sign(payload):
    body = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8"))
    signature = hmac.new(_secret(), body, hashlib.sha256).hexdigest()
    return (body + b"." + signature.encode("utf-8")).decode("utf-8")


def createToken(data, code):
    """Build a signed token for a pending signup described by `data`
    (a JSON-serializable dict), together with the one-time `code` that
    was emailed to the user - only its hash is embedded, never the code
    itself.
    """
    payload = dict(data)
    payload["otpHash"] = _hashCode(code)
    payload["expires"] = time.time() + OTP_TTL_SECONDS
    payload["attempts"] = 0
    return _sign(payload)


def reissueWithFailedAttempt(payload):
    """Re-sign `payload` (as returned by `parseToken`) with its attempt
    counter incremented by one. Nothing else changes - in particular the
    otpHash and expiry stay exactly as they were, so only the original
    code can ever succeed, and the token can't be used to buy more time.
    """
    payload = dict(payload)
    payload["attempts"] = payload.get("attempts", 0) + 1
    return _sign(payload)


def parseToken(token):
    """Verify `token`'s signature, expiry and attempt count, and return
    its payload dict. Raises InvalidToken / TokenExpired / TooManyAttempts
    if the token can no longer be used.
    """
    try:
        bodyB64, signature = token.encode("utf-8").split(b".", 1)
    except (ValueError, AttributeError):
        raise InvalidToken("Malformed token.")

    expected = hmac.new(_secret(), bodyB64, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature.decode("utf-8")):
        raise InvalidToken("Signature mismatch.")

    try:
        payload = json.loads(base64.urlsafe_b64decode(bodyB64).decode("utf-8"))
    except (ValueError, TypeError):
        raise InvalidToken("Malformed token.")

    if payload.get("expires", 0) < time.time():
        raise TokenExpired("Token expired.")

    if payload.get("attempts", 0) >= OTP_MAX_ATTEMPTS:
        raise TooManyAttempts("Too many attempts.")

    return payload


def verifyCode(payload, code):
    return bool(code) and hmac.compare_digest(payload.get("otpHash", ""), _hashCode(code))
