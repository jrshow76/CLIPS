package com.tulip.codepolicy.infra.mapper;

import com.tulip.codepolicy.domain.Policy;
import com.tulip.codepolicy.domain.PolicyAssignment;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 정책 (pol_policy, pol_policy_assignment) Mapper.
 */
@Mapper
public interface PolicyMapper {

    List<Policy> list(@Param("policyCode") String policyCode,
                      @Param("active") Boolean active);

    Policy findById(@Param("id") Long id);

    Policy findByPolicyCode(@Param("policyCode") String policyCode);

    int insert(@Param("p") Policy policy);

    int updateById(@Param("p") Policy policy);

    int deleteById(@Param("id") Long id);

    int countByPolicyCode(@Param("policyCode") String policyCode,
                          @Param("excludeId") Long excludeId);

    /* Assignments */

    List<PolicyAssignment> listAssignments(@Param("policyId") Long policyId);

    int deleteAssignmentsByPolicy(@Param("policyId") Long policyId);

    int insertAssignment(@Param("a") PolicyAssignment assignment);

    int countAssignmentsByPolicy(@Param("policyId") Long policyId);

    /**
     * 효력 정책 결정 — targetType/targetId/policyCode 로 정렬된 후보 목록을 반환.
     * 애플리케이션 레이어에서 우선순위·effective_from/to 를 추가 평가한다.
     */
    List<Policy> findEffectiveCandidates(@Param("targetType") String targetType,
                                         @Param("targetId") String targetId,
                                         @Param("policyCode") String policyCode);
}
