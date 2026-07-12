# typhoon

2026年7月11日台风巴威影响下气象站数据分析

## 项目简介

读取气象站观测数据(风速、阵风、气压、降水、气温),按站点计算关键统计量,
识别台风影响最强的站点与时刻,并绘制风速、气压随时间变化的图表。

## 环境要求

- Python 3.12
- 系统包 `python3.12-venv`(用于创建虚拟环境)

## 快速开始

```bash
# 创建虚拟环境并安装依赖
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt   # 含开发工具(ruff、pytest)
# 仅运行时依赖:  .venv/bin/python -m pip install -r requirements.txt

# 运行分析(读取 data/ 下示例数据,图表输出到 output/)
.venv/bin/python analyze.py

# 代码检查
.venv/bin/ruff check .

# 运行测试
.venv/bin/pytest -q
```

## 目录结构

- `analyze.py` —— 分析入口,支持 `--data` 与 `--output` 参数。
- `data/weather_stations_bavi.csv` —— 示例气象站观测数据。
- `tests/` —— 单元测试。
- `output/` —— 生成的图表(已在 `.gitignore` 中忽略)。
