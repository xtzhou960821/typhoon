"""可视化：时序曲线与站点对比图。"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib import font_manager

# 中文字体：优先 Noto / 文泉驿，避免 seaborn 主题覆盖后回退到 DejaVu
_CJK_CANDIDATES = (
    "Noto Sans CJK SC",
    "Noto Sans CJK JP",
    "WenQuanYi Micro Hei",
    "SimHei",
    "Arial Unicode MS",
)
_available = {f.name for f in font_manager.fontManager.ttflist}
_CJK_FONT = next((name for name in _CJK_CANDIDATES if name in _available), "DejaVu Sans")

sns.set_theme(style="whitegrid", context="talk")
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = [_CJK_FONT, "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def plot_station_timeseries(
    df: pd.DataFrame,
    station_id: str,
    *,
    output_path: Path | str | None = None,
    dpi: int = 150,
) -> Path | None:
    """
    绘制单站风速、气压、小时降水时序图。

    @param df - 观测 DataFrame
    @param station_id - 站点 ID
    @param output_path - 可选输出路径；不传则仅显示
    @param dpi - 图像分辨率
    @returns 保存路径或 None
    """
    subset = df.loc[df["station_id"].astype(str) == str(station_id)].copy()
    if subset.empty:
        raise ValueError(f"无站点数据: {station_id}")

    name = subset["station_name"].iloc[0]
    fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True)

    axes[0].plot(subset["time"], subset["wind_speed_ms"], label="平均风速", color="#1f4e79")
    axes[0].plot(subset["time"], subset["wind_gust_ms"], label="阵风", color="#c45c26", alpha=0.85)
    axes[0].set_ylabel("风速 (m/s)")
    axes[0].legend(loc="upper left", fontsize=10)
    axes[0].set_title(f"{name}（{station_id}）台风影响时段气象要素")

    axes[1].plot(subset["time"], subset["pressure_hpa"], color="#2a6f6f")
    axes[1].set_ylabel("气压 (hPa)")

    axes[2].bar(subset["time"], subset["precip_1h_mm"], width=0.03, color="#3d7ea6", align="center")
    axes[2].set_ylabel("小时降水 (mm)")
    axes[2].set_xlabel("时间 (UTC+8)")

    fig.autofmt_xdate()
    fig.tight_layout()

    if output_path is None:
        return None
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_precip_comparison(
    summary: pd.DataFrame,
    *,
    output_path: Path | str | None = None,
    dpi: int = 150,
) -> Path | None:
    """
    绘制各站累计降水对比柱状图。

    @param summary - ``station_summary`` 输出表
    @param output_path - 可选输出路径
    @param dpi - 图像分辨率
    @returns 保存路径或 None
    """
    fig, ax = plt.subplots(figsize=(10, 5))
    order = summary.sort_values("precip_total_mm", ascending=True)
    ax.barh(order["station_name"], order["precip_total_mm"], color="#3d7ea6")
    ax.set_xlabel("累计降水 (mm)")
    ax.set_title("台风巴威影响时段各站累计降水")
    fig.tight_layout()

    if output_path is None:
        return None
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return path
