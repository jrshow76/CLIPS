'use client';

import { useEffect, useState } from 'react';

import {
  getAccountClient,
  getMarketClient,
  getNotificationsClient,
  type RealtimeStatus,
} from '@/lib/realtime';

export interface RealtimeOverallStatus {
  market: RealtimeStatus;
  account: RealtimeStatus;
  notifications: RealtimeStatus;
  /** 모든 채널이 open이면 true */
  allOpen: boolean;
  /** 어느 하나라도 reconnecting/connecting이면 true */
  anyConnecting: boolean;
}

const INITIAL: RealtimeOverallStatus = {
  market: 'idle',
  account: 'idle',
  notifications: 'idle',
  allOpen: false,
  anyConnecting: false,
};

/** 헤더 인디케이터 등에서 사용할 종합 상태. */
export function useRealtimeStatus(): RealtimeOverallStatus {
  const [s, setS] = useState<RealtimeOverallStatus>(INITIAL);

  useEffect(() => {
    const market = getMarketClient();
    const account = getAccountClient();
    const noti = getNotificationsClient();

    const update = () => {
      const m = market.getStatus();
      const a = account.getStatus();
      const n = noti.getStatus();
      setS({
        market: m,
        account: a,
        notifications: n,
        allOpen: m === 'open' && a === 'open' && n === 'open',
        anyConnecting: [m, a, n].some((x) => x === 'connecting' || x === 'reconnecting'),
      });
    };

    const offM = market.onStatus(update);
    const offA = account.onStatus(update);
    const offN = noti.onStatus(update);
    return () => {
      offM();
      offA();
      offN();
    };
  }, []);

  return s;
}
