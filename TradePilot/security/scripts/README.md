# TradePilot 보안 자동 점검 스크립트

본 디렉토리는 보안 리뷰를 정기적으로 자동화하기 위한 스크립트 모음이다.

## 도구 목록

| 스크립트 | 도구 | 대상 | 설치 |
|---|---|---|---|
| `bandit_scan.sh` | bandit | Python 정적 분석 | `pip install bandit==1.7.*` |
| `safety_check.sh` | pip-audit | Python 의존성 CVE | `pip install pip-audit==2.7.*` |
| `npm_audit.sh` | npm audit | JS/TS 의존성 | Node 20 + npm |
| `gitleaks_scan.sh` | gitleaks | 시크릿 누출(히스토리+워킹트리) | https://github.com/gitleaks/gitleaks/releases |
| `semgrep_rules.yml` | semgrep | 매매 시스템 특화 룰 | `pip install semgrep` |

## 빠른 실행 (전체)

```bash
cd /home/user/CLIPS

# 1) 정적 분석
bash TradePilot/security/scripts/bandit_scan.sh

# 2) 의존성 취약점
bash TradePilot/security/scripts/safety_check.sh
bash TradePilot/security/scripts/npm_audit.sh

# 3) 시크릿 누출
bash TradePilot/security/scripts/gitleaks_scan.sh

# 4) 매매 시스템 특화 룰
semgrep --config TradePilot/security/scripts/semgrep_rules.yml \
        TradePilot/backend/ TradePilot/creon-gateway/
```

## 리포트 출력 위치

모든 도구는 `TradePilot/security/reports/` 디렉토리에 JSON + 사람용 텍스트로 결과를 저장한다.
디렉토리는 스크립트가 자동 생성한다.

## CI 통합

`.github/workflows/tradepilot-security.yml`에 이미 다음이 자동화되어 있다:

- pip-audit (backend + creon-gateway)
- npm audit (frontend)
- Trivy 파일시스템 스캔
- gitleaks (전체 git 히스토리)

본 디렉토리의 스크립트는 **로컬/머지 전 검증용**이며, CI는 별도 정기 스캔(매주 월요일 09:00 UTC)이다.

추가로 다음을 CI에 통합 권장:

- bandit (운영 코드만, 테스트 제외)
- semgrep (TradePilot 매매 시스템 특화 룰)

```yaml
# .github/workflows/tradepilot-security.yml 보강 예시
- name: bandit (backend + gateway)
  run: |
    pip install bandit==1.7.*
    bandit -r TradePilot/backend/app TradePilot/creon-gateway/creon_gateway \
           --severity-level high --confidence-level medium \
           --skip B101,B601

- name: semgrep (TradePilot 룰)
  uses: returntocorp/semgrep-action@v1
  with:
    config: TradePilot/security/scripts/semgrep_rules.yml
```

## 종료 코드 정책

| 코드 | 의미 | CI 처리 |
|---:|---|---|
| 0 | 통과 | 성공 |
| 1+ | 취약점 발견 또는 도구 실패 | 실패 (PR 차단) |
| 2 | 도구 미설치 | 워닝 (CI는 설치 후 재시도) |

## 베이스라인 (False Positive 처리)

- `bandit`: `--skip B101,B601` (assert/shell-piped 워닝 제외)
- `pip-audit`: `--strict` 사용. 패치 불가 항목은 별도 ignore 파일 관리.
- `npm audit`: `--audit-level=moderate` (low 노이즈 제외)
- `gitleaks`: `.gitleaks.toml`에 검토된 false positive 등록 (예: `.env.example`의 placeholder)

## 정기 운영

- 일간: 운영자가 `gitleaks_scan.sh --no-git` 실행 (워킹트리)
- 주간: 모든 스크립트 + CI 결과 검토
- 월간: bandit/semgrep 룰 갱신, false positive 베이스라인 재정리
