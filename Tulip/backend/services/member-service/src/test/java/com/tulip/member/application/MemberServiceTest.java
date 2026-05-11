package com.tulip.member.application;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.json.JsonMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.tulip.common.core.exception.BusinessException;
import com.tulip.member.config.MemberProperties;
import com.tulip.member.domain.Member;
import com.tulip.member.dto.MemberDtos;
import com.tulip.member.error.MemberErrorCode;
import com.tulip.member.infra.mapper.MemberConsentMapper;
import com.tulip.member.infra.mapper.MemberMapper;
import com.tulip.member.infra.mapper.OutboxMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.atLeastOnce;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * {@link MemberService} 단위 테스트.
 *
 * <p>핵심 흐름:
 * <ol>
 *   <li>이메일 중복 → 409 에러</li>
 *   <li>정상 등록 → outbox 적재 + member 응답</li>
 *   <li>존재하지 않는 회원 조회 → 404 에러</li>
 *   <li>소프트 삭제 — 이미 삭제된 회원이면 409</li>
 * </ol>
 * </p>
 */
class MemberServiceTest {

    private MemberMapper memberMapper;
    private MemberConsentMapper consentMapper;
    private OutboxMapper outboxMapper;
    private MemberService service;

    @BeforeEach
    void setUp() {
        memberMapper = mock(MemberMapper.class);
        consentMapper = mock(MemberConsentMapper.class);
        outboxMapper = mock(OutboxMapper.class);

        MemberProperties props = new MemberProperties();
        props.setPiiPassphrase("test-pass");

        ObjectMapper mapper = JsonMapper.builder().addModule(new JavaTimeModule()).build();
        service = new MemberService(memberMapper, consentMapper, outboxMapper, props, mapper);
    }

    @Test
    @DisplayName("이메일이 중복되면 MEMBER_EMAIL_DUPLICATE 예외를 던진다")
    void register_emailDuplicate() {
        when(memberMapper.countByEmail(eq("dup@tulip.io"), eq(null))).thenReturn(1);
        MemberDtos.CreateMemberRequest req = new MemberDtos.CreateMemberRequest(
                "홍길동", "dup@tulip.io", "010-1111-2222",
                null, "GENERAL", 1L, null, List.of()
        );
        assertThatThrownBy(() -> service.register(1L, 100L, req))
                .isInstanceOf(BusinessException.class)
                .satisfies(ex -> {
                    BusinessException be = (BusinessException) ex;
                    assertThat(be.errorCode()).isEqualTo(MemberErrorCode.MEMBER_EMAIL_DUPLICATE);
                });
    }

    @Test
    @DisplayName("정상 등록 시 outbox 에 member.registered 이벤트가 적재된다")
    void register_publishesEvent() {
        when(memberMapper.countByEmail(anyString(), eq(null))).thenReturn(0);
        // insert 호출 시 id 부여 시뮬레이션
        doAnswer(invocation -> {
            Member m = invocation.getArgument(0);
            m.setId(42L);
            return 1;
        }).when(memberMapper).insert(any(Member.class), anyString());

        MemberDtos.CreateMemberRequest req = new MemberDtos.CreateMemberRequest(
                "홍길동", "ok@tulip.io", "010-1111-2222",
                null, "GENERAL", 1L, null,
                List.of(new MemberDtos.ConsentInput("PRIVACY", true, "v1", "ADMIN"))
        );
        MemberDtos.MemberResponse resp = service.register(1L, 100L, req);

        assertThat(resp.id()).isEqualTo(42L);
        verify(outboxMapper, atLeastOnce()).insert(any());
        verify(consentMapper, times(1)).insert(any());
    }

    @Test
    @DisplayName("존재하지 않는 회원 조회 시 404 비즈니스 예외")
    void get_notFound() {
        when(memberMapper.findById(eq(999L), anyString(), eq(false))).thenReturn(null);
        assertThatThrownBy(() -> service.get(999L))
                .isInstanceOf(BusinessException.class)
                .satisfies(ex -> assertThat(((BusinessException) ex).errorCode())
                        .isEqualTo(MemberErrorCode.MEMBER_NOT_FOUND));
    }

    @Test
    @DisplayName("이미 삭제된 회원을 다시 삭제하려 하면 ALREADY_DELETED 예외")
    void softDelete_alreadyDeleted() {
        Member existing = new Member();
        existing.setId(7L);
        existing.setDeletedAt(java.time.OffsetDateTime.now());
        when(memberMapper.findById(eq(7L), anyString(), eq(false))).thenReturn(existing);

        assertThatThrownBy(() -> service.softDelete(1L, 7L))
                .isInstanceOf(BusinessException.class)
                .satisfies(ex -> assertThat(((BusinessException) ex).errorCode())
                        .isEqualTo(MemberErrorCode.MEMBER_ALREADY_DELETED));
    }
}
