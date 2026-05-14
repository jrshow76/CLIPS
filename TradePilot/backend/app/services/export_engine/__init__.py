"""익스포트 엔진 패키지.

진입점은 :func:`runner.run_export` 한 곳뿐이다. 워커/서비스에서 다음과 같이 호출한다.

    from app.services.export_engine.runner import run_export

    result = await run_export(job_id=job.id)

각 서브모듈:
    * ``config`` - S3/TTL/한도 등 설정 상수
    * ``formats`` - CSV/XLSX writer (한글 헤더 매핑 + 셀 포맷)
    * ``extractors`` - 익스포트 종류별 DataFrame 추출기
    * ``s3_uploader`` - boto3 기반 업로드 + 사전서명 URL
    * ``runner`` - 추출 → 직렬화 → 업로드 오케스트레이션
"""
from __future__ import annotations

from app.services.export_engine.config import ExportConfig, get_export_config

__all__ = ["ExportConfig", "get_export_config"]
