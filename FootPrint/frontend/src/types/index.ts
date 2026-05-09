// ─── 공통 응답 타입 ───────────────────────────────────────────
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  errorCode?: string;
  message?: string;
}

export interface PageResponse<T> {
  content: T[];
  totalElements: number;
  totalPages: number;
  size: number;
  number: number;
}

// ─── 인증 ─────────────────────────────────────────────────────
export interface TokenResponse {
  accessToken: string;
  refreshToken: string;
  accessTokenExpiresIn: number;
}

export interface User {
  id: string;
  email: string;
  nickname: string;
  profileImageUrl?: string;
}

// ─── 카테고리 ─────────────────────────────────────────────────
export interface Category {
  id: number;
  name: string;
  color: string;
  icon: string;
  isDefault: boolean;
  sortOrder: number;
}

// ─── 장소 ─────────────────────────────────────────────────────
export interface PlaceSummary {
  id: number;
  name: string;
  address?: string;
  latitude: number;
  longitude: number;
  visitedAt: string;
  rating?: number;
  thumbnailUrl?: string;
  categories: Category[];
  tags: string[];
}

export interface PlaceDetail extends PlaceSummary {
  memo?: string;
  photos: PlacePhoto[];
  createdAt: string;
  updatedAt: string;
}

export interface PlacePhoto {
  id: number;
  fileUrl: string;
  thumbnailUrl?: string;
  originalName: string;
  sortOrder: number;
}

export interface PlaceRequest {
  name: string;
  address?: string;
  latitude: number;
  longitude: number;
  visitedAt: string;
  memo?: string;
  rating?: number;
  categoryIds: number[];
  tags?: string[];
}

// ─── 통계 ─────────────────────────────────────────────────────
export interface TopCategory {
  categoryId: number;
  name: string;
  placeCount: number;
}

export interface StatsSummary {
  totalPlaces: number;
  thisMonthPlaces: number;
  avgRating?: number;
  topCategory?: TopCategory;
}

export interface MonthlyStats {
  year: number;
  month: number;
  count: number;
}

export interface CategoryInfo {
  id: number;
  name: string;
  color: string;
  icon: string;
}

export interface CategoryStats {
  category: CategoryInfo;
  count: number;
  ratio: number;
}
