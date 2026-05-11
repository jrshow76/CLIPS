# Tulip+ Frontend Monorepo — 편의 명령
# 모든 명령은 본 디렉토리(Tulip/frontend) 기준.

.PHONY: help install dev dev-admin dev-opac build build-packages build-apps lint typecheck format clean reset

help:
	@echo "Tulip+ Frontend - 사용 가능한 명령"
	@echo "  make install        : 의존성 설치 (pnpm)"
	@echo "  make dev            : admin + opac 동시 개발 서버"
	@echo "  make dev-admin      : admin 개발 서버 (3000)"
	@echo "  make dev-opac       : opac 개발 서버 (3001)"
	@echo "  make build          : 전체 빌드"
	@echo "  make build-packages : 패키지만 빌드"
	@echo "  make build-apps     : 앱만 빌드"
	@echo "  make lint           : 전체 lint"
	@echo "  make typecheck      : 전체 타입체크"
	@echo "  make format         : Prettier 포매팅"
	@echo "  make clean          : 빌드 산출물 삭제"
	@echo "  make reset          : node_modules + 캐시 + lock 초기화"

install:
	pnpm install

dev:
	pnpm run dev

dev-admin:
	pnpm --filter @tulip/admin dev

dev-opac:
	pnpm --filter @tulip/opac dev

build: build-packages build-apps

build-packages:
	pnpm -r --filter "./packages/*" run build

build-apps:
	pnpm -r --filter "./apps/*" run build

lint:
	pnpm run lint

typecheck:
	pnpm run typecheck

format:
	pnpm run format

clean:
	pnpm run clean

reset:
	rm -rf node_modules .turbo apps/*/node_modules apps/*/.next apps/*/.turbo packages/*/node_modules packages/*/dist packages/*/.turbo pnpm-lock.yaml
