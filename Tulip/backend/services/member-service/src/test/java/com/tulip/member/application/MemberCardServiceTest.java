package com.tulip.member.application;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.json.JsonMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.tulip.common.core.exception.BusinessException;
import com.tulip.member.domain.Member;
import com.tulip.member.dto.MemberDtos;
import com.tulip.member.error.MemberErrorCode;
import com.tulip.member.infra.mapper.MemberCardMapper;
import com.tulip.member.infra.mapper.MemberMapper;
import com.tulip.member.infra.mapper.OutboxMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class MemberCardServiceTest {

    private MemberMapper memberMapper;
    private MemberCardMapper cardMapper;
    private OutboxMapper outboxMapper;
    private MemberCardService service;

    @BeforeEach
    void setUp() {
        memberMapper = mock(MemberMapper.class);
        cardMapper = mock(MemberCardMapper.class);
        outboxMapper = mock(OutboxMapper.class);
        ObjectMapper mapper = JsonMapper.builder().addModule(new JavaTimeModule()).build();
        service = new MemberCardService(memberMapper, cardMapper, outboxMapper, mapper);
    }

    @Test
    @DisplayName("회원이 없으면 카드 발급은 MEMBER_NOT_FOUND 예외")
    void issue_memberNotFound() {
        when(memberMapper.findById(eq(1L), anyString(), eq(false))).thenReturn(null);
        assertThatThrownBy(() -> service.issue(1L, 1L, 99L,
                new MemberDtos.IssueCardRequest("REGULAR", null, "신규")))
                .isInstanceOf(BusinessException.class)
                .satisfies(ex -> assertThat(((BusinessException) ex).errorCode())
                        .isEqualTo(MemberErrorCode.MEMBER_NOT_FOUND));
    }

    @Test
    @DisplayName("이미 활성 카드가 있으면 CARD_ALREADY_ISSUED 예외")
    void issue_alreadyIssued() {
        Member m = new Member();
        m.setId(1L);
        when(memberMapper.findById(eq(1L), anyString(), eq(false))).thenReturn(m);
        when(cardMapper.countActiveByMemberId(1L)).thenReturn(1);

        assertThatThrownBy(() -> service.issue(1L, 1L, 99L,
                new MemberDtos.IssueCardRequest("REGULAR", null, "재발급")))
                .isInstanceOf(BusinessException.class)
                .satisfies(ex -> assertThat(((BusinessException) ex).errorCode())
                        .isEqualTo(MemberErrorCode.CARD_ALREADY_ISSUED));
    }

    @Test
    @DisplayName("정상 발급 시 outbox 적재 + 카드 응답 반환")
    void issue_ok() {
        Member m = new Member();
        m.setId(1L);
        when(memberMapper.findById(eq(1L), anyString(), eq(false))).thenReturn(m);
        when(cardMapper.countActiveByMemberId(1L)).thenReturn(0);
        doAnswer(invocation -> {
            // generated id 부여
            invocation.<com.tulip.member.domain.MemberCard>getArgument(0).setId(11L);
            return 1;
        }).when(cardMapper).insert(any());

        MemberDtos.CardResponse resp = service.issue(1L, 1L, 99L,
                new MemberDtos.IssueCardRequest("REGULAR",
                        LocalDate.now().plusYears(2), "신규 가입"));
        assertThat(resp.id()).isEqualTo(11L);
        verify(outboxMapper).insert(any());
    }
}
