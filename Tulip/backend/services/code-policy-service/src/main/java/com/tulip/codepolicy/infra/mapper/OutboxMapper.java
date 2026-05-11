package com.tulip.codepolicy.infra.mapper;

import com.tulip.codepolicy.domain.OutboxEvent;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * cd_outbox Mapper — Outbox 폴링 워커가 사용.
 */
@Mapper
public interface OutboxMapper {

    int insert(@Param("e") OutboxEvent event);

    List<OutboxEvent> pollPending(@Param("limit") int limit);

    int markPublished(@Param("id") Long id);

    int markFailed(@Param("id") Long id,
                   @Param("retryCount") int retryCount,
                   @Param("error") String error);
}
