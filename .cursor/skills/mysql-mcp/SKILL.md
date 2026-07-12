---
name: mysql-mcp
description: 通过 MySQL MCP server 查询与分析 tess_yangchen_ms 气象监测库。在用户提到 MySQL、数据库、表结构、SQL、yangchen_record、台风/气象站数据查询时使用。
---

# MySQL MCP

通过项目配置的 `mysql` MCP server（`@benborla29/mcp-server-mysql`）访问 MySQL。

## 前置条件

1. 仓库根目录存在 `.env`（可从 `.env.example` 复制并填入密码）
2. Cursor Settings → MCP 中 `mysql` 为已连接状态
3. `.cursor/mcp.json` 通过 `envFile` 加载 `.env`

## 本仓库数据库

| 项 | 值 |
|----|-----|
| Host | `db.wulianxx.com`（或 `47.104.235.238`） |
| Port | `3306` |
| Database | `tess_yangchen_ms` |
| 主表 | `yangchen_record`（气象监测记录） |

### `yangchen_record` 字段

| 字段 | 含义（推断） |
|------|----------------|
| `recordId` | 记录主键 |
| `DeviceId` | 设备/站点 ID |
| `pm10` / `pm25` / `TSP` | 颗粒物浓度 |
| `noise` | 噪声 |
| `temperature` / `humidity` | 温湿度 |
| `wind_power` / `wind_speed` / `wind_direction` / `wind_degree` | 风力相关 |
| `light_intensity` | 光照 |
| `cumulative_rainfall` / `instantaneous_rainfall` / `today_rainfall` / `yesterday_rainfall` | 降雨 |
| `barometric_pressure` | 气压 |
| `32_bit_data` | 原始/扩展数据 |
| `uploadtime` | 上报时间（查询时间范围优先用此字段） |

## 工作流程

1. **先摸清结构**：需要时再 `DESCRIBE yangchen_record`，确认类型与索引。
2. **再写查询**：优先 `SELECT`；按 `DeviceId`、`uploadtime` 过滤；始终加 `LIMIT`。
3. **默认只读**：未明确要求写入时，不要执行 INSERT/UPDATE/DELETE。
4. **写操作**：仅在用户明确授权且 `.env` 中 `ALLOW_*` 为 `true` 时执行。
5. **结果说明**：用中文简要解释；大结果集先 `COUNT` / 聚合 / 抽样。

## 查询提示

```sql
-- 时间范围（台风分析常用）
SELECT DeviceId, temperature, humidity, wind_speed, uploadtime
FROM yangchen_record
WHERE uploadtime BETWEEN '2026-07-11 00:00:00' AND '2026-07-12 23:59:59'
ORDER BY uploadtime
LIMIT 100;

-- 站点列表
SELECT DISTINCT DeviceId FROM yangchen_record LIMIT 100;
```

## 故障排查

- MCP 不可用：检查 `.env`、凭证、网络是否可达 `db.wulianxx.com:3306`
- 认证失败：核对 `MYSQL_USER` / `MYSQL_PASS` / `MYSQL_DB`
- 改完 `.env` 后：在 Cursor MCP 面板重启 `mysql` server
