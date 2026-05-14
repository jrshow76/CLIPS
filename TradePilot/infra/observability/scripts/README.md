# 관측성 스택 운영 스크립트

> 작업 영역: `infra/observability/scripts/`
> 작성자: DevLead

## 파일 일람

| 스크립트 | 용도 |
|---|---|
| `up.sh` | 관측성 스택 기동 (사전 검증 포함) |
| `down.sh` | 스택 정지 (`--purge` 로 볼륨 삭제) |
| `backup-dashboards.sh` | Grafana 대시보드 JSON 백업 |
| `seed-alert-rules.sh` | promtool/amtool 로 룰·설정 검증 |

## 빠른 시작

```bash
# 1) 환경변수 설정 (.env)
cat >> .env <<'EOF'
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=<32자 이상 랜덤>
GRAFANA_ROOT_URL=http://grafana.tradepilot.local
SLACK_WEBHOOK_DEFAULT=https://hooks.slack.com/services/XXX
SLACK_WEBHOOK_CRITICAL=https://hooks.slack.com/services/YYY
SLACK_WEBHOOK_SECURITY=https://hooks.slack.com/services/ZZZ
ALERT_EMAIL_CRITICAL=oncall@tradepilot.local
ALERT_EMAIL_SECURITY=security@tradepilot.local
EOF

# 2) 메인 스택이 떠 있어야 함 (tp-net 네트워크 필요)
docker compose up -d

# 3) 관측성 스택 기동
bash infra/observability/scripts/up.sh

# 4) Grafana 접속 (사설망 또는 nginx 경유)
#    http://localhost:3000  admin / $GRAFANA_ADMIN_PASSWORD
```

## 운영 절차

### 룰/설정 변경 후 (반드시 검증)
```bash
bash infra/observability/scripts/seed-alert-rules.sh
# 통과 시 prometheus reload
curl -X POST http://prometheus:9090/-/reload
```

### 대시보드 백업 (일일/주간)
```bash
GRAFANA_ADMIN_PASSWORD=... bash infra/observability/scripts/backup-dashboards.sh
# 결과: infra/observability/grafana/dashboards-backup/YYYYMMDD/*.json
# Git 으로 버전 관리 권장
```

### 메트릭 보존 변경 시
`docker-compose.observability.yml` 의 prometheus 서비스 command:
- `--storage.tsdb.retention.time=30d` 수정 후 재기동.

## 트러블슈팅

| 증상 | 원인 | 조치 |
|---|---|---|
| Grafana 기동 실패 | `GRAFANA_ADMIN_PASSWORD` 미설정 | `.env` 에 강한 패스워드 설정 |
| Prometheus 룰 누락 | 룰 파일 마운트 경로 오류 | `seed-alert-rules.sh` 실행 |
| Alertmanager 알림 미발송 | webhook URL placeholder | `.env` 의 `SLACK_WEBHOOK_*` 실제 값으로 교체 |
| Loki 데이터 없음 | Promtail 도커 소켓 권한 없음 | `/var/run/docker.sock` 접근 권한 확인 |
| nginx 메트릭 0 | stub_status 미활성 | `exporters/nginx-exporter-note.md` 가이드 따라 활성화 |
