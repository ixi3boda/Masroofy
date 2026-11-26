"""Tests write to a temporary OUTPUT_ROOT, never to the real results."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)


@pytest.fixture
def tmp_output(tmp_path, monkeypatch):
    from config import settings as S
    monkeypatch.setattr(S, "OUTPUT_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture(scope="session")
def records():
    from benchmark import data as D
    return D.load()


@pytest.fixture(scope="session")
def template_split(records):
    from benchmark import splits as SP
    return SP.load(records, "template")[0]
