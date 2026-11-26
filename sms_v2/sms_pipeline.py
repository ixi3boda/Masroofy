"""The two-stage pipeline: any Stage-1 classifier -> the extraction parser -> JSON.

    from sms_pipeline import SmsPipeline
    pipe = SmsPipeline.from_dirs("outputs/models/template/multiclass/tfidf_svm/final",
                                 "outputs/models/template/extractor/v1_sklearn")
    pipe.process("تم خصم 250 جنيه من حسابك ****4321 لدى CARREFOUR")

Output per message:

    {
      "sms": "...",
      "stage1": {"model": "tfidf_svm", "experiment": "multiclass",
                 "label": "transaction", "score": 1.23,
                 "score_type": "decision_function", "routed_to_extraction": true},
      "is_transaction": true,
      "record": { ...extraction.base OUTPUT_FIELDS... }   or null
      "reason": null | "stage 1: otp" | "stage 2: no amount found"
    }

Business rules (config.labels.TRANSACTION is the only class that routes):
  * only messages labelled "transaction" reach extraction;
  * failed transactions, balance notices, OTPs, promotions and "other" never do,
    so they can never create a financial record;
  * a routed message in which no amount is found yields no record
    (config.settings.REQUIRE_AMOUNT, v1's rule).

The classifier is chosen by directory; extraction code does not change when it
does. Scores are reported with their type and are never turned into fake
probabilities (an SVM margin stays a margin).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from classification import registry                       # noqa: E402
from classification.base_classifier import read_meta      # noqa: E402
from config import labels as L                            # noqa: E402
from config import settings as S                          # noqa: E402
from extraction.v1_extractor import V1Extractor           # noqa: E402


class SmsPipeline:
    def __init__(self, classifier, extractor, require_amount=None, experiment=None):
        self.clf = classifier
        self.extractor = extractor
        self.require_amount = S.REQUIRE_AMOUNT if require_amount is None else require_amount
        self.experiment = experiment or ("binary" if list(classifier.classes) ==
                                         list(L.BINARY_CLASSES) else "multiclass")

    @classmethod
    def from_dirs(cls, classifier_dir, extractor_dir, device="auto", **kw):
        fam = read_meta(classifier_dir)["family"]
        clf = registry.load(classifier_dir, **({"device": device} if fam == "transformer" else {}))
        return cls(clf, V1Extractor.load(extractor_dir), **kw)

    def process_many(self, texts):
        texts = [t if isinstance(t, str) else ("" if t is None else str(t)) for t in texts]
        if not texts:
            return []
        labels, scores = self.clf.predict_with_scores(texts)
        tx = self.clf.classes.index(L.TRANSACTION)
        routed_idx = [i for i, lab in enumerate(labels) if lab == L.TRANSACTION]
        extracted = dict(zip(routed_idx,
                             self.extractor.extract_many([texts[i] for i in routed_idx])))
        out = []
        for i, (text, lab) in enumerate(zip(texts, labels)):
            stage1 = {"model": self.clf.name, "experiment": self.experiment, "label": lab,
                      "score": round(float(scores[i][tx]), 4),
                      "score_type": self.clf.score_type,
                      "routed_to_extraction": lab == L.TRANSACTION}
            rec, reason = None, None
            if lab != L.TRANSACTION:
                reason = f"stage 1: {lab}"
            else:
                rec = extracted[i]
                if not rec["extraction_ok"] and self.require_amount:
                    reason = "stage 2: " + (rec.get("extraction_note") or "no amount found")
                    rec = None
            out.append({"sms": text, "stage1": stage1, "is_transaction": rec is not None,
                        "record": rec, "reason": reason})
        return out

    def process(self, text):
        return self.process_many([text])[0]
