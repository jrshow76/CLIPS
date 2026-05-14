"""CSV writer.

- UTF-8 BOM 으로 인코딩(엑셀 한글 깨짐 방지).
- 컬럼명은 한글로 치환.
- 다중 시트가 필요한 경우 시트별 파일을 합쳐 ZIP 으로 묶지 않고,
  본 모듈은 ``write_csv`` 가 단일 DataFrame 만 처리한다.
  XLSX 와 의미적으로 동치인 "메인 시트"만 CSV 로 내보낸다.
"""
from __future__ import annotations

from io import BytesIO
from typing import Iterable, Mapping

import pandas as pd

from app.services.export_engine.formats.header_map import translate_columns


def write_csv(
    df: pd.DataFrame,
    *,
    chunks: Iterable[pd.DataFrame] | None = None,
) -> bytes:
    """DataFrame(또는 청크 iterator) 를 UTF-8 BOM CSV 바이트로 직렬화.

    Args:
        df: 단일 DataFrame. ``chunks`` 가 주어지면 ``df`` 는 컬럼 메타 용으로만
            사용되며 데이터는 청크에서 읽는다.
        chunks: 메모리 절약용 청크 iterator. None 이면 ``df`` 전체를 한 번에 쓴다.

    Returns:
        UTF-8 BOM 포함 CSV 바이트.
    """
    buf = BytesIO()
    # 1. UTF-8 BOM 선두에 직접 기록 (pandas to_csv 의 encoding='utf-8-sig' 동작과 동일하나
    #    바이너리 모드 일관성 위해 명시적으로 작성)
    buf.write(b"\xef\xbb\xbf")

    if chunks is None:
        translated = translate_columns(df)
        translated.to_csv(buf, index=False, encoding="utf-8", lineterminator="\n")
        return buf.getvalue()

    # 청크 처리: 첫 번째 청크에만 헤더 작성
    header_written = False
    for chunk in chunks:
        if chunk is None or chunk.empty:
            continue
        translated = translate_columns(chunk)
        translated.to_csv(
            buf,
            index=False,
            encoding="utf-8",
            lineterminator="\n",
            header=not header_written,
            mode="a",
        )
        header_written = True

    # 행이 0개인 경우: 헤더만이라도 남기기 위해 빈 DataFrame 헤더 작성
    if not header_written:
        translate_columns(df).to_csv(buf, index=False, encoding="utf-8", lineterminator="\n")

    return buf.getvalue()


def write_csv_multi(sheets: Mapping[str, pd.DataFrame]) -> bytes:
    """다중 시트 CSV 대용: 시트 구분자(`# Sheet: ...`) 형태로 직렬 연결.

    XLSX 가 아닌 CSV 포맷에서 다중 시트를 표현하기 위한 절충안이다.
    UI 에서 안내 문구를 함께 보여주는 것을 권장한다.
    """
    buf = BytesIO()
    buf.write(b"\xef\xbb\xbf")
    first = True
    for sheet_name, df in sheets.items():
        if not first:
            buf.write(b"\n")
        # 시트 헤더 줄
        header_line = f"# Sheet: {sheet_name}\n".encode("utf-8")
        buf.write(header_line)
        translate_columns(df).to_csv(buf, index=False, encoding="utf-8", lineterminator="\n")
        first = False
    return buf.getvalue()
