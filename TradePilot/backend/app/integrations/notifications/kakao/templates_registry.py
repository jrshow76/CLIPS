"""카카오 알림톡 템플릿 메타 레지스트리.

알림톡 운영 절차상 발송 가능한 메시지는 사전에 카카오비즈/NHN Cloud 콘솔에 등록되어
승인된 템플릿만 가능하다. 본 레지스트리는 코드와 템플릿 ID(또는 키)를 매핑하고,
서비스 코드가 발송할 때 사용할 ``template_code`` 와 변수 형식을 정의한다.

운영 환경에서는 ``template_id`` 를 콘솔에서 발급된 실제 값으로 갱신해야 한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class KakaoTemplate:
    """알림톡 템플릿 메타."""

    code: str
    template_id: str
    name: str
    sample_content: str
    variables: tuple[str, ...]


# 운영 콘솔 등록 후 template_id 값을 교체한다.
KAKAO_TEMPLATES: dict[str, KakaoTemplate] = {
    "SIGNAL_ALERT": KakaoTemplate(
        code="SIGNAL_ALERT",
        template_id="TP_SIGNAL_001",
        name="매매 시그널 발생",
        sample_content=(
            "[TradePilot]\n"
            "#{stock_name}(#{stock_code})에 #{action_ko} 시그널이 감지되었습니다.\n"
            "전략: #{strategy_name}\n"
            "신뢰도: #{confidence}\n"
            "기준가: #{trigger_price}원"
        ),
        variables=("stock_name", "stock_code", "action_ko", "strategy_name", "confidence", "trigger_price"),
    ),
    "EXECUTION_ALERT": KakaoTemplate(
        code="EXECUTION_ALERT",
        template_id="TP_EXEC_001",
        name="주문 체결",
        sample_content=(
            "[TradePilot]\n"
            "#{stock_name}(#{stock_code}) #{side_ko} 체결\n"
            "수량: #{filled_qty}주 / 단가: #{filled_price}원\n"
            "체결시각: #{filled_at}"
        ),
        variables=("stock_name", "stock_code", "side_ko", "filled_qty", "filled_price", "filled_at"),
    ),
    "KILL_SWITCH": KakaoTemplate(
        code="KILL_SWITCH",
        template_id="TP_KILL_001",
        name="비상정지 발동",
        sample_content=(
            "[TradePilot - 중요]\n"
            "Kill Switch가 발동되었습니다.\n"
            "사유: #{reason}\n"
            "취소 #{canceled_count}건 / 실패 #{failed_count}건\n"
            "즉시 웹에서 상태를 확인해주세요."
        ),
        variables=("reason", "canceled_count", "failed_count"),
    ),
    "SECURITY_ALERT": KakaoTemplate(
        code="SECURITY_ALERT",
        template_id="TP_SEC_001",
        name="보안 이벤트",
        sample_content=(
            "[TradePilot - 보안]\n"
            "계정에서 #{event_type_ko}이(가) 감지되었습니다.\n"
            "시각: #{occurred_at}\n"
            "본인 활동이 아닌 경우 즉시 비밀번호를 변경해주세요."
        ),
        variables=("event_type_ko", "occurred_at"),
    ),
    "DAILY_REPORT": KakaoTemplate(
        code="DAILY_REPORT",
        template_id="TP_DAILY_001",
        name="일일 매매 리포트",
        sample_content=(
            "[TradePilot]\n"
            "#{report_date} 일일 리포트\n"
            "실현손익: #{realized_pnl}원\n"
            "승률: #{win_rate}%\n"
            "상세 내용은 이메일을 확인해주세요."
        ),
        variables=("report_date", "realized_pnl", "win_rate"),
    ),
}


def get_kakao_template(code: str) -> KakaoTemplate | None:
    """코드로 알림톡 템플릿 메타 조회."""
    return KAKAO_TEMPLATES.get(code)


def render_kakao_content(code: str, variables: dict[str, Any]) -> str:
    """알림톡 ``sample_content`` 의 ``#{key}`` 변수를 실값으로 치환한 텍스트 반환.

    실제 NHN Cloud 알림톡 API 는 ``templateParameter`` 로 변수를 전달하므로 본 함수는
    Fallback(SMS) 용 본문 생성 및 단위 테스트에 사용된다.
    """
    tpl = get_kakao_template(code)
    if not tpl:
        return ""
    content = tpl.sample_content
    for k, v in variables.items():
        content = content.replace("#{" + k + "}", str(v))
    return content
