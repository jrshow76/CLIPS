package com.tulip.member.domain;

import com.fasterxml.jackson.databind.JsonNode;

import java.time.OffsetDateTime;

/**
 * Outbox 이벤트 (mbr_outbox 매핑).
 *
 * <p>회원 변경 트랜잭션과 같은 커밋 경계에 본 row 가 적재되며,
 * OutboxPublisher 가 폴링하여 Kafka 로 발행한다.</p>
 */
public class OutboxEvent {

    private Long id;
    private Long tenantId;
    private String aggregateType;
    private String aggregateId;
    private String eventType;
    private JsonNode payload;
    private JsonNode headers;
    private String traceId;
    private OffsetDateTime occurredAt;
    private OffsetDateTime publishedAt;
    private Integer retryCount;
    private String status;
    private String lastError;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getTenantId() { return tenantId; }
    public void setTenantId(Long tenantId) { this.tenantId = tenantId; }
    public String getAggregateType() { return aggregateType; }
    public void setAggregateType(String aggregateType) { this.aggregateType = aggregateType; }
    public String getAggregateId() { return aggregateId; }
    public void setAggregateId(String aggregateId) { this.aggregateId = aggregateId; }
    public String getEventType() { return eventType; }
    public void setEventType(String eventType) { this.eventType = eventType; }
    public JsonNode getPayload() { return payload; }
    public void setPayload(JsonNode payload) { this.payload = payload; }
    public JsonNode getHeaders() { return headers; }
    public void setHeaders(JsonNode headers) { this.headers = headers; }
    public String getTraceId() { return traceId; }
    public void setTraceId(String traceId) { this.traceId = traceId; }
    public OffsetDateTime getOccurredAt() { return occurredAt; }
    public void setOccurredAt(OffsetDateTime occurredAt) { this.occurredAt = occurredAt; }
    public OffsetDateTime getPublishedAt() { return publishedAt; }
    public void setPublishedAt(OffsetDateTime publishedAt) { this.publishedAt = publishedAt; }
    public Integer getRetryCount() { return retryCount; }
    public void setRetryCount(Integer retryCount) { this.retryCount = retryCount; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public String getLastError() { return lastError; }
    public void setLastError(String lastError) { this.lastError = lastError; }
}
