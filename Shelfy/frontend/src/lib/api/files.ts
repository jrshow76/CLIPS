/**
 * 파일 업로드 API 함수
 * API 요구사항 정의서 8. 파일 업로드 API 기반
 */

import apiClient from './client'
import type { ApiResponse } from '@/types/api'

export type FileUploadType = 'ITEM_IMAGE' | 'PROFILE_IMAGE'

export interface UploadedFile {
  imageId: string
  url: string
  fileName: string
  fileSize: number
  uploadedAt: string
}

/** 이미지 업로드 (인증 필요, multipart/form-data) */
export async function uploadFile(
  file: File,
  type: FileUploadType
): Promise<UploadedFile> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('type', type)

  const res = await apiClient.post<ApiResponse<UploadedFile>>(
    '/files/upload',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  )

  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error?.message ?? '파일 업로드에 실패했습니다.')
  }

  return res.data.data
}
