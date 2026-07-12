# AGENTS.md

## Cursor Cloud specific instructions

本仓库是一个 **Python 数据分析** 项目(气象站/台风数据分析)。

### 服务与命令

单一服务,无长驻进程或数据库,通过 CLI 运行:

- 运行应用:`.venv/bin/python analyze.py`(读取 `data/weather_stations_bavi.csv`,图表写入 `output/`)
- 代码检查:`.venv/bin/ruff check .`
- 运行测试:`.venv/bin/pytest -q`

标准依赖与用法见 `README.md`;依赖清单见 `requirements.txt` / `requirements-dev.txt`。

### 非显而易见的注意事项

- 依赖安装在项目本地虚拟环境 `.venv/` 中(由启动更新脚本自动创建/刷新),请使用 `.venv/bin/...` 前缀调用工具,而非系统 Python。
- 创建虚拟环境依赖系统包 `python3.12-venv`;该系统包已在环境搭建阶段安装,不应放入更新脚本。
- `analyze.py` 使用 matplotlib 的非交互 `Agg` 后端,可在无图形界面/无头环境下直接出图。
- 图表中的站点标注使用英文(`STATION_LABELS`),因默认字体(DejaVu Sans)缺少中文字形;控制台输出仍为中文站名。如需在图中显示中文,需另行安装中文字体。

### 气象监测数据库(MySQL)与 MCP

- 真实观测数据在阿里云 MySQL(数据库 `tess_yangchen_ms`,主表 `yangchen_record`,约 11 万+ 行)。表结构、示例 SQL 与用法见 skill `.cursor/skills/mysql-weather-db/SKILL.md`。
- 已配置全局 MySQL MCP server(`@benborla29/mcp-server-mysql`),配置文件 `~/.cursor/mcp.json`(**不入库**),暴露只读工具 `mysql_query`。MCP 只在 Cursor/Agent 会话启动时加载,新增/修改后需新会话才生效。
- 数据库密码不写入仓库:MCP 配置通过 `"${env:MYSQL_PASS}"` 从 **Cursor Secret `MYSQL_PASS`** 读取(在「Secrets」面板添加);终端脚本 `.cursor/skills/mysql-weather-db/scripts/query.py` 也从环境变量 `MYSQL_PASS` 读取。
- `~/.cursor/mcp.json` 位于 VM 家目录,其跨会话持久化依赖快照;若未持久化,可用相同连接信息重建(见 skill),密码始终来自 Secret `MYSQL_PASS`。
