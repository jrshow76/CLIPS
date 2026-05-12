export type NotificationVariant =
  | 'SIGNAL'
  | 'FILL'
  | 'LIMIT'
  | 'SYSTEM'
  | 'BACKTEST'
  | 'NEWS';

export interface AppNotification {
  id: string;
  variant: NotificationVariant;
  title: string;
  message: string;
  /** ISO 시각 */
  created_at: string;
  read: boolean;
  /** 클릭 시 이동할 라우트 */
  link?: string;
}
