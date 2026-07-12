#!/usr/bin/env python3
"""生成台风巴威影响时段的示例气象站观测数据。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "sample_stations.csv"

# 站点基础态：越靠近登陆区，风雨信号越强
STATIONS = [
    # id, name, base_pressure, wind_amp, precip_amp, landfall_offset_h
    ("54511", "北京", 1002.0, 4.0, 8.0, 36.0),
    ("58367", "上海", 1000.0, 12.0, 18.0, 18.0),
    ("58457", "杭州", 999.0, 14.0, 28.0, 14.0),
    ("58665", "温州", 997.0, 22.0, 45.0, 6.0),
    ("58847", "福州", 996.0, 24.0, 50.0, 4.0),
    ("59134", "厦门", 998.0, 16.0, 30.0, 10.0),
]


def _gaussian(x: np.ndarray, center: float, width: float) -> np.ndarray:
    """
    高斯包络，用于模拟台风过境峰值。

    @param x - 时间小时序列
    @param center - 峰值中心（小时）
    @param width - 宽度参数
    @returns 包络值数组
    """
    return np.exp(-0.5 * ((x - center) / width) ** 2)


def generate() -> pd.DataFrame:
    """
    生成 2026-07-10 ~ 2026-07-12 逐小时示例观测。

    @returns 多站时序 DataFrame
    """
    rng = np.random.default_rng(20260711)
    times = pd.date_range("2026-07-10", "2026-07-12 23:00:00", freq="h")
    hours = np.arange(len(times), dtype=float)
    # 假定核心影响约在 7/11 傍晚前后（相对 7/10 00 时约 42h）
    landfall_h = 42.0

    rows: list[dict] = []
    for sid, name, p0, wind_amp, precip_amp, offset in STATIONS:
        center = landfall_h + offset
        envelope = _gaussian(hours, center, 10.0)
        rain_env = _gaussian(hours, center - 2.0, 8.0)

        n = len(hours)
        pressure = p0 - 28.0 * envelope + rng.normal(0, 0.4, size=n)
        wind = 3.0 + wind_amp * envelope + rng.normal(0, 0.6, size=n)
        gust = wind * (1.35 + 0.25 * envelope) + rng.normal(0, 0.5, size=n)
        precip = np.clip(precip_amp * rain_env + rng.normal(0, 0.8, size=n), 0, None)
        temp = 28.0 - 4.0 * envelope + rng.normal(0, 0.3, size=n)
        humidity = np.clip(75 + 20 * rain_env + rng.normal(0, 2, size=n), 40, 100)
        # 风向随过境旋转（简化）
        wind_dir = (90 + 180 * envelope + rng.normal(0, 8, size=n)) % 360

        for i, t in enumerate(times):
            rows.append(
                {
                    "time": t.strftime("%Y-%m-%d %H:%M:%S"),
                    "station_id": sid,
                    "station_name": name,
                    "temp_c": round(float(temp[i]), 1),
                    "pressure_hpa": round(float(pressure[i]), 1),
                    "humidity_pct": round(float(humidity[i]), 1),
                    "wind_speed_ms": round(float(max(wind[i], 0)), 1),
                    "wind_gust_ms": round(float(max(gust[i], 0)), 1),
                    "wind_dir_deg": round(float(wind_dir[i]), 0),
                    "precip_1h_mm": round(float(precip[i]), 1),
                }
            )

    return pd.DataFrame(rows)


def main() -> None:
    """写入示例 CSV。"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df = generate()
    df.to_csv(OUT, index=False)
    print(f"已生成示例数据: {OUT} ({len(df)} 行)")


if __name__ == "__main__":
    main()
