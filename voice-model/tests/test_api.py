"""REST API tests with FastAPI's TestClient (needs fastapi + httpx from requirements.txt)."""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
try:  # python-multipart >= 0.0.13 is imported as "python_multipart"
    import python_multipart  # type: ignore  # noqa: F401
except ImportError:
    pytest.importorskip("multipart")

from fastapi.testclient import TestClient  # noqa: E402

from voice_expense.api import app  # noqa: E402

REF = "2026-11-20T14:00:00+02:00"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_root_redirects_to_docs(client: TestClient) -> None:
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"] == "/docs"


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["asr_backend"] == "mock" and body["llm_available"] is False


def test_parse_text(client: TestClient) -> None:
    r = client.post("/v1/expenses/parse-text",
                    json={"text": "صرفت 250 على groceries امبارح", "reference_time": REF, "extractor": "rules"})
    assert r.status_code == 200
    d = r.json()
    assert d["amount"] == 250.0 and d["currency"] == "EGP" and d["category"] == "groceries"
    assert d["date"] == "2026-11-19" and d["extraction_method"] == "rules"


def test_parse_text_validation_error(client: TestClient) -> None:
    r = client.post("/v1/expenses/parse-text", json={"reference_time": REF})
    assert r.status_code == 422
    assert r.json()["error_code"] == "validation_error"


def test_parse_text_bad_extractor(client: TestClient) -> None:
    r = client.post("/v1/expenses/parse-text", json={"text": "دفعت 5", "extractor": "magic"})
    assert r.status_code == 422


def test_parse_audio_mock(client: TestClient, audio_fixtures) -> None:
    with open(audio_fixtures["ar"], "rb") as fh:
        r = client.post("/v1/expenses/parse-audio", files={"file": ("tone_ar.wav", fh, "audio/wav")},
                        data={"reference_time": REF})
    # The upload is saved under a temporary name, so the mock backend finds no sidecar transcript:
    # the API must still answer with a draft that flags everything for review.
    assert r.status_code == 200
    d = r.json()
    assert d["amount"] is None and "amount" in d["needs_review"]


def test_parse_audio_bad_format(client: TestClient) -> None:
    r = client.post("/v1/expenses/parse-audio", files={"file": ("x.txt", b"hello", "text/plain")})
    assert r.status_code == 415
    assert r.json()["error_code"] == "unsupported_audio_format"


def test_parse_audio_empty(client: TestClient) -> None:
    r = client.post("/v1/expenses/parse-audio", files={"file": ("x.wav", b"", "audio/wav")})
    assert r.status_code == 400
    assert r.json()["error_code"] == "empty_audio"


def test_confirm_and_list(client: TestClient) -> None:
    draft = client.post("/v1/expenses/parse-text", json={"text": "دفعت 150 جنيه في Uber", "reference_time": REF}).json()
    r = client.post("/v1/expenses/confirm", json={"draft": draft, "corrections": {"amount": 160, "payment_method": "card"}})
    assert r.status_code == 201, r.text
    saved = r.json()
    assert saved["id"] >= 1 and saved["amount"] == 160.0 and saved["payment_method"] == "card"
    assert sorted(saved["user_edited_fields"]) == ["amount", "payment_method"]
    lst = client.get("/v1/expenses").json()
    assert lst[0]["id"] == saved["id"]
    stats = client.get("/v1/expenses/stats").json()
    assert stats["transactions"] == 1 and stats["per_field"]["amount"] == 1


def test_confirm_without_amount(client: TestClient) -> None:
    draft = client.post("/v1/expenses/parse-text", json={"text": "دفعت تمن البنزين", "reference_time": REF}).json()
    r = client.post("/v1/expenses/confirm", json={"draft": draft})
    assert r.status_code == 422 and r.json()["error_code"] == "amount_required"


def test_confirm_invalid_correction(client: TestClient) -> None:
    draft = client.post("/v1/expenses/parse-text", json={"text": "دفعت 150 جنيه", "reference_time": REF}).json()
    r = client.post("/v1/expenses/confirm", json={"draft": draft, "corrections": {"color": "red"}})
    assert r.status_code == 422


def test_not_found_shape(client: TestClient) -> None:
    r = client.get("/nope")
    assert r.status_code == 404 and r.json()["error_code"] == "not_found"


def test_docs_available(client: TestClient) -> None:
    assert client.get("/docs").status_code == 200
    assert "parse-text" in client.get("/openapi.json").text
