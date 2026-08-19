# AGENTS.md

## Cursor Cloud specific instructions

本仓库是「尤溪施工气象站 · 近24小时观测」项目:静态可视化站点(`site/`)加只读数据流水线(`scripts/`)。完整说明与命令见 `README.md`。GitHub Pages: https://xtzhou960821.github.io/typhoon/

### 开发与运行(命令见 README,勿重复记忆)

- 依赖安装于本地虚拟环境 `.venv/`,请用 `.venv/bin/...` 前缀调用,而非系统 Python;依赖清单见 `requirements.txt`(仅需 `pymysql`)。
- 本地预览站点、运行数据流水线(`scripts/ingest_and_analyze.py`)的具体命令见 `README.md`。
- 创建虚拟环境依赖系统包 `python3.12-venv`,已在环境搭建阶段安装,不应放入更新脚本。
- `site/` 为站点源;`docs/` 为 Pages 发布副本。ingest 会同步写出两份 `analysis.json` 与 `standalone.html`;Actions 部署前再将 `site/` 复制到 `docs/`。

### 气象监测数据库(MySQL)与 MCP —— 非显而易见

- **唯一**生产数据源为阿里云 MySQL:数据库 `tess_yangchen_ms`,主表 `yangchen_record`。ingest **只读 SELECT**,禁止 CREATE/ALTER/INSERT/UPDATE/DELETE。
- 表结构、示例 SQL、连接与用法见 skill `.cursor/skills/mysql-weather-db/SKILL.md`。
- 已配置**全局** MySQL MCP server(`@benborla29/mcp-server-mysql`),配置文件 `~/.cursor/mcp.json`(**不入库**),暴露只读工具 `mysql_query`(写操作默认关闭)。MCP 仅在 Cursor/Agent 会话启动时加载,新增/修改后需新会话才生效。
- 数据库密码**不写入仓库**:
  - 流水线优先读环境变量 `MYSQL_PASSWORD`(GitHub Actions 用 `${{ secrets.MYSQL_PASSWORD }}`);兼容 `MYSQL_PASS`。
  - MCP / skill 脚本通过 `"${env:MYSQL_PASS}"` 或环境变量 `MYSQL_PASS` 读取 Cursor Secret。
- `~/.cursor/mcp.json` 位于 VM 家目录,跨会话持久化依赖快照;若未保留,可用 skill 中的连接信息重建,密码始终取自 Secret。
- `.gitignore` 忽略 `.cursor/*`,但通过 `!.cursor/skills/` 显式保留共享 skill 目录。
