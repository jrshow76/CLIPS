-- =============================================================================
-- TradePilot 데이터 정합성 점검 쿼리 모음
--
-- 매일 16:30 (장 종료 후 30분) 자동 실행. 모든 쿼리는 결과가 0건이어야 정상.
-- 결과 1건 이상 → 즉시 알림 + RCA.
--
-- 실행:
--   psql $DATABASE_URL -v ON_ERROR_STOP=1 -f scripts/data_consistency_check.sql
--
-- 참고:
--   - 본 쿼리는 운영 DB 스키마를 가정한다.
--   - 일부 컬럼/테이블 이름이 다를 경우 운영 환경에 맞게 조정한다.
-- =============================================================================

\timing on
\echo '=========================================='
\echo 'TradePilot Data Consistency Check'
\echo '=========================================='


-- -----------------------------------------------------------------------------
-- 1. 주문-체결 수량 일치
--    FILLED 주문은 체결 합계 == 주문 수량.
--    PARTIALLY_FILLED 는 체결 합계 < 주문 수량.
-- -----------------------------------------------------------------------------
\echo '--- 1. 주문-체결 수량 불일치 (정상: 0건) ---'
SELECT o.id AS order_id,
       o.user_id,
       o.stock_code,
       o.qty AS order_qty,
       COALESCE(SUM(e.qty), 0) AS executed_qty,
       o.status,
       o.created_at
  FROM orders o
  LEFT JOIN executions e ON e.order_id = o.id
 WHERE o.created_at::date = CURRENT_DATE
   AND (
        (o.status = 'FILLED' AND COALESCE(SUM(e.qty), 0) <> o.qty)
     OR (o.status = 'PARTIALLY_FILLED' AND COALESCE(SUM(e.qty), 0) >= o.qty)
     OR (COALESCE(SUM(e.qty), 0) > o.qty)
   )
 GROUP BY o.id, o.user_id, o.stock_code, o.qty, o.status, o.created_at
 ORDER BY o.created_at;


-- -----------------------------------------------------------------------------
-- 2. 일일 PnL 정합성
--    체결 기반 realized + 포지션 평가 unrealized == daily_pnl 테이블의 reported
-- -----------------------------------------------------------------------------
\echo '--- 2. 일일 PnL 불일치 (정상: 0건, 임계: 1원) ---'
WITH realized AS (
  SELECT user_id,
         SUM(CASE WHEN side = 'SELL' THEN qty * price ELSE -qty * price END)
           - COALESCE(SUM(fee + tax), 0) AS realized_pnl
    FROM executions
   WHERE ts::date = CURRENT_DATE
   GROUP BY user_id
),
eval AS (
  SELECT user_id, SUM(eval_pnl) AS unrealized_pnl
    FROM positions
   WHERE updated_at::date = CURRENT_DATE
   GROUP BY user_id
)
SELECT u.id,
       u.email,
       COALESCE(r.realized_pnl, 0) AS realized,
       COALESCE(e.unrealized_pnl, 0) AS unrealized,
       d.daily_pnl AS reported,
       (COALESCE(r.realized_pnl, 0) + COALESCE(e.unrealized_pnl, 0)) - d.daily_pnl AS diff
  FROM users u
  LEFT JOIN realized r ON r.user_id = u.id
  LEFT JOIN eval e ON e.user_id = u.id
  LEFT JOIN daily_pnl d ON d.user_id = u.id AND d.date = CURRENT_DATE
 WHERE ABS(
        (COALESCE(r.realized_pnl, 0) + COALESCE(e.unrealized_pnl, 0))
        - COALESCE(d.daily_pnl, 0)
       ) > 1.0
 ORDER BY ABS(
        (COALESCE(r.realized_pnl, 0) + COALESCE(e.unrealized_pnl, 0))
        - COALESCE(d.daily_pnl, 0)
       ) DESC;


-- -----------------------------------------------------------------------------
-- 3. 모드 일관성: 사용자 trade_mode와 주문 trade_mode 일치
-- -----------------------------------------------------------------------------
\echo '--- 3. 모드 불일치 (정상: 0건) ---'
SELECT u.id,
       u.email,
       u.trade_mode AS user_mode,
       o.trade_mode AS order_mode,
       COUNT(*) AS mismatch_count
  FROM users u
  JOIN orders o ON o.user_id = u.id
 WHERE o.created_at::date = CURRENT_DATE
   AND u.trade_mode <> o.trade_mode
 GROUP BY u.id, u.email, u.trade_mode, o.trade_mode
 ORDER BY mismatch_count DESC;


-- -----------------------------------------------------------------------------
-- 4. 장 종료 후 미체결 주문 잔여 (정상: 0건)
-- -----------------------------------------------------------------------------
\echo '--- 4. 미체결 잔여 (정상: 0건, 장 종료 후) ---'
SELECT id, user_id, stock_code, side, qty, price, status, created_at
  FROM orders
 WHERE status IN ('PENDING', 'ACCEPTED', 'PARTIALLY_FILLED')
   AND created_at::date = CURRENT_DATE
 ORDER BY created_at;


-- -----------------------------------------------------------------------------
-- 5. 한도 위반 주문 (정상: 0건)
--    Risk Guard 가 차단했어야 할 주문이 실제로 발주된 경우
-- -----------------------------------------------------------------------------
\echo '--- 5. 한도 위반 주문 (정상: 0건) ---'
WITH daily_buy AS (
  SELECT user_id,
         SUM(CASE WHEN side = 'BUY' THEN qty * price ELSE 0 END) AS total_buy
    FROM orders
   WHERE created_at::date = CURRENT_DATE
     AND status NOT IN ('REJECTED', 'CANCELED')
   GROUP BY user_id
)
SELECT d.user_id,
       u.email,
       d.total_buy,
       l.daily_buy_amount_max,
       d.total_buy - l.daily_buy_amount_max AS over_amount
  FROM daily_buy d
  JOIN users u ON u.id = d.user_id
  JOIN risk_limits l ON l.user_id = d.user_id
 WHERE d.total_buy > l.daily_buy_amount_max
 ORDER BY over_amount DESC;


-- -----------------------------------------------------------------------------
-- 6. 게이트웨이 발주 vs DB 주문 수 차이 (직전 7일)
--    audit_log.action = 'gateway_order_submit' 와 orders 테이블 비교
-- -----------------------------------------------------------------------------
\echo '--- 6. 게이트웨이 발주 vs DB 주문 수 (정상: diff=0) ---'
WITH gw AS (
  SELECT created_at::date AS d, COUNT(*) AS gw_count
    FROM audit_log
   WHERE action = 'gateway_order_submit'
     AND created_at::date >= CURRENT_DATE - 7
   GROUP BY 1
),
db AS (
  SELECT created_at::date AS d, COUNT(*) AS db_count
    FROM orders
   WHERE trade_mode = 'LIVE'
     AND created_at::date >= CURRENT_DATE - 7
   GROUP BY 1
)
SELECT COALESCE(gw.d, db.d) AS d,
       COALESCE(gw.gw_count, 0) AS gw_count,
       COALESCE(db.db_count, 0) AS db_count,
       COALESCE(gw.gw_count, 0) - COALESCE(db.db_count, 0) AS diff
  FROM gw
  FULL OUTER JOIN db ON gw.d = db.d
 WHERE COALESCE(gw.gw_count, 0) <> COALESCE(db.db_count, 0)
 ORDER BY d DESC;


-- -----------------------------------------------------------------------------
-- 7. 체결가 이상치 (현재가 대비 ±10% 이상)
--    슬리피지 모니터링용. 0건이 정상.
-- -----------------------------------------------------------------------------
\echo '--- 7. 체결가 이상치 (정상: 0건, 임계: ±10%) ---'
SELECT e.id,
       e.order_id,
       e.code,
       e.price AS exec_price,
       q.price AS quote_price_at_exec,
       (e.price - q.price) / NULLIF(q.price, 0) * 100 AS deviation_pct
  FROM executions e
  LEFT JOIN LATERAL (
        SELECT price
          FROM quotes q
         WHERE q.code = e.code AND q.ts <= e.ts
         ORDER BY q.ts DESC LIMIT 1
  ) q ON TRUE
 WHERE e.ts::date = CURRENT_DATE
   AND ABS((e.price - q.price) / NULLIF(q.price, 0)) > 0.1
 ORDER BY deviation_pct DESC;


-- -----------------------------------------------------------------------------
-- 8. Kill Switch 발동 이력 (참고용 로그)
-- -----------------------------------------------------------------------------
\echo '--- 8. Kill Switch 발동 이력 (참고) ---'
SELECT created_at, user_id, action, details
  FROM audit_log
 WHERE action LIKE 'kill_switch%'
   AND created_at::date = CURRENT_DATE
 ORDER BY created_at;


\echo '=========================================='
\echo 'Data Consistency Check 완료'
\echo '=========================================='
