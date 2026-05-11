package com.tulip.codepolicy.infra.outbox;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.tulip.codepolicy.config.CodePolicyProperties;
import com.tulip.codepolicy.domain.OutboxEvent;
import com.tulip.codepolicy.infra.mapper.OutboxMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

/**
 * cd_outbox 폴링 → Kafka 발행 워커.
 *
 * <p>토픽: {@code tulip.code.*}, {@code tulip.policy.*}.
 * 이벤트 타입의 prefix(code./policy.) 에 따라 자동 분기한다.</p>
 */
@Component
public class OutboxPublisher {

    private static final Logger log = LoggerFactory.getLogger(OutboxPublisher.class);

    private final OutboxMapper outboxMapper;
    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;
    private final CodePolicyProperties properties;

    public OutboxPublisher(OutboxMapper outboxMapper,
                           KafkaTemplate<String, String> kafkaTemplate,
                           ObjectMapper objectMapper,
                           CodePolicyProperties properties) {
        this.outboxMapper = outboxMapper;
        this.kafkaTemplate = kafkaTemplate;
        this.objectMapper = objectMapper;
        this.properties = properties;
    }

    @Scheduled(fixedDelayString = "${tulip.code-policy.outbox.poll-interval-ms:1000}")
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
                log.debug("cd_outbox 발행 완료 id={} topic={} type={}",
                        event.getId(), topic, event.getEventType());
            } catch (Exception ex) {
                int next = (event.getRetryCount() == null ? 0 : event.getRetryCount()) + 1;
                outboxMapper.markFailed(event.getId(), next, ex.getMessage());
                log.warn("cd_outbox 발행 실패 id={} retry={} cause={}",
                        event.getId(), next, ex.getMessage());
            }
        }
    }

    /**
     * 이벤트 타입을 토픽명으로 변환한다.
     * <ul>
     *   <li>{@code code.added} → {@code tulip.code.added.v1}</li>
     *   <li>{@code policy.created} → {@code tulip.policy.created.v1}</li>
     * </ul>
     */
    private String topicFor(OutboxEvent event) {
        String type = event.getEventType() == null ? "unknown" : event.getEventType();
        int dot = type.indexOf('.');
        if (dot < 0) {
            return "tulip.cdp." + type + ".v1";
        }
        String domain = type.substring(0, dot);
        String action = type.substring(dot + 1).replace('_', '-');
        return "tulip." + domain + "." + action + ".v1";
    }

    private String toJson(JsonNode node) {
        try {
            return node == null ? "{}" : objectMapper.writeValueAsString(node);
        } catch (Exception e) {
            return "{}";
        }
    }
}
