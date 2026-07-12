"""分析流程编排：清洗 → 衍生 → 汇总 → 出图。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from typhoon.config import ensure_output_dirs, load_config
from typhoon.io import load_sample_data, read_station_csv, write_processed
from typhoon.process import add_derived_features, clean_observations, filter_time_window, station_summary
from typhoon.viz import plot_precip_comparison, plot_station_timeseries


def run_pipeline(
    csv_path: Path | str | None = None,
    *,
    config_path: Path | str | None = None,
) -> dict[str, Any]:
    """
    执行完整分析流水线。

    @param csv_path - 观测 CSV；为 None 时使用内置示例数据
    @param config_path - 可选配置文件路径
    @returns 含汇总表、输出路径等信息的结果字典
    """
    config = load_config(config_path)
    dirs = ensure_output_dirs(config)
    typhoon = config.get("typhoon", {})
    dpi = int(config.get("output", {}).get("dpi", 150))

    raw = read_station_csv(csv_path) if csv_path else load_sample_data()
    cleaned = clean_observations(raw)
    windowed = filter_time_window(
        cleaned,
        start=typhoon.get("analysis_start"),
        end=typhoon.get("analysis_end"),
    )
    featured = add_derived_features(windowed)
    summary = station_summary(featured)

    processed_path = write_processed(
        featured,
        Path("data/processed/stations_featured.csv"),
    )
    summary_path = write_processed(summary, dirs["tables_dir"] / "station_summary.csv")

    figure_paths: list[Path] = []
    # 为配置中的每个有数据站点出一张时序图
    station_ids = featured["station_id"].astype(str).unique().tolist()
    for sid in station_ids:
        name = featured.loc[featured["station_id"].astype(str) == sid, "station_name"].iloc[0]
        safe = str(name).replace(" ", "_")
        fig_path = dirs["figures_dir"] / f"timeseries_{sid}_{safe}.png"
        plot_station_timeseries(featured, sid, output_path=fig_path, dpi=dpi)
        figure_paths.append(fig_path)

    precip_fig = dirs["figures_dir"] / "precip_comparison.png"
    plot_precip_comparison(summary, output_path=precip_fig, dpi=dpi)
    figure_paths.append(precip_fig)

    return {
        "config": config,
        "rows": len(featured),
        "summary": summary,
        "processed_path": processed_path,
        "summary_path": summary_path,
        "figure_paths": figure_paths,
    }


def extreme_events(df: pd.DataFrame, config: dict[str, Any] | None = None) -> pd.DataFrame:
    """
    根据阈值提取大风/强降水时段。

    @param df - 含观测列的 DataFrame
    @param config - 可选配置；默认加载仓库配置
    @returns 触发阈值的事件行
    """
    cfg = config or load_config()
    thr = cfg.get("thresholds", {})
    gust = float(thr.get("wind_gust_ms", 17.2))
    precip = float(thr.get("precip_1h_mm", 20.0))

    mask = (df["wind_gust_ms"] >= gust) | (df["precip_1h_mm"] >= precip)
    cols = [
        "time",
        "station_id",
        "station_name",
        "wind_speed_ms",
        "wind_gust_ms",
        "precip_1h_mm",
        "pressure_hpa",
    ]
    return df.loc[mask, cols].sort_values("time").reset_index(drop=True)
