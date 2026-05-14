"""KIS OAuth2 토큰 관리.

KIS 토큰 발급 엔드포인트: ``POST /oauth2/tokenP``
요청 바디: ``{"grant_type": "client_credentials", "appkey", "appsecret"}``
응답: ``{"access_token", "token_type": "Bearer", "expires_in": 86400}``

설계:
- Redis 캐시 키: ``tp:kis:token:<appkey-hash>``  (appkey 별 분리)
- TTL: ``expires_in - 1시간`` (사전 갱신 마진) — 기본 23시간
- 동시 갱신 회피: Redis 분산락(SET NX) 5초

테스트 (`tests/unit/test_kis_adapter.py`):
- mock httpx → 토큰 발급 1회 후 캐시 hit
- TTL 만료 시 재발급
"""
from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass
from typing import Any

import httpx
import orjson
import structlog

from app.core.exceptions import AppException
from app.core.redis_client import get_redis
from app.integrations.kis.config import KisConfig, get_kis_config

log = structlog.get_logger(__name__)


@dataclass
class KisToken:
    """KIS access token 보유 객체."""

    access_token: str
    token_type: str
    expires_at: float  # epoch seconds (만료 시각)

    def is_expired(self, margin_sec: int = 60) -> bool:
        return time.time() + margin_sec >= self.expires_at

    def bearer(self) -> str:
        return f"{self.token_type} {self.access_token}"


def _cache_key(appkey: str) -> str:
    # appkey 그대로 노출하지 않도록 해시
    h = hashlib.sha256(appkey.encode("utf-8")).hexdigest()[:16]
    return f"tp:kis:token:{h}"


def _lock_key(appkey: str) -> str:
    h = hashlib.sha256(appkey.encode("utf-8")).hexdigest()[:16]
    return f"tp:kis:token:lock:{h}"


class KisAuth:
    """KIS 토큰 발급/캐시 관리자.

    어댑터 단위 싱글톤 사용을 권장하며, 자격증명을 사용자별로 사용해야
    하는 경우 `with_credentials()` 로 클론한다.
    """

    def __init__(
        self,
        config: KisConfig | None = None,
        *,
        appkey: str | None = None,
        appsecret: str | None = None,
        trade_mode: str | None = None,
    ) -> None:
        self.config = config or get_kis_config()
        self.appkey = appkey or self.config.appkey
        self.appsecret = appsecret or self.config.appsecret
        self.trade_mode = (trade_mode or self.config.trade_env).upper()
        self._cached: KisToken | None = None
        self._lock = asyncio.Lock()

    def with_credentials(
        self, appkey: str, appsecret: str, trade_mode: str | None = None
    ) -> "KisAuth":
        """사용자별 자격증명으로 새 인스턴스 생성 (캐시 분리)."""
        return KisAuth(
            config=self.config,
            appkey=appkey,
            appsecret=appsecret,
            trade_mode=trade_mode or self.trade_mode,
        )

    # ------------------------------------------------------------------
    # 핵심 API
    # ------------------------------------------------------------------
    async def get_token(self) -> KisToken:
        """캐시 → Redis → 발급 순서로 토큰 반환."""
        # 1) 메모리 캐시
        if self._cached and not self._cached.is_expired():
            return self._cached

        async with self._lock:
            # 다른 코루틴이 이미 갱신했을 수 있음
            if self._cached and not self._cached.is_expired():
                return self._cached

            # 2) Redis 캐시
            redis_token = await self._read_from_redis()
            if redis_token and not redis_token.is_expired():
                self._cached = redis_token
                return redis_token

            # 3) 신규 발급 (분산락)
            token = await self._issue_with_lock()
            self._cached = token
            return token

    async def invalidate(self) -> None:
        """수동 무효화 — 인증 오류 응답 수신 시 호출."""
        self._cached = None
        try:
            await get_redis().delete(_cache_key(self.appkey))
        except Exception:  # noqa: BLE001
            log.warning("kis_token_invalidate_redis_failed")

    # ------------------------------------------------------------------
    # 내부 헬퍼
    # ------------------------------------------------------------------
    async def _read_from_redis(self) -> KisToken | None:
        try:
            raw = await get_redis().get(_cache_key(self.appkey))
        except Exception:  # noqa: BLE001
            return None
        if not raw:
            return None
        try:
            data = orjson.loads(raw)
            return KisToken(
                access_token=data["access_token"],
                token_type=data["token_type"],
                expires_at=float(data["expires_at"]),
            )
        except Exception:  # noqa: BLE001
            return None

    async def _write_to_redis(self, token: KisToken) -> None:
        ttl = max(60, int(token.expires_at - time.time()) - 60)
        try:
            await get_redis().setex(
                _cache_key(self.appkey),
                ttl,
                orjson.dumps(
                    {
                        "access_token": token.access_token,
                        "token_type": token.token_type,
                        "expires_at": token.expires_at,
                    }
                ),
            )
        except Exception:  # noqa: BLE001
            log.warning("kis_token_redis_write_failed")

    async def _issue_with_lock(self) -> KisToken:
        """Redis 분산락으로 KIS 동시 토큰 발급 회피."""
        redis = get_redis()
        lock_key = _lock_key(self.appkey)
        # SET NX EX
        try:
            acquired = await redis.set(lock_key, "1", nx=True, ex=5)
        except Exception:  # noqa: BLE001
            acquired = True  # Redis 장애 시 락 무시하고 진행

        if not acquired:
            # 누가 발급 중 → 잠시 대기 후 캐시 재확인
            for _ in range(20):  # 최대 ~2초
                await asyncio.sleep(0.1)
                cached = await self._read_from_redis()
                if cached and not cached.is_expired():
                    return cached
            # 락 보유자가 발급에 실패한 케이스 — 강제 발급
        try:
            token = await self._call_token_endpoint()
            await self._write_to_redis(token)
            return token
        finally:
            try:
                await redis.delete(lock_key)
            except Exception:  # noqa: BLE001
                pass

    async def _call_token_endpoint(self) -> KisToken:
        """KIS ``/oauth2/tokenP`` 호출."""
        if not self.appkey or not self.appsecret:
            raise AppException(
                "E0001",
                message="KIS 자격증명(APPKEY/APPSECRET) 이 설정되지 않았습니다.",
            )
        url = self.config.base_url(self.trade_mode) + "/oauth2/tokenP"
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.appkey,
            "appsecret": self.appsecret,
        }
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_sec) as cli:
                resp = await cli.post(
                    url, json=payload, headers={"Content-Type": "application/json"}
                )
        except httpx.TimeoutException as e:
            raise AppException("E0072", message="KIS 토큰 발급 타임아웃") from e
        except httpx.RequestError as e:
            raise AppException("E0012", message="KIS 토큰 엔드포인트 연결 실패") from e

        if resp.status_code >= 500:
            raise AppException(
                "E0004",
                message="KIS 토큰 발급 서버 오류",
                details={"status": resp.status_code},
            )
        try:
            data: dict[str, Any] = resp.json()
        except Exception as e:
            raise AppException("E0004", message="KIS 토큰 응답 파싱 실패") from e
        if "access_token" not in data:
            raise AppException(
                "E0001",
                message="KIS 토큰 발급 실패",
                details={
                    "msg_cd": data.get("error_code"),
                    "msg": data.get("error_description"),
                },
            )
        expires_in = int(data.get("expires_in", 86400))
        # 사전 마진 (1시간) 적용
        expires_at = time.time() + max(60, expires_in - 3600)
        token = KisToken(
            access_token=str(data["access_token"]),
            token_type=str(data.get("token_type", "Bearer")),
            expires_at=expires_at,
        )
        log.info("kis_token_issued", trade_mode=self.trade_mode, ttl=expires_in)
        return token


# 모듈 싱글톤 (시스템 기본 자격증명)
_auth_singleton: KisAuth | None = None


def get_kis_auth() -> KisAuth:
    global _auth_singleton
    if _auth_singleton is None:
        _auth_singleton = KisAuth()
    return _auth_singleton


def reset_kis_auth() -> None:
    """테스트용."""
    global _auth_singleton
    _auth_singleton = None
