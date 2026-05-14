#!/usr/bin/env python3
"""
TradePilot 부하 테스트 결과 분석기.

k6 --summary-export 로 생성된 JSON 파일을 수집해 다음을 산출한다.
  - 시나리오별 핵심 지표 표 (Markdown)
  - SLA 위반 여부
  - 베이스라인 대비 회귀(±5%) 추적 (옵션)

사용:
  python3 qa/load/analyze_results.py \
    --reports-dir qa/load/reports \
    --timestamp 20260514_100000 \
    --out qa/load/reports/20260514_100000_analysis.md

종속성: 표준 라이브러리만 사용.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Any


# 시나리오별 SLA (qa/load/82_sla_definition.md 와 동기화)
SLA = {
    "orders":   {"p95_ms": 500,  "p99_ms": 1500, "fail_rate": 0.01},
    "signals":  {"p95_ms": 300,  "p99_ms": 800,  "fail_rate": 0.01},
    "ws":       {"p95_ms": 1500, "p99_ms": 3000, "fail_rate": 0.02},
    "mixed":    {"p95_ms": 800,  "p99_ms": 2000, "fail_rate": 0.01},
    "backtest": {"p95_ms": 2000, "p99_ms": 5000, "fail_rate": 0.05},
}


def get_metric(data: dict[str, Any], metric: str, sub: str) -> float | None:
    """k6 summary JSON 에서 metric.values.sub 추출."""
    try:
        return float(data["metrics"][metric]["values"][sub])
    except (KeyError, TypeError, ValueError):
        return None


def fmt(v: float | None, decimals: int = 1, suffix: str = "") -> str:
    if v is None:
        return "N/A"
    return f"{v:.{decimals}f}{suffix}"


def evaluate_sla(scenario: str, summary: dict[str, Any]) -> tuple[bool, list[str]]:
    """SLA 위반 여부를 평가. (passed, violations) 반환."""
    sla = SLA.get(scenario)
    if not sla:
        return True, []
    violations = []
    p95 = get_metric(summary, "http_req_duration", "p(95)")
    p99 = get_metric(summary, "http_req_duration", "p(99)")
    fail = get_metric(summary, "http_req_failed", "rate")
    if p95 is not None and p95 > sla["p95_ms"]:
        violations.append(f"P95 {p95:.0f}ms > {sla['p95_ms']}ms")
    if p99 is not None and p99 > sla["p99_ms"]:
        violations.append(f"P99 {p99:.0f}ms > {sla['p99_ms']}ms")
    if fail is not None and fail > sla["fail_rate"]:
        violations.append(f"실패율 {fail*100:.2f}% > {sla['fail_rate']*100:.2f}%")
    return len(violations) == 0, violations


def render_scenario_table(scenario: str, summary: dict[str, Any]) -> str:
    p50 = get_metric(summary, "http_req_duration", "p(50)")
    p90 = get_metric(summary, "http_req_duration", "p(90)")
    p95 = get_metric(summary, "http_req_duration", "p(95)")
    p99 = get_metric(summary, "http_req_duration", "p(99)")
    avg = get_metric(summary, "http_req_duration", "avg")
    fail = get_metric(summary, "http_req_failed", "rate")
    total = get_metric(summary, "http_reqs", "count")
    rps = get_metric(summary, "http_reqs", "rate")

    passed, violations = evaluate_sla(scenario, summary)
    status = "PASS" if passed else "FAIL"

    out = []
    out.append(f"### {scenario}")
    out.append("")
    out.append(f"- SLA 상태: **{status}**")
    if violations:
        out.append("- 위반 항목:")
        for v in violations:
            out.append(f"  - {v}")
    out.append("")
    out.append("| 지표 | 값 |")
    out.append("|---|---:|")
    out.append(f"| 총 요청 수 | {fmt(total, 0)} |")
    out.append(f"| 평균 RPS | {fmt(rps, 1)} |")
    out.append(f"| 실패율 | {fmt(fail*100 if fail is not None else None, 2, '%')} |")
    out.append(f"| 평균 응답(ms) | {fmt(avg, 1)} |")
    out.append(f"| P50 (ms) | {fmt(p50, 1)} |")
    out.append(f"| P90 (ms) | {fmt(p90, 1)} |")
    out.append(f"| P95 (ms) | {fmt(p95, 1)} |")
    out.append(f"| P99 (ms) | {fmt(p99, 1)} |")
    out.append("")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", required=True)
    parser.add_argument("--timestamp", required=True,
                        help="run_all_loads.sh 의 TIMESTAMP (예: 20260514_100000)")
    parser.add_argument("--out", required=True)
    parser.add_argument("--baseline", default=None,
                        help="이전 베이스라인 JSON 파일 (회귀 비교용)")
    args = parser.parse_args()

    reports_dir = Path(args.reports_dir)
    ts = args.timestamp

    summaries: dict[str, dict] = {}
    for name in SLA.keys():
        f = reports_dir / f"{ts}_{name}.json"
        if f.exists():
            try:
                summaries[name] = json.loads(f.read_text())
            except json.JSONDecodeError as e:
                print(f"WARN: {f} 파싱 실패: {e}", file=sys.stderr)

    if not summaries:
        print("ERROR: 분석할 결과 JSON 이 없다.", file=sys.stderr)
        return 1

    lines = []
    lines.append(f"# 부하 테스트 결과 분석 ({ts})")
    lines.append("")
    lines.append(f"- 생성: {datetime.now().isoformat()}")
    lines.append(f"- 시나리오 수: {len(summaries)}")
    lines.append("")

    # 요약 표
    lines.append("## 요약")
    lines.append("")
    lines.append("| 시나리오 | 총 요청 | 평균 RPS | 실패율 | P95(ms) | P99(ms) | SLA |")
    lines.append("|---|---:|---:|---:|---:|---:|:---:|")
    fail_any = False
    for name, summary in summaries.items():
        total = get_metric(summary, "http_reqs", "count")
        rps = get_metric(summary, "http_reqs", "rate")
        fail = get_metric(summary, "http_req_failed", "rate")
        p95 = get_metric(summary, "http_req_duration", "p(95)")
        p99 = get_metric(summary, "http_req_duration", "p(99)")
        passed, _ = evaluate_sla(name, summary)
        if not passed:
            fail_any = True
        lines.append(
            f"| {name} | {fmt(total, 0)} | {fmt(rps, 1)} | "
            f"{fmt(fail*100 if fail is not None else None, 2, '%')} | "
            f"{fmt(p95, 0)} | {fmt(p99, 0)} | "
            f"{'PASS' if passed else 'FAIL'} |"
        )
    lines.append("")

    # 상세
    lines.append("## 시나리오별 상세")
    lines.append("")
    for name, summary in summaries.items():
        lines.append(render_scenario_table(name, summary))

    # 베이스라인 회귀
    if args.baseline and Path(args.baseline).exists():
        lines.append("## 베이스라인 회귀 비교")
        lines.append("")
        try:
            base = json.loads(Path(args.baseline).read_text())
        except Exception as e:
            lines.append(f"- 베이스라인 파싱 실패: {e}")
        else:
            lines.append("| 시나리오 | 지표 | 베이스라인 | 현재 | 변동(%) | 회귀 5%? |")
            lines.append("|---|---|---:|---:|---:|:---:|")
            for name, summary in summaries.items():
                if name not in base:
                    continue
                for metric in ("p(95)", "p(99)"):
                    b = get_metric(base[name], "http_req_duration", metric)
                    c = get_metric(summary, "http_req_duration", metric)
                    if b is None or c is None or b == 0:
                        continue
                    delta = (c - b) / b * 100
                    regress = delta > 5.0
                    lines.append(
                        f"| {name} | {metric} | {b:.1f} | {c:.1f} | "
                        f"{delta:+.1f}% | {'YES' if regress else 'no'} |"
                    )
        lines.append("")

    Path(args.out).write_text("\n".join(lines))
    print(f"분석 결과 저장: {args.out}")
    return 1 if fail_any else 0


if __name__ == "__main__":
    sys.exit(main())
