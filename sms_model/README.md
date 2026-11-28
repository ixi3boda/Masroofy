# sms_model — local SMS inference (AraBERT classifier → MARBERT extractor)

Runs fully offline on CPU. Both fine-tuned checkpoints are stored in this folder; nothing is
downloaded from Colab, Google Drive or Hugging Face at run time.

```
sms_model/
  arabert_classifier/          AraBERT 6-class classifier (Stage 1)
    classifier.json            label list, preprocessing, training config
    config.json  model.safetensors (541 MB)  tokenizer.json  tokenizer_config.json
  marbert_extractor/           MARBERT extractor (Stage 2)
    extractor.json             schema, preprocessing, training config
    heads.pt                   token / type / channel heads
    encoder/config.json  encoder/model.safetensors (651 MB)
    tokenizer.json  tokenizer_config.json
  test_sms.py                  terminal inference script (load_models / predict)
  gui_sms.py                   desktop window on top of test_sms.py
  masroofy_arabert_marbert.tar original download (backup; safe to delete)
```

## Selected checkpoints

Taken from the experiments in `sms_v2/sms_tests_results.ipynb` (split `template`, unseen templates):

| | AraBERT classifier | MARBERT extractor |
|---|---|---|
| Base model | `aubmindlab/bert-base-arabertv02` | `UBC-NLP/MARBERT` |
| Trained in | section 5, `multiclass/arabert` | E1.1a, `extractor/marbert` |
| Training | best epoch 3 of 6, lr 3e-5, max_len 160 | best epoch 10 of 10, lr 3e-5, max_len 160 |
| Test result | accuracy 0.985, macro-F1 0.935, 0 missed / 0 false transactions | amount 0.988, counterparty F1 0.858, direction 0.735, type 0.633, full record 0.437 |
| Together (E1.3) | end-to-end exact-record F1 0.439, 0 false records | |

**Verified locally (CPU, offline):** re-running these two folders on the same 336 test messages gives
exactly the notebook numbers (accuracy 0.985, 0 missed / 0 false; extractor fields identical to 3 decimals).

Classes: `transaction`, `balance_inquiry`, `otp`, `promotional`, `failed_transaction`, `other`.
Only `transaction` is sent to the extractor.

## Install

Python 3.12, CPU only. The script reuses the experiment code in `../sms_v2/`, so keep both folders
side by side in the repo.

```
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install transformers tokenizers numpy scikit-learn
```

Tested with torch 2.9.1+cpu, transformers 4.51.3, tokenizers 0.21.4, numpy 1.26.4, scikit-learn 1.7.2.
(The checkpoints were saved by transformers 5.22.1 on Colab and load correctly with 4.51.3.)

## Run

From this folder:

```
python test_sms.py                         # paste an SMS, Enter; empty line quits
python test_sms.py --sms "تم خصم 250.00 جنيه من حسابك ****4321 لدى CARREFOUR MAADI"
```

### Desktop window (GUI)

```
python gui_sms.py
```

Paste an SMS (Arabic or English) and press **Analyze** (or Ctrl+Enter), or pick one from **Example**.
The window shows whether it is a transaction (and its class if not), the type, amount, direction and
merchant, and the AraBERT / MARBERT / total time in ms. Every SMS is kept in the history; click a row to
show it again. **Copy result as JSON** copies the full result. Uses tkinter (part of Python, nothing to
install) and the same `load_models()` / `predict()` as `test_sms.py`; the window stays responsive
while the models load (~15–45 s) and while an SMS is analyzed.

Loading both models takes about 15–45 s (once per start). After that, each SMS on this laptop
(Intel CPU, 8 GB RAM) takes roughly 150–250 ms to classify and 150–600 ms more to extract if it is a
transaction. Memory: about 0.7 GB with both models loaded.

## Output

Transaction:
```json
{
 "sms": "تم خصم 250.00 جنيه من حسابك ****4321 لدى CARREFOUR MAADI يوم 10/08/2026",
 "is_transaction": true,
 "type": "debit",
 "amount": 250.0,
 "currency": "EGP",
 "direction": "deducted",
 "merchant": "CARREFOUR MAADI",
 "class": "transaction",
 "transaction_probability": 0.99,
 "reason": null,
 "timing_ms": {"classification": 165.8, "extraction": 199.5, "total": 386.0}
}
```

Not a transaction (extraction skipped):
```json
{
 "sms": "Your CIB OTP is 847237. Do not share this code with anyone.",
 "is_transaction": false,
 "type": null, "amount": null, "currency": null, "direction": null, "merchant": null,
 "class": "otp",
 "transaction_probability": 0.0006,
 "reason": "classified as otp",
 "timing_ms": {"classification": 194.4, "extraction": "skipped", "total": 194.4}
}
```

Fields:
* `type`: `debit`, `credit`, `transfer_out`, `transfer_in`, `atm_withdrawal`, `bill_payment`, `other`.
* `direction`: `deducted` (debit, transfer_out, atm_withdrawal, bill_payment), `added` (credit,
  transfer_in), `null` when the type is `other`. It is derived from `type`, as in the experiments.
* `merchant`: the counterparty span (shop, or the person for transfers); `null` if none was found.
* A transaction in which the extractor finds no amount returns `is_transaction: false` with a reason
  (same rule as `sms_v2/sms_pipeline.py`).

## Use from your app

```python
import sys; sys.path.insert(0, "path/to/sms_model")
from test_sms import load_models, predict
models = load_models()          # once, at startup
result = predict(models, sms)   # per SMS -> the dict above
```

## Limits to keep in mind

* Trained and tested on a synthetic, template-generated corpus; real users' SMS were not measured.
* Weakest fields: `type` (0.63) and `direction` (0.74) on unseen templates; let users correct them.
* Not tested on banks absent from training (`sender` split).

## Git

The model folders and the `.tar` are listed in the repo's `.gitignore` (files over 100 MB cannot go to
GitHub). Only `test_sms.py` and this README are tracked. Keep a backup of the folders (external drive
or a private Hugging Face repo).
