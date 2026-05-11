package com.tulip.iam;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Tulip+ IAM Service (Sprint 1-B).
 *
 * <p>OAuth2 BFF + Resource Server. 포트 8101 에서 기동.
 * Keycloak 과의 브로커 역할을 수행하며, Refresh 토큰은 HttpOnly 쿠키로만 유지한다.</p>
 */
@SpringBootApplication
public class IamServiceApplication {

    public static void main(String[] args) {
        SpringApplication.run(IamServiceApplication.class, args);
    }
}
