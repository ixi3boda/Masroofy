"""The three traditional baselines: TF-IDF + {Logistic Regression, Linear SVM,
Multinomial Naive Bayes}.

All three share one feature extractor (config.settings.SKLEARN_FEATURES): char_wb
2-5-grams + word 1-2-grams, fitted on the TRAINING texts only. Validation texts
are only ever transform()ed.

Model selection: each model has a small grid (SKLEARN_MODELS[...]["grid"]). Every
value is fitted on train and scored on validation by macro F1; the best is kept.
The test set is never touched here.

Class imbalance: class_weight="balanced" for LR and SVM; NB has no class_weight,
so it gets the equivalent balanced sample weights (and fit_prior=False so the
prior does not undo them).
"""
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from classification.base_classifier import (BaseClassifier, check_preprocessing,  # noqa: E402
                                            read_meta)
from config import settings as S                                                # noqa: E402


class _Features:
    """char + word TF-IDF, hstacked. Fitted once on the training texts."""

    def __init__(self, spec):
        self.spec = spec

    def fit_transform(self, texts):
        from scipy.sparse import hstack
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.vecs = [TfidfVectorizer(**self.spec[k]) for k in ("char", "word")]
        return hstack([v.fit_transform(texts) for v in self.vecs]).tocsr()

    def transform(self, texts):
        from scipy.sparse import hstack
        return hstack([v.transform(texts) for v in self.vecs]).tocsr()

    @property
    def n_features(self):
        return sum(len(v.vocabulary_) for v in self.vecs)


class TfidfClassifier(BaseClassifier):
    family = "sklearn"
    kind = None                      # "lr" | "svm" | "nb"

    def __init__(self, classes, grid=None, class_weight="balanced", features=None, **kw):
        super().__init__(classes, **kw)
        self.grid = grid or {}
        self.class_weight = class_weight
        self.feature_spec = features or S.SKLEARN_FEATURES
        self.params.update(grid=self.grid, class_weight=class_weight)

    def _estimator(self, value):
        raise NotImplementedError

    def _fit_one(self, X, y, value):
        est = self._estimator(value)
        if self.kind == "nb" and self.class_weight == "balanced":
            from sklearn.utils.class_weight import compute_sample_weight
            est.fit(X, y, sample_weight=compute_sample_weight("balanced", y))
        else:
            est.fit(X, y)
        return est

    def train(self, train_texts, train_labels, val_texts=None, val_labels=None, **kw):
        from sklearn.metrics import f1_score
        t0 = time.perf_counter()
        self.features = _Features(self.feature_spec)
        X = self.features.fit_transform(self.prepare(train_texts))
        y = np.asarray(train_labels)
        unknown = set(y) - set(self.classes)
        if unknown:
            raise ValueError(f"training labels not in classes: {unknown}")

        (param, values), = self.grid.items() if self.grid else ((None, [None]),)
        search = []
        if val_texts is not None and len(values) > 1:
            Xv = self.features.transform(self.prepare(val_texts))
            best = None
            for v in values:
                est = self._fit_one(X, y, v)
                f1 = f1_score(val_labels, est.predict(Xv), labels=self.classes,
                              average="macro", zero_division=0)
                search.append({param: v, "val_macro_f1": round(float(f1), 5)})
                if best is None or f1 > best[0]:          # ties keep the earlier value
                    best = (f1, v, est)
            _, chosen, self.est = best
        else:
            chosen = values[0]
            self.est = self._fit_one(X, y, chosen)
        self._order = [list(self.est.classes_).index(c) if c in self.est.classes_ else None
                       for c in self.classes]
        self.train_info = {"train_time_s": time.perf_counter() - t0,
                           "selected": {param: chosen} if param else {},
                           "grid_search": search, "n_features": self.features.n_features,
                           "n_train": len(train_labels)}
        return self.train_info

    def _raw(self, X):
        raise NotImplementedError

    def _scores(self, prepared):
        raw = self._raw(self.features.transform(prepared))
        fill = 0.0 if self.supports_proba else -1e9
        out = np.full((raw.shape[0], len(self.classes)), fill)
        for j, k in enumerate(self._order):
            if k is not None:
                out[:, j] = raw[:, k]
        return out

    def save(self, directory):
        import joblib
        os.makedirs(directory, exist_ok=True)
        joblib.dump(self, os.path.join(directory, "model.joblib"), compress=3)
        self.write_meta(directory)

    @classmethod
    def load(cls, directory):
        import joblib
        check_preprocessing(read_meta(directory))
        return joblib.load(os.path.join(directory, "model.joblib"))


class TfidfLogReg(TfidfClassifier):
    name, kind = "tfidf_lr", "lr"

    def _estimator(self, C):
        from sklearn.linear_model import LogisticRegression
        return LogisticRegression(C=C, max_iter=5000, class_weight=self.class_weight)

    def _raw(self, X):
        return self.est.predict_proba(X)


class TfidfLinearSVM(TfidfClassifier):
    name, kind = "tfidf_svm", "svm"
    score_type = "decision_function"
    supports_proba = False

    def _estimator(self, C):
        from sklearn.svm import LinearSVC
        return LinearSVC(C=C, class_weight=self.class_weight, max_iter=20000)

    def _raw(self, X):
        d = self.est.decision_function(X)
        if d.ndim == 1:                                  # binary: margin for classes_[1]
            d = np.stack([-d, d], axis=1)
        return d


class TfidfNaiveBayes(TfidfClassifier):
    name, kind = "tfidf_nb", "nb"

    def _estimator(self, alpha):
        from sklearn.naive_bayes import MultinomialNB
        return MultinomialNB(alpha=alpha, fit_prior=self.class_weight != "balanced")

    def _raw(self, X):
        return self.est.predict_proba(X)
