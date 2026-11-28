-- Write side of transactions (Add Transaction, Figma 03-06 -> 03-14). Spec: Backend/docs/add-transaction.md.
--   * AUDIT_LOG from the entity doc: one row per create / update / delete of financial data, with the values
--     before and after.
--   * transactions.client_request_id: the app sends the same id when it retries a save, so a retry never creates
--     a second transaction.
--   * Every existing user without an account gets a "Cash" account (new users get one from the app on sign-up).

-- ---- AUDIT_LOG ---------------------------------------------------------------------------------------------------
-- entity_id has no foreign key on purpose: the history must outlive a hard delete.
CREATE TABLE audit_log (
    id          UUID                     PRIMARY KEY,
    user_id     UUID                     NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    entity      VARCHAR(32)              NOT NULL,
    entity_id   UUID                     NOT NULL,
    action      VARCHAR(8)               NOT NULL,
    before      JSONB,
    after       JSONB,
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT ck_audit_log_action CHECK (action IN ('create', 'update', 'delete')),
    CONSTRAINT ck_audit_log_values CHECK (
        (action = 'create' AND before IS NULL AND after IS NOT NULL) OR
        (action = 'update' AND before IS NOT NULL AND after IS NOT NULL) OR
        (action = 'delete' AND before IS NOT NULL AND after IS NULL))
);

CREATE INDEX ix_audit_log_user_created ON audit_log (user_id, created_at DESC);
CREATE INDEX ix_audit_log_entity ON audit_log (entity, entity_id);

-- ---- Idempotent create -------------------------------------------------------------------------------------------
ALTER TABLE transactions ADD COLUMN client_request_id UUID;

CREATE UNIQUE INDEX uk_transactions_client_request
    ON transactions (user_id, client_request_id) WHERE client_request_id IS NOT NULL;

-- ---- Default Cash account for users who have none ------------------------------------------------------------------
INSERT INTO accounts (id, user_id, name, type, currency, opening_balance, is_archived, created_at, updated_at)
SELECT gen_random_uuid(), u.id, 'Cash', 'cash', u.base_currency, 0, FALSE, now(), now()
FROM users u
WHERE NOT EXISTS (SELECT 1 FROM accounts a WHERE a.user_id = u.id);
