"""QA 회귀 테스트 패키지.

본 패키지는 QA가 작성/관리하는 회귀 자동화 테스트를 포함한다.
- 마커: `@pytest.mark.qa`
- 대상: 매매 정책, Kill Switch, 한도, 멱등성, 레이트리밋, 지표 정확성, 페이지네이션, 보안
- 실행: `pytest backend/tests/qa -m qa -v`
- conftest.py 는 상위(`backend/tests/conftest.py`)의 픽스처를 공유한다.
"""
