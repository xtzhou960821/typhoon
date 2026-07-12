/**
 * 台风巴威观测可视化主逻辑
 * 从 analysis.json 读取 MySQL 提取结果并渲染图表 / 地图
 */

/** @typedef {import('../data/analysis.json')} AnalysisData */

const PALETTE = {
  primary: "#1E40AF",
  secondary: "#3B82F6",
  accent: "#D97706",
  rain: "#0EA5E9",
  gust: "#DC2626",
  pressure: "#1E3A8A",
  humidity: "#64748B",
};

/** @type {Chart[]} */
const charts = [];

/**
 * 格式化北京时窗口文案
 * @param {{start:string,end:string}} window
 * @returns {string}
 */
function formatWindow(window) {
  return `${window.start.slice(5, 16).replace(" ", " ")} → ${window.end.slice(5, 16)} CST`;
}

/**
 * 渲染 KPI 卡片
 * @param {any} data
 */
function renderKpis(data) {
  const h = data.highlights;
  const items = [
    {
      label: "24h 最大降水",
      value: `${h.top_rain.precip_24h_mm}`,
      unit: "mm",
      sub: h.top_rain.name,
      cls: "warn",
    },
    {
      label: "最大阵风",
      value: `${h.top_gust.max_gust_ms}`,
      unit: "m/s",
      sub: `${h.top_gust.name} · 约${h.top_gust.max_gust_level}级`,
      cls: "alert",
    },
    {
      label: "最低气压",
      value: `${h.lowest_pressure.min_pressure_hpa}`,
      unit: "hPa",
      sub: h.lowest_pressure.name,
      cls: "",
    },
    {
      label: "样本规模",
      value: `${h.total_records}`,
      unit: "条",
      sub: `${h.total_stations} 站 × 近24小时`,
      cls: "",
    },
  ];

  const root = document.getElementById("kpiGrid");
  root.innerHTML = items
    .map(
      (item) => `
      <article class="kpi ${item.cls}">
        <p class="label">${item.label}</p>
        <p class="value">${item.value}<small style="font-size:0.55em;margin-left:0.25rem">${item.unit}</small></p>
        <p class="sub">${item.sub}</p>
      </article>`
    )
    .join("");
}

/**
 * 渲染登陆时间线
 * @param {any} data
 */
function renderTimeline(data) {
  const t = data.typhoon;
  const nodes = [
    {
      time: t.landfall_1.time,
      title: "玉环坎门首次登陆",
      detail: `${t.landfall_1.level} · ${t.landfall_1.wind_ms} m/s · ${t.landfall_1.pressure} hPa · ${t.landfall_1.place}`,
    },
    {
      time: t.landfall_2.time,
      title: "乐清清江二次登陆",
      detail: `${t.landfall_2.level} · ${t.landfall_2.wind_ms} m/s · ${t.landfall_2.pressure} hPa · ${t.landfall_2.place}`,
    },
    ...data.track
      .filter((p) => !p.note.includes("登陆"))
      .map((p) => ({
        time: p.track_time.slice(0, 16),
        title: p.category,
        detail: `${p.note} · 中心风速 ${p.wind_ms} m/s · ${p.pressure_hpa} hPa`,
      })),
  ].sort((a, b) => a.time.localeCompare(b.time));

  document.getElementById("landfallTimeline").innerHTML = nodes
    .map(
      (n) => `
      <li>
        <time datetime="${n.time}">${n.time}</time>
        <div>
          <strong>${n.title}</strong>
          <span>${n.detail}</span>
        </div>
      </li>`
    )
    .join("");
}

/**
 * 初始化 Leaflet 路径地图
 * @param {any} data
 */
function renderMap(data) {
  const map = L.map("stormMap", { scrollWheelZoom: false }).setView([28.2, 121.0], 7);
  L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
    attribution: "&copy; OpenStreetMap &copy; CARTO",
    maxZoom: 18,
  }).addTo(map);

  const latlngs = data.track.map((p) => [p.latitude, p.longitude]);
  L.polyline(latlngs, { color: "#1E40AF", weight: 3, opacity: 0.85 }).addTo(map);

  data.track.forEach((p, idx) => {
    const isLandfall = String(p.note).includes("登陆");
    L.circleMarker([p.latitude, p.longitude], {
      radius: isLandfall ? 8 : 5,
      color: isLandfall ? "#DC2626" : "#1E40AF",
      fillColor: isLandfall ? "#FCA5A5" : "#93C5FD",
      fillOpacity: 0.95,
      weight: 2,
    })
      .bindPopup(
        `<strong>${p.track_time.slice(5, 16)}</strong><br/>${p.category}<br/>${p.note}<br/>${p.wind_ms} m/s · ${p.pressure_hpa} hPa`
      )
      .addTo(map);

    if (idx === data.track.length - 1) {
      L.marker([p.latitude, p.longitude]).bindPopup("最新路径点").addTo(map);
    }
  });

  data.station_stats.forEach((s) => {
    L.circleMarker([s.lat, s.lon], {
      radius: 6,
      color: "#D97706",
      fillColor: "#FDE68A",
      fillOpacity: 0.95,
      weight: 2,
    })
      .bindPopup(
        `<strong>${s.name}</strong><br/>${s.role}<br/>降水 ${s.precip_24h_mm} mm<br/>阵风 ${s.max_gust_ms} m/s`
      )
      .addTo(map);
  });

  map.fitBounds(L.latLngBounds([...latlngs, ...data.station_stats.map((s) => [s.lat, s.lon])]).pad(0.2));
}

/**
 * 站点对比柱状图与表格
 * @param {any} data
 */
function renderStationCompare(data) {
  const stats = data.station_stats;
  const ctx = document.getElementById("stationBar");
  charts.push(
    new Chart(ctx, {
      type: "bar",
      data: {
        labels: stats.map((s) => s.name),
        datasets: [
          {
            label: "24h 降水 (mm)",
            data: stats.map((s) => s.precip_24h_mm),
            backgroundColor: "rgba(14, 165, 233, 0.75)",
            borderRadius: 4,
            yAxisID: "y",
          },
          {
            label: "最大阵风 (m/s)",
            data: stats.map((s) => s.max_gust_ms),
            backgroundColor: "rgba(220, 38, 38, 0.7)",
            borderRadius: 4,
            yAxisID: "y1",
          },
        ],
      },
      options: {
        responsive: true,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { position: "top" },
          tooltip: { enabled: true },
        },
        scales: {
          y: {
            type: "linear",
            position: "left",
            title: { display: true, text: "mm" },
            grid: { color: "rgba(30,64,175,0.08)" },
          },
          y1: {
            type: "linear",
            position: "right",
            title: { display: true, text: "m/s" },
            grid: { drawOnChartArea: false },
          },
        },
      },
    })
  );

  const tbody = document.querySelector("#stationTable tbody");
  tbody.innerHTML = stats
    .map(
      (s) => `
      <tr>
        <td>${s.name}</td>
        <td>${s.role}</td>
        <td>${s.precip_24h_mm}</td>
        <td>${s.max_gust_ms}</td>
        <td>${s.min_pressure_hpa}</td>
      </tr>`
    )
    .join("");
}

/**
 * 创建双轴折线/面积图
 * @param {string} canvasId
 * @param {string[]} labels
 * @param {object[]} datasets
 * @param {object} scales
 */
function makeLineChart(canvasId, labels, datasets, scales) {
  const chart = new Chart(document.getElementById(canvasId), {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { position: "top" } },
      scales,
      elements: {
        line: { tension: 0.28, borderWidth: 2 },
        point: { radius: 0, hitRadius: 8, hoverRadius: 4 },
      },
      animation: { duration: 700 },
    },
  });
  charts.push(chart);
  return chart;
}

/**
 * 渲染单站小时序列
 * @param {any} data
 * @param {string} stationId
 */
function renderSeries(data, stationId) {
  const series = data.series[stationId];
  if (!series) return;

  // 清理已有序列图（保留站点对比柱状图）
  ["pressureWind", "rainHumidity", "regionalChart"].forEach((id) => {
    const existing = Chart.getChart(id);
    if (existing) existing.destroy();
  });

  makeLineChart(
    "pressureWind",
    series.times,
    [
      {
        label: "气压 hPa",
        data: series.pressure,
        borderColor: PALETTE.pressure,
        backgroundColor: "rgba(30, 58, 138, 0.12)",
        fill: true,
        yAxisID: "y",
        borderDash: [],
      },
      {
        label: "风速 m/s",
        data: series.wind,
        borderColor: PALETTE.secondary,
        yAxisID: "y1",
        borderDash: [6, 4],
      },
      {
        label: "阵风 m/s",
        data: series.gust,
        borderColor: PALETTE.gust,
        yAxisID: "y1",
      },
    ],
    {
      y: {
        title: { display: true, text: "hPa" },
        grid: { color: "rgba(30,64,175,0.08)" },
      },
      y1: {
        position: "right",
        title: { display: true, text: "m/s" },
        grid: { drawOnChartArea: false },
      },
    }
  );

  makeLineChart(
    "rainHumidity",
    series.times,
    [
      {
        label: "小时降水 mm",
        data: series.precip,
        borderColor: PALETTE.rain,
        backgroundColor: "rgba(14, 165, 233, 0.25)",
        fill: true,
        yAxisID: "y",
      },
      {
        label: "相对湿度 %",
        data: series.humidity,
        borderColor: PALETTE.humidity,
        yAxisID: "y1",
        borderDash: [4, 4],
      },
    ],
    {
      y: {
        title: { display: true, text: "mm" },
        grid: { color: "rgba(30,64,175,0.08)" },
      },
      y1: {
        position: "right",
        min: 50,
        max: 100,
        title: { display: true, text: "%" },
        grid: { drawOnChartArea: false },
      },
    }
  );

  const regional = data.regional;
  makeLineChart(
    "regionalChart",
    regional.map((r) => r.label),
    [
      {
        label: "六站平均气压",
        data: regional.map((r) => r.mean_pressure),
        borderColor: PALETTE.pressure,
        yAxisID: "y",
      },
      {
        label: "六站最大阵风",
        data: regional.map((r) => r.max_gust),
        borderColor: PALETTE.gust,
        yAxisID: "y1",
        borderDash: [5, 4],
      },
      {
        label: "六站平均降水",
        data: regional.map((r) => r.mean_precip),
        borderColor: PALETTE.rain,
        backgroundColor: "rgba(14,165,233,0.15)",
        fill: true,
        yAxisID: "y1",
      },
    ],
    {
      y: {
        title: { display: true, text: "hPa" },
        grid: { color: "rgba(30,64,175,0.08)" },
      },
      y1: {
        position: "right",
        title: { display: true, text: "m/s · mm" },
        grid: { drawOnChartArea: false },
      },
    }
  );
}

/**
 * 填充研判与页脚
 * @param {any} data
 */
function renderInsights(data) {
  document.getElementById("insightList").innerHTML = data.insights
    .map((text) => `<li>${text}</li>`)
    .join("");

  const t = data.typhoon;
  const h = data.highlights;
  document.getElementById("briefBody").textContent =
    `${t.number}台风「${t.name_zh}」（${t.name_en}，国际编号 ${t.intl_id}）于 ${t.landfall_1.time} 以${t.landfall_1.level}在${t.landfall_1.place}登陆，` +
    `并于 ${t.landfall_2.time} 在${t.landfall_2.place}再次登陆。` +
    `近24小时站点资料显示：最大阵风 ${h.top_gust.max_gust_ms} m/s（${h.top_gust.name}），` +
    `累计降水峰值 ${h.top_rain.precip_24h_mm} mm（${h.top_rain.name}），` +
    `最低气压 ${h.lowest_pressure.min_pressure_hpa} hPa。` +
    `${t.impact} 展望：${t.forecast}`;

  document.getElementById("dataNote").textContent = data.data_note;
}

/**
 * 绑定站点选择器
 * @param {any} data
 */
function bindStationSelect(data) {
  const select = document.getElementById("stationSelect");
  const ids = Object.keys(data.series);
  select.innerHTML = ids
    .map((id) => `<option value="${id}">${data.series[id].name}</option>`)
    .join("");

  const preferred = ids.includes("YH") ? "YH" : ids[0];
  select.value = preferred;
  renderSeries(data, preferred);

  select.addEventListener("change", () => {
    renderSeries(data, select.value);
  });
}

/**
 * 应用入口
 */
async function main() {
  let data;
  if (window.__ANALYSIS__) {
    data = window.__ANALYSIS__;
  } else {
    const resp = await fetch("./data/analysis.json", { cache: "no-store" });
    if (!resp.ok) {
      throw new Error(`无法加载分析数据：${resp.status}`);
    }
    data = await resp.json();
  }

  document.getElementById("windowLabel").textContent = formatWindow(data.window);
  document.getElementById("heroLead").textContent =
    `${data.typhoon.number}台风「${data.typhoon.name_zh}」于今日凌晨两度登陆浙江。` +
    `本页展示 ${formatWindow(data.window)} 六站观测（MySQL 提取）与路径对照分析。`;

  renderKpis(data);
  renderTimeline(data);
  renderMap(data);
  renderStationCompare(data);
  bindStationSelect(data);
  renderInsights(data);
}

main().catch((err) => {
  console.error(err);
  document.getElementById("windowLabel").textContent = "数据加载失败";
  document.getElementById("heroLead").textContent = String(err.message || err);
});
