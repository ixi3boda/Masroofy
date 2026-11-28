"""Benchmark configuration: paths, splits, preprocessing and every model's knobs.

Kept free of logic so it can be read on its own. Anything here can be overridden
from the command line (`python bench.py classify --help`).

Paths
-----
Code and data live in the repo; everything the benchmark *produces* (splits are
the exception, see below) goes under OUTPUT_ROOT:

    OUTPUT_ROOT/
      models/<split>/<experiment>/<model>/        checkpoints, final weights
      results/<split>/<experiment>/<model>/       metrics.json, predictions.csv, DONE
      results/<split>/extraction/                 standalone extraction
      results/<split>/end_to_end/                 pipeline results
      results/<split>/summary/                    comparison tables + charts
      experiment_log.jsonl                        one line per run start/finish/failure

Set the environment variable SMS_V2_OUTPUT to put it elsewhere — in Colab that is
a Google Drive folder, so a disconnect loses nothing that was finished.

Splits are written to sms_v2/data/splits/ inside the repo, so the local machine
and Colab use byte-identical splits. They are deterministic from SPLIT_SEED and
the data, and carry a hash of the data they were made from.
"""
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # sms_v2/
REPO = os.path.dirname(HERE)

DATA_PATH = os.environ.get("SMS_V2_DATA",
                           os.path.join(REPO, "sms_eval_final", "sms_dataset_2200.jsonl"))
MANIFEST_PATH = os.environ.get("SMS_V2_MANIFEST",
                               os.path.join(REPO, "sms_eval_final", "manifest_2200.csv"))
V1_DIR = os.path.join(REPO, "sms_eval_final")

SPLITS_DIR = os.path.join(HERE, "data", "splits")
PROCESSED_DIR = os.path.join(HERE, "data", "processed")
OUTPUT_ROOT = os.environ.get("SMS_V2_OUTPUT", os.path.join(HERE, "outputs"))

# ------------------------------------------------- transformer checkpoints
# Where the per-epoch training checkpoints (weights + optimizer state, 2-3.5 GB
# for these models) are written. None = beside the model under OUTPUT_ROOT. On
# Colab this is the VM's local disk: fast, and rewriting it every epoch does not
# fill Google Drive's Trash (files deleted on Drive keep using your quota).
CHECKPOINT_ROOT = os.environ.get("SMS_V2_CHECKPOINTS") or None
# A second copy of the latest resumable state, for when the VM itself is lost.
# Fixed slot folders, overwritten in place (never deleted), each file checksummed;
# resume takes the newest slot that verifies and falls back to the next. None = off.
CHECKPOINT_BACKUP = os.environ.get("SMS_V2_CHECKPOINT_BACKUP") or None
# 2 = a disconnect during a backup write falls back to the epoch before it.
# Needs ~2 x (4 x model size) on Drive: ~5.5 GB MARBERT, ~9 GB XLM-R. 1 halves it.
CHECKPOINT_BACKUP_SLOTS = int(os.environ.get("SMS_V2_BACKUP_SLOTS", "2"))
CHECKPOINT_BACKUP_EVERY = int(os.environ.get("SMS_V2_BACKUP_EVERY", "1"))   # epochs

# --------------------------------------------------------------------- splits
SPLIT_SEED = 42
# Candidate seeds tried (SPLIT_SEED .. SPLIT_SEED+SPLIT_SEARCH-1); the draw whose
# val/test class shares are closest to the corpus's is kept (labels only, no model).
SPLIT_SEARCH = 30
# Fractions of the whole corpus. Test is carved first, then validation from the rest.
TEST_FRACTION = 0.15
VAL_FRACTION = 0.15
# Two messages whose character-4-gram sets have cosine >= this are treated as
# near-duplicates and forced into the same split.
NEAR_DUP_THRESHOLD = 0.92

# Split strategies (see benchmark/splits.py):
#   template  primary. Groups = template_id + near-duplicate clusters, so the test
#             set holds wordings the model never saw. The honest default.
#   random    optimistic reference. Groups = near-duplicate clusters only.
#   sender    held-out senders as test (an unseen bank's format).
SPLIT_STRATEGIES = ["template", "random", "sender"]
PRIMARY_SPLIT = "template"
HELD_OUT_SENDERS = ["VF-Cash", "CIB", "HSBC", "NileBank"]     # same as dataset.py

# --------------------------------------------------------------------- preprocessing
# One preprocessing mode for EVERY model, so no model gets a different view of
# the text. See benchmark/preprocess.py for what each does.
#   "digits"        emoji -> U+FFFD, Arabic-Indic digits/separators -> ASCII.
#                   Exactly what v1 and v2 already do; length-preserving.
#   "digits_light"  + strip tatweel and Arabic diacritics, unify alef/yaa forms.
PREPROCESSING = "digits"

# --------------------------------------------------------------------- experiments
EXPERIMENTS = ["binary", "multiclass"]

# --------------------------------------------------------------------- models
SKLEARN_FEATURES = {
    # char n-grams within word boundaries handle Arabic morphology, glued
    # currency ("195.15EGP") and typos; word n-grams carry phrase cues.
    "char": {"analyzer": "char_wb", "ngram_range": (2, 5), "min_df": 2, "sublinear_tf": True},
    "word": {"analyzer": "word", "token_pattern": r"[A-Za-z؀-ۿ]+",
             "ngram_range": (1, 2), "min_df": 2, "sublinear_tf": True, "lowercase": True},
}

SKLEARN_MODELS = {
    # Grids are searched on the VALIDATION set only (macro F1); the winner is the
    # model trained on the training set with that value.
    "tfidf_lr": {"kind": "lr", "grid": {"C": [1.0, 4.0, 16.0]}, "class_weight": "balanced"},
    "tfidf_svm": {"kind": "svm", "grid": {"C": [0.1, 0.5, 2.0]}, "class_weight": "balanced"},
    "tfidf_nb": {"kind": "nb", "grid": {"alpha": [0.01, 0.1, 0.5]}, "class_weight": "balanced"},
}

# Checkpoints were chosen after looking at each one (AUDIT.md, "Checkpoints"):
#   MARBERT      UBC-NLP/MARBERT — what sms_v2/marbert.py already uses. Dialectal
#                (Egyptian incl.) tweets, 100k WordPiece vocab, lowercases English.
#                Corpus max is 116 tokens, inside its 128-token pretraining length.
#                UBC-NLP/MARBERTv2 has the identical tokenizer; swap it in here.
#   AraBERT      aubmindlab/bert-base-arabertv02 — MSA, 64k vocab, NO Farasa
#                pre-segmentation needed (the "arabertv2" variants need it). The
#                "-twitter" variant was skipped: pretrained at 64 tokens only.
#   XLM-RoBERTa  FacebookAI/xlm-roberta-base — multilingual SentencePiece, cased,
#                0 UNK on this corpus; ~40% of messages are English or mixed.
TRANSFORMER_DEFAULTS = {
    "max_len": 160,            # corpus max is 145 tokens (AraBERT/XLM-R), so nothing truncates
    "batch_size": 32,          # fits a T4 (16 GB) at fp16 and max_len 160 for base models
    "eval_batch_size": 64,
    "epochs": 10,
    "lr": 3e-5,
    "weight_decay": 0.01,
    "warmup_ratio": 0.1,
    "grad_clip": 1.0,
    "early_stopping_patience": 3,      # epochs without val macro-F1 improvement
    "class_weighting": "balanced",     # "balanced" | "none"
    "fp16": True,                      # used only on CUDA
    "seed": 42,
}

TRANSFORMER_MODELS = {
    "marbert": {"checkpoint": "UBC-NLP/MARBERT"},
    "arabert": {"checkpoint": "aubmindlab/bert-base-arabertv02"},
    "xlm_roberta": {"checkpoint": "FacebookAI/xlm-roberta-base", "lr": 2e-5},
}

# Reference row: the existing v1 model's built-in transaction gate (binary only).
REFERENCE_MODELS = ["v1_gate"]

# --------------------------------------------------------------------- routing
# Probability a classifier must give "transaction" before a message is routed to
# extraction. None = plain argmax. Applies only to models with real probabilities;
# for the SVM the equivalent knob is SVM_MARGIN on its decision function.
TRANSACTION_THRESHOLD = None
SVM_MARGIN = None

# v1's rule, kept: a message the extractor finds no amount in yields no record.
REQUIRE_AMOUNT = True

# ===================================================================== new experiments
# Experiment 1 (cross-model combinations) and Experiment 2 (one joint model). Both are
# additive: they write to their own folders and never touch the runs above.
#
# Transformer EXTRACTORS (Stage 2) for Experiment 1. Architecture = sms_v2/marbert.py's
# extractor, unchanged: one encoder + BIO token head (17 labels) + type head (7) +
# channel head (7), loss = plain sum of the three cross-entropies. Trained on the gold
# transactions of the benchmark's TRAIN split, early-stopped on val full-record exact.
# Checkpoints are the classifiers' checkpoints, so the two stages of a combination start
# from the same pretrained encoder.
EXTRACTOR_MODELS = {
    "marbert": {"checkpoint": TRANSFORMER_MODELS["marbert"]["checkpoint"]},
    "arabert": {"checkpoint": TRANSFORMER_MODELS["arabert"]["checkpoint"]},
}
# Experiment 2: ONE model per run = one encoder with a classification head (binary or
# 6-class, the existing gold labels) AND the extractor's three heads, trained jointly.
JOINT_MODELS = {
    "marbert": {"checkpoint": TRANSFORMER_MODELS["marbert"]["checkpoint"]},
    "arabert": {"checkpoint": TRANSFORMER_MODELS["arabert"]["checkpoint"]},
}
# Hyperparameters on top of TRANSFORMER_DEFAULTS (same max_len, batch, lr, epochs,
# patience, warmup, fp16, seed as the classifiers).
EXTRACTOR_DEFAULTS = {"dropout": 0.1}
# Experiment 1 pairs these classifiers with these extractors (4 combinations x 2 exps).
COMBO_CLASSIFIERS = ["arabert", "marbert"]
COMBO_EXTRACTORS = ["arabert", "marbert"]
# Messages run one at a time through the LIVE pipeline (classifier -> extractor) to
# measure real per-SMS latency of each stage and to check it reproduces the cached result.
COMBO_LATENCY_SAMPLE = 50
