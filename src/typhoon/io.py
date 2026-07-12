"""气象站观测数据读写。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from typhoon.config import ROOT

# 标准列名（UTC+8 时次）
REQUIRED_COLUMNS = (
    "time",
    "station_id",
    "station_name",
    "temp_c",
    "pressure_hpa",
    "humidity_pct",
    "wind_speed_ms",
    "wind_gust_ms",
    "wind_dir_deg",
    "precip_1h_mm",
)

SAMPLE_RAW = ROOT / "data" / "raw" / "sample_stations.csv"


def read_station_csv(path: Path | str) -> pd.DataFrame:
    """
    读取气象站 CSV，规范化时间与数值列。

    @param path - CSV 文件路径
    @returns 规范化后的观测 DataFrame
    """
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"缺少必要列: {missing}")

    out = df.copy()
    out["time"] = pd.to_datetime(out["time"])
    out["station_id"] = out["station_id"].astype(str)
    numeric_cols = [
        "temp_c",
        "pressure_hpa",
        "humidity_pct",
        "wind_speed_ms",
        "wind_gust_ms",
        "wind_dir_deg",
        "precip_1h_mm",
    ]
    for col in numeric_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    return out.sort_values(["station_id", "time"]).reset_index(drop=True)


def load_sample_data() -> pd.DataFrame:
    """
    加载仓库内置示例观测数据。

    @returns 示例气象站观测 DataFrame
    """
    if not SAMPLE_RAW.exists():
        raise FileNotFoundError(f"示例数据不存在: {SAMPLE_RAW}")
    return read_station_csv(SAMPLE_RAW)


def write_processed(df: pd.DataFrame, path: Path | str) -> Path:
    """
    将处理后的数据写入 CSV。

    @param df - 待写入 DataFrame
    @param path - 输出路径
    @returns 实际写入路径
    """
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    return out
