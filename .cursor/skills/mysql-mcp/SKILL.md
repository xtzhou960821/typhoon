---
name: mysql-mcp
description: 通过 MySQL MCP server 查询与分析数据库。在用户提到 MySQL、数据库、表结构、SQL、台风/气象站数据查询，或需要检查库表时使用。
---

# MySQL MCP

通过项目配置的 `mysql` MCP server（`@benborla29/mcp-server-mysql`）访问 MySQL。

## 前置条件

1. 仓库根目录存在 `.env`（可从 `.env.example` 复制）
2. Cursor Settings → MCP 中 `mysql` 为已连接状态
3. `.cursor/mcp.json` 已配置该 server，并通过 `envFile` 加载 `.env`

## 连接变量（写入 `.env`）

| 变量 | 含义 |
|------|------|
| `MYSQL_HOST` | 主机，默认 `127.0.0.1` |
| `MYSQL_PORT` | 端口，默认 `3306` |
| `MYSQL_USER` | 用户名 |
| `MYSQL_PASS` | 密码 |
| `MYSQL_DB` | 默认库名 |
| `ALLOW_INSERT_OPERATION` | 是否允许 INSERT，默认 `false` |
| `ALLOW_UPDATE_OPERATION` | 是否允许 UPDATE，默认 `false` |
| `ALLOW_DELETE_OPERATION` | 是否允许 DELETE，默认 `false` |

## 工作流程

1. **先摸清结构**：用 MCP 资源或只读 SQL（`SHOW TABLES`、`DESCRIBE`、`INFORMATION_SCHEMA`）确认库表与字段。
2. **再写查询**：优先 `SELECT`；加合理 `WHERE`、`LIMIT`；避免无过滤地 `SELECT *`。
3. **默认只读**：未明确要求写入时，不要执行 INSERT/UPDATE/DELETE。
4. **写操作**：仅在用户明确授权且 `.env` 中对应 `ALLOW_*` 为 `true` 时执行；执行前说明影响范围。
5. **结果说明**：用中文简要解释查询结果；大结果集先聚合或抽样。

## 本仓库场景

本仓库用于台风影响下的气象站数据分析。查询时应优先确认：

- 站点标识、观测时间、气象要素字段命名
- 时间范围是否覆盖目标台风时段
- 缺失值、重复观测、单位是否一致

## 故障排查

- MCP 不可用：检查 `.env` 是否存在、凭证是否正确、MySQL 是否可达
- 认证失败：核对 `MYSQL_USER` / `MYSQL_PASS` / `MYSQL_DB`
- 改完 `.env` 后：在 Cursor MCP 面板重启 `mysql` server
