'use client';

import { AlertTriangle } from 'lucide-react';
import { useEffect, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Field, Input } from '@/components/ui/input';
import { Modal } from '@/components/ui/modal';
import { RadioGroup } from '@/components/ui/radio';
import { StatRow } from '@/components/ui/stat-row';
import { useCreateOrder } from '@/lib/api/queries/orders';
import { useQuote } from '@/lib/api/queries/stocks';
import { formatCurrency } from '@/lib/utils/format';
import { useTradeModeStore } from '@/stores/trade-mode-store';
import type { OrderSide, OrderType } from '@/types/order';

export interface OrderModalProps {
  open: boolean;
  onClose: () => void;
  code: string;
  name?: string;
  /** 기본 매수/매도 */
  defaultSide?: OrderSide;
  /** 시그널/추천에서 추천된 가격 (지정가 기본값) */
  suggestedPrice?: number;
}

/**
 * 주문 모달.
 * - 시그널 상세, 차트 페이지, 추천주 상세에서 재사용.
 * - LIVE 모드에서는 빨간 배너 + 2차 확인 문구.
 * - 실제 주문은 useCreateOrder mutation 호출 (X-Trade-Mode, idempotent 자동).
 */
export function OrderModal({ open, onClose, code, name, defaultSide = 'BUY', suggestedPrice }: OrderModalProps) {
  const mode = useTradeModeStore((s) => s.mode);
  const quote = useQuote(open ? code : undefined);
  const createOrder = useCreateOrder();

  const [side, setSide] = useState<OrderSide>(defaultSide);
  const [orderType, setOrderType] = useState<OrderType>('LIMIT');
  const [qty, setQty] = useState<number>(1);
  const [price, setPrice] = useState<number>(suggestedPrice ?? 0);
  const [confirmStep, setConfirmStep] = useState<'edit' | 'confirm'>('edit');

  useEffect(() => {
    if (open) {
      setSide(defaultSide);
      setQty(1);
      setOrderType('LIMIT');
      setPrice(suggestedPrice ?? quote.data?.price ?? 0);
      setConfirmStep('edit');
    }
  }, [open, defaultSide, suggestedPrice, quote.data?.price]);

  const total = orderType === 'MARKET' && quote.data ? quote.data.price * qty : price * qty;

  async function onSubmit() {
    if (confirmStep === 'edit') {
      setConfirmStep('confirm');
      return;
    }
    await createOrder.mutateAsync({
      code,
      side,
      qty,
      order_type: orderType,
      price: orderType === 'LIMIT' ? price : undefined,
    });
    onClose();
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`${name ?? code} ${side === 'BUY' ? '매수' : '매도'} 주문`}
      danger={mode === 'LIVE'}
      size="md"
      footer={
        <>
          {confirmStep === 'confirm' ? (
            <Button variant="ghost" onClick={() => setConfirmStep('edit')} disabled={createOrder.isPending}>
              뒤로
            </Button>
          ) : (
            <Button variant="ghost" onClick={onClose}>
              취소
            </Button>
          )}
          <Button
            variant={side === 'BUY' ? 'primary' : 'danger'}
            onClick={onSubmit}
            loading={createOrder.isPending}
            disabled={qty <= 0 || (orderType === 'LIMIT' && price <= 0)}
          >
            {confirmStep === 'confirm' ? '주문 전송' : '주문 확인'}
          </Button>
        </>
      }
    >
      <div className="stack gap-4">
        {mode === 'LIVE' && (
          <div className="row gap-2 items-start" style={{ background: 'var(--color-danger-bg)', padding: 'var(--space-3)', borderRadius: 'var(--radius-md)' }}>
            <AlertTriangle className="text-danger h-4 w-4 mt-0.5 flex-none" />
            <p className="text-sm">
              실거래 모드입니다. 주문 전송 시 실제 증권사 계좌에 주문이 접수됩니다.
            </p>
          </div>
        )}

        <div className="row items-center justify-between">
          <div>
            <p className="text-strong fw-semibold">{name ?? '종목'}</p>
            <p className="text-subtle text-xs">{code}</p>
          </div>
          <Badge variant={mode === 'LIVE' ? 'live' : 'sim'} dot>
            {mode === 'LIVE' ? '실거래' : '시뮬'}
          </Badge>
        </div>

        {quote.data && (
          <StatRow
            label="현재가"
            value={
              <span className="text-num">
                {quote.data.price.toLocaleString('ko-KR')}원
              </span>
            }
          />
        )}

        {confirmStep === 'edit' ? (
          <>
            <Field label="구분">
              <RadioGroup<OrderSide>
                name="side"
                value={side}
                onChange={setSide}
                options={[
                  { value: 'BUY', label: '매수' },
                  { value: 'SELL', label: '매도' },
                ]}
              />
            </Field>
            <Field label="주문 유형">
              <RadioGroup<OrderType>
                name="orderType"
                value={orderType}
                onChange={setOrderType}
                options={[
                  { value: 'LIMIT', label: '지정가' },
                  { value: 'MARKET', label: '시장가' },
                ]}
              />
            </Field>
            <Field label="수량 (주)" required>
              <Input
                type="number"
                min={1}
                value={qty}
                onChange={(e) => setQty(Number(e.target.value))}
              />
            </Field>
            {orderType === 'LIMIT' && (
              <Field label="지정가 (원)" required>
                <Input
                  type="number"
                  min={0}
                  value={price}
                  onChange={(e) => setPrice(Number(e.target.value))}
                />
              </Field>
            )}
            <StatRow label="예상 체결금액" value={<span className="text-num fw-semibold">{formatCurrency(total)}</span>} />
          </>
        ) : (
          <div className="stack gap-2">
            <p className="text-sm">아래 내용으로 주문을 전송합니다.</p>
            <StatRow label="구분" value={side === 'BUY' ? '매수' : '매도'} />
            <StatRow label="주문 유형" value={orderType === 'LIMIT' ? `지정가 ${price.toLocaleString('ko-KR')}원` : '시장가'} />
            <StatRow label="수량" value={`${qty.toLocaleString('ko-KR')}주`} />
            <StatRow label="예상 체결금액" value={<span className="fw-semibold text-num">{formatCurrency(total)}</span>} />
          </div>
        )}
      </div>
    </Modal>
  );
}
