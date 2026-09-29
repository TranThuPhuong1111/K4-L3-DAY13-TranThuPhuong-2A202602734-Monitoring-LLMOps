from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_slo_documents_error_budget_calculation() -> None:
    config = yaml.safe_load(
        (REPO_ROOT / "config" / "slo.yaml").read_text(encoding="utf-8")
    )
    slo = config["primary_slo"]
    calculation = slo["error_budget_calculation"]

    assert slo["target_percent"] == 99.5
    assert slo["error_budget_percent"] == 0.5
    assert calculation["formula"] == "100% - target_percent"
    assert calculation["example_window_requests"] == 10000
    assert calculation["allowed_bad_requests"] == 50


def test_alert_rules_have_three_complete_symptom_runbooks() -> None:
    config = yaml.safe_load(
        (REPO_ROOT / "config" / "alert_rules.yaml").read_text(encoding="utf-8")
    )
    alerts = config["alerts"]
    runbooks = (REPO_ROOT / "docs" / "alerts.md").read_text(encoding="utf-8")
    runbook_anchors = {
        line[3:].lower().replace(" ", "-")
        for line in runbooks.splitlines()
        if line.startswith("## ")
    }

    assert len(alerts) == 3
    for alert in alerts:
        assert alert["type"] == "symptom-based"
        assert alert["severity"] in {"warning", "critical"}
        assert alert["condition"]
        assert alert["duration"].endswith("m")
        assert alert["owner"]
        assert alert["channel"].startswith("#")
        assert alert["runbook"].startswith("docs/alerts.md#")
        assert alert["runbook"].split("#", 1)[1] in runbook_anchors