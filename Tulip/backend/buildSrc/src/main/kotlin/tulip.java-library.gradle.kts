/*
 * Tulip+ 공통 Java 라이브러리 convention plugin.
 *
 * - Java 21 toolchain
 * - Spring Boot BOM (dependency-management) 적용
 * - Lombok / SLF4J / Validation API 공통 의존성
 * - UTF-8 인코딩 / 단위 테스트 설정
 */
plugins {
    `java-library`
    id("io.spring.dependency-management")
}

java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(21))
    }
    withSourcesJar()
}

repositories {
    mavenCentral()
}

val springBootVersion: String = providers.gradleProperty("springBootVersion").get()
val lombokVersion: String = providers.gradleProperty("lombokVersion").get()

dependencyManagement {
    imports {
        mavenBom("org.springframework.boot:spring-boot-dependencies:$springBootVersion")
    }
}

dependencies {
    compileOnly("org.projectlombok:lombok:$lombokVersion")
    annotationProcessor("org.projectlombok:lombok:$lombokVersion")
    testCompileOnly("org.projectlombok:lombok:$lombokVersion")
    testAnnotationProcessor("org.projectlombok:lombok:$lombokVersion")

    implementation("org.slf4j:slf4j-api")
    implementation("jakarta.validation:jakarta.validation-api")
    implementation("jakarta.annotation:jakarta.annotation-api")

    testImplementation("org.springframework.boot:spring-boot-starter-test") {
        exclude(group = "org.mockito", module = "mockito-core")
    }
    testImplementation("org.mockito:mockito-core")
    testImplementation("org.junit.jupiter:junit-jupiter")
    testImplementation("org.assertj:assertj-core")
}

tasks.withType<JavaCompile>().configureEach {
    options.encoding = "UTF-8"
    options.compilerArgs.addAll(listOf("-parameters"))
}

tasks.withType<Test>().configureEach {
    useJUnitPlatform()
    systemProperty("file.encoding", "UTF-8")
    testLogging {
        events("passed", "skipped", "failed")
    }
}

// java-library 모듈은 Spring Boot 실행 jar 가 아니므로 bootJar 비활성화.
plugins.withId("org.springframework.boot") {
    tasks.named("bootJar") { enabled = false }
    tasks.named("jar") { enabled = true }
}
