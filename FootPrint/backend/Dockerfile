# ── Stage 1: Build ──────────────────────────────────────────────────────────
FROM gradle:8.7-jdk17-alpine AS builder

WORKDIR /app

# 의존성 캐시를 위해 gradle 파일 먼저 복사
COPY build.gradle settings.gradle ./
RUN gradle dependencies --no-daemon --quiet 2>/dev/null || true

# 소스 전체 복사 후 빌드
COPY src ./src
RUN gradle bootJar --no-daemon -x test

# ── Stage 2: Run ─────────────────────────────────────────────────────────────
FROM eclipse-temurin:17-jre-alpine AS runner

WORKDIR /app

RUN apk add --no-cache curl && \
    addgroup -S appgroup && adduser -S appuser -G appgroup

COPY --from=builder /app/build/libs/*.jar app.jar

RUN mkdir -p /app/uploads && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "-Djava.security.egd=file:/dev/./urandom", "app.jar"]
