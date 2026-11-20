package com.masroofy.backend.model;

public enum AuthCodePurpose {
    /** 6-digit code sent after sign-up (screen 01-03). */
    EMAIL_VERIFICATION,
    /** 6-digit code sent from "Forgot password" (screens 01-05, 01-06). */
    PASSWORD_RESET,
    /** Opaque token returned once a reset code is accepted; authorises "Set new password" (01-07). */
    PASSWORD_RESET_TOKEN
}
