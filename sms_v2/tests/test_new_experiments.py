"""Experiment 1 (classifier x extractor combinations) and Experiment 2 (joint model).

Routing and missing-checkpoint tests need no torch. The model tests use a tiny random
BERT (skipped offline / without torch): only mechanics are under test, never scores.
"""
import hashlib
import json
import os

import numpy as np
import pytest

from config import labels as L
from config import settings as S
from extraction.base import OUTPUT_FIELDS, empty_output
from sms_pipeline import JointPipeline, SmsPipeline

TX = "تم خصم 250.00 جنيه من حسابك ****4321 لدى CARREFOUR MAADI يوم 10/08/2026"
OTP = "Your CIB OTP is 847237. Do not share this code with anyone."
TINY = "hf-internal-testing/tiny-random-bert"


# ------------------------------------------------------------------ stubs (no torch)
class FixedClassifier:
    name, family, score_type = "stub", "stub", "probability"

    def __init__(self, classes, labels):
        self.classes, self._labels = classes, labels

    def predict_with_scores(self, texts):
        labs = [self._labels[t] for t in texts]
        return labs, np.array([[1.0 if c == lab else 0.0 for c in self.classes] for lab in labs])


class SpyExtractor:
    """Records every text it is asked to extract; returns a fixed valid record."""

    def __init__(self, ok=True):
        self.calls, self.ok = [], ok

    def extract_many(self, texts):
        self.calls.extend(texts)
        out = []
        for _ in texts:
            if not self.ok:
                out.append(empty_output("no amount found"))
                continue
            rec = {k: None for k in OUTPUT_FIELDS}
            rec.update(amount=250.0, currency="EGP", type="debit", direction="debit",
                       extraction_ok=True, extraction_note=None)
            out.append(rec)
        return out


class StubJoint:
    is_joint, name = True, "stub"

    def __init__(self, classes, labels, ok=True):
        self.classes, self._labels, self._ok = classes, labels, ok
        self.passes = 0

    def infer(self, texts):
        self.passes += 1
        labs = [self._labels[t] for t in texts]
        probs = np.array([[1.0 if c == lab else 0.0 for c in self.classes] for lab in labs])
        return labs, probs, SpyExtractor(self._ok).extract_many(texts)


# ------------------------------------------------------------------ routing
def test_binary_non_transaction_never_reaches_extractor():
    spy = SpyExtractor()
    clf = FixedClassifier(list(L.BINARY_CLASSES), {OTP: L.NON_TRANSACTION})
    out = SmsPipeline(clf, spy).process(OTP)
    assert spy.calls == []
    assert out["record"] is None and not out["is_transaction"]
    assert out["reason"] == "stage 1: non_transaction"
    assert out["stage1"]["experiment"] == "binary" and not out["stage1"]["routed_to_extraction"]


def test_binary_transaction_goes_straight_to_extractor():
    spy = SpyExtractor()
    clf = FixedClassifier(list(L.BINARY_CLASSES), {TX: L.TRANSACTION})
    out = SmsPipeline(clf, spy).process(TX)
    assert spy.calls == [TX]
    assert out["is_transaction"] and out["record"]["amount"] == 250.0 and out["reason"] is None


@pytest.mark.parametrize("cls", [c for c in L.CLASSES if c != L.TRANSACTION])
def test_multiclass_non_transaction_classes_are_not_extracted(cls):
    spy = SpyExtractor()
    clf = FixedClassifier(list(L.CLASSES), {TX: cls})
    out = SmsPipeline(clf, spy).process(TX)
    assert spy.calls == [] and out["record"] is None and out["reason"] == f"stage 1: {cls}"
    assert out["stage1"]["experiment"] == "multiclass"


def test_multiclass_batch_extracts_only_routed_messages():
    spy = SpyExtractor()
    clf = FixedClassifier(list(L.CLASSES), {TX: L.TRANSACTION, OTP: "otp"})
    out = SmsPipeline(clf, spy).process_many([OTP, TX, OTP])
    assert spy.calls == [TX]
    assert [o["is_transaction"] for o in out] == [False, True, False]


def test_routed_message_without_amount_gives_no_record():
    clf = FixedClassifier(list(L.CLASSES), {TX: L.TRANSACTION})
    out = SmsPipeline(clf, SpyExtractor(ok=False)).process(TX)
    assert out["record"] is None and out["reason"].startswith("stage 2")


@pytest.mark.parametrize("classes", [list(L.BINARY_CLASSES), list(L.CLASSES)])
def test_joint_pipeline_routes_in_one_pass(classes):
    non_tx = L.NON_TRANSACTION if len(classes) == 2 else "otp"
    jm = StubJoint(classes, {TX: L.TRANSACTION, OTP: non_tx})
    out = JointPipeline(jm).process_many([TX, OTP])
    assert jm.passes == 1                                     # one model, one call
    assert out[0]["is_transaction"] and out[0]["record"]["amount"] == 250.0
    assert out[1]["record"] is None and out[1]["reason"] == f"stage 1: {non_tx}"
    jm2 = StubJoint(classes, {TX: L.TRANSACTION}, ok=False)
    assert JointPipeline(jm2).process(TX)["reason"].startswith("stage 2")


# ------------------------------------------------------------------ missing checkpoints
def test_missing_classifier_dir_fails_clearly(tmp_path):
    with pytest.raises(FileNotFoundError, match="no trained classifier"):
        SmsPipeline.from_dirs(str(tmp_path / "nope"), str(tmp_path))


def test_missing_or_empty_extractor_dir_fails_clearly(tmp_path):
    from extraction.loader import load_extractor
    with pytest.raises(FileNotFoundError, match="not found"):
        load_extractor(str(tmp_path / "nope"))
    with pytest.raises(FileNotFoundError, match="no fitted extractor"):
        load_extractor(str(tmp_path))


def test_missing_combo_checkpoints_fail_clearly(tmp_output):
    from benchmark import layout, run_combos, store
    with pytest.raises(layout.MissingCheckpoint, match="classify --models arabert"):
        SmsPipeline.from_combo("template", "binary", "arabert", "marbert")
    store.mark_done(store.result_dir("template", "binary", "arabert"))     # classifier "done"
    with pytest.raises(layout.MissingCheckpoint, match="extract-tf --models marbert"):
        run_combos.run("template", "binary", "arabert", "marbert", log=lambda *a: None)
    assert not os.path.exists(layout.combo_result_dir("template", "binary", "arabert", "marbert"))


def test_missing_joint_model_fails_clearly(tmp_output, tmp_path):
    from benchmark import layout
    with pytest.raises(layout.MissingCheckpoint, match="bench.py joint --models arabert"):
        JointPipeline.from_run("template", "binary", "arabert")
    with pytest.raises(FileNotFoundError, match="no trained joint model"):
        JointPipeline.from_dir(str(tmp_path))


def test_new_folders_never_collide_with_existing_ones(tmp_output):
    from benchmark import layout, store
    new = [layout.extractor_result_dir("template", "marbert"),
           layout.combo_result_dir("template", "binary", "arabert", "marbert"),
           layout.joint_result_dir("template", "binary", "arabert"),
           layout.summary_dir("template"),
           layout.extractor_model_dir("template", "marbert"),
           layout.joint_model_dir("template", "binary", "arabert")]
    old = [store.result_dir("template", e, m) for e in S.EXPERIMENTS for m in
           ("arabert", "marbert")] + [store.stage_dir("template", n) for n in
                                      ("extraction", "end_to_end", "summary")] + \
          [store.model_dir("template", e, m) for e in S.EXPERIMENTS for m in ("arabert", "marbert")] + \
          [os.path.join(store.root(), "models", "template", "extractor", "v1_sklearn")]
    for n in new:
        for o in old:
            assert not (n == o or n.startswith(o + os.sep) or o.startswith(n + os.sep)), (n, o)


# ------------------------------------------------------------------ tiny transformer models
torch_needed = pytest.mark.skipif(
    __import__("importlib").util.find_spec("torch") is None
    or __import__("importlib").util.find_spec("transformers") is None,
    reason="needs torch + transformers")


@pytest.fixture(scope="module")
def tiny_ok():
    try:
        from transformers import AutoTokenizer
        AutoTokenizer.from_pretrained(TINY)
    except Exception as e:
        pytest.skip(f"cannot fetch {TINY}: {e}")


def _small(split):
    tr = [r for r in split["train"] if r["expected"]["is_transaction"]][::20] + \
         [r for r in split["train"] if not r["expected"]["is_transaction"]][::20]
    va = split["val"][::8]
    return tr, va


HP = dict(checkpoint=TINY, epochs=2, batch_size=16, eval_batch_size=32,
          early_stopping_patience=5, device="cpu")


class Interrupt(Exception):
    pass


@torch_needed
def test_extractor_train_interrupt_resume_save_load(tiny_ok, template_split, tmp_path):
    from extraction.loader import load_extractor
    from extraction.transformer_extractor import build_extractor
    tr, va = _small(template_split)

    def stop(msg):
        if "epoch 2/2 step" in msg:
            raise Interrupt()

    with pytest.raises(Interrupt):
        build_extractor("marbert", **HP).train(tr, va, work_dir=str(tmp_path), log=stop)
    logs = []
    ex = build_extractor("marbert", **HP)
    info = ex.train(tr, va, work_dir=str(tmp_path), log=logs.append)
    assert any("resuming" in m for m in logs) and [h["epoch"] for h in info["history"]] == [1, 2]
    assert info["n_train"] == sum(r["expected"]["is_transaction"] for r in tr)   # gold tx only
    texts = [TX, OTP, "", "\U0001F642 50 EGP"]
    first = ex.extract_many(texts)
    ex.save(str(tmp_path / "final"))
    again = load_extractor(str(tmp_path / "final"), device="cpu")
    assert again.extract_many(texts) == first
    for rec in first:
        assert set(OUTPUT_FIELDS) <= set(rec) and "extraction_ok" in rec
        if not rec["extraction_ok"]:
            assert all(rec[k] is None for k in OUTPUT_FIELDS)


@torch_needed
def test_joint_model_one_pass_save_load(tiny_ok, template_split, tmp_path):
    from extraction.loader import load_extractor
    from extraction.transformer_extractor import build_joint
    tr, va = _small(template_split)
    jm = build_joint("arabert", list(L.CLASSES), **HP)
    info = jm.train(tr, va, work_dir=str(tmp_path), label_col="label_multi", log=lambda m: None)
    assert "val_macro_f1" in info["history"][0] and "val_full_record_exact" in info["history"][0]
    jm.save(str(tmp_path / "final"))
    pipe = JointPipeline.from_dir(str(tmp_path / "final"), device="cpu")
    out = pipe.process_many([TX, OTP])
    assert [o["stage1"]["label"] for o in out] == jm.predict([TX, OTP])
    for o in out:
        assert o["stage1"]["label"] in L.CLASSES
        assert (o["record"] is not None) <= (o["stage1"]["label"] == L.TRANSACTION)
    with pytest.raises(ValueError, match="joint model"):
        load_extractor(str(tmp_path / "final"))          # never usable as a plain extractor


@torch_needed
def test_all_four_combinations_sms_to_json(tiny_ok, template_split, tmp_path):
    """Both experiments x {arabert, marbert} classifier x {arabert, marbert} extractor,
    loaded from their directories and run SMS -> JSON in one call."""
    from classification import registry
    from extraction.transformer_extractor import build_extractor
    tr, va = _small(template_split)
    ext_dirs = {}
    for name in ("arabert", "marbert"):
        ex = build_extractor(name, **dict(HP, epochs=1))
        ex.train(tr, va, work_dir=str(tmp_path / f"ext_{name}"), log=lambda m: None)
        ext_dirs[name] = str(tmp_path / f"ext_{name}" / "final")
        ex.save(ext_dirs[name])
    for exp, col, classes in (("binary", "label_binary", list(L.BINARY_CLASSES)),
                              ("multiclass", "label_multi", list(L.CLASSES))):
        for cname in ("arabert", "marbert"):
            clf = registry.build(cname, classes, checkpoint=TINY, epochs=1, batch_size=16,
                                 device="cpu")
            clf.train([r["sms"] for r in tr], [r[col] for r in tr], [r["sms"] for r in va],
                      [r[col] for r in va], work_dir=str(tmp_path / f"clf_{exp}_{cname}"),
                      train_ids=[r["id"] for r in tr], log=lambda m: None)
            cdir = str(tmp_path / f"clf_{exp}_{cname}" / "final")
            clf.save(cdir)
            for ename, edir in ext_dirs.items():
                pipe = SmsPipeline.from_dirs(cdir, edir, device="cpu")
                assert pipe.experiment == exp and pipe.extractor.name == ename
                for o in pipe.process_many([TX, OTP]):
                    assert set(o) == {"sms", "stage1", "is_transaction", "record", "reason"}
                    assert o["stage1"]["model"] == cname
                    routed = o["stage1"]["label"] == L.TRANSACTION
                    assert o["stage1"]["routed_to_extraction"] == routed
                    assert (o["record"] is not None) <= routed
                    json.dumps(o, ensure_ascii=False)              # JSON-serialisable


def _snapshot(root):
    out = {}
    for dp, _, files in os.walk(root):
        for fn in files:
            p = os.path.join(dp, fn)
            with open(p, "rb") as f:
                out[os.path.relpath(p, root)] = hashlib.sha256(f.read()).hexdigest()
    return out


@torch_needed
def test_runners_write_new_folders_and_leave_existing_results_untouched(tiny_ok, tmp_output):
    """Existing runs first (TF-IDF, a tiny AraBERT classifier, v1 extraction, e2e,
    compare), then every new runner. Every pre-existing file must be byte-identical
    afterwards; only the experiment log may grow (append-only)."""
    from benchmark import (layout, run_classify, run_combos, run_e2e, run_extract,
                           run_extract_tf, run_joint, store)
    from evaluation import compare_models, compare_new
    quiet = lambda *a: None                                               # noqa: E731
    tiny = {"checkpoint": TINY, "epochs": 1}
    run_classify.run("template", "binary", "tfidf_lr", log=quiet)
    try:
        run_classify.run("template", "binary", "arabert", overrides=tiny, device="cpu", log=quiet)
    except TypeError:
        # pre-existing run_classify log line cannot format a None precision (a tiny random
        # model predicts no transaction); the run itself is complete (DONE written first)
        pass
    assert store.is_done(store.result_dir("template", "binary", "arabert"))
    run_extract.run("template", log=quiet)
    run_e2e.run("template", log=quiet)
    compare_models.run("template", make_charts=False)

    log_path = os.path.join(str(tmp_output), "experiment_log.jsonl")
    with open(log_path, encoding="utf-8") as f:
        log_before = f.read()
    before = {k: v for k, v in _snapshot(str(tmp_output)).items() if k != "experiment_log.jsonl"}

    run_extract_tf.run("template", "marbert", overrides=tiny, device="cpu", log=quiet)
    m = run_combos.run("template", "binary", "arabert", "marbert", live_latency=5,
                       device="cpu", log=quiet)
    run_joint.run("template", "binary", "arabert", overrides=tiny, device="cpu", log=quiet)
    compare_new.run("template", make_charts=True)

    after = _snapshot(str(tmp_output))
    changed = [k for k, v in before.items() if after.get(k) != v]
    assert changed == [], f"existing files changed or deleted: {changed}"
    with open(log_path, encoding="utf-8") as f:
        assert f.read().startswith(log_before)

    cdir = layout.combo_result_dir("template", "binary", "arabert", "marbert")
    jdir = layout.joint_result_dir("template", "binary", "arabert")
    edir = layout.extractor_result_dir("template", "marbert")
    for d, files in ((cdir, ["config.json", "metrics.json", "predictions.jsonl", "outcomes.csv",
                             "confusion_matrix.csv", "DONE.json"]),
                     (jdir, ["config.json", "metrics.json", "predictions.csv", "predictions.jsonl",
                             "extraction_predictions.jsonl", "outcomes.csv",
                             "confusion_matrix.csv", "DONE.json"]),
                     (edir, ["config.json", "metrics.json", "predictions.jsonl", "DONE.json"])):
        for fn in files:
            assert os.path.exists(os.path.join(d, fn)), (d, fn)
    # the live one-call pipeline reproduces the cached composition exactly (CPU, fp32)
    assert m["timing"]["live"]["output_agreement_with_cached"] == 1.0
    assert m["n_messages"] == m["correct_records"] + m["missed_transactions"] + \
        m["false_records"] + m["correct_rejects"]
    assert os.path.exists(os.path.join(layout.summary_dir("template"), "REPORT_NEW.md"))
    # completed runs are skipped, not redone
    again = run_combos.run("template", "binary", "arabert", "marbert", live_latency=5,
                           device="cpu", log=quiet)
    assert again["finished"] == m["finished"]
