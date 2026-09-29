from __future__ import annotations

import json
from pathlib import Path

from scripts import validate_logs


def test_validator_detects_raw_vietnamese_phone(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    log_path = tmp_path / "logs.jsonl"
    record = {
        "ts": "2026-08-10T00:00:00Z",
        "level": "info",
        "service": "api",
        "event": "request_received",
        "correlation_id": "req-12345678",
        "user_id_hash": "abc123",
        "session_id": "session-01",
        "feature": "monitoring",
        "model": "fake-llm",
        "payload": {"message_preview": "Contact 090 123 4567"},
    }
    log_path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
    monkeypatch.setattr(validate_logs, "LOG_PATH", log_path)

    validate_logs.main()

    output = capsys.readouterr().out
    assert "Potential PII leaks detected: 1" in output
    assert "phone_vn" in output
    assert "[FAILED] PII scrubbing" in output


def test_validator_detects_all_required_pii_categories(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    log_path = tmp_path / "logs.jsonl"
    record = {
        "ts": "2026-08-10T00:00:00Z",
        "level": "info",
        "service": "api",
        "event": "request_received",
        "correlation_id": "req-12345678",
        "payload": {
            "raw": (
                "person@example.com 0901234567 012345678901 "
                "378282246310005"
            )
        },
    }
    log_path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
    monkeypatch.setattr(validate_logs, "LOG_PATH", log_path)

    validate_logs.main()

    output = capsys.readouterr().out
    assert "Potential PII leaks detected: 1" in output
    for pii_type in ("email", "phone_vn", "cccd", "credit_card"):
        assert pii_type in output
