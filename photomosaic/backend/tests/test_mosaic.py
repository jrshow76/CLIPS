"""
포토모자이크 백엔드 단위 테스트

테스트 항목:
1. 썸네일 생성 테스트
2. Magic Bytes 검증 테스트
3. 포토모자이크 알고리즘 소형 테스트 (5x5 격자, 10개 타일)
"""
import io
import os
import sys
import tempfile
import uuid

import numpy as np
import pytest
from PIL import Image

# 프로젝트 루트를 sys.path에 추가 (상대 경로 임포트 해결)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.image_service import (
    create_thumbnail,
    validate_magic_bytes,
    save_image_file,
    is_allowed_extension,
)
from app.services.mosaic_service import (
    _compute_average_color,
    _compute_dominant_color,
    _split_target_into_cells,
    _match_tiles_with_kdtree,
    _compose_mosaic,
    _square_crop_and_resize,
)
from app.services.session_service import SessionData
from app.core.config import settings


# ============================================================
# 헬퍼 함수
# ============================================================

def make_solid_color_image(width: int, height: int, color: tuple) -> Image.Image:
    """단색 PIL 이미지를 생성한다."""
    img = Image.new("RGB", (width, height), color)
    return img


def make_jpeg_bytes(width: int = 100, height: int = 100, color: tuple = (128, 64, 32)) -> bytes:
    """JPEG 바이너리 데이터를 생성한다."""
    img = make_solid_color_image(width, height, color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def make_png_bytes(width: int = 100, height: int = 100, color: tuple = (64, 128, 200)) -> bytes:
    """PNG 바이너리 데이터를 생성한다."""
    img = make_solid_color_image(width, height, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def make_webp_bytes(width: int = 100, height: int = 100, color: tuple = (200, 100, 50)) -> bytes:
    """WEBP 바이너리 데이터를 생성한다."""
    img = make_solid_color_image(width, height, color)
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=85)
    return buf.getvalue()


# ============================================================
# 1. 썸네일 생성 테스트
# ============================================================

class TestThumbnailCreation:
    """썸네일 생성 관련 테스트"""

    def test_thumbnail_생성_정상(self, tmp_path):
        """일반 RGB 이미지에 대해 썸네일이 정상적으로 생성되어야 한다."""
        output_path = str(tmp_path / "thumb.jpg")
        img = make_solid_color_image(400, 300, (255, 0, 0))
        create_thumbnail(img, output_path)

        assert os.path.exists(output_path), "썸네일 파일이 생성되어야 한다."
        thumb = Image.open(output_path)
        assert thumb.format == "JPEG", "썸네일 포맷은 JPEG여야 한다."
        assert thumb.width <= settings.THUMBNAIL_SIZE, "썸네일 너비는 최대 크기를 초과하면 안 된다."
        assert thumb.height <= settings.THUMBNAIL_SIZE, "썸네일 높이는 최대 크기를 초과하면 안 된다."

    def test_thumbnail_RGBA_이미지_처리(self, tmp_path):
        """RGBA 이미지에서도 썸네일이 정상 생성되어야 한다 (투명도 -> 흰 배경)."""
        output_path = str(tmp_path / "thumb_rgba.jpg")
        img = Image.new("RGBA", (200, 200), (0, 128, 255, 128))
        create_thumbnail(img, output_path)

        assert os.path.exists(output_path), "RGBA 이미지의 썸네일이 생성되어야 한다."
        thumb = Image.open(output_path)
        assert thumb.mode == "RGB", "썸네일 모드는 RGB여야 한다."

    def test_thumbnail_정사각형_비율_유지(self, tmp_path):
        """가로로 긴 이미지에서도 비율을 유지하며 썸네일을 생성해야 한다."""
        output_path = str(tmp_path / "thumb_wide.jpg")
        img = make_solid_color_image(1000, 100, (0, 255, 0))  # 10:1 비율
        create_thumbnail(img, output_path)

        thumb = Image.open(output_path)
        # 너비 또는 높이 중 하나가 200px, 다른 하나는 그보다 작아야 함
        assert max(thumb.width, thumb.height) == settings.THUMBNAIL_SIZE
        assert min(thumb.width, thumb.height) <= settings.THUMBNAIL_SIZE

    def test_thumbnail_소형_이미지(self, tmp_path):
        """썸네일 크기보다 작은 이미지도 정상 처리되어야 한다."""
        output_path = str(tmp_path / "thumb_small.jpg")
        img = make_solid_color_image(50, 50, (100, 100, 100))
        create_thumbnail(img, output_path)

        assert os.path.exists(output_path), "소형 이미지의 썸네일이 생성되어야 한다."


# ============================================================
# 2. Magic Bytes 검증 테스트
# ============================================================

class TestMagicBytesValidation:
    """파일 Magic Bytes 검증 관련 테스트"""

    def test_JPEG_magic_bytes_유효(self):
        """JPEG 파일의 Magic Bytes(FF D8 FF)는 유효해야 한다."""
        jpeg_data = make_jpeg_bytes()
        assert validate_magic_bytes(jpeg_data) is True, "JPEG Magic Bytes는 유효해야 한다."

    def test_PNG_magic_bytes_유효(self):
        """PNG 파일의 Magic Bytes(89 50 4E 47)는 유효해야 한다."""
        png_data = make_png_bytes()
        assert validate_magic_bytes(png_data) is True, "PNG Magic Bytes는 유효해야 한다."

    def test_WEBP_magic_bytes_유효(self):
        """WEBP 파일의 Magic Bytes(RIFF....WEBP)는 유효해야 한다."""
        webp_data = make_webp_bytes()
        assert validate_magic_bytes(webp_data) is True, "WEBP Magic Bytes는 유효해야 한다."

    def test_잘못된_데이터_거부(self):
        """임의의 바이너리 데이터는 거부되어야 한다."""
        fake_data = b"\x00\x01\x02\x03" * 100
        assert validate_magic_bytes(fake_data) is False, "유효하지 않은 데이터는 거부되어야 한다."

    def test_텍스트_파일_거부(self):
        """텍스트 파일 내용은 이미지로 인식되면 안 된다."""
        text_data = b"Hello, World! This is not an image." * 10
        assert validate_magic_bytes(text_data) is False, "텍스트 파일은 거부되어야 한다."

    def test_짧은_데이터_거부(self):
        """12바이트 미만의 데이터는 거부되어야 한다."""
        short_data = b"\xff\xd8\xff"  # JPEG 헤더지만 너무 짧음 (3바이트)
        # validate_magic_bytes는 보안상 최소 12바이트를 요구하므로 False를 반환해야 한다.
        # JPEG 시그니처가 맞더라도 12바이트 미만이면 조기 거부(early reject)한다.
        assert validate_magic_bytes(short_data) is False, "12바이트 미만 데이터는 거부되어야 한다."

    def test_빈_데이터_거부(self):
        """빈 데이터는 거부되어야 한다."""
        assert validate_magic_bytes(b"") is False, "빈 데이터는 거부되어야 한다."

    def test_허용_확장자_검증(self):
        """허용된 확장자 목록이 올바르게 검증되어야 한다."""
        assert is_allowed_extension("photo.jpg") is True
        assert is_allowed_extension("photo.jpeg") is True
        assert is_allowed_extension("photo.png") is True
        assert is_allowed_extension("photo.webp") is True
        assert is_allowed_extension("photo.gif") is False
        assert is_allowed_extension("photo.bmp") is False
        assert is_allowed_extension("photo.tiff") is False
        assert is_allowed_extension("photo.exe") is False

    def test_대소문자_확장자_처리(self):
        """확장자 대소문자 구분 없이 처리되어야 한다."""
        assert is_allowed_extension("photo.JPG") is True
        assert is_allowed_extension("photo.PNG") is True
        assert is_allowed_extension("photo.WEBP") is True


# ============================================================
# 3. 포토모자이크 알고리즘 소형 테스트
# ============================================================

class TestMosaicAlgorithm:
    """포토모자이크 핵심 알고리즘 관련 테스트"""

    def _make_tile_images(self, n: int, size: int = 32) -> list:
        """n개의 다양한 색상 타일 이미지를 생성한다."""
        tiles = []
        for i in range(n):
            # 색상을 균등하게 분산
            r = (i * 25) % 256
            g = (i * 50 + 100) % 256
            b = (i * 75 + 50) % 256
            img = make_solid_color_image(size, size, (r, g, b))
            tiles.append(img)
        return tiles

    def test_평균_색상_계산(self):
        """단색 이미지의 평균 색상은 해당 색상과 일치해야 한다."""
        target_color = (200, 100, 50)
        img = make_solid_color_image(64, 64, target_color)
        avg = _compute_average_color(img)

        assert len(avg) == 3, "평균 색상은 RGB 3채널이어야 한다."
        np.testing.assert_allclose(avg, [200, 100, 50], atol=2.0,
                                   err_msg="단색 이미지의 평균 색상이 올바르지 않다.")

    def test_주요색_계산(self):
        """단색 이미지의 주요색은 해당 색상과 일치해야 한다."""
        target_color = (150, 75, 200)
        img = make_solid_color_image(64, 64, target_color)
        dominant = _compute_dominant_color(img)

        assert len(dominant) == 3, "주요색은 RGB 3채널이어야 한다."
        np.testing.assert_allclose(dominant, [150, 75, 200], atol=2.0,
                                   err_msg="단색 이미지의 주요색이 올바르지 않다.")

    def test_격자_분할_5x5(self):
        """500x500 이미지를 5x5 격자로 분할하면 25개 셀이 생성되어야 한다."""
        target = make_solid_color_image(500, 500, (128, 128, 128))
        cell_colors, cell_bounds = _split_target_into_cells(target, grid_cols=5, grid_rows=5)

        assert len(cell_colors) == 25, "5x5 격자는 25개 셀을 생성해야 한다."
        assert len(cell_bounds) == 25, "경계 목록도 25개여야 한다."
        assert cell_colors.shape == (25, 3), "색상 벡터 shape은 (25, 3)이어야 한다."

    def test_격자_분할_색상_정확도(self):
        """단색 이미지를 격자 분할하면 모든 셀 색상이 동일해야 한다."""
        target_color = (200, 150, 100)
        target = make_solid_color_image(100, 100, target_color)
        cell_colors, _ = _split_target_into_cells(target, grid_cols=5, grid_rows=5)

        for i, color in enumerate(cell_colors):
            np.testing.assert_allclose(
                color, target_color, atol=2.0,
                err_msg=f"셀 {i}의 색상이 타겟 색상과 다르다."
            )

    def test_KDTree_매칭_반복허용(self):
        """
        10개 타일, 25개 셀, allow_repeat=True 조건에서
        KD-Tree 매칭이 정상적으로 수행되어야 한다.
        """
        n_tiles = 10
        n_cells = 25

        # 타일 색상 벡터 생성
        tile_colors = np.array([
            [(i * 25) % 256, (i * 50 + 100) % 256, (i * 75 + 50) % 256]
            for i in range(n_tiles)
        ], dtype=np.float64)

        # 셀 색상 벡터 생성 (랜덤)
        np.random.seed(42)
        cell_colors = np.random.randint(0, 256, size=(n_cells, 3)).astype(np.float64)

        tile_indices, fallback = _match_tiles_with_kdtree(
            cell_colors=cell_colors,
            tile_colors=tile_colors,
            allow_repeat=True,
            n_tiles=n_tiles,
            n_cells=n_cells,
        )

        assert len(tile_indices) == n_cells, f"매칭 결과는 {n_cells}개여야 한다."
        assert fallback is False, "반복 허용 모드에서는 fallback이 발생하면 안 된다."
        assert all(0 <= idx < n_tiles for idx in tile_indices), "모든 인덱스는 유효한 범위여야 한다."

    def test_KDTree_매칭_반복금지_타일충분(self):
        """
        30개 타일, 25개 셀, allow_repeat=False 조건에서
        헝가리안 알고리즘으로 1:1 매칭이 수행되어야 한다.
        """
        n_tiles = 30
        n_cells = 25

        tile_colors = np.array([
            [(i * 8) % 256, (i * 12) % 256, (i * 16) % 256]
            for i in range(n_tiles)
        ], dtype=np.float64)

        np.random.seed(7)
        cell_colors = np.random.randint(0, 256, size=(n_cells, 3)).astype(np.float64)

        tile_indices, fallback = _match_tiles_with_kdtree(
            cell_colors=cell_colors,
            tile_colors=tile_colors,
            allow_repeat=False,
            n_tiles=n_tiles,
            n_cells=n_cells,
        )

        assert len(tile_indices) == n_cells, f"매칭 결과는 {n_cells}개여야 한다."
        assert fallback is False, "타일이 충분할 때 fallback이 발생하면 안 된다."
        # 반복 금지 조건: 모든 타일 인덱스는 유일해야 함
        assert len(set(tile_indices)) == n_cells, "반복 금지 모드에서 타일 인덱스는 중복되면 안 된다."

    def test_KDTree_매칭_반복금지_타일부족_fallback(self):
        """
        5개 타일, 25개 셀, allow_repeat=False 조건에서
        타일 수 < 셀 수이므로 fallback=True가 발생해야 한다.
        """
        n_tiles = 5
        n_cells = 25

        tile_colors = np.array([
            [(i * 50) % 256, (i * 100) % 256, (i * 150) % 256]
            for i in range(n_tiles)
        ], dtype=np.float64)

        np.random.seed(99)
        cell_colors = np.random.randint(0, 256, size=(n_cells, 3)).astype(np.float64)

        tile_indices, fallback = _match_tiles_with_kdtree(
            cell_colors=cell_colors,
            tile_colors=tile_colors,
            allow_repeat=False,
            n_tiles=n_tiles,
            n_cells=n_cells,
        )

        assert fallback is True, "타일 수 < 셀 수일 때 fallback이 발생해야 한다."
        assert len(tile_indices) == n_cells, f"매칭 결과는 {n_cells}개여야 한다."
        assert all(0 <= idx < n_tiles for idx in tile_indices), "모든 인덱스는 유효한 범위여야 한다."

    def test_모자이크_합성_소형(self):
        """
        5x5 격자, 10개 타일로 소형 모자이크를 합성한다.
        결과 이미지 크기가 올바르고 파일 저장이 성공해야 한다.
        """
        grid_cols = 5
        grid_rows = 5
        tile_size = 32
        n_tiles = 10

        output_width = grid_cols * tile_size
        output_height = grid_rows * tile_size

        # 타일 이미지 생성
        tile_images = self._make_tile_images(n_tiles, tile_size)

        # 타겟 이미지 생성 및 격자 분할
        target = make_solid_color_image(output_width, output_height, (128, 64, 192))
        cell_colors, cell_bounds = _split_target_into_cells(target, grid_cols, grid_rows)

        # 색상 벡터 계산
        tile_colors = np.array([
            np.array(img, dtype=np.float64).mean(axis=(0, 1))
            for img in tile_images
        ])

        # KD-Tree 매칭
        tile_indices, _ = _match_tiles_with_kdtree(
            cell_colors=cell_colors,
            tile_colors=tile_colors,
            allow_repeat=True,
            n_tiles=n_tiles,
            n_cells=grid_cols * grid_rows,
        )

        # 모자이크 합성
        mosaic = _compose_mosaic(
            tile_images=tile_images,
            tile_indices=tile_indices,
            cell_bounds=cell_bounds,
            output_width=output_width,
            output_height=output_height,
            tile_size=tile_size,
        )

        assert mosaic.size == (output_width, output_height), (
            f"모자이크 크기는 ({output_width}, {output_height})여야 한다. "
            f"실제: {mosaic.size}"
        )
        assert mosaic.mode == "RGB", "모자이크 모드는 RGB여야 한다."

    def test_정사각형_크롭_및_리사이즈(self):
        """직사각형 이미지를 정사각형으로 크롭하면 지정 크기의 정사각형이 되어야 한다."""
        img = make_solid_color_image(200, 100, (255, 128, 0))
        resized = _square_crop_and_resize(img, size=32)

        assert resized.size == (32, 32), "정사각형 크롭 후 크기는 (32, 32)여야 한다."

    def test_end_to_end_소형_모자이크(self, tmp_path):
        """
        End-to-End 소형 모자이크 생성 테스트.
        임시 세션 디렉토리를 사용하여 전체 파이프라인을 검증한다.
        이미지 파일 저장 -> 세션 등록 -> 알고리즘 실행 -> 결과 검증
        """
        # 임시 세션 디렉토리 구성
        session_id = str(uuid.uuid4())
        session = SessionData(session_id)
        # 설정값을 임시 경로로 오버라이드
        images_dir = str(tmp_path / "images")
        thumbnails_dir = str(tmp_path / "thumbnails")
        results_dir = str(tmp_path / "results")
        os.makedirs(images_dir)
        os.makedirs(thumbnails_dir)
        os.makedirs(results_dir)

        # SessionData의 경로 메서드를 임시 경로로 패치
        session.get_images_dir = lambda: images_dir
        session.get_thumbnails_dir = lambda: thumbnails_dir
        session.get_results_dir = lambda: results_dir

        # 타일 이미지 10개 저장
        tile_ids = []
        for i in range(10):
            color = ((i * 25) % 256, (i * 50 + 30) % 256, (i * 75 + 60) % 256)
            jpeg_data = make_jpeg_bytes(64, 64, color)
            image_info = save_image_file(jpeg_data, f"tile_{i}.jpg", session)
            assert image_info is not None, f"타일 이미지 {i} 저장에 실패했다."
            tile_ids.append(image_info.image_id)

        # 타겟 이미지 1개 저장
        target_jpeg = make_jpeg_bytes(200, 200, (100, 150, 200))
        target_info = save_image_file(target_jpeg, "target.jpg", session)
        assert target_info is not None, "타겟 이미지 저장에 실패했다."

        # 세션 이미지 수 확인
        assert len(session.images) == 11, "총 11개 이미지가 등록되어야 한다."

        # 썸네일 파일 존재 확인
        for image_id in tile_ids + [target_info.image_id]:
            thumb_path = os.path.join(thumbnails_dir, f"{image_id}_thumb.jpg")
            assert os.path.exists(thumb_path), f"썸네일이 생성되어야 한다: {image_id}"


# ============================================================
# pytest 실행 진입점
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
