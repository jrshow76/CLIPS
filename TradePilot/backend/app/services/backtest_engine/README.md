# Backtest Engine

TradePilot 백테스트 엔진. **Vectorized + Event-Driven 하이브리드** 구조.

## 구조

```
backtest_engine/
├── __init__.py         # 외부 API: run_backtest, BacktestConfig, BacktestResult, TradeRecord
├── config.py           # 입력/출력 데이터클래스, 한국 시장 기본 상수
├── data_loader.py      # price_daily 로드, 합성 데이터 fallback
├── indicators.py       # 전체 시리즈 사전 계산 (MA/RSI/MACD/BB/ATR)
├── portfolio.py        # 현금/포지션/거래내역/수수료/세금 추적
├── executor.py         # 시그널 → 주문 이벤트 드리븐 루프
├── metrics.py          # CAGR/Sharpe/MDD/WinRate/ProfitFactor/월별수익률
├── runner.py           # 진입점 (run_backtest)
└── strategies/
    ├── base.py             # Strategy 추상 클래스
    ├── registry.py         # name → 클래스 매핑
    ├── golden_cross.py     # MA 골든/데드크로스
    ├── rsi_reversal.py     # RSI 30/70 역추세
    ├── macd_cross.py       # MACD 시그널 라인 교차
    ├── bollinger_breakout.py  # 볼린저 돌파/회귀
    └── composite.py        # entry/exit_rules JSONB DSL 조합
```

## 데이터 흐름

```
BacktestConfig
   │
   ▼
data_loader.load_daily_prices    ── price_daily (DB)
   │  (dict[code, DataFrame])
   ▼
indicators.attach_indicators     ── vectorized 지표 부착
   │
   ▼
strategy.generate_signals        ── pd.Series(-1/0/1), shift(1) 적용
   │
   ▼
BacktestExecutor.run             ── 거래일 순회, Portfolio 갱신, mark-to-market
   │
   ▼
metrics.compute_metrics          ── 결과 메트릭 + equity_curve
   │
   ▼
BacktestResult                   ── 서비스 레이어가 DB 저장
```

## 한국 시장 관습

| 항목 | 기본값 | 출처 |
|---|---|---|
| 수수료 | 0.015% | 대신증권 영업점 외 기본 |
| 슬리피지 | 0.05% | 시장가 가정 |
| 매도세 | 0.23% | KOSPI (KOSDAQ 0.18% 별도) |
| 거래단위 | 1주 | (소수점 매매 미지원) |

매도세는 매도 시 거래대금에 일률 적용. 매수에는 미적용.

## 전략 플러그인 추가 방법

```python
# strategies/my_strategy.py
import pandas as pd
from app.services.backtest_engine.strategies.base import Strategy
from app.services.backtest_engine.strategies.registry import register_strategy


class MyStrategy(Strategy):
    name = "my_strategy"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        # df 에는 ma5, ma20, rsi14, macd, bb_upper 등이 부착되어 있음
        # 반환은 1=매수, -1=매도, 0=홀드 의 정수 Series
        ...
        return signals.shift(1).fillna(0).astype("int8")


register_strategy("my_strategy", MyStrategy)
```

그리고 `strategies/__init__.py` 에 import 추가하면 자동 등록된다.

## Look-ahead Bias 방지

- 시그널은 t 시점 데이터로 계산하지만 모두 `shift(1)` 적용 → t+1 봉에서 체결.
- `execution_lag="next_open"` 옵션 시 추가로 다음 봉 시가 사용.

## 한계 (v1.0 미반영 사항)

- **분봉 백테스트** 미지원 (현재는 일봉만)
- **부분 체결** 미지원 (시장가 전량 체결 가정)
- **호가 갭** 무시 (실제 슬리피지보다 낙관적 가능성)
- **배당/증자/액면분할** 미반영 (`corporate_actions` 미적용)
- **상한가/하한가** 도달 시 거부 시뮬레이션 없음
- **마진 거래/공매도** 미지원
- **세금** 코스피만 반영, ETF/ELS 세율 별도 처리 필요

## 진행률 콜백

`run_backtest(config, db, progress_cb)` 의 `progress_cb`는 0~100 사이 정수를 받는 콜백.

워커는 5% 단위로만 DB `backtest_runs.progress` 컬럼을 갱신해 비용을 절감한다.

## 메모리/성능

- 5년 일봉 1종목 ≈ 1,250행. 100 종목도 약 130MB 이내.
- 지표 사전 계산은 pandas vectorized.
- 이벤트 루프는 거래일 수 × 종목 수 만큼 반복 (5년 × 100종목 ≈ 125,000회).
- 단일 종목 5년 백테스트 < 1초.
