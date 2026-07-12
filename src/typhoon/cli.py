"""命令行入口：运行台风巴威气象站分析。"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from typhoon.analysis import extreme_events, run_pipeline


def build_parser() -> argparse.ArgumentParser:
    """
    构建 CLI 参数解析器。

    @returns ArgumentParser 实例
    """
    parser = argparse.ArgumentParser(
        prog="typhoon-analyze",
        description="台风巴威影响下气象站数据分析",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="观测 CSV 路径；默认使用 data/raw/sample_stations.csv",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="配置文件路径；默认使用 config/stations.yaml",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """
    CLI 主函数。

    @param argv - 可选参数列表；默认读取 sys.argv
    @returns 进程退出码
    """
    args = build_parser().parse_args(argv)
    result = run_pipeline(args.csv, config_path=args.config)

    featured = pd.read_csv(result["processed_path"], parse_dates=["time"])
    events = extreme_events(featured, result["config"])
    events_path = result["summary_path"].parent / "extreme_events.csv"
    events.to_csv(events_path, index=False)

    print("台风巴威气象站分析完成")
    print(f"  观测行数: {result['rows']}")
    print(f"  处理后数据: {result['processed_path']}")
    print(f"  站点汇总: {result['summary_path']}")
    print(f"  极值事件: {events_path} ({len(events)} 条)")
    print(f"  图件数: {len(result['figure_paths'])}")
    for path in result["figure_paths"]:
        print(f"    - {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
