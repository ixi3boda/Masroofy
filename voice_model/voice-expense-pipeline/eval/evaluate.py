"""Evaluate the pipeline on the labeled dataset and write a Markdown report.

Examples:
    python eval/evaluate.py --mode text --extractor rules
    python eval/evaluate.py --mode text --compare                 # rules vs hybrid
    python eval/evaluate.py --mode audio --manifest eval/audio/synthetic/manifest.csv
    python eval/evaluate.py --mode audio --manifest eval/audio/synthetic/manifest.csv --compare   # ar vs auto

Outputs (in results/<timestamp>/):
    report.md        tables + environment + which column answers which proposal question
    predictions.csv  one row per example (expected vs predicted for every field)
    errors.csv       only wrong fields, with the transcript
WHY text mode exists: it measures extraction alone, fully offline, in seconds.
Audio mode adds ASR errors and real latency.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.metrics import (  # noqa: E402
    EVAL_FIELDS,
    KEY_FIELDS,
    aggregate,
    cer,
    latency_stats,
    score_record,
    wer,
)
from voice_expense.asr import AudioValidationError, _cuda_available  # noqa: E402
from voice_expense.config import get_settings  # noqa: E402
from voice_expense.pipeline import process_audio, process_text  # noqa: E402

DEFAULT_DATASET = ROOT / "eval" / "dataset" / "phrases.jsonl"


def _setup_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass


def load_dataset(path: Path) -> list[dict[str, Any]]:
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_manifest(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _pred_dict(draft: Any) -> dict[str, Any]:
    return {
        "transaction_type": draft.transaction_type,
        "amount": float(draft.amount) if draft.amount is not None else None,
        "currency": draft.currency,
        "merchant": draft.merchant,
        "category": draft.category,
        "date": draft.date.isoformat(),
        "time": draft.time,
        "payment_method": draft.payment_method,
    }


def run_once(examples: list[dict[str, Any]], mode: str, extractor: str, manifest: Optional[list[dict[str, str]]],
             asr_language: Optional[str], asr_backend: Optional[str]) -> dict[str, Any]:
    """Run one configuration. Returns records + timing lists."""
    by_id = {e["id"]: e for e in examples}
    items: list[tuple[dict[str, Any], Optional[str]]] = []
    if mode == "text":
        items = [(e, None) for e in examples]
    else:
        assert manifest is not None
        for row in manifest:
            ex = by_id.get(row.get("id", ""))
            if ex is None:
                continue
            p = row.get("path", "")
            audio_path = p if os.path.isabs(p) else str((ROOT / p).resolve())
            items.append((ex, audio_path))
    if not items:
        return {"records": [], "rows": [], "lat": {}, "model_load_ms": 0.0, "asr": {}, "skipped": 0}

    # Warm-up (excluded from statistics): loads models, fills caches.
    warm_ex, warm_path = items[0]
    try:
        if mode == "text":
            process_text(warm_ex["text"], now=warm_ex["reference_time"], extractor=extractor)
        else:
            process_audio(warm_path, now=warm_ex["reference_time"], language=asr_language, extractor=extractor,  # type: ignore[arg-type]
                          asr_backend=asr_backend)
    except AudioValidationError:
        pass

    records, rows = [], []
    lat: dict[str, list[float]] = {"asr_ms": [], "extract_ms": [], "total_ms": [], "rtf": []}
    model_load = 0.0
    wers: dict[str, list[float]] = {}
    cers: dict[str, list[float]] = {}
    skipped = 0
    backend_used = ""
    for i, (ex, audio_path) in enumerate(items, 1):
        try:
            if mode == "text":
                d = process_text(ex["text"], now=ex["reference_time"], extractor=extractor)
            else:
                d = process_audio(audio_path, now=ex["reference_time"], language=asr_language,  # type: ignore[arg-type]
                                  extractor=extractor, asr_backend=asr_backend)
        except AudioValidationError as exc:
            print(f"  skip {ex['id']}: {exc.message}")
            skipped += 1
            continue
        pred = _pred_dict(d)
        correct = score_record(ex["expected"], pred, ex.get("tags", []))
        records.append({"id": ex["id"], "lang_group": ex["lang_group"], "difficulty": ex["difficulty"],
                        "correct": correct, "needs_review": d.needs_review,
                        "expected": ex["expected"], "predicted": pred})
        lat["extract_ms"].append(d.timings_ms.extract)
        lat["total_ms"].append(d.timings_ms.total)
        model_load = max(model_load, d.timings_ms.model_load)
        row = {"id": ex["id"], "lang_group": ex["lang_group"], "difficulty": ex["difficulty"],
               "text": ex["text"], "transcript": d.transcript, "method": d.extraction_method,
               "needs_review": "|".join(d.needs_review), "total_ms": d.timings_ms.total}
        if mode == "audio":
            lat["asr_ms"].append(d.timings_ms.asr)
            w, c = wer(ex["text"], d.transcript), cer(ex["text"], d.transcript)
            wers.setdefault(ex["lang_group"], []).append(w)
            cers.setdefault(ex["lang_group"], []).append(c)
            row["wer"], row["cer"] = round(w, 3), round(c, 3)
            for warn in d.warnings:
                if warn.startswith("ASR backend:"):
                    backend_used = warn.split(":", 1)[1].strip()
            dur = None
            try:
                from voice_expense.asr import audio_duration

                dur = audio_duration(Path(audio_path))  # type: ignore[arg-type]
            except Exception:
                dur = None
            if dur:
                lat["rtf"].append(d.timings_ms.asr / 1000.0 / dur)
        for f in EVAL_FIELDS:
            row[f"exp_{f}"] = ex["expected"].get(f)
            row[f"pred_{f}"] = pred.get(f)
            row[f"ok_{f}"] = int(correct[f])
        rows.append(row)
        if i % 25 == 0:
            print(f"  {i}/{len(items)} done")
    asr_summary = {}
    if mode == "audio":
        groups = sorted(wers)
        all_w = [x for g in groups for x in wers[g]]
        all_c = [x for g in groups for x in cers[g]]
        asr_summary = {
            "wer": {g: round(100 * sum(wers[g]) / len(wers[g]), 1) for g in groups},
            "cer": {g: round(100 * sum(cers[g]) / len(cers[g]), 1) for g in groups},
            "wer_all": round(100 * sum(all_w) / len(all_w), 1) if all_w else float("nan"),
            "cer_all": round(100 * sum(all_c) / len(all_c), 1) if all_c else float("nan"),
            "backend": backend_used,
        }
    return {"records": records, "rows": rows, "lat": {k: latency_stats(v) for k, v in lat.items()},
            "model_load_ms": model_load, "asr": asr_summary, "skipped": skipped}


def _na(v: Any) -> Any:
    """Show NaN (e.g. recall when nothing was wrong) as n/a."""
    return "n/a" if isinstance(v, float) and v != v else v


def _table(title: str, data: dict[str, dict[str, float]], cols: list[str]) -> str:
    lines = [f"**{title}**", "", "| group | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    for g, vals in data.items():
        lines.append(f"| {g} | " + " | ".join(f"{vals.get(c, float('nan')):.1f}" for c in cols) + " |")
    return "\n".join(lines) + "\n"


def _prf_section(agg: dict[str, Any]) -> list[str]:
    """Markdown tables: per-field precision/recall/F1, per-language F1, category report."""
    if "slot_prf" not in agg:
        return []
    md = ["**Precision / Recall / F1 per field (%)** — slot-filling scoring: a wrong value counts as a false "
          "positive AND a false negative; an empty prediction where a value was expected is a false negative.\n",
          "| field | accuracy | precision | recall | F1 | TP | FP | FN | TN |", "|---|---|---|---|---|---|---|---|---|"]
    for f, v in agg["slot_prf"].items():
        name = "**micro (all fields)**" if f == "micro" else f
        md.append(f"| {name} | {_na(v['accuracy'])} | {_na(v['precision'])} | {_na(v['recall'])} | {_na(v['f1'])} | "
                  f"{v['tp']} | {v['fp']} | {v['fn']} | {v['tn']} |")
    md.append("")
    fields = ["amount", "merchant", "date", "category", "currency", "time", "payment_method"]
    md.append("**F1 by language group (%)**\n")
    md.append("| group | " + " | ".join(fields) + " | micro |")
    md.append("|---|" + "---|" * (len(fields) + 1))
    for g, prf in agg["slot_prf_by_lang"].items():
        md.append(f"| {g} | " + " | ".join(str(_na(prf[f]["f1"])) for f in fields) + f" | {_na(prf['micro']['f1'])} |")
    md.append("")
    for title, key in (("Category", "category_report"), ("Transaction type", "transaction_type_report"),
                       ("Payment method", "payment_report")):
        rep = agg[key]
        md.append(f"**{title} classification report (%)** — accuracy {rep['accuracy']}, "
                  f"macro F1 {_na(rep['macro']['f1'])}, weighted F1 {_na(rep['weighted']['f1'])}\n")
        md.append("| class | precision | recall | F1 | support |\n|---|---|---|---|---|")
        for c, v in rep["per_class"].items():
            md.append(f"| {c} | {_na(v['precision'])} | {_na(v['recall'])} | {_na(v['f1'])} | {v['support']} |")
        md.append(f"| *macro avg* | {_na(rep['macro']['precision'])} | {_na(rep['macro']['recall'])} | "
                  f"{_na(rep['macro']['f1'])} | |")
        md.append(f"| *weighted avg* | {_na(rep['weighted']['precision'])} | {_na(rep['weighted']['recall'])} | "
                  f"{_na(rep['weighted']['f1'])} | |\n")
    md.append("The category confusion matrix is in `confusion_category.csv` (rows = expected, columns = predicted).\n")
    return md


def write_confusion(out_dir: Path, agg: dict[str, Any], suffix: str = "") -> None:
    rep = agg.get("category_report")
    if not rep:
        return
    labels = rep["labels"]
    with open(out_dir / f"confusion_category{suffix}.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["expected \\ predicted"] + labels)
        for t in labels:
            w.writerow([t] + [rep["confusion"][t][p] for p in labels])


def environment(settings: Any, mode: str, extractor: str, asr_language: Optional[str], backend: str) -> dict[str, str]:
    gpu = "CUDA GPU" if _cuda_available() else "none detected"
    return {
        "date": datetime.now().isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu": f"{platform.processor() or platform.machine()} ({os.cpu_count()} logical cores)",
        "gpu": gpu,
        "mode": mode,
        "extractor": extractor,
        "asr_backend": backend or ("n/a (text mode)" if mode == "text" else settings.asr_backend),
        "whisper_model": settings.whisper_model if mode == "audio" else "n/a",
        "asr_language": (asr_language or settings.asr_language) if mode == "audio" else "n/a",
        "llm_provider": settings.llm_provider,
        "llm_model": settings.effective_llm_model or "n/a",
    }


def write_report(out_dir: Path, runs: dict[str, dict[str, Any]], env: dict[str, str], mode: str) -> str:
    md: list[str] = ["# Voice expense pipeline — evaluation report", ""]
    md.append("## Environment\n")
    md.append("| key | value |\n|---|---|")
    md.extend(f"| {k} | {v} |" for k, v in env.items())
    md.append("")
    md.append("## How to read this report (mapping to the project proposal)\n")
    md.append("- **\"Whether amount, date and merchant are captured correctly\"** → the `amount`, `date` and "
              "`merchant` columns of *Per-field accuracy* (by language group), plus *Full-record exact match*.")
    md.append("- **\"How often a user needs to correct a field\"** → *Estimated correction rate*: average number of "
              "fields per transaction that are wrong (= the user would edit them) and % of transactions needing at "
              "least one edit. Real-usage numbers come from `GET /v1/expenses/stats` after people use the app.")
    md.append("- **\"How long processing takes\"** → *Latency* (mean / p50 / p95 in ms, real-time factor, model load "
              "time reported separately; the first item is a warm-up and is excluded).")
    md.append("")
    names = list(runs)
    for name, run in runs.items():
        agg = run["agg"]
        md.append(f"## Results: {name}  (n = {agg['n']}{', skipped ' + str(run['skipped']) if run['skipped'] else ''})\n")
        md.append(_table("Per-field accuracy (%) — all", {"all": agg["field_accuracy"]}, EVAL_FIELDS))
        md.append(_table("Per-field accuracy (%) — by language group", agg["by_lang"], EVAL_FIELDS))
        md.append(_table("Per-field accuracy (%) — by difficulty", agg["by_difficulty"], EVAL_FIELDS))
        md.append(f"**Full-record exact match** ({', '.join(KEY_FIELDS)} all correct): **{agg['exact_match']}%** — "
                  + ", ".join(f"{g}: {v}%" for g, v in agg["exact_match_by_lang"].items()) + "\n")
        md.append("**Estimated correction rate**\n")
        md.append("| group | avg fields to fix per transaction | % transactions needing ≥1 fix |\n|---|---|---|")
        md.append(f"| all | {agg['correction']['avg_fields_to_fix']} | {agg['correction']['pct_needing_fix']} |")
        for g, c in agg["correction_by_lang"].items():
            md.append(f"| {g} | {c['avg_fields_to_fix']} | {c['pct_needing_fix']} |")
        md.append("")
        rc = agg["review_counts"]
        md.append(f"**needs_review quality**: precision {_na(agg['review_precision'])}% (flagged fields that were really "
                  f"wrong), recall {_na(agg['review_recall'])}% (wrong fields that were flagged), "
                  f"F1 {_na(agg['review_f1'])}%. "
                  f"Counts: {rc['flagged']} flagged, {rc['wrong']} wrong, {rc['flagged_and_wrong']} both.\n")
        md.extend(_prf_section(agg))
        md.append("**Latency (ms)**\n")
        md.append("| stage | mean | p50 | p95 | n |\n|---|---|---|---|---|")
        for k, v in run["lat"].items():
            if v.get("n"):
                md.append(f"| {k} | {v['mean']} | {v['p50']} | {v['p95']} | {v['n']} |")
        if run["model_load_ms"]:
            md.append(f"\nModel load time (excluded above): {run['model_load_ms']:.0f} ms")
        md.append("")
        if run["asr"]:
            a = run["asr"]
            md.append("**ASR error rates (%)** (after the same normalization on reference and hypothesis)\n")
            md.append("| group | WER | CER |\n|---|---|---|")
            for g in a["wer"]:
                md.append(f"| {g} | {a['wer'][g]} | {a['cer'][g]} |")
            md.append(f"| **all** | **{a['wer_all']}** | **{a['cer_all']}** |\n")
    if len(names) == 2:
        a, b = runs[names[0]]["agg"], runs[names[1]]["agg"]
        md.append(f"## Side by side: {names[0]} vs {names[1]}\n")
        md.append(f"| field | {names[0]} | {names[1]} | Δ |\n|---|---|---|---|")
        for f in EVAL_FIELDS:
            x, y = a["field_accuracy"][f], b["field_accuracy"][f]
            md.append(f"| {f} | {x} | {y} | {y - x:+.1f} |")
        md.append(f"| exact match | {a['exact_match']} | {b['exact_match']} | {b['exact_match'] - a['exact_match']:+.1f} |")
        md.append(f"| avg fields to fix | {a['correction']['avg_fields_to_fix']} | {b['correction']['avg_fields_to_fix']} | |")
        ra, rb = runs[names[0]]["asr"], runs[names[1]]["asr"]
        if ra and rb:
            md.append(f"| WER (all) | {ra['wer_all']} | {rb['wer_all']} | {rb['wer_all'] - ra['wer_all']:+.1f} |")
        md.append("")
    md.append("## Notes\n")
    md.append("- Synthetic (TTS) audio is much cleaner than real phone recordings. Report real-recording numbers "
              "(eval/record_audio.py) as the honest result.")
    md.append("- Time is counted correct within ±60 min when the phrase used a time-of-day word (الصبح → 09:00).")
    md.append("- The main dataset (phrases.jsonl) was written together with the rules, so text-mode accuracy on it is an "
              "upper bound. `eval/dataset/challenge_unseen.jsonl` holds 30 phrasings written afterwards and never used "
              "for tuning: run `python eval/evaluate.py --mode text --dataset eval/dataset/challenge_unseen.jsonl` for a "
              "more honest generalization check, and add your team's own phrases.")
    text = "\n".join(md) + "\n"
    (out_dir / "report.md").write_text(text, encoding="utf-8")
    return text


def write_csvs(out_dir: Path, rows: list[dict[str, Any]], suffix: str = "") -> None:
    if not rows:
        return
    with open(out_dir / f"predictions{suffix}.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with open(out_dir / f"errors{suffix}.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "lang_group", "difficulty", "field", "expected", "predicted", "text", "transcript", "needs_review"])
        for r in rows:
            for f in EVAL_FIELDS:
                if not r[f"ok_{f}"]:
                    w.writerow([r["id"], r["lang_group"], r["difficulty"], f, r[f"exp_{f}"], r[f"pred_{f}"],
                                r["text"], r["transcript"], r["needs_review"]])


def main(argv: Optional[list[str]] = None) -> int:
    _setup_console()
    ap = argparse.ArgumentParser(description="Evaluate the voice expense pipeline")
    ap.add_argument("--mode", choices=["text", "audio"], default="text")
    ap.add_argument("--manifest", help="CSV with id,path,... (audio mode)")
    ap.add_argument("--dataset", default=str(DEFAULT_DATASET))
    ap.add_argument("--extractor", choices=["rules", "llm", "hybrid"], default="rules")
    ap.add_argument("--asr-language", choices=["ar", "auto", "en"], default=None)
    ap.add_argument("--asr-backend", choices=["auto", "faster_whisper", "openai_whisper", "openai_api", "mock"], default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--compare", action="store_true", help="text: rules vs hybrid; audio: ASR language ar vs auto")
    ap.add_argument("--out", default=str(ROOT / "results"))
    args = ap.parse_args(argv)

    settings = get_settings()
    examples = load_dataset(Path(args.dataset))
    manifest = None
    if args.mode == "audio":
        if not args.manifest or not Path(args.manifest).is_file():
            print(f"Manifest not found: {args.manifest}. Generate audio first: python eval/generate_audio.py --limit 20")
            return 1
        manifest = load_manifest(Path(args.manifest))
        if args.limit:
            manifest = manifest[: args.limit]
    elif args.limit:
        examples = examples[: args.limit]

    if args.compare:
        configs = ([("rules", "rules", args.asr_language), ("hybrid", "hybrid", args.asr_language)]
                   if args.mode == "text" else
                   [("asr_lang=ar", args.extractor, "ar"), ("asr_lang=auto", args.extractor, "auto")])
    else:
        name = args.extractor if args.mode == "text" else f"{args.extractor} / asr_lang={args.asr_language or settings.asr_language}"
        configs = [(name, args.extractor, args.asr_language)]

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = Path(args.out) / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    runs: dict[str, dict[str, Any]] = {}
    t0 = time.perf_counter()
    for idx, (name, extractor, lang) in enumerate(configs):
        print(f"Running [{name}] on {len(manifest) if manifest is not None else len(examples)} examples ...")
        run = run_once(examples, args.mode, extractor, manifest, lang, args.asr_backend)
        if not run["records"]:
            print("No examples were evaluated (check the manifest paths).")
            return 1
        run["agg"] = aggregate(run["records"])
        runs[name] = run
        write_confusion(out_dir, run["agg"], "" if idx == 0 else f"_{idx}")
        write_csvs(out_dir, run["rows"], "" if idx == 0 else f"_{name.replace('=', '-').replace(' ', '').replace('/', '_')}")
    backend = next((r["asr"].get("backend", "") for r in runs.values() if r["asr"]), "")
    env = environment(settings, args.mode, args.extractor, args.asr_language, backend)
    write_report(out_dir, runs, env, args.mode)

    # Console summary
    for name, run in runs.items():
        agg = run["agg"]
        print(f"\n=== {name} (n={agg['n']}) ===")
        print("field accuracy %: " + ", ".join(f"{f}={agg['field_accuracy'][f]}" for f in EVAL_FIELDS))
        for g, vals in agg["by_lang"].items():
            print(f"  {g:7s}: " + ", ".join(f"{f}={vals[f]}" for f in ("amount", "merchant", "category", "date")))
        print(f"exact match: {agg['exact_match']}% | avg fields to fix: {agg['correction']['avg_fields_to_fix']} | "
              f"needing a fix: {agg['correction']['pct_needing_fix']}%")
        print(f"needs_review precision/recall/F1: {_na(agg['review_precision'])}% / {_na(agg['review_recall'])}% / "
              f"{_na(agg['review_f1'])}%")
        print("precision / recall / F1 per field (%):")
        for f, v in agg["slot_prf"].items():
            print(f"  {f:16s} P={_na(v['precision'])}  R={_na(v['recall'])}  F1={_na(v['f1'])}  "
                  f"(TP={v['tp']} FP={v['fp']} FN={v['fn']})")
        rep = agg["category_report"]
        print(f"category: accuracy {rep['accuracy']}%, macro F1 {_na(rep['macro']['f1'])}%, "
              f"weighted F1 {_na(rep['weighted']['f1'])}%")
        lt = run["lat"]["total_ms"]
        print(f"latency total ms: mean {lt['mean']} p50 {lt['p50']} p95 {lt['p95']}")
        if run["asr"]:
            print(f"WER {run['asr']['wer_all']}%  CER {run['asr']['cer_all']}%  by group: {run['asr']['wer']}")
    print(f"\nReport written to {out_dir / 'report.md'}  ({time.perf_counter() - t0:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
