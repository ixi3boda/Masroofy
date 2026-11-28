"""Where results go, how completion is marked, and the experiment log.

Rules that make interrupted Colab sessions safe:
  * every file is written to <name>.tmp and then os.replace()d, so a disconnect
    mid-write never leaves a half-written metrics.json behind;
  * a run is complete only when its DONE.json marker exists, written last;
  * a completed run is never overwritten unless the caller passes overwrite=True;
  * every start, finish and failure is appended to experiment_log.jsonl, so a
    failed run is recorded, not silently skipped.
"""
import csv
import datetime as dt
import json
import os
import platform
import shutil
import sys
import traceback

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from config import settings as S                      # noqa: E402


def root():
    return S.OUTPUT_ROOT


def model_dir(split, experiment, model):
    return os.path.join(root(), "models", split, experiment, model)


def checkpoint_dir(split, experiment, model):
    """Where a transformer's per-epoch checkpoints go: S.CHECKPOINT_ROOT (Colab's
    local disk) when set, else beside the model."""
    if S.CHECKPOINT_ROOT:
        return os.path.join(S.CHECKPOINT_ROOT, split, experiment, model)
    return model_dir(split, experiment, model)


def checkpoint_backup(split, experiment, model, log=print):
    """The Drive backup for this run, or None when S.CHECKPOINT_BACKUP is unset."""
    if not S.CHECKPOINT_BACKUP:
        return None
    from classification.checkpoint_backup import CheckpointBackup
    return CheckpointBackup(S.CHECKPOINT_BACKUP, f"{split}/{experiment}/{model}",
                            slots=S.CHECKPOINT_BACKUP_SLOTS, every=S.CHECKPOINT_BACKUP_EVERY,
                            log=log)


def result_dir(split, experiment, model):
    return os.path.join(root(), "results", split, experiment, model)


def stage_dir(split, name):
    """results/<split>/<name>/ for extraction, end_to_end, summary."""
    return os.path.join(root(), "results", split, name)


def now():
    return dt.datetime.now().isoformat(timespec="seconds")


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False, default=_default)
    os.replace(tmp, path)


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    os.replace(tmp, path)


def _default(o):
    try:
        import numpy as np
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
    except ImportError:
        pass
    return str(o)


def is_done(directory):
    return os.path.exists(os.path.join(directory, "DONE.json"))


def mark_done(directory, **info):
    write_json(os.path.join(directory, "DONE.json"), dict(finished=now(), **info))


def clear(directory):
    """Remove a previous (complete or partial) result before an explicit overwrite."""
    if os.path.isdir(directory):
        shutil.rmtree(directory)


def log(event, **fields):
    os.makedirs(root(), exist_ok=True)
    rec = {"time": now(), "event": event, **fields}
    with open(os.path.join(root(), "experiment_log.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, default=_default) + "\n")


def read_log():
    path = os.path.join(root(), "experiment_log.jsonl")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def environment():
    env = {"python": platform.python_version(), "platform": platform.platform()}
    for mod in ("sklearn", "numpy", "torch", "transformers"):
        try:
            env[mod] = __import__(mod).__version__
        except ImportError:
            env[mod] = None
    try:
        import torch
        env["cuda"] = torch.cuda.is_available()
        if env["cuda"]:
            env["gpu"] = torch.cuda.get_device_name(0)
    except ImportError:
        env["cuda"] = False
    env["code_version"] = code_version()
    return env


def code_version():
    """The pack_for_colab.py stamp when running from an archive, else the git commit."""
    stamp = os.path.join(HERE, "CODE_VERSION.json")
    if os.path.exists(stamp):
        v = read_json(stamp)
        return {k: v.get(k) for k in ("content_hash", "packed", "git_branch", "git_commit",
                                      "uncommitted")}
    try:
        import subprocess
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=HERE,
                             capture_output=True, text=True, timeout=10)
        dirty = subprocess.run(["git", "status", "--porcelain", "--", "."], cwd=HERE,
                               capture_output=True, text=True, timeout=10)
        return {"git_commit": out.stdout.strip() or None,
                "uncommitted": [ln[3:] for ln in dirty.stdout.splitlines()]}
    except (OSError, subprocess.SubprocessError):
        return None


class Run:
    """Context manager around one experiment: logs start / done / failed.

        with store.Run("classify", split=..., experiment=..., model=...) as run:
            ...
            run.info["test_macro_f1"] = 0.97
    A failure is logged with its traceback and re-raised."""

    def __init__(self, kind, **ident):
        self.kind, self.ident, self.info = kind, ident, {}

    def __enter__(self):
        log("start", kind=self.kind, **self.ident)
        return self

    def __exit__(self, et, ev, tb):
        if et is None:
            log("done", kind=self.kind, **self.ident, **self.info)
        elif et is KeyboardInterrupt:
            log("interrupted", kind=self.kind, **self.ident)
        else:
            log("failed", kind=self.kind, **self.ident, error=f"{et.__name__}: {ev}",
                traceback="".join(traceback.format_exception(et, ev, tb))[-4000:])
        return False


def dir_size(path):
    total = 0
    for dp, _, files in os.walk(path):
        for fn in files:
            try:
                total += os.path.getsize(os.path.join(dp, fn))
            except OSError:
                pass
    return total
