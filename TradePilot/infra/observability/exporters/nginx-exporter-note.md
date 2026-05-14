# nginx-exporter 활성화 가이드

> 작성자: DevLead
> 대상: BackendSenior / DevOps
> 본 파일은 가이드 문서이며 nginx 설정 자체는 `infra/nginx/` 디렉토리의 담당자가 수정한다.

## 1. nginx `stub_status` 모듈 활성화

`infra/nginx/conf.d/_status.conf` 를 신규 생성한다 (별도 PR).

```nginx
# stub_status 는 사설망에서만 접근 가능해야 한다.
server {
    listen 127.0.0.1:8081 default_server;
    server_name localhost;
    access_log off;

    location = /stub_status {
        stub_status on;
        allow 127.0.0.1;
        allow 172.16.0.0/12;       # docker compose 내부 네트워크
        deny  all;
    }
}
```

`nginx -t && nginx -s reload` 로 적용.

## 2. nginx-exporter 컨테이너

`docker-compose.observability.yml` 에 다음 서비스가 정의되어 있다:

```yaml
nginx-exporter:
  image: nginx/nginx-prometheus-exporter:1.1.0
  command:
    - "--nginx.scrape-uri=http://nginx:8081/stub_status"
  expose:
    - "9113"
```

## 3. 노출 지표 (주요)

| 지표 | 의미 |
|---|---|
| `nginx_http_requests_total` | 누적 요청 수 |
| `nginx_connections_active` | 활성 연결 |
| `nginx_connections_reading` | 읽는 중 |
| `nginx_connections_writing` | 쓰는 중 |
| `nginx_connections_waiting` | keep-alive 대기 |
| `nginx_connections_accepted` | 누적 accept |
| `nginx_connections_handled` | 누적 handled |

## 4. 한계 및 보강

- `stub_status` 는 상태 코드별/엔드포인트별 분포를 제공하지 않는다.
- 상세 분석은 nginx access log → Promtail → Loki 로 보강한다 (`promtail.yml` 의 nginx 매처 참조).
- VTS 모듈을 빌드하면 상태 코드별/zone 별 지표 노출 가능하나, 표준 nginx 이미지에는 미포함.
