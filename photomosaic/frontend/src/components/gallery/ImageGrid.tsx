import { memo, useCallback, useMemo, useState } from 'react';
import { useAppStore } from '../../store';
import { setTargetImageApi, buildThumbnailUrl } from '../../utils/api';
import type { ImageInfo } from '../../types';
import styles from './ImageGrid.module.css';

// 썸네일 크기(px) - CSS와 일치해야 함
const THUMBNAIL_SIZE = 160;
// 한 번에 렌더링할 이미지 수 (가상화 대신 점진적 로드)
const PAGE_SIZE = 200;

interface ThumbnailProps {
  image: ImageInfo;
  isSelected: boolean;
  sessionId: string;
  onSelect: (imageId: string) => void;
}

// 개별 썸네일 컴포넌트 (메모이제이션으로 불필요한 재렌더링 방지)
const Thumbnail = ({ image, isSelected, sessionId, onSelect }: ThumbnailProps) => {
  const [imgError, setImgError] = useState(false);

  const handleClick = useCallback(() => {
    onSelect(image.image_id);
  }, [image.image_id, onSelect]);

  // 썸네일 URL에 session_id 쿼리 파라미터 추가 (헤더 전송 불가한 img 태그 대응)
  const thumbnailSrc = buildThumbnailUrl(image.thumbnail_url, sessionId);

  return (
    <div
      className={`${styles.thumbnail} ${isSelected ? styles.selected : ''}`}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') handleClick();
      }}
      aria-label={`${image.filename}${isSelected ? ' (타겟으로 선택됨)' : ''}`}
      aria-pressed={isSelected}
    >
      {/* 이미지 */}
      {imgError ? (
        <div className={styles.imgError}>이미지 없음</div>
      ) : (
        <img
          src={thumbnailSrc}
          alt={image.filename}
          className={styles.img}
          loading="lazy"
          width={THUMBNAIL_SIZE}
          height={THUMBNAIL_SIZE}
          onError={() => setImgError(true)}
        />
      )}

      {/* 타겟 선택 배지 */}
      {isSelected && (
        <div className={styles.selectedBadge} aria-hidden="true">
          ★ 타겟
        </div>
      )}

      {/* 파일명 툴팁 (호버 시 표시) */}
      <div className={styles.tooltip}>{image.filename}</div>
    </div>
  );
};

// React.memo로 메모이제이션하여 부모 재렌더링 시 불필요한 썸네일 재렌더링 방지
const MemoThumbnail = memo(Thumbnail);

export function ImageGrid() {
  const images = useAppStore((state) => state.images);
  const targetImageId = useAppStore((state) => state.targetImageId);
  const sessionId = useAppStore((state) => state.sessionId);
  const setTargetImage = useAppStore((state) => state.setTargetImage);
  const addToast = useAppStore((state) => state.addToast);

  // 현재 표시 중인 이미지 수 (점진적 로드)
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  // 보이는 이미지 목록
  const visibleImages = useMemo(
    () => images.slice(0, visibleCount),
    [images, visibleCount]
  );

  const hasMore = visibleCount < images.length;

  // 타겟 이미지 선택 핸들러
  const handleSelect = useCallback(
    async (imageId: string) => {
      // 이미 선택된 이미지 클릭 시 선택 해제 없이 그대로 유지
      if (imageId === targetImageId) return;

      try {
        // 로컬 상태 즉시 업데이트 (낙관적 업데이트)
        setTargetImage(imageId);
        // 서버에 타겟 지정 요청
        await setTargetImageApi(imageId, sessionId);
      } catch (err) {
        const message = err instanceof Error ? err.message : '타겟 이미지 설정 중 오류가 발생했습니다.';
        addToast('error', message);
      }
    },
    [targetImageId, setTargetImage, sessionId, addToast]
  );

  // 더 보기 클릭
  const handleLoadMore = useCallback(() => {
    setVisibleCount((prev) => Math.min(prev + PAGE_SIZE, images.length));
  }, [images.length]);

  if (images.length === 0) {
    return (
      <div className={styles.empty}>
        <p>업로드된 이미지가 없습니다.</p>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* 이미지 수 정보 */}
      <div className={styles.header}>
        <span className={styles.count}>
          전체 {images.length.toLocaleString()}장
          {visibleImages.length < images.length &&
            ` (${visibleImages.length.toLocaleString()}장 표시 중)`}
        </span>
        {targetImageId && (
          <span className={styles.targetInfo}>★ 타겟 이미지 선택됨</span>
        )}
      </div>

      {/* 썸네일 그리드 */}
      <div
        className={styles.grid}
        role="listbox"
        aria-label="이미지 목록"
        aria-multiselectable="false"
      >
        {visibleImages.map((image) => (
          <MemoThumbnail
            key={image.image_id}
            image={image}
            isSelected={image.image_id === targetImageId}
            sessionId={sessionId}
            onSelect={handleSelect}
          />
        ))}
      </div>

      {/* 더 보기 버튼 */}
      {hasMore && (
        <div className={styles.loadMoreWrapper}>
          <button className={styles.loadMoreButton} onClick={handleLoadMore}>
            더 보기 ({images.length - visibleCount}장 남음)
          </button>
        </div>
      )}
    </div>
  );
}
