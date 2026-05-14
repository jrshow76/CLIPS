"""익스포트 엔진 설정.

환경변수(`.env`) 기반으로 S3 버킷, 키 prefix, TTL 등을 일괄 로드한다.
운영 환경에서는 IAM Role 사용을 권장하며, 개발에서는 access key 또는 MinIO를
사용하기 위해 ``EXPORT_S3_ENDPOINT_URL`` 을 지정한다.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ExportConfig:
    """익스포트 런타임 설정.

    Attributes:
        s3_bucket: 업로드 대상 S3 버킷 이름.
        s3_region: S3 리전(IAM/Signer 용).
        s3_prefix: 키 prefix(예: ``exports/``). user_id, public_id 추가.
        s3_endpoint_url: MinIO/R2 호환 엔드포인트(없으면 AWS 기본).
        s3_access_key: IAM Role 없이 사용 시 access key.
        s3_secret_key: IAM Role 없이 사용 시 secret key.
        presign_ttl_sec: 사전서명 URL 만료(초). 기본 3600(1h).
        retention_hours: S3 파일 보관 기간(시간). 기본 168(7일).
        max_rows: 단일 익스포트 최대 행수. 초과 시 익스포트 실패 처리.
        chunk_size: pandas iterator 처리 시 청크 크기.
        multipart_threshold_mb: 멀티파트 업로드 임계치(MB).
        concurrent_per_user: 사용자당 동시 PENDING/RUNNING 최대.
        daily_limit_per_user: 사용자당 일일 신규 요청 최대.
    """

    s3_bucket: str
    s3_region: str
    s3_prefix: str
    s3_endpoint_url: str | None
    s3_access_key: str | None
    s3_secret_key: str | None
    presign_ttl_sec: int
    retention_hours: int
    max_rows: int
    chunk_size: int
    multipart_threshold_mb: int
    concurrent_per_user: int
    daily_limit_per_user: int

    def object_key(self, user_id: int, public_id: str, ext: str) -> str:
        """S3 object key 생성.

        형식: ``{prefix}{user_id}/{public_id}.{ext}``.
        prefix 가 ``exports/`` 인 경우 → ``exports/42/abc-def.csv``.
        """
        clean_prefix = self.s3_prefix.rstrip("/") + "/" if self.s3_prefix else ""
        return f"{clean_prefix}{user_id}/{public_id}.{ext.lstrip('.')}"


def _env_int(key: str, default: int) -> int:
    """환경변수 정수 파싱. 잘못된 값이면 기본값."""
    raw = os.getenv(key)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def get_export_config() -> ExportConfig:
    """현재 환경의 설정을 로드한다.

    테스트에서는 ``EXPORT_S3_BUCKET=test-bucket`` 정도로 충분하며,
    실제 boto3 호출은 mock 또는 botocore Stubber 로 처리한다.
    """
    return ExportConfig(
        s3_bucket=os.getenv("EXPORT_S3_BUCKET", "tradepilot-exports"),
        s3_region=os.getenv("EXPORT_S3_REGION", "ap-northeast-2"),
        s3_prefix=os.getenv("EXPORT_S3_PREFIX", "exports/"),
        s3_endpoint_url=os.getenv("EXPORT_S3_ENDPOINT_URL") or None,
        s3_access_key=os.getenv("AWS_ACCESS_KEY_ID") or None,
        s3_secret_key=os.getenv("AWS_SECRET_ACCESS_KEY") or None,
        presign_ttl_sec=_env_int("EXPORT_PRESIGN_TTL_SECONDS", 3600),
        retention_hours=_env_int("EXPORT_TTL_HOURS", 168),
        max_rows=_env_int("EXPORT_MAX_ROWS", 1_000_000),
        chunk_size=_env_int("EXPORT_CHUNK_SIZE", 50_000),
        multipart_threshold_mb=_env_int("EXPORT_MULTIPART_THRESHOLD_MB", 10),
        concurrent_per_user=_env_int("EXPORT_CONCURRENT_PER_USER", 3),
        daily_limit_per_user=_env_int("EXPORT_DAILY_LIMIT_PER_USER", 20),
    )
