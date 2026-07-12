# AGENTS.md

## Cursor Cloud specific instructions

本仓库是「台风巴威 · 气象站观测分析」项目:一个静态可视化站点(`site/`)加数据流水线(`scripts/`)。完整说明、部署与运行命令见 `README.md`。

### 开发与运行(命令见 README,勿重复记忆)

- 依赖安装于本地虚拟环境 `.venv/`,请用 `.venv/bin/...` 前缀调用,而非系统 Python;依赖清单见 `requirements.txt`。
- 本地预览站点、运行数据流水线(`scripts/ingest_and_analyze.py`)的具体命令见 `README.md`。
- 创建虚拟环境依赖系统包 `python3.12-venv`,已在环境搭建阶段安装,不应放入更新脚本。

### 气象监测数据库(MySQL)与 MCP —— 非显而易见

- 你的**真实**气象观测数据在阿里云 MySQL:数据库 `tess_yangchen_ms`,主表 `yangchen_record`(约 11 万+ 行)。注意:这与 `README.md` 数据流水线里用到的本机 `typhoon_obs` 库是两套不同数据源。表结构、示例 SQL、连接与用法见 skill `.cursor/skills/mysql-weather-db/SKILL.md`。
- 已配置**全局** MySQL MCP server(`@benborla29/mcp-server-mysql`),配置文件 `~/.cursor/mcp.json`(**不入库**),暴露只读工具 `mysql_query`(写操作默认关闭)。MCP 仅在 Cursor/Agent 会话启动时加载,新增/修改后需新会话才生效。
- 数据库密码**不写入仓库**:MCP 配置通过 `"${env:MYSQL_PASS}"` 从 **Cursor Secret `MYSQL_PASS`** 读取(在「Secrets」面板添加);终端脚本 `.cursor/skills/mysql-weather-db/scripts/query.py` 也从环境变量 `MYSQL_PASS` 读取。
- `~/.cursor/mcp.json` 位于 VM 家目录,跨会话持久化依赖快照;若未保留,可用 skill 中的连接信息重建,密码始终取自 Secret `MYSQL_PASS`。
- `.gitignore` 忽略 `.cursor/*`,但通过 `!.cursor/skills/` 显式保留共享 skill 目录。
