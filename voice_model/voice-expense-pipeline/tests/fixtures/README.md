# Test fixtures

This folder is filled **at test time** by `tests/conftest.py` (fixture `audio_fixtures`):

| file | what it is |
|---|---|
| `tone_ar.wav` + `tone_ar.txt` | 0.5 s sine tone; the mock ASR reads the Arabic sentence from the `.txt` |
| `tone_mixed.wav` + `tone_mixed.wav.txt` | same, using the `<audio>.wav.txt` sidecar naming |
| `silence.wav` | 0.5 s of silence with **no** transcript, to test the "nothing heard" path |

The WAV files are written with Python's built-in `wave` module, so no binary
files are stored in the repository.
