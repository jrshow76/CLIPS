# =====================================================================
# Tulip+ Backend — Developer Shortcuts
# =====================================================================

COMPOSE ?= docker compose
GRADLE  ?= ./gradlew

.PHONY: help up down logs ps nuke build test clean wrapper seed psql

help: ## 본 Makefile 의 사용 가능한 명령을 표시한다
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

## --------- 인프라 ---------
up: ## 로컬 인프라를 백그라운드로 기동
	$(COMPOSE) up -d

down: ## 인프라 컨테이너 종료 (볼륨 유지)
	$(COMPOSE) down

logs: ## 모든 컨테이너 로그 실시간 출력
	$(COMPOSE) logs -f

ps: ## 컨테이너 상태 확인
	$(COMPOSE) ps

nuke: ## 컨테이너 + 볼륨 모두 제거 (데이터 초기화)
	$(COMPOSE) down -v

## --------- 애플리케이션 ---------
build: ## 전체 모듈 빌드 (테스트 포함)
	$(GRADLE) build

assemble: ## 테스트 제외 빌드
	$(GRADLE) assemble

test: ## 모든 단위/통합 테스트 실행
	$(GRADLE) test

clean: ## 빌드 산출물 정리
	$(GRADLE) clean

wrapper: ## Gradle Wrapper 생성 (gradle 8.10)
	gradle wrapper --gradle-version 8.10

## --------- DB ---------
seed: ## V1 마이그레이션을 psql 로 직접 적용 (Flyway 미설정 시 임시 사용)
	$(COMPOSE) exec -T postgres psql -U tulip -d tulip < db/migration/V1__init_common.sql

psql: ## tulip DB 에 psql 접속
	$(COMPOSE) exec postgres psql -U tulip -d tulip
