package com.tulip.codepolicy.infra.mapper;

import com.tulip.codepolicy.domain.CodeGroup;
import com.tulip.codepolicy.domain.CodeItem;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 코드 그룹/코드 (cd_code_group, cd_code) Mapper.
 *
 * <p>글로벌 코드는 tenant_id IS NULL 로 저장되며 RLS 정책상 모든 사용자가 SELECT 가능.
 * 변경은 SYS_ADMIN 만 가능하다 (애플리케이션 레이어에서 강제).</p>
 */
@Mapper
public interface CodeMapper {

    /** 글로벌 + 테넌트 그룹 목록. tenantId 가 null 이면 글로벌만. */
    List<CodeGroup> listGroups(@Param("tenantId") Long tenantId);

    CodeGroup findGroupByCode(@Param("groupCode") String groupCode,
                              @Param("tenantId") Long tenantId);

    List<CodeItem> listItemsByGroup(@Param("groupCode") String groupCode,
                                    @Param("tenantId") Long tenantId);

    CodeItem findItemById(@Param("id") Long id);

    CodeItem findItem(@Param("groupCode") String groupCode,
                      @Param("code") String code,
                      @Param("tenantId") Long tenantId);

    int insertItem(@Param("i") CodeItem item);

    int updateItem(@Param("i") CodeItem item);

    int deleteItem(@Param("id") Long id);

    int countItemByCode(@Param("groupId") Long groupId,
                        @Param("code") String code,
                        @Param("excludeId") Long excludeId);
}
