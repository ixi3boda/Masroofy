"""Labels are consistent with gold; splits are leak-free and reproducible."""
from collections import Counter

import pytest

from benchmark import data as D
from benchmark import splits as SP
from config import labels as L


def test_labels_validate(records):
    assert D.validate(records) == []
    assert Counter(r["label_binary"] for r in records)[L.TRANSACTION] == 1449


def test_multiclass_coarsens_to_binary(records):
    for r in records:
        assert (r["label_multi"] == L.TRANSACTION) == (r["label_binary"] == L.TRANSACTION)


def test_every_class_present(records):
    assert set(Counter(r["label_multi"] for r in records)) == set(L.CLASSES)


def test_unknown_category_is_an_error():
    rec = {"id": 1, "sms": "x", "category": "brand_new", "expected": {"is_transaction": False}}
    with pytest.raises(D.LabelError):
        D.multiclass_label(rec)


@pytest.mark.parametrize("text,cls", [
    ("Your CIB OTP is 123456. Do not share", "otp"),
    ("تم رفض المعاملة على بطاقتك الرصيد المتاح 5 EGP", "failed_transaction"),  # decline beats balance
    ("رصيد محفظة اورنچ كاش الحالي 3.68 جنيه.", "balance_inquiry"),
    ("ادفع فواتيرك باورنچ كاش واكسب 10% كاش باك", "promotional"),
    ("تم تسجيل الدخول علي حساب الانترنت البنكي", "other"),
])
def test_mixed_bucket_rules(text, cls):
    rec = {"id": 1, "sms": text, "category": "cib_none", "expected": {"is_transaction": False}}
    assert D.multiclass_label(rec)[0] == cls


@pytest.mark.parametrize("strategy", ["template", "random", "sender"])
def test_saved_splits_are_disjoint_and_complete(records, strategy):
    sides, meta = SP.load(records, strategy)
    ids = [r["id"] for s in SP.SIDES for r in sides[s]]
    assert len(ids) == len(set(ids))
    for s in SP.SIDES:
        assert len(sides[s]) > 0
    if strategy != "sender":                  # sender drops a few cross-sender near-dups
        assert len(ids) == len(records)


def test_template_split_has_no_shared_templates_or_near_duplicates(records, template_split):
    groups, _ = SP.build_groups(records, True, 0.92)
    g = {r["id"]: grp for r, grp in zip(records, groups)}
    seen = {s: {g[r["id"]] for r in template_split[s]} for s in SP.SIDES}
    assert not (seen["train"] & seen["val"])
    assert not (seen["train"] & seen["test"])
    assert not (seen["val"] & seen["test"])
    tmpl = {s: {r["template_id"] for r in template_split[s]} for s in SP.SIDES}
    assert not (tmpl["train"] & tmpl["test"])


def test_exact_duplicates_stay_together(records, template_split):
    side = {r["id"]: s for s in SP.SIDES for r in template_split[s]}
    by_text = {}
    for r in records:
        by_text.setdefault(SP.skeleton(r["sms"]), set()).add(side[r["id"]])
    assert all(len(v) == 1 for v in by_text.values())


def test_split_is_deterministic(records):
    a, _ = SP.make_split(records, "template", search=3)
    b, _ = SP.make_split(records, "template", search=3)
    assert a == b
