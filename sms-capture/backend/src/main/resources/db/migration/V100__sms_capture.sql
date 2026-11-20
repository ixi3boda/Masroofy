-- SMS transaction capture (PostgreSQL). Flyway picks this up from src/main/resources/db/migration.
-- If your app already has "accounts" / "transactions" tables, keep yours and run only the ALTER
-- statements at the bottom (commented) instead of the two CREATE TABLEs.

CREATE TABLE IF NOT EXISTS accounts (
    id           BIGSERIAL PRIMARY KEY,
    user_id      BIGINT        NOT NULL,
    name         VARCHAR(100)  NOT NULL,
    type         VARCHAR(16)   NOT NULL CHECK (type IN ('CASH', 'CARD', 'BANK', 'WALLET')),
    institution  VARCHAR(100),                 -- bank or app that sends SMS, e.g. 'NileBank'
    last4        VARCHAR(4),                   -- card/account ending shown in SMS
    currency     VARCHAR(3)    NOT NULL DEFAULT 'EGP',
    balance      NUMERIC(14,2) NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_accounts_user ON accounts (user_id);

CREATE TABLE IF NOT EXISTS transactions (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             BIGINT        NOT NULL,
    account_id          BIGINT        REFERENCES accounts (id),
    type                VARCHAR(20)   NOT NULL CHECK (type IN ('DEBIT','CREDIT','TRANSFER_OUT','TRANSFER_IN','ATM_WITHDRAWAL','BILL_PAYMENT','OTHER')),
    status              VARCHAR(12)   NOT NULL CHECK (status IN ('DRAFT','CONFIRMED','REJECTED')),
    source              VARCHAR(12)   NOT NULL DEFAULT 'MANUAL',
    amount              NUMERIC(14,2) NOT NULL CHECK (amount > 0),
    fee                 NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (fee >= 0),
    currency            VARCHAR(3)    NOT NULL DEFAULT 'EGP',
    occurred_at         TIMESTAMPTZ   NOT NULL,
    merchant            VARCHAR(200),
    channel             VARCHAR(20),
    institution         VARCHAR(100),
    account_last4       VARCHAR(4),
    category            VARCHAR(60),
    internal_transfer   BOOLEAN       NOT NULL DEFAULT FALSE,
    transfer_group      UUID,
    duplicate_of_id     BIGINT        REFERENCES transactions (id),
    reported_balance    NUMERIC(14,2),
    balance_difference  NUMERIC(14,2),
    confidence          NUMERIC(4,3),
    review_reasons      VARCHAR(200),
    sms_message_id      BIGINT,
    applied             BOOLEAN       NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ   NOT NULL DEFAULT now(),
    -- a counted transaction must be confirmed and have an account
    CONSTRAINT chk_applied CHECK (NOT applied OR (status = 'CONFIRMED' AND account_id IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS idx_tx_user_status_time ON transactions (user_id, status, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_tx_user_amount_time ON transactions (user_id, amount, occurred_at);

CREATE TABLE IF NOT EXISTS sms_messages (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT       NOT NULL,
    sender          VARCHAR(64)  NOT NULL,
    institution     VARCHAR(100),
    body            TEXT,                      -- kept only for transactions; NULL for OTPs, offers, etc.
    body_hash       VARCHAR(64)  NOT NULL,     -- SHA-256 of sender + received time + text
    received_at     TIMESTAMPTZ  NOT NULL,
    status          VARCHAR(12)  NOT NULL CHECK (status IN ('APPLIED','DRAFT','IGNORED')),
    confidence      NUMERIC(4,3),
    transaction_id  BIGINT       REFERENCES transactions (id),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT uq_sms_user_hash UNIQUE (user_id, body_hash)   -- the same SMS is never processed twice
);

CREATE TABLE IF NOT EXISTS sms_senders (
    id           BIGSERIAL PRIMARY KEY,
    user_id      BIGINT       NOT NULL,
    sender_id    VARCHAR(64)  NOT NULL,       -- normalised: lower case, letters and digits only
    institution  VARCHAR(100) NOT NULL,
    kind         VARCHAR(16)  NOT NULL CHECK (kind IN ('CASH','CARD','BANK','WALLET')),
    enabled      BOOLEAN      NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_sender_user UNIQUE (user_id, sender_id)
);

-- Existing tables instead of the CREATEs above:
-- ALTER TABLE accounts     ADD COLUMN institution VARCHAR(100), ADD COLUMN last4 VARCHAR(4);
-- ALTER TABLE transactions ADD COLUMN status VARCHAR(12) NOT NULL DEFAULT 'CONFIRMED', ADD COLUMN source VARCHAR(12) NOT NULL DEFAULT 'MANUAL',
--   ADD COLUMN fee NUMERIC(14,2) NOT NULL DEFAULT 0, ADD COLUMN channel VARCHAR(20), ADD COLUMN institution VARCHAR(100),
--   ADD COLUMN account_last4 VARCHAR(4), ADD COLUMN internal_transfer BOOLEAN NOT NULL DEFAULT FALSE, ADD COLUMN transfer_group UUID,
--   ADD COLUMN duplicate_of_id BIGINT, ADD COLUMN reported_balance NUMERIC(14,2), ADD COLUMN balance_difference NUMERIC(14,2),
--   ADD COLUMN confidence NUMERIC(4,3), ADD COLUMN review_reasons VARCHAR(200), ADD COLUMN sms_message_id BIGINT,
--   ADD COLUMN applied BOOLEAN NOT NULL DEFAULT TRUE;   -- existing rows are already in the balance
