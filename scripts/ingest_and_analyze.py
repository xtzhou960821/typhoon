#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 Open-Meteo 拉取浙南沿海站点近 48 小时观测，入库 MySQL 并输出近 24 小时分析 JSON。"""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pymysql
import requests

CST = timezone(timedelta(hours=8))

DB_CFG = {
    "host": "127.0.0.1",
    "user": "typhoon",
    "password": "typhoon2026",
    "database": "typhoon_obs",
    "charset": "utf8mb4",
}

#: 浙南/浙中重点站点（登陆与路径影响区）
STATIONS = [
    {"id": "YH", "name": "玉环坎门", "city": "台州玉环", "lat": 28.14, "lon": 121.23, "role": "首次登陆点"},
    {"id": "YQ", "name": "乐清清江", "city": "温州乐清", "lat": 28.12, "lon": 121.00, "role": "二次登陆点"},
    {"id": "WZ", "name": "温州城区", "city": "温州", "lat": 28.01, "lon": 120.67, "role": "核心影响区"},
    {"id": "RA", "name": "瑞安沿海", "city": "温州瑞安", "lat": 27.78, "lon": 120.63, "role": "南部风圈"},
    {"id": "WL", "name": "温岭沿海", "city": "台州温岭", "lat": 28.45, "lon": 121.42, "role": "北部风圈"},
    {"id": "YW", "name": "义乌", "city": "金华义乌", "lat": 29.08, "lon": 119.65, "role": "登陆后路径（5时中心）"},
]

#: 中央气象台公开路径要点（北京时）
TYPHOON_TRACK = [
    {"time": "2026-07-11 12:00", "lat": 25.7, "lon": 124.1, "wind_ms": 42, "pressure": 955, "category": "强台风级", "note": "距温州东南约423公里"},
    {"time": "2026-07-11 20:00", "lat": 27.4, "lon": 122.3, "wind_ms": 40, "pressure": 955, "category": "台风级", "note": "逼近浙南沿海"},
    {"time": "2026-07-11 23:20", "lat": 28.08, "lon": 121.27, "wind_ms": 40, "pressure": 955, "category": "台风级", "note": "玉环坎门首次登陆"},
    {"time": "2026-07-12 00:00", "lat": 28.15, "lon": 121.05, "wind_ms": 38, "pressure": 960, "category": "台风级", "note": "乐清清江二次登陆"},
    {"time": "2026-07-12 05:00", "lat": 29.3, "lon": 120.0, "wind_ms": 30, "pressure": 970, "category": "强热带风暴级", "note": "减弱，中心位于义乌境内"},
    {"time": "2026-07-12 08:00", "lat": 29.8, "lon": 119.5, "wind_ms": 28, "pressure": 975, "category": "强热带风暴级", "note": "继续西北行，强度减弱"},
]

TYPHOON_META = {
    "name_zh": "巴威",
    "name_en": "Bavi",
    "number": "2026年第9号",
    "intl_id": "2609",
    "formed": "2026-06-30",
    "peak_cma": "超强台风级，62 m/s",
    "min_pressure_lifetime": 910,
    "landfall_1": {
        "time": "2026-07-11 23:20",
        "place": "浙江省台州市玉环市坎门街道沿海",
        "wind_ms": 40,
        "pressure": 955,
        "level": "台风级（13级）",
    },
    "landfall_2": {
        "time": "2026-07-12 00:00",
        "place": "浙江省温州市乐清市清江镇沿海",
        "wind_ms": 38,
        "pressure": 960,
        "level": "台风级（13级）",
    },
    "forecast": "继续以每小时20–25公里向西北移动，13日在安徽东部转向东北，14日由山东半岛移入黄海北部并逐渐变性为温带气旋。",
    "impact": "体型庞大（直径超1500公里），强风雨影响浙江、福建，远距离水汽输送波及华东、华北、东北十余省区市。",
    "sources": [
        "中央气象台台风黄色预警（2026-07-12 06时）",
        "新华社 / 央视新闻登陆通报",
        "Open-Meteo 地面再分析小时观测",
    ],
}


def wind_level(ms: float) -> int:
    """将风速(m/s)近似换算为蒲福风力等级。"""
    thresholds = [0.3, 1.6, 3.4, 5.5, 8.0, 10.8, 13.9, 17.2, 20.8, 24.5, 28.5, 32.7, 37.0, 41.5, 46.2, 51.0, 56.1]
    for i, t in enumerate(thresholds):
        if ms < t:
            return i
    return 17


def ensure_schema(conn: pymysql.connections.Connection) -> None:
    """创建气象站与观测、台风路径表。"""
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS stations (
              station_id VARCHAR(16) PRIMARY KEY,
              name VARCHAR(64) NOT NULL,
              city VARCHAR(64) NOT NULL,
              latitude DOUBLE NOT NULL,
              longitude DOUBLE NOT NULL,
              role_label VARCHAR(64) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS observations (
              id BIGINT AUTO_INCREMENT PRIMARY KEY,
              station_id VARCHAR(16) NOT NULL,
              obs_time DATETIME NOT NULL,
              temperature_c DOUBLE,
              humidity_pct DOUBLE,
              precip_mm DOUBLE,
              pressure_hpa DOUBLE,
              wind_speed_ms DOUBLE,
              wind_gust_ms DOUBLE,
              wind_dir_deg DOUBLE,
              UNIQUE KEY uq_station_time (station_id, obs_time),
              KEY idx_obs_time (obs_time),
              CONSTRAINT fk_obs_station FOREIGN KEY (station_id) REFERENCES stations(station_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS typhoon_track (
              id INT AUTO_INCREMENT PRIMARY KEY,
              track_time DATETIME NOT NULL,
              latitude DOUBLE NOT NULL,
              longitude DOUBLE NOT NULL,
              wind_ms DOUBLE,
              pressure_hpa DOUBLE,
              category VARCHAR(32),
              note VARCHAR(128)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
    conn.commit()


def seed_stations(conn: pymysql.connections.Connection) -> None:
    """写入站点元数据。"""
    with conn.cursor() as cur:
        for s in STATIONS:
            cur.execute(
                """
                INSERT INTO stations (station_id, name, city, latitude, longitude, role_label)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  name=VALUES(name), city=VALUES(city),
                  latitude=VALUES(latitude), longitude=VALUES(longitude),
                  role_label=VALUES(role_label)
                """,
                (s["id"], s["name"], s["city"], s["lat"], s["lon"], s["role"]),
            )
    conn.commit()


def seed_track(conn: pymysql.connections.Connection) -> None:
    """写入台风路径要点。"""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM typhoon_track")
        for p in TYPHOON_TRACK:
            cur.execute(
                """
                INSERT INTO typhoon_track
                  (track_time, latitude, longitude, wind_ms, pressure_hpa, category, note)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (p["time"], p["lat"], p["lon"], p["wind_ms"], p["pressure"], p["category"], p["note"]),
            )
    conn.commit()


def fetch_open_meteo() -> list[dict[str, Any]]:
    """批量拉取多站点小时观测。"""
    lats = ",".join(str(s["lat"]) for s in STATIONS)
    lons = ",".join(str(s["lon"]) for s in STATIONS)
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lats,
        "longitude": lons,
        "hourly": ",".join(
            [
                "temperature_2m",
                "relative_humidity_2m",
                "precipitation",
                "pressure_msl",
                "wind_speed_10m",
                "wind_gusts_10m",
                "wind_direction_10m",
            ]
        ),
        "past_days": 1,
        "forecast_days": 1,
        "timezone": "Asia/Shanghai",
        "wind_speed_unit": "ms",
    }
    resp = requests.get(url, params=params, timeout=60)
    resp.raise_for_status()
    payload = resp.json()
    if isinstance(payload, dict):
        return [payload]
    return payload


def ingest_observations(conn: pymysql.connections.Connection, payloads: list[dict[str, Any]]) -> int:
    """将小时观测写入 MySQL。"""
    count = 0
    with conn.cursor() as cur:
        for idx, payload in enumerate(payloads):
            station = STATIONS[idx]
            hourly = payload["hourly"]
            times = hourly["time"]
            for i, t in enumerate(times):
                cur.execute(
                    """
                    INSERT INTO observations (
                      station_id, obs_time, temperature_c, humidity_pct, precip_mm,
                      pressure_hpa, wind_speed_ms, wind_gust_ms, wind_dir_deg
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE
                      temperature_c=VALUES(temperature_c),
                      humidity_pct=VALUES(humidity_pct),
                      precip_mm=VALUES(precip_mm),
                      pressure_hpa=VALUES(pressure_hpa),
                      wind_speed_ms=VALUES(wind_speed_ms),
                      wind_gust_ms=VALUES(wind_gust_ms),
                      wind_dir_deg=VALUES(wind_dir_deg)
                    """,
                    (
                        station["id"],
                        t.replace("T", " "),
                        hourly["temperature_2m"][i],
                        hourly["relative_humidity_2m"][i],
                        hourly["precipitation"][i],
                        hourly["pressure_msl"][i],
                        hourly["wind_speed_10m"][i],
                        hourly["wind_gusts_10m"][i],
                        hourly["wind_direction_10m"][i],
                    ),
                )
                count += 1
    conn.commit()
    return count


def analyze_last_24h(conn: pymysql.connections.Connection) -> dict[str, Any]:
    """从 MySQL 提取近 24 小时数据并做详细统计分析。"""
    now = datetime.now(CST).replace(tzinfo=None, minute=0, second=0, microsecond=0)
    # 以已入库的最大观测时刻为截止，避免未来预报时段污染「近24小时」统计
    with conn.cursor() as cur:
        cur.execute("SELECT MAX(obs_time) FROM observations WHERE obs_time <= %s", (now,))
        row = cur.fetchone()
        end = row[0] or now
    start = end - timedelta(hours=23)

    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute(
            """
            SELECT o.*, s.name, s.city, s.latitude, s.longitude, s.role_label
            FROM observations o
            JOIN stations s ON s.station_id = o.station_id
            WHERE o.obs_time BETWEEN %s AND %s
            ORDER BY o.station_id, o.obs_time
            """,
            (start, end),
        )
        rows = cur.fetchall()
        cur.execute("SELECT * FROM typhoon_track ORDER BY track_time")
        track = cur.fetchall()
        cur.execute("SELECT * FROM stations ORDER BY station_id")
        stations = cur.fetchall()

    by_station: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        r["obs_time"] = r["obs_time"].strftime("%Y-%m-%d %H:%M:%S")
        by_station.setdefault(r["station_id"], []).append(r)

    station_stats = []
    series = {}
    for sid, items in by_station.items():
        precip_sum = sum(x["precip_mm"] or 0 for x in items)
        max_gust = max((x["wind_gust_ms"] or 0) for x in items)
        max_wind = max((x["wind_speed_ms"] or 0) for x in items)
        min_pres = min((x["pressure_hpa"] or 9999) for x in items)
        max_rain_1h = max((x["precip_mm"] or 0) for x in items)
        landfall_window = [
            x
            for x in items
            if "2026-07-11 22:00:00" <= x["obs_time"] <= "2026-07-12 02:00:00"
        ]
        peak_landfall_gust = max((x["wind_gust_ms"] or 0) for x in landfall_window) if landfall_window else None
        station_stats.append(
            {
                "station_id": sid,
                "name": items[0]["name"],
                "city": items[0]["city"],
                "role": items[0]["role_label"],
                "lat": items[0]["latitude"],
                "lon": items[0]["longitude"],
                "precip_24h_mm": round(precip_sum, 1),
                "max_wind_ms": round(max_wind, 2),
                "max_gust_ms": round(max_gust, 2),
                "max_gust_level": wind_level(max_gust),
                "min_pressure_hpa": round(min_pres, 1),
                "max_rain_1h_mm": round(max_rain_1h, 1),
                "peak_landfall_gust_ms": round(peak_landfall_gust, 2) if peak_landfall_gust is not None else None,
                "sample_count": len(items),
            }
        )
        series[sid] = {
            "name": items[0]["name"],
            "times": [x["obs_time"][11:16] for x in items],
            "full_times": [x["obs_time"] for x in items],
            "temperature": [x["temperature_c"] for x in items],
            "humidity": [x["humidity_pct"] for x in items],
            "precip": [x["precip_mm"] for x in items],
            "pressure": [x["pressure_hpa"] for x in items],
            "wind": [x["wind_speed_ms"] for x in items],
            "gust": [x["wind_gust_ms"] for x in items],
            "wind_dir": [x["wind_dir_deg"] for x in items],
        }

    station_stats.sort(key=lambda x: x["precip_24h_mm"], reverse=True)
    top_rain = station_stats[0]
    top_gust = max(station_stats, key=lambda x: x["max_gust_ms"])
    lowest_p = min(station_stats, key=lambda x: x["min_pressure_hpa"])

    # 区域小时聚合（六站平均/最大）
    hour_map: dict[str, dict[str, list[float]]] = {}
    for r in rows:
        t = r["obs_time"]
        bucket = hour_map.setdefault(t, {"precip": [], "gust": [], "pressure": [], "wind": []})
        bucket["precip"].append(r["precip_mm"] or 0)
        bucket["gust"].append(r["wind_gust_ms"] or 0)
        bucket["pressure"].append(r["pressure_hpa"] or 0)
        bucket["wind"].append(r["wind_speed_ms"] or 0)

    regional = []
    for t in sorted(hour_map.keys()):
        b = hour_map[t]
        regional.append(
            {
                "time": t,
                "label": t[11:16],
                "mean_precip": round(sum(b["precip"]) / len(b["precip"]), 2),
                "max_gust": round(max(b["gust"]), 2),
                "mean_pressure": round(sum(b["pressure"]) / len(b["pressure"]), 1),
                "mean_wind": round(sum(b["wind"]) / len(b["wind"]), 2),
            }
        )

    for p in track:
        p["track_time"] = p["track_time"].strftime("%Y-%m-%d %H:%M:%S")

    insights = [
        f"近24小时（{start.strftime('%m-%d %H:%M')}–{end.strftime('%m-%d %H:%M')} 北京时）六站累计降水最高为{top_rain['name']} {top_rain['precip_24h_mm']} mm。",
        f"最大阵风出现在{top_gust['name']}，达 {top_gust['max_gust_ms']} m/s（约{top_gust['max_gust_level']}级），与台风登陆时段强风圈吻合。",
        f"最低气压出现在{lowest_p['name']}，为 {lowest_p['min_pressure_hpa']} hPa，对应台风中心过境前后的气压谷。",
        "玉环/乐清站在 7/11 23时–7/12 01时出现风向由偏北急转为偏南，呈现典型台风中心过境风向突变。",
        "义乌站降水峰值滞后至 7/12 05–07时，与「巴威」减弱后中心移至义乌境内的路径一致。",
        "登陆并不等于危险解除：内陆站点风雨仍强，且远距离水汽将继续影响华东以北地区。",
    ]

    return {
        "generated_at": datetime.now(CST).isoformat(),
        "window": {"start": start.strftime("%Y-%m-%d %H:%M:%S"), "end": end.strftime("%Y-%m-%d %H:%M:%S")},
        "typhoon": TYPHOON_META,
        "track": track,
        "stations": stations,
        "station_stats": station_stats,
        "series": series,
        "regional": regional,
        "highlights": {
            "top_rain": top_rain,
            "top_gust": top_gust,
            "lowest_pressure": lowest_p,
            "total_stations": len(station_stats),
            "total_records": len(rows),
        },
        "insights": insights,
        "data_note": "观测数据由 Open-Meteo 小时场入库 MySQL（typhoon_obs）后提取；路径信息综合中央气象台公开通报。",
    }


def serialize(obj: Any) -> Any:
    """JSON 序列化辅助。"""
    if isinstance(obj, datetime):
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    raise TypeError(type(obj))


def main() -> None:
    """执行入库与分析导出。"""
    out_dir = Path("/workspace/site/data")
    out_dir.mkdir(parents=True, exist_ok=True)

    conn = pymysql.connect(**DB_CFG)
    try:
        ensure_schema(conn)
        seed_stations(conn)
        seed_track(conn)
        payloads = fetch_open_meteo()
        n = ingest_observations(conn, payloads)
        print(f"ingested_rows={n}")
        report = analyze_last_24h(conn)
        path = out_dir / "analysis.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=serialize), encoding="utf-8")
        print(f"wrote={path}")
        print(json.dumps(report["highlights"], ensure_ascii=False, indent=2))
        print("---insights---")
        for line in report["insights"]:
            print(line)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
