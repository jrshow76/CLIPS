# =============================================================================
# TradePilot Backend - 멀티 스테이지 빌드 Dockerfile
# - target: builder (의존성 설치)
# - target: runtime (api/worker/scheduler 공용 이미지)
# 환경변수 SERVICE_ROLE (api|worker|scheduler) 로 분기한다.
# =============================================================================

ARG PYTHON_VERSION=3.11

# -------- builder --------
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# pandas-ta / numpy 등 빌드용 패키지
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# 의존성 정의만 먼저 복사 (캐시 최적화)
COPY pyproject.toml ./
COPY app/__init__.py ./app/

RUN pip install --upgrade pip setuptools wheel && \
    pip install --prefix=/install ".[dev]"

# -------- runtime --------
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/app \
    TZ=Asia/Seoul

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime

# 비루트 유저
RUN groupadd -r app && useradd -r -g app -d ${APP_HOME} -s /sbin/nologin app

WORKDIR ${APP_HOME}

# builder 단계의 설치 결과 복사
COPY --from=builder /install /usr/local

# 애플리케이션 코드
COPY --chown=app:app . ${APP_HOME}

USER app

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://localhost:8000/healthz', timeout=3)" || exit 1

# 기본 entrypoint는 API 서버. docker-compose에서 command 로 override.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
