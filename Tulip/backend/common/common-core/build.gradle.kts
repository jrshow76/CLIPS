/*
 * common-core
 *
 * Tulip+ 전 서비스가 공유하는 표준 응답/에러/예외/페이지네이션 모델을 제공한다.
 * 다른 common-* 모듈도 본 모듈에 의존한다.
 */
plugins {
    id("tulip.java-library")
}

dependencies {
    implementation("com.fasterxml.jackson.core:jackson-annotations")
    implementation("com.fasterxml.jackson.core:jackson-databind")
    implementation("org.apache.commons:commons-lang3")
}
