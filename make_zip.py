"""Package the whole project (voice-service + backend) into voice-expense-pipeline.zip to share with the team.

    python make_zip.py

Excludes things that are personal, generated or huge: .venv, __pycache__, .pytest_cache,
backend/target, node_modules, *.db, results/, model caches, generated audio, test WAVs and
.env files (your API keys and passwords must never be shared).
"""
from __future__ import annotations

import fnmatch
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "voice-expense-pipeline.zip"

EXCLUDE_DIRS = {".venv", "venv", "env", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "results",
                ".cache", ".git", ".idea", "target", "huggingface", ".ipynb_checkpoints", "node_modules",
                "flagged", ".gradio"}
EXCLUDE_FILES = {".env", "voice-expense-pipeline.zip", ".DS_Store", "Thumbs.db",
                 # real people's data stays private (labels contain their transcripts)
                 "real_labels.csv", "real.jsonl", "real_manifest.csv"}
EXCLUDE_PATTERNS = ["*.db", "*.db-journal", "*.pyc", "*.pyo", "*.zip", "*.log"]
# Generated audio is large and can be regenerated; keep only the manifests' folders.
EXCLUDE_UNDER = [("voice-service", "eval", "audio"), ("voice-service", "tests", "fixtures")]
KEEP_UNDER_EXCLUDED = {"README.md", ".gitkeep"}


def should_include(rel: Path) -> bool:
    parts = rel.parts
    if any(p in EXCLUDE_DIRS for p in parts[:-1]):
        return False
    name = parts[-1]
    if name in EXCLUDE_FILES or any(fnmatch.fnmatch(name, pat) for pat in EXCLUDE_PATTERNS):
        return False
    for prefix in EXCLUDE_UNDER:
        if parts[: len(prefix)] == prefix and name not in KEEP_UNDER_EXCLUDED:
            return False
    return True


def main() -> int:
    files = sorted(p for p in ROOT.rglob("*") if p.is_file() and should_include(p.relative_to(ROOT)))
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in files:
            zf.write(p, Path("voice-expense-pipeline") / p.relative_to(ROOT))
    size_kb = OUT.stat().st_size / 1024
    print(f"Created {OUT.name}: {len(files)} files, {size_kb:.0f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
