package com.tulip.tenant.infra.mapper;

import com.tulip.tenant.domain.TenantSetting;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Optional;

/**
 * 테넌트 설정 ({@code tnt_tenant_setting}) MyBatis Mapper.
 */
public interface TenantSettingMapper {

    int insert(TenantSetting setting);

    int update(TenantSetting setting);

    Optional<TenantSetting> findByKey(@Param("tenantId") Long tenantId, @Param("key") String key);

    List<TenantSetting> findAllByTenant(@Param("tenantId") Long tenantId);
}
