package com.tulip.codepolicy.infra.cache;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.tulip.codepolicy.config.CodePolicyProperties;
import com.tulip.codepolicy.dto.CodeDtos;
import com.tulip.codepolicy.infra.mapper.CodeMapper;
import jakarta.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.util.Collections;
import java.util.List;

/**
 * 코드 그룹별 Redis 캐시.
 *
 * <p>키: {@code cache:codes:{groupCode}:{tenantId|GLOBAL}}, TTL 기본 1시간.
 * 시작 시 글로벌 코드 그룹을 사전 적재한다. 코드 변경 시 {@link #invalidate(String, Long)} 호출.</p>
 */
@Component
public class CodeCache {

    private static final Logger log = LoggerFactory.getLogger(CodeCache.class);
    private static final String KEY_PREFIX = "cache:codes:";

    private final StringRedisTemplate redis;
    private final ObjectMapper objectMapper;
    private final CodeMapper codeMapper;
    private final CodePolicyProperties properties;

    public CodeCache(StringRedisTemplate redis,
                     ObjectMapper objectMapper,
                     CodeMapper codeMapper,
                     CodePolicyProperties properties) {
        this.redis = redis;
        this.objectMapper = objectMapper;
        this.codeMapper = codeMapper;
        this.properties = properties;
    }

    /** 시작 시 글로벌 코드 그룹을 캐시에 적재한다. */
    @PostConstruct
    public void preload() {
        try {
            for (String group : properties.getCache().getPreloadGroups()) {
                refresh(group, null);
            }
            log.info("CodeCache preload 완료 groups={}", properties.getCache().getPreloadGroups());
        } catch (Exception ex) {
            log.warn("CodeCache preload 실패 (서비스 기동은 계속) cause={}", ex.getMessage());
        }
    }

    /** 캐시 조회 — 미스 시 DB 폴백 후 적재. */
    public List<CodeDtos.CodeItemResponse> get(String groupCode, Long tenantId) {
        String key = buildKey(groupCode, tenantId);
        try {
            String value = redis.opsForValue().get(key);
            if (value != null) {
                return objectMapper.readValue(value, new TypeReference<>() {
                });
            }
        } catch (Exception ex) {
            log.warn("CodeCache read 실패 key={} cause={}", key, ex.getMessage());
        }
        return refresh(groupCode, tenantId);
    }

    /** DB 에서 항목을 다시 읽어 캐시에 적재한다. */
    public List<CodeDtos.CodeItemResponse> refresh(String groupCode, Long tenantId) {
        List<CodeDtos.CodeItemResponse> items = codeMapper.listItemsByGroup(groupCode, tenantId).stream()
                .map(i -> new CodeDtos.CodeItemResponse(
                        i.getId(), i.getTenantId(), i.getGroupCode(), i.getCode(), i.getName(),
                        i.getDescription(), i.getParentId(), i.getSortOrder(), i.isActive(),
                        i.getAttributesJson(), i.getCreatedAt(), i.getUpdatedAt(),
                        Collections.emptyList()
                ))
                .toList();
        String key = buildKey(groupCode, tenantId);
        try {
            String json = objectMapper.writeValueAsString(items);
            redis.opsForValue().set(key, json,
                    Duration.ofSeconds(properties.getCache().getTtlSeconds()));
        } catch (Exception ex) {
            log.warn("CodeCache write 실패 key={} cause={}", key, ex.getMessage());
        }
        return items;
    }

    /** 코드 변경 시 캐시 무효화. */
    public void invalidate(String groupCode, Long tenantId) {
        redis.delete(buildKey(groupCode, tenantId));
    }

    private static String buildKey(String groupCode, Long tenantId) {
        String tenantPart = tenantId == null ? "GLOBAL" : String.valueOf(tenantId);
        return KEY_PREFIX + groupCode + ":" + tenantPart;
    }
}
