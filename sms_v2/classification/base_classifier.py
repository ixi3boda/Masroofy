"""The interface every Stage-1 classifier implements.

    clf = SomeClassifier(classes=[...], **params)
    info = clf.train(train_texts, train_labels, val_texts, val_labels)
    labels = clf.predict(texts)                 # list[str]
    P = clf.predict_proba(texts)                # (n, n_classes), only if supports_proba
    S = clf.decision_scores(texts)              # (n, n_classes) raw scores, any model
    clf.save(directory);  clf = registry.load(directory)

Texts go in RAW. Each classifier applies benchmark.preprocess.prepare() with its
configured mode itself, so the caller cannot forget it and every model sees the
same normalization.

Confidence is never invented. `score_type` says what decision_scores() returns:
  "probability"        softmax / predict_proba output — LR, NB, transformers.
                       (NB's probabilities are known to be poorly calibrated.)
  "decision_function"  signed margins — the linear SVM. NOT a probability; there
                       is no predict_proba and calling it raises.

Routing threshold: if `threshold` is set, a message is labelled "transaction"
only when its transaction score reaches it (probability for probabilistic
models, margin for the SVM); otherwise it gets the best NON-transaction class.
With threshold None the decision is plain argmax.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from benchmark.preprocess import prepare_all          # noqa: E402
from config import labels as L                        # noqa: E402
from config import settings as S                      # noqa: E402


class ProbabilitiesNotSupported(NotImplementedError):
    pass


class BaseClassifier:
    name = "base"
    family = "base"
    score_type = "probability"
    supports_proba = True

    def __init__(self, classes, preprocessing=None, threshold=None, **params):
        if L.TRANSACTION not in classes:
            raise ValueError(f"classes must include {L.TRANSACTION!r}")
        self.classes = list(classes)
        self.preprocessing = preprocessing or S.PREPROCESSING
        self.threshold = threshold
        self.params = params
        self.train_info = {}

    # ------------------------------------------------------------ to implement
    def train(self, train_texts, train_labels, val_texts=None, val_labels=None, **kw):
        raise NotImplementedError

    def _scores(self, prepared_texts):
        """(n, n_classes) scores in self.classes order, for preprocessed texts."""
        raise NotImplementedError

    def save(self, directory):
        raise NotImplementedError

    @classmethod
    def load(cls, directory):
        raise NotImplementedError

    # ------------------------------------------------------------ shared
    def prepare(self, texts):
        return prepare_all(texts, self.preprocessing)

    def decision_scores(self, texts):
        return self._scores(self.prepare(texts))

    def predict_proba(self, texts):
        if not self.supports_proba:
            raise ProbabilitiesNotSupported(
                f"{self.name} produces {self.score_type} scores, not probabilities; "
                "use decision_scores() instead")
        return self.decision_scores(texts)

    def labels_from_scores(self, scores):
        scores = np.asarray(scores, dtype=float)
        tx = self.classes.index(L.TRANSACTION)
        if self.threshold is None:
            return [self.classes[i] for i in scores.argmax(1)]
        out = []
        for row in scores:
            if row[tx] >= self.threshold:
                out.append(L.TRANSACTION)
            else:
                rest = row.copy()
                rest[tx] = -np.inf
                out.append(self.classes[int(rest.argmax())])
        return out

    def predict(self, texts):
        return self.labels_from_scores(self.decision_scores(texts))

    def predict_with_scores(self, texts):
        """-> (labels, scores) with one forward pass."""
        sc = self.decision_scores(texts)
        return self.labels_from_scores(sc), sc

    def release(self):
        """Free large resources (GPU memory). No-op for CPU models."""

    # ------------------------------------------------------------ metadata
    def meta(self):
        return {"name": self.name, "family": self.family, "classes": self.classes,
                "preprocessing": self.preprocessing, "score_type": self.score_type,
                "supports_proba": self.supports_proba, "threshold": self.threshold,
                "params": self.params, "train_info": self.train_info}

    def write_meta(self, directory):
        os.makedirs(directory, exist_ok=True)
        tmp = os.path.join(directory, "classifier.json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.meta(), f, indent=1, default=str)
        os.replace(tmp, os.path.join(directory, "classifier.json"))


def read_meta(directory):
    with open(os.path.join(directory, "classifier.json"), encoding="utf-8") as f:
        return json.load(f)


def check_preprocessing(meta):
    if meta.get("preprocessing") != S.PREPROCESSING:
        raise ValueError(f"model was trained with preprocessing {meta.get('preprocessing')!r} "
                         f"but config says {S.PREPROCESSING!r}; refusing to mix them")
