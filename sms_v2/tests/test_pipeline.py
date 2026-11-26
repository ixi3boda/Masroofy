"""Routing rules, null handling and end-to-end accounting."""
import numpy as np
import pytest

from benchmark import data as D
from classification import registry
from config import labels as L
from evaluation import end_to_end_metrics as E2E
from extraction.base import OUTPUT_FIELDS, find_reference
from extraction.v1_extractor import V1Extractor
from sms_pipeline import SmsPipeline

V1F = ["type", "amount", "currency", "fee", "balance_after", "merchant", "channel",
       "datetime", "account_last4"]


class FixedClassifier:
    """Stub Stage 1 that returns a preset label per message."""
    name, family, score_type = "stub", "stub", "probability"

    def __init__(self, classes, labels):
        self.classes, self._labels = classes, labels

    def predict_with_scores(self, texts):
        labs = [self._labels.get(t, self.classes[-1]) for t in texts]
        sc = np.array([[1.0 if c == lab else 0.0 for c in self.classes] for lab in labs])
        return labs, sc


@pytest.fixture(scope="module")
def extractor(template_split):
    return V1Extractor().fit(template_split["train"])


TX = "تم خصم 250.00 جنيه من حسابك ****4321 لدى CARREFOUR MAADI يوم 10/08/2026"
OTP = "Your CIB OTP is 847237. Do not share this code with anyone."


def test_only_transactions_are_extracted(extractor):
    clf = FixedClassifier(list(L.CLASSES), {TX: "transaction", OTP: "otp"})
    out = SmsPipeline(clf, extractor).process_many([TX, OTP])
    assert out[0]["is_transaction"] and out[0]["record"]["amount"] == 250.0
    assert out[0]["record"]["direction"] == "debit"
    assert out[1]["record"] is None and out[1]["reason"] == "stage 1: otp"


@pytest.mark.parametrize("cls", ["failed_transaction", "balance_inquiry", "promotional", "other"])
def test_non_transaction_classes_never_produce_records(extractor, cls):
    clf = FixedClassifier(list(L.CLASSES), {TX: cls})
    out = SmsPipeline(clf, extractor).process(TX)
    assert out["record"] is None and not out["is_transaction"]


def test_missing_fields_are_null_not_invented(extractor):
    clf = FixedClassifier(list(L.CLASSES), {"no numbers here at all": "transaction"})
    out = SmsPipeline(clf, extractor).process("no numbers here at all")
    assert out["record"] is None and out["reason"].startswith("stage 2")
    rec = extractor.extract("Purchase of EGP 38.32 at NADA JUICE BAR")
    assert set(OUTPUT_FIELDS) <= set(rec)
    assert rec["fee"] is None and rec["balance_after"] is None


def test_odd_inputs_do_not_crash(extractor):
    clf = FixedClassifier(list(L.CLASSES), {})
    out = SmsPipeline(clf, extractor).process_many(["", None, "\U0001F642\U0001F642", "x" * 5000])
    assert len(out) == 4
    assert extractor.extract_many(["", "\U0001F642"])[0]["extraction_ok"] is False


def test_reference_extraction():
    assert find_reference("DeltaPay: received EGP 5. Ref IP2601045307672") == "IP2601045307672"
    assert find_reference("رقم العملية 019824251083") == "019824251083"
    assert find_reference("Thanks for using our service") is None


def test_e2e_counts_classification_errors():
    gold_tx = {"id": 1, "label_multi": "transaction",
               "expected": {"is_transaction": True, "type": "debit", "amount": 5.0,
                            "currency": "EGP", "fee": None, "balance_after": None,
                            "merchant": "X", "channel": "card", "datetime": None,
                            "account_last4": None}}
    gold_otp = {"id": 2, "label_multi": "otp",
                "expected": {"is_transaction": False, **{k: None for k in V1F}}}
    good = {"amount": 5.0, "currency": "EGP", "direction": "debit", "type": "debit",
            "channel": "card", "counterparty": "X", "date": None, "datetime": None,
            "account_last4": None, "fee": None, "balance_after": None, "reference": None,
            "extraction_ok": True, "extraction_note": None}
    outputs = {1: {"output": good}, 2: {"output": dict(good, amount=9.0)}}
    # Stage 1 rejects the transaction and accepts the OTP: both errors must show
    res, _ = E2E.compute([gold_tx, gold_otp], {1: False, 2: True}, outputs)
    assert res["missed_transactions"] == 1 and res["false_records"] == 1
    assert res["false_records_by_class"] == {"otp": 1}
    assert res["e2e_full_exact_recall"] == 0.0
    assert res["headline"]["amount_acc"] == 0.0          # a miss scores as wrong
    res, _ = E2E.compute([gold_tx, gold_otp], {1: True, 2: False}, outputs)
    assert res["e2e_full_exact_f1"] == 1.0 and res["false_records"] == 0


def test_live_pipeline_matches_offline_combination(template_split, extractor):
    """run_e2e combines saved predictions; SmsPipeline runs live. Same answer."""
    tr, va, te = (template_split[s][::4] for s in ("train", "val", "test"))
    clf = registry.build("tfidf_svm", D.class_list("multiclass"))
    clf.train([r["sms"] for r in tr], [r["label_multi"] for r in tr],
              [r["sms"] for r in va], [r["label_multi"] for r in va])
    texts = [r["sms"] for r in te]
    live = SmsPipeline(clf, extractor).process_many(texts)
    routed = {r["id"]: p == L.TRANSACTION for r, p in zip(te, clf.predict(texts))}
    outputs = {r["id"]: {"output": o} for r, o in zip(te, extractor.extract_many(texts))}
    res, outcomes = E2E.compute(te, routed, outputs)
    assert sum(o["is_transaction"] for o in live) == res["records_produced"]
    for o, oc in zip(live, outcomes):
        assert o["is_transaction"] == (oc["outcome"] in ("correct_record", "false_record"))
