"""
포토모자이크 핵심 알고리즘 서비스

처리 흐름:
1. 타일 이미지 로드 및 평균/주요 색상 계산 (numpy)
2. KD-Tree 구축 (scipy.spatial.cKDTree)
3. 타겟 이미지 격자 분할
4. 각 셀 평균 색상으로 KD-Tree 쿼리 -> 최적 타일 인덱스 반환
5. allow_tile_repeat=False 시 헝가리안 알고리즘 적용
   (타일 수 < 격자 수이면 allow_tile_repeat=True로 fallback)
6. Pillow로 최종 이미지 합성
7. blend_ratio > 0 이면 원본 이미지와 블렌딩
8. 결과 저장 및 job 상태 업데이트
"""
import asyncio
import io
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, List, Optional, Tuple, Any

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

from app.core.config import settings
from app.models.schemas import MosaicOptions
from app.services.session_service import session_service

# CPU 바운드 작업용 스레드풀 (max_workers는 설정값 기반)
_executor = ThreadPoolExecutor(max_workers=settings.MAX_CONCURRENT_JOBS)

# 작업 상태 저장소 (in-memory)
jobs: Dict[str, Dict[str, Any]] = {}

# 현재 실행 중인 작업 수 추적
_running_jobs_count = 0
_jobs_lock = asyncio.Lock()


def _get_elapsed(start_time: float) -> float:
    """경과 시간을 초 단위로 반환한다."""
    return round(time.time() - start_time, 2)


def _update_job(
    job_id: str,
    status: Optional[str] = None,
    progress: Optional[int] = None,
    step: Optional[str] = None,
    step_message: Optional[str] = None,
    result_path: Optional[str] = None,
    error: Optional[str] = None,
    allow_tile_repeat_fallback: Optional[bool] = None,
) -> None:
    """작업 상태를 업데이트한다. None인 필드는 변경하지 않는다."""
    if job_id not in jobs:
        return
    job = jobs[job_id]
    if status is not None:
        job["status"] = status
    if progress is not None:
        job["progress"] = progress
    if step is not None:
        job["step"] = step
    if step_message is not None:
        job["step_message"] = step_message
    if result_path is not None:
        job["result_path"] = result_path
    if error is not None:
        job["error"] = error
    if allow_tile_repeat_fallback is not None:
        job["allow_tile_repeat_fallback"] = allow_tile_repeat_fallback


def _compute_average_color(image: Image.Image, size: int = 32) -> np.ndarray:
    """
    이미지를 지정된 크기로 리사이즈한 후 평균 RGB 색상을 계산한다.
    반환값: shape=(3,) float64 numpy 배열 (R, G, B)
    """
    resized = image.resize((size, size), Image.LANCZOS)
    rgb = resized.convert("RGB")
    arr = np.array(rgb, dtype=np.float64)
    return arr.mean(axis=(0, 1))  # shape=(3,)


def _compute_dominant_color(image: Image.Image, size: int = 32) -> np.ndarray:
    """
    이미지의 주요색(최빈 색상 클러스터 중심)을 계산한다.
    단순 구현: 리사이즈 후 중앙 25% 영역의 평균 색상을 주요색으로 사용한다.
    반환값: shape=(3,) float64 numpy 배열 (R, G, B)
    """
    resized = image.resize((size, size), Image.LANCZOS)
    rgb = resized.convert("RGB")
    arr = np.array(rgb, dtype=np.float64)
    # 중앙 50% 영역 (25%~75%)
    quarter = size // 4
    center = arr[quarter: size - quarter, quarter: size - quarter]
    if center.size == 0:
        return arr.mean(axis=(0, 1))
    return center.mean(axis=(0, 1))


def _load_tile_images(
    tile_paths: List[str],
    tile_size: int,
    color_method: str,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Tuple[np.ndarray, List[Image.Image]]:
    """
    타일 이미지 파일 목록을 로드하고 색상 벡터를 계산한다.

    Args:
        tile_paths: 타일 이미지 파일 경로 목록
        tile_size: 타일 크기 (px)
        color_method: 색상 계산 방식 ("average" | "dominant")
        progress_callback: 진행 상태 콜백 (progress_pct, message)

    Returns:
        (color_vectors, tile_images)
        - color_vectors: shape=(N, 3) 색상 벡터 배열
        - tile_images: 리사이즈된 타일 이미지 목록
    """
    color_vectors = []
    tile_images = []
    total = len(tile_paths)

    for idx, path in enumerate(tile_paths):
        try:
            img = Image.open(path).convert("RGB")
            # 타일 크기로 리사이즈 (정사각형 crop 후 리사이즈)
            img_resized = _square_crop_and_resize(img, tile_size)
            tile_images.append(img_resized)

            # 색상 벡터 계산
            if color_method == "dominant":
                color = _compute_dominant_color(img_resized, size=tile_size)
            else:
                color = _compute_average_color(img_resized, size=tile_size)
            color_vectors.append(color)

        except Exception as e:
            print(f"[경고] 타일 이미지 로드 실패: {path}, 원인: {e}")
            continue

        # 진행 상태 업데이트 (10개 단위)
        if progress_callback and (idx + 1) % max(1, total // 10) == 0:
            pct = int((idx + 1) / total * 20)  # 전체 진행의 0~20%
            progress_callback(pct, f"타일 분석 중... ({idx + 1}/{total})")

    if not color_vectors:
        raise ValueError("로드 가능한 타일 이미지가 없습니다.")

    return np.array(color_vectors, dtype=np.float64), tile_images


def _square_crop_and_resize(image: Image.Image, size: int) -> Image.Image:
    """
    이미지를 정사각형으로 중앙 크롭한 후 지정 크기로 리사이즈한다.
    """
    w, h = image.size
    min_dim = min(w, h)
    left = (w - min_dim) // 2
    top = (h - min_dim) // 2
    cropped = image.crop((left, top, left + min_dim, top + min_dim))
    return cropped.resize((size, size), Image.LANCZOS)


def _split_target_into_cells(
    target: Image.Image,
    grid_cols: int,
    grid_rows: int,
) -> Tuple[np.ndarray, List[Tuple[int, int, int, int]]]:
    """
    타겟 이미지를 격자로 분할하고 각 셀의 평균 색상을 계산한다.

    Args:
        target: 타겟 이미지
        grid_cols: 가로 격자 수
        grid_rows: 세로 격자 수

    Returns:
        (cell_colors, cell_bounds)
        - cell_colors: shape=(grid_rows*grid_cols, 3) 각 셀의 평균 색상
        - cell_bounds: [(x1, y1, x2, y2), ...] 각 셀의 픽셀 경계
    """
    w, h = target.size
    target_arr = np.array(target.convert("RGB"), dtype=np.float64)

    cell_colors = []
    cell_bounds = []

    cell_w = w / grid_cols
    cell_h = h / grid_rows

    for row in range(grid_rows):
        for col in range(grid_cols):
            x1 = int(col * cell_w)
            y1 = int(row * cell_h)
            x2 = int((col + 1) * cell_w)
            y2 = int((row + 1) * cell_h)

            # 경계를 이미지 크기 내로 클램프
            x2 = min(x2, w)
            y2 = min(y2, h)

            # 셀 영역 평균 색상 계산
            cell_region = target_arr[y1:y2, x1:x2]
            if cell_region.size > 0:
                avg_color = cell_region.mean(axis=(0, 1))
            else:
                avg_color = np.array([128.0, 128.0, 128.0])

            cell_colors.append(avg_color)
            cell_bounds.append((x1, y1, x2, y2))

    return np.array(cell_colors, dtype=np.float64), cell_bounds


def _match_tiles_with_kdtree(
    cell_colors: np.ndarray,
    tile_colors: np.ndarray,
    allow_repeat: bool,
    n_tiles: int,
    n_cells: int,
) -> Tuple[List[int], bool]:
    """
    KD-Tree를 이용하여 각 셀에 최적 타일을 매칭한다.

    allow_repeat=False 이고 타일 수 >= 격자 수인 경우:
    -> scipy.optimize.linear_sum_assignment(헝가리안 알고리즘)로 최적 매칭

    타일 수 < 격자 수인 경우:
    -> allow_tile_repeat=True로 자동 fallback

    Returns:
        (tile_indices, fallback_applied)
        - tile_indices: 각 셀에 대응하는 타일 인덱스 목록
        - fallback_applied: fallback이 적용됐으면 True
    """
    fallback_applied = False

    # KD-Tree 구축 (RGB 3차원 공간)
    tree = cKDTree(tile_colors)

    if not allow_repeat and n_tiles >= n_cells:
        # 헝가리안 알고리즘: 타일 수 >= 격자 수인 경우 1:1 최적 매칭
        # 비용 행렬: 각 셀과 타일 간의 유클리드 거리
        from scipy.optimize import linear_sum_assignment

        # 비용 행렬 계산 (셀 수 x 타일 수)
        # 메모리 절약을 위해 float32 사용
        cost_matrix = np.zeros((n_cells, n_tiles), dtype=np.float32)
        for i, cell_color in enumerate(cell_colors):
            diff = tile_colors - cell_color
            cost_matrix[i] = np.sqrt((diff ** 2).sum(axis=1))

        # 헝가리안 알고리즘 적용 (최소 비용 매칭)
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        tile_indices = list(col_ind)

    elif not allow_repeat and n_tiles < n_cells:
        # 타일 수가 격자 수보다 적으므로 repeat 모드로 fallback
        print(
            f"[경고] 타일 수({n_tiles})가 격자 수({n_cells})보다 적어 "
            "allow_tile_repeat=True로 자동 전환합니다."
        )
        fallback_applied = True
        _, indices = tree.query(cell_colors)
        tile_indices = indices.tolist()

    else:
        # allow_repeat=True: KD-Tree 최근접 이웃 검색으로 최적 타일 반환
        _, indices = tree.query(cell_colors)
        tile_indices = indices.tolist()

    return tile_indices, fallback_applied


def _compose_mosaic(
    tile_images: List[Image.Image],
    tile_indices: List[int],
    output_width: int,
    output_height: int,
    tile_size: int,
    grid_cols: int,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Image.Image:
    """
    타일 이미지를 합성하여 최종 모자이크 이미지를 생성한다.

    paste 위치는 출력 캔버스 기준(col × tile_size, row × tile_size)으로 계산한다.
    cell_bounds(타겟 이미지 좌표계)를 그대로 사용하면 캔버스 크기와 달라 검정 공백이 생긴다.
    """
    mosaic = Image.new("RGB", (output_width, output_height))
    total = len(tile_indices)

    for i, tile_idx in enumerate(tile_indices):
        row = i // grid_cols
        col = i % grid_cols
        x = col * tile_size
        y = row * tile_size

        mosaic.paste(tile_images[tile_idx], (x, y))

        if progress_callback and (i + 1) % max(1, total // 20) == 0:
            pct = 60 + int((i + 1) / total * 30)
            progress_callback(pct, f"모자이크 합성 중... ({i + 1}/{total})")

    return mosaic


def _run_mosaic_sync(
    job_id: str,
    session_id: str,
    target_image_id: str,
    options: MosaicOptions,
) -> None:
    """
    포토모자이크 생성 핵심 로직 (동기 함수, 스레드풀에서 실행).

    Args:
        job_id: 작업 ID
        session_id: 세션 ID
        target_image_id: 타겟 이미지 ID
        options: 모자이크 생성 옵션
    """
    global _running_jobs_count

    start_time = jobs[job_id]["start_time"]

    def progress_callback(pct: int, message: str) -> None:
        """진행 상태 업데이트 콜백"""
        _update_job(job_id, progress=pct, step_message=message)

    try:
        # 작업 상태를 running으로 변경
        _update_job(
            job_id,
            status="running",
            step="LOADING",
            step_message="세션 및 이미지 로드 중...",
            progress=1,
        )

        # 1. 세션 및 이미지 경로 조회
        session = session_service.get_session(session_id)
        if session is None:
            raise ValueError(f"세션을 찾을 수 없습니다: {session_id}")

        target_info = session.images.get(target_image_id)
        if target_info is None:
            raise ValueError(f"타겟 이미지를 찾을 수 없습니다: {target_image_id}")

        # 타일 이미지: 타겟 이미지를 제외한 모든 이미지
        tile_image_infos = [
            info for img_id, info in session.images.items()
            if img_id != target_image_id
        ]

        if not tile_image_infos:
            raise ValueError("타일로 사용할 이미지가 없습니다. 타겟 이미지 외에 최소 1개 이상의 이미지가 필요합니다.")

        images_dir = session.get_images_dir()

        # 타겟 이미지 경로 구성
        _, target_ext = os.path.splitext(target_info.filename.lower())
        if target_ext == ".jpg":
            target_ext = ".jpeg"
        target_path = os.path.join(images_dir, f"{target_image_id}{target_ext}")

        if not os.path.exists(target_path):
            raise ValueError(f"타겟 이미지 파일이 존재하지 않습니다: {target_path}")

        # 타일 이미지 경로 목록 구성
        tile_paths = []
        for info in tile_image_infos:
            _, ext = os.path.splitext(info.filename.lower())
            if ext == ".jpg":
                ext = ".jpeg"
            tile_path = os.path.join(images_dir, f"{info.image_id}{ext}")
            if os.path.exists(tile_path):
                tile_paths.append(tile_path)

        if not tile_paths:
            raise ValueError("유효한 타일 이미지 파일이 없습니다.")

        _update_job(job_id, step="LOADING", step_message="타겟 이미지 로드 중...", progress=5)

        # 타임아웃 검사 함수
        def check_timeout():
            elapsed = time.time() - start_time
            if elapsed > settings.JOB_TIMEOUT_SECONDS:
                raise TimeoutError(
                    f"작업 타임아웃: {settings.JOB_TIMEOUT_SECONDS}초 초과"
                )

        # 2. 타겟 이미지 로드
        check_timeout()
        target_image = Image.open(target_path).convert("RGB")
        target_w, target_h = target_image.size

        # 3. 격자 분할 계산
        grid_cols = options.grid_division
        # 세로 격자 수는 가로/세로 비율에 따라 자동 계산
        grid_rows = max(1, round(grid_cols * (target_h / target_w)))

        # 출력 이미지 크기: 타일 크기 x 격자 수
        output_width = grid_cols * options.tile_size
        output_height = grid_rows * options.tile_size

        _update_job(
            job_id,
            step="ANALYZING",
            step_message=f"타일 이미지 분석 중... (0/{len(tile_paths)})",
            progress=10,
        )

        # 4. 타일 이미지 로드 및 색상 벡터 계산
        check_timeout()
        tile_color_vectors, tile_images = _load_tile_images(
            tile_paths=tile_paths,
            tile_size=options.tile_size,
            color_method=options.color_match_method,
            progress_callback=progress_callback,
        )

        n_tiles = len(tile_images)
        _update_job(
            job_id,
            step="ANALYZING",
            step_message=f"KD-Tree 구축 중... ({n_tiles}개 타일)",
            progress=25,
        )

        # 5. 타겟 이미지 격자 분할
        check_timeout()
        _update_job(
            job_id,
            step="PROCESSING",
            step_message="타겟 이미지 격자 분할 중...",
            progress=30,
        )

        cell_colors, cell_bounds = _split_target_into_cells(
            target=target_image,
            grid_cols=grid_cols,
            grid_rows=grid_rows,
        )
        n_cells = len(cell_bounds)

        _update_job(
            job_id,
            step="PROCESSING",
            step_message=f"색상 매칭 중... ({n_cells}개 셀, {n_tiles}개 타일)",
            progress=40,
        )

        # 6. KD-Tree 기반 색상 매칭
        check_timeout()
        tile_indices, fallback_applied = _match_tiles_with_kdtree(
            cell_colors=cell_colors,
            tile_colors=tile_color_vectors,
            allow_repeat=options.allow_tile_repeat,
            n_tiles=n_tiles,
            n_cells=n_cells,
        )

        if fallback_applied:
            _update_job(job_id, allow_tile_repeat_fallback=True)

        _update_job(
            job_id,
            step="COMPOSING",
            step_message="모자이크 이미지 합성 중...",
            progress=60,
        )

        # 7. 모자이크 이미지 합성
        check_timeout()
        mosaic_image = _compose_mosaic(
            tile_images=tile_images,
            tile_indices=tile_indices,
            output_width=output_width,
            output_height=output_height,
            tile_size=options.tile_size,
            grid_cols=grid_cols,
            progress_callback=progress_callback,
        )

        _update_job(job_id, step="BLENDING", step_message="블렌딩 처리 중...", progress=90)

        # 8. 원본 이미지 블렌딩 (blend_ratio > 0인 경우)
        check_timeout()
        if options.blend_ratio > 0.0:
            target_resized = target_image.resize(
                (output_width, output_height), Image.LANCZOS
            )
            mosaic_image = Image.blend(mosaic_image, target_resized, options.blend_ratio)

        _update_job(job_id, step="SAVING", step_message="결과 파일 저장 중...", progress=95)

        # 9. 결과 파일 저장
        check_timeout()
        results_dir = session.get_results_dir()
        result_filename = f"{job_id}.{options.output_format}"
        result_path = os.path.join(results_dir, result_filename)

        save_kwargs: dict = {}
        fmt = options.output_format.upper()
        if fmt == "PNG":
            save_kwargs["format"] = "PNG"
            save_kwargs["optimize"] = True
        elif fmt == "JPEG":
            save_kwargs["format"] = "JPEG"
            save_kwargs["quality"] = options.output_quality
            save_kwargs["optimize"] = True
        elif fmt == "WEBP":
            save_kwargs["format"] = "WEBP"
            save_kwargs["quality"] = options.output_quality

        mosaic_image.save(result_path, **save_kwargs)

        # 10. 작업 완료 상태 업데이트
        result_url = f"/api/v1/mosaic/jobs/{job_id}/result"
        _update_job(
            job_id,
            status="completed",
            progress=100,
            step="DONE",
            step_message="모자이크 생성 완료",
            result_path=result_path,
        )
        jobs[job_id]["result_url"] = result_url

        elapsed = _get_elapsed(start_time)
        print(f"[모자이크] 작업 완료: {job_id}, 소요시간: {elapsed}초")

    except TimeoutError as e:
        _update_job(
            job_id,
            status="failed",
            step="ERROR",
            step_message="작업 타임아웃",
            error=str(e),
        )
        print(f"[모자이크] 작업 타임아웃: {job_id}, 원인: {e}")

    except Exception as e:
        _update_job(
            job_id,
            status="failed",
            step="ERROR",
            step_message=f"오류 발생: {str(e)}",
            error=str(e),
        )
        print(f"[모자이크] 작업 실패: {job_id}, 원인: {e}")

    finally:
        global _running_jobs_count
        _running_jobs_count = max(0, _running_jobs_count - 1)


async def generate_mosaic(
    session_id: str,
    target_image_id: str,
    options: MosaicOptions,
) -> str:
    """
    포토모자이크 생성 작업을 비동기로 시작한다.

    동시 실행 작업 수를 MAX_CONCURRENT_JOBS로 제한한다.
    세션당 1개 작업만 허용한다.

    Returns:
        job_id (str): 생성된 작업 ID
    """
    global _running_jobs_count

    # 세션당 실행 중인 작업이 있는지 확인
    for jid, job_data in jobs.items():
        if (
            job_data.get("session_id") == session_id
            and job_data.get("status") in ("pending", "running")
        ):
            raise ValueError(
                f"세션에 이미 진행 중인 작업이 있습니다: {jid}. "
                "기존 작업이 완료된 후 새 작업을 시작하세요."
            )

    # 전체 동시 작업 수 제한 확인
    if _running_jobs_count >= settings.MAX_CONCURRENT_JOBS:
        raise ValueError(
            f"최대 동시 작업 수({settings.MAX_CONCURRENT_JOBS})에 도달했습니다. "
            "잠시 후 다시 시도하세요."
        )

    # 작업 ID 생성 및 초기 상태 등록
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "step": "PENDING",
        "step_message": "작업 대기 중...",
        "start_time": time.time(),
        "result_path": None,
        "result_url": None,
        "error": None,
        "session_id": session_id,
        "allow_tile_repeat_fallback": False,
    }
    _running_jobs_count += 1

    # CPU 바운드 작업을 스레드풀에서 비동기 실행
    loop = asyncio.get_event_loop()
    loop.run_in_executor(
        _executor,
        _run_mosaic_sync,
        job_id,
        session_id,
        target_image_id,
        options,
    )

    return job_id


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """작업 ID로 현재 상태를 조회한다. 존재하지 않으면 None을 반환한다."""
    return jobs.get(job_id)


def cancel_job(job_id: str) -> bool:
    """
    작업을 취소한다.
    이미 완료/실패 상태이거나 존재하지 않으면 False를 반환한다.

    주의: 스레드풀에서 실행 중인 작업은 즉시 중단되지 않고,
    다음 타임아웃 체크 시점에 감지되도록 상태만 변경한다.
    """
    global _running_jobs_count

    job = jobs.get(job_id)
    if job is None:
        return False

    if job["status"] in ("completed", "failed", "cancelled"):
        return False

    _update_job(
        job_id,
        status="cancelled",
        step="CANCELLED",
        step_message="사용자에 의해 취소됨",
    )
    _running_jobs_count = max(0, _running_jobs_count - 1)
    return True


def get_result_path(job_id: str) -> Optional[str]:
    """완료된 작업의 결과 파일 경로를 반환한다."""
    job = jobs.get(job_id)
    if job is None or job["status"] != "completed":
        return None
    return job.get("result_path")


def cleanup_old_jobs(max_age_seconds: int = 7200) -> int:
    """
    오래된 완료/실패/취소 작업 상태를 메모리에서 제거한다.
    max_age_seconds(기본 2시간)이 지난 작업을 정리한다.
    제거된 작업 수를 반환한다.
    """
    now = time.time()
    to_delete = []
    for jid, job in jobs.items():
        if job["status"] in ("completed", "failed", "cancelled"):
            age = now - job["start_time"]
            if age > max_age_seconds:
                to_delete.append(jid)

    for jid in to_delete:
        del jobs[jid]

    if to_delete:
        print(f"[작업 정리] {len(to_delete)}개 오래된 작업 상태 제거")

    return len(to_delete)
