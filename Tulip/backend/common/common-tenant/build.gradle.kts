/*
 * common-tenant
 *
 * TenantContext, TenantContextFilter, @RequiresTenant 어노테이션 제공.
 * 멀티테넌트 격리 정책의 코드 단 첫 단계.
 */
plugins {
    id("tulip.java-library")
}

dependencies {
    api(project(":common:common-core"))

    implementation("org.springframework:spring-web")
    implementation("org.springframework:spring-context")
    implementation("jakarta.servlet:jakarta.servlet-api")
}
