package com.tulip.member.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.json.JsonMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.tulip.common.security.jwt.JwksJwtTokenProvider;
import com.tulip.common.security.jwt.JwtTokenProvider;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.Set;

/**
 * member-service 의 인프라 빈 구성.
 *
 * <p>Properties · JWT · ObjectMapper · KafkaTemplate 은 Spring Boot 자동구성을 사용한다.
 * 본 클래스는 자동구성 외 커스터마이즈가 필요한 빈만 정의한다.</p>
 */
@Configuration
@EnableConfigurationProperties({MemberProperties.class, IamProperties.class})
public class MemberConfig {

    /** JWT(JWKS) 검증기. iam-service 와 동일한 issuer 를 사용한다. */
    @Bean
    public JwtTokenProvider jwtTokenProvider(IamProperties props) {
        Set<String> aud = props.getExpectedAudiences() == null ? Set.of() : props.getExpectedAudiences();
        return new JwksJwtTokenProvider(props.getJwksUri(), props.getIssuerUri(), aud);
    }

    /** JSR-310 시간 타입 직렬화 대응 ObjectMapper. */
    @Bean
    public ObjectMapper memberObjectMapper() {
        return JsonMapper.builder()
                .addModule(new JavaTimeModule())
                .build();
    }
}
