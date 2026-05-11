package com.tulip.codepolicy.application;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.tulip.codepolicy.domain.OutboxEvent;
import com.tulip.codepolicy.domain.Policy;
import com.tulip.codepolicy.domain.PolicyAssignment;
import com.tulip.codepolicy.dto.PolicyDtos;
import com.tulip.codepolicy.error.CodePolicyErrorCode;
import com.tulip.codepolicy.infra.mapper.OutboxMapper;
import com.tulip.codepolicy.infra.mapper.PolicyMapper;
import com.tulip.common.core.exception.BusinessException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.List;

/**
 * 정책 도메인 서비스.
 *
 * <p>정책 자체의 CRUD + 할당 관리 + 효력 정책 평가를 제공한다.
 * 본 서비스는 정책 평가 규칙(rules_json) 자체를 해석하지 않는다 — 소비 서비스
 * (Circulation/Access/Facility) 가 자신의 컨텍스트에서 해석한다.</p>
 */
@Service
public class PolicyService {

    private final PolicyMapper policyMapper;
    private final OutboxMapper outboxMapper;
    private final ObjectMapper objectMapper;

    public PolicyService(PolicyMapper policyMapper,
                         OutboxMapper outboxMapper,
                         ObjectMapper objectMapper) {
        this.policyMapper = policyMapper;
        this.outboxMapper = outboxMapper;
        this.objectMapper = objectMapper;
    }

    /* ============================== Query ============================== */

    @Transactional(readOnly = true)
    public List<PolicyDtos.PolicyResponse> list(String policyCode, Boolean active) {
        return policyMapper.list(policyCode, active).stream()
                .map(p -> toResponse(p, policyMapper.listAssignments(p.getId())))
                .toList();
    }

    @Transactional(readOnly = true)
    public PolicyDtos.PolicyResponse get(Long id) {
        Policy p = requirePolicy(id);
        return toResponse(p, policyMapper.listAssignments(id));
    }

    @Transactional(readOnly = true)
    public PolicyDtos.EffectivePolicyResponse evaluate(String targetType,
                                                       String targetId,
                                                       String policyCode) {
        List<Policy> candidates = policyMapper.findEffectiveCandidates(targetType, targetId, policyCode);
        if (candidates.isEmpty()) {
            throw new BusinessException(CodePolicyErrorCode.EFFECTIVE_POLICY_NOT_RESOLVED);
        }
        Policy chosen = candidates.get(0);
        List<PolicyAssignment> assignments = policyMapper.listAssignments(chosen.getId());
        PolicyAssignment matched = assignments.stream()
                .filter(a -> isMatch(a, targetType, targetId))
                .findFirst()
                .orElse(assignments.isEmpty() ? null : assignments.get(0));

        return new PolicyDtos.EffectivePolicyResponse(
                chosen.getId(), chosen.getPolicyCode(), chosen.getName(),
                chosen.getPolicyVersion(), chosen.getRulesJson(),
                matched == null ? null : matched.getTargetType(),
                matched == null ? null : matched.getTargetId(),
                matched == null ? null : matched.getPriority()
        );
    }

    /* ============================== Command ============================== */

    @Transactional
    public PolicyDtos.PolicyResponse create(Long tenantId, PolicyDtos.CreatePolicyRequest req) {
        int dup = policyMapper.countByPolicyCode(req.policyCode(), null);
        if (dup > 0) {
            throw new BusinessException(CodePolicyErrorCode.POLICY_DUPLICATE);
        }

        Policy p = new Policy();
        p.setTenantId(tenantId);
        p.setPolicyCode(req.policyCode());
        p.setName(req.name());
        p.setDescription(req.description());
        p.setPolicyVersion(req.policyVersion());
        p.setRulesJson(req.rules());
        p.setEffectiveFrom(req.effectiveFrom());
        p.setEffectiveTo(req.effectiveTo());
        p.setActive(req.active() == null ? true : req.active());

        policyMapper.insert(p);
        publish("policy.created", p);
        return toResponse(p, List.of());
    }

    @Transactional
    public PolicyDtos.PolicyResponse update(Long id, PolicyDtos.UpdatePolicyRequest req) {
        requirePolicy(id);
        Policy patch = new Policy();
        patch.setId(id);
        patch.setName(req.name());
        patch.setDescription(req.description());
        patch.setPolicyVersion(req.policyVersion());
        patch.setRulesJson(req.rules());
        patch.setEffectiveFrom(req.effectiveFrom());
        patch.setEffectiveTo(req.effectiveTo());
        patch.setActive(Boolean.TRUE.equals(req.active()));

        policyMapper.updateById(patch);
        Policy updated = policyMapper.findById(id);
        publish("policy.updated", updated);
        return toResponse(updated, policyMapper.listAssignments(id));
    }

    @Transactional
    public PolicyDtos.PolicyResponse assign(Long policyId,
                                            Long tenantId,
                                            PolicyDtos.AssignmentsRequest req) {
        Policy policy = requirePolicy(policyId);
        policyMapper.deleteAssignmentsByPolicy(policyId);
        for (PolicyDtos.AssignmentInput input : req.assignments()) {
            PolicyAssignment a = new PolicyAssignment();
            a.setTenantId(tenantId);
            a.setPolicyId(policyId);
            a.setTargetType(input.targetType());
            a.setTargetId(input.targetId());
            a.setPriority(input.priority() == null ? 0 : input.priority());
            policyMapper.insertAssignment(a);
        }
        publish("policy.assigned", policy);
        return toResponse(policy, policyMapper.listAssignments(policyId));
    }

    /* ============================== Helpers ============================== */

    private Policy requirePolicy(Long id) {
        Policy p = policyMapper.findById(id);
        if (p == null) {
            throw new BusinessException(CodePolicyErrorCode.POLICY_NOT_FOUND);
        }
        return p;
    }

    private boolean isMatch(PolicyAssignment a, String targetType, String targetId) {
        return a.getTargetType().equals(targetType) && a.getTargetId().equals(targetId);
    }

    private PolicyDtos.PolicyResponse toResponse(Policy p, List<PolicyAssignment> assignments) {
        List<PolicyDtos.AssignmentResponse> a = assignments == null ? List.of()
                : assignments.stream()
                        .map(x -> new PolicyDtos.AssignmentResponse(
                                x.getId(), x.getPolicyId(), x.getTargetType(),
                                x.getTargetId(), x.getPriority()))
                        .toList();
        return new PolicyDtos.PolicyResponse(
                p.getId(), p.getTenantId(), p.getPolicyCode(), p.getName(),
                p.getDescription(), p.getPolicyVersion(), p.getRulesJson(),
                p.getEffectiveFrom(), p.getEffectiveTo(), p.isActive(),
                p.getCreatedAt(), p.getUpdatedAt(), a
        );
    }

    private void publish(String eventType, Policy snapshot) {
        OutboxEvent ev = new OutboxEvent();
        ev.setTenantId(snapshot.getTenantId());
        ev.setAggregateType("Policy");
        ev.setAggregateId(String.valueOf(snapshot.getId()));
        ev.setEventType(eventType);
        ev.setPayload(buildPayload(eventType, snapshot));
        ev.setOccurredAt(OffsetDateTime.now());
        outboxMapper.insert(ev);
    }

    private JsonNode buildPayload(String eventType, Policy snapshot) {
        ObjectNode root = objectMapper.createObjectNode();
        root.put("eventType", eventType);
        root.put("policyCode", snapshot.getPolicyCode());
        root.set("data", objectMapper.valueToTree(snapshot));
        return root;
    }
}
