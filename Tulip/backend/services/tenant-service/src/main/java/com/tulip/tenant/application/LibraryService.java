package com.tulip.tenant.application;

import com.tulip.common.core.exception.BusinessException;
import com.tulip.common.core.exception.NotFoundException;
import com.tulip.common.core.response.ResponseMeta;
import com.tulip.common.core.util.UlidGenerator;
import com.tulip.common.tenant.context.TenantContextHolder;
import com.tulip.tenant.api.dto.LibraryDtos;
import com.tulip.tenant.domain.Library;
import com.tulip.tenant.domain.LibraryType;
import com.tulip.tenant.domain.TenantStatus;
import com.tulip.tenant.error.TenantErrorCode;
import com.tulip.tenant.infra.mapper.LibraryBranchMapper;
import com.tulip.tenant.infra.mapper.LibraryMapper;
import com.tulip.tenant.infra.mapper.params.LibrarySearchParam;
import com.tulip.tenant.outbox.OutboxAppender;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

/**
 * Library 도메인 application service.
 *
 * <p>RLS 정책으로 tenant_id 격리가 강제되므로 본 서비스는 별도 tenantId 파라미터 없이
 * 호출된다. tenantId 는 컨트롤러가 {@link TenantContextHolder} 에서 가져와 검증한다.</p>
 */
@Service
public class LibraryService {

    public static final String AGGREGATE = "library";
    public static final String EVT_CREATED = "library.created";
    public static final String EVT_UPDATED = "library.updated";
    public static final String EVT_DELETED = "library.deleted";

    private final LibraryMapper mapper;
    private final LibraryBranchMapper branchMapper;
    private final OutboxAppender outbox;

    public LibraryService(LibraryMapper mapper,
                          LibraryBranchMapper branchMapper,
                          OutboxAppender outbox) {
        this.mapper = mapper;
        this.branchMapper = branchMapper;
        this.outbox = outbox;
    }

    @Transactional
    public LibraryDtos.Response create(LibraryDtos.CreateRequest req, Long tenantId, Long actorId) {
        if (mapper.countByCode(req.code()) > 0) {
            throw new BusinessException(TenantErrorCode.LIBRARY_CODE_DUPLICATE);
        }
        Library lib = Library.create(
                UlidGenerator.newUlid(),
                tenantId,
                req.code(),
                req.name(),
                LibraryType.parseOrDefault(req.type(), LibraryType.CENTRAL),
                actorId
        );
        if (req.addressJson() != null) lib.setAddressJson(req.addressJson());
        if (req.contactJson() != null) lib.setContactJson(req.contactJson());
        if (req.openingHoursJson() != null) lib.setOpeningHoursJson(req.openingHoursJson());

        mapper.insert(lib);

        outbox.append(AGGREGATE, lib.getPublicId(), EVT_CREATED,
                Map.of(
                        "id", lib.getId(),
                        "publicId", lib.getPublicId(),
                        "tenantId", lib.getTenantId(),
                        "code", lib.getCode(),
                        "name", lib.getName(),
                        "type", lib.getType().name(),
                        "occurredAt", OffsetDateTime.now().toString()
                ),
                tenantId);

        return LibraryDtos.Response.from(lib);
    }

    @Transactional(readOnly = true)
    public LibraryDtos.Response getById(Long id) {
        return LibraryDtos.Response.from(requireById(id));
    }

    @Transactional(readOnly = true)
    public Library requireById(Long id) {
        return mapper.findById(id).orElseThrow(() -> new NotFoundException(TenantErrorCode.LIBRARY_NOT_FOUND));
    }

    @Transactional(readOnly = true)
    public SearchResult search(LibraryDtos.SearchCondition cond) {
        LibrarySearchParam param = new LibrarySearchParam(
                cond.name(), cond.status(),
                Math.max(0, cond.offset()), Math.min(100, Math.max(1, cond.limit()))
        );
        long total = mapper.countSearch(param);
        List<LibraryDtos.Response> items = mapper.search(param).stream()
                .map(LibraryDtos.Response::from)
                .toList();
        return new SearchResult(items, PageMetaBuilder.offsetMeta(param.offset(), param.limit(), total));
    }

    public record SearchResult(List<LibraryDtos.Response> items, ResponseMeta meta) {
    }

    @Transactional
    public LibraryDtos.Response update(Long id, LibraryDtos.UpdateRequest req, Long actorId) {
        Library lib = requireById(id);
        if (req.name() != null) lib.setName(req.name());
        if (req.addressJson() != null) lib.setAddressJson(req.addressJson());
        if (req.contactJson() != null) lib.setContactJson(req.contactJson());
        if (req.openingHoursJson() != null) lib.setOpeningHoursJson(req.openingHoursJson());
        if (req.status() != null) {
            TenantStatus next = TenantStatus.parseOrNull(req.status());
            if (next == null) {
                throw new BusinessException(TenantErrorCode.INVALID_STATUS_TRANSITION);
            }
            try {
                lib.changeStatus(next);
            } catch (IllegalStateException e) {
                throw new BusinessException(TenantErrorCode.INVALID_STATUS_TRANSITION, e.getMessage());
            }
        }
        lib.setUpdatedBy(actorId);
        int affected = mapper.update(lib);
        if (affected == 0) {
            throw new BusinessException(TenantErrorCode.INVALID_STATUS_TRANSITION,
                    "다른 사용자가 먼저 수정했습니다");
        }
        outbox.append(AGGREGATE, lib.getPublicId(), EVT_UPDATED,
                Map.of(
                        "id", lib.getId(),
                        "publicId", lib.getPublicId(),
                        "tenantId", lib.getTenantId(),
                        "status", lib.getStatus().name(),
                        "name", lib.getName(),
                        "occurredAt", OffsetDateTime.now().toString()
                ),
                lib.getTenantId());
        return LibraryDtos.Response.from(lib);
    }

    @Transactional
    public void delete(Long id, Long actorId) {
        Library lib = requireById(id);
        if (branchMapper.countActiveByLibrary(id) > 0) {
            throw new BusinessException(TenantErrorCode.LIBRARY_HAS_ACTIVE_BRANCHES);
        }
        lib.softDelete(actorId);
        mapper.update(lib);
        outbox.append(AGGREGATE, lib.getPublicId(), EVT_DELETED,
                Map.of(
                        "id", lib.getId(),
                        "publicId", lib.getPublicId(),
                        "tenantId", lib.getTenantId(),
                        "occurredAt", OffsetDateTime.now().toString()
                ),
                lib.getTenantId());
    }
}
