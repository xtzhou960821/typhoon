# 台风巴威 · 浙南气象站近24小时观测分析

2026年7月11–12日，第9号台风「巴威」先后登陆浙江玉环、乐清。本仓库从 MySQL（`typhoon_obs`）提取近24小时站点观测，结合中央气象台路径通报，生成可视化分析站点。

## 公共访问

- **当前公网预览（Cloudflare Tunnel）**：https://stunning-obviously-ken-convicted.trycloudflare.com/
- **单文件版**：同域名下 `/standalone.html`（数据已内嵌，便于 CDN 分享）
- **GitHub Pages**：合并后在仓库 Settings → Pages 启用 `docs/` 或 Actions 工作流，预期地址 `https://xtzhou960821.github.io/typhoon/`

本地预览：

```bash
cd site && python3 -m http.server 8080
```

## 数据流水线

```bash
# 依赖
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# 需本机 MySQL，库名 typhoon_obs，账号见 scripts/ingest_and_analyze.py
.venv/bin/python scripts/ingest_and_analyze.py
```

脚本会：

1. 创建 `stations` / `observations` / `typhoon_track` 表  
2. 拉取 Open-Meteo 浙南六站小时观测并入库  
3. 从 MySQL 提取近24小时并写出 `site/data/analysis.json`

## 设计

使用 [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) 生成 Data-Dense Dashboard 设计系统（Fira Sans / Fira Code，主色 `#1E40AF`，强调色 `#D97706`）。

## 站点结构

- `site/index.html` — 分析页  
- `site/css/styles.css` — 样式  
- `site/js/app.js` — Chart.js + Leaflet 渲染  
- `site/data/analysis.json` — MySQL 分析结果  

## 说明

若云环境未配置你的远程 MySQL，流水线会使用本机 `typhoon_obs` 库承载观测数据；路径信息来自中央气象台公开通报。
