"""The existing v1 model's own transaction decision, as a reference row.

sms_eval_final/sms_model.py:SmsTxnModel fuses classification and extraction: its
type classifier has a "none" class, and it also rejects any message with no
number in it. This wrapper retrains it on the benchmark's TRAINING split and
reports exactly that decision, so the new classifiers can be compared against the
system that exists today. v1 itself is imported, never modified.

Binary only (v1 has no OTP / promo / balance classes). Scores are
1 - P(type = none) from v1's type classifier; the final decision additionally
applies v1's "no amount -> not a transaction" rule, so the score and the
decision can disagree, and no threshold is supported.
"""
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from classification.base_classifier import (BaseClassifier, check_preprocessing,  # noqa: E402
                                            read_meta)
from config import labels as L                                                  # noqa: E402
from config import settings as S                                                # noqa: E402


def import_v1():
    if S.V1_DIR not in sys.path:
        sys.path.insert(0, S.V1_DIR)
    from sms_model import SmsTxnModel                     # noqa: E402
    return SmsTxnModel


class V1Gate(BaseClassifier):
    name = "v1_gate"
    family = "reference"
    score_type = "probability"
    supports_proba = True

    def __init__(self, classes, **kw):
        if list(classes) != list(L.BINARY_CLASSES):
            raise ValueError("v1_gate is a binary reference only")
        kw.pop("threshold", None)
        super().__init__(classes, threshold=None, **kw)

    def train(self, train_texts, train_labels, val_texts=None, val_labels=None,
              train_records=None, **kw):
        if train_records is None:
            raise ValueError("v1_gate trains on full records (it learns extraction too)")
        Model = import_v1()
        t0 = time.perf_counter()
        self.model = Model().fit(train_records)
        self.train_info = {"train_time_s": time.perf_counter() - t0,
                           "n_train": len(train_records)}
        return self.train_info

    def _scores(self, prepared):
        # v1 does its own normalization internally; `prepared` is already the
        # benchmark's "digits" view, which is idempotent under v1's normalize().
        X = self.model._text(prepared)
        p = self.model.type_clf.predict_proba(X)
        none = list(self.model.type_clf.classes_).index("none")
        tx = 1.0 - p[:, none]
        return np.stack([tx, 1.0 - tx], axis=1)

    def predict_with_scores(self, texts):
        sc = self.decision_scores(texts)
        labels = [L.TRANSACTION if self.model.predict(t)["is_transaction"] else L.NON_TRANSACTION
                  for t in texts]
        return labels, sc

    def predict(self, texts):
        return self.predict_with_scores(texts)[0]

    def save(self, directory):
        import joblib
        os.makedirs(directory, exist_ok=True)
        joblib.dump(self.model, os.path.join(directory, "v1_model.joblib"), compress=3)
        self.write_meta(directory)

    @classmethod
    def load(cls, directory):
        import joblib
        meta = read_meta(directory)
        check_preprocessing(meta)
        import_v1()
        obj = cls(meta["classes"])
        obj.model = joblib.load(os.path.join(directory, "v1_model.joblib"))
        obj.train_info = meta.get("train_info", {})
        return obj
