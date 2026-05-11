package com.tulip.codepolicy.application;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.tulip.codepolicy.domain.CodeGroup;
import com.tulip.codepolicy.dto.CodeDtos;
import com.tulip.codepolicy.error.CodePolicyErrorCode;
import com.tulip.codepolicy.infra.cache.CodeCache;
import com.tulip.codepolicy.infra.mapper.CodeMapper;
import com.tulip.codepolicy.infra.mapper.OutboxMapper;
import com.tulip.common.core.exception.BusinessException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class CodeServiceTest {

    private CodeMapper codeMapper;
    private OutboxMapper outboxMapper;
    private CodeCache cache;
    private CodeService service;

    @BeforeEach
    void setUp() {
        codeMapper = mock(CodeMapper.class);
        outboxMapper = mock(OutboxMapper.class);
        cache = mock(CodeCache.class);
        service = new CodeService(codeMapper, outboxMapper, cache, new ObjectMapper());
    }

    @Test
    @DisplayName("코드 그룹이 없으면 CODE_GROUP_NOT_FOUND")
    void list_groupNotFound() {
        when(codeMapper.findGroupByCode(eq("UNKNOWN"), eq(1L))).thenReturn(null);
        assertThatThrownBy(() -> service.listItems("UNKNOWN", 1L))
                .isInstanceOf(BusinessException.class)
                .satisfies(ex -> assertThat(((BusinessException) ex).errorCode())
                        .isEqualTo(CodePolicyErrorCode.CODE_GROUP_NOT_FOUND));
    }

    @Test
    @DisplayName("코드 중복이면 CODE_DUPLICATE")
    void create_duplicate() {
        CodeGroup group = new CodeGroup();
        group.setId(10L);
        group.setGroupCode("LANG");
        when(codeMapper.findGroupByCode(eq("LANG"), eq(1L))).thenReturn(group);
        when(codeMapper.countItemByCode(eq(10L), eq("ko"), eq(null))).thenReturn(1);

        CodeDtos.CreateCodeItemRequest req = new CodeDtos.CreateCodeItemRequest(
                "ko", "한국어", null, null, 0, true, null
        );
        assertThatThrownBy(() -> service.create("LANG", 1L, req))
                .isInstanceOf(BusinessException.class)
                .satisfies(ex -> assertThat(((BusinessException) ex).errorCode())
                        .isEqualTo(CodePolicyErrorCode.CODE_DUPLICATE));
    }

    @Test
    @DisplayName("정상 생성 시 outbox 적재 + 캐시 무효화")
    void create_ok() {
        CodeGroup group = new CodeGroup();
        group.setId(10L);
        group.setGroupCode("LANG");
        when(codeMapper.findGroupByCode(eq("LANG"), eq(1L))).thenReturn(group);
        when(codeMapper.countItemByCode(eq(10L), eq("ja"), eq(null))).thenReturn(0);
        doAnswer(inv -> {
            inv.<com.tulip.codepolicy.domain.CodeItem>getArgument(0).setId(123L);
            return 1;
        }).when(codeMapper).insertItem(any());

        CodeDtos.CreateCodeItemRequest req = new CodeDtos.CreateCodeItemRequest(
                "ja", "일본어", null, null, 0, true, null
        );
        CodeDtos.CodeItemResponse resp = service.create("LANG", 1L, req);
        assertThat(resp.id()).isEqualTo(123L);
        verify(outboxMapper).insert(any());
        verify(cache).invalidate(eq("LANG"), eq(1L));
    }
}
