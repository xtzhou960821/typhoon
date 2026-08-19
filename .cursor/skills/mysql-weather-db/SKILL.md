---
name: mysql-weather-db
description: 查询施工气象站 MySQL 数据库(数据库 tess_yangchen_ms,主表 yangchen_record)。当需要读取真实气象站观测数据(pm2.5/pm10、温湿度、风速风向、降水、气压等)进行分析、统计或与 ingest_and_analyze.py 结合时使用。
---

# 气象监测 MySQL 数据库(yangchen_record)

真实气象站监测数据存放在阿里云 MySQL(MySQL 9.2)中,可通过 **MySQL MCP server**(工具 `mysql_query`,只读)查询,也可用 `scripts/query.py` 在终端直接查询。站点看板流水线 `scripts/ingest_and_analyze.py` 亦只读本表近24小时数据。

## 连接信息

| 项 | 值 |
| --- | --- |
| host | `db.wulianxx.com`(或 IP `47.104.235.238`) |
| port | `3306` |
| 用户 | `root` |
| 数据库 | `tess_yangchen_ms` |
| 主表 | `yangchen_record` |

密码 **不写入仓库**:

- 全局 MCP 配置 `~/.cursor/mcp.json` 通过 `"${env:MYSQL_PASS}"` 从 **Cursor Secret `MYSQL_PASS`** 读取;skill 终端脚本读 `MYSQL_PASS`。
- 仓库流水线优先读 `MYSQL_PASSWORD`(GitHub Actions Secret),并兼容 `MYSQL_PASS`。

请在 Cursor「Secrets」面板添加 `MYSQL_PASS`,在 GitHub 仓库 Secrets 添加 `MYSQL_PASSWORD`。

## 使用 MySQL MCP(推荐)

MCP server `mysql` 暴露只读工具 `mysql_query`,直接传入 SQL 即可,例如:

```sql
SELECT COUNT(*) FROM yangchen_record;
```

默认禁用写操作(INSERT/UPDATE/DELETE);如需开启,在 `~/.cursor/mcp.json` 中把对应 `ALLOW_*_OPERATION` 设为 `true`。

## `yangchen_record` 表结构

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `recordId` | int | 主键 |
| `DeviceId` | int | 设备(站点)ID |
| `pm10` / `pm25` | varchar | 颗粒物浓度 |
| `noise` | varchar | 噪声 |
| `temperature` / `humidity` | varchar | 气温 / 湿度 |
| `wind_power` | varchar | 风力等级 |
| `wind_speed` | double | 风速 |
| `wind_direction` / `wind_degree` | varchar | 风向 / 风向角度 |
| `TSP` | varchar | 总悬浮颗粒物 |
| `light_intensity` | varchar | 光照强度 |
| `cumulative_rainfall` / `today_rainfall` / `yesterday_rainfall` / `instantaneous_rainfall` | varchar | 各类降水量 |
| `barometric_pressure` | varchar | 气压(**kPa**,正常约 100,勿当 hPa) |
| `32_bit_data` | varchar | 原始 32 位数据 |
| `uploadtime` | datetime | 上传时间(北京时) |

> 注意:除 `wind_speed`(double)、`uploadtime`(datetime)外,数值字段多为 `varchar`,做数值统计时需要 `CAST(... AS DECIMAL)`;列名 `32_bit_data` 以数字开头,引用时需加反引号。`wind_direction` 为八方位码字符串(常见 `0`–`7`),`wind_degree` 常为空。`devices` 表可能无行,站点名称勿依赖该表。

## 常用查询示例

```sql
-- 各设备最近一次上报时间
SELECT DeviceId, MAX(uploadtime) AS last_upload
FROM yangchen_record GROUP BY DeviceId;

-- 指定时间段内某设备的风速与气压序列
SELECT uploadtime, wind_speed, barometric_pressure
FROM yangchen_record
WHERE DeviceId = 1
  AND uploadtime BETWEEN '2026-07-11 00:00:00' AND '2026-07-11 23:59:59'
ORDER BY uploadtime;

-- 最大瞬时降水 Top 10(varchar 需转数值)
SELECT recordId, DeviceId, uploadtime,
       CAST(instantaneous_rainfall AS DECIMAL(10,2)) AS rain
FROM yangchen_record
ORDER BY rain DESC LIMIT 10;
```

## 在终端查询(不经 MCP)

```bash
export MYSQL_PASS='<数据库密码>'   # 或从 Secret 注入
/workspace/.venv/bin/python .cursor/skills/mysql-weather-db/scripts/query.py \
  "SELECT COUNT(*) FROM yangchen_record"
```

## 与分析脚本结合

仓库看板流水线:

```bash
export MYSQL_PASSWORD='<密码>'   # 或 MYSQL_PASS
/workspace/.venv/bin/python /workspace/scripts/ingest_and_analyze.py
```

脚本对 `yangchen_record` **只读 SELECT** 近24小时,写出 `site/data/analysis.json`(并同步 `docs/`)。
