package com.tulip.tenant.application;

import com.tulip.common.core.exception.BusinessException;
import com.tulip.common.core.exception.NotFoundException;
import com.tulip.common.core.response.ResponseMeta;
import com.tulip.common.core.util.UlidGenerator;
import com.tulip.tenant.api.dto.TenantDtos;
import com.tulip.tenant.domain.Tenant;
import com.tulip.tenant.domain.TenantStatus;
import com.tulip.tenant.error.TenantErrorCode;
import com.tulip.tenant.infra.mapper.TenantMapper;
import com.tulip.tenant.infra.mapper.params.TenantSearchParam;
import com.tulip.tenant.outbox.OutboxAppender;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

/**
 * Tenant 도메인 application service.
 *
 * <p>SYS_ADMIN bypass 모드에서만 호출되어야 한다. 컨트롤러는 본 서비스 호출 전
 * 보안 어노테이션({@code @PreAuthorize("hasRole('SYS_ADMIN')")}) 으로 차단한다.</p>
 *
 * <p>모든 변경 메서드는 동일 트랜잭션에서 {@link OutboxAppender} 를 통해 도메인 이벤트를 적재한다.</p>
 */
@Service
public class TenantService {

    public static final String AGGREGATE = "tenant";
    public static final String EVT_CREATED = "tenant.created";
    public static final String EVT_UPDATED = "tenant.updated";
    public static final String EVT_STATUS_CHANGED = "tenant.status_changed";

    private final TenantMapper mapper;
    private final OutboxAppender outbox;

    public TenantService(TenantMapper mapper, OutboxAppender outbox) {
        this.mapper = mapper;
        this.outbox = outbox;
    }

    /** 테넌트 생성. */
    @Transactional
    public TenantDtos.Response create(TenantDtos.CreateRequest req, Long actorId) {
        if (mapper.countByCode(req.code()) > 0) {
            throw new BusinessException(TenantErrorCode.TENANT_CODE_DUPLICATE);
        }
        Tenant t = Tenant.create(UlidGenerator.newUlid(), req.code(), req.name(), req.plan(), actorId);
        if (req.contactJson() != null) {
            t.setContactJson(req.contactJson());
        }
        mapper.insert(t);
        outbox.append(AGGREGATE, t.getPublicId(), EVT_CREATED,
                Map.of(
                        "id", t.getId(),
                        "publicId", t.getPublicId(),
                        "code", t.getCode(),
                        "name", t.getName(),
                        "status", t.getStatus().name(),
                        "plan", t.getPlan(),
                        "occurredAt", OffsetDateTime.now().toString()
                ),
                t.getId());
        return TenantDtos.Response.from(t);
    }

    /** 단건 조회 (id). */
    @Transactional(readOnly = true)
    public TenantDtos.Response getById(Long id) {
        Tenant t = mapper.findById(id).orElseThrow(() -> new NotFoundException(TenantErrorCode.TENANT_NOT_FOUND));
        return TenantDtos.Response.from(t);
    }

    /** 단건 조회 — 도메인. */
    @Transactional(readOnly = true)
    public Tenant requireById(Long id) {
        return mapper.findById(id).orElseThrow(() -> new NotFoundException(TenantErrorCode.TENANT_NOT_FOUND));
    }

    /** 코드로 조회. */
    @Transactional(readOnly = true)
    public boolean existsById(Long id) {
        return mapper.findById(id).isPresent();
    }

    /** 검색 (페이지). */
    @Transactional(readOnly = true)
    public SearchResult search(TenantDtos.SearchCondition cond) {
        TenantSearchParam param = new TenantSearchParam(
                cond.code(), cond.name(), cond.status(),
                Math.max(0, cond.offset()), Math.min(100, Math.max(1, cond.limit()))
        );
        long total = mapper.countSearch(param);
        List<TenantDtos.Response> items = mapper.search(param).stream()
                .map(TenantDtos.Response::from)
                .toList();
        return new SearchResult(items, PageMetaBuilder.offsetMeta(param.offset(), param.limit(), total));
    }

    public record SearchResult(List<TenantDtos.Response> items, ResponseMeta meta) {
    }

    /** 수정 (PATCH). */
    @Transactional
    public TenantDtos.Response update(Long id, TenantDtos.UpdateRequest req, Long actorId) {
        Tenant t = requireById(id);

        boolean statusChanged = false;
        if (req.name() != null) t.setName(req.name());
        if (req.plan() != null) t.changePlan(req.plan());
        if (req.contactJson() != null) t.setContactJson(req.contactJson());
        if (req.primaryLocale() != null) t.setPrimaryLocale(req.primaryLocale());
        if (req.primaryTimezone() != null) t.setPrimaryTimezone(req.primaryTimezone());
        if (req.status() != null) {
            TenantStatus next = TenantStatus.parseOrNull(req.status());
            if (next == null) {
                throw new BusinessException(TenantErrorCode.INVALID_STATUS_TRANSITION);
            }
            if (next != t.getStatus()) {
                try {
                    t.changeStatus(next);
                    statusChanged = true;
                } catch (IllegalStateException ex) {
                    throw new BusinessException(TenantErrorCode.INVALID_STATUS_TRANSITION, ex.getMessage());
                }
            }
        }
        t.setUpdatedBy(actorId);
        int affected = mapper.update(t);
        if (affected == 0) {
            // version 불일치 = 낙관락 충돌
            throw new BusinessException(TenantErrorCode.INVALID_STATUS_TRANSITION,
                    "다른 사용자가 먼저 수정했습니다");
        }
        outbox.append(AGGREGATE, t.getPublicId(),
                statusChanged ? EVT_STATUS_CHANGED : EVT_UPDATED,
                Map.of(
                        "id", t.getId(),
                        "publicId", t.getPublicId(),
                        "status", t.getStatus().name(),
                        "plan", t.getPlan(),
                        "name", t.getName(),
                        "occurredAt", OffsetDateTime.now().toString()
                ),
                t.getId());
        return TenantDtos.Response.from(t);
    }

    /** 소프트 삭제(=CLOSE). SUSPENDED 상태 필요. */
    @Transactional
    public void close(Long id, Long actorId) {
        Tenant t = requireById(id);
        if (t.getStatus() != TenantStatus.SUSPENDED) {
            throw new BusinessException(TenantErrorCode.TENANT_NOT_SUSPENDED);
        }
        t.close(actorId);
        mapper.update(t);
        outbox.append(AGGREGATE, t.getPublicId(), EVT_STATUS_CHANGED,
                Map.of(
                        "id", t.getId(),
                        "publicId", t.getPublicId(),
                        "status", t.getStatus().name(),
                        "occurredAt", OffsetDateTime.now().toString()
                ),
                t.getId());
    }
}
