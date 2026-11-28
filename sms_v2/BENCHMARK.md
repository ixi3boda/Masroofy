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
python -m pytest tests -q      # 63 tests, ~15 min (transformer tests fetch a tiny model)
```

On Colab run `colab.ipynb` top to bottom. After a disconnect or runtime restart, run sections 0
(configuration) and 1 (setup) — or Run all — and every later section works again, in any order;
finished runs are skipped and an unfinished transformer resumes.

To run code on Colab **without committing it**: `python pack_for_colab.py` writes `sms_colab.tgz`
(code + data exactly as on disk, no results). Copy it to `MyDrive/masroofy_sms_v2/code/` and keep
`CODE_SOURCE = 'drive'` (or use `'upload'` and pick the file). The notebook fetches the code fresh
each time its section 1 (setup) runs, and every run's `metrics.json` records the archive's
`code_version` (content hash, commit, uncommitted files).
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
| `classification/` | `base_classifier.py` (interface), `sklearn_models.py` (LR, SVM, NB), `transformer_classifier.py` (MARBERT, AraBERT, XLM-R), `checkpoint_backup.py` (Drive copy of training state), `v1_reference.py`, `registry.py` |
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
appendix (the separate `.bak` copy made at the time has since been removed).

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

Transformer defaults: max_len 160, batch 32, ≤ 10 epochs, lr 3e-5, warmup 10 %, weight decay
0.01, clip 1.0, patience 3, fp16 on CUDA, seed 42. Checkpoints are saved after every epoch
(`checkpoints/last` with optimizer/scheduler/scaler/RNG state, and `checkpoints/best`). Resuming
checks a config fingerprint and refuses a mismatch. After a run completes, `final/` holds the
best epoch and the epoch checkpoints are deleted (`--keep-checkpoints` keeps them).

**Disconnect protection** (`classification/checkpoint_backup.py`, switched on by `colab.ipynb`):

| setting (env var) | Colab value | |
|---|---|---|
| `CHECKPOINT_ROOT` (`SMS_V2_CHECKPOINTS`) | `/content/checkpoints` | per-epoch checkpoints on the VM's local disk. Unset = beside the model under `OUTPUT_ROOT`. |
| `CHECKPOINT_BACKUP` (`SMS_V2_CHECKPOINT_BACKUP`) | `DRIVE_ROOT/resume` | second copy of the resumable state after each epoch. Unset = off. |
| `CHECKPOINT_BACKUP_SLOTS` (`SMS_V2_BACKUP_SLOTS`) | 2 | slots alternate, so a disconnect mid-backup still leaves the previous epoch |
| `CHECKPOINT_BACKUP_EVERY` (`SMS_V2_BACKUP_EVERY`) | 1 | epochs between backups; the last epoch is always backed up |

* Each slot holds `last/` (weights, tokenizer, `training_state.pt`) and `best/` when the best epoch
  is not the last. Its `manifest.json` is set to `writing` before any file is touched and to `ok`
  with every file's size and SHA-256 after.
* Drive uploads in the background and in no guaranteed order. So on resume every restored file is
  re-hashed; a slot that does not match is rejected and the next one is tried. The newest state
  that verifies wins, whether local or backup. `train_info.resumed_from` records which one it was.
* Slots are reused by every run and overwritten in place, never deleted: files deleted on Drive go
  to the Trash and keep counting against the quota. A finished run marks its slots `free`.
* Space: 2 slots need about 2 × 4 × model size (MARBERT ≈ 5.5 GB, XLM-R ≈ 9 GB); 1 slot halves it.
  Not verified: whether Drive bills old versions of overwritten files. The notebook prints Drive's
  free space next to the slot table, so watch that.
* A failed backup (Drive full, say) is logged in `train_info.backup_errors` and training carries
  on. Losing the VM mid-run then restarts that run.
* An interrupted epoch is lost; the run restarts from the start of that epoch, about 1–3 minutes
  of work.

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
rows appear once `colab.ipynb` section 5 runs. Full tables are in
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

## New experiments: cross-model combinations (1) and one joint model (2)

Both are **additive**. They reuse the data, the fixed splits, the preprocessing, the metrics,
the checkpoint/resume/Drive-backup machinery and the existing classifier runs. They write
only to new folders (below). No existing metric, model, checkpoint or `DONE.json` is
rewritten; `tests/test_new_experiments.py` checks this byte for byte.

```bash
python bench.py extract-tf --models marbert,arabert     # Exp 1: train the 2 transformer extractors (GPU)
python bench.py combos                                  # Exp 1: 4 combinations x binary + multiclass
python bench.py joint --models arabert,marbert          # Exp 2: 4 joint models (GPU)
python bench.py compare-new                             # tables, charts, REPORT_NEW.md
python bench.py predict --combo arabert:marbert --experiment binary "SMS ..."
python bench.py predict --joint arabert --experiment multiclass "SMS ..."
```

On Colab, `colab.ipynb` and `sms_tests.ipynb` both have one cell per configuration (sections
E1.0–E3, before the appendix). Run sections 0 and 1, then only the cells you want.

### What existed before, and what had to be added

| piece | before | now |
|---|---|---|
| AraBERT / MARBERT **classifiers** (binary, 6-class) | `transformer_classifier.py`, trained by section 5 | reused as they are, never retrained |
| **Extractor** used by the benchmark | only `v1_sklearn` (the v1 parser) | unchanged; still Stage 2 of the existing runs |
| MARBERT extractor | architecture in `marbert.py`, **never trained**: `compare_results.json` has `v2: null` on every split, and no `runs/` folder exists. Its `train.py` used `dataset.py`'s own 80/20 split, which overlaps the benchmark's test set, and had no validation, early stopping or checkpoints | the same architecture, wrapped in the benchmark's split / checkpoint / resume / backup rules: `extraction/transformer_extractor.py` |
| AraBERT extractor | did not exist | the same architecture on `aubmindlab/bert-base-arabertv02` |

**No model is substituted.** A missing classifier or extractor raises `MissingCheckpoint`
with the exact command that trains it. The v1 extractor is never used in place of a
transformer.

### Experiment 1: classifier → extractor combinations

| | AraBERT extractor | MARBERT extractor |
|---|---|---|
| **AraBERT classifier** | `arabert__arabert` | `arabert__marbert` |
| **MARBERT classifier** | `marbert__arabert` | `marbert__marbert` |

These are run for experiment A (binary classifier) and experiment B (6-class classifier), so
there are 8 configurations.

**Flow** (`SmsPipeline`, one call, no manual step): SMS → classifier → label.
* Label `transaction` → the extractor → JSON record. If no amount is found → no record
  (v1's rule, `REQUIRE_AMOUNT`).
* Any other label (binary `non_transaction`; 6-class `balance_inquiry`, `otp`,
  `promotional`, `failed_transaction`, `other`) → no extraction, reason `stage 1: <label>`.

```python
from sms_pipeline import SmsPipeline
pipe = SmsPipeline.from_combo("template", "binary", "arabert", "marbert")
pipe.process(sms)        # {"sms", "stage1": {...}, "is_transaction", "record", "reason"}
SmsPipeline.from_dirs(classifier_final_dir, extractor_final_dir)   # any dirs; kind auto-detected
```

**Extractor.** One encoder with three heads, as in `marbert.py`:
* BIO token head with 17 labels: amount, fee, balance, last-4, merchant, currency, date, time;
* type head (7 classes);
* channel head (7 classes).

The loss is the sum of the three cross-entropies. Decoding is `pipeline.py`'s
`Pipeline._assemble`, unchanged. The output is the benchmark's record (`extraction/base.py`),
the same shape as the v1 extractor's.
* **Training data:** the gold transactions of the template train split (985).
* **Model selection:** early stopping on full-record exact over the gold val transactions (219).
* **Hyperparameters:** the classifiers' (`TRANSFORMER_DEFAULTS`) plus dropout 0.1.
* **Input text:** always `spans.normalize` (= the `digits` preprocessing). It preserves
  length, so the predicted spans stay valid offsets into the raw SMS.

**Evaluation.** `bench.py combos` trains nothing.
* It combines the classifier's saved test routing (`predictions.csv`) with the extractor's
  saved test outputs.
* It scores them with the existing end-to-end code: every gold transaction counts, misses are
  scored wrong, false records are counted.
* It then loads both models and runs the real pipeline one SMS at a time on 50 test messages.
  This measures per-stage latency and checks that the live JSON equals the cached composition
  (`timing.live.output_agreement_with_cached`, 1.0 on CPU).

Each combination reports:
* the classifier's accuracy, macro P/R/F1, per-class scores and confusion matrix;
* field accuracy over all gold transactions: amount, currency, counterparty (accuracy and F1),
  date, direction, type, account;
* full-record exact precision, recall and F1;
* missed transactions (split by stage) and false records (by true class);
* classification, extraction and pipeline ms/SMS, both batched and live.

### Experiment 2: one joint model (one workflow)

Experiment 1 still uses two models. Experiment 2 uses **one AraBERT or MARBERT encoder**, with:
* a classification head on [CLS];
* the extractor's three heads.

They are trained together, and one forward pass returns both the class and the record
(`JointPipeline`).

**Labels.** No new classes are defined and no gold label is changed. The class head uses the
existing label sets:

| run | class head | labels |
|---|---|---|
| `joint binary` | 2 classes | `transaction` / `non_transaction` = gold `is_transaction` |
| `joint multiclass` | 6 classes | `transaction` + the 5 derived non-transaction classes of `config/labels.py` |

**Why this is not a re-run of experiment B.** The 6-class experiment B was already a single
classification task: one model, one softmax over 6 classes, no binary stage before it. It
only decided whether to extract, and a separate extractor did the extraction. Experiment 2
merges classification and extraction into one network.

* **Loss:** class-weighted cross-entropy (as the classifiers), plus the three extraction
  losses on gold transactions only. Non-transactions have no field labels, which is exactly
  what the separate extractor sees. So the only change from Experiment 1 is the shared
  encoder.
* **Model selection:** early stopping on the mean of val macro-F1 and val full-record exact.
* **Checkpoints:** existing classifier checkpoints cannot be reused. The network has heads
  they lack, and its encoder is trained on a different objective. So all 4 joint runs are
  new trainings (2 encoders × 2 label sets).

### Results layout (all new folders)

```
models/<split>/extractor/{marbert,arabert}/final/            beside the existing v1_sklearn/
models/<split>/joint/{binary,multiclass}/{arabert,marbert}/final/
results/<split>/extractors/<model>/                          config, metrics (standalone), predictions.jsonl (every test SMS), DONE
results/<split>/combos/<experiment>/<clf>__<ext>/            config, metrics, predictions.jsonl (final JSON per SMS),
                                                             outcomes.csv, confusion_matrix.csv, DONE
results/<split>/joint/<experiment>/<model>/                  config, metrics, predictions.csv, predictions.jsonl,
                                                             extraction_predictions.jsonl, outcomes.csv, confusion_matrix.csv, DONE
results/<split>/summary_new/                                 status.csv, extractors.csv, pipelines.csv, classification.csv,
                                                             REPORT_NEW.md, charts/, confusion_matrices/
```

Checkpoints follow the classifiers' rules (VM disk on Colab, Drive backup slots under run keys
`<split>/extractor/<model>` and `<split>/joint/<exp>/<model>`). A finished run is skipped
unless you pass `--overwrite`. An interrupted run resumes from its last epoch. A combination
is recomputed automatically if either of its two inputs is re-run.

### Checkpoint requirements

| to run | needs (finished, i.e. `DONE.json`) | trained by |
|---|---|---|
| combination `<exp>/<clf>__<ext>` | classifier `results/<split>/<exp>/<clf>` + extractor `results/<split>/extractors/<ext>` | section 5 / `bench.py classify`; `bench.py extract-tf` |
| joint `<exp>/<model>` | nothing; it trains its own model | `bench.py joint` |
| `compare-new` | any subset; `status.csv` lists what is missing and the command for it | — |

**Training still to be done:**
* the 2 extractors;
* the 4 joint models;
* any of the 4 AraBERT/MARBERT classifier runs not yet finished on Drive.

### Reading the results

* **Same extractor, different classifier** (`arabert__marbert` vs `marbert__marbert`): the
  differences come from routing alone. Read them with missed transactions and false records.
* **Same classifier, different extractor:** routing is identical, so the differences come from
  extraction alone. Standalone extraction (`extractors.csv`, perfect Stage 1) gives the same
  comparison without classifier noise.
* **Joint vs the matching combination** (`joint_arabert` vs `arabert__arabert`): the cost or
  benefit of sharing one encoder, plus the latency of one pass instead of two.
* **`ref` rows** are the existing classifier with the v1 extractor. They show what replacing
  v1 with a transformer extractor changes.
* **Exact-record F1 can rise when a stricter gate drops messages the extractor would get
  wrong anyway.** Always read it together with the miss and false-record counts.
* **Timing:**
  * "Batched" = the whole test set at once, per SMS.
  * "Live" = one SMS at a time (median).
  * The pipeline cost is classification + share routed × extraction.
  * Compare only rows from the same device (the `device` fields).

### Limitations of the new experiments

* **The extractors learn only the spans `spans.gold_spans` can locate.** A field it cannot
  find in the text is all-O for that message (see `dataset.py coverage`).
* **Validation is thin for the joint model's type head on the template split.** It has no
  `bill_payment` or tx-`other`, and has only one template each for `debit` and
  `atm_withdrawal`. Early stopping therefore sees a narrow set of transaction wordings.
* **Combinations reuse the classifiers' cached test predictions.** That is exact for the
  routing decision. On GPU with fp16 the live re-run can flip near-ties; the agreement rate
  is recorded.
* **The joint selection rule (mean of two val scores) is a design choice**, documented in each
  run's `config.json`.
* **Everything above inherits the benchmark's limits:** synthetic data, derived 6-class
  labels, a small test set per class, and wide intervals.
* **Bug found in the existing code, not changed.** `run_classify.py`'s final log line cannot
  format a `None` transaction precision. This happens when a model predicts no transaction at
  all. The run is complete (`DONE.json` is written first), but the command reports a failure.
  Only a degenerate model triggers it.
