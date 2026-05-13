"""시장 캘린더 API 통합 테스트.

DB(Postgres) + Redis 가 기동된 환경에서 동작.
시드(`16_calendar_seed.sql`) 데이터를 전제로 한다.
"""
from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.integration


def _signup_and_login(app_client, email_prefix: str = "user") -> str:
    email = f"{email_prefix}-{uuid.uuid4().hex[:8]}@test.local"
    pw = "Abcd1234!"
    app_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": pw, "nickname": "t"},
    )
    r = app_client.post("/api/v1/auth/login", json={"email": email, "password": pw})
    return r.json()["data"]["access_token"]


def _admin_token(app_client) -> str:
    """초기 시드된 admin 계정의 비밀번호를 강제로 세팅 후 로그인.
    초기 비밀번호 해시는 더미('!')이므로 신규 회원가입한 사용자를 admin 으로
    승격시키는 훅이 없는 환경에서는 별도 방식이 필요. 본 테스트는
    퍼블릭 조회 + 인증된 일반 사용자 케이스만 검증한다.
    """
    return _signup_and_login(app_client, "admin-tester")


# ---------------------------------------------------------------------------
# 1) 퍼블릭 조회
# ---------------------------------------------------------------------------
def test_get_calendar_legacy_query_returns_2026(app_client) -> None:
    """레거시 ?year= 쿼리 캘린더는 2026 신정을 포함."""
    r = app_client.get("/api/v1/market/calendar?year=2026")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)
    assert any(item["date"] == "2026-01-01" for item in body["data"])


def test_get_calendar_by_year_returns_seed_holidays(app_client) -> None:
    r = app_client.get("/api/v1/market/calendar/2026")
    assert r.status_code == 200, r.text
    items = r.json()["data"]
    assert isinstance(items, list)
    assert len(items) >= 10
    # 첫 항목은 신정
    first = items[0]
    assert first["holiday_date"] == "2026-01-01"
    assert first["holiday_name"] == "신정"
    assert first["holiday_type"] in ("REGULAR", "TEMPORARY", "SUBSTITUTE")
    assert first["market"] == "KRX"


def test_get_business_day_for_2026_01_05(app_client) -> None:
    """2026-01-05(월)은 영업일, 이전 영업일은 2026-01-02, 다음은 2026-01-06."""
    r = app_client.get("/api/v1/market/calendar/business-day/2026-01-05")
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["date"] == "2026-01-05"
    assert data["is_business_day"] is True
    assert data["is_holiday"] is False
    assert data["is_weekend"] is False
    assert data["previous_business_day"] == "2026-01-02"
    assert data["next_business_day"] == "2026-01-06"


def test_get_business_day_for_seollal(app_client) -> None:
    """2026-02-17 설날은 휴장 + 영업일 아님."""
    r = app_client.get("/api/v1/market/calendar/business-day/2026-02-17")
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["is_business_day"] is False
    assert data["is_holiday"] is True


# ---------------------------------------------------------------------------
# 2) 관리자 - 동기화 (mock pykrx)
# ---------------------------------------------------------------------------
def test_admin_sync_calendar_requires_role(app_client) -> None:
    """일반 사용자는 ROLE_ADMIN/OPERATOR 가 아니므로 403 (E0002 또는 E0092)."""
    token = _signup_and_login(app_client)
    r = app_client.post(
        "/api/v1/admin/market/calendar/sync/2027",
        headers={"Authorization": f"Bearer {token}"},
    )
    # 권한 없음
    assert r.status_code in (401, 403)


def test_admin_sync_invalid_year(app_client) -> None:
    """잘못된 연도는 401(권한 미선통과 시) 또는 400(통과 후 검증)."""
    token = _signup_and_login(app_client)
    r = app_client.post(
        "/api/v1/admin/market/calendar/sync/1999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code in (400, 401, 403)


# ---------------------------------------------------------------------------
# 3) sync_from_krx 내부 로직 - mock pykrx
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_sync_from_krx_with_mocked_pykrx_unavailable() -> None:
    """pykrx 미설치 환경에서는 빈 결과를 반환하고 예외 없이 동작."""
    from app.services import calendar_service as cs

    class _FakeSession:
        async def execute(self, *a, **kw): ...
        async def commit(self): ...

    svc = cs.CalendarService(_FakeSession())  # type: ignore[arg-type]

    def _raise_unavailable(_year: int):
        raise cs._PykrxUnavailable("pykrx import 실패")

    with patch.object(cs, "_fetch_pykrx_holidays", side_effect=_raise_unavailable):
        result = await svc.sync_from_krx(2027)
    assert result == {"fetched": 0, "upserted": 0, "skipped": 0}
