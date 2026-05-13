/**
 * 실시간 WebSocket 클라이언트.
 *
 * 책임:
 *  - 단일 채널(/ws/market, /ws/account, /ws/notifications)에 대한 연결 관리
 *  - JWT 자동 부착 (query string `?token=`)
 *  - 자동 재연결 (지수 백오프, 최대 30초)
 *  - heartbeat (30초마다 ping → 서버 pong 미수신 시 재연결)
 *  - 메시지 타입별 listener 등록/해제
 *  - 종목 구독/해제 (market 채널 전용)
 *
 * 사용 예:
 *  const client = new RealtimeClient('/ws/market', () => session.get()?.access_token);
 *  client.connect();
 *  client.on('tick', (msg) => console.log(msg));
 *  client.subscribeStock('005930');
 */

export type RealtimeStatus = 'idle' | 'connecting' | 'open' | 'reconnecting' | 'closed';

export interface RealtimeMessage {
  type: string;
  // 그 외 임의 필드 (각 핸들러에서 좁혀 사용)
  [key: string]: unknown;
}

type Listener<T extends RealtimeMessage = RealtimeMessage> = (msg: T) => void;
type StatusListener = (status: RealtimeStatus) => void;

export interface RealtimeClientOptions {
  /** 채널 경로 ("/ws/market" 등) */
  path: string;
  /** 토큰 조회 함수 (호출 시점 최신 토큰을 반환) */
  getToken: () => string | undefined;
  /** WS base URL (없으면 location 기반 자동) */
  baseUrl?: string;
  /** heartbeat 주기 ms (기본 30s) */
  heartbeatIntervalMs?: number;
  /** pong 타임아웃 ms (heartbeatIntervalMs의 2배 권장, 기본 70s) */
  pongTimeoutMs?: number;
  /** 최초 백오프 지연 ms (기본 1s) */
  backoffStartMs?: number;
  /** 최대 백오프 지연 ms (기본 30s) */
  backoffMaxMs?: number;
}

const DEFAULT_HEARTBEAT_MS = 30_000;
const DEFAULT_PONG_TIMEOUT_MS = 70_000;
const DEFAULT_BACKOFF_START_MS = 1_000;
const DEFAULT_BACKOFF_MAX_MS = 30_000;

/** WS base URL 결정. NEXT_PUBLIC_WS_BASE_URL 우선, 없으면 location 기반. */
export function resolveWsBaseUrl(): string {
  const env = process.env.NEXT_PUBLIC_WS_BASE_URL;
  if (env && env.length > 0) return env;
  if (typeof window === 'undefined') return 'ws://localhost:8000';
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.host}`;
}

export class RealtimeClient {
  private ws: WebSocket | null = null;
  private status: RealtimeStatus = 'idle';
  private statusListeners = new Set<StatusListener>();
  private listeners = new Map<string, Set<Listener>>();
  private subscribedStocks = new Set<string>();

  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private pongTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private retryCount = 0;
  /** 외부 close() 호출 여부 - true면 재연결 시도 안 함 */
  private explicitlyClosed = false;

  private readonly heartbeatMs: number;
  private readonly pongTimeoutMs: number;
  private readonly backoffStartMs: number;
  private readonly backoffMaxMs: number;
  private readonly baseUrl: string;

  constructor(private readonly opts: RealtimeClientOptions) {
    this.heartbeatMs = opts.heartbeatIntervalMs ?? DEFAULT_HEARTBEAT_MS;
    this.pongTimeoutMs = opts.pongTimeoutMs ?? DEFAULT_PONG_TIMEOUT_MS;
    this.backoffStartMs = opts.backoffStartMs ?? DEFAULT_BACKOFF_START_MS;
    this.backoffMaxMs = opts.backoffMaxMs ?? DEFAULT_BACKOFF_MAX_MS;
    this.baseUrl = opts.baseUrl ?? resolveWsBaseUrl();
  }

  // --------------------------------------------------------------
  // 라이프사이클
  // --------------------------------------------------------------
  /** 연결 시도. 토큰이 없으면 idle 유지. */
  connect(): void {
    if (typeof window === 'undefined') return; // SSR 가드
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }
    const token = this.opts.getToken();
    if (!token) {
      this.setStatus('idle');
      return;
    }
    this.explicitlyClosed = false;
    this.setStatus(this.retryCount > 0 ? 'reconnecting' : 'connecting');

    const url = `${this.baseUrl}${this.opts.path}?token=${encodeURIComponent(token)}`;
    let ws: WebSocket;
    try {
      ws = new WebSocket(url);
    } catch (e) {
      console.error('[realtime] WebSocket constructor failed', e);
      this.scheduleReconnect();
      return;
    }
    this.ws = ws;

    ws.onopen = () => {
      this.retryCount = 0;
      this.setStatus('open');
      this.startHeartbeat();
      // 재연결 시 기존 종목 자동 재구독 (market 채널)
      if (this.subscribedStocks.size > 0) {
        this.send({ type: 'subscribe', stock_codes: Array.from(this.subscribedStocks) });
      }
    };

    ws.onmessage = (ev) => {
      this.handleMessage(ev.data);
    };

    ws.onerror = () => {
      // onclose가 곧 호출되므로 여기서는 로그만
      // (브라우저는 보안상 상세 에러 노출 안 함)
    };

    ws.onclose = (ev) => {
      this.cleanupTimers();
      this.ws = null;
      // 정책 위반(1008) 등 영구 실패 코드는 재시도 안 함
      if (this.explicitlyClosed || ev.code === 1008) {
        this.setStatus('closed');
        return;
      }
      this.scheduleReconnect();
    };
  }

  /** 명시적 종료. 재연결 안 함. */
  close(): void {
    this.explicitlyClosed = true;
    this.cleanupTimers();
    if (this.ws) {
      try {
        this.ws.close(1000, 'client closed');
      } catch {
        // ignore
      }
      this.ws = null;
    }
    this.setStatus('closed');
  }

  // --------------------------------------------------------------
  // 메시지 송신
  // --------------------------------------------------------------
  send(payload: Record<string, unknown>): boolean {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return false;
    try {
      this.ws.send(JSON.stringify(payload));
      return true;
    } catch (e) {
      console.error('[realtime] send failed', e);
      return false;
    }
  }

  // --------------------------------------------------------------
  // 종목 구독 (market 채널 전용)
  // --------------------------------------------------------------
  subscribeStock(code: string): void {
    if (this.subscribedStocks.has(code)) return;
    this.subscribedStocks.add(code);
    if (this.status === 'open') {
      this.send({ type: 'subscribe', stock_codes: [code] });
    }
  }

  unsubscribeStock(code: string): void {
    if (!this.subscribedStocks.has(code)) return;
    this.subscribedStocks.delete(code);
    if (this.status === 'open') {
      this.send({ type: 'unsubscribe', stock_codes: [code] });
    }
  }

  getSubscribedStocks(): string[] {
    return Array.from(this.subscribedStocks);
  }

  // --------------------------------------------------------------
  // 리스너
  // --------------------------------------------------------------
  on<T extends RealtimeMessage>(type: string, listener: Listener<T>): () => void {
    let set = this.listeners.get(type);
    if (!set) {
      set = new Set();
      this.listeners.set(type, set);
    }
    set.add(listener as Listener);
    return () => {
      this.listeners.get(type)?.delete(listener as Listener);
    };
  }

  onStatus(listener: StatusListener): () => void {
    this.statusListeners.add(listener);
    listener(this.status);
    return () => this.statusListeners.delete(listener);
  }

  getStatus(): RealtimeStatus {
    return this.status;
  }

  // --------------------------------------------------------------
  // 내부
  // --------------------------------------------------------------
  private handleMessage(raw: string | ArrayBuffer | Blob): void {
    if (typeof raw !== 'string') {
      // 서버는 send_bytes를 사용하므로 ArrayBuffer로 올 수 있음
      if (raw instanceof ArrayBuffer) {
        raw = new TextDecoder().decode(raw);
      } else {
        return;
      }
    }
    let msg: RealtimeMessage;
    try {
      msg = JSON.parse(raw) as RealtimeMessage;
    } catch {
      return;
    }
    if (msg.type === 'pong') {
      this.clearPongTimeout();
      return;
    }
    const set = this.listeners.get(msg.type);
    if (set) {
      for (const listener of set) {
        try {
          listener(msg);
        } catch (e) {
          console.error('[realtime] listener error', e);
        }
      }
    }
  }

  private setStatus(status: RealtimeStatus): void {
    if (this.status === status) return;
    this.status = status;
    for (const l of this.statusListeners) {
      try {
        l(status);
      } catch {
        // ignore
      }
    }
  }

  private startHeartbeat(): void {
    this.cleanupTimers();
    this.heartbeatTimer = setInterval(() => {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
      this.send({ type: 'ping', ts: new Date().toISOString() });
      // pong 타임아웃 시작
      this.pongTimer = setTimeout(() => {
        console.warn('[realtime] pong timeout, forcing reconnect');
        try {
          this.ws?.close(4000, 'pong timeout');
        } catch {
          // ignore
        }
      }, this.pongTimeoutMs);
    }, this.heartbeatMs);
  }

  private clearPongTimeout(): void {
    if (this.pongTimer) {
      clearTimeout(this.pongTimer);
      this.pongTimer = null;
    }
  }

  private cleanupTimers(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
    this.clearPongTimeout();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private scheduleReconnect(): void {
    this.retryCount += 1;
    // 지수 백오프 + 0~500ms 지터
    const base = Math.min(this.backoffStartMs * 2 ** (this.retryCount - 1), this.backoffMaxMs);
    const jitter = Math.floor(Math.random() * 500);
    const delay = base + jitter;
    this.setStatus('reconnecting');
    this.reconnectTimer = setTimeout(() => this.connect(), delay);
  }
}
