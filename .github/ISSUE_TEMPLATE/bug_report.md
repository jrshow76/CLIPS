---
name: 버그 리포트 (Bug Report)
about: TradePilot 동작 이상 / 결함을 보고합니다.
title: "[BUG] "
labels: ["bug", "tradepilot"]
assignees: []
---

<!--
참고: 본 템플릿은 TradePilot/qa/55_bug_template.md 의 양식을 단순화한 GitHub 이슈용입니다.
정식 회귀 추적이 필요한 경우 QA 가 동일 정보를 Jira 에 동기화합니다.
-->

## 요약 (1줄)

## 환경

- 영역: backend / frontend / creon-gateway / db / 기타
- 환경: dev / staging / prod
- 버전 (커밋 SHA 또는 release 태그):
- 사용자 모드: SIM / LIVE  (LIVE 인 경우 우선순위 P0 가능)
- 브라우저 (frontend 인 경우): 

## 재현 절차

1. 
2. 
3. 

## 기대 동작

## 실제 동작

## 로그 / 스크린샷

```
<관련 로그 붙여넣기 (PII / 시크릿 마스킹 필수)>
```

## 매매 영향도 (자동주식매매 시스템 필수 항목)

- [ ] 주문 누락 가능성 있음
- [ ] 주문 중복 / 다중 체결 가능성 있음
- [ ] 손익 계산 오류 가능성 있음
- [ ] 킬스위치 / 한도 미동작 가능성 있음
- [ ] 위 항목 해당 없음

## 우선순위 제안

- [ ] P0 (실거래 중단/금전 손실 위험)
- [ ] P1 (핵심 기능 장애)
- [ ] P2 (일반 기능 장애)
- [ ] P3 (개선/사소)
