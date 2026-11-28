"""Local SMS inference: AraBERT 6-class classifier -> MARBERT extractor, CPU only, no cloud.

    python test_sms.py                      # type / paste an SMS, Enter; empty line quits
    python test_sms.py --sms "..." --sms "..."

Both models are loaded ONCE from this folder (arabert_classifier/, marbert_extractor/), with
Hugging Face downloads switched off. Preprocessing, tokenization, label mappings and decoding are
the experiments' own code in ../sms_v2 (nothing is re-implemented here):
  * classification.registry.load  + .predict_with_scores   (the classifier, as in the benchmark)
  * extraction.loader.load_extractor + .extract_many        (the extractor, as in the benchmark)
  * routing rule from sms_pipeline.SmsPipeline: only class "transaction" is extracted, and a
    transaction with no amount found gives no record (config.settings.REQUIRE_AMOUNT).

From other Python code (app integration):
    from test_sms import load_models, predict
    models = load_models()
    predict(models, "تم خصم 250 جنيه ...")   # -> dict, see predict()
"""
import os

# no cloud, no TensorFlow: set BEFORE transformers is imported
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import argparse      # noqa: E402
import json          # noqa: E402
import sys           # noqa: E402
import time          # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.path.join(HERE, "..", "sms_v2"))      # the experiments' code
CLASSIFIER_DIR = os.path.join(HERE, "arabert_classifier")
EXTRACTOR_DIR = os.path.join(HERE, "marbert_extractor")

# extractor "direction" is derived from the predicted type (extraction.base.DIRECTION)
DIRECTION_WORD = {"debit": "deducted", "credit": "added", None: None}


def load_models(classifier_dir=CLASSIFIER_DIR, extractor_dir=EXTRACTOR_DIR):
    """Load both models once, on CPU. -> dict with the classifier and the extractor."""
    for d, f in ((classifier_dir, "classifier.json"), (extractor_dir, "extractor.json")):
        if not os.path.exists(os.path.join(d, f)):
            raise SystemExit(f"{f} not found in {d}: the model files are missing from sms_model/")
    if not os.path.isdir(CODE):
        raise SystemExit(f"experiment code not found at {CODE} (test_sms.py reuses sms_v2/)")
    if CODE not in sys.path:
        sys.path.insert(0, CODE)
    from classification import registry
    from config import labels as L
    from config import settings as S
    from extraction.loader import load_extractor

    clf = registry.load(classifier_dir, device="cpu")
    ext = load_extractor(extractor_dir, device="cpu")
    if L.TRANSACTION not in clf.classes:
        raise SystemExit(f"{classifier_dir} has no '{L.TRANSACTION}' class: {clf.classes}")
    models = {"classifier": clf, "extractor": ext, "transaction": L.TRANSACTION,
              "require_amount": S.REQUIRE_AMOUNT}
    warm = "تم خصم 100 جنيه من حسابك"      # first call of each model allocates buffers: not timed
    clf.predict_with_scores([warm])
    ext.extract_many([warm])
    return models


def predict(models, sms):
    """One SMS -> {is_transaction, type, amount, currency, direction, merchant, class, reason, timing_ms}."""
    clf, ext, TX = models["classifier"], models["extractor"], models["transaction"]
    t0 = time.perf_counter()
    labels, scores = clf.predict_with_scores([sms])
    t1 = time.perf_counter()
    label = labels[0]
    out = {"is_transaction": False, "type": None, "amount": None, "currency": None,
           "direction": None, "merchant": None, "class": label,
           "transaction_probability": round(float(scores[0][clf.classes.index(TX)]), 4),
           "reason": None}
    extraction_ms = "skipped"
    if label != TX:
        out["reason"] = f"classified as {label}"
    else:
        rec = ext.extract_many([sms])[0]
        extraction_ms = round((time.perf_counter() - t1) * 1000, 1)
        if not rec["extraction_ok"] and models["require_amount"]:
            out["reason"] = "extractor found no amount: " + (rec.get("extraction_note") or "")
        else:
            out.update(is_transaction=True, type=rec["type"], amount=rec["amount"],
                       currency=rec["currency"], direction=DIRECTION_WORD.get(rec["direction"]),
                       merchant=rec["counterparty"])
    t2 = time.perf_counter()
    out["timing_ms"] = {"classification": round((t1 - t0) * 1000, 1), "extraction": extraction_ms,
                        "total": round((t2 - t0) * 1000, 1)}
    return out


def main():
    ap = argparse.ArgumentParser(description="AraBERT classifier -> MARBERT extractor, local CPU")
    ap.add_argument("--sms", action="append", help="an SMS (repeatable); without it: interactive")
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")          # Arabic on the Windows console
    t = time.time()
    models = load_models()
    print(f"models loaded from {HERE} in {time.time() - t:.1f} s (CPU)", file=sys.stderr)

    def show(sms):
        print(json.dumps({"sms": sms, **predict(models, sms)}, ensure_ascii=False, indent=1))

    if a.sms:
        for s in a.sms:
            show(s)
        return
    print("Paste an SMS and press Enter (empty line quits).", file=sys.stderr)
    while True:
        try:
            line = input("\nsms> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            break
        show(line)


if __name__ == "__main__":
    main()
