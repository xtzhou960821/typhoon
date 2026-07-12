# typhoon

2026 年 7 月 11 日台风 **巴威（Bavi，2026 年第 9 号）** 影响下的气象站数据分析。

## 功能

- 读取多站逐小时观测 CSV（气温、气压、湿度、风速/阵风、风向、小时降水）
- 数据清洗、衍生指标（累计降水、气压 3 小时变化、阵风比）
- 站点极值汇总与阈值事件提取（大风 / 强降水）
- 自动输出时序图与累计降水对比图

## 快速开始

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 使用内置示例数据跑通流水线
typhoon-analyze
# 或
python -m typhoon.cli
```

输出位置：

- `data/processed/stations_featured.csv` — 清洗与衍生后的观测
- `outputs/tables/station_summary.csv` — 站点汇总
- `outputs/tables/extreme_events.csv` — 阈值事件
- `outputs/figures/` — 各站时序图与降水对比图

## 使用自有数据

CSV 需包含以下列：

| 列名 | 说明 |
|------|------|
| `time` | 观测时间（建议 UTC+8） |
| `station_id` | 站号 |
| `station_name` | 站名 |
| `temp_c` | 气温 ℃ |
| `pressure_hpa` | 气压 hPa |
| `humidity_pct` | 相对湿度 % |
| `wind_speed_ms` | 平均风速 m/s |
| `wind_gust_ms` | 阵风 m/s |
| `wind_dir_deg` | 风向 ° |
| `precip_1h_mm` | 小时降水 mm |

```bash
typhoon-analyze --csv path/to/your_stations.csv
```

站点列表、分析时间窗与阈值见 [`config/stations.yaml`](config/stations.yaml)。

## 重新生成示例数据

```bash
python scripts/generate_sample_data.py
```

示例数据为演示用合成序列，模拟闽浙沿海登陆影响与华北远距离水汽输送差异，**非正式业务实况**。

## 测试

```bash
pytest
```

## 目录结构

```
config/           # 台风与站点配置
data/raw/         # 原始观测
data/processed/   # 处理后数据
src/typhoon/      # 核心库（io / process / viz / analysis / cli）
scripts/          # 辅助脚本
outputs/          # 图表与汇总表
tests/            # 单元测试
```
