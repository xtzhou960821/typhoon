"""``analyze`` 模块的单元测试。"""

from pathlib import Path

import pandas as pd

import analyze


def _sample_frame() -> pd.DataFrame:
    """构造一个最小的两站点观测数据框用于测试。

    :returns: 含两个站点、各两条记录的数据框。
    """
    return pd.DataFrame(
        {
            "station_id": ["S01", "S01", "S02", "S02"],
            "station_name": ["沿海站", "沿海站", "内陆站", "内陆站"],
            "datetime": pd.to_datetime(
                [
                    "2026-07-11 00:00",
                    "2026-07-11 01:00",
                    "2026-07-11 00:00",
                    "2026-07-11 01:00",
                ]
            ),
            "wind_speed_ms": [10, 20, 5, 8],
            "gust_ms": [15, 30, 8, 12],
            "pressure_hpa": [1000, 980, 1005, 1002],
            "rainfall_mm": [3, 7, 1, 2],
            "temperature_c": [26, 25, 28, 27],
        }
    )


def test_summarize_computes_expected_aggregates() -> None:
    """校验汇总函数对峰值、最低气压与累计降水的计算。"""
    summary = analyze.summarize(_sample_frame()).set_index("station_id")

    assert summary.loc["S01", "peak_wind_ms"] == 20
    assert summary.loc["S01", "peak_gust_ms"] == 30
    assert summary.loc["S01", "min_pressure_hpa"] == 980
    assert summary.loc["S01", "total_rainfall_mm"] == 10
    # 最低气压出现的时刻应对应第二条记录
    assert str(summary.loc["S01", "peak_impact_time"]) == "2026-07-11 01:00:00"


def test_load_data_missing_file_raises(tmp_path: Path) -> None:
    """当数据文件不存在时应抛出 ``FileNotFoundError``。"""
    missing = tmp_path / "does_not_exist.csv"
    try:
        analyze.load_data(missing)
    except FileNotFoundError:
        return
    raise AssertionError("缺失文件时未抛出 FileNotFoundError")


def test_bundled_dataset_loads() -> None:
    """随仓库分发的示例数据集应可正常加载且非空。"""
    frame = analyze.load_data(Path("data/weather_stations_bavi.csv"))
    assert not frame.empty
    assert set(["station_id", "wind_speed_ms", "pressure_hpa"]).issubset(frame.columns)
