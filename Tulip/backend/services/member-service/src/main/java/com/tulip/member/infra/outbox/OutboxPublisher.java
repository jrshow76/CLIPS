package com.tulip.member.infra.outbox;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.tulip.member.config.MemberProperties;
import com.tulip.member.domain.OutboxEvent;
import com.tulip.member.infra.mapper.OutboxMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

/**
 * mbr_outbox 폴링 → Kafka 발행 워커.
 *
 * <p>polling 주기는 {@code tulip.member.outbox.poll-interval-ms} 로 조정.
 * 본 워커는 단일/다중 인스턴스 모두 안전하다 (SELECT ... FOR UPDATE SKIP LOCKED).</p>
 *
 * <p>토픽 네이밍은 {@code tulip.member.<event-type>.v1} 형식 ({@code 02_service_decomposition.md} §5.2).</p>
 */
@Component
public class OutboxPublisher {

    private static final Logger log = LoggerFactory.getLogger(OutboxPublisher.class);

    private final OutboxMapper outboxMapper;
    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;
    private final MemberProperties properties;

    public OutboxPublisher(OutboxMapper outboxMapper,
                           KafkaTemplate<String, String> kafkaTemplate,
                           ObjectMapper objectMapper,
                           MemberProperties properties) {
        this.outboxMapper = outboxMapper;
        this.kafkaTemplate = kafkaTemplate;
        this.objectMapper = objectMapper;
        this.properties = properties;
    }

    /** 폴링·발행 사이클. 트랜잭션 단위로 한 배치를 처리한다. */
    @Scheduled(fixedDelayString = "${tulip.member.outbox.poll-interval-ms:1000}")
    @Transactional(propagation = Propagation.REQUIRED)
    public void pollAndPublish() {
        List<OutboxEvent> batch = outboxMapper.pollPending(properties.getOutbox().getBatchSize());
        if (batch.isEmpty()) {
            return;
        }
        for (OutboxEvent event : batch) {
            try {
                String topic = topicFor(event);
                String payloadJson = toJson(event.getPayload());
                kafkaTemplate.send(topic, event.getAggregateId(), payloadJson);
                outboxMapper.markPublished(event.getId());
                log.debug("Outbox 발행 완료 id={} topic={} type={}", event.getId(), topic, event.getEventType());
            } catch (Exception ex) {
                int next = (event.getRetryCount() == null ? 0 : event.getRetryCount()) + 1;
                outboxMapper.markFailed(event.getId(), next, ex.getMessage());
                log.warn("Outbox 발행 실패 id={} retry={} cause={}", event.getId(), next, ex.getMessage());
            }
        }
    }

    /** {@code member.registered} → {@code tulip.member.registered.v1} 변환. */
    private String topicFor(OutboxEvent event) {
        String type = event.getEventType() != null ? event.getEventType() : "unknown";
        String suffix = type.contains(".") ? type.substring(type.indexOf('.') + 1) : type;
        return "tulip.member." + suffix.replace('_', '-') + ".v1";
    }

    private String toJson(JsonNode node) {
        try {
            return node == null ? "{}" : objectMapper.writeValueAsString(node);
        } catch (Exception e) {
            return "{}";
        }
    }
}
