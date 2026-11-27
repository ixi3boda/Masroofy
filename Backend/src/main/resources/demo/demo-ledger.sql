-- =====================================================================================================================
--  Masroofy demo data for the home dashboard (development only)
-- =====================================================================================================================
--  Defines session-local functions; nothing is stored in the schema. Used by:
--    * the backend (DemoLedgerLoader): demo users at startup and, optionally, every new sign-up
--    * scripts/load-demo-data.sh <email>: loads it for one existing user by hand
--
--      SELECT pg_temp.demo_load_ledger('<user uuid>');          -- returns the number of transactions written
--      SELECT pg_temp.demo_load_ledger_for_email('you@x.com');  -- same, by email
--
--  It REPLACES that user's accounts, transactions, transfers and budgets. Other users are not touched.
--  Dates are relative to "now" in the user's time zone, so the current month always has data:
--    * last month: a full month of activity
--    * this month: spread over the days before today, in the same order every time, between 09:00 and 22:00
--
--  Expected dashboard for the current month (matches the "02 / Home Dashboard" Figma frame):
--    Total income 30,000.00 EGP · Total expense 12,450.00 EGP · Net 17,550.00
--    CIB Account 20,550.00 EGP · Cash 4,000.00 EGP · Payoneer USD 300.00 USD (= 14,550.00 EGP at 48.50)
--    Current balance 39,100.00 EGP (the Figma frame's 24,550 is CIB + Cash; the USD wallet shows multi-currency)
--    Budget 18,000.00 · spent 12,450.00 · remaining 5,550.00 · 69% used · ON_TRACK
--    Recent: Carrefour (Groceries) -850 · Uber (Transport) -120 · Vodafone (Bills) -250
--    Badge: 1 transaction waiting for review (an SMS-detected Starbucks payment)
--  Last month: income 46,870.00 · expense 31,410.00 · balance 21,460.00 · budget 174% OVER
-- =====================================================================================================================

-- A point inside a period of `days` whole days starting at local midnight `first_day`. frac 0 = start, 1 = end.
-- Times land between 09:00 and 22:00 local time and keep the order of `frac`.
CREATE OR REPLACE FUNCTION pg_temp.demo_waking_time(first_day DATE, days INTEGER, frac NUMERIC)
    RETURNS TIMESTAMPTZ LANGUAGE plpgsql AS $$
DECLARE
    v_tz TEXT := (SELECT tz FROM demo_ctx);
BEGIN
    RETURN ((first_day + floor(days * frac)::INTEGER)::TIMESTAMP
            + INTERVAL '9 hours' + (days * frac - floor(days * frac)) * INTERVAL '13 hours') AT TIME ZONE v_tz;
END $$;

-- Last month: all of it.
CREATE OR REPLACE FUNCTION pg_temp.demo_prev_at(frac NUMERIC) RETURNS TIMESTAMPTZ LANGUAGE plpgsql AS $$
DECLARE
    c RECORD;
BEGIN
    SELECT * INTO c FROM demo_ctx;
    RETURN pg_temp.demo_waking_time((c.prev_start AT TIME ZONE c.tz)::DATE,
                                    (c.this_start AT TIME ZONE c.tz)::DATE - (c.prev_start AT TIME ZONE c.tz)::DATE,
                                    frac);
END $$;

-- This month: the whole days before today, so everything is in the past. On the 1st, spread from midnight to now.
CREATE OR REPLACE FUNCTION pg_temp.demo_this_at(frac NUMERIC) RETURNS TIMESTAMPTZ LANGUAGE plpgsql AS $$
DECLARE
    c RECORD;
    full_days INTEGER;
BEGIN
    SELECT * INTO c FROM demo_ctx;
    full_days := floor(extract(EPOCH FROM now() - c.this_start) / 86400)::INTEGER;
    IF full_days >= 1 THEN
        RETURN pg_temp.demo_waking_time((c.this_start AT TIME ZONE c.tz)::DATE, full_days, frac);
    END IF;
    RETURN c.this_start + (now() - c.this_start) * frac;
END $$;

-- One income or expense. The category is a system category key (groceries, salary, ...).
CREATE OR REPLACE FUNCTION pg_temp.demo_tx(p_account TEXT, p_category TEXT, p_type TEXT, p_amount NUMERIC,
                                           p_at TIMESTAMPTZ, p_merchant TEXT, p_note TEXT DEFAULT NULL,
                                           p_fx NUMERIC DEFAULT 1, p_source TEXT DEFAULT 'manual',
                                           p_status TEXT DEFAULT 'confirmed', p_deleted BOOLEAN DEFAULT FALSE)
    RETURNS VOID LANGUAGE plpgsql AS $$
DECLARE
    v_user UUID := (SELECT user_id FROM demo_ctx);
    v_account accounts%ROWTYPE;
    v_category UUID;
BEGIN
    SELECT * INTO STRICT v_account FROM accounts WHERE user_id = v_user AND name = p_account;
    SELECT id INTO STRICT v_category FROM categories WHERE user_id IS NULL AND icon = p_category AND kind = p_type;
    INSERT INTO transactions (id, user_id, account_id, category_id, type, amount, currency, fx_rate_to_base,
                              occurred_at, merchant, note, source, status, is_deleted, created_at, updated_at)
    VALUES (gen_random_uuid(), v_user, v_account.id, v_category, p_type, p_amount, v_account.currency, p_fx,
            p_at, p_merchant, p_note, p_source, p_status, p_deleted, p_at, p_at);
END $$;

-- A move between two of the user's own accounts (same currency): one TRANSFER and its two legs.
CREATE OR REPLACE FUNCTION pg_temp.demo_transfer(p_from TEXT, p_to TEXT, p_amount NUMERIC, p_at TIMESTAMPTZ,
                                                 p_note TEXT) RETURNS VOID LANGUAGE plpgsql AS $$
DECLARE
    v_user UUID := (SELECT user_id FROM demo_ctx);
    v_from accounts%ROWTYPE;
    v_to accounts%ROWTYPE;
    v_transfer UUID := gen_random_uuid();
BEGIN
    SELECT * INTO STRICT v_from FROM accounts WHERE user_id = v_user AND name = p_from;
    SELECT * INTO STRICT v_to FROM accounts WHERE user_id = v_user AND name = p_to;
    INSERT INTO transfers (id, user_id, occurred_at, note, created_at, updated_at)
    VALUES (v_transfer, v_user, p_at, p_note, p_at, p_at);
    INSERT INTO transactions (id, user_id, account_id, transfer_id, type, amount, currency, occurred_at, merchant,
                              note, created_at, updated_at)
    VALUES (gen_random_uuid(), v_user, v_from.id, v_transfer, 'transfer_out', p_amount, v_from.currency, p_at, NULL,
            p_note, p_at, p_at),
           (gen_random_uuid(), v_user, v_to.id, v_transfer, 'transfer_in', p_amount, v_to.currency, p_at, NULL,
            p_note, p_at, p_at);
END $$;

-- ---- The demo ledger of one user ------------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION pg_temp.demo_load_ledger(p_user_id UUID) RETURNS INTEGER LANGUAGE plpgsql AS $$
DECLARE
    c RECORD;
    v_prev_month TEXT;
    v_this_month TEXT;
    v_written INTEGER;
BEGIN
    IF to_regclass('pg_temp.demo_ctx') IS NOT NULL THEN
        DROP TABLE pg_temp.demo_ctx;
    END IF;
    CREATE TEMP TABLE demo_ctx ON COMMIT DROP AS
    SELECT u.id                                                                       AS user_id,
           u.timezone                                                                 AS tz,
           u.base_currency                                                            AS base_currency,
           date_trunc('month', now() AT TIME ZONE u.timezone) AT TIME ZONE u.timezone AS this_start,
           (date_trunc('month', now() AT TIME ZONE u.timezone) - INTERVAL '1 month')
               AT TIME ZONE u.timezone                                                AS prev_start
    FROM users u
    WHERE u.id = p_user_id;

    SELECT * INTO c FROM demo_ctx;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'No Masroofy user with id %', p_user_id;
    END IF;
    IF c.base_currency <> 'EGP' THEN
        RAISE EXCEPTION 'The demo data is in EGP; this user''s base currency is %.', c.base_currency;
    END IF;
    v_prev_month := to_char(c.prev_start AT TIME ZONE c.tz, 'FMMonth');
    v_this_month := to_char(c.this_start AT TIME ZONE c.tz, 'FMMonth');

    -- Start clean (this user only)
    DELETE FROM transfers    WHERE user_id = p_user_id;   -- removes transfer legs too
    DELETE FROM transactions WHERE user_id = p_user_id;
    DELETE FROM budgets      WHERE user_id = p_user_id;
    DELETE FROM accounts     WHERE user_id = p_user_id;

    -- Exchange rates (EGP per 1 unit). Real rates will come from the market-data job.
    -- Last month's rate applies to last month; the latest one (inside this month) to this month.
    INSERT INTO price_quotes (id, asset_id, price, as_of, source_api)
    SELECT gen_random_uuid(), a.id, q.price, q.as_of, 'demo'
    FROM (VALUES ('USD-EGP', 48.20::NUMERIC, c.prev_start + INTERVAL '1 day'),
                 ('USD-EGP', 48.50, GREATEST(now() - INTERVAL '1 hour', c.this_start)),
                 ('EUR-EGP', 52.30, GREATEST(now() - INTERVAL '1 hour', c.this_start)),
                 ('GBP-EGP', 61.20, GREATEST(now() - INTERVAL '1 hour', c.this_start)),
                 ('SAR-EGP', 12.93, GREATEST(now() - INTERVAL '1 hour', c.this_start)),
                 ('AED-EGP', 13.21, GREATEST(now() - INTERVAL '1 hour', c.this_start))) AS q(symbol, price, as_of)
    JOIN assets a ON a.symbol = q.symbol
    ON CONFLICT (asset_id, as_of) DO NOTHING;

    -- Accounts (opened 5 days before last month)
    INSERT INTO accounts (id, user_id, name, type, currency, opening_balance, card_last4, sms_sender_id, is_archived,
                          created_at, updated_at)
    SELECT gen_random_uuid(), p_user_id, a.name, a.type, a.currency, a.opening, a.last4, a.sms, FALSE,
           c.prev_start - INTERVAL '5 days', c.prev_start - INTERVAL '5 days'
    FROM (VALUES ('CIB Account',  'bank',     'EGP', 5000.00, '4821', 'CIB'),
                 ('Cash',         'cash',     'EGP', 1000.00, NULL,   NULL),
                 ('Payoneer USD', 'e_wallet', 'USD',    0.00, NULL,   NULL)) AS a(name, type, currency, opening, last4, sms);

    -- Budgets: overall 18,000 EGP a month from last month; groceries 3,000
    INSERT INTO budgets (id, user_id, category_id, amount, period, start_date, rollover, alert_threshold_pct,
                         created_at, updated_at)
    VALUES (gen_random_uuid(), p_user_id, NULL, 18000.00, 'monthly', (c.prev_start AT TIME ZONE c.tz)::DATE, FALSE,
            80, c.prev_start, c.prev_start);
    INSERT INTO budgets (id, user_id, category_id, amount, period, start_date, rollover, alert_threshold_pct,
                         created_at, updated_at)
    SELECT gen_random_uuid(), p_user_id, cat.id, 3000.00, 'monthly', (c.prev_start AT TIME ZONE c.tz)::DATE, FALSE,
           90, c.prev_start, c.prev_start
    FROM categories cat WHERE cat.user_id IS NULL AND cat.icon = 'groceries';

    -- ---- Last month ----
    -- Income: salary 30,000 EGP + freelance 350 USD (at 48.20)
    PERFORM pg_temp.demo_tx('CIB Account', 'salary', 'income', 30000, pg_temp.demo_prev_at(0.01),
                            v_prev_month || ' salary');
    PERFORM pg_temp.demo_tx('Payoneer USD', 'freelance', 'income', 350, pg_temp.demo_prev_at(0.40), 'Upwork client',
                            'Logo design', 48.20);
    PERFORM pg_temp.demo_transfer('CIB Account', 'Cash', 3000, pg_temp.demo_prev_at(0.10), 'ATM withdrawal');
    -- CIB expenses: 26,500 EGP
    PERFORM pg_temp.demo_tx('CIB Account', 'rent',      'expense', 6500, pg_temp.demo_prev_at(0.03), 'Landlord', 'Monthly rent');
    PERFORM pg_temp.demo_tx('CIB Account', 'other',     'expense',  100, pg_temp.demo_prev_at(0.05), 'Spotify');
    PERFORM pg_temp.demo_tx('CIB Account', 'groceries', 'expense', 2400, pg_temp.demo_prev_at(0.12), 'Carrefour');
    PERFORM pg_temp.demo_tx('CIB Account', 'bills',     'expense',  250, pg_temp.demo_prev_at(0.20), 'Vodafone');
    PERFORM pg_temp.demo_tx('CIB Account', 'bills',     'expense',  700, pg_temp.demo_prev_at(0.22), 'North Cairo Electricity');
    PERFORM pg_temp.demo_tx('CIB Account', 'bills',     'expense',  550, pg_temp.demo_prev_at(0.24), 'WE Internet');
    PERFORM pg_temp.demo_tx('CIB Account', 'dining',    'expense',  650, pg_temp.demo_prev_at(0.30), 'Talabat');
    PERFORM pg_temp.demo_tx('CIB Account', 'shopping',  'expense', 2500, pg_temp.demo_prev_at(0.35), 'Noon');
    PERFORM pg_temp.demo_tx('CIB Account', 'groceries', 'expense', 1100, pg_temp.demo_prev_at(0.45), 'Spinneys');
    PERFORM pg_temp.demo_tx('CIB Account', 'health',    'expense',  900, pg_temp.demo_prev_at(0.50), 'Seif Pharmacy');
    PERFORM pg_temp.demo_tx('CIB Account', 'transport', 'expense',  650, pg_temp.demo_prev_at(0.55), 'Uber');
    PERFORM pg_temp.demo_tx('CIB Account', 'health',    'expense', 1200, pg_temp.demo_prev_at(0.58), 'Cleopatra Clinic');
    PERFORM pg_temp.demo_tx('CIB Account', 'dining',    'expense',  700, pg_temp.demo_prev_at(0.62), 'Zooba');
    PERFORM pg_temp.demo_tx('CIB Account', 'other',     'expense',  400, pg_temp.demo_prev_at(0.66), 'VOX Cinemas');
    PERFORM pg_temp.demo_tx('CIB Account', 'shopping',  'expense', 2300, pg_temp.demo_prev_at(0.70), 'Zara');
    PERFORM pg_temp.demo_tx('CIB Account', 'shopping',  'expense', 3400, pg_temp.demo_prev_at(0.74), 'IKEA');
    PERFORM pg_temp.demo_tx('CIB Account', 'bills',     'expense',  120, pg_temp.demo_prev_at(0.77), 'Town Gas');
    PERFORM pg_temp.demo_tx('CIB Account', 'groceries', 'expense', 1630, pg_temp.demo_prev_at(0.80), 'Carrefour');
    PERFORM pg_temp.demo_tx('CIB Account', 'groceries', 'expense',  450, pg_temp.demo_prev_at(0.88), 'Metro Market');
    -- Cash expenses: 2,500 EGP
    PERFORM pg_temp.demo_tx('Cash', 'groceries', 'expense', 300, pg_temp.demo_prev_at(0.13), 'Kiosk');
    PERFORM pg_temp.demo_tx('Cash', 'transport', 'expense', 150, pg_temp.demo_prev_at(0.18), 'Microbus');
    PERFORM pg_temp.demo_tx('Cash', 'dining',    'expense', 250, pg_temp.demo_prev_at(0.27), 'Cilantro');
    PERFORM pg_temp.demo_tx('Cash', 'groceries', 'expense', 600, pg_temp.demo_prev_at(0.41), 'Fruit market');
    PERFORM pg_temp.demo_tx('Cash', 'other',     'expense', 200, pg_temp.demo_prev_at(0.52), 'Barber');
    PERFORM pg_temp.demo_tx('Cash', 'transport', 'expense', 300, pg_temp.demo_prev_at(0.64), 'Taxi');
    PERFORM pg_temp.demo_tx('Cash', 'dining',    'expense', 400, pg_temp.demo_prev_at(0.79), 'El Abd Bakery');
    PERFORM pg_temp.demo_tx('Cash', 'other',     'expense', 300, pg_temp.demo_prev_at(0.91), 'Parking');
    -- USD expense: 50 USD (at 48.20)
    PERFORM pg_temp.demo_tx('Payoneer USD', 'shopping', 'expense', 50, pg_temp.demo_prev_at(0.60), 'Canva Pro', NULL, 48.20);

    -- ---- This month (days before today) ----
    PERFORM pg_temp.demo_tx('CIB Account', 'salary', 'income', 30000, pg_temp.demo_this_at(0.02),
                            v_this_month || ' salary');
    PERFORM pg_temp.demo_transfer('CIB Account', 'Cash', 4000, pg_temp.demo_this_at(0.15), 'ATM withdrawal');
    -- CIB expenses: 10,950 EGP
    PERFORM pg_temp.demo_tx('CIB Account', 'rent',      'expense', 6500, pg_temp.demo_this_at(0.04), 'Landlord', 'Monthly rent');
    PERFORM pg_temp.demo_tx('CIB Account', 'bills',     'expense',  650, pg_temp.demo_this_at(0.30), 'North Cairo Electricity');
    PERFORM pg_temp.demo_tx('CIB Account', 'bills',     'expense',  550, pg_temp.demo_this_at(0.35), 'WE Internet');
    PERFORM pg_temp.demo_tx('CIB Account', 'dining',    'expense',  420, pg_temp.demo_this_at(0.45), 'Talabat');
    PERFORM pg_temp.demo_tx('CIB Account', 'shopping',  'expense', 1280, pg_temp.demo_this_at(0.55), 'Amazon');
    PERFORM pg_temp.demo_tx('CIB Account', 'health',    'expense',  350, pg_temp.demo_this_at(0.62), 'Seif Pharmacy');
    PERFORM pg_temp.demo_tx('CIB Account', 'other',     'expense',  100, pg_temp.demo_this_at(0.70), 'Spotify');
    PERFORM pg_temp.demo_tx('CIB Account', 'bills',     'expense',  250, pg_temp.demo_this_at(0.85), 'Vodafone');
    PERFORM pg_temp.demo_tx('CIB Account', 'groceries', 'expense',  850, pg_temp.demo_this_at(0.97), 'Carrefour', 'Weekly groceries');
    -- Cash expenses: 1,500 EGP
    PERFORM pg_temp.demo_tx('Cash', 'groceries', 'expense', 180, pg_temp.demo_this_at(0.20), 'Kiosk');
    PERFORM pg_temp.demo_tx('Cash', 'transport', 'expense',  60, pg_temp.demo_this_at(0.25), 'Microbus');
    PERFORM pg_temp.demo_tx('Cash', 'dining',    'expense', 140, pg_temp.demo_this_at(0.40), 'Cilantro');
    PERFORM pg_temp.demo_tx('Cash', 'other',     'expense', 200, pg_temp.demo_this_at(0.50), 'Barber');
    PERFORM pg_temp.demo_tx('Cash', 'groceries', 'expense', 800, pg_temp.demo_this_at(0.75), 'Fruit market');
    PERFORM pg_temp.demo_tx('Cash', 'transport', 'expense', 120, pg_temp.demo_this_at(0.90), 'Uber');
    -- Not counted anywhere: waiting for review (shows as a badge), and a deleted duplicate.
    PERFORM pg_temp.demo_tx('CIB Account', 'dining', 'expense', 340, pg_temp.demo_this_at(0.93), 'Starbucks',
                            'Detected from a CIB SMS', 1, 'sms', 'pending_review');
    PERFORM pg_temp.demo_tx('CIB Account', 'groceries', 'expense', 850, pg_temp.demo_this_at(0.96), 'Carrefour',
                            'Entered twice by mistake', 1, 'manual', 'confirmed', TRUE);

    SELECT count(*) INTO v_written FROM transactions WHERE user_id = p_user_id;
    DROP TABLE pg_temp.demo_ctx;
    RETURN v_written;
END $$;

-- Same, for the user with this email (for loading by hand with psql).
CREATE OR REPLACE FUNCTION pg_temp.demo_load_ledger_for_email(p_email TEXT) RETURNS INTEGER LANGUAGE plpgsql AS $$
DECLARE
    v_user UUID := (SELECT id FROM users WHERE email = lower(trim(p_email)));
BEGIN
    IF v_user IS NULL THEN
        RAISE EXCEPTION 'No Masroofy user with that email. Sign up and verify the email first, then run this again.';
    END IF;
    RETURN pg_temp.demo_load_ledger(v_user);
END $$;
