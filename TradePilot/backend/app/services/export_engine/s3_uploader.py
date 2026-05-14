"""S3 업로드 + 사전서명 URL 발급.

- ``boto3`` 클라이언트는 ``EXPORT_S3_ENDPOINT_URL`` 이 있으면 MinIO/R2 등 호환 스토리지로 사용.
- 10MB 이상 파일은 멀티파트 업로드 (boto3 ``upload_fileobj`` 가 ``TransferConfig`` 로 자동 처리).
- 사전서명 URL 은 GET 동작 + 기본 1시간 TTL.
- 객체 삭제는 ``cleanup_expired`` 잡에서 호출.
"""
from __future__ import annotations

from io import BytesIO
from typing import Any

import structlog

from app.services.export_engine.config import ExportConfig, get_export_config

log = structlog.get_logger(__name__)


class S3Uploader:
    """boto3 기반 S3 업로드 래퍼."""

    def __init__(self, config: ExportConfig | None = None) -> None:
        self.config = config or get_export_config()
        self._client: Any | None = None

    # ------------------------------------------------------------------
    # 클라이언트 lazy 생성 (boto3 import 비용 최소화)
    # ------------------------------------------------------------------
    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        import boto3
        from botocore.config import Config as BotoConfig

        kwargs: dict[str, Any] = {
            "region_name": self.config.s3_region,
            "config": BotoConfig(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        }
        if self.config.s3_endpoint_url:
            kwargs["endpoint_url"] = self.config.s3_endpoint_url
        if self.config.s3_access_key and self.config.s3_secret_key:
            kwargs["aws_access_key_id"] = self.config.s3_access_key
            kwargs["aws_secret_access_key"] = self.config.s3_secret_key

        self._client = boto3.client("s3", **kwargs)
        return self._client

    def set_client(self, client: Any) -> None:
        """테스트용 클라이언트 주입(스텁/모의)."""
        self._client = client

    # ------------------------------------------------------------------
    # 업로드
    # ------------------------------------------------------------------
    def upload_bytes(
        self,
        data: bytes,
        key: str,
        *,
        content_type: str,
    ) -> dict[str, Any]:
        """바이트를 S3 객체로 업로드한다. (10MB 이상은 멀티파트.)

        Returns:
            ``{"key": ..., "size": ..., "etag": ...}``
        """
        client = self._get_client()
        size = len(data)
        threshold = self.config.multipart_threshold_mb * 1024 * 1024

        if size < threshold:
            # 단일 PUT
            resp = client.put_object(
                Bucket=self.config.s3_bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
                # 사용자 데이터 → 서버 측 암호화 권장
                ServerSideEncryption="AES256",
            )
            log.info("s3_put_object", key=key, size=size)
            return {"key": key, "size": size, "etag": resp.get("ETag")}

        # 멀티파트 업로드 (boto3 upload_fileobj 가 자동 처리)
        from boto3.s3.transfer import TransferConfig

        transfer_cfg = TransferConfig(
            multipart_threshold=threshold,
            multipart_chunksize=threshold,
            use_threads=True,
        )
        client.upload_fileobj(
            Fileobj=BytesIO(data),
            Bucket=self.config.s3_bucket,
            Key=key,
            Config=transfer_cfg,
            ExtraArgs={
                "ContentType": content_type,
                "ServerSideEncryption": "AES256",
            },
        )
        log.info("s3_multipart_upload", key=key, size=size)
        return {"key": key, "size": size, "etag": None}

    # ------------------------------------------------------------------
    # 사전서명 URL
    # ------------------------------------------------------------------
    def generate_presigned_url(self, key: str, *, ttl_sec: int | None = None) -> str:
        """GET 동작용 사전서명 URL 발급. TTL 미지정 시 설정값(1h)."""
        client = self._get_client()
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.config.s3_bucket, "Key": key},
            ExpiresIn=ttl_sec or self.config.presign_ttl_sec,
        )

    # ------------------------------------------------------------------
    # 삭제 (cleanup)
    # ------------------------------------------------------------------
    def delete_object(self, key: str) -> None:
        """객체 삭제. 존재하지 않아도 예외 던지지 않는다."""
        client = self._get_client()
        try:
            client.delete_object(Bucket=self.config.s3_bucket, Key=key)
            log.info("s3_delete_object", key=key)
        except Exception as exc:  # noqa: BLE001 - cleanup best-effort
            log.warning("s3_delete_failed", key=key, error=str(exc)[:200])


def content_type_for(format_: str) -> str:
    """포맷에 맞는 MIME 타입."""
    fmt = format_.upper()
    if fmt == "XLSX":
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return "text/csv; charset=utf-8"


def extension_for(format_: str) -> str:
    fmt = format_.upper()
    return "xlsx" if fmt == "XLSX" else "csv"
