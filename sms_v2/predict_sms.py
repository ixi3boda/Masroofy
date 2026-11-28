"""Read an SMS, print what the chosen models extract from it. Runs locally on CPU (no GPU needed).

Models (trained on Colab, downloaded once, see "Getting the models" below):
    Stage 1  AraBERT 6-class classifier   outputs/models/template/multiclass/arabert/final
    Stage 2  MARBERT extractor            outputs/models/template/extractor/marbert/final

Usage (from sms_v2/):
    python predict_sms.py                          # interactive: type / paste an SMS, Enter; empty line quits
    python predict_sms.py --sms "تم خصم 250 جنيه ..."  # one or more --sms
    python predict_sms.py --file inbox.txt         # one SMS per line
    python predict_sms.py --sms "..." --json       # the pipeline's full JSON (what an app would consume)

From other Python code (e.g. a backend for the app), load once and reuse:
    from predict_sms import load_pipeline
    pipe = load_pipeline()
    result = pipe.process("...")          # dict: is_transaction, record, reason, stage1
    results = pipe.process_many([...])    # faster for many messages

Getting the models: in Colab run the "Export the chosen models" cell of sms_tests.ipynb. It writes
DRIVE_ROOT/export/masroofy_arabert_marbert.tar. Download it, then from sms_v2/:
    tar -xf <path to>/masroofy_arabert_marbert.tar -C outputs
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

MODELS = os.path.join(os.environ.get("SMS_V2_OUTPUT", os.path.join(HERE, "outputs")), "models", "template")
DEFAULT_CLASSIFIER = os.path.join(MODELS, "multiclass", "arabert", "final")
DEFAULT_EXTRACTOR = os.path.join(MODELS, "extractor", "marbert", "final")
GET_MODELS = ("Download masroofy_arabert_marbert.tar (Colab: 'Export the chosen models' cell of "
              "sms_tests.ipynb), then run from sms_v2/:  tar -xf <path>/masroofy_arabert_marbert.tar -C outputs")


def _check_dirs(classifier_dir, extractor_dir):
    from extraction.loader import extractor_kind
    missing = []
    if not os.path.exists(os.path.join(classifier_dir, "classifier.json")):
        missing.append(("classifier", classifier_dir, "classifier.json"))
    if not os.path.isdir(extractor_dir) or extractor_kind(extractor_dir) is None:
        missing.append(("extractor", extractor_dir, "extractor.json"))
    if missing:
        lines = [f"  {what}: {d}  ({f} not found)" for what, d, f in missing]
        raise SystemExit("Model files missing:\n" + "\n".join(lines) + "\n\n" + GET_MODELS)


def _check_transformers_version(*dirs):
    """A checkpoint saved by a newer transformers major version may not load in an older one."""
    import transformers
    local = int(transformers.__version__.split(".")[0])
    for d in dirs:
        for cfg in (os.path.join(d, "config.json"), os.path.join(d, "encoder", "config.json")):
            if os.path.exists(cfg):
                saved = json.load(open(cfg, encoding="utf-8")).get("transformers_version", "")
                if saved and int(saved.split(".")[0]) > local:
                    print(f"warning: {d} was saved with transformers {saved}, you have "
                          f"{transformers.__version__}. If loading fails: pip install -U transformers",
                          file=sys.stderr)
                break


def load_pipeline(classifier_dir=DEFAULT_CLASSIFIER, extractor_dir=DEFAULT_EXTRACTOR, device="cpu"):
    """-> SmsPipeline (AraBERT classifier -> MARBERT extractor). Load once, call .process(sms)."""
    _check_dirs(classifier_dir, extractor_dir)
    _check_transformers_version(classifier_dir, extractor_dir)
    from sms_pipeline import SmsPipeline
    return SmsPipeline.from_dirs(classifier_dir, extractor_dir, device=device, experiment="multiclass")


def show(result):
    """Short human-readable view of one pipeline result."""
    s1 = result["stage1"]
    print(f"  class: {s1['label']}  (transaction probability {s1['score']:.3f})")
    if result["record"] is None:
        print(f"  no financial record: {result['reason']}")
        return
    for k, v in result["record"].items():
        if k not in ("extraction_ok", "extraction_note") and v is not None:
            print(f"  {k:14s} {v}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sms", action="append", help="an SMS text (repeatable)")
    ap.add_argument("--file", help="text file, one SMS per line")
    ap.add_argument("--json", action="store_true", help="print the full JSON result")
    ap.add_argument("--classifier", default=DEFAULT_CLASSIFIER)
    ap.add_argument("--extractor", default=DEFAULT_EXTRACTOR)
    ap.add_argument("--device", default="cpu", help="cpu (default), cuda or auto")
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")        # Arabic on the Windows console

    t0 = time.time()
    pipe = load_pipeline(a.classifier, a.extractor, a.device)
    print(f"models loaded in {time.time() - t0:.1f} s", file=sys.stderr)

    def run(texts):
        t = time.time()
        results = pipe.process_many(texts)
        ms = (time.time() - t) * 1000 / max(len(texts), 1)
        for r in results:
            if a.json:
                print(json.dumps(r, ensure_ascii=False, indent=1))
            else:
                print(f"\nSMS: {r['sms']}")
                show(r)
        print(f"({ms:.0f} ms per SMS)", file=sys.stderr)

    texts = list(a.sms or [])
    if a.file:
        with open(a.file, encoding="utf-8-sig") as f:
            texts += [l.strip() for l in f if l.strip()]
    if texts:
        run(texts)
        return
    print("Paste an SMS and press Enter (empty line to quit).", file=sys.stderr)
    while True:
        try:
            line = input("\nsms> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            break
        run([line])


if __name__ == "__main__":
    main()
