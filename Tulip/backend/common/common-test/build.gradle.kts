/*
 * common-test
 *
 * 통합 테스트 유틸리티 및 Testcontainers 베이스 모듈.
 * PostgreSQL/Redis/Kafka 컨테이너 헬퍼와 공통 픽스처를 제공한다.
 */
plugins {
    id("tulip.java-library")
}

val testcontainersVersion: String = providers.gradleProperty("testcontainersVersion").get()

dependencies {
    api(project(":common:common-core"))
    api(project(":common:common-tenant"))

    api("org.springframework.boot:spring-boot-starter-test") {
        exclude(group = "org.mockito", module = "mockito-core")
    }
    api("org.mockito:mockito-core")
    api("org.junit.jupiter:junit-jupiter")
    api("org.assertj:assertj-core")

    api("org.testcontainers:testcontainers:$testcontainersVersion")
    api("org.testcontainers:junit-jupiter:$testcontainersVersion")
    api("org.testcontainers:postgresql:$testcontainersVersion")
    api("org.testcontainers:kafka:$testcontainersVersion")
}
