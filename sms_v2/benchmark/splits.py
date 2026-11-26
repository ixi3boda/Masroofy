"""Reproducible train / validation / test splits, shared by every model and both
experiments.

Leakage control
---------------
Messages are first merged into GROUPS that must never straddle two splits:

  1. exact duplicates after normalization (the corpus has 20 duplicate pairs);
  2. the manifest's `duplicate_group` (deliberate near-duplicate pairs);
  3. near-duplicates: binary character-4-gram vectors of the "skeleton" text
     (normalized, digits -> 0, whitespace collapsed) with cosine >= the
     configured threshold. This uses no labels and no learned statistics
     (no IDF), so computing it over the whole corpus leaks nothing;
  4. for the `template` strategy only: the manifest's `template_id`, so a
     wording seen in training never appears in validation or test.

Groups are merged with union-find, then assigned with StratifiedGroupKFold on the
6-class label, which keeps every class in every split as far as group sizes
allow. Binary labels are a coarsening of the 6 classes, so the binary experiment
is stratified too, on the very same rows.

Strategies
  template  primary benchmark: unseen wordings
  random    optimistic reference: only duplicate/near-duplicate grouping
  sender    test = HELD_OUT_SENDERS (an unseen bank's format), val grouped by template

Each split is saved as data/splits/<strategy>.json with the ids per side, the
seed, the data hash and the class counts, and is reloaded — not recomputed — by
every later run. Loading checks the data hash, so a changed corpus is caught.
"""
import json
import os
import re
import sys
from collections import Counter

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import spans                                         # noqa: E402
from benchmark import data as D                      # noqa: E402
from config import settings as S                      # noqa: E402

SIDES = ("train", "val", "test")


# ------------------------------------------------------------------ grouping
class _UF:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, a):
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)


def skeleton(text):
    t = spans.normalize(text).lower()
    t = re.sub(r"\d", "0", t)
    return re.sub(r"\s+", " ", t).strip()


def near_duplicate_pairs(records, threshold):
    """Pairs (i, j) of near-duplicate messages; binary char-4-gram cosine."""
    from sklearn.feature_extraction.text import CountVectorizer
    from sklearn.preprocessing import normalize as l2
    sk = [skeleton(r["sms"]) or "_" for r in records]
    X = CountVectorizer(analyzer="char", ngram_range=(4, 4), binary=True).fit_transform(sk)
    X = l2(X.astype(np.float32))
    sim = (X @ X.T).tocoo()
    return [(int(i), int(j)) for i, j, v in zip(sim.row, sim.col, sim.data)
            if i < j and v >= threshold]


def build_groups(records, by_template, threshold):
    """-> (group id per record, stats dict)."""
    n = len(records)
    uf = _UF(n)
    first = {}
    for i, r in enumerate(records):
        for key in [("sk", skeleton(r["sms"])),
                    ("dg", r["duplicate_group"]) if r["duplicate_group"] else None,
                    ("tp", r["template_id"]) if by_template else None]:
            if key is None:
                continue
            if key in first:
                uf.union(first[key], i)
            else:
                first[key] = i
    before = len({uf.find(i) for i in range(n)})
    pairs = near_duplicate_pairs(records, threshold)
    for i, j in pairs:
        uf.union(i, j)
    groups = [uf.find(i) for i in range(n)]
    stats = {"n_groups": len(set(groups)), "groups_before_near_dup": before,
             "near_dup_pairs": len(pairs),
             "largest_group": max(Counter(groups).values())}
    return groups, stats


# ------------------------------------------------------------------ assignment
def _carve(idx, y, groups, fraction, seed):
    """Pick ~`fraction` of idx as one stratified, group-disjoint fold."""
    from sklearn.model_selection import StratifiedGroupKFold
    k = max(2, int(round(1.0 / fraction)))
    sgkf = StratifiedGroupKFold(n_splits=k, shuffle=True, random_state=seed)
    idx = np.asarray(idx)
    rest, held = next(sgkf.split(idx, np.asarray(y)[idx], np.asarray(groups)[idx]))
    return idx[rest].tolist(), idx[held].tolist()


def _imbalance(y, parts):
    """Worst relative deviation of any class's share in any part from its overall share.

    Used ONLY to choose among candidate seeds; it looks at labels, never at a model."""
    total = Counter(y)
    n = len(y)
    worst = 0.0
    for part in parts:
        c = Counter(y[i] for i in part)
        for cls, cnt in total.items():
            expected = cnt / n
            worst = max(worst, abs(c.get(cls, 0) / max(len(part), 1) - expected) / expected)
    return worst


def make_split(records, strategy, seed=None, search=None):
    """-> (sides as index lists, stats).

    Large groups make any single stratified-group draw lumpy, so `search`
    candidate seeds (SPLIT_SEED, SPLIT_SEED+1, ...) are tried and the draw whose
    val/test class proportions are closest to the corpus's is kept. Deterministic."""
    seed = S.SPLIT_SEED if seed is None else seed
    search = S.SPLIT_SEARCH if search is None else search
    y = [r["label_multi"] for r in records]
    all_idx = list(range(len(records)))
    groups, gstats = build_groups(records, strategy != "random", S.NEAR_DUP_THRESHOLD)

    best = None
    for cand in range(seed, seed + max(1, search)):
        if strategy in ("template", "random"):
            rest, test = _carve(all_idx, y, groups, S.TEST_FRACTION, cand)
            val_frac = S.VAL_FRACTION / (1.0 - S.TEST_FRACTION)
            train, val = _carve(rest, y, groups, val_frac, cand + 10_000)
            score = _imbalance(y, [val, test])
        elif strategy == "sender":
            held = set(S.HELD_OUT_SENDERS)
            test = [i for i in all_idx if records[i]["sender"] in held]
            # a near-duplicate cluster spanning a held-out and a kept sender is
            # dropped from training rather than allowed to leak
            test_groups = {groups[i] for i in test}
            rest = [i for i in all_idx
                    if records[i]["sender"] not in held and groups[i] not in test_groups]
            train, val = _carve(rest, y, groups, S.VAL_FRACTION, cand + 10_000)
            score = _imbalance(y, [val])              # test is fixed by definition
        else:
            raise ValueError(f"unknown split strategy {strategy!r}; "
                             f"pick one of {S.SPLIT_STRATEGIES}")
        if best is None or score < best[0]:
            best = (score, cand, train, val, test)
    score, chosen, train, val, test = best
    gstats = dict(gstats, chosen_seed=chosen, seeds_tried=max(1, search),
                  imbalance=round(score, 4))

    sides = {"train": sorted(train), "val": sorted(val), "test": sorted(test)}
    # hard guarantees, checked every time a split is made
    for a in SIDES:
        for b in SIDES:
            if a < b:
                ga = {groups[i] for i in sides[a]}
                gb = {groups[i] for i in sides[b]}
                if ga & gb:
                    raise AssertionError(f"{strategy}: groups shared by {a} and {b}")
    return sides, gstats


def describe(records, sides):
    out = {}
    for side, idx in sides.items():
        rs = [records[i] for i in idx]
        out[side] = {"n": len(rs),
                     "binary": dict(Counter(r["label_binary"] for r in rs)),
                     "multiclass": dict(Counter(r["label_multi"] for r in rs)),
                     "senders": len({r["sender"] for r in rs}),
                     "templates": len({r["template_id"] for r in rs})}
    return out


# ------------------------------------------------------------------ persistence
def split_path(strategy):
    return os.path.join(S.SPLITS_DIR, f"{strategy}.json")


def create(records, strategy, overwrite=False):
    path = split_path(strategy)
    if os.path.exists(path) and not overwrite:
        raise FileExistsError(f"{path} exists; pass overwrite=True (--overwrite-splits) to "
                              "replace it. Replacing a split invalidates every result made on it.")
    sides, gstats = make_split(records, strategy)
    payload = {"strategy": strategy, "seed": S.SPLIT_SEED,
               "test_fraction": S.TEST_FRACTION, "val_fraction": S.VAL_FRACTION,
               "near_dup_threshold": S.NEAR_DUP_THRESHOLD,
               "data_hash": D.data_hash(S.DATA_PATH),
               "manifest_hash": D.data_hash(S.MANIFEST_PATH),
               "grouping": gstats,
               "summary": describe(records, sides),
               "ids": {s: [records[i]["id"] for i in sides[s]] for s in SIDES}}
    os.makedirs(S.SPLITS_DIR, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, ensure_ascii=False)
    os.replace(tmp, path)
    return payload


def load(records, strategy):
    """-> {"train": [records], "val": [...], "test": [...]}, plus the split's metadata."""
    path = split_path(strategy)
    if not os.path.exists(path):
        raise FileNotFoundError(f"no split at {path}; run  python bench.py prepare")
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    h = D.data_hash(S.DATA_PATH)
    if payload["data_hash"] != h:
        raise ValueError(f"split {strategy} was made from data {payload['data_hash']}, but the "
                         f"current data is {h}. Re-create it deliberately with --overwrite-splits.")
    by_id = {r["id"]: r for r in records}
    out = {s: [by_id[i] for i in payload["ids"][s]] for s in SIDES}
    seen = set()
    for s in SIDES:
        ids = set(payload["ids"][s])
        if ids & seen:
            raise ValueError(f"split {strategy}: an id appears in two sides")
        seen |= ids
    return out, payload
