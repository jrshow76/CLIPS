import { useEffect, useRef, useCallback } from 'react';
import { getJobStatus } from '../utils/api';
import { useAppStore } from '../store';
import type { JobStatus } from '../types';

// 폴링을 중단하는 최종 상태 목록
const TERMINAL_STATUSES: JobStatus[] = ['completed', 'failed', 'cancelled'];

// 폴링 간격 (밀리초)
const POLLING_INTERVAL_MS = 2000;

/**
 * 작업 상태를 주기적으로 조회하는 커스텀 훅
 * - jobId가 있으면 2초마다 상태 폴링
 * - status가 completed/failed/cancelled이면 폴링 중단
 */
export function useJobPolling(jobId: string | null): void {
  const updateJob = useAppStore((state) => state.updateJob);
  const setStep = useAppStore((state) => state.setStep);
  const addToast = useAppStore((state) => state.addToast);
  const currentJob = useAppStore((state) => state.currentJob);
  const sessionId = useAppStore((state) => state.sessionId);

  // 폴링 타이머 ref (클린업용)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // 현재 폴링 중인 jobId 추적
  const activeJobIdRef = useRef<string | null>(null);

  const stopPolling = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const poll = useCallback(async () => {
    if (!activeJobIdRef.current) return;

    try {
      const job = await getJobStatus(activeJobIdRef.current, sessionId);
      updateJob(job);

      if (TERMINAL_STATUSES.includes(job.status)) {
        // 최종 상태 도달 시 폴링 중단 및 단계 전환
        stopPolling();

        if (job.status === 'completed') {
          setStep('result');
        } else if (job.status === 'failed') {
          addToast('error', `모자이크 생성 실패: ${job.step_message || '알 수 없는 오류'}`);
          setStep('gallery');
        } else if (job.status === 'cancelled') {
          addToast('warning', '모자이크 생성이 취소되었습니다.');
          setStep('gallery');
        }
      } else {
        // 계속 폴링
        timerRef.current = setTimeout(poll, POLLING_INTERVAL_MS);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : '상태 조회 중 오류가 발생했습니다.';
      addToast('error', message);
      stopPolling();
      setStep('gallery');
    }
  }, [updateJob, setStep, addToast, stopPolling]);

  useEffect(() => {
    if (!jobId) {
      stopPolling();
      activeJobIdRef.current = null;
      return;
    }

    // 이미 최종 상태라면 폴링 불필요
    if (currentJob && TERMINAL_STATUSES.includes(currentJob.status)) {
      return;
    }

    activeJobIdRef.current = jobId;
    // 첫 폴링 즉시 시작
    poll();

    return () => {
      stopPolling();
    };
    // poll은 useCallback으로 메모이제이션되어 있으므로 jobId 변경 시에만 재실행
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);
}
