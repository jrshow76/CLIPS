package com.tulip.gateway;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Tulip+ API Gateway (Sprint 1-B).
 *
 * <p>Spring Cloud Gateway(WebFlux) 기반. 포트 9100 에서 기동하며 모든 외부 트래픽의 단일 진입점이다.</p>
 */
@SpringBootApplication
public class ApiGatewayApplication {

    public static void main(String[] args) {
        SpringApplication.run(ApiGatewayApplication.class, args);
    }
}
