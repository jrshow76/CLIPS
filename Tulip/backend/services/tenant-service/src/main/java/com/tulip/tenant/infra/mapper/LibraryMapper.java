package com.tulip.tenant.infra.mapper;

import com.tulip.tenant.domain.Library;
import com.tulip.tenant.infra.mapper.params.LibrarySearchParam;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Optional;

/**
 * Library 테이블 ({@code tnt_library}) MyBatis Mapper.
 */
public interface LibraryMapper {

    int insert(Library library);

    int update(Library library);

    Optional<Library> findById(@Param("id") Long id);

    List<Library> search(LibrarySearchParam param);

    long countSearch(LibrarySearchParam param);

    int countByCode(@Param("code") String code);
}
