package com.tulip.tenant.outbox;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.tulip.common.core.trace.TraceContext;
import com.tulip.tenant.error.TenantErrorCode;
import com.tulip.tenant.infra.mapper.OutboxMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

/**
 * 트랜잭션 내에서 {@code tnt_outbox} 행을 적재하는 헬퍼.
 *
 * <p>{@link OutboxAppender#append} 는 호출자의 트랜잭션과 동일한 단위로 실행되어야 한다.
 * 즉, 비즈니스 변경과 outbox INSERT 가 같이 commit / rollback 되어야 원자성이 보장된다.</p>
 *
 * <p>payload 는 임의 객체(보통 record)를 받아 Jackson 으로 직렬화한다.
 * traceId 는 MDC ({@link TraceContext#MDC_TRACE_ID}) 에서 자동 수집한다.</p>
 */
@Component
public class OutboxAppender {

    private static final Logger log = LoggerFactory.getLogger(OutboxAppender.class);

    private final OutboxMapper mapper;
    private final ObjectMapper objectMapper;

    public OutboxAppender(OutboxMapper mapper, ObjectMapper objectMapper) {
        this.mapper = mapper;
        this.objectMapper = objectMapper;
    }

    /**
     * 새 outbox 행을 적재한다.
     *
     * @param aggregateType  도메인 집합체 타입 (예: "tenant", "library")
     * @param aggregateId    집합체 식별자 (publicId/ULID 권장)
     * @param eventType      이벤트 타입 (예: "tenant.created")
     * @param payload        직렬화 가능한 payload 객체 (record 권장)
     * @param tenantId       테넌트 식별자 (시스템 이벤트일 경우 null 허용 — SYS_ADMIN 컨텍스트 필요)
     */
    @Transactional(propagation = Propagation.MANDATORY)
    public OutboxEntry append(String aggregateType, String aggregateId, String eventType,
                              Object payload, Long tenantId) {
        String payloadJson;
        try {
            payloadJson = objectMapper.writeValueAsString(payload);
        } catch (JsonProcessingException e) {
            log.error("outbox payload 직렬화 실패 eventType={}", eventType, e);
            throw new IllegalStateException(TenantErrorCode.OUTBOX_PUBLISH_FAILED.defaultMessage(), e);
        }
        String traceId = MDC.get(TraceContext.MDC_TRACE_ID);
        OutboxEntry entry = OutboxEntry.of(aggregateType, aggregateId, eventType, payloadJson, tenantId, traceId);
        mapper.insert(entry);
        log.debug("outbox append id={} type={} aggregate={}/{}",
                entry.getId(), eventType, aggregateType, aggregateId);
        return entry;
    }
}
