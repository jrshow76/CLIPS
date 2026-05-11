package com.tulip.tenant.outbox;

import com.tulip.tenant.infra.mapper.OutboxMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.List;

/**
 * tnt_outbox 폴링 → Kafka 발행 → 상태 전이 스케줄러.
 *
 * <p>동작:
 *  - 5초 주기로 {@code FOR UPDATE SKIP LOCKED} 로 최대 100건의 PENDING 행을 잠금 획득
 *  - 잠금 트랜잭션 안에서 PROCESSING 으로 전이
 *  - 트랜잭션 commit 후, Kafka 발행 시도 — 성공 시 COMPLETED, 실패 시 retry_count++ 후 PENDING 복귀
 *  - retry_count > 5 인 경우 FAILED 마킹.</p>
 *
 * <p>RLS 정책상 SYS_ADMIN 역할이 필요하므로 본 컴포넌트는 별도 데이터소스
 * (BYPASSRLS 또는 SYS_ADMIN 컨텍스트) 로 작동해야 한다. 본 구현은 단일
 * 데이터소스에서 SYS_ADMIN role 을 SET LOCAL 로 적용한 별도 트랜잭션을 사용한다.</p>
 */
@Component
public class OutboxPoller {

    private static final Logger log = LoggerFactory.getLogger(OutboxPoller.class);

    private final OutboxMapper mapper;
    private final OutboxPublisher publisher;
    private final TransactionTemplate transactionTemplate;
    private final RlsSessionApplier rlsApplier;

    @Value("${tulip.tenant.outbox.batch-size:100}")
    private int batchSize;

    @Value("${tulip.tenant.outbox.max-retry:5}")
    private int maxRetry;

    @Value("${tulip.tenant.outbox.enabled:true}")
    private boolean enabled;

    public OutboxPoller(OutboxMapper mapper,
                        OutboxPublisher publisher,
                        TransactionTemplate transactionTemplate,
                        RlsSessionApplier rlsApplier) {
        this.mapper = mapper;
        this.publisher = publisher;
        this.transactionTemplate = transactionTemplate;
        this.rlsApplier = rlsApplier;
    }

    /**
     * 5초 주기 폴링. 통합 테스트에서 빠른 검증이 필요하면 properties 로 override.
     */
    @Scheduled(fixedDelayString = "${tulip.tenant.outbox.poll-delay-ms:5000}")
    public void poll() {
        if (!enabled) {
            return;
        }
        List<OutboxEntry> picked = pickBatch();
        if (picked.isEmpty()) {
            return;
        }
        log.debug("outbox poll picked={}", picked.size());
        for (OutboxEntry entry : picked) {
            handleOne(entry);
        }
    }

    /** PENDING 행을 PROCESSING 으로 전이하는 짧은 트랜잭션. */
    private List<OutboxEntry> pickBatch() {
        return transactionTemplate.execute(status -> {
            rlsApplier.applySysAdmin();
            return mapper.pickPending(batchSize);
        });
    }

    /** 한 건씩 발행 시도하고 상태 갱신. */
    private void handleOne(OutboxEntry entry) {
        try {
            publisher.publish(entry);
            transactionTemplate.executeWithoutResult(status -> {
                rlsApplier.applySysAdmin();
                mapper.markCompleted(entry.getId());
            });
        } catch (Exception ex) {
            int next = entry.getRetryCount() + 1;
            String errMsg = ex.getClass().getSimpleName() + ": " + ex.getMessage();
            log.warn("outbox publish 실패 id={} retry={}/{} cause={}",
                    entry.getId(), next, maxRetry, errMsg);
            transactionTemplate.executeWithoutResult(status -> {
                rlsApplier.applySysAdmin();
                if (next > maxRetry) {
                    mapper.markFailed(entry.getId(), errMsg, next);
                } else {
                    mapper.markRetry(entry.getId(), errMsg, next);
                }
            });
        }
    }
}
