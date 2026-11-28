"""Real-dataset workflow: label sheet -> import -> audio evaluation (mock ASR, offline)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval import evaluate, import_labels, make_label_sheet
from tests.conftest import write_wav


def test_parsers() -> None:
    assert str(import_labels.parse_date("2026-11-20")) == "2026-11-20"
    assert str(import_labels.parse_date("05/11/2026")) == "2026-11-05"  # day/month/year
    assert import_labels.parse_time("7:30 pm") == "19:30"
    assert import_labels.parse_time("19:30:00") == "19:30"
    assert import_labels.parse_time("") is None
    assert import_labels.parse_reference("25/11/2026 18:30").isoformat() == "2026-11-25T18:30:00+02:00"
    assert import_labels.parse_reference("2026-11-25 18:30").hour == 18
    assert import_labels.parse_amount("1,500") == 1500.0
    with pytest.raises(ValueError):
        import_labels.parse_amount("-5")


def test_full_workflow(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ASR_BACKEND", "mock")
    audio = tmp_path / "collected" / "sara"
    write_wav(audio / "n1.wav", 0.5)
    (audio / "n1.txt").write_text("دفعت 150 جنيه في Uber امبارح", encoding="utf-8")
    write_wav(audio / "n2.wav", 0.5)
    (audio / "n2.txt").write_text("paid 80 pounds for coffee", encoding="utf-8")
    write_wav(audio / "n3.wav", 0.5)
    sheet = tmp_path / "labels.csv"
    assert make_label_sheet.main(["--audio-dir", str(tmp_path / "collected"), "--out", str(sheet)]) == 0
    rows = make_label_sheet.read_sheet(sheet)
    assert len(rows) == 3 and rows[0]["speaker"] == "sara"

    labels = {
        "n1.wav": dict(transcript="دفعت 150 جنيه في Uber امبارح", lang_group="mixed", amount="150", merchant="أوبر",
                       category="transport", date="19/11/2026"),
        "n2.wav": dict(transcript="paid 80 pounds for coffee", lang_group="en", amount="80", category="food_dining",
                       date="2026-11-20"),
        "n3.wav": dict(transcript="something", lang_group="en", amount="10", category="not_a_category",
                       date="2026-11-20"),
    }
    for r in rows:
        r.update(labels[Path(r["file"]).name], reference_time="2026-11-20 14:00", checked="yes")
    make_label_sheet.write_sheet(sheet, rows)
    out, man = tmp_path / "real.jsonl", tmp_path / "real_manifest.csv"
    args = ["--sheet", str(sheet), "--out", str(out), "--manifest", str(man)]
    assert import_labels.main(args) == 1          # the bad category blocks the import
    assert import_labels.main(args + ["--skip-invalid"]) == 0
    data = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert len(data) == 2 and data[0]["expected"]["merchant"] == "Uber" and data[0]["expected"]["date"] == "2026-11-19"

    res = tmp_path / "res"
    assert evaluate.main(["--mode", "audio", "--dataset", str(out), "--manifest", str(man),
                          "--asr-backend", "mock", "--out", str(res)]) == 0
    report = next(res.glob("*/report.md")).read_text(encoding="utf-8")
    assert "95% CI" in report and "WER" in report and "| amount | 100.0" in report


def test_new_files_are_appended_without_losing_labels(tmp_path: Path) -> None:
    d = tmp_path / "c" / "ali"
    write_wav(d / "a.wav", 0.3)
    sheet = tmp_path / "s.csv"
    make_label_sheet.main(["--audio-dir", str(tmp_path / "c"), "--out", str(sheet)])
    rows = make_label_sheet.read_sheet(sheet)
    rows[0]["transcript"] = "دفعت 20 جنيه"
    make_label_sheet.write_sheet(sheet, rows)
    write_wav(d / "b.wav", 0.3)
    make_label_sheet.main(["--audio-dir", str(tmp_path / "c"), "--out", str(sheet)])
    rows = make_label_sheet.read_sheet(sheet)
    assert len(rows) == 2 and rows[0]["transcript"] == "دفعت 20 جنيه"
