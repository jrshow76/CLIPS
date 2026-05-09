import { useCallback, useState } from 'react';
import { useAppStore } from '../../store';
import { downloadResult, buildResultUrl } from '../../utils/api';
import { Spinner } from '../common/Spinner';
import styles from './ResultView.module.css';

export function ResultView() {
  const sessionId = useAppStore((state) => state.sessionId);
  const currentJob = useAppStore((state) => state.currentJob);
  const mosaicOptions = useAppStore((state) => state.mosaicOptions);
  const reset = useAppStore((state) => state.reset);
  const addToast = useAppStore((state) => state.addToast);

  const [downloadingFormat, setDownloadingFormat] = useState<'png' | 'jpeg' | null>(null);

  // Blob을 <a> 태그로 다운로드하는 유틸
  const triggerDownload = useCallback((blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    // 메모리 해제
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }, []);

  // 다운로드 핸들러
  const handleDownload = useCallback(
    async (format: 'png' | 'jpeg') => {
      if (!currentJob?.job_id || downloadingFormat !== null) return;

      setDownloadingFormat(format);
      try {
        const quality = format === 'jpeg' ? 90 : 100;
        const blob = await downloadResult(
          currentJob.job_id,
          sessionId,
          format,
          quality
        );
        const ext = format === 'jpeg' ? 'jpg' : 'png';
        const filename = `photomosaic_${currentJob.job_id.slice(0, 8)}.${ext}`;
        triggerDownload(blob, filename);
        addToast('success', `${ext.toUpperCase()} 파일 다운로드 시작`);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : '다운로드 중 오류가 발생했습니다.';
        addToast('error', message);
      } finally {
        setDownloadingFormat(null);
      }
    },
    [currentJob, sessionId, downloadingFormat, triggerDownload, addToast]
  );

  // 다시 시작 핸들러
  const handleRestart = useCallback(() => {
    const confirmed = window.confirm(
      '처음부터 다시 시작하시겠습니까?\n업로드된 이미지와 현재 세션이 초기화됩니다.'
    );
    if (confirmed) {
      reset();
    }
  }, [reset]);

  if (!currentJob || !currentJob.result_url) {
    return (
      <div className={styles.container}>
        <div className={styles.errorCard}>
          <p>결과 이미지를 불러올 수 없습니다.</p>
          <button className={styles.restartButton} onClick={handleRestart} type="button">
            다시 시작
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        {/* 완료 배지 */}
        <div className={styles.successBadge}>
          <span className={styles.checkIcon}>✓</span>
          모자이크 생성 완료!
        </div>

        {/* 결과 이미지 미리보기 (session_id 쿼리 파라미터로 인증) */}
        <div className={styles.previewWrapper}>
          <img
            src={currentJob.result_url ? buildResultUrl(currentJob.result_url, sessionId) : ''}
            alt="생성된 포토모자이크 결과"
            className={styles.resultImage}
          />
        </div>

        {/* 생성 옵션 요약 정보 */}
        <div className={styles.summary}>
          <span className={styles.summaryItem}>
            격자 {mosaicOptions.grid_division}×{mosaicOptions.grid_division}
          </span>
          <span className={styles.summaryDivider}>·</span>
          <span className={styles.summaryItem}>
            타일 {mosaicOptions.tile_size}px
          </span>
          <span className={styles.summaryDivider}>·</span>
          <span className={styles.summaryItem}>
            {mosaicOptions.color_match_method === 'average' ? '평균색' : '주요색'} 매칭
          </span>
        </div>

        {/* 다운로드 버튼 그룹 */}
        <div className={styles.downloadGroup}>
          <p className={styles.downloadLabel}>다운로드</p>
          <div className={styles.buttonRow}>
            {/* PNG 다운로드 */}
            <button
              className={styles.downloadButton}
              onClick={() => handleDownload('png')}
              disabled={downloadingFormat !== null}
              type="button"
            >
              {downloadingFormat === 'png' ? (
                <Spinner size="sm" label="" />
              ) : null}
              PNG 다운로드
              <span className={styles.formatBadge}>무손실</span>
            </button>

            {/* JPG 다운로드 */}
            <button
              className={`${styles.downloadButton} ${styles.jpgButton}`}
              onClick={() => handleDownload('jpeg')}
              disabled={downloadingFormat !== null}
              type="button"
            >
              {downloadingFormat === 'jpeg' ? (
                <Spinner size="sm" label="" />
              ) : null}
              JPG 다운로드
              <span className={styles.formatBadge}>품질 90</span>
            </button>
          </div>
        </div>

        {/* 다시 시작 버튼 */}
        <button
          className={styles.restartButton}
          onClick={handleRestart}
          type="button"
        >
          다시 시작
        </button>
      </div>
    </div>
  );
}
