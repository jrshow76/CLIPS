package com.shelfy.user.repository;

import com.shelfy.user.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.Optional;

/**
 * User JPA Repository
 * <p>
 * deleted_at IS NULL 조건을 직접 메서드명에 포함하거나 JPQL로 명시하여
 * 탈퇴 계정을 조회에서 제외한다.
 */
public interface UserRepository extends JpaRepository<User, Long> {

    /**
     * 이메일로 사용자 조회 (탈퇴 계정 포함 - 로그인 시 탈퇴 여부 직접 검사)
     */
    Optional<User> findByEmail(String email);

    /**
     * ID로 사용자 조회 (탈퇴 계정 제외)
     */
    @Query("SELECT u FROM User u WHERE u.id = :id AND u.deletedAt IS NULL")
    Optional<User> findActiveById(@Param("id") Long id);

    /**
     * 닉네임으로 사용자 조회 (탈퇴 계정 제외)
     */
    @Query("SELECT u FROM User u WHERE u.nickname = :nickname AND u.deletedAt IS NULL")
    Optional<User> findActiveByNickname(@Param("nickname") String nickname);

    /**
     * 이메일 존재 여부 확인 (탈퇴 계정 제외) - 회원가입 중복 체크
     */
    boolean existsByEmailAndDeletedAtIsNull(String email);

    /**
     * 닉네임 존재 여부 확인 (탈퇴 계정 제외) - 회원가입/닉네임 변경 중복 체크
     */
    boolean existsByNicknameAndDeletedAtIsNull(String nickname);

    /**
     * 닉네임 존재 여부 확인 (자신 제외, 탈퇴 계정 제외) - 닉네임 변경 시 중복 체크
     */
    @Query("SELECT COUNT(u) > 0 FROM User u WHERE u.nickname = :nickname AND u.id <> :excludeId AND u.deletedAt IS NULL")
    boolean existsByNicknameExcludingUser(@Param("nickname") String nickname, @Param("excludeId") Long excludeId);
}
