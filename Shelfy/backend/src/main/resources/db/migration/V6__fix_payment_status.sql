-- =============================================================================
-- V6: subscription_payments.status 체크 제약 수정
-- Entity(PaymentStatus)는 PENDING/COMPLETED/FAILED 사용
-- DDL은 SUCCESS/FAILED만 허용 → PENDING, COMPLETED 추가
-- =============================================================================
ALTER TABLE subscription_payments DROP CONSTRAINT chk_subscription_payments_status;
ALTER TABLE subscription_payments ADD CONSTRAINT chk_subscription_payments_status
    CHECK (status IN ('PENDING', 'COMPLETED', 'SUCCESS', 'FAILED'));
