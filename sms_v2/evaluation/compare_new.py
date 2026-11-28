"""Tables, charts and REPORT_NEW.md for Experiment 1 (combinations) and Experiment 2
(joint models), next to the existing two-stage results they are compared with.

Reads only what the runners wrote; trains and predicts nothing. Writes ONLY to
results/<split>/summary_new/ (the existing summary/ is never touched):

  status.csv            every new run: done / missing (with the command that makes it)
  extractors.csv        standalone extraction (perfect Stage 1): v1_sklearn, marbert, arabert
  pipelines.csv         one row per end-to-end workflow and experiment:
                          combo   <clf> classifier -> <ext> extractor   (Exp 1)
                          joint   one model                              (Exp 2)
                          ref     <clf> classifier -> v1 extractor       (existing runs)
  classification.csv    the class decision of every workflow (Exp 1 rows = their classifier)
  REPORT_NEW.md, charts/*.png, confusion_matrices/*.png
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from benchmark import layout                           # noqa: E402
from benchmark import store                            # noqa: E402
from config import settings as S                       # noqa: E402
from evaluation import classification_metrics as CM    # noqa: E402
from evaluation.compare_models import (GRID, TEXT, TEXT2, _grouped, _md,  # noqa: E402
                                       _style, _write)

# Fixed colour per workflow, in the validated categorical order (identity follows the
# workflow, never its rank; every chart also carries value labels and a CSV table).
SERIES_COLOR = {"arabert__arabert": "#257de0", "arabert__marbert": "#f47230",
                "marbert__arabert": "#00b894", "marbert__marbert": "#f2a600",
                "joint_arabert": "#ee7fac", "joint_marbert": "#008a17"}
SERIES = list(SERIES_COLOR)


def label(series):
    if series.startswith("joint_"):
        return f"joint {series[6:]} (one model)"
    c, e = series.split("__")
    return f"{c} clf → {e} ext"


FIELDS = [("amount_acc", "amount"), ("currency_acc", "currency"),
          ("counterparty_acc", "counterparty"), ("date_acc", "date"),
          ("direction_acc", "direction"), ("type_acc", "type"),
          ("account_last4_acc", "account")]


def _e2e_row(m):
    h = m["headline"]
    acc = m["fields_over_all_gold_transactions"]["accuracy"]
    return {"e2e_exact_precision": m["e2e_full_exact_precision"],
            "e2e_exact_recall": m["e2e_full_exact_recall"],
            "e2e_exact_f1": m["e2e_full_exact_f1"],
            "missed_transactions": m["missed_transactions"],
            "missed_by_stage1": m["missed_by_reason"].get("rejected by stage 1", 0),
            "missed_no_amount": m["missed_by_reason"].get("stage 2: no amount found", 0),
            "false_records": m["false_records"],
            "false_records_by_class": m["false_records_by_class"],
            "amount_acc": h["amount_acc"], "currency_acc": h["currency_acc"],
            "counterparty_acc": acc["merchant"], "counterparty_f1": h["counterparty_f1"],
            "date_acc": h["date_acc"], "direction_acc": h["direction_acc"],
            "type_acc": h["type_acc"], "account_last4_acc": h["account_last4_acc"],
            "core_record_exact": h["core_record_exact"]}


def _cls_row(test):
    h = CM.headline(test)
    return {k: h[k] for k in ("accuracy", "macro_precision", "macro_recall", "macro_f1",
                              "transaction_precision", "transaction_recall")}


def collect(split):
    status, pipelines, classification, extractors, confusions = [], [], [], [], []
    # ---- standalone extractors
    v1 = os.path.join(store.stage_dir(split, "extraction"), "metrics.json")
    if os.path.exists(v1):
        m = store.read_json(v1)
        extractors.append({"extractor": "v1_sklearn", "n": m["n_test_gold_transactions"],
                           **m["headline"], "ms_per_sms": m["timing"]["ms_per_sms"]})
    for ext in S.EXTRACTOR_MODELS:
        d = layout.extractor_result_dir(split, ext)
        done = store.is_done(d)
        status.append({"run": f"extractor {ext}", "state": "done" if done else "MISSING",
                       "make_it": "" if done else
                       f"python bench.py extract-tf --models {ext} --splits {split}"})
        if done:
            m = store.read_json(os.path.join(d, "metrics.json"))
            extractors.append({"extractor": ext, "n": m["n_test_gold_transactions"],
                               **m["headline"], "ms_per_sms": m["timing"]["ms_per_sms"],
                               "best_epoch": m["train"]["best_epoch"],
                               "device": m["train"]["device"]})
    for exp in S.EXPERIMENTS:
        # ---- Exp 1
        for clf in S.COMBO_CLASSIFIERS:
            cdone = store.is_done(store.result_dir(split, exp, clf))
            status.append({"run": f"classifier {exp}/{clf} (existing)",
                           "state": "done" if cdone else "MISSING",
                           "make_it": "" if cdone else
                           f"python bench.py classify --models {clf} --experiments {exp}"})
            for ext in S.COMBO_EXTRACTORS:
                name = layout.combo_name(clf, ext)
                d = layout.combo_result_dir(split, exp, clf, ext)
                done = store.is_done(d)
                status.append({"run": f"combo {exp}/{name}", "state": "done" if done else "MISSING",
                               "make_it": "" if done else
                               f"python bench.py combos --experiments {exp} --classifiers {clf} "
                               f"--extractors {ext}"})
                if not done:
                    continue
                m = store.read_json(os.path.join(d, "metrics.json"))
                t = m["timing"]
                live = t.get("live") or {}
                pipelines.append({"experiment": exp, "kind": "combo", "series": name,
                                  "workflow": label(name),
                                  **_cls_row({**m["classification"],
                                              "weighted_f1": m["classification"]["weighted_f1"]}),
                                  **_e2e_row(m),
                                  "classification_ms": t["classifier_ms_per_sms_batch"],
                                  "extraction_ms": t["extractor_ms_per_sms_batch"],
                                  "pipeline_ms": t["pipeline_ms_per_sms"],
                                  "live_classification_ms": (live.get("classification_ms") or {}).get("median"),
                                  "live_extraction_ms": (live.get("extraction_ms_routed") or {}).get("median"),
                                  "live_pipeline_ms": (live.get("pipeline_ms") or {}).get("median"),
                                  "live_agreement": live.get("output_agreement_with_cached")})
        for clf in S.COMBO_CLASSIFIERS:
            rd = store.result_dir(split, exp, clf)
            if store.is_done(rd):
                m = store.read_json(os.path.join(rd, "metrics.json"))
                classification.append({"experiment": exp, "workflow": f"{clf} classifier "
                                       "(Exp 1, shared by its 2 combos)", **_cls_row(m["test"])})
                confusions.append((f"{exp}_{clf}_classifier", f"{clf} classifier — {exp}",
                                   m["test"]["confusion_matrix"]))
            ref = os.path.join(store.stage_dir(split, "end_to_end"), exp, clf)
            if store.is_done(ref):
                m = store.read_json(os.path.join(ref, "metrics.json"))
                pipelines.append({"experiment": exp, "kind": "ref", "series": f"{clf}__v1",
                                  "workflow": f"{clf} clf → v1 ext (existing)", **_e2e_row(m),
                                  "classification_ms": m["timing"]["classifier_ms_per_sms"],
                                  "extraction_ms": m["timing"]["extractor_ms_per_sms"],
                                  "pipeline_ms": m["timing"]["pipeline_ms_per_sms"]})
        # ---- Exp 2
        for model in S.JOINT_MODELS:
            d = layout.joint_result_dir(split, exp, model)
            done = store.is_done(d)
            status.append({"run": f"joint {exp}/{model}", "state": "done" if done else "MISSING",
                           "make_it": "" if done else
                           f"python bench.py joint --models {model} --experiments {exp}"})
            if not done:
                continue
            m = store.read_json(os.path.join(d, "metrics.json"))
            series = f"joint_{model}"
            pipelines.append({"experiment": exp, "kind": "joint", "series": series,
                              "workflow": label(series), **_cls_row(m["test"]),
                              **_e2e_row(m["end_to_end"]),
                              "classification_ms": None, "extraction_ms": None,
                              "pipeline_ms": m["timing"]["batch_ms_per_sms"],
                              "live_pipeline_ms": m["timing"]["single_ms_per_sms_median"]})
            classification.append({"experiment": exp, "workflow": label(series),
                                   **_cls_row(m["test"])})
            confusions.append((f"{exp}_{series}", f"{label(series)} — {exp}",
                               m["test"]["confusion_matrix"]))
    return status, extractors, pipelines, classification, confusions


# ------------------------------------------------------------------ charts
def charts(split, pipelines, confusions, out):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed: tables written, charts skipped")
        return []
    import evaluation.compare_models as CMP
    CMP.MODEL_COLOR.update(SERIES_COLOR)       # _grouped colours by series key
    cdir = os.path.join(out, "charts")
    os.makedirs(cdir, exist_ok=True)
    made = []

    def save(fig, name):
        p = os.path.join(cdir, name)
        fig.savefig(p, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        made.append(p)

    rows = [r for r in pipelines if r["kind"] in ("combo", "joint")]
    series = [s for s in SERIES if any(r["series"] == s for r in rows)]
    if not rows:
        return made

    def relabel(ax):
        h, lab = ax.get_legend_handles_labels()
        ax.legend(h, [label(x) for x in lab], frameon=False, fontsize=8, ncol=3,
                  loc="upper left", bbox_to_anchor=(0, -0.12))

    for metric, title, fmt, ylim in [
            ("e2e_exact_f1", "Full-record exact F1, end to end", "{:.2f}", (0, 1.08)),
            ("e2e_exact_precision", "Full-record exact precision, end to end", "{:.2f}", (0, 1.08)),
            ("e2e_exact_recall", "Full-record exact recall, end to end", "{:.2f}", (0, 1.08)),
            ("macro_f1", "Classification macro F1", "{:.2f}", (0, 1.08)),
            ("missed_transactions", "Missed transactions", "{:.0f}", None),
            ("false_records", "False financial records", "{:.0f}", None)]:
        fig, ax = plt.subplots(figsize=(9, 4))
        vals = {(r["experiment"], r["series"]): r.get(metric) for r in rows}
        _grouped(ax, S.EXPERIMENTS, series, vals, labels_fmt=fmt, ylim=ylim)
        relabel(ax)
        _style(ax, f"{title} — test, split '{split}'", metric)
        save(fig, f"{metric}.png")

    for exp in S.EXPERIMENTS:
        sub = [r for r in rows if r["experiment"] == exp]
        if not sub:
            continue
        fig, ax = plt.subplots(figsize=(11, 4))
        vals = {(f, r["series"]): r[k] for r in sub for k, f in FIELDS}
        _grouped(ax, [f for _, f in FIELDS], [s for s in series if any(r["series"] == s for r in sub)],
                 vals, ylim=(0, 1.08))
        relabel(ax)
        _style(ax, f"Field accuracy over ALL gold transactions (misses scored wrong) — {exp}",
               "accuracy")
        save(fig, f"field_accuracy_{exp}.png")

    # latency: stacked classification + routed share of extraction (combos); joint = one pass
    for exp in S.EXPERIMENTS:
        sub = [r for r in rows if r["experiment"] == exp]
        if not sub:
            continue
        fig, ax = plt.subplots(figsize=(9, 0.9 + 0.55 * len(sub)))
        names = [label(r["series"]) for r in sub]
        y = np.arange(len(sub))
        # joint: one pass, drawn as one solid segment
        clf = [(r["pipeline_ms"] if r["kind"] == "joint" else r["classification_ms"]) or 0
               for r in sub]
        rest = [(r["pipeline_ms"] or 0) - c for r, c in zip(sub, clf)]
        ax.barh(y, clf, 0.6, color=[SERIES_COLOR[r["series"]] for r in sub], edgecolor="white",
                linewidth=2, label="classification")
        ax.barh(y, rest, 0.6, left=clf, color=[SERIES_COLOR[r["series"]] for r in sub],
                alpha=0.45, edgecolor="white", linewidth=2, label="extraction (× share routed)")
        for yi, r in zip(y, sub):
            ax.text(r["pipeline_ms"] or 0, yi, f"  {r['pipeline_ms']:.2f} ms", va="center",
                    fontsize=7.5, color=TEXT2)
        ax.set_yticks(y)
        ax.set_yticklabels(names, fontsize=8)
        ax.invert_yaxis()
        ax.set_title(f"Pipeline time per SMS (batched; solid = classification, light = "
                     f"extraction; joint = one pass) — {exp}", fontsize=10, color=TEXT, loc="left")
        ax.tick_params(colors=TEXT2, labelsize=8, length=0)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(GRID)
        ax.xaxis.grid(True, color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)
        ax.set_xlabel("ms per SMS", fontsize=8, color=TEXT2)
        save(fig, f"latency_{exp}.png")

    mdir = os.path.join(out, "confusion_matrices")
    os.makedirs(mdir, exist_ok=True)
    for key, title, cm in confusions:
        labs, M = cm["labels"], np.array(cm["matrix"])
        k = len(labs)
        fig, ax = plt.subplots(figsize=(1.0 + 0.9 * k, 0.8 + 0.8 * k))
        norm = M / np.maximum(M.sum(1, keepdims=True), 1)
        ax.imshow(norm, cmap="Blues", vmin=0, vmax=1)
        for i in range(k):
            for j in range(k):
                ax.text(j, i, str(M[i, j]), ha="center", va="center", fontsize=8,
                        color="white" if norm[i, j] > 0.55 else TEXT)
        short = [lab.replace("_transaction", "").replace("_inquiry", "") for lab in labs]
        ax.set_xticks(range(k))
        ax.set_xticklabels(short, rotation=35, ha="right", fontsize=7)
        ax.set_yticks(range(k))
        ax.set_yticklabels(short, fontsize=7)
        ax.set_xlabel("predicted", fontsize=8, color=TEXT2)
        ax.set_ylabel("gold", fontsize=8, color=TEXT2)
        ax.set_title(title, fontsize=9, color=TEXT, loc="left")
        p = os.path.join(mdir, f"{key}.png")
        fig.savefig(p, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        made.append(p)
    return made


# ------------------------------------------------------------------ main
def run(split, make_charts=True):
    out = layout.summary_dir(split)
    os.makedirs(out, exist_ok=True)
    status, extractors, pipelines, classification, confusions = collect(split)
    _write(os.path.join(out, "status.csv"), status)
    _write(os.path.join(out, "extractors.csv"), extractors)
    _write(os.path.join(out, "pipelines.csv"), pipelines)
    _write(os.path.join(out, "classification.csv"), classification)
    made = charts(split, pipelines, confusions, out) if make_charts else []

    md = [f"# New experiments — split `{split}`\n",
          "Exp 1 = four classifier → extractor combinations (two separate models, run "
          "automatically one after the other). Exp 2 = one joint model (one forward pass "
          "gives the class and the record). `ref` rows = the existing classifier with the v1 "
          "extractor. All numbers are on the same fixed test set; field accuracy is over ALL "
          "gold transactions with misses scored wrong.\n",
          "## Status\n", _md(status, ["run", "state", "make_it"]),
          "## Standalone extraction (perfect Stage 1, gold test transactions)\n",
          _md(extractors, ["extractor", "n", "amount_acc", "currency_acc", "counterparty_f1",
                           "date_acc", "direction_acc", "type_acc", "account_last4_acc",
                           "full_record_exact", "ms_per_sms"]),
          "## Classification (the routing decision of each workflow)\n",
          _md(classification, ["experiment", "workflow", "accuracy", "macro_precision",
                               "macro_recall", "macro_f1", "transaction_precision",
                               "transaction_recall"]),
          "## End to end\n",
          _md(pipelines, ["experiment", "kind", "workflow", "e2e_exact_precision",
                          "e2e_exact_recall", "e2e_exact_f1", "missed_transactions",
                          "false_records", "amount_acc", "currency_acc", "counterparty_acc",
                          "date_acc", "direction_acc", "type_acc", "account_last4_acc"]),
          "## Time per SMS (ms)\n",
          "Batched = whole test set at once; live = one SMS at a time through the real pipeline "
          "(median). Pipeline (batched) = classification + share routed × extraction.\n\n",
          _md(pipelines, ["experiment", "workflow", "classification_ms", "extraction_ms",
                          "pipeline_ms", "live_classification_ms", "live_extraction_ms",
                          "live_pipeline_ms", "live_agreement"]),
          "\nCharts: " + ", ".join(os.path.relpath(p, out).replace(os.sep, "/") for p in made)
          + "\n"]
    with open(os.path.join(out, "REPORT_NEW.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"summary_new -> {out}  ({sum(s['state'] == 'done' for s in status)}/{len(status)} "
          f"runs done, {len(made)} charts)")
    return {"status": status, "extractors": extractors, "pipelines": pipelines}
