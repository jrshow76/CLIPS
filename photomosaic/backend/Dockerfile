FROM python:3.11-slim

WORKDIR /app

# 의존성 파일만 먼저 복사하여 레이어 캐싱 최적화
COPY requirements.txt .

# 패키지 설치 (캐시 없이, 빌드 최소화)
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 소스 복사
COPY . .

# 업로드 디렉토리 사전 생성 (컨테이너 내부)
RUN mkdir -p /tmp/mosaic

EXPOSE 8000

# uvicorn으로 실행 (0.0.0.0 바인딩으로 외부 접근 허용)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
