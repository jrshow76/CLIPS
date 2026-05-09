import { useEffect, useCallback, useRef, useState } from 'react';
import { useAppStore } from '../../store';
import { getImages } from '../../utils/api';
import { ImageGrid } from './ImageGrid';
import { OptionsPanel } from './OptionsPanel';
import { Spinner } from '../common/Spinner';
import styles from './GalleryView.module.css';

export function GalleryView() {
  const sessionId = useAppStore((state) => state.sessionId);
  const setImages = useAppStore((state) => state.setImages);
  const addToast = useAppStore((state) => state.addToast);
  const setStep = useAppStore((state) => state.setStep);

  // useState로 관리해야 값 변경 시 리렌더가 발생한다 (useRef는 리렌더를 유발하지 않음)
  const [isLoading, setIsLoading] = useState(true);
  const hasLoadedRef = useRef(false);
  const isLoadingRef = useRef(false);

  const loadImages = useCallback(async () => {
    if (isLoadingRef.current) return;
    isLoadingRef.current = true;
    try {
      // 백엔드 page_size 최대값이 100이므로 페이지를 순회하여 전체 이미지를 로드한다.
      const PAGE_SIZE = 100;
      const allItems: import('../../types').ImageInfo[] = [];
      let page = 1;
      let totalPages = 1;

      do {
        const result = await getImages(sessionId, page, PAGE_SIZE);
        allItems.push(...result.items);
        totalPages = result.total_pages;
        page++;
      } while (page <= totalPages);

      setImages(allItems);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : '이미지 목록을 불러오지 못했습니다.';
      addToast('error', message);
    } finally {
      isLoadingRef.current = false;
      setIsLoading(false);
    }
  }, [sessionId, setImages, addToast]);

  useEffect(() => {
    // 갤러리 첫 진입 시 항상 서버에서 최신 목록을 로드한다.
    if (!hasLoadedRef.current) {
      hasLoadedRef.current = true;
      loadImages();
    }
  }, [loadImages]);

  // 이미지 추가 업로드 버튼 → 업로드 단계로 이동
  const handleAddMore = useCallback(() => {
    setStep('upload');
  }, [setStep]);

  return (
    <div className={styles.container}>
      {/* 상단 액션 바 */}
      <div className={styles.actionBar}>
        <h2 className={styles.sectionTitle}>이미지 갤러리</h2>
        <button
          className={styles.addButton}
          onClick={handleAddMore}
          type="button"
        >
          + 이미지 추가
        </button>
      </div>

      {isLoading ? (
        /* 로딩 중 */
        <div className={styles.loadingWrapper}>
          <Spinner size="lg" label="이미지 목록을 불러오는 중..." />
        </div>
      ) : (
        /* 갤러리 + 옵션 패널 레이아웃 */
        <div className={styles.layout}>
          {/* 좌측: 이미지 그리드 */}
          <div className={styles.gridArea}>
            <ImageGrid />
          </div>

          {/* 우측: 옵션 패널 */}
          <aside className={styles.panelArea}>
            <OptionsPanel />
          </aside>
        </div>
      )}
    </div>
  );
}
