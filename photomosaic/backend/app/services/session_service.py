"""
세션 관리 서비스
세션별 디렉토리와 이미지 메타데이터를 관리한다.
"""
import os
import shutil
import time
import threading
from typing import Dict, Optional

from app.core.config import settings
from app.models.schemas import ImageInfo


class SessionData:
    """세션 데이터 컨테이너"""

    def __init__(self, session_id: str):
        self.session_id: str = session_id
        self.images: Dict[str, ImageInfo] = {}  # image_id -> ImageInfo
        self.target_image_id: Optional[str] = None
        self.created_at: float = time.time()
        self.updated_at: float = time.time()

    def touch(self):
        """마지막 접근 시간을 갱신한다."""
        self.updated_at = time.time()

    def is_expired(self) -> bool:
        """세션이 TTL을 초과했는지 확인한다."""
        return (time.time() - self.updated_at) > settings.SESSION_TTL_SECONDS

    def get_images_dir(self) -> str:
        """이미지 저장 디렉토리 경로를 반환한다."""
        return os.path.join(settings.BASE_UPLOAD_DIR, self.session_id, "images")

    def get_thumbnails_dir(self) -> str:
        """썸네일 저장 디렉토리 경로를 반환한다."""
        return os.path.join(settings.BASE_UPLOAD_DIR, self.session_id, "thumbnails")

    def get_results_dir(self) -> str:
        """결과 파일 저장 디렉토리 경로를 반환한다."""
        return os.path.join(settings.BASE_UPLOAD_DIR, self.session_id, "results")

    def total_size_bytes(self) -> int:
        """현재 세션의 총 이미지 크기를 계산한다."""
        return sum(img.size_bytes for img in self.images.values())


class SessionService:
    """세션 생명주기 관리 서비스"""

    def __init__(self):
        # 세션 데이터 in-memory 저장소
        self._sessions: Dict[str, SessionData] = {}
        # 스레드 안전성을 위한 락
        self._lock = threading.RLock()

    def get_session(self, session_id: str) -> Optional[SessionData]:
        """세션 ID로 세션 데이터를 조회한다. 존재하지 않으면 None을 반환한다."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is not None:
                session.touch()
            return session

    def create_if_not_exists(self, session_id: str) -> SessionData:
        """
        세션이 없으면 새로 생성하고 디렉토리를 초기화한다.
        이미 존재하면 기존 세션을 반환한다.
        """
        with self._lock:
            if session_id not in self._sessions:
                session = SessionData(session_id)
                self._sessions[session_id] = session
                # 필요한 디렉토리 생성
                os.makedirs(session.get_images_dir(), exist_ok=True)
                os.makedirs(session.get_thumbnails_dir(), exist_ok=True)
                os.makedirs(session.get_results_dir(), exist_ok=True)
            return self._sessions[session_id]

    def delete_session(self, session_id: str) -> bool:
        """
        세션과 관련된 모든 파일 및 메타데이터를 삭제한다.
        삭제 성공 여부를 반환한다.
        """
        with self._lock:
            if session_id not in self._sessions:
                return False

            # 세션 디렉토리 삭제
            session_dir = os.path.join(settings.BASE_UPLOAD_DIR, session_id)
            if os.path.exists(session_dir):
                try:
                    shutil.rmtree(session_dir)
                except OSError as e:
                    # 파일 삭제 실패 시 로그만 남기고 메타데이터는 제거
                    print(f"[경고] 세션 디렉토리 삭제 실패: {session_dir}, 에러: {e}")

            # 메타데이터 제거
            del self._sessions[session_id]
            return True

    def cleanup_expired_sessions(self) -> int:
        """
        TTL이 초과된 세션을 일괄 삭제한다.
        삭제된 세션 수를 반환한다.
        """
        with self._lock:
            expired_ids = [
                sid for sid, session in self._sessions.items()
                if session.is_expired()
            ]

        # 락 외부에서 삭제 수행 (파일 I/O는 락 없이)
        deleted_count = 0
        for session_id in expired_ids:
            if self.delete_session(session_id):
                deleted_count += 1
                print(f"[세션 정리] 만료된 세션 삭제: {session_id}")

        if deleted_count > 0:
            print(f"[세션 정리] 총 {deleted_count}개 세션 삭제 완료")

        return deleted_count

    def get_all_session_ids(self) -> list[str]:
        """현재 활성화된 모든 세션 ID 목록을 반환한다."""
        with self._lock:
            return list(self._sessions.keys())

    def session_count(self) -> int:
        """현재 활성화된 세션 수를 반환한다."""
        with self._lock:
            return len(self._sessions)


# 전역 세션 서비스 인스턴스 (싱글톤)
session_service = SessionService()
