# Phase 1 audit — state of the project before the benchmark was added

Written 2026-11-26, before any of the benchmark code existed. Kept as the record of what was
found and of the decisions it forced.

## What exists

| part | where | state |
|---|---|---|
| v1 parser (sklearn) | `sms_eval_final/sms_model.py` `SmsTxnModel` | **Working, the only trained extractor.** Classification and extraction are fused: the type classifier has a `none` class, then number-role LR, merchant BIO-LR, date/currency rules. |
| v1 evaluator | `sms_eval_final/evaluate.py` | `score()` = tx P/R/F1 + per-field accuracy on messages both sides call transactions. 5-fold / GroupKFold / leave-one-sender-out. |
| v2 | `sms_v2/` (untracked in git) | MARBERT gate + multi-task MARBERT extractor (`marbert.py`, `train.py`, `pipeline.py`), a linear gate, span layer `spans.py` with tests. **MARBERT never trained** — only `runs/random/gate` (linear) exists. `compare.py` has only been run `--v1-only`. |
| notebook | `sms_v2/colab.ipynb` | Trains v2 on 4 splits, compares to v1. No Drive persistence, no resume. |

## The data

* `sms_eval_final/sms_dataset_2200.jsonl`: 2 200 messages, **all synthetic** — 1 000 "fictional"
  senders + 1 200 generated from real bank / wallet templates (`gen_real_formats.py`;
  provenance `verified` 1 032, `approximate` 168). No real user SMS.
* 19 senders, 249 `template_id`s, Arabic / English / mixed, 121 with Arabic-Indic digits.
* Gold: `expected.is_transaction` + the v1 record (`type, amount, currency, fee, balance_after,
  merchant, channel, datetime, account_last4`). 1 449 transactions, 751 non-transactions.
  Every gold transaction has an amount.
* 20 exact-duplicate pairs (no conflicting labels), plus deliberate near-duplicate pairs in the
  manifest's `duplicate_group`. Templates make most messages near-duplicates of their siblings:
  5 031 near-duplicate pairs at char-4-gram cosine ≥ 0.92, **all inside a template**.
* Largest template groups are big (`vf_promo` 72, `nbe_ipn_in` 61, `cib_none` 61) — any
  template-grouped test set is therefore lumpy and has high variance.

## Labels for the two experiments

* **Binary** is exactly `is_transaction`. Nothing to derive.
* **Multi-class does not exist in the data.** The manifest's `category` (84 values) separates
  transactions from non-transactions perfectly (no category mixes the two) and most
  non-transaction categories are homogeneous (`otp`, `promo`, `declined`, `balance`, `due`, …).
  Four real-format buckets — `cib_none` (61), `hsbc_none` (52), `bm_none` (36), `oc_none` (31) —
  mix OTPs, declines, promotions, statements and alerts, and their `template_id` is just the
  category, so they had to be classified **message by message** with documented keyword rules.
  All 180 were read after labelling; one rule bug (Orange Cash balance falling to `other`) was
  found and fixed. The result is a *derived* label, stated as such everywhere.
* Decisions a reader may disagree with (all configurable in `config/labels.py`):
  * due-date reminders and card statements → `other` (they are not marketing);
  * `vf_withdraw_request` (cash-out requested, awaiting PIN) → `other`, not a transaction;
  * HSBC "refund … should be credited within 30 days" → `other` (pending, no money moved yet);
  * card / limit-available notices → `balance_inquiry`; phishing → `other`.
* The proposed "Failed transaction" class maps to `declined`, `vf_insufficient`, `vf_wrong_pin`
  and the declines inside the mixed buckets. Reversals and refunds that DID move money are
  gold transactions and stay `transaction`.

## Extraction fields asked for vs. available

| asked | gold available | how handled |
|---|---|---|
| amount, currency, account (last 4) | yes | v1 |
| merchant / recipient / sender | yes (`merchant`) | v1, reported as `counterparty` |
| date | yes (`datetime`) | v1; `date` = its date part |
| debit / credit | **derived** from `type` | debit, transfer_out, atm_withdrawal, bill_payment → debit; credit, transfer_in → credit; `other` (8 records) → null |
| reference / transaction id | **no gold** | extracted by a regex, reported, **not evaluated** |

## Compatibility issues found

* `sms_v2/` is untracked in git: edits to existing files there could not be undone. Hence the
  benchmark is **new modules beside** the existing ones; the only existing file rewritten is
  `colab.ipynb` (original kept verbatim as its appendix and as `colab.before_benchmark.ipynb.bak`).
* The suggested `pipeline/` package would shadow the existing `pipeline.py`, so the two-stage
  pipeline is `sms_pipeline.py`.
* v1's `predict()` decides transaction-or-not itself. To use it as Stage 2 without editing it,
  `extraction/v1_extractor.py` hands it a view of its type classifier with `P(none) = 0`; the
  rest of v1 runs as written.
* `sms_model.joblib` was trained on all 2 200 messages; it cannot be scored on any test split.
  The benchmark refits v1 on each training split.
* `compare_report.txt` shows v1 at 1.000 tx-F1 on its `random` split: that split has no
  near-duplicate control, so siblings of every test message are in training.
* Tokenizers (checked on the full corpus): MARBERT max 116 tokens, AraBERT 145, XLM-R 141;
  `max_len` 160 truncates nothing. AraBERT has 2.3 % `[UNK]` (emoji placeholder, some symbols),
  MARBERT 0.7 %, XLM-R 0 %. MARBERT lowercases Latin, XLM-R is cased.
* This laptop cannot hold XLM-R's 768 MB embedding matrix in free RAM: transformer training
  belongs on Colab, as planned.
