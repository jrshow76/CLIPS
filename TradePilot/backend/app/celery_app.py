"""docker-compose에서 `-A app.celery_app` 참조 호환을 위한 re-export."""
from app.workers.celery_app import celery_app

__all__ = ["celery_app"]
