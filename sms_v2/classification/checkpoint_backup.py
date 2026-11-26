"""A second, verifiable copy of a transformer's resumable training state.

The per-epoch checkpoints live on the Colab VM's local disk (fast, and rewriting
them does not churn Google Drive). If the VM itself is recycled they are gone,
so after each epoch the latest state is also copied here, normally a Drive folder:

    <root>/slot_0/manifest.json
              /last/...          weights + tokenizer + training_state.pt
              /best/...          best epoch's weights (absent when best == last)
    <root>/slot_1/...

Rules
  * Slots are reused by every run and their files are OVERWRITTEN IN PLACE, never
    deleted: deleting on Drive moves files to the Trash, which keeps counting
    against the quota.
  * A slot's manifest is set to "writing" before any file is touched and to "ok"
    (with every file's size and SHA-256) only after all of them are written.
  * Drive uploads in the background and in no guaranteed order, so "ok" does not
    prove the bytes arrived. restore() re-hashes everything it copies back and
    rejects a slot that does not match; the caller then tries the next slot.
  * With 2 slots they alternate, so a disconnect in the middle of a backup still
    leaves the previous epoch intact.
"""
import datetime as dt
import hashlib
import json
import os
import shutil

MANIFEST = "manifest.json"
CHUNK = 8 << 20


class BackupCorrupt(Exception):
    pass


def _rel_files(directory):
    out = []
    for dp, _, files in os.walk(directory):
        for fn in files:
            out.append(os.path.relpath(os.path.join(dp, fn), directory).replace(os.sep, "/"))
    return sorted(out)


def _copy_hashed(src, dst):
    """Stream src -> dst (dst overwritten in place), returning {size, sha256} of the bytes read."""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    h, size = hashlib.sha256(), 0
    with open(src, "rb") as fi, open(dst, "wb") as fo:
        while True:
            b = fi.read(CHUNK)
            if not b:
                break
            h.update(b)
            fo.write(b)
            size += len(b)
        fo.flush()
        os.fsync(fo.fileno())
    return {"size": size, "sha256": h.hexdigest()}


class CheckpointBackup:
    def __init__(self, root, run, slots=2, every=1, log=print):
        self.root, self.run = root, run
        self.n = max(1, int(slots))
        self.every = max(1, int(every))
        self.log = log

    # ------------------------------------------------------------ manifests
    def slot_dir(self, i):
        return os.path.join(self.root, f"slot_{i}")

    def manifest(self, i):
        try:
            with open(os.path.join(self.slot_dir(i), MANIFEST), encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def _write_manifest(self, i, m):
        os.makedirs(self.slot_dir(i), exist_ok=True)
        with open(os.path.join(self.slot_dir(i), MANIFEST), "w", encoding="utf-8") as f:
            json.dump(m, f, indent=1)
            f.flush()
            os.fsync(f.fileno())

    def _target(self, fingerprint):
        """Slot to write next: one not holding this run's state, else this run's oldest."""
        ours = []
        for i in range(self.n):
            m = self.manifest(i)
            if m.get("state") != "ok" or m.get("fingerprint") != fingerprint:
                return i
            ours.append((m.get("epoch", 0), i))
        return min(ours)[1]

    # ------------------------------------------------------------ write
    def push(self, fingerprint, epoch, best_epoch, last_dir, best_dir, force=False):
        """Copy the state after `epoch` into a slot. -> slot index, or None if skipped."""
        if not force and epoch % self.every:
            return None
        i = self._target(fingerprint)
        old = self.manifest(i)
        reuse_best = (old.get("fingerprint") == fingerprint and old.get("best_epoch") == best_epoch
                      and any(k.startswith("best/") for k in old.get("files", {})))
        self._write_manifest(i, {"state": "writing", "run": self.run,
                                 "fingerprint": fingerprint, "epoch": epoch})
        files = {}
        for rel in _rel_files(last_dir):
            files["last/" + rel] = _copy_hashed(os.path.join(last_dir, rel),
                                                os.path.join(self.slot_dir(i), "last", rel))
        best_is_last = best_epoch == epoch
        if not best_is_last:
            if reuse_best:
                files.update({k: v for k, v in old["files"].items() if k.startswith("best/")})
            else:
                for rel in _rel_files(best_dir):
                    files["best/" + rel] = _copy_hashed(os.path.join(best_dir, rel),
                                                        os.path.join(self.slot_dir(i), "best", rel))
        self._write_manifest(i, {"state": "ok", "run": self.run, "fingerprint": fingerprint,
                                 "epoch": epoch, "best_epoch": best_epoch,
                                 "best_is_last": best_is_last, "files": files,
                                 "written": dt.datetime.now().isoformat(timespec="seconds")})
        return i

    # ------------------------------------------------------------ read
    def candidates(self, fingerprint):
        """Slots holding this run's state, newest epoch first."""
        out = []
        for i in range(self.n):
            m = self.manifest(i)
            if m.get("state") == "ok" and m.get("fingerprint") == fingerprint:
                out.append((m["epoch"], i))
        return [i for _, i in sorted(out, reverse=True)]

    def restore(self, i, last_dir, best_dir):
        """Copy slot i back into last_dir / best_dir, verifying every hash. -> its manifest.
        Raises BackupCorrupt (and leaves last_dir / best_dir untouched) on any mismatch."""
        m = self.manifest(i)
        stage = last_dir + ".restore"
        shutil.rmtree(stage, ignore_errors=True)
        try:
            for key, want in m["files"].items():
                src = os.path.join(self.slot_dir(i), *key.split("/"))
                if not os.path.exists(src):
                    raise BackupCorrupt(f"slot_{i}: {key} missing")
                got = _copy_hashed(src, os.path.join(stage, *key.split("/")))
                if got != want:
                    raise BackupCorrupt(f"slot_{i}: {key} does not match its checksum "
                                        "(upload to Drive probably never finished)")
            if m.get("best_is_last"):
                shutil.copytree(os.path.join(stage, "last"), os.path.join(stage, "best"),
                                ignore=shutil.ignore_patterns("training_state.pt"))
        except BackupCorrupt:
            shutil.rmtree(stage, ignore_errors=True)
            raise
        for sub, dst in (("last", last_dir), ("best", best_dir)):
            shutil.rmtree(dst, ignore_errors=True)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            os.replace(os.path.join(stage, sub), dst)
        shutil.rmtree(stage, ignore_errors=True)
        return m

    # ------------------------------------------------------------ cleanup
    def release(self):
        """Mark this run's slots free (after it completed, or before an overwrite).
        The files stay and are overwritten by the next run: nothing goes to the Trash."""
        for i in range(self.n):
            m = self.manifest(i)
            if m.get("run") == self.run:
                self._write_manifest(i, {"state": "free", "previous_run": self.run})


def describe(root, slots=2):
    """Rows for a status table: what each slot holds."""
    b = CheckpointBackup(root, run=None, slots=slots)
    rows = []
    for i in range(b.n):
        m = b.manifest(i)
        size = sum(f["size"] for f in m.get("files", {}).values())
        rows.append({"slot": i, "state": m.get("state", "empty"), "run": m.get("run"),
                     "epoch": m.get("epoch"), "best_epoch": m.get("best_epoch"),
                     "size_mb": round(size / 2 ** 20), "written": m.get("written")})
    return rows
