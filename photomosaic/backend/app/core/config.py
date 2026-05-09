"""
애플리케이션 설정 모듈
환경변수를 로드하여 전역 설정값을 제공한다.
"""
import os
from dotenv import load_dotenv

# .env 파일이 존재하면 로드한다
load_dotenv()


class Settings:
    """애플리케이션 전역 설정"""

    # 업로드 파일 기본 저장 경로
    BASE_UPLOAD_DIR: str = os.getenv("BASE_UPLOAD_DIR", "/tmp/mosaic")

    # 세션 만료 시간 (초 단위, 기본 1시간)
    SESSION_TTL_SECONDS: int = int(os.getenv("SESSION_TTL_SECONDS", "3600"))

    # 동시 처리 가능한 최대 작업 수
    MAX_CONCURRENT_JOBS: int = int(os.getenv("MAX_CONCURRENT_JOBS", "4"))

    # 단일 파일 최대 크기 (MB)
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "20"))

    # 세션당 총 업로드 최대 크기 (MB)
    MAX_TOTAL_SIZE_MB: int = int(os.getenv("MAX_TOTAL_SIZE_MB", "500"))

    # 세션당 최대 이미지 수
    MAX_IMAGES_PER_SESSION: int = int(os.getenv("MAX_IMAGES_PER_SESSION", "1000"))

    # 썸네일 크기 (px, 정사각형)
    THUMBNAIL_SIZE: int = int(os.getenv("THUMBNAIL_SIZE", "200"))

    # 작업 타임아웃 (초)
    JOB_TIMEOUT_SECONDS: int = int(os.getenv("JOB_TIMEOUT_SECONDS", "300"))

    # ZIP Bomb 방지: 압축 해제 최대 크기 (바이트, 기본 3GB)
    MAX_UNCOMPRESSED_SIZE_BYTES: int = int(
        os.getenv("MAX_UNCOMPRESSED_SIZE_BYTES", str(3 * 1024 * 1024 * 1024))
    )

    @property
    def MAX_FILE_SIZE_BYTES(self) -> int:
        """단일 파일 최대 크기 (바이트)"""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def MAX_TOTAL_SIZE_BYTES(self) -> int:
        """총 업로드 최대 크기 (바이트)"""
        return self.MAX_TOTAL_SIZE_MB * 1024 * 1024


# 전역 설정 인스턴스
settings = Settings()
