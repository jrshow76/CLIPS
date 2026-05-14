"""KIS 응답 코드 → 표준 에러 코드(Exxxx) 매핑.

KIS REST 응답 구조 (성공/실패 공통):
  {
    "rt_cd": "0" | "1",              # 0=성공, 그 외 실패
    "msg_cd": "OPSP0000" | ...,      # 비즈니스 코드
    "msg1": "정상처리 되었습니다.",
    "output": {...},
    ...
  }

매핑 방침:
- 통신/타임아웃: 본체 ``KisClient`` 가 ``E0072 / E0004`` 직접 발생.
- 비즈니스 거부: 본 모듈에서 msg_cd 분류 후 ``E00xx`` 매핑.
- 알려지지 않은 코드: ``E0023`` (증권사 주문 처리 오류) 기본값.
"""
from __future__ import annotations

# KIS 비즈니스 코드 → 본체 표준 에러 코드.
# 실제 운영 도중 추가 코드 확인 시 본 매핑 확장 (코드 변동 가능 → 변경 시 docs 동기화).
KIS_MSG_CODE_MAP: dict[str, str] = {
    # 인증/권한
    "EGW00121": "E0001",  # 토큰 만료
    "EGW00123": "E0001",  # 잘못된 토큰
    "EGW00201": "E0002",  # 권한 없음
    # 주문 거부
    "OPSP0001": "E0023",  # 일반 주문 실패
    "APBK0918": "E0024",  # 증거금 부족 (가정)
    "APBK0919": "E0024",  # 매도 가능 수량 부족
    "APBK0920": "E0026",  # 호가 단위 오류
    "APBK0921": "E0027",  # 상하한가
    "APBK0922": "E0028",  # 거래 정지
    # 시세
    "MCA00120": "E0061",  # 시세 미수신
}


def map_kis_error(msg_cd: str | None, default: str = "E0023") -> str:
    """KIS msg_cd → 표준 에러 코드."""
    if not msg_cd:
        return default
    return KIS_MSG_CODE_MAP.get(msg_cd, default)


def is_success(rt_cd: str | int | None) -> bool:
    """KIS rt_cd 가 성공(0) 인지 판단."""
    if rt_cd is None:
        return False
    return str(rt_cd).strip() == "0"
