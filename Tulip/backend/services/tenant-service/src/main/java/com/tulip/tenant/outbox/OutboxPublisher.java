package com.tulip.tenant.outbox;

import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.header.internals.RecordHeader;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.support.SendResult;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.util.concurrent.CompletableFuture;

/**
 * Outbox 행을 Kafka 토픽으로 전송하는 어댑터.
 *
 * <p>토픽 명명 규칙: {@code tulip.tenant.{aggregateType}.{event}} —
 * 예) {@code tulip.tenant.tenant.created}, {@code tulip.tenant.library.deleted}.</p>
 *
 * <p>전송 헤더에 {@code traceId}, {@code tenantId}, {@code eventType} 을 부착하여
 * 컨슈머가 컨텍스트를 복원할 수 있도록 한다.</p>
 */
@Component
public class OutboxPublisher {

    private static final Logger log = LoggerFactory.getLogger(OutboxPublisher.class);

    public static final String TOPIC_PREFIX = "tulip.tenant.";

    private final KafkaTemplate<String, String> kafkaTemplate;

    public OutboxPublisher(KafkaTemplate<String, String> kafkaTemplate) {
        this.kafkaTemplate = kafkaTemplate;
    }

    /** {@link OutboxEntry} 를 Kafka 로 발행. 동기 대기 — 성공 시 정상 반환. */
    public void publish(OutboxEntry entry) {
        String topic = resolveTopic(entry);
        String key = entry.getAggregateId();

        ProducerRecord<String, String> record = new ProducerRecord<>(topic, key, entry.getPayload());
        if (entry.getTraceId() != null) {
            record.headers().add(new RecordHeader("traceId",
                    entry.getTraceId().getBytes(StandardCharsets.UTF_8)));
        }
        if (entry.getTenantId() != null) {
            record.headers().add(new RecordHeader("tenantId",
                    entry.getTenantId().toString().getBytes(StandardCharsets.UTF_8)));
        }
        if (entry.getEventType() != null) {
            record.headers().add(new RecordHeader("eventType",
                    entry.getEventType().getBytes(StandardCharsets.UTF_8)));
        }

        CompletableFuture<SendResult<String, String>> future = kafkaTemplate.send(record);
        // 동기 대기 — Poller 가 결과에 따라 outbox 상태를 전이시키므로 예외는 위로 던진다.
        SendResult<String, String> result = future.join();
        log.debug("outbox publish topic={} partition={} offset={} key={} eventType={}",
                topic,
                result.getRecordMetadata().partition(),
                result.getRecordMetadata().offset(),
                key,
                entry.getEventType());
    }

    /** "tenant.created" -> "tulip.tenant.tenant.created" */
    public String resolveTopic(OutboxEntry entry) {
        return TOPIC_PREFIX + entry.getAggregateType() + "." + extractEventName(entry.getEventType());
    }

    private String extractEventName(String eventType) {
        if (eventType == null) {
            return "unknown";
        }
        int idx = eventType.indexOf('.');
        return idx >= 0 ? eventType.substring(idx + 1) : eventType;
    }
}
