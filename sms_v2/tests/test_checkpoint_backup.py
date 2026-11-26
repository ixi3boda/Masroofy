"""Drive backup of transformer training state: slot rotation, verification, fallback.
The first tests use plain files; the last trains a tiny BERT and simulates a lost VM."""
import os
import shutil

import pytest

from classification.checkpoint_backup import BackupCorrupt, CheckpointBackup, describe


def _state(root, epoch, best_epoch):
    last, best = root / "ck" / "last", root / "ck" / "best"
    for d in (last, best):
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True)
    (last / "model.safetensors").write_bytes(f"weights-{epoch}".encode() * 1000)
    (last / "training_state.pt").write_bytes(f"state-{epoch}".encode())
    (best / "model.safetensors").write_bytes(f"weights-{best_epoch}".encode() * 1000)
    return str(last), str(best)


def test_slots_alternate_and_restore_newest(tmp_path):
    b = CheckpointBackup(str(tmp_path / "drive"), "t/b/m", slots=2)
    assert [b.push("fp", e, 1, *_state(tmp_path, e, 1)) for e in (1, 2, 3)] == [0, 1, 0]
    assert b.candidates("fp") == [0, 1]                    # epoch 3, then epoch 2
    assert b.candidates("other") == []
    shutil.rmtree(tmp_path / "ck")                          # the VM is gone
    last, best = str(tmp_path / "ck" / "last"), str(tmp_path / "ck" / "best")
    m = b.restore(0, last, best)
    assert m["epoch"] == 3
    assert open(os.path.join(last, "training_state.pt"), "rb").read() == b"state-3"
    assert open(os.path.join(best, "model.safetensors"), "rb").read().startswith(b"weights-1")


def test_corrupt_slot_is_rejected_and_local_dirs_kept(tmp_path):
    b = CheckpointBackup(str(tmp_path / "drive"), "t/b/m", slots=2)
    b.push("fp", 1, 1, *_state(tmp_path, 1, 1))
    last, best = _state(tmp_path, 2, 2)
    b.push("fp", 2, 2, last, best)
    # an upload that never finished: right size, wrong bytes
    p = os.path.join(b.slot_dir(1), "last", "model.safetensors")
    data = bytearray(open(p, "rb").read())
    data[10] ^= 0xFF
    open(p, "wb").write(bytes(data))
    with pytest.raises(BackupCorrupt):
        b.restore(1, last, best)
    assert open(os.path.join(last, "training_state.pt"), "rb").read() == b"state-2"
    assert b.restore(0, last, best)["epoch"] == 1           # the fallback slot
    assert os.path.exists(os.path.join(best, "model.safetensors"))   # best == last copied


def test_release_frees_without_deleting(tmp_path):
    b = CheckpointBackup(str(tmp_path / "drive"), "t/b/m", slots=2)
    b.push("fp", 1, 1, *_state(tmp_path, 1, 1))
    b.release()
    assert b.candidates("fp") == []
    assert os.path.exists(os.path.join(b.slot_dir(0), "last", "model.safetensors"))
    assert describe(str(tmp_path / "drive"))[0]["state"] == "free"
    assert CheckpointBackup(str(tmp_path / "drive"), "x", slots=2).push(
        "fp2", 1, 1, *_state(tmp_path, 1, 1)) == 0          # free slot reused first


def test_every_n_epochs(tmp_path):
    b = CheckpointBackup(str(tmp_path / "drive"), "t/b/m", slots=1, every=2)
    assert b.push("fp", 1, 1, *_state(tmp_path, 1, 1)) is None
    assert b.push("fp", 2, 1, *_state(tmp_path, 2, 1)) == 0
    assert b.push("fp", 3, 1, *_state(tmp_path, 3, 1), force=True) == 0


def test_transformer_resumes_from_backup_after_vm_loss(template_split, tmp_path):
    torch = pytest.importorskip("torch")
    pytest.importorskip("transformers")
    from transformers import AutoTokenizer
    tiny = "hf-internal-testing/tiny-random-bert"
    try:
        AutoTokenizer.from_pretrained(tiny)
    except Exception as e:
        pytest.skip(f"cannot fetch {tiny}: {e}")
    from benchmark import data as D
    from classification import registry

    classes = D.class_list("binary")
    tr, va = template_split["train"][::12], template_split["val"][::10]
    args = ([r["sms"] for r in tr], [r["label_binary"] for r in tr],
            [r["sms"] for r in va], [r["label_binary"] for r in va])
    hp = dict(checkpoint=tiny, epochs=3, batch_size=16, early_stopping_patience=5, device="cpu")
    work = tmp_path / "local"
    backup = CheckpointBackup(str(tmp_path / "drive"), "template/binary/marbert", slots=2)

    class Interrupt(Exception):
        pass

    def stop(msg):
        if "epoch 3/3 step" in msg:
            raise Interrupt()

    with pytest.raises(Interrupt):
        registry.build("marbert", classes, **hp).train(
            *args, work_dir=str(work), train_ids=[r["id"] for r in tr], log=stop, backup=backup)
    shutil.rmtree(work)                                     # VM recycled: local disk gone
    newest = backup.candidates(backup.manifest(0)["fingerprint"])[0]
    assert backup.manifest(newest)["epoch"] == 2
    p = os.path.join(backup.slot_dir(newest), "last", "training_state.pt")
    with open(p, "r+b") as f:                               # half-uploaded newest slot
        f.seek(100)
        f.write(b"\0" * 64)

    logs = []
    info = registry.build("marbert", classes, **hp).train(
        *args, work_dir=str(work), train_ids=[r["id"] for r in tr], log=logs.append,
        backup=backup)
    assert any("unusable" in m for m in logs)
    assert info["resumed_from"] == f"backup slot_{1 - newest}"
    assert [h["epoch"] for h in info["history"]] == [1, 2, 3]
    assert info["backup_errors"] == []
    assert torch.load(work / "checkpoints" / "last" / "training_state.pt",
                      weights_only=False)["epoch"] == 3
