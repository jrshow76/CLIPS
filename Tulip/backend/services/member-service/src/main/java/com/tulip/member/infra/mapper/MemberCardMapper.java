package com.tulip.member.infra.mapper;

import com.tulip.member.domain.MemberCard;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 회원증 Mapper.
 */
@Mapper
public interface MemberCardMapper {

    int insert(@Param("c") MemberCard card);

    int updateById(@Param("c") MemberCard card);

    MemberCard findById(@Param("id") Long id);

    List<MemberCard> findByMemberId(@Param("memberId") Long memberId);

    int countActiveByMemberId(@Param("memberId") Long memberId);
}
