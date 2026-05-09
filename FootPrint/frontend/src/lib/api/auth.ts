import { apiClient } from './client';
import type { ApiResponse, TokenResponse, User } from '@/types';

export interface SignupRequest {
  email: string;
  password: string;
  nickname: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export const authApi = {
  signup: (data: SignupRequest) =>
    apiClient.post<ApiResponse<User>>('/auth/signup', data),

  login: (data: LoginRequest) =>
    apiClient.post<ApiResponse<TokenResponse & { user: User }>>('/auth/login', data),

  refresh: (refreshToken: string) =>
    apiClient.post<ApiResponse<TokenResponse>>(
      '/auth/refresh',
      null,
      { headers: { 'X-Refresh-Token': refreshToken } }
    ),

  logout: () =>
    apiClient.post<ApiResponse<null>>('/auth/logout'),

  me: () =>
    apiClient.get<ApiResponse<User>>('/auth/me'),
};
