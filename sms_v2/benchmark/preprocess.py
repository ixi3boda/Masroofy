"""The single text-preprocessing function every model in the benchmark uses.

Why one function: if the TF-IDF models saw ASCII digits and MARBERT saw ٢٥٠, a
difference in scores could be preprocessing rather than modelling. So the mode is
set once (config.settings.PREPROCESSING), recorded in every model's metadata, and
a model refuses to load under a different mode.

Modes
  digits        spans.normalize(): emoji -> U+FFFD (so Python/Java offsets agree),
                Arabic-Indic digits and separators -> ASCII. Length-preserving.
                This is what v1 and v2 already do, so it is the default.
  digits_light  digits + remove tatweel and harakat, unify أ/إ/آ -> ا and ى -> ي.
                NOT length-preserving, so it is used for classification only; the
                extractor always reads the original text.

Deliberately NOT done anywhere: lowercasing (each tokenizer has its own rule —
MARBERT lowercases, XLM-R is cased; TF-IDF lowercases), stop-word removal,
stemming, or Farasa segmentation.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import spans                                    # noqa: E402

MODES = ("digits", "digits_light")

_TATWEEL_HARAKAT = re.compile("[ـً-ٰٟ]")
_ALEF = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي"})


def prepare(text, mode="digits"):
    """Text -> the string a classifier sees. Never raises on odd input."""
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    out = spans.normalize(text)
    if mode == "digits":
        return out
    if mode == "digits_light":
        return _TATWEEL_HARAKAT.sub("", out).translate(_ALEF)
    raise ValueError(f"unknown preprocessing mode {mode!r}; pick one of {MODES}")


def prepare_all(texts, mode="digits"):
    return [prepare(t, mode) for t in texts]
