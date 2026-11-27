-- USER (entity doc v2, section 1). "user" is reserved in PostgreSQL, so the table is "users".
-- Credentials live in Firebase Authentication; only the Firebase uid is stored here.
CREATE TABLE users (
    id                 UUID                     PRIMARY KEY,
    firebase_uid       VARCHAR(128)             NOT NULL,
    email              VARCHAR(254)             NOT NULL,
    phone              VARCHAR(32),
    full_name          VARCHAR(100)             NOT NULL,
    base_currency      CHAR(3)                  NOT NULL DEFAULT 'EGP',
    locale             VARCHAR(10)              NOT NULL DEFAULT 'en',
    timezone           VARCHAR(64)              NOT NULL DEFAULT 'Africa/Cairo',
    fcm_token          VARCHAR(512),
    email_verified_at  TIMESTAMP WITH TIME ZONE,
    terms_accepted_at  TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at         TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at         TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT uk_users_firebase_uid UNIQUE (firebase_uid),
    CONSTRAINT uk_users_email UNIQUE (email),
    -- UNIQUE allows many NULLs, so phone is unique only when set.
    CONSTRAINT uk_users_phone UNIQUE (phone),
    CONSTRAINT ck_users_locale CHECK (locale IN ('en', 'ar-EG'))
);

-- AUTH_CODE (added for the auth screens): one-time 6-digit codes for email verification and
-- password reset, plus the short-lived reset token issued after a reset code is accepted.
-- Only an HMAC of the code/token is stored.
CREATE TABLE auth_codes (
    id           UUID                     PRIMARY KEY,
    user_id      UUID                     NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    purpose      VARCHAR(32)              NOT NULL,
    code_hash    VARCHAR(64)              NOT NULL,
    attempts     INTEGER                  NOT NULL DEFAULT 0,
    expires_at   TIMESTAMP WITH TIME ZONE NOT NULL,
    consumed_at  TIMESTAMP WITH TIME ZONE,
    created_at   TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT ck_auth_codes_purpose
        CHECK (purpose IN ('EMAIL_VERIFICATION', 'PASSWORD_RESET', 'PASSWORD_RESET_TOKEN'))
);

CREATE INDEX ix_auth_codes_user_purpose ON auth_codes (user_id, purpose, created_at);
CREATE INDEX ix_auth_codes_hash ON auth_codes (code_hash);
