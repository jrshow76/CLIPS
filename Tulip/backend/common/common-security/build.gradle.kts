/*
 * common-security
 *
 * JWT 검증, SecurityConfig 베이스, TulipUserPrincipal 제공.
 * 토큰 발급은 service-auth(Phase 1-B)에서 수행하며 본 모듈은 검증 책임만 진다.
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

    implementation("io.jsonwebtoken:jjwt-api:$jjwtVersion")
    runtimeOnly("io.jsonwebtoken:jjwt-impl:$jjwtVersion")
    runtimeOnly("io.jsonwebtoken:jjwt-jackson:$jjwtVersion")
}
