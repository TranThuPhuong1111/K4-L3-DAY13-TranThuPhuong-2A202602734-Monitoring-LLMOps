from __future__ import annotations

import argparse
import html
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def _timestamp(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None
    return parsed.astimezone(timezone.utc)


def _percentile(values: list[float], percentile: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((percentile / 100) * len(ordered) + 0.5) - 1))
    return ordered[index]


def _bar_rows(values: list[tuple[str, float]], unit: str) -> str:
    maximum = max((value for _, value in values), default=0.0) or 1.0
    rows = []
    for label, value in values:
        width = max(2, min(100, round(value / maximum * 100)))
        if unit == "req":
            value_label = f"{value:,.0f} req"
        elif unit == "USD":
            value_label = f"${value:,.4f}"
        else:
            value_label = f"{value:,.2f} {html.escape(unit)}"
        rows.append(
            f'<div class="bar-row"><span>{html.escape(label)}</span>'
            f'<div class="bar-track"><i style="width:{width}%"></i></div>'
            f'<b>{value_label}</b></div>'
        )
    return "".join(rows)


def collect_snapshot(
    log_path: Path,
    config_path: Path,
    now: datetime | None = None,
) -> tuple[dict, dict, datetime]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))["dashboard"]
    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    cutoff = current_time - timedelta(minutes=config["time_range_minutes"])
    records = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        timestamp = _timestamp(record.get("ts"))
        if timestamp is not None and cutoff <= timestamp <= current_time:
            record["_timestamp"] = timestamp
            records.append(record)

    requests = [record for record in records if record.get("event") == "request_received"]
    responses = [record for record in records if record.get("event") == "response_sent"]
    failures = [record for record in records if record.get("event") == "request_failed"]
    successful_retrievals = [
        record for record in responses
        if record.get("tool_name") == "retrieval" and record.get("tool_success") is True
    ]
    failed_retrievals = [
        record for record in failures
        if record.get("tool_name") == "retrieval" and record.get("tool_success") is False
    ]
    latencies = [float(record["latency_ms"]) for record in responses if isinstance(record.get("latency_ms"), (int, float))]
    ttft = [float(record["ttft_ms"]) for record in responses if isinstance(record.get("ttft_ms"), (int, float))]
    costs = [float(record["cost_usd"]) for record in responses if isinstance(record.get("cost_usd"), (int, float))]
    tokens_in = [int(record["tokens_in"]) for record in responses if isinstance(record.get("tokens_in"), (int, float))]
    tokens_out = [int(record["tokens_out"]) for record in responses if isinstance(record.get("tokens_out"), (int, float))]
    quality = [float(record["quality_score"]) for record in responses if isinstance(record.get("quality_score"), (int, float))]
    request_buckets: Counter[datetime] = Counter(
        record["_timestamp"].replace(second=0, microsecond=0) for record in requests
    )
    cost_buckets: dict[datetime, float] = defaultdict(float)
    for record in responses:
        cost = record.get("cost_usd")
        if isinstance(cost, (int, float)):
            minute = record["_timestamp"].replace(second=0, microsecond=0)
            cost_buckets[minute] += float(cost)
    activity_events = {"request_received", "response_sent", "request_failed"}
    activity_end = max(
        (record["_timestamp"] for record in records if record.get("event") in activity_events),
        default=current_time,
    ).replace(second=0, microsecond=0)
    recent_minutes = [
        activity_end - timedelta(minutes=offset)
        for offset in reversed(range(12))
    ]
    retrieval_attempts = len(successful_retrievals) + len(failed_retrievals)
    summary = {
        "records": len(records),
        "requests": len(requests),
        "responses": len(responses),
        "failures": len(failures),
        "error_rate_pct": 100 * len(failures) / len(requests) if requests else 0.0,
        "retrieval_success_pct": 100 * len(successful_retrievals) / retrieval_attempts if retrieval_attempts else 0.0,
        "latency_p50": _percentile(latencies, 50),
        "latency_p95": _percentile(latencies, 95),
        "latency_p99": _percentile(latencies, 99),
        "ttft_p95": _percentile(ttft, 95),
        "cost_total": sum(costs),
        "cost_avg": mean(costs) if costs else 0.0,
        "tokens_in": sum(tokens_in),
        "tokens_out": sum(tokens_out),
        "quality_mean": mean(quality) if quality else 0.0,
        "request_buckets": [(item.strftime("%H:%M"), request_buckets[item]) for item in recent_minutes],
        "cost_buckets": [(item.strftime("%H:%M"), cost_buckets[item]) for item in recent_minutes],
    }
    return config, summary, current_time


def render_dashboard(config: dict, data: dict, generated_at: datetime) -> str:
    panels = {panel["id"]: panel for panel in config["panels"]}
    latency = panels["latency"]["threshold"]["value"]
    quality_threshold = panels["quality"]["threshold"]["value"]
    traffic_bars = _bar_rows(data["request_buckets"], "req")
    cost_bars = _bar_rows(data["cost_buckets"], "USD")
    grid = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(config['title'])}</title>
<style>
:root {{ color-scheme: light; --ink:#172a3a; --muted:#627482; --line:#dce4e9; --surface:#fff; --canvas:#edf2f4; --blue:#3175ad; --amber:#b86d08; --red:#bd3c4a; --green:#187c62; --teal:#087f8c; --violet:#6755a5; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--canvas); color:var(--ink); font-family:"Segoe UI",Tahoma,sans-serif; font-size:14px; }}
header {{ display:flex; align-items:end; justify-content:space-between; gap:24px; padding:22px 28px 18px; background:#fff; border-bottom:1px solid var(--line); }}
h1 {{ margin:0; font-family:Georgia,serif; font-size:25px; font-weight:600; }}
.sub {{ margin-top:6px; color:var(--muted); }}
.meta {{ color:var(--muted); text-align:right; line-height:1.7; }}
main {{ max-width:1440px; margin:0 auto; padding:20px 24px 28px; }}
.grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px; }}
section {{ min-height:240px; padding:16px 17px; background:var(--surface); border:1px solid var(--line); border-top:3px solid var(--accent); border-radius:4px; box-shadow:0 1px 2px #1424320b; }}
.latency {{--accent:var(--amber)}} .traffic {{--accent:var(--blue)}} .errors {{--accent:var(--red)}} .cost {{--accent:var(--green)}} .tokens {{--accent:var(--teal)}} .quality {{--accent:var(--violet)}}
h2 {{ margin:0 0 5px; font-size:16px; font-weight:650; }}
.hint {{ color:var(--muted); font-size:12px; }}
.primary {{ margin:18px 0 16px; font-size:30px; font-weight:650; font-variant-numeric:tabular-nums; }}
.primary small {{ display:block; margin-top:4px; color:var(--muted); font-size:12px; font-weight:500; }}
.stats {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:8px; }}
.stat {{ padding-top:8px; border-top:1px solid var(--line); }}
.label {{ color:var(--muted); font-size:11px; text-transform:uppercase; }}
.value {{ margin-top:4px; font-size:17px; font-weight:600; font-variant-numeric:tabular-nums; }}
.bar-row {{ display:grid; grid-template-columns:48px 1fr 88px; align-items:center; gap:8px; margin-top:10px; color:var(--muted); font-size:11px; }}
.bar-track {{ height:7px; overflow:hidden; background:#e8eef1; border-radius:2px; }}
.bar-track i {{ display:block; height:100%; background:var(--accent); border-radius:2px; }}
.bar-row b {{ color:var(--ink); text-align:right; font-weight:600; font-variant-numeric:tabular-nums; }}
.threshold {{ display:inline-block; margin-top:12px; padding:4px 7px; border:1px solid var(--line); border-radius:3px; color:var(--muted); font-size:11px; }}
.status {{ display:flex; align-items:center; gap:8px; margin-top:16px; font-weight:600; }}
.dot {{ width:9px; height:9px; border-radius:50%; background:var(--accent); }}
footer {{ margin-top:14px; color:var(--muted); font-size:11px; }}
@media (max-width:1000px) {{ .grid {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} }}
@media (max-width:640px) {{ header {{ align-items:start; flex-direction:column; padding:18px; }} .meta {{ text-align:left; }} main {{ padding:14px; }} .grid {{ grid-template-columns:1fr; }} }}
</style></head>
<body><header><div><h1>{html.escape(config['title'])}</h1><div class="sub">Application telemetry · structured logs</div></div>
<div class="meta">Window: {config['time_range_minutes']} minutes<br>Generated: {generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}<br>Refresh contract: {config['refresh_seconds']} s</div></header>
<main><div class="grid">
<section class="latency"><h2>Latency and TTFT</h2><div class="hint">response_sent · milliseconds</div><div class="primary">{data['latency_p95']:,.0f}<small>P95 ms</small></div><div class="stats"><div class="stat"><div class="label">P50</div><div class="value">{data['latency_p50']:,.0f}</div></div><div class="stat"><div class="label">P99</div><div class="value">{data['latency_p99']:,.0f}</div></div><div class="stat"><div class="label">TTFT P95</div><div class="value">{data['ttft_p95']:,.0f}</div></div></div><div class="threshold">P95 threshold ≤ {latency:,.0f} ms</div></section>
<section class="traffic"><h2>Request traffic</h2><div class="hint">request_received · 12 latest active minutes</div><div class="primary">{data['requests']}<small>requests · {data['requests']/config['time_range_minutes']:.2f}/min</small></div>{traffic_bars}</section>
<section class="errors"><h2>Errors and retrieval</h2><div class="hint">request_failed / request_received · retrieval attempts</div><div class="primary">{data['error_rate_pct']:.1f}<small>% error rate</small></div><div class="stats"><div class="stat"><div class="label">Failures</div><div class="value">{data['failures']}</div></div><div class="stat"><div class="label">Retrieval success</div><div class="value">{data['retrieval_success_pct']:.1f}%</div></div><div class="stat"><div class="label">Requests</div><div class="value">{data['requests']}</div></div></div></section>
<section class="cost"><h2>Cost over window</h2><div class="hint">response_sent · USD</div><div class="primary">${data['cost_total']:.4f}<small>total</small></div><div class="stats"><div class="stat"><div class="label">Average/request</div><div class="value">${data['cost_avg']:.4f}</div></div><div class="stat"><div class="label">Successful responses</div><div class="value">{data['responses']}</div></div><div class="stat"><div class="label">Source</div><div class="value">JSONL</div></div></div>{cost_bars}</section>
<section class="tokens"><h2>Token usage</h2><div class="hint">response_sent · total tokens by field</div><div class="primary">{data['tokens_in']+data['tokens_out']:,}<small>tokens</small></div><div class="stats"><div class="stat"><div class="label">Input</div><div class="value">{data['tokens_in']:,}</div></div><div class="stat"><div class="label">Output</div><div class="value">{data['tokens_out']:,}</div></div><div class="stat"><div class="label">Requests</div><div class="value">{data['responses']}</div></div></div></section>
<section class="quality"><h2>Quality proxy</h2><div class="hint">response_sent · mean score</div><div class="primary">{data['quality_mean']:.3f}<small>score</small></div><div class="stats"><div class="stat"><div class="label">Responses</div><div class="value">{data['responses']}</div></div><div class="stat"><div class="label">Threshold</div><div class="value">≥ {quality_threshold:.2f}</div></div><div class="stat"><div class="label">Records</div><div class="value">{data['records']}</div></div></div><div class="status"><span class="dot"></span>{'At or above threshold' if data['quality_mean'] >= quality_threshold else 'Below threshold'}</div></section>
</div><footer>Snapshot computed from data/logs.jsonl using the six-panel contract in config/dashboard.yaml. Values are not a live auto-refreshing dashboard.</footer></main></body></html>"""
    return grid


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a six-panel HTML snapshot from structured logs")
    parser.add_argument("--logs", type=Path, default=REPO_ROOT / "data" / "logs.jsonl")
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "config" / "dashboard.yaml")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "submission" / "evidence" / "11-dashboard-overview.html")
    args = parser.parse_args()
    config, data, generated_at = collect_snapshot(args.logs, args.config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_dashboard(config, data, generated_at), encoding="utf-8")
    print(f"Rendered 6 dashboard panels from {args.logs} to {args.output}")
    print(f"Window: {config['time_range_minutes']}m; records: {data['records']}; requests: {data['requests']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())