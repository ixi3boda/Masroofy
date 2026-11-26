"""Every sklearn classifier honours the shared interface."""
import numpy as np
import pytest

from benchmark import data as D
from classification import registry
from classification.base_classifier import ProbabilitiesNotSupported
from config import labels as L


def _xy(side, exp):
    col = D.label_column(exp)
    return [r["sms"] for r in side], [r[col] for r in side]


@pytest.fixture(scope="module")
def small(template_split):
    return {k: v[::3] for k, v in template_split.items()}


@pytest.mark.parametrize("name", ["tfidf_lr", "tfidf_svm", "tfidf_nb"])
@pytest.mark.parametrize("exp", ["binary", "multiclass"])
def test_interface(name, exp, small, tmp_path):
    classes = D.class_list(exp)
    clf = registry.build(name, classes)
    clf.train(*_xy(small["train"], exp), *_xy(small["val"], exp))
    texts = [r["sms"] for r in small["test"][:20]] + ["", "   ", "123"]
    pred = clf.predict(texts)
    assert len(pred) == len(texts) and set(pred) <= set(classes)
    scores = clf.decision_scores(texts)
    assert scores.shape == (len(texts), len(classes))
    if clf.supports_proba:
        assert np.allclose(clf.predict_proba(texts).sum(1), 1, atol=1e-6)
    else:
        with pytest.raises(ProbabilitiesNotSupported):
            clf.predict_proba(texts)
    clf.save(str(tmp_path / "m"))
    again = registry.load(str(tmp_path / "m"))
    assert again.predict(texts) == pred
    assert "grid_search" in clf.train_info


def test_threshold_only_changes_transaction_decision(small):
    classes = D.class_list("multiclass")
    clf = registry.build("tfidf_lr", classes)
    clf.train(*_xy(small["train"], "multiclass"), *_xy(small["val"], "multiclass"))
    texts = [r["sms"] for r in small["test"]]
    base = clf.predict(texts)
    clf.threshold = 1.01                                 # nothing can reach it
    strict = clf.predict(texts)
    assert L.TRANSACTION not in strict
    for b, s in zip(base, strict):
        if b != L.TRANSACTION:
            assert b == s


def test_unknown_model_name():
    with pytest.raises(KeyError):
        registry.build("bert_large_imaginary", D.class_list("binary"))
