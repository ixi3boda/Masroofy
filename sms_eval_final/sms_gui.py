#!/usr/bin/env python3
"""Tiny GUI over SmsTxnModel: paste an SMS, see whether it is a transaction,
how much was added or deducted, and the merchant.

    python sms_gui.py [--model path/to/model.joblib]

Needs tkinter (bundled with python.org builds) and a trained model in this folder.
"""
import argparse, os, queue, sys, threading, tkinter as tk
from tkinter import ttk

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)          # the .joblib pickles sms_model.SmsTxnModel by name

CANDIDATE_MODELS = ["sms_txn_model.local.joblib", "sms_txn_model.joblib"]

# Which transaction types take money out of the account, and which put it in.
DEDUCTED = {"debit", "transfer_out", "atm_withdrawal", "bill_payment"}
ADDED = {"credit", "transfer_in"}

BG, CARD, FG, MUTED = "#f4f4f2", "#ffffff", "#1a1a18", "#6b6b66"
RED, GREEN, GREY = "#b3261e", "#1e7a3c", "#555550"

SAMPLE = ("Your card ending 7788 was charged EGP 1,249.00 at NOON.COM "
          "on 18/11/2026. Available balance EGP 8,431.25")


def find_model(explicit):
    if explicit:
        return explicit
    for name in CANDIDATE_MODELS:
        p = os.path.join(HERE, name)
        if os.path.exists(p):
            return p
    return None


def money(amount, currency):
    """1249.0 -> '1,249.00 EGP'"""
    if amount is None:
        return "-"
    txt = f"{amount:,.2f}"
    return f"{txt} {currency}" if currency else txt


class App:
    def __init__(self, root, model_path):
        self.root = root
        self.model = None
        self.inbox = queue.Queue()
        root.title("Masroofy - SMS transaction reader")
        root.configure(bg=BG)
        root.minsize(560, 430)

        wrap = tk.Frame(root, bg=BG)
        wrap.pack(fill="both", expand=True, padx=18, pady=16)

        tk.Label(wrap, text="Paste the SMS", bg=BG, fg=MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w")
        self.text = tk.Text(wrap, height=6, wrap="word", bg=CARD, fg=FG, relief="flat",
                            font=("Segoe UI", 10), padx=10, pady=8,
                            highlightthickness=1, highlightbackground="#ddddd8",
                            highlightcolor="#9a9a92", insertbackground=FG)
        self.text.pack(fill="x", pady=(4, 10))
        self.text.insert("1.0", SAMPLE)
        self.text.focus_set()

        row = tk.Frame(wrap, bg=BG)
        row.pack(fill="x")
        self.btn = ttk.Button(row, text="Read SMS", command=self.parse)
        self.btn.pack(side="left")
        ttk.Button(row, text="Clear", command=self.clear).pack(side="left", padx=6)
        tk.Label(row, text="Ctrl+Enter", bg=BG, fg=MUTED,
                 font=("Segoe UI", 8)).pack(side="left", padx=4)

        # ---- results card
        card = tk.Frame(wrap, bg=CARD, highlightthickness=1, highlightbackground="#ddddd8")
        card.pack(fill="both", expand=True, pady=(14, 8))
        inner = tk.Frame(card, bg=CARD)
        inner.pack(fill="both", expand=True, padx=16, pady=14)

        self.v_istx = self.field(inner, "is_transaction", 15)
        self.v_amount = self.field(inner, "amount", 22)
        self.v_merchant = self.field(inner, "merchant", 15)

        self.status = tk.Label(wrap, text="loading model...", bg=BG, fg=MUTED,
                               font=("Segoe UI", 8), anchor="w")
        self.status.pack(fill="x")

        root.bind("<Control-Return>", lambda e: self.parse())
        self.set_enabled(False)
        threading.Thread(target=self.load, args=(model_path,), daemon=True).start()
        self.root.after(80, self.drain)

    def field(self, parent, label, size):
        tk.Label(parent, text=label, bg=CARD, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w")
        v = tk.Label(parent, text="-", bg=CARD, fg=FG, font=("Segoe UI Semibold", size),
                     anchor="w", justify="left", wraplength=470)
        v.pack(anchor="w", pady=(0, 12))
        return v

    # ---- model loading, off the UI thread so the window paints straight away
    def load(self, path):
        try:
            from sms_model import SmsTxnModel
            model = SmsTxnModel.load(path)
            model.predict("test 1")      # a pickle from another sklearn fails here, not on load
            self.inbox.put(("ready", model, os.path.basename(path)))
        except Exception as e:
            try:
                import sklearn
                version = sklearn.__version__
            except Exception:
                version = "unknown"
            self.inbox.put(("failed", f"{type(e).__name__}: {e}", version))

    def drain(self):
        try:
            msg = self.inbox.get_nowait()
        except queue.Empty:
            self.root.after(80, self.drain)
            return
        if msg[0] == "ready":
            self.model, name = msg[1], msg[2]
            self.status.config(text=f"{name} - ready")
            self.set_enabled(True)
            self.parse()
        else:
            self.status.config(text="model failed to load", fg=RED)
            self.v_istx.config(text="model error", fg=RED)
            self.v_amount.config(text=msg[1], fg=MUTED, font=("Segoe UI", 9))
            self.v_merchant.config(
                text=f"This .joblib was pickled by a different scikit-learn than the "
                     f"installed {msg[2]}.\nRetrain:\n"
                     f"  python sms_model.py train sms_dataset_2200.jsonl "
                     f"sms_txn_model.local.joblib",
                fg=MUTED, font=("Consolas", 8))
        self.root.after(80, self.drain)

    def set_enabled(self, on):
        self.btn.state(["!disabled"] if on else ["disabled"])

    def clear(self):
        self.text.delete("1.0", "end")
        self.text.focus_set()

    def parse(self):
        if self.model is None:
            return
        sms = self.text.get("1.0", "end").strip()
        if not sms:
            self.show_blank()
            return
        try:
            p = self.model.predict(sms)
        except Exception as e:
            self.v_istx.config(text="error", fg=RED)
            self.v_amount.config(text=f"{type(e).__name__}: {e}", fg=MUTED, font=("Segoe UI", 9))
            self.v_merchant.config(text="-", fg=MUTED)
            return
        self.show(p)

    def show_blank(self):
        for v in (self.v_istx, self.v_amount, self.v_merchant):
            v.config(text="-", fg=MUTED)

    def show(self, p):
        istx = p["is_transaction"]
        conf = p.get("_confidence")
        self.v_istx.config(text="true" if istx else "false", fg=GREEN if istx else GREY)

        if not istx:
            reason = p.get("_reason", "not a transaction")
            self.v_amount.config(text=reason, fg=MUTED, font=("Segoe UI", 11))
            self.v_merchant.config(text="-", fg=MUTED, font=("Segoe UI Semibold", 15))
            self.status.config(text=f"confidence {conf}", fg=MUTED)
            return

        typ = p.get("type")
        amount = money(p.get("amount"), p.get("currency"))
        if typ in DEDUCTED:
            self.v_amount.config(text=f"− {amount}   deducted", fg=RED,
                                 font=("Segoe UI Semibold", 22))
        elif typ in ADDED:
            self.v_amount.config(text=f"+ {amount}   added", fg=GREEN,
                                 font=("Segoe UI Semibold", 22))
        else:                      # type "other": card repayment, reversal, unclear direction
            self.v_amount.config(text=f"{amount}   (direction unclear)", fg=GREY,
                                 font=("Segoe UI Semibold", 18))

        merchant = p.get("merchant")
        self.v_merchant.config(text=merchant or "-", fg=FG if merchant else MUTED,
                               font=("Segoe UI Semibold", 15))
        self.status.config(text=f"type {typ} - channel {p.get('channel')} - confidence {conf}",
                           fg=MUTED)


def main():
    ap = argparse.ArgumentParser(description="Simple GUI for the SMS transaction model.")
    ap.add_argument("--model", default=None,
                    help="path to a .joblib (default: sms_txn_model.local.joblib, "
                         "then sms_txn_model.joblib)")
    args = ap.parse_args()

    path = find_model(args.model)
    if path is None or not os.path.exists(path):
        sys.exit("no model found in this folder.\ntrain one:  python sms_model.py train "
                 "sms_dataset_2200.jsonl sms_txn_model.local.joblib")

    root = tk.Tk()
    try:
        root.tk.call("tk", "scaling", 1.3)      # readable on a high-DPI screen
    except tk.TclError:
        pass
    App(root, path)
    root.mainloop()


if __name__ == "__main__":
    main()
