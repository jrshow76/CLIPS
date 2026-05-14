# 48. 익스포트(CSV/XLSX) 가이드

본 문서는 TradePilot 의 거래내역/리포트 익스포트 기능(D2) 의 운영·개발 가이드이다.
구현 위치는 다음과 같다.

| 구성 요소 | 경로 |
| --- | --- |
| DB 마이그레이션 | `database/migrations/2026_05_add_export_jobs.sql` |
| ORM | `backend/app/models/trade.py` (`ExportJob`) |
| 엔진 패키지 | `backend/app/services/export_engine/` |
| 서비스 | `backend/app/services/export_service.py` |
| 워커 | `backend/app/workers/tasks/export_tasks.py` |
| API | `backend/app/api/v1/exports.py` |
| 프론트엔드 | `frontend/src/components/exports/`, `frontend/src/lib/api/queries/exports.ts` |

## 1. 익스포트 흐름

```
사용자 → [POST /exports] → ExportService.request_export
                ↓ Celery enqueue (queue=exports)
        [exports.run] 워커
                ↓
        EXTRACTORS[job_type](db, user_id, filter_params)
                ↓ DataFrame{시트명}
        write_csv / write_xlsx
                ↓ bytes
        S3Uploader.upload_bytes (10MB 이상 멀티파트)
                ↓
        generate_presigned_url (TTL 1h)
                ↓
        export_jobs UPDATE status=DONE, download_url, expires_at(=완료 후 7일)
                ↓
사용자 ← [GET /exports/{id}/download] ← presigned URL (만료 시 자동 갱신)
```

진행률 단계: **10% 추출 → 60% 직렬화 → 90% S3 업로드 → 100% 완료**

각 단계에서 Redis 채널 `export:{public_id}` 로 진행률을 publish 한다. 프론트엔드는
폴링(3초 간격) 으로도 동일 정보를 받는다.

## 2. 익스포트 종류 5종

| job_type | 시트 | 주요 필터 |
| --- | --- | --- |
| `ORDERS` | 주문, 체결 | `from`, `to`, `code`, `status` |
| `PNL` | 일별, 월별 | `from`, `to` |
| `BACKTEST` | 백테스트요약, 거래내역, 자본곡선 | `run_id` 또는 `run_id_list` |
| `SIGNALS` | 시그널이력 | `from`, `to`, `code`, `action` |
| `POSITIONS` | 보유종목 | `trade_mode` (SIM/LIVE) |

CSV 포맷 선택 시 첫 번째 시트(메인) 만 사용된다. 다중 시트가 의미 있는
ORDERS / PNL / BACKTEST 는 XLSX 사용을 권장한다.

## 3. 한글 헤더 매핑

영문 → 한글 매핑은 `app/services/export_engine/formats/header_map.py` 의
`HEADER_MAP` 단일 출처를 따른다. 새 컬럼 추가 시 본 매핑과 (포맷이 필요한 경우)
다음 분류 집합도 함께 갱신해야 한다.

| 분류 | 포맷 | 예시 컬럼 |
| --- | --- | --- |
| `CURRENCY_COLUMNS` | `#,##0` | `price`, `fee`, `realized_pnl`, `cash` |
| `PERCENT_COLUMNS` | `0.00%` | `mdd`, `win_rate`, `cumulative_return` |
| `NUMERIC_COLUMNS` | `#,##0` | `qty`, `fill_qty`, `trade_count` |
| `DATE_COLUMNS` | `yyyy-mm-dd` | `trade_date`, `period_from` |
| `DATETIME_COLUMNS` | `yyyy-mm-dd hh:mm:ss` | `ordered_at`, `filled_at` |

매핑에 없는 컬럼은 원본 영문 이름이 그대로 출력된다. CSV 는 UTF-8 BOM
선두 바이트를 포함하여 엑셀에서 바로 열어도 한글이 깨지지 않는다.

## 4. S3 설정

### 4.1. AWS S3

```bash
# .env
EXPORT_S3_BUCKET=tradepilot-exports
EXPORT_S3_REGION=ap-northeast-2
EXPORT_S3_PREFIX=exports/
# IAM Role 사용 시 ACCESS/SECRET 비워둠
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
```

### 4.2. MinIO / Cloudflare R2

```bash
EXPORT_S3_ENDPOINT_URL=https://minio.internal:9000   # 또는 R2 endpoint
EXPORT_S3_BUCKET=tradepilot-exports
EXPORT_S3_REGION=us-east-1                            # 호환 임의값
AWS_ACCESS_KEY_ID=MINIO_ACCESS_KEY
AWS_SECRET_ACCESS_KEY=MINIO_SECRET_KEY
```

boto3 는 `signature_version=s3v4` 를 사용하므로 MinIO/R2 와 호환된다.

### 4.3. IAM 권한 가이드 (최소 권한)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "TradePilotExportRW",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:AbortMultipartUpload"
      ],
      "Resource": "arn:aws:s3:::tradepilot-exports/exports/*"
    },
    {
      "Sid": "TradePilotExportList",
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::tradepilot-exports",
      "Condition": {"StringLike": {"s3:prefix": ["exports/*"]}}
    }
  ]
}
```

서버 측 암호화는 `AES256`(SSE-S3) 을 기본 사용한다. KMS 가 필요한 경우
`s3_uploader.py` 의 `ServerSideEncryption` / `SSEKMSKeyId` 를 조정한다.

## 5. 보안

- **사용자 격리**: S3 키는 `{prefix}{user_id}/{public_id}.{ext}` 형식이며,
  서비스 레이어가 `WHERE user_id = ?` 로 본인 잡만 조회·갱신한다. 다른 사용자
  익스포트에 접근 시 `E0062` 반환.
- **사전서명 URL**: 기본 1시간 TTL. 만료된 경우 `GET /exports/{id}/download`
  호출 시 자동 갱신된다 (`refresh_presigned_url`).
- **보관 기간**: 완료 후 7일(`EXPORT_TTL_HOURS=168`). cleanup 잡이
  `expires_at < now()` 인 행의 S3 객체 + DB 행을 삭제.

## 6. 한도

| 한도 | 기본값 | 환경변수 |
| --- | --- | --- |
| 사용자당 동시 PENDING/RUNNING | 3 | `EXPORT_CONCURRENT_PER_USER` |
| 사용자당 일일 신규 요청 | 20 | `EXPORT_DAILY_LIMIT_PER_USER` |
| 단일 익스포트 최대 행수 | 1,000,000 | `EXPORT_MAX_ROWS` |
| 청크 처리 크기 | 50,000 | `EXPORT_CHUNK_SIZE` |
| 멀티파트 임계치 | 10 MB | `EXPORT_MULTIPART_THRESHOLD_MB` |

한도 초과 시 `E0021` 반환.

## 7. 보관 정책 & 비용 추정

- 완료된 익스포트는 7일간 S3 에 보관 후 자동 삭제.
- 일평균 사용자 100명 × 익스포트 5건 × 평균 1MB ≈ 500MB/일.
- 7일 누적 ≈ 3.5GB. 월간 ≈ 100GB 미만.
- AWS S3 ap-northeast-2 기준 표준 스토리지 약 USD 2~3/월 수준 + 요청 비용.
- 멀티파트(10MB+) 외에는 PUT 요청 비용만 누적되므로 큰 추가 비용 없음.

## 8. 운영 체크리스트

1. **S3 버킷 생성** 후 라이프사이클 규칙으로 `exports/` prefix 에 8일 후
   자동 삭제 규칙을 보조로 추가(앱 cleanup 잡 누락 대비).
2. **버킷 정책**으로 외부 공개 차단(`BlockPublicAcls=true`).
3. **CloudWatch 알람**: `exports.cleanup_expired` 실패 시 알람.
4. **요청량 모니터링**: `export_jobs` 행 수 + S3 PUT 횟수 추적.

## 9. 트러블슈팅

| 증상 | 원인 | 조치 |
| --- | --- | --- |
| 404 NoSuchKey | cleanup 잡이 이미 삭제 | 새 익스포트 재요청 |
| Presigned URL 만료 | 1시간 경과 | `/exports/{id}/download` 재호출 시 자동 갱신 |
| 한도 초과(E0021) | 동시 3건/일 20건 초과 | 기존 잡 완료 후 재시도 또는 다음 날 |
| 파일 다운로드 시 한글 깨짐 | 엑셀이 BOM 미인식 | "데이터 가져오기 → CSV → UTF-8" 명시 선택 |
| 0 byte 파일 | 추출 결과 0건 | 헤더만 포함된 정상 동작. 필터 재확인 |
