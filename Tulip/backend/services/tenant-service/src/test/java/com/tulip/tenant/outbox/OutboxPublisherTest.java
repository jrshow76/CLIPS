package com.tulip.tenant.outbox;

import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.kafka.core.KafkaTemplate;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * OutboxPublisher 의 토픽 명명 규칙 단위 테스트.
 */
class OutboxPublisherTest {

    @SuppressWarnings("unchecked")
    private final KafkaTemplate<String, String> template = Mockito.mock(KafkaTemplate.class);
    private final OutboxPublisher publisher = new OutboxPublisher(template);

    @Test
    void 토픽_명명규칙은_tulip_tenant_aggregate_event_이다() {
        OutboxEntry e = OutboxEntry.of("tenant", "01HXYZ", "tenant.created", "{}", 1L, "trace-1");
        assertThat(publisher.resolveTopic(e)).isEqualTo("tulip.tenant.tenant.created");

        OutboxEntry e2 = OutboxEntry.of("library_branch", "01HABC", "library_branch.updated", "{}", 1L, null);
        assertThat(publisher.resolveTopic(e2)).isEqualTo("tulip.tenant.library_branch.updated");
    }
}
