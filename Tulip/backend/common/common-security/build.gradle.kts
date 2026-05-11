/*
 * common-security
 *
 * JWT 검증, SecurityConfig 베이스, TulipUserPrincipal, JWKS 캐시 검증기,
 * JTI 블랙리스트 인터페이스, 표준 인증/인가 ApiResponse 매핑 등 보안 공통 모듈.
 *
 * 토큰 발급은 service-auth(Phase 1-B iam-service)에서 수행하며 본 모듈은
 * 검증·표준 매핑 책임만 진다.
 */
plugins {
    id("tulip.java-library")
}

val jjwtVersion: String = providers.gradleProperty("jjwtVersion").get()

dependencies {
    api(project(":common:common-core"))
    api(project(":common:common-tenant"))

    implementation("org.springframework.boot:spring-boot-starter-security")
    implementation("org.springframework.boot:spring-boot-starter-oauth2-resource-server")
    implementation("org.springframework.security:spring-security-oauth2-jose")
    implementation("com.fasterxml.jackson.core:jackson-databind")
    // 핸들러는 servlet 환경 전용 (reactive 환경은 Gateway 가 자체 처리)
    compileOnly("jakarta.servlet:jakarta.servlet-api")

    implementation("io.jsonwebtoken:jjwt-api:$jjwtVersion")
    runtimeOnly("io.jsonwebtoken:jjwt-impl:$jjwtVersion")
    runtimeOnly("io.jsonwebtoken:jjwt-jackson:$jjwtVersion")

    testImplementation("org.springframework.boot:spring-boot-starter-web")
}
