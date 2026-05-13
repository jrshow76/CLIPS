<!--
TradePilot PR 템플릿
- 매매 정책에 영향이 있는 경우 반드시 PM + DevLead 승인 필수입니다.
- 모든 PR 은 CI 그린 + Code Owner 리뷰 통과 후 머지 가능합니다.
-->

## 변경 요약

<!-- 1~3줄로 "왜" 이 변경이 필요한지 요약. "무엇"은 코드/diff 로 충분. -->

## 영향 영역

- [ ] backend (`TradePilot/backend`)
- [ ] frontend (`TradePilot/frontend`)
- [ ] creon-gateway (`TradePilot/creon-gateway`)
- [ ] database / migration (`TradePilot/database`, `TradePilot/backend/alembic`)
- [ ] QA / E2E (`TradePilot/qa`)
- [ ] docs (`TradePilot/docs`)
- [ ] CI / 인프라 (`.github`, `Dockerfile`, `docker-compose.yml`)

## 관련 문서 / 이슈

- 기획서:
- API 명세:
- 이슈/티켓:

## 테스트

- [ ] 단위 테스트 추가/수정
- [ ] 통합 테스트 추가/수정
- [ ] E2E 시나리오 추가/수정
- [ ] 수동 검증 시나리오 첨부 (스크린샷/로그)

## 매매 정책 / 안전장치 영향 (매우 중요)

> 본 섹션은 자동주식매매 시스템 특성상 **모든 PR 작성자가 명시적으로 체크**해야 합니다.

- [ ] 본 PR 은 매매 로직(주문 라우터, 신호 평가, 리스크 한도, 킬스위치, 모드 가드 등)을 **변경하지 않음**.
- [ ] 또는, 매매 로직 변경이 포함되며 다음을 모두 충족함:
  - [ ] 거래 모드 가드(`X-Trade-Mode`) 동작 회귀 테스트 통과
  - [ ] 1일 손실 한도 / 종목 한도 / 동시 보유 한도 회귀 테스트 통과
  - [ ] Idempotency 키 정책 영향 검토 완료
  - [ ] 킬스위치 동작 검증 완료
  - [ ] PM + DevLead 별도 승인 (`docs/15_trading_policy.md` 참조)

## 배포 / 롤백 영향

- [ ] DB 마이그레이션 포함 (포함 시 롤백 SQL 첨부 또는 무중단 마이그레이션 명시)
- [ ] 환경 변수 / 시크릿 변경 포함 (변경 시 운영팀 사전 공유)
- [ ] 롤백 절차: <!-- 예: 이전 이미지 태그로 재배포 -->

## 체크리스트

- [ ] CI (`tradepilot-backend-ci`, `tradepilot-frontend-ci`, `tradepilot-e2e-ci`) 그린
- [ ] 보안 스캔 신규 HIGH/CRITICAL 없음
- [ ] 코드 표준 준수 (`docs/25_code_standard.md`)
- [ ] 변경 사항이 `docs/24_api_response_spec.md` 와 호환됨
