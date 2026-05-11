package com.tulip.tenant.infra.mapper;

import com.tulip.tenant.domain.LibraryBranch;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Optional;

/**
 * 분관 ({@code tnt_library_branch}) MyBatis Mapper.
 */
public interface LibraryBranchMapper {

    int insert(LibraryBranch branch);

    int update(LibraryBranch branch);

    Optional<LibraryBranch> findById(@Param("id") Long id);

    List<LibraryBranch> findByLibrary(@Param("libraryId") Long libraryId);

    int countActiveByLibrary(@Param("libraryId") Long libraryId);

    int countByCodeInLibrary(@Param("libraryId") Long libraryId, @Param("code") String code);
}
