"""인증 API 라우터.

`docs/13_api_requirements.md` §1 명세 구현.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.core.response import success_response
from app.schemas.auth import (
    LoginRequest,
    LogoutResponse,
    MeResponse,
    OtpSendRequest,
    OtpSendResponse,
    OtpVerifyRequest,
    OtpVerifyResponse,
    PasswordChangeRequest,
    PasswordResetConfirmIn,
    PasswordResetRequestIn,
    RefreshRequest,
    RefreshResponse,
    SignupRequest,
    SignupResponse,
    TokenPair,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", summary="회원가입", status_code=201)
async def signup(payload: SignupRequest, db: AsyncSession = Depends(get_db)):
    svc = AuthService(db)
    user = await svc.signup(
        email=payload.email, password=payload.password, nickname=payload.nickname
    )
    return success_response(
        SignupResponse(user_id=str(user.public_id), status="REGISTERED"),
        http_status=201,
    )


@router.post("/login", summary="로그인")
async def login(payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    svc = AuthService(db)
    ua = request.headers.get("User-Agent")
    ip = request.client.host if request.client else None
    user, access, refresh, ttl = await svc.login(
        email=payload.email, password=payload.password, user_agent=ua, ip=ip
    )
    return success_response(
        TokenPair(
            access_token=access,
            refresh_token=refresh,
            expires_in=ttl,
        )
    )


@router.post("/refresh", summary="액세스 토큰 갱신")
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    svc = AuthService(db)
    access, ttl = await svc.refresh(payload.refresh_token)
    return success_response(RefreshResponse(access_token=access, expires_in=ttl))


@router.post("/logout", summary="로그아웃")
async def logout(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    svc = AuthService(db)
    await svc.logout(user.id)
    return success_response(LogoutResponse(logged_out=True))


@router.get("/me", summary="내 정보 조회", response_model=None)
async def get_me(user: CurrentUser):
    return success_response(
        MeResponse(
            id=str(user.public_id),
            email=user.email,
            nickname=user.nickname,
            role=user.role,
            trade_mode=user.trade_mode,
            email_verified=user.email_verified,
            phone_verified=user.phone_verified,
            created_at=user.created_at.isoformat(),
        )
    )


@router.post("/otp/send", summary="OTP 발급")
async def otp_send(
    payload: OtpSendRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = AuthService(db)
    otp_id, ttl = await svc.send_otp(
        user_id=user.id,
        purpose=payload.purpose,
        channel=payload.channel,
        phone=payload.phone,
    )
    return success_response(OtpSendResponse(otp_id=otp_id, expires_in=ttl))


@router.post("/otp/verify", summary="OTP 검증")
async def otp_verify(payload: OtpVerifyRequest, db: AsyncSession = Depends(get_db)):
    svc = AuthService(db)
    token = await svc.verify_otp(payload.otp_id, payload.code)
    return success_response(OtpVerifyResponse(otp_token=token, verified=True))


@router.post("/password/change", summary="비밀번호 변경")
async def password_change(
    payload: PasswordChangeRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = AuthService(db)
    await svc.change_password(user.id, payload.current_password, payload.new_password)
    return success_response({"changed": True})


@router.post("/password/reset-request", summary="비밀번호 재설정 요청")
async def password_reset_request(
    payload: PasswordResetRequestIn, db: AsyncSession = Depends(get_db)
):
    svc = AuthService(db)
    await svc.request_password_reset(payload.email)
    # 보안상 항상 성공 응답
    return success_response({"sent": True})


@router.post("/password/reset-confirm", summary="비밀번호 재설정 확인")
async def password_reset_confirm(
    payload: PasswordResetConfirmIn, db: AsyncSession = Depends(get_db)
):
    svc = AuthService(db)
    await svc.confirm_password_reset(payload.token, payload.new_password)
    return success_response({"reset": True})
