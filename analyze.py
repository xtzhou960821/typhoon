"""台风巴威气象站数据分析。

读取气象站观测数据(风速、阵风、气压、降水、气温),计算各站点的关键统计量,
识别台风影响最强的站点与时刻,并绘制风速与气压随时间变化的图表。

用法::

    python analyze.py [--data data/weather_stations_bavi.csv] [--output output]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 无图形界面环境下使用非交互后端

import matplotlib.pyplot as plt
import pandas as pd

# 中文字体在多数无头环境中缺失,图表统一使用英文标签避免乱码,同时关闭负号异常显示
plt.rcParams["axes.unicode_minus"] = False

# 站点在图表中使用的英文标注(控制台仍输出中文站名)
STATION_LABELS = {
    "S01": "S01 (Coastal)",
    "S02": "S02 (Inland)",
    "S03": "S03 (Mountain)",
}


def load_data(data_path: Path) -> pd.DataFrame:
    """加载气象站观测数据。

    :param data_path: CSV 数据文件路径。
    :returns: 已按站点与时间排序、且 ``datetime`` 列为时间类型的数据框。
    :raises FileNotFoundError: 当数据文件不存在时抛出。
    """
    if not data_path.exists():
        raise FileNotFoundError(f"未找到数据文件: {data_path}")

    frame = pd.read_csv(data_path, parse_dates=["datetime"])
    return frame.sort_values(["station_id", "datetime"]).reset_index(drop=True)


def summarize(frame: pd.DataFrame) -> pd.DataFrame:
    """按站点汇总关键气象要素。

    :param frame: 原始观测数据框。
    :returns: 每个站点一行的汇总数据框,包含峰值风速/阵风、最低气压、累计降水等。
    """
    grouped = frame.groupby(["station_id", "station_name"], sort=False)
    summary = grouped.agg(
        peak_wind_ms=("wind_speed_ms", "max"),
        peak_gust_ms=("gust_ms", "max"),
        min_pressure_hpa=("pressure_hpa", "min"),
        total_rainfall_mm=("rainfall_mm", "sum"),
        min_temperature_c=("temperature_c", "min"),
    )

    # 记录最低气压出现的时刻,通常对应台风影响最强的时段
    landfall_times = (
        frame.loc[grouped["pressure_hpa"].idxmin(), ["station_id", "datetime"]]
        .set_index("station_id")["datetime"]
    )
    summary = summary.reset_index()
    summary["peak_impact_time"] = summary["station_id"].map(landfall_times)
    return summary


def plot_timeseries(frame: pd.DataFrame, output_path: Path) -> Path:
    """绘制各站点风速与气压随时间变化的双子图。

    :param frame: 原始观测数据框。
    :param output_path: 图片输出文件路径(PNG)。
    :returns: 实际写入的图片路径。
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, (ax_wind, ax_pressure) = plt.subplots(2, 1, figsize=(11, 8), sharex=True)

    for station_id, station in frame.groupby("station_id", sort=False):
        label = STATION_LABELS.get(station_id, station_id)
        ax_wind.plot(station["datetime"], station["wind_speed_ms"], marker="o", label=label)
        ax_pressure.plot(station["datetime"], station["pressure_hpa"], marker="o", label=label)

    ax_wind.set_title("Typhoon Bavi (2026-07-11): Wind Speed by Station")
    ax_wind.set_ylabel("Wind speed (m/s)")
    ax_wind.grid(True, alpha=0.3)
    ax_wind.legend()

    ax_pressure.set_title("Sea-level Pressure by Station")
    ax_pressure.set_ylabel("Pressure (hPa)")
    ax_pressure.set_xlabel("Time")
    ax_pressure.grid(True, alpha=0.3)
    ax_pressure.legend()

    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_path, dpi=120)
    plt.close(fig)
    return output_path


def main() -> None:
    """命令行入口:加载数据、打印汇总并输出图表。"""
    parser = argparse.ArgumentParser(description="台风巴威气象站数据分析")
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("data/weather_stations_bavi.csv"),
        help="气象站观测数据 CSV 路径",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output"),
        help="图表输出目录",
    )
    args = parser.parse_args()

    frame = load_data(args.data)
    print(f"已加载 {len(frame)} 条观测记录,覆盖 {frame['station_id'].nunique()} 个气象站。\n")

    summary = summarize(frame)
    print("各站点汇总:")
    print(summary.to_string(index=False))

    worst = summary.loc[summary["min_pressure_hpa"].idxmin()]
    print(
        f"\n受台风影响最强的站点: {worst['station_id']} ({worst['station_name']}),"
        f"最低气压 {worst['min_pressure_hpa']} hPa,"
        f"峰值阵风 {worst['peak_gust_ms']} m/s,"
        f"出现于 {worst['peak_impact_time']}。"
    )

    image_path = plot_timeseries(frame, args.output / "typhoon_bavi_analysis.png")
    print(f"\n图表已保存至: {image_path.resolve()}")


if __name__ == "__main__":
    main()
