-- =============================================================================
-- V5: Entity-DDL 불일치 해소 (BUG-002, BUG-004)
-- =============================================================================

-- [BUG-002] items.status 체크 제약에 'DELETED' 추가
-- Item.softDelete()가 status = DELETED로 변경하는데 기존 제약이 DRAFT/PUBLISHED만 허용
ALTER TABLE items DROP CONSTRAINT chk_items_status;
ALTER TABLE items ADD CONSTRAINT chk_items_status
    CHECK (status IN ('DRAFT', 'PUBLISHED', 'DELETED'));

-- [BUG-004] orders 테이블에 seller_id, content_accessed 컬럼 추가
-- Order 엔티티에 sellerId, contentAccessed 필드가 있으나 DDL에 없었음
ALTER TABLE orders ADD COLUMN seller_id BIGINT;
ALTER TABLE orders ADD COLUMN content_accessed BOOLEAN NOT NULL DEFAULT FALSE;

-- 기존 시드 데이터 orders에 seller_id 채우기 (items 테이블에서 조인)
UPDATE orders o
SET seller_id = i.seller_id
FROM items i
WHERE o.item_id = i.id;

-- [BUG-004] orders.status 체크 제약에 'CANCELLED' 추가
-- Order.OrderStatus 에 CANCELLED가 있으나 기존 제약에 없었음
ALTER TABLE orders DROP CONSTRAINT chk_orders_status;
ALTER TABLE orders ADD CONSTRAINT chk_orders_status
    CHECK (status IN ('PENDING', 'COMPLETED', 'REFUNDED', 'FAILED', 'CANCELLED'));
