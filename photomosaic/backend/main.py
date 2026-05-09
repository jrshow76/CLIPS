"""
포토모자이크 FastAPI 백엔드 애플리케이션 진입점

주요 설정:
- CORS: http://localhost:3000 허용
- Rate Limiting: slowapi (업로드 30/min, 생성 10/min)
- APScheduler: 만료 세션 정리 (1시간마다)
- 업로드 디렉토리 초기화
"""
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api import images, mosaic, sessions
from app.core.config import settings
from app.services.mosaic_service import cleanup_old_jobs
from app.services.session_service import session_service
from app.utils.error_handlers import register_error_handlers

# Rate Limiter 전역 인스턴스 생성
limiter = Limiter(key_func=get_remote_address)

# FastAPI 앱 생성
app = FastAPI(
    title="포토모자이크 API",
    description="이미지를 타일로 조합하여 포토모자이크를 생성하는 RESTful API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Rate Limiter 상태 등록
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS 미들웨어 등록 (프론트엔드 개발 서버 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# 전역 에러 핸들러 등록
register_error_handlers(app)

# API 라우터 등록 (/api/v1 prefix)
app.include_router(images.router, prefix="/api/v1")
app.include_router(mosaic.router, prefix="/api/v1")
app.include_router(sessions.router, prefix="/api/v1")

# APScheduler 인스턴스
scheduler = AsyncIOScheduler()


async def scheduled_cleanup():
    """스케줄 작업: 만료된 세션 및 오래된 작업 상태를 정리한다."""
    session_count = session_service.cleanup_expired_sessions()
    job_count = cleanup_old_jobs(max_age_seconds=7200)
    print(
        f"[스케줄러] 정리 완료 - 세션: {session_count}개, 작업: {job_count}개 삭제"
    )


@app.on_event("startup")
async def startup_event():
    """
    애플리케이션 시작 시 초기화 작업:
    1. 업로드 기본 디렉토리 생성
    2. APScheduler 시작 (1시간마다 만료 세션 정리)
    """
    # 업로드 디렉토리 초기화
    os.makedirs(settings.BASE_UPLOAD_DIR, exist_ok=True)
    print(f"[시작] 업로드 디렉토리 초기화 완료: {settings.BASE_UPLOAD_DIR}")

    # APScheduler 등록 및 시작 (1시간 = 3600초 간격)
    scheduler.add_job(
        scheduled_cleanup,
        trigger="interval",
        hours=1,
        id="session_cleanup",
        replace_existing=True,
    )
    scheduler.start()
    print("[시작] APScheduler 시작 완료 (1시간마다 세션 정리)")
    print(f"[시작] 최대 동시 작업 수: {settings.MAX_CONCURRENT_JOBS}")
    print(f"[시작] 세션 TTL: {settings.SESSION_TTL_SECONDS}초")


@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 스케줄러를 정상 종료한다."""
    scheduler.shutdown(wait=False)
    print("[종료] APScheduler 종료 완료")


@app.get("/", tags=["헬스체크"])
async def root():
    """API 서버 상태 확인 엔드포인트"""
    return {
        "success": True,
        "data": {
            "service": "포토모자이크 API",
            "version": "1.0.0",
            "status": "running",
        },
        "error": None,
    }


@app.get("/health", tags=["헬스체크"])
async def health_check():
    """헬스체크 엔드포인트 (로드밸런서/컨테이너 오케스트레이터용)"""
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "upload_dir": settings.BASE_UPLOAD_DIR,
            "active_sessions": session_service.session_count(),
        },
        "error": None,
    }
