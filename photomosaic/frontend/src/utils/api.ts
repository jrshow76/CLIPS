import axios, { type AxiosProgressEvent } from 'axios';
import type {
  ApiResponse,
  GenerateRequest,
  ImageListResponse,
  JobInfo,
  UploadResponse,
} from '../types';

// axios 인스턴스 생성 (Vite 프록시로 /api → localhost:8000 전달)
const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
});

// 응답 인터셉터: 서버 에러 메시지 추출
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error)) {
      const errorData = error.response?.data;
      // 백엔드 CommonResponse 에러 형식 처리
      const serverMessage =
        errorData?.error?.message ||
        errorData?.detail?.message ||
        errorData?.detail ||
        errorData?.message ||
        error.message;
      return Promise.reject(new Error(
        typeof serverMessage === 'string' ? serverMessage : JSON.stringify(serverMessage)
      ));
    }
    return Promise.reject(error);
  }
);

// 공통 응답 언래핑 헬퍼: CommonResponse<T> → T
function unwrap<T>(apiResponse: ApiResponse<T>): T {
  if (!apiResponse.success || apiResponse.data === undefined || apiResponse.data === null) {
    const msg = apiResponse.error?.message || '서버 오류가 발생했습니다.';
    throw new Error(msg);
  }
  return apiResponse.data;
}

// 이미지 파일 복수 업로드
export const uploadImages = async (
  files: File[],
  sessionId: string,
  onProgress?: (percent: number) => void
): Promise<UploadResponse> => {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));

  const response = await apiClient.post<ApiResponse<UploadResponse>>(
    '/images/upload',
    formData,
    {
      headers: {
        'X-Session-ID': sessionId,
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (event: AxiosProgressEvent) => {
        if (event.total && onProgress) {
          const percent = Math.round((event.loaded / event.total) * 100);
          onProgress(percent);
        }
      },
    }
  );
  return unwrap(response.data);
};

// ZIP 파일 업로드 (엔드포인트: /images/upload/zip)
export const uploadZip = async (
  file: File,
  sessionId: string,
  onProgress?: (percent: number) => void
): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post<ApiResponse<UploadResponse>>(
    '/images/upload/zip',
    formData,
    {
      headers: {
        'X-Session-ID': sessionId,
        'Content-Type': 'multipart/form-data',
      },
      timeout: 120000,
      onUploadProgress: (event: AxiosProgressEvent) => {
        if (event.total && onProgress) {
          const percent = Math.round((event.loaded / event.total) * 100);
          onProgress(percent);
        }
      },
    }
  );
  return unwrap(response.data);
};

// 이미지 목록 조회 (페이지네이션, 백엔드는 items 키 사용)
export const getImages = async (
  sessionId: string,
  page = 1,
  pageSize = 100
): Promise<ImageListResponse> => {
  const response = await apiClient.get<ApiResponse<ImageListResponse>>('/images', {
    headers: { 'X-Session-ID': sessionId },
    params: { page, page_size: pageSize },
  });
  return unwrap(response.data);
};

// 타겟 이미지 지정 (PATCH /images/{id}/target)
export const setTargetImageApi = async (
  imageId: string,
  sessionId: string
): Promise<void> => {
  await apiClient.patch(
    `/images/${imageId}/target`,
    { session_id: sessionId },
    { headers: { 'X-Session-ID': sessionId } }
  );
};

// 모자이크 생성 요청 (POST /mosaic/generate, 202 반환)
export const generateMosaic = async (request: GenerateRequest): Promise<JobInfo> => {
  const response = await apiClient.post<ApiResponse<JobInfo>>(
    '/mosaic/generate',
    request,
    { headers: { 'X-Session-ID': request.session_id } }
  );
  return unwrap(response.data);
};

// 작업 상태 조회 (GET /mosaic/jobs/{id}/status)
export const getJobStatus = async (jobId: string, sessionId: string): Promise<JobInfo> => {
  const response = await apiClient.get<ApiResponse<JobInfo>>(
    `/mosaic/jobs/${jobId}/status`,
    { headers: { 'X-Session-ID': sessionId } }
  );
  return unwrap(response.data);
};

// 작업 취소 (DELETE /mosaic/jobs/{id})
export const cancelJob = async (
  jobId: string,
  sessionId: string
): Promise<void> => {
  await apiClient.delete(`/mosaic/jobs/${jobId}`, {
    headers: { 'X-Session-ID': sessionId },
  });
};

// 결과 이미지 다운로드 (GET /mosaic/jobs/{id}/result → Blob 반환)
export const downloadResult = async (
  jobId: string,
  sessionId: string,
  format: 'png' | 'jpeg' | 'webp',
  quality = 90
): Promise<Blob> => {
  const response = await apiClient.get(`/mosaic/jobs/${jobId}/result`, {
    headers: { 'X-Session-ID': sessionId },
    params: { format, quality },
    responseType: 'blob',
    timeout: 60000,
  });
  return response.data as Blob;
};

// 썸네일 URL 생성 헬퍼 (session_id 쿼리 파라미터 포함)
export const buildThumbnailUrl = (thumbnailUrl: string, sessionId: string): string => {
  const separator = thumbnailUrl.includes('?') ? '&' : '?';
  return `${thumbnailUrl}${separator}session_id=${encodeURIComponent(sessionId)}`;
};

// 결과 이미지 URL 생성 헬퍼 (session_id 쿼리 파라미터 포함)
export const buildResultUrl = (resultUrl: string, sessionId: string): string => {
  const separator = resultUrl.includes('?') ? '&' : '?';
  return `${resultUrl}${separator}session_id=${encodeURIComponent(sessionId)}`;
};

export default apiClient;
