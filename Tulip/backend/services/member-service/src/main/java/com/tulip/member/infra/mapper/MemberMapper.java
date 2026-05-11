package com.tulip.member.infra.mapper;

import com.tulip.member.domain.Member;
import com.tulip.member.dto.MemberDtos;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 회원 (mbr_member) MyBatis Mapper.
 *
 * <p>모든 쿼리는 RLS 가 자동 격리하므로 tenant_id 조건은 명시하지 않아도 되지만,
 * 추가 인덱스 활용을 위해 일부 쿼리는 RLS 외에 명시적으로 tenant_id 를 포함한다.</p>
 */
@Mapper
public interface MemberMapper {

    /** 회원 단건 INSERT. PII 컬럼은 pgp_sym_encrypt 사용. */
    int insert(@Param("m") Member member, @Param("pass") String pgpPassphrase);

    /** 회원 단건 UPDATE. */
    int updateById(@Param("m") Member member, @Param("pass") String pgpPassphrase);

    /** 상태/이용제한 변경. */
    int updateStatus(@Param("id") Long id,
                     @Param("status") String status,
                     @Param("reason") String reason);

    /** 소프트 삭제 (deleted_at 채움). */
    int softDelete(@Param("id") Long id);

    /** ID 로 단건 조회 (deleted_at 무시 옵션). */
    Member findById(@Param("id") Long id,
                    @Param("pass") String pgpPassphrase,
                    @Param("includeDeleted") boolean includeDeleted);

    /** 회원번호로 조회. */
    Member findByMemberNo(@Param("memberNo") String memberNo,
                          @Param("pass") String pgpPassphrase);

    /** 검색 — offset 페이지네이션. */
    List<Member> search(@Param("c") MemberDtos.MemberSearchCriteria criteria,
                        @Param("pass") String pgpPassphrase,
                        @Param("offset") int offset,
                        @Param("size") int size);

    /** 검색 결과 총 개수. */
    long countSearch(@Param("c") MemberDtos.MemberSearchCriteria criteria);

    /** 이메일 중복 확인 (활성 회원만). */
    int countByEmail(@Param("email") String emailLower,
                     @Param("excludeId") Long excludeId);

    /** 회원번호 중복 확인. */
    int countByMemberNo(@Param("memberNo") String memberNo);
}
