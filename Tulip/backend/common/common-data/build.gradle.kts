/*
 * common-data
 *
 * MyBatis 베이스, BaseDomain, AuditingHandler, TypeHandler, RLS 헬퍼.
 */
plugins {
    id("tulip.java-library")
}

val mybatisStarterVersion: String = providers.gradleProperty("mybatisStarterVersion").get()
val postgresqlDriverVersion: String = providers.gradleProperty("postgresqlDriverVersion").get()

dependencies {
    api(project(":common:common-core"))
    api(project(":common:common-tenant"))

    implementation("org.springframework.boot:spring-boot-starter-jdbc")
    implementation("org.mybatis.spring.boot:mybatis-spring-boot-starter:$mybatisStarterVersion")
    implementation("org.postgresql:postgresql:$postgresqlDriverVersion")
    implementation("com.fasterxml.jackson.core:jackson-databind")
}
