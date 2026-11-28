"""The Colab archive: has the code and data the notebook needs, none of the results."""
import json
import tarfile

import pack_for_colab


def test_archive_contents(tmp_path):
    out, ver = pack_for_colab.pack(str(tmp_path / "sms_colab.tgz"))
    with tarfile.open(out) as t:
        names = set(t.getnames())
        stamp = json.load(t.extractfile("sms_v2/CODE_VERSION.json"))
    for need in ("sms_v2/bench.py", "sms_v2/colab.ipynb", "sms_v2/data/splits/template.json",
                 "sms_v2/classification/checkpoint_backup.py", "sms_eval_final/sms_model.py",
                 "sms_eval_final/sms_dataset_2200.jsonl", "sms_eval_final/manifest_2200.csv"):
        assert need in names, need
    bad = [n for n in names if "/outputs/" in n or "/runs/" in n or "__pycache__" in n
           or n.endswith((".tgz", ".bak", ".log", ".local.joblib"))]
    assert bad == []
    assert stamp["content_hash"] == ver["content_hash"] and stamp["n_files"] == len(names) - 1
