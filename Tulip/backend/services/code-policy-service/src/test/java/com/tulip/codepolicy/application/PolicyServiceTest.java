package com.tulip.codepolicy.application;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.tulip.codepolicy.domain.Policy;
import com.tulip.codepolicy.dto.PolicyDtos;
import com.tulip.codepolicy.error.CodePolicyErrorCode;
import com.tulip.codepolicy.infra.mapper.OutboxMapper;
import com.tulip.codepolicy.infra.mapper.PolicyMapper;
import com.tulip.common.core.exception.BusinessException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class PolicyServiceTest {

    private PolicyMapper policyMapper;
    private OutboxMapper outboxMapper;
    private PolicyService service;

    @BeforeEach
    void setUp() {
        policyMapper = mock(PolicyMapper.class);
        outboxMapper = mock(OutboxMapper.class);
        service = new PolicyService(policyMapper, outboxMapper, new ObjectMapper());
    }

    @Test
    @DisplayName("정책 코드 중복이면 POLICY_DUPLICATE")
    void create_duplicate() {
        when(policyMapper.countByPolicyCode(eq("LOAN"), eq(null))).thenReturn(1);
        PolicyDtos.CreatePolicyRequest req = new PolicyDtos.CreatePolicyRequest(
                "LOAN", "기본 대출 정책", null, "1.0",
                new ObjectMapper().createObjectNode(), null, null, true
        );
        assertThatThrownBy(() -> service.create(1L, req))
                .isInstanceOf(BusinessException.class)
                .satisfies(ex -> assertThat(((BusinessException) ex).errorCode())
                        .isEqualTo(CodePolicyErrorCode.POLICY_DUPLICATE));
    }

    @Test
    @DisplayName("효력 정책 후보가 없으면 EFFECTIVE_POLICY_NOT_RESOLVED")
    void evaluate_noCandidates() {
        when(policyMapper.findEffectiveCandidates(anyString(), anyString(), anyString()))
                .thenReturn(List.of());
        assertThatThrownBy(() -> service.evaluate("LIBRARY", "1", "LOAN"))
                .isInstanceOf(BusinessException.class)
                .satisfies(ex -> assertThat(((BusinessException) ex).errorCode())
                        .isEqualTo(CodePolicyErrorCode.EFFECTIVE_POLICY_NOT_RESOLVED));
    }

    @Test
    @DisplayName("정상 생성 시 outbox 에 policy.created 적재")
    void create_ok() {
        when(policyMapper.countByPolicyCode(eq("HOLD"), eq(null))).thenReturn(0);
        doAnswer(inv -> {
            inv.<Policy>getArgument(0).setId(50L);
            return 1;
        }).when(policyMapper).insert(any());

        PolicyDtos.CreatePolicyRequest req = new PolicyDtos.CreatePolicyRequest(
                "HOLD", "예약 정책", null, "1.0",
                new ObjectMapper().createObjectNode(), null, null, true
        );
        PolicyDtos.PolicyResponse resp = service.create(1L, req);
        assertThat(resp.id()).isEqualTo(50L);
        verify(outboxMapper).insert(any());
    }
}
