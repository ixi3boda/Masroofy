# sms_v2 — MARBERT transaction gate + field extractor

A second implementation of Masroofy's SMS reader, built to be compared against the
existing one rather than to replace it. `sms_eval_final/` (call it **v1**) stays
exactly as it is; nothing here writes to it.

```
SMS ──▶ stage 1: gate ──▶ not a transaction → {"is_transaction": false}
                 │
                 └─ transaction ──▶ stage 2: MARBERT extractor ──▶ JSON record
```

**Stage 1 — gate.** Binary sequence classification: is this SMS a transaction at
all? OTPs, promos, declines, statements and balance notices get dropped here.
Backends: `marbert` (fine-tuned `UBC-NLP/MARBERT`) or `linear` (char+word TF-IDF →
logistic regression, needs no torch — it is the control, not the contender).

**Stage 2 — extractor.** One MARBERT encoder, three heads:

| head | what it predicts |
|---|---|
| token (BIO, 17 labels) | `AMOUNT` `FEE` `BALANCE` `LAST4` `MERCHANT` `CURRENCY` `DATE` `TIME` spans |
| type | `debit` `credit` `transfer_out` `transfer_in` `atm_withdrawal` `bill_payment` `other` |
| channel | `card` `instapay` `wallet` `bank_transfer` `atm` `other` `unknown` |

One encoder with three heads rather than three models: the fields are mutually
informative (a number after `رصيد` is a balance *because* the message is a debit),
it is 3× less to train, and the sequence heads regularise the token head. Loss is
the plain sum of the three cross-entropies.

Output is v1's exact record schema, so `sms_eval_final/evaluate.py:score()` grades
both implementations with the same code — see `compare.py`.

## Why this might beat v1, concretely

`REAL_FORMATS.md:103` says items 1–3 and 7 of its failure list are **rule-layer
limits that more training data cannot fix**. Those are limits of v1's regexes, not
of its statistics, so v2 fixes them in `spans.py` and proves it in `test_spans.py`:

| REAL_FORMATS item | example | v1 | v2 |
|---|---|---|---|
| 2 glued currency | `195.15EGP` | `195.0` | `195.15` |
| 2 glued currency | `EGP15,608.48` | *no number found* | `15608.48` |
| 2 glued currency | `11260EGP` | *no number found* | `11260.0` |
| 2 glued currency | `EGP209.69` | *no number found* | `209.69` |
| 3 leading dot | `EUR .93` | *no number found* | `0.93` |
| 1 `YY-MM-DD` | `26-10-14` | `2014-10-26` | `2026-10-14` |
| 1 `DDMMMYY` | `31AUG26` | `null` | `2026-08-31` |
| 1 `DD-MMM-YYYY` | `30-AUG-2026` | `null` | `2026-08-30` |
| 1 `MMM D, YYYY` | `Feb 13, 2026` | `null` | `2026-02-13` |
| 1 `MM/DD/YYYY` | `08/20/2026` | `null` | `2026-08-20` |
| 7 script boundary | `فيNETFLIX.COM` | one token, span uncuttable | WordPiece splits scripts |

Items 4, 5, 6, 8, 9 and 10 of that list are *statistical* failures (CIB writing the
same words for both transfer directions, non-transactions with amounts getting
accepted, `رقم` missing from `MASKED_RE`). Those are what the transformer is
actually for.

## Install

The span layer, the linear gate and `compare.py --v1-only` run on what this project
already has. MARBERT needs more:

```bash
pip install -r requirements.txt
# or, much smaller, CPU-only torch:
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install transformers
```

~2.5 GB installed, plus ~650 MB of MARBERT weights downloaded on first use and
cached in `~/.cache/huggingface`.

**Hardware.** On a GPU a fine-tune of this corpus is minutes. On CPU, budget
30–60 min per epoch per stage — call it 2–3 h for one split's gate + extractor at
3 epochs, ×4 splits for the full comparison. `--limit 64 --epochs 1` smoke-tests
the whole path in a couple of minutes first.

Disk and memory are the real constraints, not patience: torch + transformers is
~2.5 GB installed, MARBERT's weights another ~650 MB, and each checkpoint is
~650 MB per stage per split. A BERT-base fine-tune wants 4–6 GB of RAM.

**`colab.ipynb` is the path of least resistance** — open it in Colab, set the
runtime to a T4, and it clones or uploads the code, smoke-tests, trains all four
splits and runs the comparison. Colab already has torch, so only `transformers`
installs. Bring `compare_report.txt` home and leave the checkpoints there unless
you intend to serve the model.

## Run

```bash
# what the splits look like
python dataset.py splits
python dataset.py coverage        # can the span layer even locate each gold field?

# tests, no torch needed
python test_spans.py              # the REAL_FORMATS failure list, as assertions
python test_labels.py             # oracle round-trip = v2's extraction ceiling

# train
python train.py --split random --stage gate --backend linear      # ~16 s, no torch
python train.py --split random --stage both                        # MARBERT, slow
python train.py --split random --stage both --limit 64 --epochs 1  # smoke test

# predict — a JSON database in the corpus's own schema
python predict.py --run runs/random "تم خصم 250 جنيه ..."
python predict.py --run runs/random --jsonl inbox.jsonl --out db.jsonl --as-dataset

# compare
python compare.py --splits random --v1-only                        # baseline only
python compare.py --splits random,unseen_wording,unseen_sender,real_formats
```

`--as-dataset` writes `{"id", "sender", "sms", "expected": {...}}`, i.e. exactly
`sms_dataset_2200.jsonl`'s shape, so the output is a drop-in corpus that
`evaluate.py` and `make_parity_fixture.py` read unchanged.

## The splits, and why they differ from eval_report.txt

`evaluate.py` cross-validates — 5-fold, GroupKFold, leave-one-sender-out, 30 fits
in all. That is fine for a 12-second sklearn fit and impossible for a transformer.
So `dataset.py` defines **one** train/test division per regime, with the same
intent as v1's folds, and `compare.py` trains both implementations on that exact
division:

| split | train | test | what it measures |
|---|---|---|---|
| `random` | 1760 | 440 | optimistic: every template seen in training |
| `unseen_wording` | 1803 | 397 | 20% of `template_id`s held out |
| `unseen_sender` | 1367 | 833 | VF-Cash, CIB, HSBC, NileBank held out entirely |
| `real_formats` | 1000 | 1200 | train on fictional senders, test on real formats |

**Absolute numbers here are therefore not comparable to `eval_report.txt`** (one
80/20 split is not 5-fold CV; `unseen_sender` holds out 4 senders at once rather
than one at a time). The v1-vs-v2 delta within a split is the meaningful figure,
which is why `compare.py` retrains v1 per split instead of reusing the committed
`.joblib` — otherwise v1 would have seen the test rows.

## Fairness rules in compare.py

* identical train rows, identical test rows, from `dataset.split()`
* both graded by `sms_eval_final/evaluate.py:score()` — v1's own scorer, so metric
  definitions cannot drift between the two
* v1 retrained per split, never scored on rows it trained on
* v2 keeps v1's rule that **a transaction must carry an amount**, so neither side
  gets a free pass on that
* per-field accuracy is over messages both sides call transactions, which is how
  `score()` has always worked — read it next to `tx_f1` and `non_tx_rejected`, or a
  model that rejects everything looks precise

## Known ceiling

`test_labels.py` feeds the *correct* labels to the decoder and measures what comes
back. That isolates the span finders, the BIO alignment and the parsers from the
model, and the result is the best v2 can possibly do:

```
amount 100%  currency 100%  fee 100%  balance_after 100%
merchant 100%  account_last4 100%  datetime 99.9%
all span fields 99.9%  (1447/1449)
```

The two residual misses are NBE branch deposits writing `يوم 07/02/2026`, where
`DD/MM` and `MM/DD` are both valid readings of the same span and the corpus means
`MM/DD`. Unresolvable from the span alone; a sender-conditioned preference or a
small day/month-order head would fix it, at the cost of overfitting the senders in
`unseen_sender`. Left alone, documented, 2 records out of 1449.

`dataset.py coverage` reports the same thing from the other direction: the share of
gold fields that can be located in the text at all. Everything is 100% except
`FEE` at 93.3% — the remainder are the 15 records that state "no fees" in words
with no number to tag, handled by `pipeline.NO_FEE` instead.

## Files

| file | |
|---|---|
| `schema.py` | field names, label sets, the record shape — shared with v1 |
| `spans.py` | number / date / time / currency finders and parsers; no deps |
| `dataset.py` | loading, the four splits, span↔BIO alignment, coverage report |
| `marbert.py` | both models, the training loop, save/load |
| `linear_gate.py` | torch-free stage-1 control |
| `pipeline.py` | gate + extractor → a v1-schema record |
| `train.py` | train either stage on one split |
| `predict.py` | SMS or `.jsonl` → JSON records |
| `compare.py` | v1 vs v2, same data, same scorer |
| `test_spans.py` | the REAL_FORMATS failure list as assertions |
| `test_labels.py` | oracle round-trip, the ceiling |
| `colab.ipynb` | train on a free GPU and run the comparison end to end |

`runs/` holds checkpoints and is not meant for git — a MARBERT checkpoint is
~650 MB per stage per split.

## Two-stage benchmark (Stage-1 classifiers → extraction)

A benchmark of seven Stage-1 classifiers (TF-IDF LR / SVM / NB, MARBERT, AraBERT,
XLM-RoBERTa, and v1's own gate), binary and 6-class, wired to the v1 extraction parser and
evaluated end to end on leak-free splits. See **`BENCHMARK.md`** (how to run, design,
metrics, results, limitations) and **`AUDIT.md`** (what the project looked like before it).
Entry point: `python bench.py --help`. The Colab notebook now runs the benchmark first; the
original v1-vs-v2 cells are kept unchanged as its appendix.
