from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts.render_dashboard import collect_snapshot, render_dashboard


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_snapshot_sums_cost_per_minute(tmp_path: Path) -> None:
    records = [
        {"ts": "2026-09-29T12:00:01Z", "event": "request_received"},
        {
            "ts": "2026-09-29T12:00:02Z",
            "event": "response_sent",
            "latency_ms": 1000,
            "ttft_ms": 100,
            "cost_usd": 0.004,
            "tokens_in": 10,
            "tokens_out": 5,
            "quality_score": 0.8,
            "tool_name": "retrieval",
            "tool_success": True,
        },
        {"ts": "2026-09-29T12:00:03Z", "event": "request_received"},
        {
            "ts": "2026-09-29T12:00:04Z",
            "event": "response_sent",
            "latency_ms": 1200,
            "ttft_ms": 120,
            "cost_usd": 0.006,
            "tokens_in": 12,
            "tokens_out": 6,
            "quality_score": 0.9,
            "tool_name": "retrieval",
            "tool_success": True,
        },
        {"ts": "2026-09-29T12:30:01Z", "event": "app_started"},
    ]
    log_path = tmp_path / "logs.jsonl"
    log_path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )

    config, snapshot, generated_at = collect_snapshot(
        log_path,
        REPO_ROOT / "config" / "dashboard.yaml",
        now=datetime(2026, 9, 29, 12, 31, tzinfo=timezone.utc),
    )
    html = render_dashboard(config, snapshot, generated_at)

    assert snapshot["cost_total"] == pytest.approx(0.01)
    assert dict(snapshot["cost_buckets"])["12:00"] == pytest.approx(0.01)
    assert dict(snapshot["request_buckets"])["12:00"] == 2
    assert "12:30" not in dict(snapshot["request_buckets"])
    assert "6 dashboard panels" not in html
    assert html.count("<section class=") == 6
    assert "$0.0100" in html