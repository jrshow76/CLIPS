#!/usr/bin/env python3
"""VAPID 키쌍 생성 스크립트.

사용:
    python scripts/generate_vapid_keys.py
    python scripts/generate_vapid_keys.py --output .env.vapid
    python scripts/generate_vapid_keys.py --subject mailto:ops@tradepilot.example.com

생성된 키를 `.env` 의 다음 항목에 채워 넣는다.

    VAPID_PUBLIC_KEY=...
    VAPID_PRIVATE_KEY=...
    VAPID_SUBJECT=mailto:admin@tradepilot.example.com

키는 P-256 ECDSA 키쌍이며, RFC 8292 (VAPID) 에 따라 base64url 인코딩으로 출력한다.

회전 정책:
    - 1년 1회 또는 누출 의심 시 즉시 회전.
    - 회전 시 기존 활성 구독은 일제히 무효화되므로, 사전에 사용자 공지 + 재구독 안내 필요.
    - 운영 절차: docs/43_secrets_management.md 참조.

의존성:
    - cryptography>=42 (이미 backend 의존성에 포함)
"""
from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
except ImportError:  # pragma: no cover
    print(
        "[ERROR] cryptography 패키지가 필요합니다.\n"
        "  pip install cryptography>=42\n",
        file=sys.stderr,
    )
    sys.exit(1)


def _b64url_encode(data: bytes) -> str:
    """base64url 인코딩 (패딩 제거)."""
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def generate_vapid_keypair() -> tuple[str, str]:
    """P-256 ECDSA 키쌍을 생성하고 (public_key_b64url, private_key_b64url) 반환.

    - public_key: 비압축 좌표 (0x04 prefix + X(32B) + Y(32B)) = 65 bytes → base64url
    - private_key: scalar (32B) → base64url
    """
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_numbers = private_key.public_key().public_numbers()

    # 공개키: 비압축 포맷 0x04 || X(32) || Y(32)
    x_bytes = public_numbers.x.to_bytes(32, "big")
    y_bytes = public_numbers.y.to_bytes(32, "big")
    public_uncompressed = b"\x04" + x_bytes + y_bytes
    public_b64 = _b64url_encode(public_uncompressed)

    # 개인키: scalar 32B
    private_value = private_key.private_numbers().private_value
    private_bytes = private_value.to_bytes(32, "big")
    private_b64 = _b64url_encode(private_bytes)

    return public_b64, private_b64


def main() -> int:
    parser = argparse.ArgumentParser(description="TradePilot VAPID 키쌍 생성기")
    parser.add_argument(
        "--subject",
        default="mailto:admin@tradepilot.example.com",
        help="VAPID subject (mailto: 또는 https://)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="키 출력 파일 (.env 포맷). 미지정 시 stdout 출력",
    )
    args = parser.parse_args()

    public_key, private_key = generate_vapid_keypair()

    block = (
        "# ---- TradePilot VAPID 키쌍 ----\n"
        "# 생성: scripts/generate_vapid_keys.py\n"
        "# !! VAPID_PRIVATE_KEY 는 절대 외부 공개 금지 !!\n"
        f"VAPID_PUBLIC_KEY={public_key}\n"
        f"VAPID_PRIVATE_KEY={private_key}\n"
        f"VAPID_SUBJECT={args.subject}\n"
    )

    if args.output:
        args.output.write_text(block, encoding="utf-8")
        print(f"[OK] {args.output} 에 키쌍을 기록했습니다.", file=sys.stderr)
        print(
            "  → .env 의 VAPID_* 항목으로 복사하거나 시크릿 매니저에 업로드하세요.",
            file=sys.stderr,
        )
    else:
        print(block)
        print(
            "[안내] .env 의 VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY / VAPID_SUBJECT 에 복사하세요.\n"
            "       프로덕션 환경은 시크릿 매니저(AWS Secrets Manager, GCP Secret Manager 등) 사용을 권장합니다.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
