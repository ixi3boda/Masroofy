-- Logout and password reset raise session_version and copy it into the Firebase custom claim
-- "session_version". Every ID token minted afterwards carries the new value; FirebaseTokenFilter rejects
-- tokens carrying an older one. Unlike Firebase's own revocation check (whole seconds, compared with the
-- server clock), this does not depend on clocks, so tokens issued just before logout are rejected too.
ALTER TABLE users ADD COLUMN session_version INTEGER NOT NULL DEFAULT 0;
