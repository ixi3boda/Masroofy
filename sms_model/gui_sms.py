"""Desktop GUI for local SMS inference: AraBERT classifier -> MARBERT extractor (CPU, offline).

    python gui_sms.py

Same models and the same inference as test_sms.py (load_models / predict are imported from it):
paste an SMS, press Analyze (or Ctrl+Enter), and see the class, the extracted fields and the
time each stage took. Every analyzed SMS is kept in the history below; click one to show it again.
"""
import json
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_sms import load_models, predict      # noqa: E402  (sets the offline env vars on import)

EXAMPLES = [
    "تم خصم 250.00 جنيه من حسابك ****4321 لدى CARREFOUR MAADI يوم 10/08/2026",
    "تم إيداع مبلغ 5000 جنيه في حسابك رقم ****7788 بتاريخ 15/08/2026",
    "Your account ****1234 was debited with EGP 320.50 at UBER EATS on 12/08/2026",
    "You have received EGP 1,500.00 from AHMED ALI via InstaPay",
    "Your CIB OTP is 847237. Do not share this code with anyone.",
    "تم رفض المعاملة على بطاقتك المنتهية بـ **4832 بقيمة 191.00 EGP لعدم كفاية الرصيد",
    "رصيدك الحالي في حساب ****4321 هو 12,450.00 جنيه",
    "Enjoy 20% cashback on all purchases this weekend with your NBE card!",
]

GREEN, RED, AMBER, GREY = "#1a7f37", "#b42318", "#b54708", "#667085"
FONT = ("Segoe UI", 11)
BIG = ("Segoe UI Semibold", 15)


def _is_arabic(text):
    return any("؀" <= ch <= "ۿ" for ch in text)


class App:
    def __init__(self, root):
        self.root, self.models, self.results = root, None, []
        root.title("Masroofy SMS — AraBERT → MARBERT (local, CPU)")
        root.geometry("920x720")
        root.minsize(760, 600)
        ttk.Style().configure("Treeview", rowheight=24, font=("Segoe UI", 10))
        ttk.Style().configure("TButton", font=FONT)

        outer = ttk.Frame(root, padding=14)
        outer.pack(fill="both", expand=True)

        # ---- input
        ttk.Label(outer, text="SMS text", font=("Segoe UI Semibold", 11)).pack(anchor="w")
        self.inp = tk.Text(outer, height=4, wrap="word", font=("Segoe UI", 13), relief="solid", bd=1)
        self.inp.pack(fill="x", pady=(4, 8))
        self.inp.tag_configure("rtl", justify="right")
        self.inp.bind("<KeyRelease>", lambda e: self._align_input())
        self.inp.bind("<Control-Return>", lambda e: (self.analyze(), "break")[1])

        bar = ttk.Frame(outer)
        bar.pack(fill="x")
        self.btn = ttk.Button(bar, text="Analyze  (Ctrl+Enter)", command=self.analyze, state="disabled")
        self.btn.pack(side="left")
        ttk.Button(bar, text="Clear", command=self.clear).pack(side="left", padx=6)
        ttk.Label(bar, text="Example:").pack(side="left", padx=(18, 4))
        self.example = ttk.Combobox(bar, values=EXAMPLES, state="readonly", width=48, font=("Segoe UI", 10))
        self.example.pack(side="left", fill="x", expand=True)
        self.example.bind("<<ComboboxSelected>>", self._use_example)

        # ---- status
        st = ttk.Frame(outer)
        st.pack(fill="x", pady=(10, 4))
        self.status = ttk.Label(st, text="Loading models from sms_model/ …", foreground=GREY, font=FONT)
        self.status.pack(side="left")
        self.prog = ttk.Progressbar(st, mode="indeterminate", length=180)
        self.prog.pack(side="right")
        self.prog.start(12)

        # ---- result card
        card = ttk.LabelFrame(outer, text=" Result ", padding=12)
        card.pack(fill="x", pady=(6, 8))
        self.verdict = tk.Label(card, text="—", font=BIG, fg=GREY, anchor="w")
        self.verdict.grid(row=0, column=0, columnspan=4, sticky="w")
        self.detail = tk.Label(card, text="", font=("Segoe UI", 10), fg=GREY, anchor="w")
        self.detail.grid(row=1, column=0, columnspan=4, sticky="w", pady=(0, 8))

        self.vals = {}
        fields = [("Type", "type"), ("Amount", "amount"), ("Direction", "direction"), ("Merchant", "merchant")]
        for i, (label, key) in enumerate(fields):
            r, c = 2 + i // 2, (i % 2) * 2
            tk.Label(card, text=label, font=("Segoe UI", 10), fg=GREY).grid(row=r, column=c, sticky="w", padx=(0, 10))
            v = tk.Label(card, text="—", font=("Segoe UI Semibold", 13), anchor="w")
            v.grid(row=r, column=c + 1, sticky="w", padx=(0, 40), pady=2)
            self.vals[key] = v
        card.columnconfigure(1, weight=1)
        card.columnconfigure(3, weight=1)

        tim = ttk.Frame(card)
        tim.grid(row=4, column=0, columnspan=4, sticky="we", pady=(10, 0))
        self.times = {}
        for k, label in (("classification", "AraBERT classification"), ("extraction", "MARBERT extraction"),
                         ("total", "Total")):
            f = ttk.Frame(tim)
            f.pack(side="left", padx=(0, 28))
            tk.Label(f, text=label, font=("Segoe UI", 9), fg=GREY).pack(anchor="w")
            v = tk.Label(f, text="—", font=("Consolas", 13))
            v.pack(anchor="w")
            self.times[k] = v

        # ---- bottom bar (packed before the history so the history cannot push it off-screen)
        self.json_btn = ttk.Button(outer, text="Copy result as JSON", command=self.copy_json, state="disabled")
        self.json_btn.pack(side="bottom", anchor="e", pady=(8, 0))

        # ---- history
        ttk.Label(outer, text="History (click a row to show it again)",
                  font=("Segoe UI Semibold", 11)).pack(anchor="w", pady=(6, 4))
        hf = ttk.Frame(outer)
        hf.pack(fill="both", expand=True)
        cols = ("result", "amount", "direction", "merchant", "total", "sms")
        self.hist = ttk.Treeview(hf, columns=cols, show="headings", height=8)
        for c, w, title in (("result", 150, "Result"), ("amount", 110, "Amount"), ("direction", 85, "Direction"),
                            ("merchant", 150, "Merchant"), ("total", 80, "Total ms"), ("sms", 320, "SMS")):
            self.hist.heading(c, text=title, anchor="w")
            self.hist.column(c, width=w, anchor="w", stretch=(c == "sms"))
        sb = ttk.Scrollbar(hf, orient="vertical", command=self.hist.yview)
        self.hist.configure(yscrollcommand=sb.set)
        self.hist.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.hist.bind("<<TreeviewSelect>>", self._show_history)

        self.inp.focus_set()
        threading.Thread(target=self._load, daemon=True).start()

    # ------------------------------------------------------------ model loading / inference
    def _load(self):
        t = time.time()
        try:
            models = load_models()
        except BaseException as e:               # SystemExit from missing files included
            self.root.after(0, self._loaded, None, f"Could not load the models: {e}", 0)
            return
        self.root.after(0, self._loaded, models, None, time.time() - t)

    def _loaded(self, models, error, secs):
        self.prog.stop()
        self.prog.pack_forget()
        if error:
            self.status.configure(text=error, foreground=RED)
            return
        self.models = models
        self.status.configure(text=f"Models loaded in {secs:.1f} s (CPU, offline). Paste an SMS and press Analyze.",
                              foreground=GREEN)
        self.btn.configure(state="normal")

    def analyze(self):
        sms = self.inp.get("1.0", "end").strip()
        if not sms or self.models is None or str(self.btn["state"]) == "disabled":
            return
        self.btn.configure(state="disabled")
        self.status.configure(text="Analyzing …", foreground=GREY)
        threading.Thread(target=self._run, args=(sms,), daemon=True).start()

    def _run(self, sms):
        try:
            res = {"sms": sms, **predict(self.models, sms)}
            self.root.after(0, self._done, res, None)
        except Exception as e:
            self.root.after(0, self._done, None, e)

    def _done(self, res, error):
        self.btn.configure(state="normal")
        if error:
            self.status.configure(text=f"Error: {error}", foreground=RED)
            return
        self.status.configure(text="Done.", foreground=GREEN)
        self.results.append(res)
        self._show(res)
        self.hist.insert("", 0, iid=str(len(self.results) - 1), values=(
            "transaction" if res["is_transaction"] else f"not: {res['class']}",
            self._amount(res), res["direction"] or "", res["merchant"] or "",
            res["timing_ms"]["total"], res["sms"]))

    # ------------------------------------------------------------ display
    @staticmethod
    def _amount(res):
        if res["amount"] is None:
            return ""
        return f"{res['amount']:,.2f} {res['currency'] or ''}".strip()

    def _show(self, res):
        self.current = res
        self.json_btn.configure(state="normal")
        p = res["transaction_probability"]
        if res["is_transaction"]:
            self.verdict.configure(text="✔  Transaction", fg=GREEN)
            self.detail.configure(text=f"class: transaction · transaction probability {p:.3f}")
        elif res["class"] == "transaction":
            self.verdict.configure(text="⚠  No record", fg=AMBER)
            self.detail.configure(text=res["reason"])
        else:
            self.verdict.configure(text=f"✖  Not a transaction  ({res['class'].replace('_', ' ')})", fg=RED)
            self.detail.configure(text=f"{res['reason']} · transaction probability {p:.3f} · extraction skipped")
        direction = {"deducted": ("▼ deducted", RED), "added": ("▲ added", GREEN)}.get(res["direction"])
        self.vals["type"].configure(text=res["type"] or "—", fg="black")
        self.vals["amount"].configure(text=self._amount(res) or "—", fg="black")
        self.vals["direction"].configure(text=direction[0] if direction else "—",
                                         fg=direction[1] if direction else "black")
        self.vals["merchant"].configure(text=res["merchant"] or "—", fg="black")
        t = res["timing_ms"]
        self.times["classification"].configure(text=f"{t['classification']:.1f} ms")
        self.times["extraction"].configure(text="skipped" if t["extraction"] == "skipped"
                                           else f"{t['extraction']:.1f} ms")
        self.times["total"].configure(text=f"{t['total']:.1f} ms")

    def _show_history(self, _):
        sel = self.hist.selection()
        if sel:
            res = self.results[int(sel[0])]
            self._show(res)
            self._set_input(res["sms"])

    # ------------------------------------------------------------ input helpers
    def _align_input(self):
        self.inp.tag_remove("rtl", "1.0", "end")
        if _is_arabic(self.inp.get("1.0", "end")):
            self.inp.tag_add("rtl", "1.0", "end")

    def _set_input(self, text):
        self.inp.delete("1.0", "end")
        self.inp.insert("1.0", text)
        self._align_input()

    def _use_example(self, _):
        self._set_input(self.example.get())
        self.analyze()

    def clear(self):
        self.inp.delete("1.0", "end")
        self.inp.focus_set()

    def copy_json(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(json.dumps(self.current, ensure_ascii=False, indent=1))
        self.status.configure(text="Result copied to the clipboard as JSON.", foreground=GREEN)


def main():
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)        # sharp text on high-DPI Windows screens
    except Exception:
        pass
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
