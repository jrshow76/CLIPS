FROM node:20-alpine

WORKDIR /app

# 패키지 파일 복사 후 의존성 설치 (레이어 캐시 활용)
COPY package*.json ./
RUN npm install

# 소스코드 전체 복사
COPY . .

EXPOSE 3000

# 개발 서버 실행 (모든 네트워크 인터페이스에 바인딩)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
