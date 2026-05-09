import {
  useRef,
  useState,
  useCallback,
  type DragEvent,
  type ChangeEvent,
} from 'react';
import { uploadImages, uploadZip } from '../../utils/api';
import { useAppStore } from '../../store';
import { Spinner } from '../common/Spinner';
import styles from './UploadZone.module.css';

// 단일 파일 최대 크기 (20MB)
const MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024;
// 허용 이미지 MIME 타입
const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];

// 파일 크기를 사람이 읽기 쉬운 형태로 변환
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)}MB`;
}

export function UploadZone() {
  const sessionId = useAppStore((state) => state.sessionId);
  const addImages = useAppStore((state) => state.addImages);
  const setStep = useAppStore((state) => state.setStep);
  const addToast = useAppStore((state) => state.addToast);
  const isUploading = useAppStore((state) => state.isUploading);
  const uploadProgress = useAppStore((state) => state.uploadProgress);
  const setUploading = useAppStore((state) => state.setUploading);
  const setUploadProgress = useAppStore((state) => state.setUploadProgress);

  const [isDragOver, setIsDragOver] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');

  // 파일 input ref
  const imageInputRef = useRef<HTMLInputElement>(null);
  const zipInputRef = useRef<HTMLInputElement>(null);

  // 이미지 파일 유효성 검증
  const validateImageFiles = useCallback(
    (files: File[]): { valid: File[]; errors: string[] } => {
      const valid: File[] = [];
      const errors: string[] = [];

      for (const file of files) {
        if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
          errors.push(`${file.name}: 지원하지 않는 형식 (JPEG/PNG/WEBP/GIF만 허용)`);
          continue;
        }
        if (file.size > MAX_FILE_SIZE_BYTES) {
          errors.push(
            `${file.name}: 파일 크기 초과 (${formatFileSize(file.size)} > 20MB)`
          );
          continue;
        }
        valid.push(file);
      }

      return { valid, errors };
    },
    []
  );

  // 이미지 파일 업로드 처리
  const handleImageUpload = useCallback(
    async (files: File[]) => {
      if (files.length === 0) return;

      const { valid, errors } = validateImageFiles(files);

      if (errors.length > 0) {
        errors.forEach((e) => addToast('warning', e));
      }

      if (valid.length === 0) {
        addToast('error', '업로드 가능한 파일이 없습니다.');
        return;
      }

      setUploading(true);
      setUploadProgress(0);
      setStatusMessage(`${valid.length}개 파일 업로드 중...`);

      try {
        const result = await uploadImages(valid, sessionId, (percent) => {
          setUploadProgress(percent);
        });

        if (result.failed.length > 0) {
          result.failed.forEach((f) =>
            addToast('warning', `${f.filename}: ${f.error}`)
          );
        }

        if (result.uploaded.length > 0) {
          addImages(result.uploaded);
          addToast(
            'success',
            `${result.uploaded.length}개 이미지 업로드 완료`
          );
          setStep('gallery');
        } else {
          addToast('error', '업로드된 이미지가 없습니다.');
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : '업로드 중 오류가 발생했습니다.';
        addToast('error', message);
      } finally {
        setUploading(false);
        setUploadProgress(0);
        setStatusMessage('');
      }
    },
    [sessionId, addImages, setStep, addToast, setUploading, setUploadProgress, validateImageFiles]
  );

  // ZIP 파일 업로드 처리
  const handleZipUpload = useCallback(
    async (file: File) => {
      if (file.size > 500 * 1024 * 1024) {
        addToast('warning', 'ZIP 파일은 500MB 이하만 업로드 가능합니다.');
        return;
      }

      setUploading(true);
      setUploadProgress(0);
      setStatusMessage('ZIP 파일 업로드 및 압축 해제 중...');

      try {
        const result = await uploadZip(file, sessionId, (percent) => {
          setUploadProgress(percent);
        });

        if (result.failed.length > 0) {
          result.failed.slice(0, 3).forEach((f) =>
            addToast('warning', `${f.filename}: ${f.error}`)
          );
          if (result.failed.length > 3) {
            addToast('warning', `외 ${result.failed.length - 3}개 파일 처리 실패`);
          }
        }

        if (result.uploaded.length > 0) {
          addImages(result.uploaded);
          addToast(
            'success',
            `ZIP에서 ${result.uploaded.length}개 이미지 업로드 완료`
          );
          setStep('gallery');
        } else {
          addToast('error', 'ZIP 파일에서 이미지를 찾을 수 없습니다.');
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : 'ZIP 업로드 중 오류가 발생했습니다.';
        addToast('error', message);
      } finally {
        setUploading(false);
        setUploadProgress(0);
        setStatusMessage('');
      }
    },
    [sessionId, addImages, setStep, addToast, setUploading, setUploadProgress]
  );

  // 드래그 앤 드롭 이벤트 핸들러
  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: DragEvent<HTMLDivElement>) => {
    // 자식 요소로 이동 시 이벤트 무시
    if (!e.currentTarget.contains(e.relatedTarget as Node)) {
      setIsDragOver(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragOver(false);

      const files = Array.from(e.dataTransfer.files);
      const zipFiles = files.filter((f) => f.type === 'application/zip' || f.name.endsWith('.zip'));
      const imageFiles = files.filter((f) => ALLOWED_IMAGE_TYPES.includes(f.type));

      if (zipFiles.length > 0) {
        handleZipUpload(zipFiles[0]);
      } else if (imageFiles.length > 0) {
        handleImageUpload(imageFiles);
      } else {
        addToast('error', '이미지 파일(JPEG/PNG/WEBP) 또는 ZIP 파일을 드롭하세요.');
      }
    },
    [handleImageUpload, handleZipUpload, addToast]
  );

  // 파일 input 변경 핸들러
  const handleImageInputChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files ?? []);
      handleImageUpload(files);
      // input 값 초기화 (동일 파일 재선택 허용)
      e.target.value = '';
    },
    [handleImageUpload]
  );

  const handleZipInputChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        handleZipUpload(file);
        e.target.value = '';
      }
    },
    [handleZipUpload]
  );

  return (
    <div className={styles.container}>
      <div
        className={`${styles.dropZone} ${isDragOver ? styles.dragOver : ''} ${isUploading ? styles.uploading : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        role="region"
        aria-label="파일 업로드 영역"
      >
        {isUploading ? (
          /* 업로드 진행 중 표시 */
          <div className={styles.uploadingState}>
            <Spinner size="lg" label="" />
            <p className={styles.statusMessage}>{statusMessage}</p>
            <div className={styles.progressBar}>
              <div
                className={styles.progressFill}
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
            <p className={styles.progressText}>{uploadProgress}%</p>
          </div>
        ) : (
          /* 기본 업로드 안내 */
          <div className={styles.idleState}>
            <div className={styles.iconWrapper}>
              <svg
                className={styles.uploadIcon}
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
              </svg>
            </div>

            <h2 className={styles.title}>이미지를 드래그하거나 선택하세요</h2>
            <p className={styles.description}>
              JPEG, PNG, WEBP 이미지 파일 (최대 20MB/개)
              <br />
              또는 이미지가 담긴 ZIP 파일
            </p>

            <div className={styles.buttonGroup}>
              {/* 이미지 파일 선택 버튼 */}
              <button
                className={styles.primaryButton}
                onClick={() => imageInputRef.current?.click()}
                type="button"
              >
                이미지 파일 선택
              </button>

              {/* ZIP 파일 선택 버튼 */}
              <button
                className={styles.secondaryButton}
                onClick={() => zipInputRef.current?.click()}
                type="button"
              >
                ZIP 파일 선택
              </button>
            </div>

            <p className={styles.hint}>
              드래그 앤 드롭으로도 업로드 가능합니다
            </p>
          </div>
        )}
      </div>

      {/* 숨김 파일 input */}
      <input
        ref={imageInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/gif"
        multiple
        className={styles.hiddenInput}
        onChange={handleImageInputChange}
        aria-hidden="true"
      />
      <input
        ref={zipInputRef}
        type="file"
        accept=".zip,application/zip"
        className={styles.hiddenInput}
        onChange={handleZipInputChange}
        aria-hidden="true"
      />
    </div>
  );
}
