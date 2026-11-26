"""Train the v2 stages on one split.

    # the full thing (needs torch + transformers, GPU strongly advised)
    python train.py --split random --stage both

    # prove the plumbing works in ~20 seconds, no torch needed
    python train.py --split random --stage gate --backend linear

    # smoke-test the MARBERT path on 64 records before committing hours
    python train.py --split random --stage both --limit 64 --epochs 1

Checkpoints land in runs/<split>/{gate,extractor}/, which is where compare.py and
predict.py look for them.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dataset
import marbert
import spans
from schema import CHANNELS, IGNORE_INDEX, TYPES

HERE = os.path.dirname(os.path.abspath(__file__))


def build_gate_batches(tok, records, batch_size, max_len):
    rows = []
    for r in records:
        enc = marbert.encode(tok, spans.bmp(r["sms"]), max_len)
        rows.append({"input_ids": enc["input_ids"],
                     "label": int(bool(r["expected"]["is_transaction"]))})
    import torch
    batches = []
    for i in range(0, len(rows), batch_size):
        chunk = rows[i:i + batch_size]
        b = marbert.pad_batch(tok, chunk, ["input_ids"], {"input_ids": tok.pad_token_id})
        b["labels"] = torch.tensor([c["label"] for c in chunk], dtype=torch.long)
        batches.append(b)
    return batches


def build_extractor_batches(tok, records, batch_size, max_len):
    """Transactions only — the extractor never sees a non-transaction, that is the
    gate's job. Records whose fields cannot be located are still used: their
    unlocatable field is simply all-O (see dataset.py coverage)."""
    rows, skipped = [], 0
    for r in records:
        exp = r["expected"]
        if not exp["is_transaction"]:
            continue
        if exp["type"] not in TYPES or exp["channel"] not in CHANNELS:
            skipped += 1
            continue
        text = spans.bmp(r["sms"])
        enc = marbert.encode(tok, text, max_len, offsets=True)
        gold = spans.gold_spans(text, exp)
        labels = dataset.bio_from_spans(enc["offset_mapping"], gold,
                                        enc["special_tokens_mask"])
        rows.append({"input_ids": enc["input_ids"], "token_labels": labels,
                     "type_label": TYPES.index(exp["type"]),
                     "channel_label": CHANNELS.index(exp["channel"])})
    if skipped:
        print(f"  skipped {skipped} records with an out-of-schema type/channel")

    import torch
    batches = []
    for i in range(0, len(rows), batch_size):
        chunk = rows[i:i + batch_size]
        b = marbert.pad_batch(tok, chunk, ["input_ids", "token_labels"],
                              {"input_ids": tok.pad_token_id,
                               "token_labels": IGNORE_INDEX})
        b["type_label"] = torch.tensor([c["type_label"] for c in chunk], dtype=torch.long)
        b["channel_label"] = torch.tensor([c["channel_label"] for c in chunk], dtype=torch.long)
        batches.append(b)
    return batches


def train_gate_marbert(train, args, out_dir):
    marbert.require_torch("training the MARBERT gate")
    from transformers import AutoModelForSequenceClassification
    import torch.nn as nn

    device = marbert.pick_device(args.device)
    tok = marbert.load_tokenizer(args.model_name)
    model = AutoModelForSequenceClassification.from_pretrained(args.model_name, num_labels=2)
    batches = build_gate_batches(tok, train, args.batch_size, args.max_len)
    print(f"  gate: {len(train)} records, {len(batches)} batches, device {device}")

    ce = nn.CrossEntropyLoss()

    def loss_fn(out, batch):
        return ce(out.logits, batch["labels"]), None

    marbert.train_loop(model, batches, args.epochs, args.lr, device,
                       loss_fn=loss_fn, label="gate")
    marbert.save_gate(model, tok, out_dir, model_name=args.model_name,
                      max_len=args.max_len, split=args.split, epochs=args.epochs)
    return out_dir


def train_gate_linear(train, args, out_dir):
    from linear_gate import LinearGate
    print(f"  gate (linear): {len(train)} records")
    gate = LinearGate().fit(train)
    gate.save(out_dir)
    return out_dir


def train_extractor(train, args, out_dir):
    marbert.require_torch("training the MARBERT extractor")
    device = marbert.pick_device(args.device)
    tok = marbert.load_tokenizer(args.model_name)
    model = marbert.build_extractor(args.model_name)
    batches = build_extractor_batches(tok, train, args.batch_size, args.max_len)
    n_tx = sum(r["expected"]["is_transaction"] for r in train)
    print(f"  extractor: {n_tx} transactions, {len(batches)} batches, device {device}")
    marbert.train_loop(model, batches, args.epochs, args.lr, device,
                       loss_fn=marbert.extractor_loss, label="extractor")
    marbert.save_extractor(model, tok, out_dir, model_name=args.model_name,
                           max_len=args.max_len, split=args.split, epochs=args.epochs)
    return out_dir


def main():
    ap = argparse.ArgumentParser(description="Train the v2 gate and/or MARBERT extractor.")
    ap.add_argument("--split", default="random", choices=dataset.SPLITS)
    ap.add_argument("--stage", default="both", choices=["gate", "extractor", "both"])
    ap.add_argument("--backend", default="marbert", choices=["marbert", "linear"],
                    help="stage-1 gate backend; the extractor is always MARBERT")
    ap.add_argument("--model-name", default=marbert.DEFAULT_MODEL)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--max-len", type=int, default=marbert.MAX_LEN)
    ap.add_argument("--device", default="auto", help="auto | cpu | cuda | mps")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0, help="train on the first N records (smoke test)")
    ap.add_argument("--out", default=None, help="default: runs/<split>")
    ap.add_argument("--data", default=dataset.DEFAULT_DATA)
    ap.add_argument("--manifest", default=dataset.DEFAULT_MANIFEST)
    args = ap.parse_args()

    out_root = args.out or os.path.join(HERE, "runs", args.split)
    data, man = dataset.load(args.data, args.manifest)
    train, test = dataset.split(data, man, args.split, args.seed)
    if args.limit:
        train = train[:args.limit]
    print(f"split {args.split}: {len(train)} train / {len(test)} test")

    if args.backend == "marbert" or args.stage in ("extractor", "both"):
        marbert.require_torch("training with MARBERT")
        marbert.set_seed(args.seed)

    t0 = time.time()
    if args.stage in ("gate", "both"):
        gate_dir = os.path.join(out_root, "gate")
        if args.backend == "linear":
            train_gate_linear(train, args, gate_dir)
        else:
            train_gate_marbert(train, args, gate_dir)
        print(f"  -> {gate_dir}")
    if args.stage in ("extractor", "both"):
        ext_dir = os.path.join(out_root, "extractor")
        train_extractor(train, args, ext_dir)
        print(f"  -> {ext_dir}")
    print(f"done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
