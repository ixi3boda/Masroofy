# Two-stage SMS benchmark

```
SMS ─▶ Stage 1 classifier ─┬─ transaction ─▶ Stage 2: v1 extraction parser ─▶ JSON record
                           └─ OTP / promo / balance / failed / other / non_transaction ─▶ no record
```

Stage 1 is swappable (7 classifiers, 2 label schemes); Stage 2 is the existing v1 parser,
unchanged. Everything is measured on one fixed, leak-free test set. `AUDIT.md` records the
state of the project before this was built and why each decision below was made.

## Quick start

```bash
cd sms_v2
python bench.py prepare        # validate labels, write audit, load/create splits
python bench.py classify       # TF-IDF LR / SVM / NB + v1 reference, both experiments (~1 min, CPU)
python bench.py classify --models marbert,arabert,xlm_roberta    # GPU; use colab.ipynb
python bench.py extract        # standalone extraction
python bench.py e2e            # end-to-end, every finished classifier
python bench.py compare        # tables, charts, REPORT.md
python bench.py status         # done / failed / incomplete / not run
python -m pytest tests -q      # 36 tests, ~2-3 min (transformer tests fetch a tiny model)
```

On Colab run `colab.ipynb` top to bottom; re-run it after a disconnect and it carries on.
Results go to `outputs/` locally, or wherever `SMS_V2_OUTPUT` points (a Drive folder on Colab).

Use the pipeline:

```bash
python bench.py predict --model-dir outputs/models/template/multiclass/tfidf_svm/final \
    --extractor-dir outputs/models/template/extractor/v1_sklearn "تم خصم 250 جنيه ..."
```
```python
from sms_pipeline import SmsPipeline
pipe = SmsPipeline.from_dirs(classifier_dir, extractor_dir)
pipe.process(sms)   # {"stage1": {...}, "is_transaction": bool, "record": {...} | None, "reason": ...}
```

## Layout

| path | |
|---|---|
| `config/labels.py` | class definitions, category → class map, rules for mixed buckets |
| `config/settings.py` | paths, split settings, preprocessing, every model's hyperparameters, thresholds |
| `benchmark/data.py` | load corpus + manifest, derive labels, validate, write the label audit |
| `benchmark/splits.py` | leak-free stratified group splits, saved to `data/splits/` |
| `benchmark/preprocess.py` | the one preprocessing function all models use |
| `benchmark/run_classify.py` / `run_extract.py` / `run_e2e.py` | the three runners |
| `benchmark/store.py`, `status.py` | atomic writes, DONE markers, experiment log, status |
| `classification/` | `base_classifier.py` (interface), `sklearn_models.py` (LR, SVM, NB), `transformer_classifier.py` (MARBERT, AraBERT, XLM-R), `v1_reference.py`, `registry.py` |
| `extraction/` | `base.py` (output schema, nulls, direction, reference), `v1_extractor.py` (adapter over v1) |
| `evaluation/` | `classification_metrics.py`, `extraction_metrics.py`, `end_to_end_metrics.py`, `compare_models.py` |
| `sms_pipeline.py` | the live two-stage pipeline |
| `bench.py` | command line |
| `data/splits/*.json`, `data/processed/` | committed splits; label audit and dataset report |
| `tests/` | labels, leakage, interfaces, routing, e2e accounting, transformer resume |

Deviations from the suggested structure: one `sklearn_models.py` and one
`transformer_classifier.py` instead of a file per model (the three transformers differ only in
checkpoint and learning rate, which live in `config/settings.py`); `sms_pipeline.py` instead of
`pipeline/` (which would shadow the existing `pipeline.py`); raw data stays in
`../sms_eval_final/` rather than being copied.

Existing files are untouched except `colab.ipynb`, rebuilt with the original cells kept as an
appendix (the pre-change copy is `colab.before_benchmark.ipynb.bak`).

## Labels

| class | n | source |
|---|---:|---|
| transaction | 1 449 | gold `is_transaction = true` |
| other | 189 | categories `due`, `valu_none`, `security`, `phishing`, `nbe_dormancy`, `vf_withdraw_request` + rules |
| promotional | 170 | `promo`, `vf_promo` + rules |
| otp | 163 | `otp`, `instapay_none` + rules |
| failed_transaction | 149 | `declined`, `vf_insufficient`, `vf_wrong_pin` + rules |
| balance_inquiry | 80 | `balance`, `vf_balance` + rules |

Binary = transaction vs non_transaction. The multi-class non-transaction classes are **derived
from the generator's categories**, not annotated by people; 180 messages in four mixed buckets
were assigned by ordered keyword rules (failed > OTP > promo > balance > other) and read one by
one. `data/processed/label_audit.csv` gives each message's class and the rule that set it. An
unknown category raises an error instead of being guessed.

## Splits

Each split is train / val / test ≈ 70 / 15 / 15, stratified on the 6-class label (so the binary
experiment is stratified too), with these groups never split:

1. exact duplicates after normalization, 2. the manifest's `duplicate_group`, 3. near-duplicates
(binary char-4-gram cosine ≥ 0.92 on digit-masked text; uses no labels or learned weights),
4. for `template` and `sender`: the template.

| strategy | purpose | train | val | test |
|---|---|---:|---:|---:|
| **template** (primary) | unseen wordings | 1 541 | 323 | 336 |
| random | optimistic: same templates can recur, near-duplicates cannot | 1 564 | 363 | 273 |
| sender | test = VF-Cash, CIB, HSBC, NileBank (an unseen bank) | 1 060 | 307 | 833 |

Big templates make any group split lumpy, so 30 seeds are drawn and the one whose val/test class
shares are closest to the corpus is kept. The choice uses labels only, never a model. Even so,
the `template` test set has only 8 `other` and 8 `promotional` messages. Class counts per side are
in `data/processed/dataset_report.json`. Splits are committed; loading checks the data hash.

Rules that keep the test set clean: TF-IDF vocabularies, class weights, grid search, early
stopping and the v1 extractor are all fitted or chosen on train/val only. Each run touches test
once, after its model is saved.

## Preprocessing

One mode for every model (`PREPROCESSING = "digits"`): emoji → U+FFFD, Arabic-Indic digits and
separators → ASCII. This is what v1 and v2 already did, and it preserves length. `digits_light`
(also strips tatweel and harakat, unifies alef/yaa) is available but off; changing it affects
all models together, and a model refuses to load under a different mode. No stemming, stop
words or Farasa segmentation. Casing is left to each tokenizer: TF-IDF lowercases, MARBERT
lowercases Latin, XLM-R is cased.

## Models

| name | what | selection on val | imbalance |
|---|---|---|---|
| tfidf_lr | char_wb 2-5 + word 1-2 TF-IDF → LogisticRegression | C ∈ {1, 4, 16} | class_weight balanced |
| tfidf_svm | same features → LinearSVC | C ∈ {0.1, 0.5, 2} | class_weight balanced |
| tfidf_nb | same features → MultinomialNB | α ∈ {0.01, 0.1, 0.5} | balanced sample weights, no fitted prior |
| marbert | `UBC-NLP/MARBERT` (163M) | early stopping on val macro-F1 | class-weighted CE |
| arabert | `aubmindlab/bert-base-arabertv02` (135M) | same | same |
| xlm_roberta | `FacebookAI/xlm-roberta-base` (278M), lr 2e-5 | same | same |
| v1_gate | v1's own transaction decision (binary only, reference) | — | v1's |

Transformer defaults: max_len 160, batch 32, ≤ 6 epochs, lr 3e-5, warmup 10 %, weight decay
0.01, clip 1.0, patience 2, fp16 on CUDA, seed 42. Checkpoints are saved after every epoch
(`checkpoints/last` with optimizer/scheduler/scaler/RNG state, and `checkpoints/best`). Resuming
checks a config fingerprint and refuses a mismatch. After a run completes, `final/` holds the
best epoch and the epoch checkpoints are deleted (`--keep-checkpoints` keeps them).

Why these checkpoints: MARBERT is what v2 already used. It is dialectal and tweet-trained, and
`UBC-NLP/MARBERTv2` shares its tokenizer if you want to swap. For AraBERT, v0.2 needs no Farasa
segmentation (the `arabertv2` variants do), and the `-twitter` variant was pretrained at 64
tokens only. XLM-R covers the ~40 % English/mixed messages with zero `[UNK]`.

**Scores.** LR, NB and transformers output probabilities (NB's are poorly calibrated). The SVM
outputs margins: `predict_proba` raises rather than inventing a confidence. `TRANSACTION_THRESHOLD`
(probability) and `SVM_MARGIN` (margin) raise the bar for routing; both default to plain argmax.

## Metrics

Classification (test): accuracy, macro/weighted P/R/F1, per-class P/R/F1, confusion matrix.
Two numbers are computed on the routing decision, so binary and multi-class compare directly:
**transaction recall** (a miss = a lost record) and **transaction precision** / **false-accept
rate** (a false accept = a fabricated record), plus false accepts by true class. Selection is
never by accuracy. 95 % intervals come from bootstrapping test *templates*, not messages. Cost:
training time, ms/SMS batched and one-at-a-time, model size, parameters, peak GPU memory, RSS.

Extraction, standalone (gold transactions, perfect Stage 1): amount and currency exact match,
counterparty P/R/F1, date and datetime accuracy, debit/credit accuracy, last-4, full 9-field
exact record (v1's definition) and a 6-field core exact record.

End to end (all test messages): missed transactions, split into Stage-1 rejection vs Stage-2
"no amount"; false records by true class; field accuracy over **all** gold transactions with
misses scored wrong; exact-record recall, precision and F1; pipeline ms/SMS. An `oracle` row
(perfect Stage 1) is the ceiling. Exact-record F1 can sit above the oracle: a gate that rejects
messages the extractor would get wrong anyway raises precision. Read it with the miss and
false-record counts.

## Results so far (local CPU, split `template`)

Only the CPU models have run. **MARBERT, AraBERT and XLM-R have not been trained yet**; their
rows appear once `colab.ipynb` section 7 runs. Full tables are in
`outputs/results/template/summary/REPORT.md`.

| exp | model | macro F1 (95 % CI) | tx recall | tx precision | missed | false records (e2e) |
|---|---|---|---|---|---:|---:|
| A binary | tfidf_lr | 0.707 (0.52–0.94) | 0.886 | 0.828 | 28 | 45 |
| A binary | tfidf_svm | 0.696 (0.51–0.93) | 0.886 | 0.822 | 28 | 47 |
| A binary | tfidf_nb | 0.651 (0.48–0.86) | 0.849 | 0.803 | 37 | 51 |
| A binary | v1_gate | 0.700 (0.50–0.98) | 0.784 | 0.857 | 53 | 32 |
| B multi | tfidf_lr | 0.644 (0.44–0.80) | 0.898 | 0.809 | 25 | 52 |
| B multi | tfidf_svm | 0.740 (0.62–0.88) | 0.959 | 0.830 | 10 | 48 |
| B multi | tfidf_nb | 0.520 (0.35–0.69) | 0.763 | 0.824 | 58 | 40 |

Standalone extraction (v1, 245 gold transactions): amount 0.967, currency 0.984, counterparty
F1 0.655 (P 0.92 / R 0.51), date 0.820, direction 0.804, full record 0.310.

How to read this:

* **Unseen templates are hard for TF-IDF.** Binary val macro-F1 is ~0.99 and test ~0.70. Errors
  come in whole templates: all 28 `vf_send` transactions missed, all 27 `vf_insufficient`
  declines accepted. The test set has few templates per class, so the intervals are wide and a
  single template moves a score by 0.1+. Model differences inside those intervals are not
  evidence of anything.
* Most false records come from `vf_insufficient` and `balance` messages that look like
  transactions (an amount and a balance, no failure keyword the model has seen). Those are the
  cases the transformers need to fix.
* On end-to-end exact records, Stage 2 is the bottleneck: even a perfect Stage 1 gets
  0.31 exact on unseen templates (counterparty recall and dates), matching REAL_FORMATS.md.

## Limitations

* All data is synthetic; real-format templates are generated from real bank formats, not real
  inboxes. Nothing here measures performance on real users' SMS.
* Multi-class labels are derived, not human-annotated (see Labels).
* The test set is small per class (8–41 non-transactions per class on `template`), so per-class
  numbers are noisy; use the intervals.
* `reference` has no gold labels and is not evaluated.
* The `sender` split drops near-duplicate clusters spanning held-out and kept senders from
  training; its test set is fixed by definition, so only validation was balanced.
* Inference times depend on the machine; compare models within one environment (the `device`
  column says which).
