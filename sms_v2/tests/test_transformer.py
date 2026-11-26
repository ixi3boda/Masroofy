"""Transformer path on a tiny random BERT: train, checkpoint, interrupt, resume,
save, load. Skipped without torch/transformers or without network access.
The numbers it produces mean nothing; only the mechanics are under test."""
import os

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")

from benchmark import data as D                                       # noqa: E402
from classification import registry                                   # noqa: E402

TINY = "hf-internal-testing/tiny-random-bert"


@pytest.fixture(scope="module")
def tiny_ok():
    try:
        from transformers import AutoTokenizer
        AutoTokenizer.from_pretrained(TINY)
    except Exception as e:                                             # offline
        pytest.skip(f"cannot fetch {TINY}: {e}")


def _data(split, label="label_multi"):
    tr = split["train"][::12]
    va = split["val"][::10]
    return ([r["sms"] for r in tr], [r[label] for r in tr],
            [r["sms"] for r in va], [r[label] for r in va], [r["id"] for r in tr])


class Interrupt(Exception):
    pass


def test_train_interrupt_resume_save_load(tiny_ok, template_split, tmp_path):
    classes = D.class_list("multiclass")
    hp = dict(checkpoint=TINY, epochs=3, batch_size=16, eval_batch_size=32,
              early_stopping_patience=5, device="cpu")
    xtr, ytr, xva, yva, ids = _data(template_split)

    def stop_in_epoch_2(msg):
        if "epoch 2/3 step" in msg:
            raise Interrupt()

    clf = registry.build("marbert", classes, **hp)
    with pytest.raises(Interrupt):
        clf.train(xtr, ytr, xva, yva, work_dir=str(tmp_path), train_ids=ids,
                  log=stop_in_epoch_2)
    st = torch.load(tmp_path / "checkpoints" / "last" / "training_state.pt",
                    weights_only=False)
    assert st["epoch"] == 1

    logs = []
    clf2 = registry.build("marbert", classes, **hp)
    info = clf2.train(xtr, ytr, xva, yva, work_dir=str(tmp_path), train_ids=ids,
                      log=logs.append)
    assert any("resuming" in m for m in logs)
    assert [h["epoch"] for h in info["history"]] == [1, 2, 3]

    texts = xva[:7] + ["", "\U0001F642"]
    p = clf2.predict_proba(texts)
    assert p.shape == (len(texts), len(classes))
    clf2.save(str(tmp_path / "final"))
    again = registry.load(str(tmp_path / "final"), device="cpu")
    assert again.predict(texts) == clf2.predict(texts)
    assert os.path.exists(tmp_path / "final" / "tokenizer_config.json")


def test_resume_refuses_other_config(tiny_ok, template_split, tmp_path):
    classes = D.class_list("binary")
    xtr, ytr, xva, yva, ids = _data(template_split, "label_binary")
    hp = dict(checkpoint=TINY, epochs=1, batch_size=16, device="cpu")
    registry.build("marbert", classes, **hp).train(
        xtr, ytr, xva, yva, work_dir=str(tmp_path), train_ids=ids, log=lambda m: None)
    other = registry.build("marbert", classes, **dict(hp, lr=1e-4))
    with pytest.raises(RuntimeError, match="different configuration"):
        other.train(xtr, ytr, xva, yva, work_dir=str(tmp_path), train_ids=ids,
                    log=lambda m: None)


def test_runner_end_to_end_with_tiny_model(tiny_ok, tmp_output):
    """The real runner: metrics + predictions + DONE, checkpoints cleaned, no rerun."""
    from benchmark import run_classify, store
    ov = {"checkpoint": TINY, "epochs": 1, "batch_size": 32}
    m = run_classify.run("template", "binary", "marbert", overrides=ov, device="cpu",
                         log=lambda *a: None)
    rdir = store.result_dir("template", "binary", "marbert")
    assert store.is_done(rdir) and m["n_parameters"] > 0
    assert not os.path.isdir(os.path.join(store.model_dir("template", "binary", "marbert"),
                                          "checkpoints"))
    again = run_classify.run("template", "binary", "marbert", overrides=ov, device="cpu",
                             log=lambda *a: None)
    assert again["finished"] == m["finished"]            # skipped, not overwritten


def test_runner_with_local_checkpoints_and_backup(tiny_ok, tmp_output, tmp_path, monkeypatch):
    """Colab layout: checkpoints on local disk, a backup on 'Drive', final model on OUTPUT."""
    from benchmark import run_classify, store
    from classification.checkpoint_backup import describe
    from config import settings as S
    local, drive = tmp_path / "vm_disk", tmp_path / "drive_resume"
    monkeypatch.setattr(S, "CHECKPOINT_ROOT", str(local))
    monkeypatch.setattr(S, "CHECKPOINT_BACKUP", str(drive))
    logs = []
    m = run_classify.run("template", "binary", "marbert",
                         overrides={"checkpoint": TINY, "epochs": 2, "batch_size": 32},
                         device="cpu", log=logs.append)
    assert any("backed up to slot_" in x for x in logs)
    assert m["train"]["backup_errors"] == []
    assert os.path.isdir(os.path.join(store.model_dir("template", "binary", "marbert"), "final"))
    assert not os.path.isdir(local / "template" / "binary" / "marbert" / "checkpoints")
    assert {r["state"] for r in describe(str(drive))} == {"free"}   # released, not deleted
