/*
 * Tulip+ Backend — buildSrc
 *
 * 모든 subproject 에 공통 적용되는 convention plugin 을 빌드한다.
 */
plugins {
    `kotlin-dsl`
}

repositories {
    gradlePluginPortal()
    mavenCentral()
}

dependencies {
    // Spring Boot / Dependency Management plugin
    implementation("org.springframework.boot:spring-boot-gradle-plugin:3.3.5")
    implementation("io.spring.gradle:dependency-management-plugin:1.1.6")
}
