// TradePilot WebSocket 부하 테스트 (k6)
//
// 시나리오:
//   - 동시 1,000개 WebSocket 연결을 1분간 ramp-up 후 5분 유지.
//   - 각 연결이 종목 구독(subscribe) 메시지를 보내고 ping/pong 유지.
//   - nginx 프록시(proxy_read_timeout=3600s) + WS upgrade 안정성 검증.
//
// 실행:
//   BASE_URL=wss://tradepilot.example.com TOKEN=eyJ... \
//   k6 run k6_ws_burst.js
//
// 사전 조건:
//   - JWT 토큰 (TOKEN 환경변수)
//   - /ws/market 엔드포인트 활성
//   - nginx Rate Limit (zn_ws=20r/s, burst 40) 고려: ramp-up 충분히 완만하게
//
// 합격 기준:
//   - 연결 성공률 ≥ 98%
//   - 핸드셰이크 P95 < 1500ms
//   - 끊김(자발적 close 제외) ≤ 1%
//   - nginx 5xx, 429 발생 0

import ws from 'k6/ws';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'wss://tradepilot.example.com';
const TOKEN = __ENV.TOKEN || '';
const HOLD_SEC = parseInt(__ENV.HOLD_SEC || '300', 10); // 각 VU 가 연결 유지하는 시간(초)

// ---- 메트릭 ----
const wsConnectErrors = new Counter('ws_connect_errors');
const wsConnectSuccess = new Rate('ws_connect_success');
const wsHandshake = new Trend('ws_handshake_ms', true);
const wsMessages = new Counter('ws_messages_received');
const wsUnexpectedClose = new Counter('ws_unexpected_close');

export const options = {
  scenarios: {
    // 동시 1,000 연결을 천천히 채운 뒤 일정시간 유지.
    // ramp-up 60s 동안 1,000 → ~16 conn/s (zn_ws=20r/s 한도 미만).
    ws_connections: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '60s', target: 1000 }, // ramp-up
        { duration: '5m',  target: 1000 }, // 유지
        { duration: '30s', target: 0 },    // 정리
      ],
      gracefulRampDown: '30s',
    },
  },
  thresholds: {
    'ws_connect_success': ['rate>0.98'],
    'ws_handshake_ms':    ['p(95)<1500', 'p(99)<3000'],
    'ws_unexpected_close':['count<10'],
  },
};

// 구독 종목 풀 (라운드로빈)
const STOCKS = ['005930', '000660', '035420', '035720', '051910',
                '005380', '068270', '207940', '105560', '055550'];

export default function () {
  const code = STOCKS[__VU % STOCKS.length];
  const url = `${BASE_URL}/ws/market?token=${encodeURIComponent(TOKEN)}`;
  const params = {
    headers: {
      'Origin': BASE_URL.replace(/^wss?:/, 'https:'),
      'X-Test-Run': 'k6_ws_burst',
    },
    tags: { stream: 'market' },
  };

  const startTs = Date.now();
  const res = ws.connect(url, params, function (socket) {
    wsHandshake.add(Date.now() - startTs);
    wsConnectSuccess.add(true);

    // 1) 구독
    socket.on('open', () => {
      socket.send(JSON.stringify({
        type: 'subscribe',
        channels: ['quote', 'orderbook'],
        codes: [code],
      }));
    });

    // 2) 메시지 수신 카운트
    socket.on('message', () => {
      wsMessages.add(1);
    });

    // 3) ping (서버가 알아서 보내지만, 클라이언트도 keepalive 메시지 전송)
    socket.setInterval(() => {
      try {
        socket.send(JSON.stringify({ type: 'ping', ts: Date.now() }));
      } catch (e) { /* socket 닫힌 직후 */ }
    }, 30 * 1000);

    // 4) 비정상 종료 감지
    socket.on('close', (code) => {
      // 1000(정상), 1001(going away)가 아닌 경우만 비정상
      if (code !== 1000 && code !== 1001) {
        wsUnexpectedClose.add(1);
      }
    });

    socket.on('error', (e) => {
      wsConnectErrors.add(1);
    });

    // 5) HOLD_SEC 동안 연결 유지 후 정상 종료
    socket.setTimeout(() => socket.close(1000, 'test_done'), HOLD_SEC * 1000);
  });

  const ok = check(res, {
    'ws status 101 (switching protocols)': (r) => r && r.status === 101,
  });
  if (!ok) {
    wsConnectSuccess.add(false);
    wsConnectErrors.add(1);
  }
}

export function handleSummary(data) {
  const m = data.metrics;
  const get = (k, sub = 'count') => (m[k] && m[k].values && m[k].values[sub]) || 0;
  return {
    'reports/k6_ws_summary.json': JSON.stringify(data, null, 2),
    stdout: `
=== WebSocket 부하 테스트 결과 ===
연결 시도        : ${get('vus_max', 'value')} (max VUs)
핸드셰이크 P95   : ${(get('ws_handshake_ms', 'p(95)') || 0).toFixed(1)} ms
핸드셰이크 P99   : ${(get('ws_handshake_ms', 'p(99)') || 0).toFixed(1)} ms
연결 성공률      : ${((get('ws_connect_success', 'rate') || 0) * 100).toFixed(2)} %
수신 메시지 수   : ${get('ws_messages_received')}
비정상 종료 수   : ${get('ws_unexpected_close')}
연결 에러 수     : ${get('ws_connect_errors')}
==================================
`,
  };
}
