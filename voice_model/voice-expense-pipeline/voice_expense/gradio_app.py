"""Gradio web demo: record or type an expense, review the draft, edit, confirm.

Run locally:   python -m voice_expense.gradio_app
In Colab:      python -m voice_expense.gradio_app --share   (prints a public link)

WHY a Gradio demo: it gives the team (and the graduation committee) a real
microphone -> draft -> confirm flow before the mobile app is ready, using the
same pipeline functions the REST API uses.
"""
from __future__ import annotations

import argparse
import sys
from typing import Any, Optional

from .asr import AudioValidationError, describe_backend
from .categories import category_labels
from .config import get_settings
from .pipeline import process_audio, process_text
from .schemas import ConfirmRequest, ExpenseDraft
from .storage import list_transactions, save_confirmed

EXAMPLES = [
    "دفعت 150 جنيه في Uber امبارح",
    "صرفت 250 على groceries امبارح",
    "I paid 80 pounds for coffee at Cilantro this morning",
    "اشتريت شاحن من B.Tech بألف وخمسمية جنيه",
    "دفعت ٣٠٠ كاش للدكتور يوم الخميس اللي فات",
    "dafa3t 150 f uber embare7",
]
FIELD_LABELS = {
    "amount": "Amount / المبلغ", "currency": "Currency / العملة", "merchant": "Merchant / التاجر",
    "category": "Category / الفئة", "date": "Date (YYYY-MM-DD) / التاريخ", "time": "Time (HH:MM) / الوقت",
    "payment_method": "Payment / طريقة الدفع", "note": "Note / ملاحظة",
}
FORM_FIELDS = list(FIELD_LABELS.keys())


def _label(field: str, review: list[str]) -> str:
    return ("⚠️ " + FIELD_LABELS[field] + " — please check") if field in review else FIELD_LABELS[field]


def build_demo() -> Any:
    try:
        import gradio as gr  # type: ignore
    except Exception as exc:
        print("Gradio is not installed. Run:  pip install -r requirements-demo.txt", file=sys.stderr)
        print(f"(import error: {exc})", file=sys.stderr)
        raise SystemExit(1)

    settings = get_settings()
    cat_choices = [(label, cid) for cid, label in category_labels().items()]

    def run_parse(audio_path: Optional[str], text: str, ref_time: str, extractor: str) -> list[Any]:
        ref = ref_time.strip() or None
        try:
            if audio_path:
                draft = process_audio(audio_path, now=ref, extractor=extractor)
            elif text and text.strip():
                draft = process_text(text, now=ref, extractor=extractor)
            else:
                return [None] + [gr.update() for _ in FORM_FIELDS] + ["Please record audio or type a sentence.", "", {}]
        except AudioValidationError as exc:
            return [None] + [gr.update() for _ in FORM_FIELDS] + [f"❌ {exc.message}", "", {}]
        except ValueError as exc:
            return [None] + [gr.update() for _ in FORM_FIELDS] + [f"❌ {exc}", "", {}]
        review = draft.needs_review
        values = {
            "amount": float(draft.amount) if draft.amount is not None else None,
            "currency": draft.currency,
            "merchant": draft.merchant or "",
            "category": draft.category,
            "date": draft.date.isoformat(),
            "time": draft.time or "",
            "payment_method": draft.payment_method,
            "note": draft.note or "",
        }
        updates = [gr.update(value=values[f], label=_label(f, review)) for f in FORM_FIELDS]
        status = f"**Transcript:** {draft.transcript or '(empty)'}\n\n"
        status += f"**Needs review:** {', '.join(review) if review else 'nothing — looks good ✅'}"
        if draft.warnings:
            status += "\n\n" + "\n".join(f"- ⚠️ {w}" for w in draft.warnings)
        t = draft.timings_ms
        timings = (f"| stage | ms |\n|---|---|\n| ASR | {t.asr} |\n| model load | {t.model_load} |\n"
                   f"| normalize | {t.normalize} |\n| extract | {t.extract} |\n| **total** | **{t.total}** |\n\n"
                   f"method: `{draft.extraction_method}` · language: `{draft.language}`")
        return [draft.model_dump_json()] + updates + [status, timings, draft.model_dump(mode="json")]

    def run_confirm(draft_json: Optional[str], amount: Optional[float], currency: str, merchant: str, category: str,
                    date: str, time: str, payment: str, note: str) -> tuple[str, Any]:
        if not draft_json:
            return "Parse something first.", _history()
        draft = ExpenseDraft.model_validate_json(draft_json)
        form = {
            "amount": amount, "currency": (currency or "EGP").upper(), "merchant": merchant or None,
            "category": category, "date": date, "time": time or None, "payment_method": payment, "note": note or None,
        }
        original = {
            "amount": float(draft.amount) if draft.amount is not None else None, "currency": draft.currency,
            "merchant": draft.merchant, "category": draft.category, "date": draft.date.isoformat(),
            "time": draft.time, "payment_method": draft.payment_method, "note": draft.note,
        }
        corrections = {k: v for k, v in form.items() if v != original[k]}
        try:
            saved = save_confirmed(ConfirmRequest(draft=draft, corrections=corrections))
        except ValueError as exc:
            msg = "An amount is required before saving." if str(exc) == "amount_required" else str(exc)
            return f"❌ Not saved: {msg}", _history()
        edited = ", ".join(saved.user_edited_fields) or "none"
        return f"✅ Saved as #{saved.id} (fields you corrected: {edited})", _history()

    def _history() -> list[list[Any]]:
        return [[r.id, str(r.date), float(r.amount) if r.amount is not None else None, r.currency, r.merchant or "",
                 r.category, r.payment_method, ", ".join(r.user_edited_fields)] for r in list_transactions(limit=20)]

    with gr.Blocks(title="Voice Expense Entry") as demo:
        gr.Markdown(
            "# 🎙️ Voice Expense Entry\nSpeak or type an expense in Egyptian Arabic, English or a mix. "
            "Review the draft, fix anything highlighted with ⚠️, then confirm.\n\n"
            f"ASR backend: `{describe_backend(settings)}` · extractor default: `{settings.extractor_mode}`"
        )
        with gr.Row():
            with gr.Column():
                audio_in = gr.Audio(sources=["microphone", "upload"], type="filepath", label="Record or upload")
                text_in = gr.Textbox(label="…or type the expense", placeholder="دفعت 150 جنيه في Uber امبارح", lines=2)
                ref_in = gr.Textbox(label="Reference time override (optional, e.g. 2026-11-20T14:00)", value="")
                extractor_in = gr.Radio(["rules", "hybrid", "llm"], value=settings.extractor_mode, label="Extractor")
                parse_btn = gr.Button("Parse", variant="primary")
                gr.Examples(examples=[[e] for e in EXAMPLES], inputs=[text_in])
            with gr.Column():
                status_md = gr.Markdown()
                amount_f = gr.Number(label=FIELD_LABELS["amount"])
                currency_f = gr.Dropdown(["EGP", "USD", "EUR", "SAR", "AED", "GBP"], value="EGP",
                                         label=FIELD_LABELS["currency"], allow_custom_value=True)
                merchant_f = gr.Textbox(label=FIELD_LABELS["merchant"])
                category_f = gr.Dropdown(cat_choices, value="other", label=FIELD_LABELS["category"])
                date_f = gr.Textbox(label=FIELD_LABELS["date"])
                time_f = gr.Textbox(label=FIELD_LABELS["time"])
                payment_f = gr.Dropdown(["cash", "card", "wallet", "unknown"], value="unknown",
                                        label=FIELD_LABELS["payment_method"])
                note_f = gr.Textbox(label=FIELD_LABELS["note"])
                confirm_btn = gr.Button("Confirm & save", variant="primary")
                saved_md = gr.Markdown()
        with gr.Row():
            timings_md = gr.Markdown()
            raw_json = gr.JSON(label="Draft JSON (what the mobile app receives)")
        history = gr.Dataframe(headers=["id", "date", "amount", "currency", "merchant", "category", "payment", "edited"],
                               label="Saved transactions", value=_history())
        draft_state = gr.State()
        form = [amount_f, currency_f, merchant_f, category_f, date_f, time_f, payment_f, note_f]
        parse_btn.click(run_parse, inputs=[audio_in, text_in, ref_in, extractor_in],
                        outputs=[draft_state] + form + [status_md, timings_md, raw_json])
        confirm_btn.click(run_confirm, inputs=[draft_state] + form, outputs=[saved_md, history])
    return demo


def _in_colab() -> bool:
    try:
        import google.colab  # type: ignore  # noqa: F401

        return True
    except Exception:
        return False


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Gradio demo for the voice expense pipeline")
    parser.add_argument("--share", action="store_true", help="create a public link (useful in Colab)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7860)
    args = parser.parse_args(argv)
    demo = build_demo()
    share = args.share or _in_colab()
    demo.launch(share=share, server_name=args.host, server_port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
