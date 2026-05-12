"""pytest 공통 픽스처.

- 단위 테스트는 DB 없이 동작
- 통합 테스트는 testcontainers 또는 별도 DOCKER로 실행한다고 가정 (CI 환경)
"""
from __future__ import annotations

import os

import pytest

# 테스트 환경 강제
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-test")
os.environ.setdefault("AES_KEY", "test-aes-key-32-byte-test-key-12")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")


@pytest.fixture
def app_client():
    """FastAPI TestClient (lifespan 비활성화 가능 환경에서만 사용)."""
    from fastapi.testclient import TestClient
    from app.main import create_app

    application = create_app()
    with TestClient(application) as client:
        yield client
