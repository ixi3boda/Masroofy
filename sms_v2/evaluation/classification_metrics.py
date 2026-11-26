"""Shared Stage-1 metrics. Every classifier, binary or multi-class, goes through
compute() so no model gets a friendlier definition.

Besides the usual accuracy / macro / weighted / per-class numbers, two figures
matter most for a finance app, and both are computed on the ROUTING decision
(transaction vs everything else), so binary and multi-class models are directly
comparable:

  transaction_recall      share of real transactions sent to extraction.
                          A miss is a lost financial record.
  transaction_precision   share of messages sent to extraction that really are
                          transactions. A false accept is a fabricated record.
  false_accept_rate       non-transactions wrongly sent to extraction / all
                          non-transactions (= 1 - non_transaction_recall).
  non_transaction_precision  of messages rejected, the share that really were
                          non-transactions (the literal "non-transaction
                          precision"; low means real transactions are being
                          thrown away).
  false_accepts_by_class  for multi-class gold labels: how many OTP / promo /
                          balance / failed / other messages were accepted.
"""
from collections import Counter

import numpy as np

import os
import sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from config import labels as L                    # noqa: E402


def _safe(a, b):
    return float(a) / b if b else None


def routing(y_true, y_pred, gold_multi=None):
    """Transaction-vs-rest metrics on the routing decision."""
    t = np.array([y == L.TRANSACTION for y in y_true])
    p = np.array([y == L.TRANSACTION for y in y_pred])
    tp, fp = int((t & p).sum()), int((~t & p).sum())
    fn, tn = int((t & ~p).sum()), int((~t & ~p).sum())
    prec, rec = _safe(tp, tp + fp), _safe(tp, tp + fn)
    out = {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
           "transaction_precision": prec, "transaction_recall": rec,
           "transaction_f1": (2 * prec * rec / (prec + rec)) if prec and rec else 0.0,
           "false_accept_rate": _safe(fp, fp + tn),
           "non_transaction_recall": _safe(tn, fp + tn),
           "non_transaction_precision": _safe(tn, tn + fn),
           "missed_transactions": fn, "false_transactions": fp}
    if gold_multi is not None:
        fa = Counter(g for g, pp in zip(gold_multi, p) if pp and g != L.TRANSACTION)
        out["false_accepts_by_class"] = dict(fa)
    return out


def compute(y_true, y_pred, classes, gold_multi=None):
    from sklearn.metrics import (accuracy_score, confusion_matrix,
                                 precision_recall_fscore_support)
    y_true, y_pred = list(y_true), list(y_pred)
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, labels=classes,
                                                 zero_division=0)
    res = {"n": len(y_true), "accuracy": float(accuracy_score(y_true, y_pred))}
    for avg in ("macro", "weighted"):
        ap, ar, af, _ = precision_recall_fscore_support(y_true, y_pred, labels=classes,
                                                        average=avg, zero_division=0)
        res[f"{avg}_precision"], res[f"{avg}_recall"], res[f"{avg}_f1"] = (
            float(ap), float(ar), float(af))
    res["per_class"] = {c: {"precision": float(p[i]), "recall": float(r[i]),
                            "f1": float(f[i]), "support": int(s[i])}
                        for i, c in enumerate(classes)}
    res["confusion_matrix"] = {"labels": classes,
                               "matrix": confusion_matrix(y_true, y_pred,
                                                          labels=classes).tolist()}
    res["routing"] = routing(y_true, y_pred, gold_multi)
    absent = [c for c in classes if s[classes.index(c)] == 0]
    if absent:
        res["classes_absent_from_gold"] = absent      # their per-class numbers mean nothing
    return res


def headline(res):
    """Flat dict of the numbers that go in comparison tables."""
    r = res["routing"]
    return {"accuracy": res["accuracy"], "macro_precision": res["macro_precision"],
            "macro_recall": res["macro_recall"], "macro_f1": res["macro_f1"],
            "weighted_f1": res["weighted_f1"],
            "transaction_precision": r["transaction_precision"],
            "transaction_recall": r["transaction_recall"],
            "transaction_f1": r["transaction_f1"],
            "false_accept_rate": r["false_accept_rate"],
            "non_transaction_precision": r["non_transaction_precision"],
            "missed_transactions": r["missed_transactions"],
            "false_transactions": r["false_transactions"]}
