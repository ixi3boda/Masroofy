"""Voice expense entry pipeline (Arabic / English / code-switched).

Quick use:
    >>> from voice_expense import process_text
    >>> draft = process_text("دفعت 150 جنيه في Uber امبارح", now="2026-11-20T14:00")
    >>> draft.amount, draft.merchant, str(draft.date)
    (Decimal('150.00'), 'Uber', '2026-11-19')
"""
from .pipeline import process_audio, process_text
from .schemas import ConfirmedTransaction, ConfirmRequest, ExpenseDraft

__all__ = ["process_text", "process_audio", "ExpenseDraft", "ConfirmRequest", "ConfirmedTransaction"]
__version__ = "1.1.0"
