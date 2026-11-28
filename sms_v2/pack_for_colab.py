"""Pack the code exactly as it is on disk (committed or not) for colab.ipynb.

    python pack_for_colab.py                      # -> sms_v2/sms_colab.tgz
    python pack_for_colab.py --to "G:/My Drive/masroofy_sms_v2/code"
                                                  # also copy it there (Google Drive for desktop)

Then in the notebook either
  * CODE_SOURCE = 'drive'  : the file is at DRIVE_ROOT/code/sms_colab.tgz (copy it there by hand,
                             or with --to if Google Drive for desktop is installed), or
  * CODE_SOURCE = 'upload' : pick the file when the cell asks.

The archive holds sms_v2/ and sms_eval_final/ without results, checkpoints, caches or
archives, plus sms_v2/CODE_VERSION.json (time, git commit, uncommitted files, content hash).
That file is printed by the notebook and stored with every run's metrics, so each result
says which code produced it.
"""
import argparse
import datetime as dt
import hashlib
import io
import json
import os
import shutil
import subprocess
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))           # sms_v2/
REPO = os.path.dirname(HERE)
FOLDERS = ("sms_v2", "sms_eval_final")
SKIP_DIRS = {"outputs", "runs", "__pycache__", ".pytest_cache", ".ipynb_checkpoints", ".git"}
SKIP_SUFFIXES = (".tgz", ".tar.gz", ".zip", ".bak", ".log", ".pyc", ".local.joblib")
SKIP_FILES = {"CODE_VERSION.json"}
DEFAULT_OUT = os.path.join(HERE, "sms_colab.tgz")


def files():
    out = []
    for top in FOLDERS:
        for dp, dirs, names in os.walk(os.path.join(REPO, top)):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for n in sorted(names):
                if n in SKIP_FILES or n.endswith(SKIP_SUFFIXES):
                    continue
                full = os.path.join(dp, n)
                out.append((full, os.path.relpath(full, REPO).replace(os.sep, "/")))
    return out


def _git(*args):
    try:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def version(entries):
    h = hashlib.sha256()
    for full, arc in entries:
        h.update(arc.encode())
        with open(full, "rb") as f:
            h.update(hashlib.sha256(f.read()).digest())
    dirty = _git("status", "--porcelain", "--", *FOLDERS)
    return {"packed": dt.datetime.now().isoformat(timespec="seconds"),
            "content_hash": h.hexdigest()[:12],
            "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "git_commit": _git("rev-parse", "--short", "HEAD"),
            "uncommitted": [line[3:] for line in dirty.splitlines()] if dirty else [],
            "n_files": len(entries)}


def pack(out=DEFAULT_OUT):
    entries = files()
    ver = version(entries)
    tmp = out + ".tmp"
    with tarfile.open(tmp, "w:gz") as tar:
        for full, arc in entries:
            tar.add(full, arcname=arc, recursive=False)
        blob = json.dumps(ver, indent=1).encode()
        info = tarfile.TarInfo("sms_v2/CODE_VERSION.json")
        info.size, info.mtime = len(blob), int(dt.datetime.now().timestamp())
        tar.addfile(info, io.BytesIO(blob))
    os.replace(tmp, out)
    return out, ver


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--to", help="also copy the archive into this folder (e.g. your synced Drive)")
    a = ap.parse_args()
    out, ver = pack(a.out)
    print(f"{out}  ({os.path.getsize(out) / 2 ** 20:.1f} MB, {ver['n_files']} files)")
    print(f"version {ver['content_hash']}  branch {ver['git_branch']} @ {ver['git_commit']}"
          f"  uncommitted files: {len(ver['uncommitted'])}")
    for u in ver["uncommitted"][:15]:
        print("   ", u)
    if a.to:
        os.makedirs(a.to, exist_ok=True)
        dst = os.path.join(a.to, os.path.basename(out))
        shutil.copyfile(out, dst + ".tmp")
        os.replace(dst + ".tmp", dst)
        print("copied to", dst)


if __name__ == "__main__":
    main()
