# Audio for evaluation

* `synthetic/` — created by `python eval/generate_audio.py` (TTS voices) with `manifest.csv`.
* `real/<speaker>/<id>.wav` — your own recordings, created by `python eval/record_audio.py --speaker <name>`
  (or copied from a phone and indexed with `--scan`). `real/manifest.csv` lists them.

Audio files are not included in the shared zip (they are large and can be regenerated).
