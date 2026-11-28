"""Folders of the two new experiments. Every path is new: nothing here points at a
folder an existing runner writes, so the existing results can never be overwritten.

    OUTPUT_ROOT/
      models/<split>/extractor/<marbert|arabert>/final/      Exp 1 transformer extractors
                                                             (beside the existing v1_sklearn/)
      models/<split>/joint/<experiment>/<model>/final/       Exp 2 joint models
      results/<split>/extractors/<model>/                    standalone extraction + test outputs
      results/<split>/combos/<experiment>/<clf>__<ext>/      Exp 1, one folder per combination
      results/<split>/joint/<experiment>/<model>/            Exp 2
      results/<split>/summary_new/                           tables, charts, REPORT_NEW.md

Checkpoints follow the classifiers' rule (S.CHECKPOINT_ROOT when set, i.e. the Colab
VM disk), and the Drive backup uses run keys that cannot collide with a classifier's
("<split>/extractor/<model>", "<split>/joint/<experiment>/<model>").
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from benchmark import store                       # noqa: E402
from config import settings as S                  # noqa: E402


class MissingCheckpoint(FileNotFoundError):
    """A model a run depends on has not been trained (or not finished)."""


def _ck(*parts):
    if S.CHECKPOINT_ROOT:
        return os.path.join(S.CHECKPOINT_ROOT, *parts)
    return os.path.join(store.root(), "models", *parts)


def _backup(key, log=print):
    if not S.CHECKPOINT_BACKUP:
        return None
    from classification.checkpoint_backup import CheckpointBackup
    return CheckpointBackup(S.CHECKPOINT_BACKUP, key, slots=S.CHECKPOINT_BACKUP_SLOTS,
                            every=S.CHECKPOINT_BACKUP_EVERY, log=log)


# ------------------------------------------------------------ Exp 1 extractors
def extractor_model_dir(split, model):
    return os.path.join(store.root(), "models", split, "extractor", model)


def extractor_checkpoint_dir(split, model):
    return _ck(split, "extractor", model)


def extractor_backup(split, model, log=print):
    return _backup(f"{split}/extractor/{model}", log)


def extractor_result_dir(split, model):
    return os.path.join(store.root(), "results", split, "extractors", model)


# ------------------------------------------------------------ Exp 1 combinations
def combo_name(classifier, extractor):
    return f"{classifier}__{extractor}"


def combo_result_dir(split, experiment, classifier, extractor):
    return os.path.join(store.root(), "results", split, "combos", experiment,
                        combo_name(classifier, extractor))


# ------------------------------------------------------------ Exp 2 joint models
def joint_model_dir(split, experiment, model):
    return os.path.join(store.root(), "models", split, "joint", experiment, model)


def joint_checkpoint_dir(split, experiment, model):
    return _ck(split, "joint", experiment, model)


def joint_backup(split, experiment, model, log=print):
    return _backup(f"{split}/joint/{experiment}/{model}", log)


def joint_result_dir(split, experiment, model):
    return os.path.join(store.root(), "results", split, "joint", experiment, model)


def summary_dir(split):
    return os.path.join(store.root(), "results", split, "summary_new")


# ------------------------------------------------------------ existing runs (read only)
def classifier_final_dir(split, experiment, model):
    return os.path.join(store.model_dir(split, experiment, model), "final")


def require_classifier(split, experiment, model):
    """-> (result_dir, final_dir) of a FINISHED Stage-1 run, or a clear error."""
    rdir = store.result_dir(split, experiment, model)
    fdir = classifier_final_dir(split, experiment, model)
    if not store.is_done(rdir):
        raise MissingCheckpoint(
            f"classifier {split}/{experiment}/{model} has not finished (no {rdir}/DONE.json). "
            f"Train it first:  python bench.py classify --models {model} "
            f"--experiments {experiment} --splits {split}")
    return rdir, fdir


def require_extractor(split, model):
    rdir = extractor_result_dir(split, model)
    if not store.is_done(rdir):
        raise MissingCheckpoint(
            f"{model} extractor on {split} has not finished (no {rdir}/DONE.json). "
            f"Train it first:  python bench.py extract-tf --models {model} --splits {split}")
    return rdir, os.path.join(extractor_model_dir(split, model), "final")
