"""Stage 2 = the EXISTING v1 parser (sms_eval_final/sms_model.py), unchanged.

v1's predict() starts with its own transaction decision (type == "none" ->
return early). In the two-stage pipeline that decision belongs to Stage 1, so
this adapter disables only that one step: it hands v1 a view of its type
classifier with the "none" column zeroed, so v1 picks the most likely REAL type
and runs the rest of its own code — number roles, merchant tagger, date and
currency rules — exactly as written. No v1 line is copied or edited.

v1's remaining rule — "a message with no number in it is not a transaction" —
still applies and comes back as extraction_ok=False ("no amount found"); the
pipeline treats that as no record (config.settings.REQUIRE_AMOUNT).

v1 is fitted on the benchmark's TRAINING split only (fit() is called by the
runner), so extraction is never scored on messages it learned from.
"""
import copy
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import spans                                                    # noqa: E402
from extraction.base import BaseExtractor, from_v1              # noqa: E402
from classification.v1_reference import import_v1               # noqa: E402


class _NoNone:
    """Read-only view of v1's type classifier with P(none) forced to 0."""

    def __init__(self, clf):
        self._clf = clf
        self.classes_ = clf.classes_
        self._none = list(clf.classes_).index("none")

    def predict_proba(self, X):
        p = np.array(self._clf.predict_proba(X), copy=True)
        p[:, self._none] = 0.0
        return p

    def predict(self, X):
        return self.classes_[self.predict_proba(X).argmax(1)]


class V1Extractor(BaseExtractor):
    name = "v1_sklearn"

    def __init__(self, model=None):
        self.model = model
        self.fit_time_s = None

    def fit(self, train_records):
        Model = import_v1()
        t0 = time.perf_counter()
        self.model = Model().fit(train_records)
        self.fit_time_s = time.perf_counter() - t0
        return self

    def _forced(self):
        m = copy.copy(self.model)              # shallow: shares every fitted part
        m.type_clf = _NoNone(self.model.type_clf)
        return m

    def extract_many(self, texts):
        m = self._forced()
        out = []
        for t in texts:
            t = t if isinstance(t, str) else ("" if t is None else str(t))
            try:
                pred = m.predict(t)
            except Exception as e:             # never let one odd SMS kill a batch
                pred = {"is_transaction": False, "_reason": f"extractor error: {e}"}
            out.append(from_v1(pred, spans.normalize(t)))
        return out

    def save(self, directory):
        import joblib
        os.makedirs(directory, exist_ok=True)
        joblib.dump(self.model, os.path.join(directory, "v1_model.joblib"), compress=3)

    @classmethod
    def load(cls, directory):
        import joblib
        import_v1()
        return cls(joblib.load(os.path.join(directory, "v1_model.joblib")))
