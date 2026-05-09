/**
 * API 공통 응답 타입 정의
 * DevLead 개발 표준 1.3 공통 성공 응답 포맷 기반
 */

export interface ApiResponse<T> {
  success: boolean
  data: T | null
  error: ApiError | null
  timestamp: string
}

export interface ApiError {
  code: string
  message: string
  details?: FieldError[]
}

export interface FieldError {
  field: string
  message: string
}

export interface PageResponse<T> {
  content: T[]
  page: number
  size: number
  totalElements: number
  totalPages: number
  first: boolean
  last: boolean
}
