// 이미지 정보 타입
export interface ImageInfo {
  image_id: string;
  filename: string;
  thumbnail_url: string;
  width?: number;
  height?: number;
  size_bytes?: number;
  is_target: boolean;
}

// 모자이크 생성 옵션 타입
export interface MosaicOptions {
  grid_division: number;           // 격자 분할 수: 10~200, 기본값 50
  tile_size: number;               // 타일 크기(px): 8~128, 기본값 32
  color_match_method: 'average' | 'dominant'; // 색상 매칭 방법
  allow_tile_repeat: boolean;      // 타일 반복 허용 여부
  blend_ratio: number;             // 원본 블렌딩 비율: 0.0~1.0
  output_format: 'png' | 'jpeg' | 'webp';  // 출력 파일 형식
  output_quality: number;          // JPG 품질: 1~100
}

// 작업 상태 타입
export type JobStatus =
  | 'pending'      // 대기 중
  | 'running'      // 처리 중
  | 'analyzing'    // 타일 분석 중
  | 'matching'     // 이미지 매칭 중
  | 'compositing'  // 합성 중
  | 'completed'    // 완료
  | 'failed'       // 실패
  | 'cancelled';   // 취소됨

// 작업 정보 타입 (백엔드 JobStatus 스키마와 일치)
export interface JobInfo {
  job_id: string;
  status: JobStatus;
  progress: number;              // 0~100
  step: string;
  step_message: string;
  elapsed_seconds: number;
  result_url?: string | null;
  warning?: string | null;       // 경고 메시지 (e.g. 타일 반복 fallback)
  allow_tile_repeat_fallback?: boolean;
}

// 앱 단계 타입
export type AppStep = 'upload' | 'gallery' | 'processing' | 'result';

// 모자이크 생성 요청 타입
export interface GenerateRequest {
  session_id: string;
  target_image_id: string;
  options: MosaicOptions;
}

// API 공통 응답 타입 (백엔드 CommonResponse<T> 와 일치)
export interface ApiResponse<T> {
  success: boolean;
  data?: T | null;
  error?: { code: string; message: string } | null;
}

// 이미지 목록 응답 타입 (백엔드 ImageListResponse 와 일치: items 키 사용)
export interface ImageListResponse {
  items: ImageInfo[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// 업로드 응답 타입 (백엔드 UploadResponse 와 일치: total_count 키 사용)
export interface UploadResponse {
  uploaded: ImageInfo[];
  failed: Array<{
    filename: string;
    error?: string;
    reason?: string;
  }>;
  total_count: number;
}

// 토스트 메시지 타입
export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastItem {
  id: string;
  type: ToastType;
  message: string;
}
