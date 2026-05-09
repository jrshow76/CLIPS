"""
Pydantic v2 스키마 모델 정의
API 요청/응답 데이터 구조를 정의한다.
"""
from __future__ import annotations

from typing import Generic, List, Optional, TypeVar, Any, Dict
from pydantic import BaseModel, Field, field_validator

# 제네릭 타입 변수
T = TypeVar("T")


class ImageInfo(BaseModel):
    """이미지 메타데이터 모델"""

    image_id: str = Field(..., description="이미지 고유 ID (UUID)")
    filename: str = Field(..., description="원본 파일명")
    thumbnail_url: str = Field(..., description="썸네일 URL 경로")
    width: int = Field(..., description="이미지 너비 (px)")
    height: int = Field(..., description="이미지 높이 (px)")
    size_bytes: int = Field(..., description="파일 크기 (바이트)")
    is_target: bool = Field(False, description="타겟 이미지 여부")


class UploadResponse(BaseModel):
    """이미지 업로드 응답 모델"""

    uploaded: List[ImageInfo] = Field(default_factory=list, description="업로드 성공 이미지 목록")
    failed: List[Dict[str, Any]] = Field(default_factory=list, description="업로드 실패 항목 목록")
    total_count: int = Field(..., description="현재 세션 전체 이미지 수")


class MosaicOptions(BaseModel):
    """모자이크 생성 옵션 모델"""

    # 격자 분할 수 (가로 기준, 세로는 비율에 맞게 자동 계산)
    grid_division: int = Field(50, ge=5, le=200, description="격자 분할 수 (5~200)")

    # 타일 크기 (px)
    tile_size: int = Field(32, ge=8, le=128, description="타일 크기 (8~128 px)")

    # 색상 매칭 방식: average(평균), dominant(주요색)
    color_match_method: str = Field("average", description="색상 매칭 방식 (average | dominant)")

    # 타일 반복 허용 여부
    allow_tile_repeat: bool = Field(True, description="타일 반복 허용 여부")

    # 원본 이미지 블렌딩 비율 (0.0 = 순수 모자이크, 1.0 = 원본)
    blend_ratio: float = Field(0.0, ge=0.0, le=1.0, description="원본 블렌딩 비율 (0.0~1.0)")

    # 출력 포맷
    output_format: str = Field("png", description="출력 포맷 (png | jpeg | webp)")

    # 출력 품질 (JPEG/WEBP 전용)
    output_quality: int = Field(90, ge=1, le=100, description="출력 품질 (1~100, JPEG/WEBP 전용)")

    @field_validator("color_match_method")
    @classmethod
    def validate_color_match_method(cls, v: str) -> str:
        allowed = {"average", "dominant"}
        if v not in allowed:
            raise ValueError(f"color_match_method는 {allowed} 중 하나여야 합니다.")
        return v

    @field_validator("output_format")
    @classmethod
    def validate_output_format(cls, v: str) -> str:
        allowed = {"png", "jpeg", "webp"}
        if v not in allowed:
            raise ValueError(f"output_format은 {allowed} 중 하나여야 합니다.")
        return v


class GenerateRequest(BaseModel):
    """모자이크 생성 요청 모델"""

    session_id: str = Field(..., description="세션 ID")
    target_image_id: str = Field(..., description="타겟 이미지 ID")
    options: MosaicOptions = Field(default_factory=MosaicOptions, description="모자이크 생성 옵션")


class JobStatus(BaseModel):
    """작업 진행 상태 모델"""

    job_id: str = Field(..., description="작업 ID (UUID)")
    status: str = Field(
        ..., description="작업 상태 (pending | running | completed | failed | cancelled)"
    )
    progress: int = Field(0, ge=0, le=100, description="진행률 (0~100)")
    step: str = Field("", description="현재 단계 코드")
    step_message: str = Field("", description="현재 단계 설명 메시지")
    elapsed_seconds: float = Field(0.0, description="경과 시간 (초)")
    result_url: Optional[str] = Field(None, description="결과 파일 다운로드 URL")
    warning: Optional[str] = Field(None, description="경고 메시지 (예: 타일 반복 fallback)")


class ErrorDetail(BaseModel):
    """에러 상세 정보 모델"""

    code: str = Field(..., description="에러 코드")
    message: str = Field(..., description="에러 메시지")


class CommonResponse(BaseModel, Generic[T]):
    """공통 응답 래퍼 모델"""

    success: bool = Field(..., description="성공 여부")
    data: Optional[T] = Field(None, description="응답 데이터")
    error: Optional[ErrorDetail] = Field(None, description="에러 정보")

    @classmethod
    def ok(cls, data: T) -> "CommonResponse[T]":
        """성공 응답 생성 헬퍼"""
        return cls(success=True, data=data, error=None)

    @classmethod
    def fail(cls, code: str, message: str) -> "CommonResponse[None]":
        """실패 응답 생성 헬퍼"""
        return cls(success=False, data=None, error=ErrorDetail(code=code, message=message))


class ImageListResponse(BaseModel):
    """이미지 목록 응답 모델 (페이지네이션 포함)"""

    items: List[ImageInfo] = Field(..., description="이미지 목록")
    total: int = Field(..., description="전체 이미지 수")
    page: int = Field(..., description="현재 페이지")
    page_size: int = Field(..., description="페이지당 항목 수")
    total_pages: int = Field(..., description="전체 페이지 수")
