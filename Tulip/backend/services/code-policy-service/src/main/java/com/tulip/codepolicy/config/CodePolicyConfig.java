package com.tulip.codepolicy.config;

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
 * code-policy-service 인프라 빈 구성.
 */
@Configuration
@EnableConfigurationProperties({CodePolicyProperties.class, IamProperties.class})
public class CodePolicyConfig {

    @Bean
    public JwtTokenProvider jwtTokenProvider(IamProperties props) {
        Set<String> aud = props.getExpectedAudiences() == null ? Set.of() : props.getExpectedAudiences();
        return new JwksJwtTokenProvider(props.getJwksUri(), props.getIssuerUri(), aud);
    }

    @Bean
    public ObjectMapper codePolicyObjectMapper() {
        return JsonMapper.builder().addModule(new JavaTimeModule()).build();
    }
}
