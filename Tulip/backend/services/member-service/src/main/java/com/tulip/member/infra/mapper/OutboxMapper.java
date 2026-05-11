package com.tulip.member.infra.mapper;

import com.tulip.member.domain.OutboxEvent;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * mbr_outbox Mapper — 동일 트랜잭션 내 이벤트 적재 + Worker 폴링.
 */
@Mapper
public interface OutboxMapper {

    int insert(@Param("e") OutboxEvent event);

    /** PENDING 상태 이벤트를 SKIP LOCKED 로 폴링 (워커 다중 인스턴스 안전). */
    List<OutboxEvent> pollPending(@Param("limit") int limit);

    int markPublished(@Param("id") Long id);

    int markFailed(@Param("id") Long id,
                   @Param("retryCount") int retryCount,
                   @Param("error") String error);
}
