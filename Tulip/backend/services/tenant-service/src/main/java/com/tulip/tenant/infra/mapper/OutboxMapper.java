package com.tulip.tenant.infra.mapper;

import com.tulip.tenant.outbox.OutboxEntry;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * tnt_outbox MyBatis Mapper.
 *
 * <p>Poller 는 PENDING 행을 {@code FOR UPDATE SKIP LOCKED} 로 가져와
 * PROCESSING 으로 전이시킨 후 Kafka 발행 → COMPLETED 갱신한다.</p>
 */
public interface OutboxMapper {

    int insert(OutboxEntry entry);

    /** PENDING 행을 잠금 획득 — 다중 인스턴스 안전. */
    List<OutboxEntry> pickPending(@Param("limit") int limit);

    int markCompleted(@Param("id") Long id);

    int markFailed(@Param("id") Long id,
                   @Param("error") String error,
                   @Param("retryCount") int retryCount);

    int markRetry(@Param("id") Long id,
                  @Param("error") String error,
                  @Param("retryCount") int retryCount);
}
