package com.tulip.member.application;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.tulip.common.core.exception.BusinessException;
import com.tulip.common.core.page.Pagination;
import com.tulip.common.core.util.UlidGenerator;
import com.tulip.member.config.MemberProperties;
import com.tulip.member.domain.Member;
import com.tulip.member.domain.MemberConsent;
import com.tulip.member.domain.OutboxEvent;
import com.tulip.member.dto.MemberDtos;
import com.tulip.member.error.MemberErrorCode;
import com.tulip.member.infra.mapper.MemberConsentMapper;
import com.tulip.member.infra.mapper.MemberMapper;
import com.tulip.member.infra.mapper.OutboxMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Locale;

/**
 * 회원 도메인 핵심 서비스.
 *
 * <p>등록·검색·조회·수정·소프트 삭제와 동의 등록을 담당한다. 모든 변경 트랜잭션은
 * {@code mbr_outbox} 에 이벤트를 적재하여 Kafka 발행을 보장한다 (Outbox 패턴).</p>
 */
@Service
public class MemberService {

    private final MemberMapper memberMapper;
    private final MemberConsentMapper consentMapper;
    private final OutboxMapper outboxMapper;
    private final MemberProperties properties;
    private final ObjectMapper objectMapper;

    public MemberService(MemberMapper memberMapper,
                         MemberConsentMapper consentMapper,
                         OutboxMapper outboxMapper,
                         MemberProperties properties,
                         ObjectMapper objectMapper) {
        this.memberMapper = memberMapper;
        this.consentMapper = consentMapper;
        this.outboxMapper = outboxMapper;
        this.properties = properties;
        this.objectMapper = objectMapper;
    }

    /* ============================== Command ============================== */

    /** 회원 등록. */
    @Transactional
    public MemberDtos.MemberResponse register(Long tenantId,
                                              Long createdBy,
                                              MemberDtos.CreateMemberRequest req) {
        validateUnique(req);

        Member m = new Member();
        m.setTenantId(tenantId);
        m.setLibraryId(req.libraryId());
        m.setPublicId(UlidGenerator.newUlid());
        m.setMemberNo(generateMemberNo());
        m.setName(req.name());
        m.setNameNormalized(normalizeName(req.name()));
        m.setEmail(req.email());
        m.setEmailLower(req.email() == null ? null : req.email().toLowerCase(Locale.ROOT));
        m.setPhone(req.phone());
        m.setPhoneNormalized(normalizePhone(req.phone()));
        m.setBirthdate(req.birthdate());
        m.setMemberTypeCode(req.memberTypeCode());
        m.setStatus("ACTIVE");
        m.setAddressJson(req.address());
        m.setCreatedBy(createdBy);

        memberMapper.insert(m, properties.getPiiPassphrase());

        // 동의 처리
        if (req.consents() != null) {
            for (MemberDtos.ConsentInput input : req.consents()) {
                MemberConsent c = new MemberConsent();
                c.setTenantId(tenantId);
                c.setMemberId(m.getId());
                c.setConsentType(input.consentType());
                c.setGranted(input.granted());
                c.setVersion(input.version());
                c.setChannel(input.channel() == null ? "ADMIN_REGISTRATION" : input.channel());
                c.setCollectedBy(createdBy == null ? null : String.valueOf(createdBy));
                consentMapper.insert(c);
            }
        }

        publish("member.registered", "Member", m.getId(), m, tenantId);
        return toResponse(m);
    }

    /** 회원 수정. */
    @Transactional
    public MemberDtos.MemberResponse update(Long tenantId,
                                            Long memberId,
                                            Long updatedBy,
                                            MemberDtos.UpdateMemberRequest req) {
        Member existing = requireMember(memberId);

        if (req.email() != null) {
            int dup = memberMapper.countByEmail(req.email().toLowerCase(Locale.ROOT), memberId);
            if (dup > 0) {
                throw new BusinessException(MemberErrorCode.MEMBER_EMAIL_DUPLICATE);
            }
        }

        Member patch = new Member();
        patch.setId(memberId);
        patch.setLibraryId(req.libraryId());
        if (req.name() != null) {
            patch.setName(req.name());
            patch.setNameNormalized(normalizeName(req.name()));
        }
        if (req.email() != null) {
            patch.setEmail(req.email());
            patch.setEmailLower(req.email().toLowerCase(Locale.ROOT));
        }
        if (req.phone() != null) {
            patch.setPhone(req.phone());
            patch.setPhoneNormalized(normalizePhone(req.phone()));
        }
        patch.setBirthdate(req.birthdate());
        patch.setMemberTypeCode(req.memberTypeCode());
        patch.setStatus(req.status());
        patch.setAddressJson(req.address());
        patch.setUpdatedBy(updatedBy);

        memberMapper.updateById(patch, properties.getPiiPassphrase());
        Member updated = memberMapper.findById(memberId, properties.getPiiPassphrase(), false);

        publish("member.updated", "Member", memberId, updated, tenantId);
        if (req.status() != null && !req.status().equalsIgnoreCase(existing.getStatus())
                && "SUSPENDED".equalsIgnoreCase(req.status())) {
            publish("member.suspended", "Member", memberId, updated, tenantId);
        }
        return toResponse(updated);
    }

    /** 소프트 삭제 — 즉시 deleted_at 채움. 30일 후 물리 정리는 별도 배치. */
    @Transactional
    public void softDelete(Long tenantId, Long memberId) {
        Member existing = requireMember(memberId);
        if (existing.getDeletedAt() != null) {
            throw new BusinessException(MemberErrorCode.MEMBER_ALREADY_DELETED);
        }
        memberMapper.softDelete(memberId);
        publish("member.suspended", "Member", memberId, existing, tenantId);
    }

    /** 단건 동의 등록 (별도 엔드포인트). */
    @Transactional
    public MemberDtos.ConsentResponse addConsent(Long tenantId,
                                                 Long memberId,
                                                 Long collectorId,
                                                 MemberDtos.ConsentInput input) {
        requireMember(memberId);
        MemberConsent c = new MemberConsent();
        c.setTenantId(tenantId);
        c.setMemberId(memberId);
        c.setConsentType(input.consentType());
        c.setGranted(input.granted());
        c.setVersion(input.version());
        c.setChannel(input.channel() == null ? "ADMIN_UI" : input.channel());
        c.setCollectedBy(collectorId == null ? null : String.valueOf(collectorId));
        consentMapper.insert(c);

        publish("member.consent_granted", "Member", memberId, c, tenantId);
        return new MemberDtos.ConsentResponse(
                c.getId(), c.getMemberId(), c.getConsentType(),
                c.isGranted(), c.getVersion(), c.getChannel(),
                c.getGrantedAt(), c.getRevokedAt()
        );
    }

    /* ============================== Query ============================== */

    @Transactional(readOnly = true)
    public MemberDtos.MemberResponse get(Long memberId) {
        Member m = requireMember(memberId);
        return toResponse(m);
    }

    @Transactional(readOnly = true)
    public SearchResult search(MemberDtos.MemberSearchCriteria criteria, Pagination pagination) {
        Pagination effective = pagination == null ? Pagination.defaults() : pagination;
        int offset = effective.sqlOffset();
        int size = effective.effectiveSize();

        List<Member> rows = memberMapper.search(criteria, properties.getPiiPassphrase(), offset, size);
        long total = memberMapper.countSearch(criteria);
        List<MemberDtos.MemberResponse> mapped = rows.stream().map(this::toResponse).toList();
        return new SearchResult(mapped, total, effective);
    }

    @Transactional(readOnly = true)
    public List<MemberDtos.ConsentResponse> listConsents(Long memberId) {
        requireMember(memberId);
        return consentMapper.findByMemberId(memberId).stream()
                .map(c -> new MemberDtos.ConsentResponse(
                        c.getId(), c.getMemberId(), c.getConsentType(),
                        c.isGranted(), c.getVersion(), c.getChannel(),
                        c.getGrantedAt(), c.getRevokedAt()
                ))
                .toList();
    }

    /* ============================== Helpers ============================== */

    private Member requireMember(Long memberId) {
        Member m = memberMapper.findById(memberId, properties.getPiiPassphrase(), false);
        if (m == null) {
            throw new BusinessException(MemberErrorCode.MEMBER_NOT_FOUND);
        }
        return m;
    }

    private void validateUnique(MemberDtos.CreateMemberRequest req) {
        if (req.email() != null && !req.email().isBlank()) {
            int dup = memberMapper.countByEmail(req.email().toLowerCase(Locale.ROOT), null);
            if (dup > 0) {
                throw new BusinessException(MemberErrorCode.MEMBER_EMAIL_DUPLICATE);
            }
        }
    }

    private static String normalizeName(String name) {
        if (!StringUtils.hasText(name)) return null;
        return name.trim().replaceAll("\\s+", "");
    }

    private static String normalizePhone(String phone) {
        if (!StringUtils.hasText(phone)) return null;
        return phone.replaceAll("[^0-9]", "");
    }

    private String generateMemberNo() {
        // Phase 1-C: ULID 기반 단순 채번. Phase 2 에서 정책 기반 채번으로 교체.
        return "M" + UlidGenerator.newUlid().substring(0, 12);
    }

    private MemberDtos.MemberResponse toResponse(Member m) {
        return new MemberDtos.MemberResponse(
                m.getId(),
                m.getPublicId(),
                m.getMemberNo(),
                m.getName(),
                m.getEmail(),
                m.getPhone(),
                m.getBirthdate(),
                m.getMemberTypeCode(),
                m.getStatus(),
                m.getLibraryId(),
                m.getAddressJson(),
                m.getCreatedAt(),
                m.getUpdatedAt(),
                m.getSuspendedAt()
        );
    }

    private void publish(String eventType, String aggregateType, Long aggregateId, Object snapshot, Long tenantId) {
        OutboxEvent ev = new OutboxEvent();
        ev.setTenantId(tenantId);
        ev.setAggregateType(aggregateType);
        ev.setAggregateId(String.valueOf(aggregateId));
        ev.setEventType(eventType);
        ev.setPayload(buildPayload(eventType, aggregateType, aggregateId, snapshot));
        ev.setOccurredAt(OffsetDateTime.now());
        outboxMapper.insert(ev);
    }

    private JsonNode buildPayload(String eventType, String aggregateType, Long aggregateId, Object snapshot) {
        ObjectNode root = objectMapper.createObjectNode();
        root.put("eventType", eventType);
        root.put("aggregateType", aggregateType);
        root.put("aggregateId", String.valueOf(aggregateId));
        if (snapshot != null) {
            root.set("data", objectMapper.valueToTree(snapshot));
        }
        return root;
    }

    /** 검색 응답 묶음. */
    public record SearchResult(
            List<MemberDtos.MemberResponse> items,
            long totalElements,
            Pagination pagination
    ) {
    }
}
