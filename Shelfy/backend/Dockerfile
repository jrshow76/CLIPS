# ===== Build Stage =====
FROM gradle:8.7-jdk17-alpine AS builder

WORKDIR /app

COPY build.gradle settings.gradle ./

# 의존성 레이어 캐시를 위해 소스 전에 다운로드
RUN gradle dependencies --no-daemon

COPY src src
RUN gradle bootJar --no-daemon

# ===== Runtime Stage =====
FROM eclipse-temurin:17-jre-alpine AS runtime

WORKDIR /app

# 보안: 비root 사용자 실행
RUN addgroup -S shelfy && adduser -S shelfy -G shelfy

COPY --from=builder /app/build/libs/*.jar app.jar

RUN chown shelfy:shelfy app.jar
USER shelfy

EXPOSE 8080

ENTRYPOINT ["java", \
  "-XX:+UseContainerSupport", \
  "-XX:MaxRAMPercentage=75.0", \
  "-Djava.security.egd=file:/dev/./urandom", \
  "-jar", "app.jar"]
