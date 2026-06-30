"""
Post-flight report generator.

Reads results/logs/alerts.jsonl, summarises what happened during the flight,
and calls the Claude API to produce a plain-language markdown report saved to
results/post_flight_report.md.

Usage:
    python -m guardian.report_generator
    guardian-report          # after pip install -e .

Requires the ANTHROPIC_API_KEY environment variable to be set.
"""

import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import anthropic

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOG_PATH = PROJECT_ROOT / "results" / "logs" / "alerts.jsonl"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "results" / "post_flight_report.md"


def load_alerts(log_path: Path) -> list[dict]:
    if not log_path.exists():
        return []
    alerts = []
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                alerts.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return alerts


def build_summary(alerts: list[dict]) -> dict:
    if not alerts:
        return {
            "total": 0,
            "by_severity": {},
            "by_reason_code": {},
            "by_status": {},
            "first_alert_ts": None,
            "last_alert_ts": None,
        }

    severities = Counter(a.get("severity", "UNKNOWN") for a in alerts)
    reason_codes = Counter(a.get("reason_code", "UNKNOWN") for a in alerts)
    statuses = Counter(a.get("alert_status", "unknown") for a in alerts)

    timestamps = [a.get("timestamp_ms") for a in alerts if a.get("timestamp_ms")]
    first_ts = min(timestamps) if timestamps else None
    last_ts = max(timestamps) if timestamps else None

    return {
        "total": len(alerts),
        "by_severity": dict(severities.most_common()),
        "by_reason_code": dict(reason_codes.most_common()),
        "by_status": dict(statuses.most_common()),
        "first_alert_ts": first_ts,
        "last_alert_ts": last_ts,
    }


def build_prompt(summary: dict, alerts: list[dict]) -> str:
    if summary["total"] == 0:
        data_section = "No alerts were recorded during this flight session."
    else:
        first = summary["first_alert_ts"]
        last = summary["last_alert_ts"]
        duration_s = round((last - first) / 1000) if first and last else "unknown"

        severity_lines = "\n".join(
            f"  - {sev}: {count}" for sev, count in summary["by_severity"].items()
        )
        reason_lines = "\n".join(
            f"  - {code}: {count}" for code, count in summary["by_reason_code"].items()
        )
        status_lines = "\n".join(
            f"  - {st}: {count}" for st, count in summary["by_status"].items()
        )

        # Include up to 5 sample alerts for context
        sample_alerts = alerts[:5]
        sample_lines = "\n".join(
            f"  [{a.get('severity','?')}] {a.get('reason_code','?')}: {a.get('reason_text','')}"
            f" → {a.get('recommended_action','')}"
            for a in sample_alerts
        )

        data_section = f"""Flight session duration: approximately {duration_s} seconds

Total alerts fired: {summary['total']}

Alerts by severity:
{severity_lines}

Alerts by anomaly type:
{reason_lines}

Alert resolution status:
{status_lines}

Sample alerts (first 5):
{sample_lines}"""

    return f"""You are an aerospace safety analyst reviewing a post-flight anomaly report for an RC aircraft equipped with the AI Guardian telemetry monitoring system.

Here is the flight data summary:

{data_section}

Write a concise post-flight report in markdown format. The report should include:
1. A brief executive summary (2-3 sentences)
2. Key findings — what anomalies occurred and how severe they were
3. Operator response summary — how alerts were handled (acknowledged, escalated, resolved, or left active)
4. Recommended maintenance or follow-up actions based on the anomaly types seen
5. An overall flight safety assessment (Safe / Caution / Unsafe)

Keep the tone professional, factual, and actionable. Write for a human operator who will decide whether the aircraft is safe to fly again.
"""


def generate_report(log_path: Path = DEFAULT_LOG_PATH,
                    report_path: Path = DEFAULT_REPORT_PATH,
                    api_key: str | None = None) -> str:
    """Generate a post-flight report and save it to report_path.

    Returns the report markdown string.
    Raises RuntimeError if the API key is missing.
    """
    key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY environment variable is not set. "
            "Set it before running the report generator."
        )

    alerts = load_alerts(log_path)
    summary = build_summary(alerts)
    prompt = build_prompt(summary, alerts)

    client = anthropic.Anthropic(api_key=key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    report_body = message.content[0].text

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    header = (
        f"# Post-Flight AI Report\n\n"
        f"*Generated: {generated_at} — Source: `{log_path.name}` "
        f"({summary['total']} alert{'s' if summary['total'] != 1 else ''})*\n\n---\n\n"
    )
    full_report = header + report_body

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(full_report, encoding="utf-8")

    return full_report


def main():
    try:
        report = generate_report()
        print(report)
        print(f"\nReport saved to: {DEFAULT_REPORT_PATH}")
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
