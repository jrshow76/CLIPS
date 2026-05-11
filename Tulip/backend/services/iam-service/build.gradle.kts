/*
 * iam-service (Sprint 1-B)
 *
 * Identity & Access Management — OAuth2/OIDC BFF + Resource Server.
 *
 * 책임:
 *   - Keycloak Authorization Code + PKCE 흐름의 서버측 broker (login/callback/refresh/logout)
 *   - JWT 검증 (Resource Server)
 *   - 사용자-Keycloak sub 매핑(iam_user_link)
 *   - JTI 블랙리스트 적재 (Redis)
 *   - Federation SPI (1-B.9 BackendDev 가 어댑터 구현)
 *   - MFA TOTP 인터페이스 골격 (1-B.8 Phase 2 활성화)
 */
plugins {
    id("tulip.java-library")
    id("org.springframework.boot")
}

// 본 서비스는 boot jar 가 실행 대상이므로 jar 비활성, bootJar 만 enable.
tasks.named<Jar>("jar") { enabled = false }
tasks.named("bootJar") { enabled = true }

dependencies {
    implementation(project(":common:common-core"))
    implementation(project(":common:common-web"))
    implementation(project(":common:common-security"))
    implementation(project(":common:common-tenant"))
    implementation(project(":common:common-data"))

    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("org.springframework.boot:spring-boot-starter-validation")
    implementation("org.springframework.boot:spring-boot-starter-security")
    implementation("org.springframework.boot:spring-boot-starter-oauth2-resource-server")
    implementation("org.springframework.boot:spring-boot-starter-oauth2-client")
    implementation("org.springframework.boot:spring-boot-starter-data-redis")
    implementation("org.springframework.boot:spring-boot-starter-jdbc")
    implementation("org.springframework.boot:spring-boot-starter-actuator")
    implementation("org.springdoc:springdoc-openapi-starter-webmvc-ui:${providers.gradleProperty("springdocVersion").get()}")

    implementation("org.postgresql:postgresql:${providers.gradleProperty("postgresqlDriverVersion").get()}")
    implementation("org.flywaydb:flyway-core:${providers.gradleProperty("flywayVersion").get()}")
    implementation("org.flywaydb:flyway-database-postgresql:${providers.gradleProperty("flywayVersion").get()}")

    testImplementation("org.springframework.security:spring-security-test")
    testImplementation("com.github.tomakehurst:wiremock-jre8-standalone:2.35.2")
    testImplementation("org.testcontainers:testcontainers:${providers.gradleProperty("testcontainersVersion").get()}")
    testImplementation("org.testcontainers:junit-jupiter:${providers.gradleProperty("testcontainersVersion").get()}")
    testImplementation("com.redis.testcontainers:testcontainers-redis-junit:1.6.4")
    testImplementation("org.awaitility:awaitility")
}
