"""
이미지 처리 서비스
파일 저장, 썸네일 생성, ZIP 처리, 파일 검증을 담당한다.
"""
import io
import os
import uuid
import zipfile
from typing import List, Tuple, Optional

from PIL import Image

from app.core.config import settings
from app.models.schemas import ImageInfo
from app.services.session_service import SessionData

# 허용 이미지 확장자
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# Magic Bytes 시그니처 정의
MAGIC_BYTES = {
    "jpeg": (b"\xff\xd8\xff", 3),
    "png": (b"\x89\x50\x4e\x47", 4),
    "webp_riff": (b"\x52\x49\x46\x46", 4),  # RIFF 헤더
}

# WEBP 식별을 위한 오프셋 8의 마커
WEBP_MARKER = b"\x57\x45\x42\x50"  # "WEBP"


def validate_magic_bytes(data: bytes) -> bool:
    """
    파일의 Magic Bytes를 검사하여 유효한 이미지 포맷인지 확인한다.
    JPEG, PNG, WEBP만 허용한다.
    """
    if len(data) < 12:
        return False

    # JPEG 확인: FF D8 FF
    if data[:3] == MAGIC_BYTES["jpeg"][0]:
        return True

    # PNG 확인: 89 50 4E 47
    if data[:4] == MAGIC_BYTES["png"][0]:
        return True

    # WEBP 확인: RIFF....WEBP
    if data[:4] == MAGIC_BYTES["webp_riff"][0] and data[8:12] == WEBP_MARKER:
        return True

    return False


def get_safe_filename(original_filename: str) -> Tuple[str, str]:
    """
    원본 파일명에서 확장자를 추출하고, UUID 기반의 안전한 저장 파일명을 생성한다.
    반환값: (uuid_filename, extension)
    """
    _, ext = os.path.splitext(original_filename.lower())
    if ext == ".jpg":
        ext = ".jpeg"
    file_id = str(uuid.uuid4())
    return f"{file_id}{ext}", ext


def is_allowed_extension(filename: str) -> bool:
    """파일 확장자가 허용 목록에 있는지 확인한다."""
    _, ext = os.path.splitext(filename.lower())
    if ext == ".jpg":
        ext = ".jpeg"
    return ext in ALLOWED_EXTENSIONS


def create_thumbnail(image: Image.Image, output_path: str) -> None:
    """
    Pillow를 사용하여 200x200 JPEG 썸네일을 생성한다.
    비율을 유지하며 LANCZOS 리샘플링 방식을 사용한다.
    """
    thumbnail_size = (settings.THUMBNAIL_SIZE, settings.THUMBNAIL_SIZE)
    # 원본 이미지를 복사하여 썸네일 생성 (원본 변형 방지)
    img_copy = image.copy()

    # RGBA 또는 P 모드는 RGB로 변환 (JPEG 저장을 위해)
    if img_copy.mode in ("RGBA", "P", "LA"):
        # 흰색 배경에 합성
        background = Image.new("RGB", img_copy.size, (255, 255, 255))
        if img_copy.mode == "P":
            img_copy = img_copy.convert("RGBA")
        if img_copy.mode in ("RGBA", "LA"):
            background.paste(img_copy, mask=img_copy.split()[-1])
        else:
            background.paste(img_copy)
        img_copy = background
    elif img_copy.mode != "RGB":
        img_copy = img_copy.convert("RGB")

    # 썸네일 생성 (비율 유지, 최대 200x200)
    img_copy.thumbnail(thumbnail_size, Image.LANCZOS)

    # JPEG로 저장
    img_copy.save(output_path, format="JPEG", quality=85, optimize=True)


def save_image_file(
    file_data: bytes,
    original_filename: str,
    session: SessionData,
) -> Optional[ImageInfo]:
    """
    이미지 파일을 세션 디렉토리에 저장하고 ImageInfo를 반환한다.
    실패 시 None을 반환한다.

    처리 순서:
    1. 파일 크기 검증
    2. Magic Bytes 검증
    3. UUID 기반 파일명 생성
    4. 이미지 파일 저장
    5. 썸네일 생성
    6. ImageInfo 생성 및 반환
    """
    # 1. 파일 크기 검증
    if len(file_data) > settings.MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"파일 크기 초과: {len(file_data)} bytes (최대 {settings.MAX_FILE_SIZE_MB}MB)"
        )

    # 2. 확장자 검증
    if not is_allowed_extension(original_filename):
        raise ValueError(f"허용되지 않는 파일 형식: {original_filename}")

    # 3. Magic Bytes 검증
    if not validate_magic_bytes(file_data):
        raise ValueError(f"유효하지 않은 이미지 파일: {original_filename}")

    # 4. UUID 기반 파일명 생성
    image_id = str(uuid.uuid4())
    _, ext = os.path.splitext(original_filename.lower())
    if ext == ".jpg":
        ext = ".jpeg"
    stored_filename = f"{image_id}{ext}"

    # 5. 이미지 로드 및 메타데이터 추출
    try:
        image = Image.open(io.BytesIO(file_data))
        image.verify()  # 이미지 무결성 검사
        # verify() 후 재열기 필요 (verify는 파일 포인터를 소진함)
        image = Image.open(io.BytesIO(file_data))
        width, height = image.size
    except Exception as e:
        raise ValueError(f"이미지 파일을 열 수 없습니다: {original_filename}, 원인: {e}")

    # 6. 이미지 파일 저장 (세션 디렉토리 내부)
    images_dir = session.get_images_dir()
    image_path = os.path.join(images_dir, stored_filename)

    # Path Traversal 방지 검증
    real_images_dir = os.path.realpath(images_dir)
    real_image_path = os.path.realpath(image_path)
    if not real_image_path.startswith(real_images_dir):
        raise ValueError("허용되지 않는 파일 경로입니다.")

    with open(image_path, "wb") as f:
        f.write(file_data)

    # 7. 썸네일 생성
    thumbnails_dir = session.get_thumbnails_dir()
    thumbnail_filename = f"{image_id}_thumb.jpg"
    thumbnail_path = os.path.join(thumbnails_dir, thumbnail_filename)

    try:
        create_thumbnail(image, thumbnail_path)
    except Exception as e:
        # 썸네일 생성 실패 시 원본 파일도 삭제
        if os.path.exists(image_path):
            os.remove(image_path)
        raise ValueError(f"썸네일 생성 실패: {e}")

    # 8. ImageInfo 생성
    thumbnail_url = f"/api/v1/images/{image_id}/thumbnail"
    image_info = ImageInfo(
        image_id=image_id,
        filename=original_filename,
        thumbnail_url=thumbnail_url,
        width=width,
        height=height,
        size_bytes=len(file_data),
        is_target=False,
    )

    # 세션에 이미지 메타데이터 등록
    session.images[image_id] = image_info
    session.touch()

    return image_info


def process_zip_file(
    zip_data: bytes,
    session: SessionData,
) -> Tuple[List[ImageInfo], List[dict]]:
    """
    ZIP 파일을 처리한다.

    ZIP Bomb 방지:
    - 압축 해제 전 uncompressed_size 합산
    - 3GB 초과 시 처리 거부

    처리 흐름:
    1. ZIP 파일 유효성 검사
    2. 압축 해제 크기 사전 검증 (ZIP Bomb 방지)
    3. 내부 이미지 파일 재귀 탐색 및 저장

    반환값: (성공 목록, 실패 목록)
    """
    uploaded: List[ImageInfo] = []
    failed: List[dict] = []

    try:
        zip_buffer = io.BytesIO(zip_data)
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            # ZIP Bomb 방지: 압축 전 크기 합산 검증
            total_uncompressed = sum(info.file_size for info in zf.infolist())
            if total_uncompressed > settings.MAX_UNCOMPRESSED_SIZE_BYTES:
                raise ValueError(
                    f"ZIP 압축 해제 크기 초과: "
                    f"{total_uncompressed / (1024**3):.2f}GB "
                    f"(최대 {settings.MAX_UNCOMPRESSED_SIZE_BYTES / (1024**3):.0f}GB)"
                )

            # 이미지 파일 목록 필터링
            image_entries = [
                info for info in zf.infolist()
                if not info.is_dir() and is_allowed_extension(info.filename)
            ]

            if not image_entries:
                raise ValueError("ZIP 파일 내에 유효한 이미지 파일이 없습니다.")

            for entry in image_entries:
                # 세션당 최대 이미지 수 확인
                if len(session.images) >= settings.MAX_IMAGES_PER_SESSION:
                    failed.append({
                        "filename": entry.filename,
                        "error": f"세션 최대 이미지 수 초과 ({settings.MAX_IMAGES_PER_SESSION}개)",
                    })
                    continue

                # 세션 총 크기 확인
                if session.total_size_bytes() + entry.file_size > settings.MAX_TOTAL_SIZE_BYTES:
                    failed.append({
                        "filename": entry.filename,
                        "error": f"세션 최대 저장 용량 초과 ({settings.MAX_TOTAL_SIZE_MB}MB)",
                    })
                    continue

                original_filename = os.path.basename(entry.filename)
                if not original_filename:
                    continue

                try:
                    file_data = zf.read(entry.filename)
                    image_info = save_image_file(file_data, original_filename, session)
                    if image_info:
                        uploaded.append(image_info)
                except ValueError as e:
                    failed.append({"filename": original_filename, "error": str(e)})
                except Exception as e:
                    failed.append({
                        "filename": original_filename,
                        "error": f"처리 중 오류 발생: {str(e)}",
                    })

    except zipfile.BadZipFile:
        raise ValueError("유효하지 않은 ZIP 파일입니다.")

    return uploaded, failed


def get_image_path(image_id: str, session: SessionData) -> Optional[str]:
    """
    이미지 ID로 실제 파일 경로를 반환한다.
    존재하지 않으면 None을 반환한다.
    """
    image_info = session.images.get(image_id)
    if not image_info:
        return None

    images_dir = session.get_images_dir()
    # 확장자를 찾아서 파일 경로 구성
    _, ext = os.path.splitext(image_info.filename.lower())
    if ext == ".jpg":
        ext = ".jpeg"
    stored_filename = f"{image_id}{ext}"
    image_path = os.path.join(images_dir, stored_filename)

    if os.path.exists(image_path):
        return image_path
    return None


def get_thumbnail_path(image_id: str, session: SessionData) -> Optional[str]:
    """
    이미지 ID로 썸네일 파일 경로를 반환한다.
    존재하지 않으면 None을 반환한다.
    """
    if image_id not in session.images:
        return None

    thumbnails_dir = session.get_thumbnails_dir()
    thumbnail_filename = f"{image_id}_thumb.jpg"
    thumbnail_path = os.path.join(thumbnails_dir, thumbnail_filename)

    if os.path.exists(thumbnail_path):
        return thumbnail_path
    return None
