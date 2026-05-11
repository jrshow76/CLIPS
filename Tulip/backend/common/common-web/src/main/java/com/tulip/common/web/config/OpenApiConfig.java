package com.tulip.common.web.config;

import io.swagger.v3.oas.models.Components;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.License;
import io.swagger.v3.oas.models.security.SecurityRequirement;
import io.swagger.v3.oas.models.security.SecurityScheme;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * springdoc-openapi 기본 설정.
 *
 * <p>각 서비스가 본 설정을 import 하면 표준 메타데이터(title/version/bearer auth)가 적용된다.
 * 서비스별 추가 태그/서버는 자체 Configuration 에서 확장한다.</p>
 */
@Configuration
public class OpenApiConfig {

    private static final String SECURITY_SCHEME = "bearerAuth";

    @Bean
    public OpenAPI tulipOpenApi(@Value("${spring.application.name:tulip-service}") String appName,
                                @Value("${tulip.api.version:1.0.0}") String version) {
        return new OpenAPI()
                .info(new Info()
                        .title("Tulip+ " + appName + " API")
                        .version(version)
                        .description("Tulip+ 도서관통합관리시스템 — " + appName)
                        .contact(new Contact().name("DevLead").email("devlead@tulip.example.com"))
                        .license(new License().name("Proprietary")))
                .addSecurityItem(new SecurityRequirement().addList(SECURITY_SCHEME))
                .components(new Components()
                        .addSecuritySchemes(SECURITY_SCHEME, new SecurityScheme()
                                .type(SecurityScheme.Type.HTTP)
                                .scheme("bearer")
                                .bearerFormat("JWT")
                                .description("OAuth2 Access Token (RS256)")));
    }
}
