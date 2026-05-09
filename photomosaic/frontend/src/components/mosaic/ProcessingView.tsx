import { useCallback } from 'react';
import { useAppStore } from '../../store';
import { cancelJob } from '../../utils/api';
import { useJobPolling } from '../../hooks/usePolling';
import type { JobStatus } from '../../types';
import styles from './ProcessingView.module.css';

// 단계별 한글 메시지 매핑
const STATUS_LABELS: Record<JobStatus, string> = {
  pending: '대기 중...',
  running: '처리 중...',
  analyzing: '타일 분석 중...',
  matching: '이미지 매칭 중...',
  compositing: '모자이크 합성 중...',
  completed: '완료!',
  failed: '처리 실패',
  cancelled: '취소됨',
};

// 경과 시간을 mm:ss 형식으로 변환
function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

export function ProcessingView() {
  const sessionId = useAppStore((state) => state.sessionId);
  const currentJob = useAppStore((state) => state.currentJob);
  const addToast = useAppStore((state) => state.addToast);

  // 폴링 훅 등록 (상태 자동 업데이트)
  useJobPolling(currentJob?.job_id ?? null);

  // 취소 버튼 핸들러
  const handleCancel = useCallback(async () => {
    if (!currentJob) return;

    const confirmed = window.confirm('모자이크 생성을 취소하시겠습니까?');
    if (!confirmed) return;

    try {
      await cancelJob(currentJob.job_id, sessionId);
      addToast('info', '취소 요청이 전송되었습니다. 잠시 후 종료됩니다.');
    } catch (err) {
      const message = err instanceof Error ? err.message : '취소 요청 중 오류가 발생했습니다.';
      addToast('error', message);
    }
  }, [currentJob, sessionId, addToast]);

  if (!currentJob) {
    return (
      <div className={styles.container}>
        <p className={styles.waitMessage}>처리 정보를 불러오는 중...</p>
      </div>
    );
  }

  const statusLabel =
    currentJob.step_message || STATUS_LABELS[currentJob.status] || '처리 중...';
  const isCancellable =
    currentJob.status !== 'completed' &&
    currentJob.status !== 'failed' &&
    currentJob.status !== 'cancelled';

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        {/* 제목 */}
        <h2 className={styles.title}>모자이크 생성 중</h2>

        {/* 애니메이션 아이콘 */}
        <div className={styles.animationWrapper} aria-hidden="true">
          <div className={styles.circle1} />
          <div className={styles.circle2} />
          <div className={styles.circle3} />
        </div>

        {/* 단계 메시지 */}
        <p className={styles.stepMessage}>{statusLabel}</p>

        {/* 진행률 표시 */}
        <div className={styles.progressSection}>
          <div className={styles.progressHeader}>
            <span className={styles.progressLabel}>진행률</span>
            <span className={styles.progressPercent}>
              {currentJob.progress}%
            </span>
          </div>
          <div
            className={styles.progressBar}
            role="progressbar"
            aria-valuenow={currentJob.progress}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div
              className={styles.progressFill}
              style={{ width: `${currentJob.progress}%` }}
            />
          </div>
        </div>

        {/* 경과 시간 */}
        <p className={styles.elapsed}>
          경과 시간: {formatElapsed(currentJob.elapsed_seconds)}
        </p>

        {/* 타일 반복 폴백 안내 */}
        {(currentJob.warning || currentJob.allow_tile_repeat_fallback) && (
          <div className={styles.fallbackNotice} role="alert">
            {currentJob.warning || '이미지 수가 부족하여 타일 반복 허용으로 전환되었습니다.'}
          </div>
        )}

        {/* 취소 버튼 */}
        {isCancellable && (
          <button
            className={styles.cancelButton}
            onClick={handleCancel}
            type="button"
          >
            취소
          </button>
        )}
      </div>
    </div>
  );
}
