package com.tulip.tenant.application;

import com.tulip.common.core.exception.BusinessException;
import com.tulip.common.core.exception.NotFoundException;
import com.tulip.common.core.util.UlidGenerator;
import com.tulip.tenant.api.dto.LibraryDtos;
import com.tulip.tenant.domain.Library;
import com.tulip.tenant.domain.LibraryBranch;
import com.tulip.tenant.domain.TenantStatus;
import com.tulip.tenant.error.TenantErrorCode;
import com.tulip.tenant.infra.mapper.LibraryBranchMapper;
import com.tulip.tenant.infra.mapper.LibraryMapper;
import com.tulip.tenant.outbox.OutboxAppender;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

/**
 * 분관(Branch) application service.
 */
@Service
public class LibraryBranchService {

    public static final String AGGREGATE = "library_branch";
    public static final String EVT_CREATED = "library_branch.created";
    public static final String EVT_UPDATED = "library_branch.updated";

    private final LibraryBranchMapper mapper;
    private final LibraryMapper libraryMapper;
    private final OutboxAppender outbox;

    public LibraryBranchService(LibraryBranchMapper mapper,
                                LibraryMapper libraryMapper,
                                OutboxAppender outbox) {
        this.mapper = mapper;
        this.libraryMapper = libraryMapper;
        this.outbox = outbox;
    }

    @Transactional
    public LibraryDtos.BranchResponse create(Long libraryId,
                                             LibraryDtos.BranchCreateRequest req,
                                             Long actorId) {
        Library lib = libraryMapper.findById(libraryId)
                .orElseThrow(() -> new NotFoundException(TenantErrorCode.LIBRARY_NOT_FOUND));
        if (mapper.countByCodeInLibrary(libraryId, req.code()) > 0) {
            throw new BusinessException(TenantErrorCode.BRANCH_CODE_DUPLICATE);
        }
        LibraryBranch b = LibraryBranch.create(
                UlidGenerator.newUlid(),
                lib.getTenantId(),
                libraryId,
                req.code(),
                req.name(),
                actorId
        );
        if (req.addressJson() != null) b.setAddressJson(req.addressJson());
        if (req.contactJson() != null) b.setContactJson(req.contactJson());
        mapper.insert(b);

        outbox.append(AGGREGATE, b.getPublicId(), EVT_CREATED,
                Map.of(
                        "id", b.getId(),
                        "publicId", b.getPublicId(),
                        "tenantId", b.getTenantId(),
                        "libraryId", b.getLibraryId(),
                        "code", b.getCode(),
                        "name", b.getName(),
                        "occurredAt", OffsetDateTime.now().toString()
                ),
                b.getTenantId());

        return LibraryDtos.BranchResponse.from(b);
    }

    @Transactional(readOnly = true)
    public List<LibraryDtos.BranchResponse> listByLibrary(Long libraryId) {
        return mapper.findByLibrary(libraryId).stream()
                .map(LibraryDtos.BranchResponse::from)
                .toList();
    }

    @Transactional
    public LibraryDtos.BranchResponse update(Long branchId,
                                             LibraryDtos.BranchUpdateRequest req,
                                             Long actorId) {
        LibraryBranch b = mapper.findById(branchId)
                .orElseThrow(() -> new NotFoundException(TenantErrorCode.BRANCH_NOT_FOUND));
        if (req.name() != null) b.setName(req.name());
        if (req.addressJson() != null) b.setAddressJson(req.addressJson());
        if (req.contactJson() != null) b.setContactJson(req.contactJson());
        if (req.status() != null) {
            TenantStatus next = TenantStatus.parseOrNull(req.status());
            if (next == null) throw new BusinessException(TenantErrorCode.INVALID_STATUS_TRANSITION);
            b.setStatus(next);
        }
        b.setUpdatedBy(actorId);
        int affected = mapper.update(b);
        if (affected == 0) {
            throw new BusinessException(TenantErrorCode.INVALID_STATUS_TRANSITION,
                    "다른 사용자가 먼저 수정했습니다");
        }
        outbox.append(AGGREGATE, b.getPublicId(), EVT_UPDATED,
                Map.of(
                        "id", b.getId(),
                        "publicId", b.getPublicId(),
                        "tenantId", b.getTenantId(),
                        "libraryId", b.getLibraryId(),
                        "status", b.getStatus().name(),
                        "occurredAt", OffsetDateTime.now().toString()
                ),
                b.getTenantId());
        return LibraryDtos.BranchResponse.from(b);
    }

    @Transactional
    public void delete(Long branchId, Long actorId) {
        LibraryBranch b = mapper.findById(branchId)
                .orElseThrow(() -> new NotFoundException(TenantErrorCode.BRANCH_NOT_FOUND));
        b.softDelete(actorId);
        mapper.update(b);
        outbox.append(AGGREGATE, b.getPublicId(), EVT_UPDATED,
                Map.of(
                        "id", b.getId(),
                        "publicId", b.getPublicId(),
                        "tenantId", b.getTenantId(),
                        "libraryId", b.getLibraryId(),
                        "status", "CLOSED",
                        "occurredAt", OffsetDateTime.now().toString()
                ),
                b.getTenantId());
    }
}
