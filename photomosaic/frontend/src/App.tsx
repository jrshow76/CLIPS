import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAppStore } from './store';
import { UploadZone } from './components/upload/UploadZone';
import { GalleryView } from './components/gallery/GalleryView';
import { ProcessingView } from './components/mosaic/ProcessingView';
import { ResultView } from './components/mosaic/ResultView';
import { ToastContainer } from './components/common/Toast';
import styles from './App.module.css';

// TanStack Query 클라이언트 설정
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// 단계 인디케이터 정의
const STEPS = [
  { key: 'upload', label: '1. 업로드' },
  { key: 'gallery', label: '2. 설정' },
  { key: 'processing', label: '3. 처리 중' },
  { key: 'result', label: '4. 결과' },
] as const;

function AppContent() {
  const step = useAppStore((state) => state.step);

  // 현재 단계 인덱스 계산 (인디케이터 활성화에 사용)
  const currentIndex = STEPS.findIndex((s) => s.key === step);

  return (
    <div className={styles.appWrapper}>
      {/* 헤더 */}
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <div className={styles.logo}>
            <span className={styles.logoIcon}>◈</span>
            <h1 className={styles.logoTitle}>포토모자이크 생성기</h1>
          </div>

          {/* 단계 인디케이터 */}
          <nav className={styles.stepNav} aria-label="진행 단계">
            {STEPS.map((s, idx) => (
              <div
                key={s.key}
                className={`${styles.stepItem} ${
                  idx < currentIndex
                    ? styles.stepDone
                    : idx === currentIndex
                    ? styles.stepActive
                    : styles.stepPending
                }`}
                aria-current={idx === currentIndex ? 'step' : undefined}
              >
                <span className={styles.stepNumber}>{idx + 1}</span>
                <span className={styles.stepLabel}>{s.label.replace(/^\d+\. /, '')}</span>
              </div>
            ))}
          </nav>
        </div>
      </header>

      {/* 메인 콘텐츠 */}
      <main className={styles.main}>
        <div className={styles.contentWrapper}>
          {step === 'upload' && <UploadZone />}
          {step === 'gallery' && <GalleryView />}
          {step === 'processing' && <ProcessingView />}
          {step === 'result' && <ResultView />}
        </div>
      </main>

      {/* 푸터 */}
      <footer className={styles.footer}>
        <p>포토모자이크 생성기 — 여러 장의 사진으로 하나의 모자이크 아트를 만드세요</p>
      </footer>

      {/* 토스트 알림 (전역) */}
      <ToastContainer />
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  );
}

export default App;
