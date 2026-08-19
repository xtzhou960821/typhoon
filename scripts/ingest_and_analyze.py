#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从阿里云 MySQL ``yangchen_record`` 只读提取近 24 小时观测并写出 ``analysis.json``。

连接参数(密码不硬编码):

- ``MYSQL_PASSWORD``(优先)或 ``MYSQL_PASS``(兼容 Cursor Secret)
- ``MYSQL_HOST``(默认 ``db.wulianxx.com``)
- ``MYSQL_PORT``(默认 ``3306``)
- ``MYSQL_USER``(默认 ``root``)
- ``MYSQL_DATABASE``(默认 ``tess_yangchen_ms``)

仅执行 SELECT,不写库。
"""

from __future__ import annotations

import json
import math
import os
import statistics
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pymysql

CST = timezone(timedelta(hours=8))

#: 站点展示名(devices 表为空,不依赖库内名称)
STATION_META = {
    "name": "尤溪施工气象站",
    "location": "尤溪镇下白岩至黄家寮道路建设工程",
    "interval_note": "约5分钟一条",
}

#: 八风向最佳努力映射(设备码 0–7;非度数)
WIND_DIR_LABELS = {
    "0": "北",
    "1": "东北",
    "2": "东",
    "3": "东南",
    "4": "南",
    "5": "西南",
    "6": "西",
    "7": "西北",
}

ROOT = Path(__file__).resolve().parents[1]
SITE_DATA = ROOT / "site" / "data"
DOCS_DATA = ROOT / "docs" / "data"


def env_or(name: str, default: str) -> str:
    """读取非空环境变量,否则返回默认值。

    :param name: 环境变量名。
    :param default: 默认值。
    :returns: 有效字符串。
    """
    value = os.environ.get(name)
    if value is None or not str(value).strip():
        return default
    return str(value).strip()


def db_config() -> dict[str, Any]:
    """从环境变量组装只读连接配置。

    :returns: pymysql.connect 关键字参数。
    :raises SystemExit: 缺少密码环境变量时退出。
    """
    password = os.environ.get("MYSQL_PASSWORD") or os.environ.get("MYSQL_PASS")
    if not password or not str(password).strip():
        raise SystemExit(
            "缺少数据库密码环境变量 MYSQL_PASSWORD(或兼容名 MYSQL_PASS)。"
            "请在本地 export,或在 GitHub Actions / Cursor Secrets 中配置。"
            "已提交的 site/data/analysis.json 可继续用于无密码预览。"
        )
    return {
        "host": env_or("MYSQL_HOST", "db.wulianxx.com"),
        "port": int(env_or("MYSQL_PORT", "3306")),
        "user": env_or("MYSQL_USER", "root"),
        "password": str(password).strip(),
        "database": env_or("MYSQL_DATABASE", "tess_yangchen_ms"),
        "charset": "utf8mb4",
        "connect_timeout": 20,
        "read_timeout": 60,
        "cursorclass": pymysql.cursors.DictCursor,
    }


def to_float(value: Any, ndigits: int = 2) -> float | None:
    """将 varchar / 数值字段安全转为 float。

    :param value: 原始字段值。
    :param ndigits: 保留小数位(抑制 float 二进制噪声)。
    :returns: 浮点数或 None。
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        return round(float(value), ndigits)
    text = str(value).strip()
    if not text:
        return None
    try:
        return round(float(text), ndigits)
    except ValueError:
        return None


def wind_label(code: Any) -> str | None:
    """将风向码映射为八风向中文标签。

    :param code: 原始风向码(字符串或数字)。
    :returns: 标签或 None。
    """
    if code is None:
        return None
    key = str(code).strip()
    if key.endswith(".0"):
        key = key[:-2]
    return WIND_DIR_LABELS.get(key)


def fetch_last_24h(conn: pymysql.connections.Connection) -> list[dict[str, Any]]:
    """SELECT 近 24 小时全部设备观测(只读)。

    :param conn: 已打开的连接。
    :returns: 按时间升序的行列表。
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
              recordId,
              DeviceId,
              pm10,
              pm25,
              TSP,
              noise,
              temperature,
              humidity,
              wind_power,
              wind_speed,
              wind_direction,
              wind_degree,
              light_intensity,
              cumulative_rainfall,
              instantaneous_rainfall,
              today_rainfall,
              yesterday_rainfall,
              barometric_pressure,
              uploadtime
            FROM yangchen_record
            WHERE uploadtime >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            ORDER BY DeviceId ASC, uploadtime ASC
            """
        )
        return list(cur.fetchall())


def numeric_stats(values: list[float | None]) -> dict[str, float | None]:
    """计算非空数值的 min / max / avg / latest。

    :param values: 时间序列数值(可含 None)。
    :returns: 统计字典。
    """
    clean = [v for v in values if v is not None]
    latest = next((v for v in reversed(values) if v is not None), None)
    if not clean:
        return {"min": None, "max": None, "avg": None, "latest": latest}
    return {
        "min": round(min(clean), 2),
        "max": round(max(clean), 2),
        "avg": round(statistics.fmean(clean), 2),
        "latest": round(latest, 2) if latest is not None else None,
    }


def analyze_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """由观测行生成站点统计与时间序列。

    :param rows: ``yangchen_record`` 查询结果。
    :returns: 前端可读的 analysis 对象。
    """
    if not rows:
        raise SystemExit("近24小时无观测数据,请确认设备是否在线。")

    # 当前仅一台设备;若未来多设备,按 DeviceId 分组后取样本最多者为主站
    by_device: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        by_device.setdefault(int(row["DeviceId"]), []).append(row)
    device_id = max(by_device.keys(), key=lambda d: len(by_device[d]))
    items = by_device[device_id]

    times_full: list[str] = []
    times_short: list[str] = []
    series: dict[str, list[Any]] = {
        "temperature": [],
        "humidity": [],
        "wind_speed": [],
        "wind_power": [],
        "wind_direction": [],
        "wind_direction_label": [],
        "pressure_kpa": [],
        "instantaneous_rainfall": [],
        "today_rainfall": [],
        "yesterday_rainfall": [],
        "pm25": [],
        "pm10": [],
        "noise": [],
        "light_intensity": [],
    }

    for row in items:
        ts = row["uploadtime"]
        if isinstance(ts, datetime):
            full = ts.strftime("%Y-%m-%d %H:%M:%S")
        else:
            full = str(ts)
        times_full.append(full)
        times_short.append(full[11:16])

        wind_code = None if row["wind_direction"] is None else str(row["wind_direction"]).strip()
        series["temperature"].append(to_float(row["temperature"]))
        series["humidity"].append(to_float(row["humidity"]))
        series["wind_speed"].append(to_float(row["wind_speed"]))
        series["wind_power"].append(to_float(row["wind_power"]))
        series["wind_direction"].append(wind_code)
        series["wind_direction_label"].append(wind_label(wind_code))
        series["pressure_kpa"].append(to_float(row["barometric_pressure"]))
        series["instantaneous_rainfall"].append(to_float(row["instantaneous_rainfall"]))
        series["today_rainfall"].append(to_float(row["today_rainfall"]))
        series["yesterday_rainfall"].append(to_float(row["yesterday_rainfall"]))
        series["pm25"].append(to_float(row["pm25"]))
        series["pm10"].append(to_float(row["pm10"]))
        series["noise"].append(to_float(row["noise"]))
        series["light_intensity"].append(to_float(row["light_intensity"]))

    dir_counter = Counter(c for c in series["wind_direction"] if c is not None)
    dominant_code, dominant_count = (dir_counter.most_common(1)[0] if dir_counter else (None, 0))

    last = items[-1]
    last_wind = None if last["wind_direction"] is None else str(last["wind_direction"]).strip()
    latest = {
        "uploadtime": times_full[-1],
        "temperature": to_float(last["temperature"]),
        "humidity": to_float(last["humidity"]),
        "wind_speed": to_float(last["wind_speed"]),
        "wind_power": None if last["wind_power"] is None else str(last["wind_power"]).strip(),
        "wind_direction": last_wind,
        "wind_direction_label": wind_label(last_wind),
        "wind_degree": to_float(last["wind_degree"]),
        "pressure_kpa": to_float(last["barometric_pressure"]),
        "instantaneous_rainfall": to_float(last["instantaneous_rainfall"]),
        "today_rainfall": to_float(last["today_rainfall"]),
        "yesterday_rainfall": to_float(last["yesterday_rainfall"]),
        "pm25": to_float(last["pm25"]),
        "pm10": to_float(last["pm10"]),
        "noise": to_float(last["noise"]),
        "light_intensity": to_float(last["light_intensity"]),
    }

    rain_inst = [v for v in series["instantaneous_rainfall"] if v is not None]
    station_stats = {
        "device_id": device_id,
        "sample_count": len(items),
        "temperature": numeric_stats(series["temperature"]),
        "humidity": numeric_stats(series["humidity"]),
        "wind_speed": numeric_stats(series["wind_speed"]),
        "wind_power": numeric_stats(series["wind_power"]),
        "pressure_kpa": numeric_stats(series["pressure_kpa"]),
        "pm25": numeric_stats(series["pm25"]),
        "pm10": numeric_stats(series["pm10"]),
        "noise": numeric_stats(series["noise"]),
        "light_intensity": numeric_stats(series["light_intensity"]),
        "instantaneous_rainfall": {
            "max": round(max(rain_inst), 2) if rain_inst else None,
            "sum": round(sum(rain_inst), 2) if rain_inst else None,
            "latest": latest["instantaneous_rainfall"],
        },
        "today_rainfall_latest": latest["today_rainfall"],
        "yesterday_rainfall_latest": latest["yesterday_rainfall"],
        "dominant_wind_direction": {
            "code": dominant_code,
            "label": wind_label(dominant_code),
            "count": dominant_count,
        },
    }

    start = times_full[0]
    end = times_full[-1]
    insights = [
        f"近24小时共 {len(items)} 条记录(设备 {device_id}),窗口 {start[5:16]}–{end[5:16]} 北京时。",
        f"最新气温 {latest['temperature']} °C,相对湿度 {latest['humidity']} %,气压 {latest['pressure_kpa']} kPa。",
        f"近24小时气温 {station_stats['temperature']['min']}–{station_stats['temperature']['max']} °C,"
        f"风速峰值 {station_stats['wind_speed']['max']} m/s。",
        f"主导风向码 {dominant_code}"
        + (f"（{wind_label(dominant_code)}）" if wind_label(dominant_code) else "")
        + f",出现 {dominant_count} 次;风向角度字段多为空,页面展示码值+八风向标签。",
        f"今日累计降水 {latest['today_rainfall']} mm,昨日 {latest['yesterday_rainfall']} mm;"
        f"近24小时瞬时降水峰值 {station_stats['instantaneous_rainfall']['max']} mm。",
        f"颗粒物最新 PM2.5 {latest['pm25']} / PM10 {latest['pm10']},噪声 {latest['noise']} dB。",
    ]

    return {
        "generated_at": datetime.now(CST).isoformat(),
        "window": {"start": start, "end": end},
        "station": {
            "device_id": device_id,
            **STATION_META,
        },
        "devices": [
            {"device_id": did, "sample_count": len(by_device[did])} for did in sorted(by_device)
        ],
        "latest": latest,
        "station_stats": station_stats,
        "series": {
            "times": times_short,
            "full_times": times_full,
            **series,
        },
        "insights": insights,
        "data_note": (
            "数据来自业主扬尘/气象监测站 MySQL(tess_yangchen_ms.yangchen_record)只读提取;"
            "气压单位为 kPa;风向为设备八方位码(0–7)的最佳努力中文标签,非实测方位角。"
        ),
    }


def serialize(obj: Any) -> Any:
    """JSON 序列化辅助。

    :param obj: 待序列化对象。
    :returns: 可 JSON 编码的值。
    """
    if isinstance(obj, datetime):
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    raise TypeError(type(obj))


def write_analysis(report: dict[str, Any]) -> list[Path]:
    """写入 ``site/data`` 与 ``docs/data`` 两份 analysis.json。

    :param report: 分析结果。
    :returns: 写出的路径列表。
    """
    text = json.dumps(report, ensure_ascii=False, indent=2, default=serialize)
    paths: list[Path] = []
    for directory in (SITE_DATA, DOCS_DATA):
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "analysis.json"
        path.write_text(text, encoding="utf-8")
        paths.append(path)
    return paths


def build_standalone(report: dict[str, Any]) -> list[Path]:
    """将 index + css + js + 内嵌 JSON 拼成 standalone.html。

    :param report: 分析结果(内嵌到页面)。
    :returns: 写出的 standalone 路径。
    """
    index_html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "site" / "css" / "styles.css").read_text(encoding="utf-8")
    js = (ROOT / "site" / "js" / "app.js").read_text(encoding="utf-8")
    payload = json.dumps(report, ensure_ascii=False, default=serialize)

    # 去掉外链 stylesheet / app.js,改为内联
    html = index_html.replace(
        '<link rel="stylesheet" href="./css/styles.css" />',
        f"<style>\n{css}\n</style>",
    )
    html = html.replace(
        '<script src="./js/app.js"></script>',
        f"<script>\nwindow.__ANALYSIS__ = {payload};\n{js}\n</script>",
    )

    paths: list[Path] = []
    for directory in (ROOT / "site", ROOT / "docs"):
        path = directory / "standalone.html"
        path.write_text(html, encoding="utf-8")
        paths.append(path)
    return paths


def main() -> None:
    """只读查询并导出分析 JSON / standalone。"""
    cfg = db_config()
    conn = pymysql.connect(**cfg)
    try:
        rows = fetch_last_24h(conn)
        print(f"selected_rows={len(rows)}")
        report = analyze_rows(rows)
        for path in write_analysis(report):
            print(f"wrote={path}")
        for path in build_standalone(report):
            print(f"wrote={path}")
        print(json.dumps(report["latest"], ensure_ascii=False, indent=2))
        print("---insights---")
        for line in report["insights"]:
            print(line)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
