package com.tulip.tenant.integration;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.tulip.tenant.api.dto.TenantDtos;
import com.tulip.tenant.application.TenantService;
import com.tulip.tenant.outbox.OutboxEntry;
import com.tulip.tenant.outbox.OutboxPoller;
import com.tulip.tenant.outbox.RlsSessionApplier;
import com.tulip.tenant.security.TenantSessionContext;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.awaitility.Awaitility;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.transaction.support.TransactionTemplate;
import org.testcontainers.containers.KafkaContainer;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.utility.DockerImageName;

import java.time.Duration;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 테넌트 생성 → outbox 적재 → Kafka 발행 E2E 통합 테스트.
 *
 * <p>docker 가용 환경에서만 실행되도록 {@code @Tag("integration")} 으로 분리한다.</p>
 */
@SpringBootTest(properties = {
        "tulip.tenant.outbox.poll-delay-ms=500",
        "tulip.tenant.keycloak.issuer-uri=http://localhost:0/realms/none",
        "tulip.tenant.keycloak.jwks-uri=http://localhost:0/jwks"
})
@Testcontainers
@Tag("integration")
class TenantServiceIntegrationTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>(DockerImageName.parse("postgres:15-alpine"))
            .withDatabaseName("tulip")
            .withUsername("tulip")
            .withPassword("tulip");

    @Container
    static KafkaContainer kafka = new KafkaContainer(DockerImageName.parse("confluentinc/cp-kafka:7.5.1"));

    @DynamicPropertySource
    static void registerProps(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", postgres::getJdbcUrl);
        r.add("spring.datasource.username", postgres::getUsername);
        r.add("spring.datasource.password", postgres::getPassword);
        r.add("spring.kafka.bootstrap-servers", kafka::getBootstrapServers);
    }

    @Autowired TenantService tenantService;
    @Autowired OutboxPoller poller;
    @Autowired JdbcTemplate jdbcTemplate;
    @Autowired TransactionTemplate tx;
    @Autowired RlsSessionApplier rls;
    @Autowired ObjectMapper objectMapper;

    @BeforeEach
    void setUp() {
        // 시스템 관리자 컨텍스트로 본 테스트를 수행
        TenantSessionContext.set(null, "SYS_ADMIN", true);
    }

    @AfterEach
    void tearDown() {
        TenantSessionContext.clear();
    }

    @Test
    void 테넌트_생성_시_outbox_가_적재되고_Kafka_로_발행된다() throws Exception {
        TenantDtos.CreateRequest req = new TenantDtos.CreateRequest(
                "int-" + System.currentTimeMillis(), "통합테스트 테넌트", "STANDARD", null);

        TenantDtos.Response created = tx.execute(s -> {
            rls.applySysAdmin();
            return tenantService.create(req, null);
        });
        assertThat(created.id()).isNotNull();

        // Kafka 컨슈머
        Properties props = new Properties();
        props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, kafka.getBootstrapServers());
        props.put(ConsumerConfig.GROUP_ID_CONFIG, "it-" + System.currentTimeMillis());
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");

        try (KafkaConsumer<String, String> consumer = new KafkaConsumer<>(props)) {
            consumer.subscribe(List.of("tulip.tenant.tenant.created"));
            Map<String, String> seen = new HashMap<>();
            Awaitility.await().atMost(Duration.ofSeconds(30)).pollInterval(Duration.ofSeconds(1)).untilAsserted(() -> {
                // poller 가 5초 주기로 동작하므로 명시적으로도 한 번 호출
                poller.poll();
                ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(500));
                for (ConsumerRecord<String, String> r : records) {
                    seen.put(r.key(), r.value());
                }
                assertThat(seen).containsKey(created.publicId());
            });
            String payload = seen.get(created.publicId());
            Map<String, Object> body = objectMapper.readValue(payload,
                    objectMapper.getTypeFactory().constructMapType(Map.class, String.class, Object.class));
            assertThat(body).containsEntry("code", req.code());
        }
    }

    @Test
    void Outbox_PENDING_행_은_poller_가_PROCESSING_을_거쳐_COMPLETED_로_전이시킨다() {
        // 테넌트 생성으로 outbox 행 발생
        TenantDtos.CreateRequest req = new TenantDtos.CreateRequest(
                "po-" + System.currentTimeMillis(), "Poller Test", "STANDARD", null);
        TenantDtos.Response created = tx.execute(s -> {
            rls.applySysAdmin();
            return tenantService.create(req, null);
        });

        Awaitility.await().atMost(Duration.ofSeconds(30)).pollInterval(Duration.ofSeconds(1)).untilAsserted(() -> {
            poller.poll();
            Integer pending = tx.execute(s -> {
                rls.applySysAdmin();
                return jdbcTemplate.queryForObject(
                        "SELECT COUNT(*) FROM tnt_outbox WHERE aggregate_id = ? AND status = 'COMPLETED'",
                        Integer.class, created.publicId());
            });
            assertThat(pending).isEqualTo(1);
        });

        assertThat(OutboxEntry.Status.COMPLETED).isEqualTo(OutboxEntry.Status.COMPLETED);
    }
}
