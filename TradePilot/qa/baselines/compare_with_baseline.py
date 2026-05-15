#!/usr/bin/env python3
"""
TradePilot 야간 회귀 결과를 베이스라인과 비교하는 도구.

입력:
  - pytest JUnit XML 결과 (다중 파일 허용)
  - k6 --summary-export JSON 결과 (선택)
  - baseline JSON (qa/baselines/baseline_v1.json)

출력:
  - regression_report.md (회귀 항목 표 + 종합 verdict)
  - stdout: 요약 + verdict

회귀 기준 (qa/baselines/baseline_v1.json 기준):
  - 통과 카운트가 baseline.tests.* 미만 → REGRESSION
  - p95 latency 가 baseline + 5% 초과 → REGRESSION
  - RPS 가 baseline - 5% 미만 → REGRESSION
  - 실패율이 baseline.load.fail_rate_max 초과 → REGRESSION

exit code: 0 = PASS, 1 = REGRESSION_DETECTED, 2 = INPUT_ERROR
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


KST = timezone(timedelta(hours=9))


# ---------------------------------------------------------------------------
# 데이터 모델
# ---------------------------------------------------------------------------

@dataclass
class JUnitSummary:
    """JUnit XML 1개 파일의 합산 결과."""
    file: str
    tests: int = 0
    failures: int = 0
    errors: int = 0
    skipped: int = 0

    @property
    def passed(self) -> int:
        return max(0, self.tests - self.failures - self.errors - self.skipped)


@dataclass
class K6Summary:
    """k6 --summary-export JSON 1개 시나리오의 핵심 지표."""
    scenario: str
    p95_ms: float | None = None
    p99_ms: float | None = None
    rps: float | None = None
    fail_rate: float | None = None
    total_reqs: float | None = None


@dataclass
class RegressionItem:
    category: str
    metric: str
    baseline: float
    observed: float
    delta_pct: float | None
    threshold_pct: float
    severity: str  # "warn" | "alert" | "critical"
    note: str = ""


@dataclass
class Verdict:
    status: str  # "PASS" | "REGRESSION_DETECTED"
    items: list[RegressionItem] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 파서
# ---------------------------------------------------------------------------

def parse_junit(path: Path) -> JUnitSummary:
    """JUnit XML 1개 파일을 파싱한다.

    pytest --junitxml 출력은 최상위 <testsuites> 또는 <testsuite>.
    """
    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        print(f"WARN: JUnit XML 파싱 실패 ({path}): {e}", file=sys.stderr)
        return JUnitSummary(file=str(path))

    root = tree.getroot()
    suites: list[ET.Element]
    if root.tag == "testsuites":
        suites = list(root.findall("testsuite"))
    else:
        suites = [root]

    summary = JUnitSummary(file=str(path))
    for s in suites:
        summary.tests += int(s.get("tests", "0") or 0)
        summary.failures += int(s.get("failures", "0") or 0)
        summary.errors += int(s.get("errors", "0") or 0)
        summary.skipped += int(s.get("skipped", "0") or 0)
    return summary


def parse_k6_summary(path: Path, scenario: str) -> K6Summary | None:
    """k6 --summary-export JSON 1개 파일을 파싱한다."""
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        print(f"WARN: k6 JSON 파싱 실패 ({path}): {e}", file=sys.stderr)
        return None

    def _get(metric: str, sub: str) -> float | None:
        try:
            return float(data["metrics"][metric]["values"][sub])
        except (KeyError, TypeError, ValueError):
            return None

    return K6Summary(
        scenario=scenario,
        p95_ms=_get("http_req_duration", "p(95)"),
        p99_ms=_get("http_req_duration", "p(99)"),
        rps=_get("http_reqs", "rate"),
        fail_rate=_get("http_req_failed", "rate"),
        total_reqs=_get("http_reqs", "count"),
    )


def load_baseline(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


# ---------------------------------------------------------------------------
# 회귀 판정
# ---------------------------------------------------------------------------

def _severity(delta_pct: float, sev_cfg: dict[str, float]) -> str:
    """변동률(%)을 받아 severity 분류."""
    a = abs(delta_pct)
    if a >= sev_cfg.get("critical_pct", 20.0):
        return "critical"
    if a >= sev_cfg.get("alert_pct", 10.0):
        return "alert"
    return "warn"


def compare_tests(
    junit_groups: dict[str, list[JUnitSummary]],
    baseline: dict[str, Any],
) -> list[RegressionItem]:
    """그룹별 (unit/qa/security/integration) 통과 카운트 비교."""
    out: list[RegressionItem] = []
    tests_cfg = baseline.get("tests", {})
    sev_cfg = baseline.get("regression_severity", {})

    for group, files in junit_groups.items():
        passed = sum(f.passed for f in files)
        total = sum(f.tests for f in files)
        key = f"{group}_pass_count"
        base = tests_cfg.get(key)
        if base is None:
            continue
        # 통과 카운트는 단순 비교: baseline 미만이면 회귀
        if passed < base:
            delta = (passed - base) / base * 100 if base else 0.0
            out.append(RegressionItem(
                category="tests",
                metric=f"{group}.pass_count",
                baseline=float(base),
                observed=float(passed),
                delta_pct=delta,
                threshold_pct=0.0,
                severity=_severity(delta, sev_cfg),
                note=f"통과 {passed}/{total} (실패 또는 누락)",
            ))

    # 전체 합산
    total_passed = sum(f.passed for files in junit_groups.values() for f in files)
    total_total = sum(f.tests for files in junit_groups.values() for f in files)
    base_total = tests_cfg.get("total_pass_count")
    if base_total is not None and total_passed < base_total:
        delta = (total_passed - base_total) / base_total * 100 if base_total else 0.0
        out.append(RegressionItem(
            category="tests",
            metric="total.pass_count",
            baseline=float(base_total),
            observed=float(total_passed),
            delta_pct=delta,
            threshold_pct=0.0,
            severity=_severity(delta, sev_cfg),
            note=f"전체 통과 {total_passed}/{total_total}",
        ))

    # 최소 통과율
    min_rate = tests_cfg.get("min_pass_rate", 0.97)
    if total_total > 0:
        rate = total_passed / total_total
        if rate < min_rate:
            delta = (rate - min_rate) / min_rate * 100 if min_rate else 0.0
            out.append(RegressionItem(
                category="tests",
                metric="pass_rate",
                baseline=min_rate,
                observed=rate,
                delta_pct=delta,
                threshold_pct=0.0,
                severity="critical",
                note=f"통과율 {rate*100:.2f}% < {min_rate*100:.2f}%",
            ))

    return out


def compare_latency(
    k6_results: list[K6Summary],
    baseline: dict[str, Any],
) -> list[RegressionItem]:
    """k6 p95 latency 가 baseline + threshold% 초과인지 검증."""
    out: list[RegressionItem] = []
    lat_cfg = baseline.get("latency", {})
    sev_cfg = baseline.get("regression_severity", {})
    threshold = float(baseline.get("regression_threshold_pct", 5.0))

    # 시나리오 → baseline 키 매핑
    key_map = {
        "orders": "orders_p95_ms",
        "signals": "signals_p95_ms",
        "mixed": "mixed_p95_ms",
        "backtest": "backtest_p95_ms",
        "ws": "ws_handshake_p95_ms",
    }

    for r in k6_results:
        base_key = key_map.get(r.scenario)
        if base_key is None or r.p95_ms is None:
            continue
        base = lat_cfg.get(base_key)
        if base is None or base <= 0:
            continue
        delta = (r.p95_ms - base) / base * 100
        if delta > threshold:
            out.append(RegressionItem(
                category="latency",
                metric=f"{r.scenario}.p95_ms",
                baseline=float(base),
                observed=float(r.p95_ms),
                delta_pct=delta,
                threshold_pct=threshold,
                severity=_severity(delta, sev_cfg),
                note=f"p95 {r.p95_ms:.0f}ms 가 baseline +{threshold:.0f}% 초과",
            ))
    return out


def compare_load(
    k6_results: list[K6Summary],
    baseline: dict[str, Any],
) -> list[RegressionItem]:
    """RPS / 실패율 비교."""
    out: list[RegressionItem] = []
    load_cfg = baseline.get("load", {})
    sev_cfg = baseline.get("regression_severity", {})
    threshold = float(baseline.get("regression_threshold_pct", 5.0))
    fail_max = float(load_cfg.get("fail_rate_max", 0.01))

    rps_map = {
        "orders": "orders_rps_min",
        "signals": "signals_rps_min",
        "mixed": "mixed_rps_min",
    }

    for r in k6_results:
        # RPS 회귀 (baseline - threshold% 미만)
        rps_key = rps_map.get(r.scenario)
        if rps_key and r.rps is not None:
            base = load_cfg.get(rps_key)
            if base and base > 0:
                delta = (r.rps - base) / base * 100  # 음수면 감소
                if delta < -threshold:
                    out.append(RegressionItem(
                        category="load",
                        metric=f"{r.scenario}.rps",
                        baseline=float(base),
                        observed=float(r.rps),
                        delta_pct=delta,
                        threshold_pct=threshold,
                        severity=_severity(delta, sev_cfg),
                        note=f"RPS {r.rps:.1f} 가 baseline -{threshold:.0f}% 미만",
                    ))
        # 실패율
        if r.fail_rate is not None and r.fail_rate > fail_max:
            out.append(RegressionItem(
                category="load",
                metric=f"{r.scenario}.fail_rate",
                baseline=fail_max,
                observed=float(r.fail_rate),
                delta_pct=None,
                threshold_pct=0.0,
                severity="critical",
                note=f"실패율 {r.fail_rate*100:.2f}% > 최대 {fail_max*100:.2f}%",
            ))
    return out


# ---------------------------------------------------------------------------
# 리포트 렌더링
# ---------------------------------------------------------------------------

def _fmt_pct(d: float | None) -> str:
    if d is None:
        return "N/A"
    sign = "+" if d >= 0 else ""
    return f"{sign}{d:.1f}%"


def render_report(
    verdict: Verdict,
    junit_groups: dict[str, list[JUnitSummary]],
    k6_results: list[K6Summary],
    baseline: dict[str, Any],
    meta: dict[str, str],
) -> str:
    lines: list[str] = []
    lines.append("# TradePilot 야간 회귀 리포트")
    lines.append("")
    lines.append(f"- 생성: {datetime.now(KST).isoformat(timespec='seconds')}")
    lines.append(f"- 베이스라인 버전: {baseline.get('version', 'N/A')}")
    lines.append(f"- 베이스라인 캡쳐 시각: {baseline.get('captured_at', 'N/A')}")
    lines.append(f"- 워크플로우 run_id: {meta.get('run_id', 'N/A')}")
    lines.append(f"- 워크플로우 commit: {meta.get('commit', 'N/A')}")
    lines.append("")
    lines.append(f"## 종합 판정: **{verdict.status}**")
    lines.append("")

    # 1. 테스트 결과
    lines.append("## 1. 테스트 결과")
    lines.append("")
    lines.append("| 그룹 | 통과 | 실패 | 에러 | 스킵 | 총계 | baseline | 판정 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|:---:|")
    tests_cfg = baseline.get("tests", {})
    for group, files in junit_groups.items():
        passed = sum(f.passed for f in files)
        failures = sum(f.failures for f in files)
        errors = sum(f.errors for f in files)
        skipped = sum(f.skipped for f in files)
        total = sum(f.tests for f in files)
        base = tests_cfg.get(f"{group}_pass_count", "-")
        ok = "PASS" if (isinstance(base, int) and passed >= base) or base == "-" else "REGRESSION"
        lines.append(
            f"| {group} | {passed} | {failures} | {errors} | {skipped} | "
            f"{total} | {base} | {ok} |"
        )
    lines.append("")

    # 2. 부하 결과
    if k6_results:
        lines.append("## 2. 부하 결과 (k6 smoke)")
        lines.append("")
        lines.append("| 시나리오 | p95(ms) | p99(ms) | RPS | 실패율 | 총요청 |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for r in k6_results:
            lines.append(
                f"| {r.scenario} | "
                f"{r.p95_ms:.1f if r.p95_ms is not None else 'N/A'} | "
                f"{r.p99_ms:.1f if r.p99_ms is not None else 'N/A'} | "
                f"{r.rps:.1f if r.rps is not None else 'N/A'} | "
                f"{(r.fail_rate*100):.2f if r.fail_rate is not None else 'N/A'}% | "
                f"{r.total_reqs if r.total_reqs is not None else 'N/A'} |"
            )
        lines.append("")

    # 3. 회귀 항목
    lines.append("## 3. 회귀 감지 항목")
    lines.append("")
    if not verdict.items:
        lines.append("회귀 감지 없음. 모든 항목이 baseline 이내.")
    else:
        lines.append("| 카테고리 | 메트릭 | baseline | 현재 | 변동 | 임계 | 심각도 | 비고 |")
        lines.append("|---|---|---:|---:|---:|---:|:---:|---|")
        for it in verdict.items:
            lines.append(
                f"| {it.category} | {it.metric} | {it.baseline:.2f} | "
                f"{it.observed:.2f} | {_fmt_pct(it.delta_pct)} | "
                f"{it.threshold_pct:.1f}% | **{it.severity}** | {it.note} |"
            )
    lines.append("")

    # 4. 대응 가이드
    lines.append("## 4. 다음 단계")
    lines.append("")
    if verdict.status == "PASS":
        lines.append("- 회귀 없음. 별도 조치 불필요. 결과는 `qa/baselines/history/` 에 보관.")
    else:
        lines.append("- DevLead 가 회귀 항목별 원인 분류 (코드 변경 / 인프라 / 데이터).")
        lines.append("- 5%~10% 회귀: 24시간 내 조사, P1 priority 이슈.")
        lines.append("- 10%~20% 회귀: 즉시 조사, P0 priority 이슈.")
        lines.append("- 20% 초과 회귀: 배포 차단, PM 즉시 알림.")
        lines.append("- 자세한 절차: `TradePilot/qa/85_nightly_regression_guide.md`")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--baseline", required=True, type=Path)
    p.add_argument(
        "--junit",
        action="append",
        default=[],
        help="group=path 형식. 예: --junit unit=reports/junit-unit.xml",
    )
    p.add_argument(
        "--k6",
        action="append",
        default=[],
        help="scenario=path 형식. 예: --k6 signals=reports/signals.json",
    )
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--run-id", default="")
    p.add_argument("--commit", default="")
    p.add_argument(
        "--history-out",
        type=Path,
        default=None,
        help="당일 결과를 history 디렉토리에 일자별 JSON 으로 저장",
    )
    args = p.parse_args()

    if not args.baseline.exists():
        print(f"ERROR: baseline 파일 없음: {args.baseline}", file=sys.stderr)
        return 2
    baseline = load_baseline(args.baseline)

    # JUnit 파싱
    junit_groups: dict[str, list[JUnitSummary]] = {}
    for entry in args.junit:
        if "=" not in entry:
            print(f"WARN: --junit 형식 오류: {entry}", file=sys.stderr)
            continue
        group, path_s = entry.split("=", 1)
        path = Path(path_s)
        if not path.exists():
            print(f"WARN: JUnit 파일 없음: {path}", file=sys.stderr)
            continue
        junit_groups.setdefault(group, []).append(parse_junit(path))

    # k6 파싱
    k6_results: list[K6Summary] = []
    for entry in args.k6:
        if "=" not in entry:
            print(f"WARN: --k6 형식 오류: {entry}", file=sys.stderr)
            continue
        scenario, path_s = entry.split("=", 1)
        path = Path(path_s)
        if not path.exists():
            print(f"WARN: k6 파일 없음: {path}", file=sys.stderr)
            continue
        s = parse_k6_summary(path, scenario)
        if s is not None:
            k6_results.append(s)

    # 회귀 판정
    items: list[RegressionItem] = []
    items.extend(compare_tests(junit_groups, baseline))
    items.extend(compare_latency(k6_results, baseline))
    items.extend(compare_load(k6_results, baseline))

    verdict = Verdict(
        status="REGRESSION_DETECTED" if items else "PASS",
        items=items,
    )

    # 리포트 출력
    report = render_report(
        verdict, junit_groups, k6_results, baseline,
        meta={"run_id": args.run_id, "commit": args.commit},
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(f"리포트 저장: {args.out}")
    print(f"종합 판정: {verdict.status} (회귀 {len(items)}건)")

    # 히스토리 저장 (옵션)
    if args.history_out is not None:
        args.history_out.parent.mkdir(parents=True, exist_ok=True)
        hist = {
            "captured_at": datetime.now(KST).isoformat(timespec="seconds"),
            "run_id": args.run_id,
            "commit": args.commit,
            "verdict": verdict.status,
            "regression_count": len(items),
            "tests": {
                group: {
                    "passed": sum(f.passed for f in files),
                    "failures": sum(f.failures for f in files),
                    "errors": sum(f.errors for f in files),
                    "skipped": sum(f.skipped for f in files),
                    "total": sum(f.tests for f in files),
                }
                for group, files in junit_groups.items()
            },
            "k6": [
                {
                    "scenario": r.scenario,
                    "p95_ms": r.p95_ms,
                    "p99_ms": r.p99_ms,
                    "rps": r.rps,
                    "fail_rate": r.fail_rate,
                    "total_reqs": r.total_reqs,
                }
                for r in k6_results
            ],
            "regressions": [
                {
                    "category": it.category,
                    "metric": it.metric,
                    "baseline": it.baseline,
                    "observed": it.observed,
                    "delta_pct": it.delta_pct,
                    "severity": it.severity,
                    "note": it.note,
                }
                for it in items
            ],
        }
        args.history_out.write_text(json.dumps(hist, ensure_ascii=False, indent=2))
        print(f"히스토리 저장: {args.history_out}")

    return 1 if items else 0


if __name__ == "__main__":
    sys.exit(main())
