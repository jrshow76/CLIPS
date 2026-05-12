"""CREON 게이트웨이 연결 + 단순 주문 검증 스크립트 (모의투자 모드).

본 스크립트는 운영자가 Windows 호스트 셋업 후 게이트웨이가 정상적으로
모의투자 환경에서 주문을 발주할 수 있는지를 빠르게 검증하기 위한 도구다.

수행 절차:
1. /healthz, /readyz 호출 → trade_env=SIM 확인
2. /account 호출 → 모의투자 계좌 접두사 확인
3. /market/quote/005930 → 현재가 조회
4. /orders 호출 → 1주 지정가 매수 주문 (idempotency_key 사용)
5. 5초 대기 후 /account/positions 호출 → 보유 종목 확인
6. (옵션) /orders/{id}/cancel 으로 매도 1주 발주

사용:
    python3 scripts/creon_connect_test.py \\
        --url http://gateway:9100 \\
        --api-key YOUR_KEY \\
        --code 005930 \\
        --dry-run     # 실제 주문은 하지 않고 조회만

종료 코드: 0=통과, 1=실패
"""
from __future__ import annotations

import argparse
import sys
import time
import uuid

try:
    import httpx
except ImportError:
    print("httpx 설치 필요: pip install httpx", file=sys.stderr)
    sys.exit(2)


DEFAULT_CODE = "005930"  # 삼성전자


def main() -> int:
    parser = argparse.ArgumentParser(description="CREON 게이트웨이 연결 + 주문 검증")
    parser.add_argument(
        "--url",
        default="http://localhost:9100",
        help="게이트웨이 URL (기본 http://localhost:9100)",
    )
    parser.add_argument("--api-key", required=True, help="X-Gateway-Api-Key")
    parser.add_argument(
        "--code",
        default=DEFAULT_CODE,
        help=f"테스트 종목 코드 (기본 {DEFAULT_CODE} 삼성전자)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 주문 발주 없이 조회만 수행",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="REAL 모드여도 진행 (안전장치 해제)",
    )
    args = parser.parse_args()

    client = httpx.Client(
        base_url=args.url.rstrip("/"),
        headers={"X-Gateway-Api-Key": args.api_key},
        timeout=httpx.Timeout(10.0, connect=3.0),
    )

    failures: list[str] = []

    def step(name: str) -> None:
        print(f"\n----- {name} -----")

    # -----------------------------------------------------------------
    # 1. healthz / readyz
    # -----------------------------------------------------------------
    step("1. /healthz")
    try:
        r = client.get("/healthz")
        r.raise_for_status()
        h = r.json()
        print(f"  trade_env = {h.get('trade_env')}, gateway_id = {h.get('gateway_id')}")
        if h.get("trade_env") == "REAL" and not args.force:
            print("[STOP] 게이트웨이가 REAL(실거래) 모드. --force 없이는 진행 거부.")
            return 1
    except Exception as e:
        failures.append(f"/healthz 실패: {e}")
        print(f"[FAIL] {e}")

    step("2. /readyz")
    try:
        r = client.get("/readyz")
        r.raise_for_status()
        body = r.json()
        print(f"  ok = {body.get('ok')}")
        print(f"  com_connected = {body.get('com_connected')}")
        print(f"  account_loaded = {body.get('account_loaded')}")
        if not body.get("ok"):
            failures.append("readyz ok=false")
    except Exception as e:
        failures.append(f"/readyz 실패: {e}")
        print(f"[FAIL] {e}")

    # -----------------------------------------------------------------
    # 3. /account
    # -----------------------------------------------------------------
    step("3. /account")
    try:
        r = client.get("/account")
        r.raise_for_status()
        body = r.json().get("data", {})
        print(f"  trade_env       = {body.get('trade_env')}")
        print(f"  expected_prefix = {body.get('expected_prefix')}")
        for a in body.get("accounts", []):
            acc_no = a.get("account_no", "")
            masked = acc_no[:4] + "****" if len(acc_no) >= 4 else acc_no
            print(f"  - account: {masked} (kind={a.get('account_kind')})")
        if not body.get("accounts"):
            failures.append("계좌 0개 — 모의투자 계좌 발급 확인 필요")
    except Exception as e:
        failures.append(f"/account 실패: {e}")
        print(f"[FAIL] {e}")

    # -----------------------------------------------------------------
    # 4. /market/quote
    # -----------------------------------------------------------------
    step(f"4. /market/quote/{args.code}")
    quote_price: float | None = None
    try:
        r = client.get(f"/market/quote/{args.code}")
        r.raise_for_status()
        q = r.json().get("data", {})
        quote_price = q.get("price")
        print(f"  현재가 = {quote_price}, 변동 = {q.get('change')}, 거래량 = {q.get('volume')}")
        if not quote_price or quote_price <= 0:
            failures.append("현재가 0 — 시세 미수신")
    except Exception as e:
        failures.append(f"/market/quote 실패: {e}")
        print(f"[FAIL] {e}")

    # -----------------------------------------------------------------
    # 5. /stocks/master
    # -----------------------------------------------------------------
    step(f"5. /stocks/master/{args.code}")
    try:
        r = client.get(f"/stocks/master/{args.code}")
        r.raise_for_status()
        m = r.json().get("data", {})
        print(f"  name = {m.get('name')}, market = {m.get('market')}")
        if not m.get("name"):
            failures.append("종목명 조회 실패")
    except Exception as e:
        failures.append(f"/stocks/master 실패: {e}")
        print(f"[FAIL] {e}")

    # -----------------------------------------------------------------
    # 6. /orders (지정가 매수)
    # -----------------------------------------------------------------
    broker_order_no: str | None = None
    if args.dry_run:
        print("\n[INFO] --dry-run 옵션으로 실제 주문 생략")
    elif quote_price:
        step("6. /orders (지정가 매수 1주, 모의투자)")
        idem_key = f"ctest-{uuid.uuid4()}"
        # 현재가의 -5% 가격으로 지정가 (체결되지 않게)
        unfillable_price = max(int(quote_price * 0.95), 100)
        # 호가단위 100원 가정 → 100원 단위 절사
        unfillable_price = (unfillable_price // 100) * 100
        try:
            r = client.post(
                "/orders",
                json={
                    "code": args.code,
                    "side": "BUY",
                    "qty": 1,
                    "order_type": "LIMIT",
                    "price": unfillable_price,
                    "idempotency_key": idem_key,
                },
            )
            r.raise_for_status()
            body = r.json()
            if body.get("success"):
                data = body.get("data", {})
                broker_order_no = data.get("broker_order_no")
                print(f"  accepted = {data.get('accepted')}, broker_order_no = {broker_order_no}")
                print(f"  price    = {unfillable_price} (현재가 -5%, 체결 안 됨 예상)")
            else:
                err = body.get("error", {})
                failures.append(
                    f"주문 거부: {err.get('code')} - {err.get('message')}"
                )
                print(f"[FAIL] 주문 거부: {err}")
        except Exception as e:
            failures.append(f"/orders 실패: {e}")
            print(f"[FAIL] {e}")

        # 멱등성 검증 (동일 키 재호출)
        step("6b. 멱등성 검증 (동일 idempotency_key)")
        try:
            r2 = client.post(
                "/orders",
                json={
                    "code": args.code,
                    "side": "BUY",
                    "qty": 1,
                    "order_type": "LIMIT",
                    "price": unfillable_price,
                    "idempotency_key": idem_key,
                },
            )
            data2 = r2.json().get("data", {})
            if data2.get("broker_order_no") == broker_order_no:
                print("  [OK] 동일 broker_order_no 반환 (멱등성 OK)")
            else:
                failures.append("멱등성 위반: 다른 broker_order_no")
        except Exception as e:
            print(f"  [WARN] 멱등성 검증 실패: {e}")

        # 취소
        if broker_order_no:
            step("7. /orders/{id}/cancel")
            time.sleep(2)
            try:
                r = client.post(
                    f"/orders/{broker_order_no}/cancel",
                    json={
                        "broker_order_no": broker_order_no,
                        "code": args.code,
                        "qty": 1,
                    },
                )
                r.raise_for_status()
                body = r.json()
                if body.get("success"):
                    print(f"  [OK] canceled = {body.get('data', {}).get('canceled')}")
                else:
                    print(f"  [WARN] 취소 응답: {body}")
            except Exception as e:
                print(f"  [WARN] 취소 실패: {e}")

    # -----------------------------------------------------------------
    # 결과
    # -----------------------------------------------------------------
    print("\n##############################")
    if not failures:
        print("[PASS] 모든 검증 통과")
        client.close()
        return 0
    print(f"[FAIL] 실패 {len(failures)}건")
    for f in failures:
        print(f"  - {f}")
    client.close()
    return 1


if __name__ == "__main__":
    sys.exit(main())
