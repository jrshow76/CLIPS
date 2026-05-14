"""증권사(Broker) 도메인 정의.

다증권사 어댑터 추상화에서 사용하는 enum 과 메타데이터.

- ``Broker``: 지원 증권사 enum (DB 값과 일치)
- ``BrokerInfo``: 사용자 노출용 메타 (시장/Windows 의존성/API 타입)
- ``BROKER_REGISTRY``: 시스템 기본값 + 화면용 카탈로그

설계 원칙:
- enum 문자열은 DB ``users.preferred_broker``, ``broker_status.broker`` 컬럼 값과 1:1.
- 신규 증권사를 추가할 때는 (1) enum + (2) BROKER_REGISTRY + (3) factory 분기 + (4) docs 비교표.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Broker(str, Enum):
    """지원 증권사.

    값은 대문자 식별자. DB / API / 환경변수 전반에서 그대로 사용한다.
    """

    CREON = "CREON"   # 대신증권 Plus (COM, Windows 전용)
    KIS = "KIS"       # 한국투자증권 OpenAPI (REST + WebSocket, OS 무관)
    KIWOOM = "KIWOOM" # 키움증권 OpenAPI+ (COM 32-bit, Windows 전용)


class BrokerApiType(str, Enum):
    """증권사 API 통신 방식."""

    REST = "REST"      # KIS — 백엔드에서 직접 호출 가능
    COM = "COM"        # CREON / KIWOOM — Windows 게이트웨이 경유


@dataclass(frozen=True)
class BrokerInfo:
    """증권사 메타 (사용자 노출 + 팩토리 분기 결정에 사용).

    필드:
    - ``name``: 화면 노출용 한글 명
    - ``broker``: ``Broker`` enum
    - ``api_type``: REST(직접) vs COM(게이트웨이)
    - ``supports_markets``: 지원 시장 목록 (KOSPI/KOSDAQ/NYSE 등)
    - ``requires_windows``: Windows 호스트 게이트웨이 필요 여부
    - ``supports_sim``: 모의투자 지원 여부
    - ``supports_real``: 실거래 지원 여부
    - ``recommended``: 시스템 권장 여부 (UI 정렬용)
    - ``notes``: 운영자 안내 메모
    """

    name: str
    broker: Broker
    api_type: BrokerApiType
    supports_markets: tuple[str, ...] = field(default=("KOSPI", "KOSDAQ"))
    requires_windows: bool = False
    supports_sim: bool = True
    supports_real: bool = True
    recommended: bool = False
    notes: str = ""


# 시스템 카탈로그 (등록 순서가 UI 노출 순서)
BROKER_REGISTRY: dict[Broker, BrokerInfo] = {
    Broker.KIS: BrokerInfo(
        name="한국투자증권",
        broker=Broker.KIS,
        api_type=BrokerApiType.REST,
        supports_markets=("KOSPI", "KOSDAQ", "NYSE", "NASDAQ"),
        requires_windows=False,
        supports_sim=True,
        supports_real=True,
        recommended=True,
        notes="REST + WebSocket. Linux 백엔드에서 직접 호출 가능. 가장 권장.",
    ),
    Broker.CREON: BrokerInfo(
        name="대신증권 (CREON Plus)",
        broker=Broker.CREON,
        api_type=BrokerApiType.COM,
        supports_markets=("KOSPI", "KOSDAQ"),
        requires_windows=True,
        supports_sim=True,
        supports_real=True,
        recommended=False,
        notes="COM 32-bit. Windows 게이트웨이 필수. 기존 운영 환경 호환.",
    ),
    Broker.KIWOOM: BrokerInfo(
        name="키움증권 (OpenAPI+)",
        broker=Broker.KIWOOM,
        api_type=BrokerApiType.COM,
        supports_markets=("KOSPI", "KOSDAQ", "ELW", "ETF"),
        requires_windows=True,
        supports_sim=True,
        supports_real=True,
        recommended=False,
        notes="ActiveX 32-bit. Windows 게이트웨이 필수. CREON 백업으로 권장.",
    ),
}


def get_broker_info(broker: Broker | str) -> BrokerInfo:
    """문자열/enum 모두 허용. 미등록 broker는 KeyError."""
    if isinstance(broker, str):
        broker = Broker(broker)
    return BROKER_REGISTRY[broker]


def list_broker_infos() -> list[BrokerInfo]:
    """등록된 모든 증권사 메타 (UI 카탈로그용)."""
    return list(BROKER_REGISTRY.values())


# 시스템 기본 broker (사용자 미설정 시 사용).
# 환경변수 DEFAULT_BROKER 로 운영 환경에서 override 가능 (config.py 참고).
DEFAULT_BROKER: Broker = Broker.CREON
