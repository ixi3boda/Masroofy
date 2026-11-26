"""What has been run, what failed, what is still missing — from the result
markers and the experiment log, so nothing incomplete passes unnoticed."""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from benchmark import store                       # noqa: E402
from classification import registry               # noqa: E402
from config import settings as S                  # noqa: E402


def _last_event(log, **ident):
    hits = [e for e in log if all(e.get(k) == v for k, v in ident.items())]
    return hits[-1] if hits else None


def status(split):
    log = store.read_log()
    runs = []
    for exp in S.EXPERIMENTS:
        for model in registry.ALL:
            if model in registry.REFERENCE and exp != "binary":
                continue
            d = store.result_dir(split, exp, model)
            ev = _last_event(log, kind="classify", split=split, experiment=exp, model=model)
            if store.is_done(d):
                state, detail = "done", ""
            elif ev and ev["event"] == "failed":
                state, detail = "FAILED", ev.get("error", "")[:160]
            elif ev and ev["event"] in ("start", "interrupted"):
                ck = os.path.join(store.model_dir(split, exp, model), "checkpoints", "last")
                state = "INCOMPLETE"
                detail = "resumable from checkpoint" if os.path.isdir(ck) else "restarts"
            else:
                state, detail = "not run", ""
            runs.append({"kind": "classify", "experiment": exp, "model": model,
                         "state": state, "detail": detail})
    for kind, d in [("extract", store.stage_dir(split, "extraction"))]:
        runs.append({"kind": kind, "experiment": "-", "model": "v1_sklearn",
                     "state": "done" if store.is_done(d) else "not run", "detail": ""})
    return {"split": split, "runs": runs,
            "counts": {s: sum(r["state"] == s for r in runs)
                       for s in ("done", "FAILED", "INCOMPLETE", "not run")}}


def print_status(splits):
    for split in splits:
        st = status(split)
        print(f"\nsplit {split}: {st['counts']}")
        for r in st["runs"]:
            print(f"  {r['kind']:9s} {r['experiment']:10s} {r['model']:12s} {r['state']:10s} "
                  f"{r['detail']}")
