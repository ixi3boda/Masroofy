"""A torch-free stage-1 gate, so the v2 pipeline can be exercised end to end
without a 2.5 GB install, and so compare.py can tell apart two different wins:
"MARBERT reads the fields better" from "MARBERT decides transaction-or-not better".

Deliberately plain: char + word TF-IDF into one logistic regression, no lexicon
features. It is the control, not the contender.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spans


class LinearGate:
    name = "linear"

    def __init__(self, C=8.0):
        self.C = C

    def fit(self, records):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from scipy.sparse import hstack
        texts = [spans.normalize(r["sms"]) for r in records]
        y = [bool(r["expected"]["is_transaction"]) for r in records]
        self.v_char = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5),
                                      min_df=2, sublinear_tf=True)
        self.v_word = TfidfVectorizer(analyzer="word", token_pattern=r"[A-Za-z؀-ۿ]+",
                                      ngram_range=(1, 2), min_df=2, sublinear_tf=True)
        X = hstack([self.v_char.fit_transform(texts), self.v_word.fit_transform(texts)]).tocsr()
        self.clf = LogisticRegression(C=self.C, max_iter=3000,
                                      class_weight="balanced").fit(X, y)
        return self

    def _X(self, texts):
        from scipy.sparse import hstack
        return hstack([self.v_char.transform(texts), self.v_word.transform(texts)]).tocsr()

    def predict(self, texts):
        """-> list of (is_transaction, confidence)."""
        X = self._X([spans.normalize(t) for t in texts])
        proba = self.clf.predict_proba(X)
        pos = list(self.clf.classes_).index(True)
        return [(bool(p[pos] >= 0.5), round(float(max(p)), 3)) for p in proba]

    def save(self, out_dir):
        import joblib
        os.makedirs(out_dir, exist_ok=True)
        joblib.dump(self, os.path.join(out_dir, "gate_linear.joblib"), compress=3)
        from marbert import save_meta
        save_meta(out_dir, kind="gate", backend="linear")

    @staticmethod
    def load(out_dir):
        import joblib
        return joblib.load(os.path.join(out_dir, "gate_linear.joblib"))
