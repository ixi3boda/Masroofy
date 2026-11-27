-- Core ledger (entity doc v2, sections 2 and 6): ACCOUNT, CATEGORY, TRANSFER, TRANSACTION, BUDGET, ASSET, PRICE_QUOTE.
-- Everything the home dashboard reads. Money is NUMERIC(14,2); exchange rates NUMERIC(18,8); timestamps are UTC.
--
-- Deviations from the entity doc, on purpose:
--   * ACCOUNT.current_balance is not stored. A balance is always computed from the rows:
--       opening_balance + income + transfer_in - expense - transfer_out   (confirmed, not deleted)
--     so it can never drift from the transactions.
--   * TRANSACTION.recurring_bill_id / import_batch_id exist but get their foreign keys when the RECURRING_BILL and
--     IMPORT_BATCH tables are created.
--   * CATEGORY.icon holds the app's category key (groceries, transport, ...), which the Android app maps to an icon.

-- ---- ACCOUNT -----------------------------------------------------------------------------------------------------
CREATE TABLE accounts (
    id               UUID                     PRIMARY KEY,
    user_id          UUID                     NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    name             VARCHAR(60)              NOT NULL,
    type             VARCHAR(16)              NOT NULL,
    currency         CHAR(3)                  NOT NULL,
    opening_balance  NUMERIC(14, 2)           NOT NULL DEFAULT 0,
    card_last4       CHAR(4),
    sms_sender_id    VARCHAR(32),
    is_archived      BOOLEAN                  NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at       TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT ck_accounts_type CHECK (type IN ('cash', 'card', 'bank', 'e_wallet')),
    CONSTRAINT ck_accounts_currency CHECK (currency ~ '^[A-Z]{3}$'),
    CONSTRAINT ck_accounts_card_last4 CHECK (card_last4 IS NULL OR card_last4 ~ '^[0-9]{4}$'),
    CONSTRAINT uk_accounts_user_name UNIQUE (user_id, name),
    -- Target of the transactions foreign key: a transaction must use an account of the SAME user, in the SAME currency.
    CONSTRAINT uk_accounts_owner_currency UNIQUE (id, user_id, currency)
);

-- ---- CATEGORY ----------------------------------------------------------------------------------------------------
CREATE TABLE categories (
    id          UUID                     PRIMARY KEY,
    user_id     UUID                     REFERENCES users (id) ON DELETE CASCADE,   -- NULL = system default
    parent_id   UUID                     REFERENCES categories (id),
    name        VARCHAR(60)              NOT NULL,
    kind        VARCHAR(8)               NOT NULL,
    icon        VARCHAR(40)              NOT NULL,
    is_hidden   BOOLEAN                  NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at  TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT ck_categories_kind CHECK (kind IN ('income', 'expense')),
    CONSTRAINT uk_categories_owner_kind_name UNIQUE NULLS NOT DISTINCT (user_id, kind, name)
);

-- System defaults: the category keys used by the Android app (frontend/src/constants/categories.ts).
INSERT INTO categories (id, user_id, parent_id, name, kind, icon, is_hidden, created_at, updated_at) VALUES
    ('0c0a0000-0000-4000-8000-000000000001', NULL, NULL, 'Groceries',    'expense', 'groceries',   FALSE, now(), now()),
    ('0c0a0000-0000-4000-8000-000000000002', NULL, NULL, 'Transport',    'expense', 'transport',   FALSE, now(), now()),
    ('0c0a0000-0000-4000-8000-000000000003', NULL, NULL, 'Bills',        'expense', 'bills',       FALSE, now(), now()),
    ('0c0a0000-0000-4000-8000-000000000004', NULL, NULL, 'Rent',         'expense', 'rent',        FALSE, now(), now()),
    ('0c0a0000-0000-4000-8000-000000000005', NULL, NULL, 'Dining',       'expense', 'dining',      FALSE, now(), now()),
    ('0c0a0000-0000-4000-8000-000000000006', NULL, NULL, 'Health',       'expense', 'health',      FALSE, now(), now()),
    ('0c0a0000-0000-4000-8000-000000000007', NULL, NULL, 'Shopping',     'expense', 'shopping',    FALSE, now(), now()),
    ('0c0a0000-0000-4000-8000-000000000008', NULL, NULL, 'Other',        'expense', 'other',       FALSE, now(), now()),
    ('0c0a0000-0000-4000-8000-000000000101', NULL, NULL, 'Salary',       'income',  'salary',      FALSE, now(), now()),
    ('0c0a0000-0000-4000-8000-000000000102', NULL, NULL, 'Freelance',    'income',  'freelance',   FALSE, now(), now()),
    ('0c0a0000-0000-4000-8000-000000000103', NULL, NULL, 'Investment',   'income',  'investment',  FALSE, now(), now()),
    ('0c0a0000-0000-4000-8000-000000000104', NULL, NULL, 'Gift',         'income',  'gift',        FALSE, now(), now()),
    ('0c0a0000-0000-4000-8000-000000000105', NULL, NULL, 'Refund',       'income',  'refund',      FALSE, now(), now()),
    ('0c0a0000-0000-4000-8000-000000000106', NULL, NULL, 'Other income', 'income',  'otherIncome', FALSE, now(), now());

-- ---- TRANSFER ----------------------------------------------------------------------------------------------------
CREATE TABLE transfers (
    id           UUID                     PRIMARY KEY,
    user_id      UUID                     NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    occurred_at  TIMESTAMP WITH TIME ZONE NOT NULL,
    note         TEXT,
    created_at   TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at   TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT uk_transfers_owner UNIQUE (id, user_id)
);

-- ---- TRANSACTION -------------------------------------------------------------------------------------------------
CREATE TABLE transactions (
    id                 UUID                     PRIMARY KEY,
    user_id            UUID                     NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    account_id         UUID                     NOT NULL,
    category_id        UUID                     REFERENCES categories (id),
    ai_category_id     UUID                     REFERENCES categories (id),
    ai_confidence      REAL,
    transfer_id        UUID,
    recurring_bill_id  UUID,
    import_batch_id    UUID,
    type               VARCHAR(12)              NOT NULL,
    amount             NUMERIC(14, 2)           NOT NULL,
    currency           CHAR(3)                  NOT NULL,
    -- Units of the user's base currency per 1 unit of `currency`, fixed when the transaction happened.
    fx_rate_to_base    NUMERIC(18, 8)           NOT NULL DEFAULT 1,
    occurred_at        TIMESTAMP WITH TIME ZONE NOT NULL,
    merchant           VARCHAR(120),
    note               TEXT,
    source             VARCHAR(12)              NOT NULL DEFAULT 'manual',
    status             VARCHAR(16)              NOT NULL DEFAULT 'confirmed',
    fingerprint        VARCHAR(64),
    is_deleted         BOOLEAN                  NOT NULL DEFAULT FALSE,
    created_at         TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at         TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT ck_transactions_type CHECK (type IN ('income', 'expense', 'transfer_in', 'transfer_out')),
    CONSTRAINT ck_transactions_amount CHECK (amount > 0),
    CONSTRAINT ck_transactions_fx_rate CHECK (fx_rate_to_base > 0),
    CONSTRAINT ck_transactions_ai_confidence CHECK (ai_confidence IS NULL OR ai_confidence BETWEEN 0 AND 1),
    CONSTRAINT ck_transactions_source
        CHECK (source IN ('manual', 'text', 'voice', 'receipt', 'sms', 'recurring', 'import', 'investment')),
    CONSTRAINT ck_transactions_status CHECK (status IN ('pending_review', 'confirmed')),
    -- Transfer legs, and only they, belong to a TRANSFER and have no category.
    CONSTRAINT ck_transactions_transfer_link CHECK ((type IN ('transfer_in', 'transfer_out')) = (transfer_id IS NOT NULL)),
    CONSTRAINT ck_transactions_category_presence
        CHECK ((type IN ('transfer_in', 'transfer_out')) = (category_id IS NULL)),
    -- Same user and same currency as the account (see uk_accounts_owner_currency).
    CONSTRAINT fk_transactions_account FOREIGN KEY (account_id, user_id, currency)
        REFERENCES accounts (id, user_id, currency),
    CONSTRAINT fk_transactions_transfer FOREIGN KEY (transfer_id, user_id)
        REFERENCES transfers (id, user_id) ON DELETE CASCADE
);

CREATE INDEX ix_transactions_user_occurred ON transactions (user_id, occurred_at DESC) WHERE NOT is_deleted;
CREATE INDEX ix_transactions_account ON transactions (account_id) WHERE NOT is_deleted;
CREATE INDEX ix_transactions_transfer ON transactions (transfer_id) WHERE transfer_id IS NOT NULL;

-- A category must be a system default or the user's own, and its kind must match the transaction type.
CREATE FUNCTION check_transaction_category() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    cat RECORD;
BEGIN
    IF NEW.category_id IS NOT NULL THEN
        SELECT user_id, kind INTO cat FROM categories WHERE id = NEW.category_id;
        IF FOUND AND cat.user_id IS NOT NULL AND cat.user_id <> NEW.user_id THEN
            RAISE EXCEPTION 'category % belongs to another user', NEW.category_id USING ERRCODE = 'check_violation';
        END IF;
        IF FOUND AND cat.kind <> NEW.type THEN
            RAISE EXCEPTION 'transaction type % does not match category kind %', NEW.type, cat.kind
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;
    IF NEW.ai_category_id IS NOT NULL THEN
        SELECT user_id INTO cat FROM categories WHERE id = NEW.ai_category_id;
        IF FOUND AND cat.user_id IS NOT NULL AND cat.user_id <> NEW.user_id THEN
            RAISE EXCEPTION 'category % belongs to another user', NEW.ai_category_id USING ERRCODE = 'check_violation';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_transactions_category
    BEFORE INSERT OR UPDATE OF category_id, ai_category_id, type, user_id ON transactions
    FOR EACH ROW EXECUTE FUNCTION check_transaction_category();

-- A transfer is exactly two legs: one transfer_out and one transfer_in, on different accounts, at the transfer's
-- time, both deleted or both not. Checked at COMMIT, so the transfer and its legs can be written in any order.
CREATE FUNCTION check_transfer_legs() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    tid        UUID := COALESCE(NEW.transfer_id, OLD.transfer_id);
    t_at       TIMESTAMP WITH TIME ZONE;
    legs       INTEGER;
    outs       INTEGER;
    ins        INTEGER;
    accounts_n INTEGER;
    deleted_n  INTEGER;
    wrong_time INTEGER;
BEGIN
    IF tid IS NULL THEN
        RETURN NULL;
    END IF;
    SELECT occurred_at INTO t_at FROM transfers WHERE id = tid;
    IF NOT FOUND THEN
        RETURN NULL;  -- the transfer itself was deleted (its legs cascade with it)
    END IF;
    SELECT count(*),
           count(*) FILTER (WHERE type = 'transfer_out'),
           count(*) FILTER (WHERE type = 'transfer_in'),
           count(DISTINCT account_id),
           count(*) FILTER (WHERE is_deleted),
           count(*) FILTER (WHERE occurred_at <> t_at)
      INTO legs, outs, ins, accounts_n, deleted_n, wrong_time
      FROM transactions WHERE transfer_id = tid;
    IF legs <> 2 OR outs <> 1 OR ins <> 1 OR accounts_n <> 2 OR deleted_n NOT IN (0, 2) OR wrong_time <> 0 THEN
        RAISE EXCEPTION 'transfer % must have one transfer_out and one transfer_in leg on two different accounts, '
            'at the transfer time, both deleted or both not', tid USING ERRCODE = 'check_violation';
    END IF;
    RETURN NULL;
END;
$$;

CREATE CONSTRAINT TRIGGER trg_transactions_transfer_legs
    AFTER INSERT OR UPDATE OR DELETE ON transactions
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION check_transfer_legs();

-- ---- BUDGET ------------------------------------------------------------------------------------------------------
-- A budget applies from start_date until a newer budget of the same user, category and period starts.
-- Amounts are in the user's base currency. Monthly budgets start on the 1st of a month.
CREATE TABLE budgets (
    id                   UUID                     PRIMARY KEY,
    user_id              UUID                     NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    category_id          UUID                     REFERENCES categories (id),   -- NULL = overall
    amount               NUMERIC(14, 2)           NOT NULL,
    period               VARCHAR(8)               NOT NULL,
    start_date           DATE                     NOT NULL,
    rollover             BOOLEAN                  NOT NULL DEFAULT FALSE,
    alert_threshold_pct  INTEGER                  NOT NULL DEFAULT 80,
    created_at           TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at           TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT ck_budgets_amount CHECK (amount > 0),
    CONSTRAINT ck_budgets_period CHECK (period IN ('weekly', 'monthly')),
    CONSTRAINT ck_budgets_monthly_start CHECK (period <> 'monthly' OR EXTRACT(DAY FROM start_date) = 1),
    CONSTRAINT ck_budgets_alert_threshold CHECK (alert_threshold_pct BETWEEN 1 AND 100),
    -- Entity doc: NULL category_id (overall) counts as one value.
    CONSTRAINT uk_budgets_period UNIQUE NULLS NOT DISTINCT (user_id, category_id, period, start_date)
);

CREATE FUNCTION check_budget_category() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    cat RECORD;
BEGIN
    IF NEW.category_id IS NOT NULL THEN
        SELECT user_id, kind INTO cat FROM categories WHERE id = NEW.category_id;
        IF FOUND AND ((cat.user_id IS NOT NULL AND cat.user_id <> NEW.user_id) OR cat.kind <> 'expense') THEN
            RAISE EXCEPTION 'a budget needs an expense category of the same user' USING ERRCODE = 'check_violation';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_budgets_category
    BEFORE INSERT OR UPDATE OF category_id, user_id ON budgets
    FOR EACH ROW EXECUTE FUNCTION check_budget_category();

-- ---- ASSET and PRICE_QUOTE (used here for currency conversion) ----------------------------------------------------
-- A currency pair "USD-EGP" has quote_currency EGP and its price is EGP per 1 USD.
CREATE TABLE assets (
    id              UUID         PRIMARY KEY,
    symbol          VARCHAR(20)  NOT NULL,
    type            VARCHAR(8)   NOT NULL,
    name            VARCHAR(100) NOT NULL,
    exchange        VARCHAR(40),
    quote_currency  CHAR(3)      NOT NULL,
    karat           INTEGER,
    CONSTRAINT uk_assets_symbol UNIQUE (symbol),
    CONSTRAINT ck_assets_type CHECK (type IN ('stock', 'gold', 'currency')),
    CONSTRAINT ck_assets_karat CHECK (karat IS NULL OR type = 'gold'),
    CONSTRAINT ck_assets_currency_pair
        CHECK (type <> 'currency' OR (symbol ~ '^[A-Z]{3}-[A-Z]{3}$' AND right(symbol, 3) = quote_currency))
);

CREATE TABLE price_quotes (
    id          UUID                     PRIMARY KEY,
    asset_id    UUID                     NOT NULL REFERENCES assets (id) ON DELETE CASCADE,
    price       NUMERIC(18, 8)           NOT NULL,
    as_of       TIMESTAMP WITH TIME ZONE NOT NULL,
    source_api  VARCHAR(40),
    CONSTRAINT ck_price_quotes_price CHECK (price > 0),
    -- Also serves "latest quote of an asset at or before time X" (scanned backwards).
    CONSTRAINT uk_price_quotes_asset_as_of UNIQUE (asset_id, as_of)
);

INSERT INTO assets (id, symbol, type, name, exchange, quote_currency, karat) VALUES
    ('0a55e700-0000-4000-8000-000000000001', 'USD-EGP', 'currency', 'US Dollar / Egyptian Pound',   NULL, 'EGP', NULL),
    ('0a55e700-0000-4000-8000-000000000002', 'EUR-EGP', 'currency', 'Euro / Egyptian Pound',        NULL, 'EGP', NULL),
    ('0a55e700-0000-4000-8000-000000000003', 'GBP-EGP', 'currency', 'British Pound / Egyptian Pound', NULL, 'EGP', NULL),
    ('0a55e700-0000-4000-8000-000000000004', 'SAR-EGP', 'currency', 'Saudi Riyal / Egyptian Pound', NULL, 'EGP', NULL),
    ('0a55e700-0000-4000-8000-000000000005', 'AED-EGP', 'currency', 'UAE Dirham / Egyptian Pound',  NULL, 'EGP', NULL);
