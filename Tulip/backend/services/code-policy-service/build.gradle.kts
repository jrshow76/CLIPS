/*
 * code-policy-service (Sprint 1-C)
 *
 * 코드 마스터 + 정책(대출/예약/연체/출입/시설) 관리 마이크로서비스.
 *
 * 책임:
 *   - 코드 그룹/코드 CRUD (글로벌 + 테넌트 코드)
 *   - 정책 CRUD + 정책 할당 (라이브러리·회원유형·자료유형)
 *   - 효력 정책 평가 (/policies/effective)
 *   - 글로벌 코드 Redis 캐시 (PostConstruct 적재, 변경 시 무효화)
 *   - 변경 시 cd_outbox 적재 → Kafka 발행 (code.*, policy.*)
 *
 * 포트: 8104
 */
plugins {
    id("tulip.java-library")
    id("org.springframework.boot")
}

// boot jar 실행 대상 — 일반 jar 비활성.
tasks.named<Jar>("jar") { enabled = false }
tasks.named("bootJar") { enabled = true }

val mybatisStarterVersion: String = providers.gradleProperty("mybatisStarterVersion").get()
val testcontainersVersion: String = providers.gradleProperty("testcontainersVersion").get()
val postgresqlDriverVersion: String = providers.gradleProperty("postgresqlDriverVersion").get()
val flywayVersion: String = providers.gradleProperty("flywayVersion").get()
val springdocVersion: String = providers.gradleProperty("springdocVersion").get()

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
    implementation("org.springframework.boot:spring-boot-starter-data-redis")
    implementation("org.springframework.boot:spring-boot-starter-jdbc")
    implementation("org.springframework.boot:spring-boot-starter-actuator")
    implementation("org.springframework.kafka:spring-kafka")
    implementation("org.mybatis.spring.boot:mybatis-spring-boot-starter:$mybatisStarterVersion")
    implementation("org.springdoc:springdoc-openapi-starter-webmvc-ui:$springdocVersion")

    implementation("org.postgresql:postgresql:$postgresqlDriverVersion")
    implementation("org.flywaydb:flyway-core:$flywayVersion")
    implementation("org.flywaydb:flyway-database-postgresql:$flywayVersion")
    implementation("com.fasterxml.jackson.core:jackson-databind")

    testImplementation(project(":common:common-test"))
    testImplementation("org.springframework.security:spring-security-test")
    testImplementation("org.testcontainers:postgresql:$testcontainersVersion")
}

tasks.withType<Test>().configureEach {
    // 통합 테스트 분리 — 기본 빌드에서는 단위 테스트만 실행.
    useJUnitPlatform {
        excludeTags("integration")
    }
}
