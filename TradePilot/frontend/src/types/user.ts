import type { TradeMode } from './api';

export type UserRole =
  | 'ROLE_GUEST'
  | 'ROLE_TRADER'
  | 'ROLE_TRADER_PRO'
  | 'ROLE_OPERATOR'
  | 'ROLE_ADMIN';

export interface User {
  id: string;
  email: string;
  nickname: string;
  role: UserRole;
  trade_mode: TradeMode;
  phone?: string;
  created_at: string;
  email_verified?: boolean;
}

export interface AuthTokens {
  access_token: string;
  refresh_token?: string;
  expires_in: number; // seconds
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface SignupRequest {
  email: string;
  password: string;
  nickname: string;
}
