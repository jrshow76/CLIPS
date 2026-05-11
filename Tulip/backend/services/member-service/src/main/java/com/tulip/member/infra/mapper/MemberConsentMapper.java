package com.tulip.member.infra.mapper;

import com.tulip.member.domain.MemberConsent;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 개인정보 동의 이력 Mapper.
 */
@Mapper
public interface MemberConsentMapper {

    int insert(@Param("c") MemberConsent consent);

    List<MemberConsent> findByMemberId(@Param("memberId") Long memberId);
}
