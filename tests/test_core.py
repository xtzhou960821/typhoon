"""核心模块单元测试。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from typhoon.analysis import extreme_events, run_pipeline
from typhoon.config import load_config
from typhoon.io import load_sample_data, read_station_csv
from typhoon.process import add_derived_features, clean_observations, station_summary


@pytest.fixture(scope="module")
def sample_df() -> pd.DataFrame:
    """加载示例观测数据。"""
    return load_sample_data()


def test_load_config_has_typhoon_meta() -> None:
    """配置应包含台风巴威元信息与站点列表。"""
    cfg = load_config()
    assert cfg["typhoon"]["name"] == "巴威"
    assert cfg["typhoon"]["english_name"] == "Bavi"
    assert len(cfg["stations"]) >= 3


def test_read_sample_columns(sample_df: pd.DataFrame) -> None:
    """示例数据应包含必需列且时间可解析。"""
    assert "station_id" in sample_df.columns
    assert pd.api.types.is_datetime64_any_dtype(sample_df["time"])
    assert sample_df["station_id"].nunique() >= 3


def test_clean_and_features(sample_df: pd.DataFrame) -> None:
    """清洗与衍生特征后应产生累计降水等列。"""
    cleaned = clean_observations(sample_df)
    featured = add_derived_features(cleaned)
    assert "precip_cumsum_mm" in featured.columns
    assert "pressure_delta_3h" in featured.columns
    summary = station_summary(featured)
    assert set(["station_id", "precip_total_mm", "gust_max_ms"]).issubset(summary.columns)


def test_pipeline_writes_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """流水线应写出汇总表与图件。"""
    # 将输出重定向到临时目录，避免污染仓库 outputs
    import typhoon.analysis as analysis_mod
    import typhoon.config as config_mod

    def _fake_dirs(config=None):
        figures = tmp_path / "figures"
        tables = tmp_path / "tables"
        figures.mkdir(parents=True, exist_ok=True)
        tables.mkdir(parents=True, exist_ok=True)
        return {"figures_dir": figures, "tables_dir": tables}

    monkeypatch.setattr(analysis_mod, "ensure_output_dirs", _fake_dirs)
    monkeypatch.setattr(config_mod, "ensure_output_dirs", _fake_dirs)

    processed = tmp_path / "processed.csv"

    def _fake_write(df, path):
        # 流水线内有两处 write：processed 与 summary
        p = Path(path)
        if "summary" in p.name:
            p = tmp_path / "tables" / "station_summary.csv"
            p.parent.mkdir(parents=True, exist_ok=True)
        else:
            p = processed
        df.to_csv(p, index=False)
        return p

    monkeypatch.setattr(analysis_mod, "write_processed", _fake_write)

    result = run_pipeline()
    assert result["rows"] > 0
    assert processed.exists()
    assert (tmp_path / "tables" / "station_summary.csv").exists()
    assert len(result["figure_paths"]) >= 2
    for fig in result["figure_paths"]:
        assert Path(fig).exists()


def test_extreme_events(sample_df: pd.DataFrame) -> None:
    """阈值事件提取应返回子集列。"""
    featured = add_derived_features(clean_observations(sample_df))
    events = extreme_events(featured)
    assert {"time", "station_id", "wind_gust_ms", "precip_1h_mm"}.issubset(events.columns)


def test_read_station_csv_missing_column(tmp_path: Path) -> None:
    """缺少必要列时应抛出 ValueError。"""
    bad = tmp_path / "bad.csv"
    bad.write_text("time,station_id\n2026-07-11 00:00:00,1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="缺少必要列"):
        read_station_csv(bad)
