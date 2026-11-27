-- Per-email cooldown for "resend code" and "forgot password". It is checked BEFORE the account lookup, so an
-- unknown email gets exactly the same answers (202, then 429 RESEND_COOLDOWN) as a real one and the endpoints
-- cannot be used to find out which emails have accounts. The row is keyed by an HMAC of the email, so the table
-- never holds addresses. The upsert that reserves a slot is atomic, so parallel requests cannot share one.
CREATE TABLE code_dispatches (
    email_hash    VARCHAR(64)              NOT NULL,
    purpose       VARCHAR(32)              NOT NULL,
    last_sent_at  TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_code_dispatches PRIMARY KEY (email_hash, purpose),
    CONSTRAINT ck_code_dispatches_purpose CHECK (purpose IN ('EMAIL_VERIFICATION', 'PASSWORD_RESET'))
);

CREATE INDEX ix_code_dispatches_last_sent_at ON code_dispatches (last_sent_at);
