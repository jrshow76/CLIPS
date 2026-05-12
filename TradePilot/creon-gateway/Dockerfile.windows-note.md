# 컨테이너화 불가 안내

CREON Plus는 Windows GUI 의존성 + COM 객체 + 32-bit 프로세스 제약으로
Docker 컨테이너로 실행이 **불가능**하다.

## 대안

1. **로컬 Windows 호스트** (권장)
   - Windows 10/11 Pro 64-bit
   - 32-bit Python 3.11 설치
   - CREON Plus GUI 상시 로그인
   - NSSM으로 윈도우 서비스 등록 (README.md 참조)

2. **Windows Server VM**
   - Hyper-V / VMware / 클라우드(Azure/AWS Windows VM)
   - GPU/디스플레이 의존이 있으므로 RDP 세션 유지 필요

3. **개발/CI 환경**
   - Mock 모드(`CREON_FORCE_MOCK=true`)로 Linux/macOS에서도 실행 가능
   - 실제 주문은 발생하지 않으며, 시뮬레이션 응답을 반환

## 컨테이너화 시도 시 발생 문제

- `pywin32`는 Windows API에 직접 바인딩 → Linux에서 import 불가
- COM 객체는 GUI 세션과 결합 → headless 환경 동작 안 함
- CREON Plus는 32-bit 프로세스만 지원 → 64-bit Docker 이미지 충돌

## 참고

- 본체 백엔드(`backend/`)는 Linux Docker로 정상 동작
- 게이트웨이만 별도 Windows 호스트에서 실행
- 본체 ↔ 게이트웨이 통신은 HTTP + Redis Pub/Sub (사설망)
- 자세한 설계: `docs/23_creon_gateway.md`
