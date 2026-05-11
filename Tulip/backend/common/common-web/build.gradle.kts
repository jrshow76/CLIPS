/*
 * common-web
 *
 * RestControllerAdvice / 필터 체인 / OpenAPI 등 Web 계층 공통 모듈.
 */
plugins {
    id("tulip.java-library")
}

dependencies {
    api(project(":common:common-core"))
    api(project(":common:common-tenant"))

    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("org.springframework.boot:spring-boot-starter-validation")
    implementation("org.springdoc:springdoc-openapi-starter-webmvc-ui:${providers.gradleProperty("springdocVersion").get()}")
}
