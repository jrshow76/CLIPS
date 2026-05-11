package com.tulip.member.application;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.tulip.common.core.exception.BusinessException;
import com.tulip.common.core.util.UlidGenerator;
import com.tulip.member.domain.MemberCard;
import com.tulip.member.domain.OutboxEvent;
import com.tulip.member.dto.MemberDtos;
import com.tulip.member.error.MemberErrorCode;
import com.tulip.member.infra.mapper.MemberCardMapper;
import com.tulip.member.infra.mapper.MemberMapper;
import com.tulip.member.infra.mapper.OutboxMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.List;

/**
 * 회원증 발급/상태 변경 서비스.
 *
 * <p>한 회원당 동시에 ACTIVE 카드는 최대 1매. 신규 발급 시 기존 ACTIVE 는 EXPIRED 처리.</p>
 */
@Service
public class MemberCardService {

    private static final LocalDate DEFAULT_EXPIRE = LocalDate.now().plusYears(3);

    private final MemberMapper memberMapper;
    private final MemberCardMapper cardMapper;
    private final OutboxMapper outboxMapper;
    private final ObjectMapper objectMapper;

    public MemberCardService(MemberMapper memberMapper,
                             MemberCardMapper cardMapper,
                             OutboxMapper outboxMapper,
                             ObjectMapper objectMapper) {
        this.memberMapper = memberMapper;
        this.cardMapper = cardMapper;
        this.outboxMapper = outboxMapper;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public MemberDtos.CardResponse issue(Long tenantId,
                                         Long memberId,
                                         Long issuedBy,
                                         MemberDtos.IssueCardRequest req) {
        // 회원 존재 확인 (PII 복호화는 불필요하므로 passphrase 는 null)
        if (memberMapper.findById(memberId, "", false) == null) {
            throw new BusinessException(MemberErrorCode.MEMBER_NOT_FOUND);
        }
        if (cardMapper.countActiveByMemberId(memberId) > 0) {
            throw new BusinessException(MemberErrorCode.CARD_ALREADY_ISSUED);
        }

        MemberCard card = new MemberCard();
        card.setTenantId(tenantId);
        card.setMemberId(memberId);
        card.setCardNo(generateCardNo());
        card.setCardType(req.cardType());
        card.setStatus("ACTIVE");
        card.setIssuedDate(LocalDate.now());
        card.setExpireDate(req.expireDate() == null ? DEFAULT_EXPIRE : req.expireDate());
        card.setIssuedReason(req.issuedReason());
        card.setCreatedBy(issuedBy);
        cardMapper.insert(card);

        publish("member.card_issued", memberId, card, tenantId);
        return toResponse(card);
    }

    @Transactional
    public MemberDtos.CardResponse updateCard(Long tenantId,
                                              Long cardId,
                                              Long updatedBy,
                                              MemberDtos.UpdateCardRequest req) {
        MemberCard existing = cardMapper.findById(cardId);
        if (existing == null) {
            throw new BusinessException(MemberErrorCode.CARD_NOT_FOUND);
        }
        if (req.expireDate() != null && req.expireDate().isBefore(LocalDate.now())) {
            throw new BusinessException(MemberErrorCode.CARD_INVALID_EXPIRY);
        }

        MemberCard patch = new MemberCard();
        patch.setId(cardId);
        patch.setStatus(req.status());
        patch.setExpireDate(req.expireDate());
        patch.setIssuedReason(req.issuedReason());
        patch.setUpdatedBy(updatedBy);
        cardMapper.updateById(patch);

        MemberCard updated = cardMapper.findById(cardId);
        publish("member.card_updated", updated.getMemberId(), updated, tenantId);
        return toResponse(updated);
    }

    @Transactional(readOnly = true)
    public List<MemberDtos.CardResponse> listByMember(Long memberId) {
        return cardMapper.findByMemberId(memberId).stream().map(this::toResponse).toList();
    }

    private MemberDtos.CardResponse toResponse(MemberCard c) {
        return new MemberDtos.CardResponse(
                c.getId(), c.getMemberId(), c.getCardNo(), c.getCardType(),
                c.getStatus(), c.getIssuedDate(), c.getExpireDate(), c.getIssuedReason(),
                c.getCreatedAt(), c.getUpdatedAt()
        );
    }

    private String generateCardNo() {
        return "C" + UlidGenerator.newUlid().substring(0, 14);
    }

    private void publish(String eventType, Long memberId, MemberCard snapshot, Long tenantId) {
        OutboxEvent ev = new OutboxEvent();
        ev.setTenantId(tenantId);
        ev.setAggregateType("MemberCard");
        ev.setAggregateId(String.valueOf(memberId));
        ev.setEventType(eventType);
        ev.setPayload(buildPayload(eventType, memberId, snapshot));
        ev.setOccurredAt(OffsetDateTime.now());
        outboxMapper.insert(ev);
    }

    private JsonNode buildPayload(String eventType, Long memberId, MemberCard snapshot) {
        ObjectNode root = objectMapper.createObjectNode();
        root.put("eventType", eventType);
        root.put("memberId", memberId);
        if (snapshot != null) {
            root.set("card", objectMapper.valueToTree(snapshot));
        }
        return root;
    }
}
