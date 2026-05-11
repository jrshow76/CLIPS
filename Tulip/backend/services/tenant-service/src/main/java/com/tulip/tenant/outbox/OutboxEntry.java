package com.tulip.tenant.outbox;

import java.time.OffsetDateTime;

/**
 * tnt_outbox 도메인 객체.
 *
 * <p>Outbox 패턴 (Sprint 1-C.7) — 트랜잭션 commit 과 동일 단위로 적재되며,
 * {@link OutboxPoller} 가 PENDING -> PROCESSING -> COMPLETED 로 전이시킨다.</p>
 */
public class OutboxEntry {

    /** 처리 상태. DBA CHECK 제약과 동일. */
    public enum Status {
        PENDING,
        PROCESSING,
        COMPLETED,
        FAILED;
    }

    private Long id;
    private String aggregateType;
    private String aggregateId;
    private String eventType;
    private String payload;
    private Long tenantId;
    private OffsetDateTime occurredAt;
    private OffsetDateTime processedAt;
    private int retryCount;
    private Status status;
    private String lastError;
    private String traceId;

    public OutboxEntry() {
    }

    public static OutboxEntry of(String aggregateType, String aggregateId, String eventType,
                                 String payload, Long tenantId, String traceId) {
        OutboxEntry e = new OutboxEntry();
        e.aggregateType = aggregateType;
        e.aggregateId = aggregateId;
        e.eventType = eventType;
        e.payload = payload;
        e.tenantId = tenantId;
        e.occurredAt = OffsetDateTime.now();
        e.status = Status.PENDING;
        e.retryCount = 0;
        e.traceId = traceId;
        return e;
    }

    // getter/setter
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getAggregateType() { return aggregateType; }
    public void setAggregateType(String aggregateType) { this.aggregateType = aggregateType; }
    public String getAggregateId() { return aggregateId; }
    public void setAggregateId(String aggregateId) { this.aggregateId = aggregateId; }
    public String getEventType() { return eventType; }
    public void setEventType(String eventType) { this.eventType = eventType; }
    public String getPayload() { return payload; }
    public void setPayload(String payload) { this.payload = payload; }
    public Long getTenantId() { return tenantId; }
    public void setTenantId(Long tenantId) { this.tenantId = tenantId; }
    public OffsetDateTime getOccurredAt() { return occurredAt; }
    public void setOccurredAt(OffsetDateTime occurredAt) { this.occurredAt = occurredAt; }
    public OffsetDateTime getProcessedAt() { return processedAt; }
    public void setProcessedAt(OffsetDateTime processedAt) { this.processedAt = processedAt; }
    public int getRetryCount() { return retryCount; }
    public void setRetryCount(int retryCount) { this.retryCount = retryCount; }
    public Status getStatus() { return status; }
    public void setStatus(Status status) { this.status = status; }
    public String getLastError() { return lastError; }
    public void setLastError(String lastError) { this.lastError = lastError; }
    public String getTraceId() { return traceId; }
    public void setTraceId(String traceId) { this.traceId = traceId; }
}
