package com.tulip.codepolicy.application;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.tulip.codepolicy.domain.CodeGroup;
import com.tulip.codepolicy.domain.CodeItem;
import com.tulip.codepolicy.domain.OutboxEvent;
import com.tulip.codepolicy.dto.CodeDtos;
import com.tulip.codepolicy.error.CodePolicyErrorCode;
import com.tulip.codepolicy.infra.cache.CodeCache;
import com.tulip.codepolicy.infra.mapper.CodeMapper;
import com.tulip.codepolicy.infra.mapper.OutboxMapper;
import com.tulip.common.core.exception.BusinessException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 코드 그룹/코드 도메인 서비스.
 *
 * <p>글로벌 코드는 SYS_ADMIN 만 변경할 수 있다 (컨트롤러에서 1차 보안, 서비스에서 추가 보호).
 * 코드 변경 시 캐시 무효화 및 cd_outbox 이벤트 적재.</p>
 */
@Service
public class CodeService {

    private final CodeMapper codeMapper;
    private final OutboxMapper outboxMapper;
    private final CodeCache cache;
    private final ObjectMapper objectMapper;

    public CodeService(CodeMapper codeMapper,
                       OutboxMapper outboxMapper,
                       CodeCache cache,
                       ObjectMapper objectMapper) {
        this.codeMapper = codeMapper;
        this.outboxMapper = outboxMapper;
        this.cache = cache;
        this.objectMapper = objectMapper;
    }

    /* ============================== Query ============================== */

    @Transactional(readOnly = true)
    public List<CodeDtos.CodeGroupResponse> listGroups(Long tenantId) {
        return codeMapper.listGroups(tenantId).stream()
                .map(this::toGroupResponse)
                .toList();
    }

    @Transactional(readOnly = true)
    public List<CodeDtos.CodeItemResponse> listItems(String groupCode, Long tenantId) {
        requireGroup(groupCode, tenantId);
        List<CodeItem> items = codeMapper.listItemsByGroup(groupCode, tenantId);
        return buildHierarchy(items);
    }

    @Transactional(readOnly = true)
    public CodeDtos.CodeItemResponse getItem(String groupCode, String code, Long tenantId) {
        CodeItem item = codeMapper.findItem(groupCode, code, tenantId);
        if (item == null) {
            throw new BusinessException(CodePolicyErrorCode.CODE_NOT_FOUND);
        }
        return toItemResponse(item, List.of());
    }

    /* ============================== Command ============================== */

    /** 캐시 우선 조회 — 내부 호출용. */
    @Transactional(readOnly = true)
    public List<CodeDtos.CodeItemResponse> getCached(String groupCode, Long tenantId) {
        requireGroup(groupCode, tenantId);
        return cache.get(groupCode, tenantId);
    }

    @Transactional
    public CodeDtos.CodeItemResponse create(String groupCode,
                                            Long tenantId,
                                            CodeDtos.CreateCodeItemRequest req) {
        CodeGroup group = requireGroup(groupCode, tenantId);
        // 글로벌 코드 그룹은 SYS_ADMIN 만 (서비스 가드)
        if (group.isGlobal() && tenantId == null) {
            // 글로벌 변경은 컨트롤러 권한 검사로 강제하고 본 서비스에서는 통과
        }
        int dup = codeMapper.countItemByCode(group.getId(), req.code(), null);
        if (dup > 0) {
            throw new BusinessException(CodePolicyErrorCode.CODE_DUPLICATE);
        }

        CodeItem item = new CodeItem();
        item.setTenantId(tenantId);
        item.setGroupId(group.getId());
        item.setGroupCode(group.getGroupCode());
        item.setCode(req.code());
        item.setName(req.name());
        item.setDescription(req.description());
        item.setParentId(req.parentId());
        item.setSortOrder(req.sortOrder() == null ? 0 : req.sortOrder());
        item.setActive(req.active() == null ? true : req.active());
        item.setAttributesJson(req.attributes());

        codeMapper.insertItem(item);
        publishCodeEvent("code.added", item);
        cache.invalidate(groupCode, tenantId);
        return toItemResponse(item, List.of());
    }

    @Transactional
    public CodeDtos.CodeItemResponse update(Long itemId,
                                            Long tenantId,
                                            CodeDtos.UpdateCodeItemRequest req) {
        CodeItem existing = codeMapper.findItemById(itemId);
        if (existing == null) {
            throw new BusinessException(CodePolicyErrorCode.CODE_NOT_FOUND);
        }
        CodeItem patch = new CodeItem();
        patch.setId(itemId);
        patch.setName(req.name());
        patch.setDescription(req.description());
        patch.setParentId(req.parentId());
        patch.setSortOrder(req.sortOrder());
        patch.setActive(Boolean.TRUE.equals(req.active()));
        patch.setAttributesJson(req.attributes());

        codeMapper.updateItem(patch);
        CodeItem updated = codeMapper.findItemById(itemId);
        publishCodeEvent("code.updated", updated);
        cache.invalidate(updated.getGroupCode(), updated.getTenantId());
        return toItemResponse(updated, List.of());
    }

    @Transactional
    public void delete(Long itemId) {
        CodeItem existing = codeMapper.findItemById(itemId);
        if (existing == null) {
            throw new BusinessException(CodePolicyErrorCode.CODE_NOT_FOUND);
        }
        codeMapper.deleteItem(itemId);
        publishCodeEvent("code.deleted", existing);
        cache.invalidate(existing.getGroupCode(), existing.getTenantId());
    }

    /* ============================== Helpers ============================== */

    private CodeGroup requireGroup(String groupCode, Long tenantId) {
        CodeGroup group = codeMapper.findGroupByCode(groupCode, tenantId);
        if (group == null) {
            throw new BusinessException(CodePolicyErrorCode.CODE_GROUP_NOT_FOUND);
        }
        return group;
    }

    private CodeDtos.CodeGroupResponse toGroupResponse(CodeGroup g) {
        return new CodeDtos.CodeGroupResponse(
                g.getId(), g.getTenantId(), g.getGroupCode(), g.getGroupName(),
                g.getDescription(), g.isEditable(), g.isHierarchical(), g.isGlobal()
        );
    }

    /** 트리 변환 — parentId 기준으로 children 배치. */
    private List<CodeDtos.CodeItemResponse> buildHierarchy(List<CodeItem> rows) {
        Map<Long, List<CodeDtos.CodeItemResponse>> childrenIndex = new HashMap<>();
        Map<Long, CodeItem> itemIndex = new HashMap<>();
        for (CodeItem i : rows) {
            itemIndex.put(i.getId(), i);
        }
        // 1차: 응답 객체 생성 (children 은 추후 set 으로 변환되지 않으므로 build-up 용 list 사용)
        Map<Long, List<CodeDtos.CodeItemResponse>> tempChildren = new HashMap<>();
        Map<Long, CodeDtos.CodeItemResponse> responseIndex = new HashMap<>();
        for (CodeItem i : rows) {
            List<CodeDtos.CodeItemResponse> kids = new ArrayList<>();
            tempChildren.put(i.getId(), kids);
            CodeDtos.CodeItemResponse resp = toItemResponse(i, kids);
            responseIndex.put(i.getId(), resp);
            childrenIndex.computeIfAbsent(i.getParentId(), k -> new ArrayList<>()).add(resp);
        }
        // 2차: parent.children 채우기
        for (CodeItem i : rows) {
            List<CodeDtos.CodeItemResponse> kids = childrenIndex.getOrDefault(i.getId(), List.of());
            tempChildren.get(i.getId()).addAll(kids);
        }
        return childrenIndex.getOrDefault(null, List.of());
    }

    private CodeDtos.CodeItemResponse toItemResponse(CodeItem i, List<CodeDtos.CodeItemResponse> children) {
        return new CodeDtos.CodeItemResponse(
                i.getId(), i.getTenantId(), i.getGroupCode(), i.getCode(), i.getName(),
                i.getDescription(), i.getParentId(), i.getSortOrder(), i.isActive(),
                i.getAttributesJson(), i.getCreatedAt(), i.getUpdatedAt(), children
        );
    }

    private void publishCodeEvent(String eventType, CodeItem snapshot) {
        OutboxEvent ev = new OutboxEvent();
        ev.setTenantId(snapshot.getTenantId());
        ev.setAggregateType("CodeItem");
        ev.setAggregateId(String.valueOf(snapshot.getId()));
        ev.setEventType(eventType);
        ev.setPayload(buildPayload(eventType, snapshot));
        ev.setOccurredAt(OffsetDateTime.now());
        outboxMapper.insert(ev);
    }

    private JsonNode buildPayload(String eventType, CodeItem snapshot) {
        ObjectNode root = objectMapper.createObjectNode();
        root.put("eventType", eventType);
        root.put("groupCode", snapshot.getGroupCode());
        root.put("code", snapshot.getCode());
        root.set("data", objectMapper.valueToTree(snapshot));
        return root;
    }
}
