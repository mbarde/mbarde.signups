# -*- coding: utf-8 -*-
from mbarde.signups import _
from mbarde.signups import otp
from mbarde.signups.browser.view_submitselection import SubmitSelection
from zope.component import getMultiAdapter


class VerifySignupOTP(SubmitSelection):
    """Second step of the email-verification signup flow (see
    mbarde.signups.otp for the token format and rationale).

    Reuses SubmitSelection's slot/person handling so that, once the code
    is verified, the signup is finalized exactly as a normal (non-verified)
    signup would be - including a fresh availability/waiting-list check,
    since time has passed since the code was requested.
    """

    def verifyOtp(self):
        self.results = list()
        self.email = ""

        portal_state = getMultiAdapter((self.context, self.request), name="plone_portal_state")
        self.currentLanguage = portal_state.language()

        self.token = self.request.get("token", "")
        code = (self.request.get("code", "") or "").strip()

        try:
            payload = otp.parseToken(self.token)
        except otp.TokenExpired:
            self.otpError = _("This code has expired. Please sign up again.")
            self.token = ""
            return self.otpTemplate()
        except otp.TooManyAttempts:
            self.otpError = _("Too many incorrect attempts. Please sign up again.")
            self.token = ""
            return self.otpTemplate()
        except otp.InvalidToken:
            self.otpError = _("Something went wrong. Please sign up again.")
            self.token = ""
            return self.otpTemplate()

        if not otp.verifyCode(payload, code):
            self.otpError = _("Incorrect code. Please try again.")
            self.email = payload.get("email", "")
            self.token = otp.reissueWithFailedAttempt(payload)
            return self.otpTemplate()

        # code verified: restore the submitted signup data and finalize it
        self.email = payload["email"]
        self.prename = payload["prename"]
        self.surname = payload["surname"]
        self.agreeDataUsage = payload.get("agreeDataUsage", False)
        self.selectedSlots = payload.get("selectedSlots", [])
        for fieldName, value in payload.get("extraFields", {}).items():
            setattr(self, fieldName, value)

        for slotIDLabel in self.selectedSlots:
            self.getSlotAndSignUserUpForIt(slotIDLabel)

        return self.resultTemplate()
