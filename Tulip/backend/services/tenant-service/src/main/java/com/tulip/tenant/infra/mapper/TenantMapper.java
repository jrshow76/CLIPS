package com.tulip.tenant.infra.mapper;

import com.tulip.tenant.domain.Tenant;
import com.tulip.tenant.infra.mapper.params.TenantSearchParam;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Optional;

/**
 * Tenant 테이블 ({@code tnt_tenant}) MyBatis Mapper.
 */
public interface TenantMapper {

    int insert(Tenant tenant);

    int update(Tenant tenant);

    Optional<Tenant> findById(@Param("id") Long id);

    Optional<Tenant> findByCode(@Param("code") String code);

    Optional<Tenant> findByPublicId(@Param("publicId") String publicId);

    List<Tenant> search(TenantSearchParam param);

    long countSearch(TenantSearchParam param);

    int countByCode(@Param("code") String code);
}
