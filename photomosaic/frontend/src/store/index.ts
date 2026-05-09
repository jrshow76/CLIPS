import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';
import type { AppStep, ImageInfo, JobInfo, MosaicOptions, ToastItem, ToastType } from '../types';

// localStorage 키 상수
const SESSION_KEY = 'photomosaic_session_id';

// 기존 세션 ID 복원 또는 신규 생성
const initSessionId = (): string => {
  const saved = localStorage.getItem(SESSION_KEY);
  if (saved) return saved;
  const newId = uuidv4();
  localStorage.setItem(SESSION_KEY, newId);
  return newId;
};

// 모자이크 옵션 기본값
const DEFAULT_MOSAIC_OPTIONS: MosaicOptions = {
  grid_division: 50,
  tile_size: 32,
  color_match_method: 'average',
  allow_tile_repeat: true,
  blend_ratio: 0.0,
  output_format: 'png' as const,
  output_quality: 90,
};

// 앱 전역 상태 인터페이스
interface AppStore {
  // 상태
  sessionId: string;
  step: AppStep;
  images: ImageInfo[];
  targetImageId: string | null;
  currentJob: JobInfo | null;
  mosaicOptions: MosaicOptions;
  toasts: ToastItem[];
  isUploading: boolean;
  uploadProgress: number; // 0~100

  // 액션
  setStep: (step: AppStep) => void;
  addImages: (images: ImageInfo[]) => void;
  setImages: (images: ImageInfo[]) => void;
  setTargetImage: (imageId: string) => void;
  clearTargetImage: () => void;
  updateJob: (job: JobInfo) => void;
  clearJob: () => void;
  updateOptions: (options: Partial<MosaicOptions>) => void;
  setUploading: (uploading: boolean) => void;
  setUploadProgress: (progress: number) => void;
  addToast: (type: ToastType, message: string) => void;
  removeToast: (id: string) => void;
  reset: () => void;
}

export const useAppStore = create<AppStore>((set, get) => ({
  // 초기 상태
  sessionId: initSessionId(),
  step: 'upload',
  images: [],
  targetImageId: null,
  currentJob: null,
  mosaicOptions: { ...DEFAULT_MOSAIC_OPTIONS },
  toasts: [],
  isUploading: false,
  uploadProgress: 0,

  // 단계 전환
  setStep: (step) => set({ step }),

  // 이미지 추가 (기존 목록에 병합, 중복 제거)
  addImages: (newImages) =>
    set((state) => {
      const existingIds = new Set(state.images.map((img) => img.image_id));
      const filtered = newImages.filter((img) => !existingIds.has(img.image_id));
      return { images: [...state.images, ...filtered] };
    }),

  // 이미지 목록 교체
  setImages: (images) => set({ images }),

  // 타겟 이미지 선택
  setTargetImage: (imageId) =>
    set((state) => ({
      targetImageId: imageId,
      // 이미지 목록에서 is_target 플래그 업데이트
      images: state.images.map((img) => ({
        ...img,
        is_target: img.image_id === imageId,
      })),
    })),

  // 타겟 이미지 선택 해제
  clearTargetImage: () =>
    set((state) => ({
      targetImageId: null,
      images: state.images.map((img) => ({ ...img, is_target: false })),
    })),

  // 작업 상태 업데이트
  updateJob: (job) => set({ currentJob: job }),

  // 작업 초기화
  clearJob: () => set({ currentJob: null }),

  // 옵션 부분 업데이트
  updateOptions: (options) =>
    set((state) => ({
      mosaicOptions: { ...state.mosaicOptions, ...options },
    })),

  // 업로드 상태 설정
  setUploading: (uploading) => set({ isUploading: uploading }),

  // 업로드 진행률 설정
  setUploadProgress: (progress) => set({ uploadProgress: progress }),

  // 토스트 추가
  addToast: (type, message) => {
    const id = uuidv4();
    set((state) => ({
      toasts: [...state.toasts, { id, type, message }],
    }));
    // 3초 후 자동 제거
    setTimeout(() => {
      get().removeToast(id);
    }, 3000);
  },

  // 토스트 제거
  removeToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),

  // 전체 초기화 (세션 ID는 유지)
  reset: () => {
    const newSessionId = uuidv4();
    localStorage.setItem(SESSION_KEY, newSessionId);
    set({
      sessionId: newSessionId,
      step: 'upload',
      images: [],
      targetImageId: null,
      currentJob: null,
      mosaicOptions: { ...DEFAULT_MOSAIC_OPTIONS },
      isUploading: false,
      uploadProgress: 0,
    });
  },
}));
