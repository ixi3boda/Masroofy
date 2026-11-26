"""Collect every finished run on a split into comparison tables and charts.

Reads only what the runners wrote (metrics.json, predictions.csv); trains and
predicts nothing, so it is safe to re-run at any time. Writes to
results/<split>/summary/:

  classification.csv / .json     one row per (experiment, model), test-set numbers
                                 + val macro F1 + 95% group-bootstrap intervals
  per_class.csv                  per-class precision / recall / F1 (test)
  extraction.csv                 standalone extraction (perfect Stage 1)
  end_to_end.csv                 full pipeline, Stage-1 errors included
  experiment_comparison.csv      Experiment A vs B, same model, side by side
  status.json                    done / failed / missing runs
  REPORT.md                      all of the above as markdown
  charts/*.png, confusion_matrices/*.png

Why bootstrap intervals: test messages come in templates, and a whole template
is right or wrong together (one SVM miss can be 28 messages). So intervals
resample TEMPLATE GROUPS with replacement, not messages; message-level resampling
would claim far more certainty than the data holds.
"""
import csv
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from benchmark import data as D                        # noqa: E402
from benchmark import splits as SP                     # noqa: E402
from benchmark import status as ST                     # noqa: E402
from benchmark import store                            # noqa: E402
from classification import registry                    # noqa: E402
from config import labels as L                         # noqa: E402
from config import settings as S                       # noqa: E402
from evaluation import classification_metrics as CM    # noqa: E402

N_BOOT = 1000

# Fixed colour per model (validated categorical order, light surface). Colour
# follows the model, never its rank, so every chart agrees.
MODEL_COLOR = {"tfidf_lr": "#257de0", "tfidf_svm": "#f47230", "tfidf_nb": "#00b894",
               "marbert": "#f2a600", "arabert": "#ee7fac", "xlm_roberta": "#008a17",
               "v1_gate": "#6a4ce2", "oracle": "#666666"}
TEXT, TEXT2, GRID = "#191919", "#666666", "#e5e5e5"


# ------------------------------------------------------------------ loading
def _read_preds(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def bootstrap(rows, groups, classes, n=N_BOOT, seed=0):
    """95% intervals for macro F1, tx recall, tx precision by group resampling."""
    from sklearn.metrics import f1_score
    by_g = {}
    for r in rows:
        by_g.setdefault(groups[int(r["id"])], []).append(r)
    keys = list(by_g)
    rng = np.random.default_rng(seed)
    stats = {"macro_f1": [], "transaction_recall": [], "transaction_precision": []}
    for _ in range(n):
        sample = [r for k in rng.choice(len(keys), len(keys)) for r in by_g[keys[k]]]
        g = [r["gold"] for r in sample]
        p = [r["pred"] for r in sample]
        stats["macro_f1"].append(f1_score(g, p, labels=classes, average="macro", zero_division=0))
        rt = CM.routing(g, p)
        for k in ("transaction_recall", "transaction_precision"):
            if rt[k] is not None:
                stats[k].append(rt[k])
    return {k: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] if v else None
            for k, v in stats.items()}


def collect(split):
    records = D.load()
    sides, _ = SP.load(records, split)
    groups = {r["id"]: r["template_id"] for r in sides["test"]}
    rows, per_class = [], []
    for exp in S.EXPERIMENTS:
        for model in registry.ALL:
            rdir = store.result_dir(split, exp, model)
            if not store.is_done(rdir):
                continue
            m = store.read_json(os.path.join(rdir, "metrics.json"))
            h = CM.headline(m["test"])
            ci = bootstrap(_read_preds(os.path.join(rdir, "predictions.csv")), groups,
                           m["classes"])
            t = m["timing"]
            rows.append({"experiment": exp, "model": model, "family": m["family"],
                         **{k: h[k] for k in h},
                         "macro_f1_ci95": ci["macro_f1"],
                         "transaction_recall_ci95": ci["transaction_recall"],
                         "transaction_precision_ci95": ci["transaction_precision"],
                         "val_macro_f1": m["val"]["macro_f1"],
                         "train_time_s": t["train_time_s"],
                         "infer_ms_per_sms_batch": t["batch_ms_per_sms"],
                         "infer_ms_per_sms_single": t["single_ms_per_sms_median"],
                         "model_size_mb": m["model_size_mb"],
                         "n_parameters": m.get("n_parameters"),
                         "peak_gpu_mem_train_mb": m["train"].get("peak_gpu_mem_train_mb"),
                         "peak_gpu_mem_infer_mb": t.get("peak_gpu_mem_infer_mb"),
                         "process_rss_mb": t.get("process_rss_mb"),
                         "score_type": m["score_type"],
                         "device": m["train"].get("device", "cpu"),
                         "selected": m["train"].get("selected") or
                                     ({"best_epoch": m["train"]["best_epoch"]}
                                      if "best_epoch" in m["train"] else None),
                         "_confusion": m["test"]["confusion_matrix"]})
            for c, v in m["test"]["per_class"].items():
                per_class.append({"experiment": exp, "model": model, "class": c, **v})
    return rows, per_class


def collect_e2e(split):
    out = []
    base = store.stage_dir(split, "end_to_end")
    for exp in ["oracle"] + S.EXPERIMENTS:
        for model in ["oracle"] + registry.ALL:
            d = os.path.join(base, exp, model)
            if not store.is_done(d):
                continue
            m = store.read_json(os.path.join(d, "metrics.json"))
            h = m["headline"]
            out.append({"experiment": exp, "model": model,
                        "e2e_full_exact_f1": m["e2e_full_exact_f1"],
                        "e2e_full_exact_recall": m["e2e_full_exact_recall"],
                        "e2e_full_exact_precision": m["e2e_full_exact_precision"],
                        "missed_transactions": m["missed_transactions"],
                        "missed_by_stage1": m["missed_by_reason"].get("rejected by stage 1", 0),
                        "missed_by_stage2": m["missed_by_reason"].get("stage 2: no amount found", 0),
                        "false_records": m["false_records"],
                        "false_records_by_class": m["false_records_by_class"],
                        "amount_acc": h["amount_acc"], "currency_acc": h["currency_acc"],
                        "counterparty_f1": h["counterparty_f1"], "date_acc": h["date_acc"],
                        "direction_acc": h["direction_acc"],
                        "core_record_exact": h["core_record_exact"],
                        "pipeline_ms_per_sms": m["timing"]["pipeline_ms_per_sms"],
                        "share_routed": m["timing"]["share_routed"]})
    return out


# ------------------------------------------------------------------ writing
def _cell(v):
    if isinstance(v, float):
        return f"{v:.4f}"
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    return "" if v is None else str(v)


def _write(path, rows, cols=None):
    if not rows:
        return
    cols = cols or [k for k in rows[0] if not k.startswith("_")]
    store.write_csv(path, cols, [[_cell(r.get(c)) for c in cols] for r in rows])


def _md(rows, cols, fmt=None):
    if not rows:
        return "_no completed runs_\n"
    fmt = fmt or {}
    out = "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n"
    for r in rows:
        cells = []
        for c in cols:
            v = r.get(c)
            if c in fmt and v is not None:
                v = fmt[c](v)
            elif isinstance(v, float):
                v = f"{v:.3f}"
            elif isinstance(v, list) and len(v) == 2 and all(isinstance(x, float) for x in v):
                v = f"{v[0]:.3f}–{v[1]:.3f}"
            cells.append("" if v is None else str(v))
        out += "| " + " | ".join(cells) + " |\n"
    return out


# ------------------------------------------------------------------ charts
def _style(ax, title, ylabel):
    ax.set_title(title, color=TEXT, fontsize=11, loc="left")
    ax.set_ylabel(ylabel, color=TEXT2, fontsize=9)
    ax.tick_params(colors=TEXT2, labelsize=8, length=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.yaxis.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def _grouped(ax, groups, series, values, labels_fmt="{:.2f}", ylim=None):
    """groups on x; one bar per series (model), coloured by model, value-labelled."""
    n = len(series)
    width = 0.8 / max(n, 1)
    x = np.arange(len(groups))
    for i, s in enumerate(series):
        vals = [values.get((g, s)) for g in groups]
        pos = x - 0.4 + width * (i + 0.5)
        h = [v if v is not None else 0 for v in vals]
        ax.bar(pos, h, width * 0.92, color=MODEL_COLOR.get(s, "#9c9c9c"), label=s,
               edgecolor="white", linewidth=1)
        for p, v in zip(pos, vals):
            if v is not None:
                ax.text(p, v, labels_fmt.format(v), ha="center", va="bottom", fontsize=6.5,
                        color=TEXT2)
    ax.set_xticks(x)
    ax.set_xticklabels(groups)
    if ylim:
        ax.set_ylim(*ylim)
    ax.legend(frameon=False, fontsize=8, ncol=min(n, 4), loc="upper left",
              bbox_to_anchor=(0, -0.12))


def charts(split, rows, per_class, e2e, out):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed: tables written, charts skipped")
        return []
    cdir = os.path.join(out, "charts")
    os.makedirs(cdir, exist_ok=True)
    made = []
    models = [m for m in registry.ALL if any(r["model"] == m for r in rows)]

    def save(fig, name):
        p = os.path.join(cdir, name)
        fig.savefig(p, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        made.append(p)

    # 1-2. accuracy and macro F1, grouped by experiment
    for metric, title in [("accuracy", "Accuracy (test)"), ("macro_f1", "Macro F1 (test)"),
                          ("transaction_recall", "Transaction recall (test) — missed = lost record"),
                          ("transaction_precision",
                           "Transaction precision (test) — low = fabricated records")]:
        fig, ax = plt.subplots(figsize=(8, 4))
        vals = {(r["experiment"], r["model"]): r[metric] for r in rows}
        _grouped(ax, S.EXPERIMENTS, models, vals, ylim=(0, 1.08))
        _style(ax, f"{title} — split '{split}'", metric)
        save(fig, f"{metric}.png")

    # 3. per-class F1, multiclass
    pcs = [p for p in per_class if p["experiment"] == "multiclass"]
    if pcs:
        mc_models = [m for m in models if any(p["model"] == m for p in pcs)]
        fig, ax = plt.subplots(figsize=(10, 4))
        _grouped(ax, list(L.CLASSES), mc_models,
                 {(p["class"], p["model"]): p["f1"] for p in pcs}, ylim=(0, 1.08))
        _style(ax, f"Per-class F1, multi-class (test) — split '{split}'", "F1")
        ax.tick_params(axis="x", labelsize=7)
        save(fig, "per_class_f1_multiclass.png")
    pcb = [p for p in per_class if p["experiment"] == "binary"]
    if pcb:
        b_models = [m for m in models if any(p["model"] == m for p in pcb)]
        fig, ax = plt.subplots(figsize=(7, 4))
        _grouped(ax, list(L.BINARY_CLASSES), b_models,
                 {(p["class"], p["model"]): p["f1"] for p in pcb}, ylim=(0, 1.08))
        _style(ax, f"Per-class F1, binary (test) — split '{split}'", "F1")
        save(fig, "per_class_f1_binary.png")

    # 4-5. training time and inference time (log scale: ms vs minutes)
    for metric, title, fmt in [("train_time_s", "Training time", "{:.1f}s"),
                               ("infer_ms_per_sms_batch", "Inference time per SMS (batched)",
                                "{:.2f}ms")]:
        fig, ax = plt.subplots(figsize=(8, 4))
        vals = {(r["experiment"], r["model"]): r[metric] for r in rows if r[metric]}
        _grouped(ax, S.EXPERIMENTS, models, vals, labels_fmt=fmt)
        ax.set_yscale("log")
        _style(ax, f"{title} — split '{split}' (log scale; device in classification.csv)",
               metric)
        save(fig, f"{metric}.png")

    # 6. end-to-end: missed vs false records
    if e2e:
        fig, axes = plt.subplots(1, 2, figsize=(11, 4))
        e2e_models = ["oracle"] + models
        for ax, metric, title in [(axes[0], "missed_transactions", "Missed transactions"),
                                  (axes[1], "false_records", "False financial records")]:
            vals = {(r["experiment"], r["model"]): r[metric] for r in e2e}
            _grouped(ax, ["oracle"] + S.EXPERIMENTS, e2e_models, vals, labels_fmt="{:.0f}")
            _style(ax, f"{title} (end-to-end, test)", "messages")
        save(fig, "end_to_end_errors.png")
        fig, ax = plt.subplots(figsize=(8, 4))
        _grouped(ax, ["oracle"] + S.EXPERIMENTS, e2e_models,
                 {(r["experiment"], r["model"]): r["e2e_full_exact_recall"] for r in e2e},
                 ylim=(0, 1.08))
        _style(ax, "Exact records / gold transactions (end-to-end, test)", "share")
        save(fig, "end_to_end_exact_recall.png")

    # 7. confusion matrices
    mdir = os.path.join(out, "confusion_matrices")
    os.makedirs(mdir, exist_ok=True)
    for r in rows:
        cm = r["_confusion"]
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
        ax.set_title(f"{r['model']} — {r['experiment']} ({split})", fontsize=9,
                     color=TEXT, loc="left")
        p = os.path.join(mdir, f"{r['experiment']}_{r['model']}.png")
        fig.savefig(p, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        made.append(p)
    return made


# ------------------------------------------------------------------ main
def run(split, make_charts=True):
    out = store.stage_dir(split, "summary")
    os.makedirs(out, exist_ok=True)
    rows, per_class = collect(split)
    e2e = collect_e2e(split)
    ex_path = os.path.join(store.stage_dir(split, "extraction"), "metrics.json")
    extraction = store.read_json(ex_path) if os.path.exists(ex_path) else None
    status = ST.status(split)

    _write(os.path.join(out, "classification.csv"), rows)
    store.write_json(os.path.join(out, "classification.json"),
                     [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows])
    _write(os.path.join(out, "per_class.csv"), per_class)
    _write(os.path.join(out, "end_to_end.csv"), e2e)
    store.write_json(os.path.join(out, "end_to_end.json"), e2e)
    if extraction:
        _write(os.path.join(out, "extraction.csv"),
               [{"extractor": extraction["extractor"],
                 "n_gold_transactions": extraction["n_test_gold_transactions"],
                 **extraction["headline"], "ms_per_sms": extraction["timing"]["ms_per_sms"]}])
    # Experiment A vs B, per model
    cmp_rows = []
    for model in registry.ALL:
        a = next((r for r in rows if r["model"] == model and r["experiment"] == "binary"), None)
        b = next((r for r in rows if r["model"] == model and r["experiment"] == "multiclass"), None)
        ea = next((r for r in e2e if r["model"] == model and r["experiment"] == "binary"), None)
        eb = next((r for r in e2e if r["model"] == model and r["experiment"] == "multiclass"), None)
        if not (a or b):
            continue
        row = {"model": model}
        for tag, r, e in (("A_binary", a, ea), ("B_multiclass", b, eb)):
            row[f"{tag}_tx_recall"] = r and r["transaction_recall"]
            row[f"{tag}_tx_precision"] = r and r["transaction_precision"]
            row[f"{tag}_missed"] = e and e["missed_transactions"]
            row[f"{tag}_false_records"] = e and e["false_records"]
            row[f"{tag}_e2e_exact_recall"] = e and e["e2e_full_exact_recall"]
            row[f"{tag}_pipeline_ms"] = e and e["pipeline_ms_per_sms"]
        cmp_rows.append(row)
    _write(os.path.join(out, "experiment_comparison.csv"), cmp_rows)
    store.write_json(os.path.join(out, "status.json"), status)

    made = charts(split, rows, per_class, e2e, out) if make_charts else []

    # ---- REPORT.md
    sp = SP.load(D.load(), split)[1]
    md = [f"# Stage-1 benchmark — split `{split}`\n",
          f"Generated {store.now()} from the saved runs under `{store.root()}`. "
          "Every number is on the untouched TEST set unless the column says `val`.\n",
          "## Data\n", _md([{"side": s, **{"n": v["n"]}, **v["multiclass"]}
                           for s, v in sp["summary"].items()],
                          ["side", "n"] + list(L.CLASSES)),
          f"\nGrouping: {json.dumps(sp['grouping'])}\n",
          "\n## Classification\n",
          "Intervals are 95% bootstrap over TEMPLATE groups (see compare_models.py).\n\n",
          _md(rows, ["experiment", "model", "accuracy", "macro_f1", "macro_f1_ci95",
                     "weighted_f1", "transaction_recall", "transaction_recall_ci95",
                     "transaction_precision", "false_accept_rate", "missed_transactions",
                     "false_transactions", "val_macro_f1"]),
          "\n## Cost\n",
          _md(rows, ["experiment", "model", "device", "train_time_s", "infer_ms_per_sms_batch",
                     "infer_ms_per_sms_single", "model_size_mb", "n_parameters",
                     "peak_gpu_mem_train_mb", "score_type", "selected"],
              fmt={"n_parameters": lambda v: f"{v / 1e6:.0f}M"}),
          "\n## Per-class F1 (multi-class)\n"]
    mc = {}
    for p in per_class:
        if p["experiment"] == "multiclass":
            mc.setdefault(p["model"], {"model": p["model"]})[p["class"]] = p["f1"]
    md.append(_md(list(mc.values()), ["model"] + list(L.CLASSES)))
    if extraction:
        md += ["\n## Standalone extraction (perfect Stage 1, gold transactions only)\n",
               _md([{"extractor": extraction["extractor"],
                     "n": extraction["n_test_gold_transactions"], **extraction["headline"]}],
                   ["extractor", "n", "amount_acc", "currency_acc", "counterparty_precision",
                    "counterparty_recall", "counterparty_f1", "date_acc", "direction_acc",
                    "account_last4_acc", "core_record_exact", "full_record_exact"]),
               "\n`reference` is extracted but not evaluated: the corpus has no gold ids.\n"]
    md += ["\n## End-to-end (Stage-1 errors included)\n",
           "Missed = gold transaction with no record; false record = non-transaction that "
           "produced one. Field accuracies are over ALL gold transactions, misses scored "
           "as wrong.\n\n",
           _md(e2e, ["experiment", "model", "missed_transactions", "missed_by_stage1",
                     "missed_by_stage2", "false_records", "e2e_full_exact_recall",
                     "e2e_full_exact_precision", "amount_acc", "counterparty_f1", "date_acc",
                     "direction_acc", "pipeline_ms_per_sms"]),
           "\n## Experiment A (binary) vs B (multi-class)\n",
           _md(cmp_rows, list(cmp_rows[0]) if cmp_rows else ["model"]),
           "\n## Run status\n",
           _md(status["runs"], ["kind", "experiment", "model", "state", "detail"]),
           "\n## Charts\n"]
    md += [f"- `{os.path.relpath(p, out)}`\n" for p in made]
    with open(os.path.join(out, "REPORT.md"), "w", encoding="utf-8") as f:
        f.write("".join(md))
    print(f"summary for {split}: {len(rows)} classifier runs, {len(e2e)} e2e rows, "
          f"{len(made)} charts -> {out}")
    return {"classification": rows, "per_class": per_class, "e2e": e2e, "status": status}
