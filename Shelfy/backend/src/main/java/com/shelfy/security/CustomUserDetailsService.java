package com.shelfy.security;

import com.shelfy.user.entity.User;
import com.shelfy.user.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Spring Security UserDetailsService 구현체.
 * JWT 필터에서 userId로 사용자를 조회할 때 사용한다.
 */
@Service
@RequiredArgsConstructor
public class CustomUserDetailsService implements UserDetailsService {

    private final UserRepository userRepository;

    /**
     * 이메일로 사용자 조회 (Spring Security 기본 인터페이스)
     * 탈퇴 계정은 제외하지 않는다 - 로그인 로직에서 직접 검사한다.
     */
    @Override
    @Transactional(readOnly = true)
    public UserDetails loadUserByUsername(String email) throws UsernameNotFoundException {
        User user = userRepository.findByEmail(email)
                .orElseThrow(() -> new UsernameNotFoundException("User not found: " + email));
        return toUserDetails(user);
    }

    /**
     * userId로 사용자 조회 (JWT 필터에서 사용)
     * 탈퇴 계정은 조회 제외하여 탈퇴 후 기존 토큰으로 접근 불가.
     */
    @Transactional(readOnly = true)
    public UserDetails loadUserByUserId(Long userId) {
        User user = userRepository.findActiveById(userId)
                .orElseThrow(() -> new UsernameNotFoundException("User not found: " + userId));
        return toUserDetails(user);
    }

    private CustomUserDetails toUserDetails(User user) {
        return new CustomUserDetails(
                user.getId(),
                user.getEmail(),
                user.getPasswordHash(),
                user.getNickname(),
                user.isEmailVerified(),
                !user.isLocked()
        );
    }
}
