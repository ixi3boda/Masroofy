"""The two MARBERT models.

Stage 1  Gate       sequence classification, 2 classes: is this SMS a transaction?
Stage 2  Extractor  one encoder, three heads:
                      - token head    BIO over AMOUNT/FEE/BALANCE/LAST4/MERCHANT/
                                      CURRENCY/DATE/TIME  (17 labels)
                      - type head     7 classes, [CLS] pooled
                      - channel head  7 classes, [CLS] pooled

Why one encoder with three heads rather than three models: the fields are mutually
informative (a number right after "رصيد" is a balance *because* the message is a
debit), it is 3x less to train, and the type/channel heads regularise the token
head. Loss is the plain sum of the three cross-entropies.

Default checkpoint is UBC-NLP/MARBERT (BERT-base, 163M params, pretrained on ~1B
Arabic tweets incl. Egyptian dialect). --model-name takes anything with a fast
tokenizer; MARBERTv2, aubmindlab/bert-base-arabertv02 and xlm-roberta-base are
worth trying, the last because ~40% of this corpus is English or mixed and
MARBERT's vocabulary is Arabic-first.

Offsets: the fast tokenizer's offset_mapping indexes into bmp(sms), which is
character-for-character the same length as the original, so every span decoded
here is valid in the raw SMS too.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schema import (CHANNELS, IGNORE_INDEX, TOKEN_LABELS, TYPES)

DEFAULT_MODEL = "UBC-NLP/MARBERT"
MAX_LEN = 160          # 99.5% of this corpus fits; Orange Cash ad blocks are the tail


def require_torch(what="this command"):
    try:
        import torch                                    # noqa: F401
        import transformers                             # noqa: F401
    except ImportError:
        raise SystemExit(
            f"{what} needs PyTorch and transformers, which are not installed.\n\n"
            f"    pip install -r {os.path.join(os.path.dirname(__file__), 'requirements.txt')}\n\n"
            "That is a ~2.5 GB download, and MARBERT's weights are another ~650 MB on\n"
            "first run. On CPU a fine-tune of this corpus takes hours; a GPU takes minutes.\n"
            "To check the rest of the pipeline without any of that, use the linear gate:\n"
            "    python train.py --split random --stage gate --backend linear\n"
            "    python compare.py --splits random --v1-only")


def pick_device(requested="auto"):
    import torch
    if requested != "auto":
        return torch.device(requested)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def set_seed(seed):
    import random
    import numpy as np
    import torch
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# ------------------------------------------------------------------ encoding
def load_tokenizer(model_name):
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_name, use_fast=True)
    if not tok.is_fast:
        raise SystemExit(f"{model_name} has no fast tokenizer, so character offsets are "
                         "unavailable and the token head cannot be aligned. Pick another.")
    return tok


def encode(tok, texts, max_len=MAX_LEN, offsets=False):
    return tok(texts, truncation=True, max_length=max_len, padding=False,
               return_offsets_mapping=offsets, return_special_tokens_mask=offsets)


def pad_batch(tok, rows, keys, pad_values):
    """rows: list of dicts of lists. -> dict of torch tensors, right-padded."""
    import torch
    width = max(len(r["input_ids"]) for r in rows)
    out = {}
    for k in keys:
        fill = pad_values[k]
        out[k] = torch.tensor([r[k] + [fill] * (width - len(r[k])) for r in rows],
                              dtype=torch.long)
    out["attention_mask"] = torch.tensor(
        [[1] * len(r["input_ids"]) + [0] * (width - len(r["input_ids"])) for r in rows],
        dtype=torch.long)
    return out


# ------------------------------------------------------------------ stage 2 module
def build_extractor(model_name, dropout=0.1):
    import torch.nn as nn
    from transformers import AutoModel

    class Extractor(nn.Module):
        """Shared encoder, three heads."""

        def __init__(self):
            super().__init__()
            self.encoder = AutoModel.from_pretrained(model_name)
            h = self.encoder.config.hidden_size
            self.dropout = nn.Dropout(dropout)
            self.token_head = nn.Linear(h, len(TOKEN_LABELS))
            self.type_head = nn.Linear(h, len(TYPES))
            self.channel_head = nn.Linear(h, len(CHANNELS))

        def forward(self, input_ids, attention_mask):
            out = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
            seq = self.dropout(out.last_hidden_state)
            pooled = self.dropout(out.last_hidden_state[:, 0])
            return self.token_head(seq), self.type_head(pooled), self.channel_head(pooled)

    return Extractor()


def extractor_loss(logits, batch):
    import torch.nn as nn
    tok_logits, type_logits, chan_logits = logits
    ce_tok = nn.CrossEntropyLoss(ignore_index=IGNORE_INDEX)
    ce = nn.CrossEntropyLoss()
    loss_tok = ce_tok(tok_logits.reshape(-1, tok_logits.size(-1)), batch["token_labels"].reshape(-1))
    loss_type = ce(type_logits, batch["type_label"])
    loss_chan = ce(chan_logits, batch["channel_label"])
    return loss_tok + loss_type + loss_chan, (loss_tok.item(), loss_type.item(), loss_chan.item())


# ------------------------------------------------------------------ training loop
def train_loop(model, batches, epochs, lr, device, warmup=0.1, log_every=25,
               loss_fn=None, label="model"):
    """One plain AdamW + linear-warmup loop, shared by both stages.

    `batches` is a list of already-collated dicts; `loss_fn(model_out, batch)` returns
    (loss, parts). Kept manual so the only deps are torch + transformers — no
    accelerate, no Trainer, nothing that hides the step count.
    """
    import torch
    from torch.optim import AdamW
    from transformers import get_linear_schedule_with_warmup

    model.to(device).train()
    total = len(batches) * epochs
    opt = AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    sched = get_linear_schedule_with_warmup(opt, int(total * warmup), total)

    step = 0
    for ep in range(epochs):
        running = 0.0
        for bi, batch in enumerate(batches):
            batch = {k: v.to(device) for k, v in batch.items()}
            out = model(input_ids=batch["input_ids"], attention_mask=batch["attention_mask"])
            loss, parts = loss_fn(out, batch)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            opt.zero_grad(set_to_none=True)
            running += loss.item()
            step += 1
            if (bi + 1) % log_every == 0 or bi + 1 == len(batches):
                msg = (f"  {label} epoch {ep + 1}/{epochs} step {bi + 1}/{len(batches)} "
                       f"loss {running / (bi + 1):.4f}")
                if parts and len(parts) == 3:
                    msg += f"  (tok {parts[0]:.3f} type {parts[1]:.3f} chan {parts[2]:.3f})"
                print(msg, flush=True)
    model.eval()
    return model


# ------------------------------------------------------------------ persistence
def save_meta(out_dir, **meta):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1)


def load_meta(out_dir):
    with open(os.path.join(out_dir, "meta.json"), encoding="utf-8") as f:
        return json.load(f)


def save_extractor(model, tok, out_dir, **meta):
    import torch
    os.makedirs(out_dir, exist_ok=True)
    torch.save(model.state_dict(), os.path.join(out_dir, "extractor.pt"))
    tok.save_pretrained(out_dir)
    save_meta(out_dir, kind="extractor", token_labels=TOKEN_LABELS, types=TYPES,
              channels=CHANNELS, **meta)


def load_extractor(out_dir, device=None):
    import torch
    meta = load_meta(out_dir)
    model = build_extractor(meta["model_name"])
    state = torch.load(os.path.join(out_dir, "extractor.pt"), map_location="cpu")
    model.load_state_dict(state)
    model.eval()
    if device is not None:
        model.to(device)
    return model, load_tokenizer(out_dir), meta


def save_gate(model, tok, out_dir, **meta):
    os.makedirs(out_dir, exist_ok=True)
    model.save_pretrained(out_dir)
    tok.save_pretrained(out_dir)
    save_meta(out_dir, kind="gate", backend="marbert", **meta)


def load_gate(out_dir, device=None):
    from transformers import AutoModelForSequenceClassification
    meta = load_meta(out_dir)
    model = AutoModelForSequenceClassification.from_pretrained(out_dir)
    model.eval()
    if device is not None:
        model.to(device)
    return model, load_tokenizer(out_dir), meta
