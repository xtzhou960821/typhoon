"""观测数据清洗与衍生指标。"""

from __future__ import annotations

import pandas as pd


def clean_observations(df: pd.DataFrame) -> pd.DataFrame:
    """
    清洗观测数据：去重、剔除明显异常值。

    @param df - 原始观测 DataFrame
    @returns 清洗后的 DataFrame
    """
    out = df.drop_duplicates(subset=["station_id", "time"]).copy()

    # 物理合理范围过滤（保留 NaN，仅剔除明显越界）
    masks = [
        out["temp_c"].between(-30, 50) | out["temp_c"].isna(),
        out["pressure_hpa"].between(870, 1080) | out["pressure_hpa"].isna(),
        out["humidity_pct"].between(0, 100) | out["humidity_pct"].isna(),
        out["wind_speed_ms"].between(0, 80) | out["wind_speed_ms"].isna(),
        out["wind_gust_ms"].between(0, 100) | out["wind_gust_ms"].isna(),
        out["precip_1h_mm"].between(0, 300) | out["precip_1h_mm"].isna(),
    ]
    valid = masks[0]
    for m in masks[1:]:
        valid &= m
    return out.loc[valid].reset_index(drop=True)


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    添加衍生特征：累计降水、气压变化、阵风比等。

    @param df - 清洗后的观测 DataFrame
    @returns 含衍生列的 DataFrame
    """
    out = df.sort_values(["station_id", "time"]).copy()
    grouped = out.groupby("station_id", group_keys=False)

    out["precip_cumsum_mm"] = grouped["precip_1h_mm"].cumsum()
    out["pressure_delta_3h"] = grouped["pressure_hpa"].diff(3)
    out["wind_gust_ratio"] = out["wind_gust_ms"] / out["wind_speed_ms"].replace(0, pd.NA)
    out["date"] = out["time"].dt.date
    return out.reset_index(drop=True)


def station_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    按站点汇总极值与总量。

    @param df - 含观测与衍生列的 DataFrame
    @returns 站点汇总表
    """
    agg = (
        df.groupby(["station_id", "station_name"], as_index=False)
        .agg(
            temp_min_c=("temp_c", "min"),
            temp_max_c=("temp_c", "max"),
            pressure_min_hpa=("pressure_hpa", "min"),
            pressure_max_hpa=("pressure_hpa", "max"),
            wind_max_ms=("wind_speed_ms", "max"),
            gust_max_ms=("wind_gust_ms", "max"),
            precip_total_mm=("precip_1h_mm", "sum"),
            samples=("time", "count"),
        )
        .sort_values("precip_total_mm", ascending=False)
        .reset_index(drop=True)
    )
    return agg


def filter_time_window(
    df: pd.DataFrame,
    start: str | pd.Timestamp | None = None,
    end: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """
    按时间窗过滤观测。

    @param df - 观测 DataFrame
    @param start - 起始时间（含），可为字符串
    @param end - 结束时间（不含），可为字符串
    @returns 过滤后的 DataFrame
    """
    out = df.copy()
    if start is not None:
        out = out.loc[out["time"] >= pd.Timestamp(start)]
    if end is not None:
        out = out.loc[out["time"] < pd.Timestamp(end)]
    return out.reset_index(drop=True)
