/*
 * tenant-service (Sprint 1-C)
 *
 * 테넌트/라이브러리/분관/테넌트 설정 마스터 + Outbox 이벤트 발행.
 *
 * 책임:
 *   - 테넌트 CRUD 및 시스템 관리자 전용 API (SYS_ADMIN bypass)
 *   - 라이브러리·분관 CRUD (RLS tenant_id 격리)
 *   - 테넌트 설정 KV 관리
 *   - tnt_outbox -> Kafka 도메인 이벤트 발행 (Polling Publisher)
 *   - PostgreSQL RLS 세션 변수 자동 적용 (MyBatis Interceptor)
 *   - 내부 서비스용 read-only 엔드포인트 (SCOPE_internal)
 *
 * 포트: 8102
 */
plugins {
    id("tulip.java-library")
    id("org.springframework.boot")
}

// Spring Boot 실행 jar 만 사용 — plain jar 비활성.
tasks.named<Jar>("jar") { enabled = false }
tasks.named("bootJar") { enabled = true }

val mybatisStarterVersion: String = providers.gradleProperty("mybatisStarterVersion").get()
val postgresqlDriverVersion: String = providers.gradleProperty("postgresqlDriverVersion").get()
val flywayVersion: String = providers.gradleProperty("flywayVersion").get()
val testcontainersVersion: String = providers.gradleProperty("testcontainersVersion").get()
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
    implementation("org.springframework.boot:spring-boot-starter-actuator")
    implementation("org.springframework.boot:spring-boot-starter-aop")

    // MyBatis + JDBC + Postgres
    implementation("org.mybatis.spring.boot:mybatis-spring-boot-starter:$mybatisStarterVersion")
    implementation("org.springframework.boot:spring-boot-starter-jdbc")
    implementation("org.postgresql:postgresql:$postgresqlDriverVersion")

    // Flyway (DBA 가 V1__tenant_init.sql 제공)
    implementation("org.flywaydb:flyway-core:$flywayVersion")
    implementation("org.flywaydb:flyway-database-postgresql:$flywayVersion")

    // Kafka (Outbox publisher)
    implementation("org.springframework.kafka:spring-kafka")

    // OpenAPI
    implementation("org.springdoc:springdoc-openapi-starter-webmvc-ui:$springdocVersion")

    testImplementation("org.springframework.security:spring-security-test")
    testImplementation("org.springframework.kafka:spring-kafka-test")
    testImplementation("org.testcontainers:testcontainers:$testcontainersVersion")
    testImplementation("org.testcontainers:junit-jupiter:$testcontainersVersion")
    testImplementation("org.testcontainers:postgresql:$testcontainersVersion")
    testImplementation("org.testcontainers:kafka:$testcontainersVersion")
    testImplementation("org.awaitility:awaitility")
}

tasks.withType<Test>().configureEach {
    // 통합 테스트(Testcontainers 필요)는 @Tag("integration") 로 분리,
    // 기본 빌드에서는 제외하여 docker 없는 CI 환경도 통과하도록 한다.
    useJUnitPlatform {
        excludeTags("integration")
    }
}

tasks.register<Test>("integrationTest") {
    description = "Testcontainers 가 필요한 통합 테스트"
    group = "verification"
    useJUnitPlatform {
        includeTags("integration")
    }
    shouldRunAfter("test")
}
