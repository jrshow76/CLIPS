package com.tulip.tenant.application;

import com.tulip.common.core.exception.BusinessException;
import com.tulip.common.core.exception.NotFoundException;
import com.tulip.tenant.api.dto.TenantSettingDtos;
import com.tulip.tenant.domain.TenantSetting;
import com.tulip.tenant.error.TenantErrorCode;
import com.tulip.tenant.infra.mapper.TenantSettingMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.regex.Pattern;

/**
 * 테넌트 설정 KV application service.
 *
 * <p>설정 키는 NAMESPACE.KEY (대문자, 점-구분) 형식이며, 값은 JSONB 문자열.</p>
 */
@Service
public class TenantSettingService {

    private static final Pattern KEY_PATTERN = Pattern.compile("^[A-Z][A-Z0-9_]*(\\.[A-Z][A-Z0-9_]*)+$");

    private final TenantSettingMapper mapper;

    public TenantSettingService(TenantSettingMapper mapper) {
        this.mapper = mapper;
    }

    @Transactional(readOnly = true)
    public List<TenantSettingDtos.Response> listByTenant(Long tenantId) {
        return mapper.findAllByTenant(tenantId).stream()
                .map(TenantSettingDtos.Response::from)
                .toList();
    }

    @Transactional(readOnly = true)
    public TenantSettingDtos.Response getByKey(Long tenantId, String key) {
        TenantSetting s = mapper.findByKey(tenantId, key)
                .orElseThrow(() -> new NotFoundException(TenantErrorCode.SETTING_NOT_FOUND));
        return TenantSettingDtos.Response.from(s);
    }

    /** 키 upsert. 존재하면 update, 없으면 insert. */
    @Transactional
    public TenantSettingDtos.Response upsert(Long tenantId,
                                             String key,
                                             TenantSettingDtos.UpsertRequest req,
                                             Long actorId) {
        if (!KEY_PATTERN.matcher(key).matches()) {
            throw new BusinessException(TenantErrorCode.SETTING_KEY_INVALID);
        }
        TenantSetting existing = mapper.findByKey(tenantId, key).orElse(null);
        if (existing != null) {
            existing.changeValue(req.valueJson(), actorId);
            if (req.description() != null) existing.setDescription(req.description());
            int affected = mapper.update(existing);
            if (affected == 0) {
                throw new BusinessException(TenantErrorCode.INVALID_STATUS_TRANSITION,
                        "다른 사용자가 먼저 수정했습니다");
            }
            return TenantSettingDtos.Response.from(existing);
        }
        TenantSetting created = TenantSetting.of(tenantId, key, req.valueJson(), req.description(), actorId);
        mapper.insert(created);
        return TenantSettingDtos.Response.from(created);
    }
}
