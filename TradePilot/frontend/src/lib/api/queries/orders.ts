import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { v4 as uuid } from 'uuid';

import { api } from '@/lib/api/client';
import { queryKeys } from '@/lib/api/query-keys';
import { mockOrders } from '@/lib/mocks/data';
import { toast } from '@/stores/notification-store';
import type { CreateOrderRequest, Order } from '@/types/order';

import { USE_MOCK, mockDelay } from './_mock-helpers';

export function useOrders(filter?: { status?: string; from?: string; to?: string }) {
  return useQuery<Order[]>({
    queryKey: queryKeys.orders.list(filter),
    queryFn: async () => {
      if (USE_MOCK) return mockDelay(mockOrders);
      return api.get<Order[]>('/orders', { params: filter });
    },
    staleTime: 5_000,
  });
}

/**
 * 주문 생성 mutation.
 * - X-Trade-Mode (axios 인터셉터로 자동 주입) 필수
 * - X-Idempotency-Key (axios 인터셉터로 자동 발급) 필수
 *
 * FrontendDev 가이드: 호출 측에서 `confirm dialog` 통과 후 `mutate(payload)` 호출.
 *   LIVE 모드 시 2차 확인은 UI 계층(LiveModeModal/주문확인모달)이 책임진다.
 */
export function useCreateOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateOrderRequest) => {
      const idemKey = payload.idempotency_key ?? uuid();
      if (USE_MOCK) {
        return mockDelay<Order>({
          id: `ord_${idemKey.slice(0, 8)}`,
          code: payload.code,
          side: payload.side,
          order_type: payload.order_type,
          qty: payload.qty,
          filled_qty: 0,
          price: payload.price,
          status: 'ACCEPTED',
          mode: 'SIM',
          created_at: new Date().toISOString(),
        });
      }
      return api.post<Order>('/orders', payload, {
        requireTradeMode: true,
        idempotent: true,
        headers: { 'X-Idempotency-Key': idemKey },
      });
    },
    onSuccess: (order) => {
      toast.success('주문이 접수되었습니다.', `${order.code} ${order.side} ${order.qty}주`);
      qc.invalidateQueries({ queryKey: queryKeys.orders.all });
      qc.invalidateQueries({ queryKey: queryKeys.portfolio.holdings() });
    },
    onError: (err: Error) => {
      toast.danger('주문 실패', err.message);
    },
  });
}

export function useCancelOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (orderId: string) => {
      if (USE_MOCK) return mockDelay({ id: orderId, status: 'CANCELED' as const });
      return api.post<Order>(`/orders/${orderId}/cancel`, undefined, { requireTradeMode: true });
    },
    onSuccess: () => {
      toast.success('주문 취소 요청 완료');
      qc.invalidateQueries({ queryKey: queryKeys.orders.all });
    },
  });
}
