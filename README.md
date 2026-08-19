# 尤溪施工气象站 · 近24小时观测

业主施工现场扬尘/气象监测站近24小时看板。数据只读来自阿里云 MySQL `tess_yangchen_ms.yangchen_record`，经流水线写出 `analysis.json`，由静态页渲染。

## 公共访问

- **GitHub Pages**：https://xtzhou960821.github.io/typhoon/
- **单文件版**：https://xtzhou960821.github.io/typhoon/standalone.html（数据内嵌）

本地预览：

```bash
cd site && python3 -m http.server 8080
```

无数据库密码时，仓库内已提交一份 `site/data/analysis.json` 样例，页面仍可打开；小时级 Actions 跑通后会用真实近24小时序列覆盖部署产物（不必每小时回写 git）。

## 数据流水线

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

export MYSQL_PASSWORD='<密码>'          # 必填；亦可使用 MYSQL_PASS
# 可选覆盖：
# export MYSQL_HOST=db.wulianxx.com
# export MYSQL_PORT=3306
# export MYSQL_USER=root
# export MYSQL_DATABASE=tess_yangchen_ms

.venv/bin/python scripts/ingest_and_analyze.py
```

脚本**只执行 SELECT**（不建表、不写入），拉取近24小时全部 `DeviceId` 观测，计算 `station_stats` 与时间序列，写出：

- `site/data/analysis.json`
- `docs/data/analysis.json`（与 `site/` 同步，供 Pages）
- `site/standalone.html` / `docs/standalone.html`

当前站点名固定为「尤溪施工气象站」（`devices` 表无名称可用）。气压按 **kPa** 展示；风向为设备码 0–7 的八风向标签，不编造角度。

缺少 `MYSQL_PASSWORD` / `MYSQL_PASS` 时脚本会明确报错退出，不影响已提交的样例 JSON。

## GitHub Actions

工作流 `.github/workflows/pages.yml`：

- 触发：`push` 到 `main`、每小时 `schedule`、`workflow_dispatch`
- 步骤：安装依赖 → 用 Secret 跑 ingest → 将 `site/` 复制到 `docs/` → `upload-pages-artifact` 部署
- 必填 Secret：`MYSQL_PASSWORD`
- 可选 Secret：`MYSQL_HOST` / `MYSQL_PORT` / `MYSQL_USER` / `MYSQL_DATABASE`

小时任务在 Actions 内生成 JSON 并部署，**不会**每小时把 JSON commit 回仓库。

## 站点结构

- `site/index.html` — 看板
- `site/css/styles.css` — 样式
- `site/js/app.js` — Chart.js 渲染
- `site/data/analysis.json` — 分析结果
- `docs/` — Pages 发布副本（与 `site/` 保持同步）

## 设计

沿用 [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) Data-Dense Dashboard（Fira Sans / Fira Code，主色 `#1E40AF`，强调色 `#D97706`）。
