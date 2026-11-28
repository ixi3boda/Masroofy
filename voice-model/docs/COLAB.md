# Running in Google Colab

1. Open https://colab.research.google.com → New notebook.
2. **Runtime → Change runtime type → T4 GPU** (needed for `large-v3`; the CPU runtime works with `small`).
3. Copy each cell below in order.

### Cell 1 — upload and unzip the project
```python
from google.colab import files
uploaded = files.upload()          # choose voice-expense-pipeline.zip
!unzip -q -o voice-expense-pipeline.zip
%cd voice-expense-pipeline
!ls
```
(Alternative: put the zip in Google Drive, then `from google.colab import drive; drive.mount('/content/drive')` and `!unzip -q -o /content/drive/MyDrive/voice-expense-pipeline.zip`.)

### Cell 2 — install requirements
```python
!pip install -q -r requirements.txt -r requirements-asr.txt -r requirements-demo.txt -r requirements-audio-gen.txt
```

### Cell 3 — smoke test and unit tests (offline checks)
```python
!python scripts/smoke_test.py
!pytest -q
```

### Cell 4 — configure the GPU model
```python
import os
os.environ["WHISPER_MODEL"] = "large-v3"     # use "medium" if memory is tight, "small" on CPU runtime
os.environ["WHISPER_DEVICE"] = "cuda"        # the project default is cpu; Colab's T4 has the CUDA libraries
os.environ["ASR_BACKEND"] = "faster_whisper"
!nvidia-smi --query-gpu=name,memory.total --format=csv
```

### Cell 5 — generate synthetic audio
```python
!python eval/generate_audio.py --limit 40
```

### Cell 6 — audio evaluation (first run downloads the model, ~3 GB for large-v3)
```python
!python eval/evaluate.py --mode audio --manifest eval/audio/synthetic/manifest.csv
!python eval/evaluate.py --mode audio --manifest eval/audio/synthetic/manifest.csv --compare
import glob, IPython
latest = sorted(glob.glob("results/*/report.md"))[-1]
IPython.display.display(IPython.display.Markdown(open(latest, encoding="utf-8").read()))
```

### Cell 7 — evaluate real recordings
Record on your phone, name files by phrase id (`ar_01.m4a`, `mx_05.m4a` ...), zip the folder as `real_yourname.zip`, then:
```python
uploaded = files.upload()                         # real_yourname.zip
!mkdir -p eval/audio/real/yourname && unzip -q -o real_yourname.zip -d eval/audio/real/yourname
!python eval/record_audio.py --speaker yourname --scan
!python eval/evaluate.py --mode audio --manifest eval/audio/real/manifest.csv
```
(Make sure the files end up directly inside `eval/audio/real/yourname/`, not in a sub-folder.)

### Cell 8 — live demo with a public link
```python
!python -m voice_expense.gradio_app --share
```
Open the `https://....gradio.live` link it prints (it works on your phone too; allow microphone access). Stop the cell to end the demo.

### Cell 9 — download the results
```python
!zip -q -r results.zip results
files.download("results.zip")
```

Notes
- Colab resets after ~12 h or when idle; re-run cells 1–4.
- If you see a cuDNN/CUDA error, set `os.environ["WHISPER_DEVICE"] = "cpu"` and `WHISPER_MODEL="small"`.
