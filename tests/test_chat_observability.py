from __future__ import annotations

import json
import asyncio
import re
from pathlib import Path

import httpx
from structlog.contextvars import bind_contextvars, clear_contextvars

from app import logging_config
from app.main import agent, app
from app.pii import hash_user_id


def test_chat_response_log_exposes_quality_for_dashboard(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.post(
                "/chat",
                json={
                    "user_id": "student-01",
                    "session_id": "session-01",
                    "feature": "qa",
                    "message": (
                        "Contact alice@example.com, 0901234567, "
                        "CCCD 012345678901, card 4111 1111 1111 1111"
                    ),
                },
            )

    bind_contextvars(stale_context="must-not-leak")
    try:
        response = asyncio.run(send_request())
    finally:
        clear_contextvars()

    assert response.status_code == 200
    correlation_id = response.headers["x-request-id"]
    assert re.fullmatch(r"req-[0-9a-f]{8}", correlation_id)
    assert response.headers["x-response-time-ms"].replace(".", "", 1).isdigit()
    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    request_event = next(event for event in events if event["event"] == "request_received")
    response_event = next(event for event in events if event["event"] == "response_sent")
    assert request_event["correlation_id"] == correlation_id
    assert request_event["user_id_hash"] == hash_user_id("student-01")
    assert request_event["session_id"] == "session-01"
    assert request_event["feature"] == "qa"
    assert request_event["model"] == agent.model
    assert "env" in request_event
    assert "stale_context" not in request_event
    assert response_event["quality_score"] == response.json()["quality_score"]
    assert response_event["ttft_ms"] == response.json()["ttft_ms"]
    assert response_event["tool_name"] == "retrieval"
    assert response_event["tool_success"] is True
    logging_config.get_logger().info(
        "scrubber_probe",
        service="test",
        payload={"nested": ["private@example.com", {"phone": "0901234567"}]},
    )
    serialized_logs = log_path.read_text(encoding="utf-8")
    for raw_value in (
        "alice@example.com",
        "0901234567",
        "012345678901",
        "4111 1111 1111 1111",
        "private@example.com",
    ):
        assert raw_value not in serialized_logs


def test_incoming_request_id_is_returned_in_response_and_logs(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/chat",
                headers={"x-request-id": "req-client-123"},
                json={
                    "user_id": "student-02",
                    "session_id": "session-02",
                    "feature": "qa",
                    "message": "Explain request IDs",
                },
            )

    response = asyncio.run(send_request())

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req-client-123"
    request_event = next(
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if json.loads(line)["event"] == "request_received"
    )
    assert request_event["correlation_id"] == "req-client-123"
