# -*- coding: utf-8 -*-
from mbarde.signups import otp
from mbarde.signups.testing import MBARDE_SIGNUPS_INTEGRATION_TESTING

import base64
import json
import unittest


class OTPTest(unittest.TestCase):

    layer = MBARDE_SIGNUPS_INTEGRATION_TESTING

    def makeToken(self, code="123456", data=None):
        data = data if data is not None else {"email": "person@example.org"}
        return otp.createToken(data, code)

    def test_roundtrip_success(self):
        token = self.makeToken()
        payload = otp.parseToken(token)
        self.assertTrue(otp.verifyCode(payload, "123456"))
        self.assertEqual(payload["email"], "person@example.org")

    def test_wrong_code_is_rejected(self):
        token = self.makeToken()
        payload = otp.parseToken(token)
        self.assertFalse(otp.verifyCode(payload, "000000"))

    def test_empty_code_is_rejected(self):
        token = self.makeToken()
        payload = otp.parseToken(token)
        self.assertFalse(otp.verifyCode(payload, ""))

    def test_tampered_payload_is_rejected(self):
        token = self.makeToken(data={"email": "person@example.org"})
        body, signature = token.split(".", 1)

        tampered = json.loads(base64.urlsafe_b64decode(body.encode("utf-8")))
        tampered["email"] = "attacker@example.org"
        tamperedBody = base64.urlsafe_b64encode(json.dumps(tampered).encode("utf-8")).decode(
            "utf-8"
        )
        tamperedToken = tamperedBody + "." + signature

        with self.assertRaises(otp.InvalidToken):
            otp.parseToken(tamperedToken)

    def test_garbage_token_is_rejected(self):
        with self.assertRaises(otp.InvalidToken):
            otp.parseToken("not-a-valid-token")

    def test_expired_token_is_rejected(self):
        originalTtl = otp.OTP_TTL_SECONDS
        otp.OTP_TTL_SECONDS = -1
        try:
            token = self.makeToken()
        finally:
            otp.OTP_TTL_SECONDS = originalTtl

        with self.assertRaises(otp.TokenExpired):
            otp.parseToken(token)

    def test_too_many_attempts_is_rejected(self):
        token = self.makeToken()
        payload = otp.parseToken(token)

        # each failed attempt reissues the token with attempts + 1; the
        # last one pushes attempts to OTP_MAX_ATTEMPTS, at which point the
        # token can no longer be used at all, even with the right code
        for i in range(otp.OTP_MAX_ATTEMPTS):
            token = otp.reissueWithFailedAttempt(payload)
            if i < otp.OTP_MAX_ATTEMPTS - 1:
                payload = otp.parseToken(token)

        with self.assertRaises(otp.TooManyAttempts):
            otp.parseToken(token)

    def test_reissue_preserves_original_code_hash(self):
        token = self.makeToken(code="654321")
        payload = otp.parseToken(token)

        reissued = otp.reissueWithFailedAttempt(payload)
        reissuedPayload = otp.parseToken(reissued)

        self.assertEqual(reissuedPayload["attempts"], 1)
        self.assertTrue(otp.verifyCode(reissuedPayload, "654321"))
