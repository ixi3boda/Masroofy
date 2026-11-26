"""Build or load any Stage-1 classifier by name, so callers never import a
concrete class and the pipeline can swap models without code changes."""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from classification.base_classifier import read_meta        # noqa: E402
from config import settings as S                            # noqa: E402

SKLEARN = dict(S.SKLEARN_MODELS)
TRANSFORMERS = dict(S.TRANSFORMER_MODELS)
REFERENCE = list(S.REFERENCE_MODELS)
ALL = list(SKLEARN) + list(TRANSFORMERS) + REFERENCE


def family(name):
    if name in SKLEARN:
        return "sklearn"
    if name in TRANSFORMERS:
        return "transformer"
    if name in REFERENCE:
        return "reference"
    raise KeyError(f"unknown model {name!r}; known: {', '.join(ALL)}")


def build(name, classes, **overrides):
    fam = family(name)
    if fam == "sklearn":
        from classification import sklearn_models as M
        cfg = dict(SKLEARN[name])
        kind = cfg.pop("kind")
        cls = {"lr": M.TfidfLogReg, "svm": M.TfidfLinearSVM, "nb": M.TfidfNaiveBayes}[kind]
        if kind == "svm" and "threshold" not in overrides:
            overrides["threshold"] = S.SVM_MARGIN
        overrides.setdefault("threshold", S.TRANSACTION_THRESHOLD)
        cfg.update(overrides)
        return cls(classes, **cfg)
    if fam == "transformer":
        from classification.transformer_classifier import TransformerClassifier
        cfg = dict(TRANSFORMERS[name])
        cfg.update(overrides)
        cfg.setdefault("threshold", S.TRANSACTION_THRESHOLD)
        return TransformerClassifier(classes, name, cfg.pop("checkpoint"), **cfg)
    from classification.v1_reference import V1Gate
    return V1Gate(classes, **overrides)


def load(directory, **kw):
    meta = read_meta(directory)
    fam = meta["family"]
    if fam == "sklearn":
        from classification.sklearn_models import TfidfClassifier
        return TfidfClassifier.load(directory)
    if fam == "transformer":
        from classification.transformer_classifier import TransformerClassifier
        return TransformerClassifier.load(directory, **kw)
    if fam == "reference":
        from classification.v1_reference import V1Gate
        return V1Gate.load(directory)
    raise ValueError(f"{directory}: unknown family {fam!r}")
