"""Standalone Stage-2 evaluation, independent of any classifier.

  1. fit the extractor (v1) on the split's TRAINING records;
  2. run it on EVERY test message and store the output per id
     (results/<split>/extraction/predictions.jsonl). The end-to-end evaluation
     reuses these, because the extractor's output for a message does not
     depend on which classifier routed it there;
  3. score it on the GOLD transactions of the test set only — "if Stage 1 were
     perfect, how good is extraction?" This is NOT pipeline performance;
     see run_e2e.py for that.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from benchmark import data as D                       # noqa: E402
from benchmark import splits as SP                    # noqa: E402
from benchmark import store                           # noqa: E402
from config import settings as S                      # noqa: E402
from evaluation import extraction_metrics as EM       # noqa: E402
from extraction.base import to_v1                     # noqa: E402
from extraction.v1_extractor import V1Extractor       # noqa: E402

EXTRACTOR = "v1_sklearn"


def extractor_dir(split):
    return os.path.join(store.root(), "models", split, "extractor", EXTRACTOR)


def load_predictions(split):
    path = os.path.join(store.stage_dir(split, "extraction"), "predictions.jsonl")
    if not os.path.exists(path):
        raise FileNotFoundError(f"no extraction predictions for {split}; run  "
                                f"python bench.py extract --splits {split}")
    with open(path, encoding="utf-8") as f:
        return {r["id"]: r for r in map(json.loads, f)}


def run(split, overwrite=False, log=print):
    rdir = store.stage_dir(split, "extraction")
    if store.is_done(rdir) and not overwrite:
        log(f"skip extraction/{split}: already complete. Pass --overwrite to redo it.")
        return store.read_json(os.path.join(rdir, "metrics.json"))
    store.clear(rdir)

    records = D.load()
    sides, meta = SP.load(records, split)
    tr, te = sides["train"], sides["test"]
    with store.Run("extract", split=split, extractor=EXTRACTOR) as run_:
        log(f"=== extraction / {split}: fit {EXTRACTOR} on {len(tr)} train records")
        ex = V1Extractor().fit(tr)
        mdir = extractor_dir(split)
        ex.save(mdir)

        ex.extract_many([r["sms"] for r in te[:5]])          # warm-up
        t0 = time.perf_counter()
        outs = ex.extract_many([r["sms"] for r in te])
        per_sms_ms = 1000 * (time.perf_counter() - t0) / max(len(te), 1)

        os.makedirs(rdir, exist_ok=True)
        tmp = os.path.join(rdir, "predictions.jsonl.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            for r, o in zip(te, outs):
                f.write(json.dumps({"id": r["id"], "output": o}, ensure_ascii=False) + "\n")
        os.replace(tmp, os.path.join(rdir, "predictions.jsonl"))

        gold_tx = [(r, o) for r, o in zip(te, outs) if r["expected"]["is_transaction"]]
        # standalone: the extractor's own "no amount" rejection still counts as a miss
        pairs = [(r["expected"], to_v1(o) if o["extraction_ok"] else None) for r, o in gold_tx]
        fs = EM.field_scores(pairs)
        no_record = sum(1 for _, o in gold_tx if not o["extraction_ok"])
        by_sender = {}
        for sender in sorted({r["sender"] for r, _ in gold_tx}):
            sub = [(r["expected"], to_v1(o) if o["extraction_ok"] else None)
                   for r, o in gold_tx if r["sender"] == sender]
            by_sender[sender] = EM.headline(EM.field_scores(sub)) | {"n": len(sub)}

        metrics = {"split": split, "extractor": EXTRACTOR, "n_train": len(tr),
                   "n_test_gold_transactions": len(gold_tx),
                   "no_record_on_gold_transactions": no_record,
                   "fields": fs, "headline": EM.headline(fs), "by_sender": by_sender,
                   "timing": {"fit_time_s": ex.fit_time_s, "ms_per_sms": per_sms_ms},
                   "model_size_mb": store.dir_size(mdir) / 2 ** 20,
                   "reference_field": "extracted by rule, not evaluated: the corpus has "
                                      "no gold reference ids",
                   "data_hash": meta["data_hash"], "finished": store.now()}
        store.write_json(os.path.join(rdir, "metrics.json"), metrics)
        store.mark_done(rdir)
        h = metrics["headline"]
        run_.info.update(full_record_exact=h["full_record_exact"])
        log(f"    {len(gold_tx)} gold transactions: amount {h['amount_acc']:.3f}  currency "
            f"{h['currency_acc']:.3f}  counterparty F1 {h['counterparty_f1']:.3f}  date "
            f"{h['date_acc']:.3f}  direction {h['direction_acc']:.3f}  full {h['full_record_exact']:.3f}"
            f"  | {per_sms_ms:.2f} ms/SMS")
    return metrics
