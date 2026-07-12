"""配置加载与路径工具。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# 仓库根目录（src/typhoon/config.py -> 上三级）
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "stations.yaml"


def load_config(path: Path | str | None = None) -> dict[str, Any]:
    """
    加载 YAML 配置文件。

    @param path - 配置文件路径，默认使用仓库内 ``config/stations.yaml``
    @returns 解析后的配置字典
    """
    config_path = Path(path) if path else DEFAULT_CONFIG
    with config_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"配置文件格式无效: {config_path}")
    return data


def ensure_output_dirs(config: dict[str, Any] | None = None) -> dict[str, Path]:
    """
    确保输出目录存在。

    @param config - 可选配置；未提供时自动加载默认配置
    @returns 包含 figures_dir / tables_dir 的路径字典
    """
    cfg = config or load_config()
    output = cfg.get("output", {})
    figures = ROOT / output.get("figures_dir", "outputs/figures")
    tables = ROOT / output.get("tables_dir", "outputs/tables")
    figures.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    return {"figures_dir": figures, "tables_dir": tables}
