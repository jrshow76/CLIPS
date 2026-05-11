/*
 * api-gateway (Sprint 1-B)
 *
 * Spring Cloud Gateway (WebFlux 기반 reactive) 진입점.
 */
plugins {
    id("tulip.java-library")
    id("org.springframework.boot")
}

tasks.named<Jar>("jar") { enabled = false }
tasks.named("bootJar") { enabled = true }

dependencyManagement {
    imports {
        mavenBom("org.springframework.cloud:spring-cloud-dependencies:" + providers.gradleProperty("springCloudVersion").get())
    }
}

dependencies {
    implementation(project(":common:common-core"))
    implementation(project(":common:common-security"))
    implementation("org.springframework.cloud:spring-cloud-starter-gateway")
    implementation("org.springframework.boot:spring-boot-starter-data-redis-reactive")
    implementation("org.springframework.boot:spring-boot-starter-actuator")
    implementation("org.springdoc:springdoc-openapi-starter-webflux-ui:" + providers.gradleProperty("springdocVersion").get())
    implementation("com.fasterxml.jackson.core:jackson-databind")
    testImplementation("io.projectreactor:reactor-test")
    testImplementation("com.github.tomakehurst:wiremock-jre8-standalone:2.35.2")
}
