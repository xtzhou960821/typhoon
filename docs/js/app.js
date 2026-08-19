/**
 * 尤溪施工气象站观测看板主逻辑
 * 从 analysis.json 读取近24小时 MySQL 提取结果并渲染 KPI / 图表
 */

const PALETTE = {
  primary: "#1E40AF",
  secondary: "#3B82F6",
  accent: "#D97706",
  rain: "#0EA5E9",
  gust: "#DC2626",
  pressure: "#1E3A8A",
  humidity: "#64748B",
  pm25: "#7C3AED",
  pm10: "#DB2777",
  noise: "#059669",
  temp: "#EA580C",
};

/** @type {Chart[]} */
const charts = [];

/**
 * 格式化北京时窗口文案
 * @param {{start:string,end:string}} window
 * @returns {string}
 */
function formatWindow(window) {
  return `${window.start.slice(5, 16)} → ${window.end.slice(5, 16)} CST`;
}

/**
 * 空值占位
 * @param {unknown} value
 * @param {number} [digits]
 * @returns {string}
 */
function fmt(value, digits = 1) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") return value.toFixed(digits);
  return String(value);
}

/**
 * 稀疏化横轴标签,避免 ~288 点过密
 * @param {string[]} labels
 * @param {number} maxTicks
 * @returns {(ctx:{index:number,chart:Chart}) => string|undefined}
 */
function sparseTicks(labels, maxTicks = 8) {
  const step = Math.max(1, Math.ceil(labels.length / maxTicks));
  return (ctx) => {
    const i = ctx.index;
    if (i % step === 0 || i === labels.length - 1) return labels[i];
    return undefined;
  };
}

/**
 * 渲染最新读数 KPI
 * @param {any} data
 */
function renderKpis(data) {
  const L = data.latest;
  const windText =
    L.wind_direction_label != null
      ? `码 ${L.wind_direction} · ${L.wind_direction_label}`
      : L.wind_direction != null
        ? `码 ${L.wind_direction}`
        : "—";

  const items = [
    { label: "气温", value: fmt(L.temperature), unit: "°C", sub: `湿度 ${fmt(L.humidity)} %`, cls: "" },
    { label: "风速", value: fmt(L.wind_speed), unit: "m/s", sub: `风力 ${fmt(L.wind_power, 0)} 级`, cls: "" },
    { label: "风向", value: windText, unit: "", sub: "八风向标签(非度数)", cls: "warn" },
    { label: "气压", value: fmt(L.pressure_kpa), unit: "kPa", sub: "非 hPa", cls: "" },
    { label: "今日降水", value: fmt(L.today_rainfall), unit: "mm", sub: `瞬时 ${fmt(L.instantaneous_rainfall)} mm`, cls: "" },
    { label: "PM2.5", value: fmt(L.pm25), unit: "", sub: `PM10 ${fmt(L.pm10)}`, cls: "" },
    { label: "噪声", value: fmt(L.noise), unit: "dB", sub: `光照 ${fmt(L.light_intensity, 0)}`, cls: "" },
    {
      label: "样本",
      value: `${data.station_stats.sample_count}`,
      unit: "条",
      sub: data.latest.uploadtime?.slice(5, 16) || "近24小时",
      cls: "",
    },
  ];

  const root = document.getElementById("kpiGrid");
  root.innerHTML = items
    .map(
      (item) => `
      <article class="kpi ${item.cls}">
        <p class="label">${item.label}</p>
        <p class="value">${item.value}${
          item.unit
            ? `<small style="font-size:0.55em;margin-left:0.25rem">${item.unit}</small>`
            : ""
        }</p>
        <p class="sub">${item.sub}</p>
      </article>`
    )
    .join("");

  document.getElementById("kpiSub").textContent =
    `最新采样 ${L.uploadtime || "—"} · 北京时`;
}

/**
 * 渲染极值表
 * @param {any} data
 */
function renderStatsTable(data) {
  const s = data.station_stats;
  const rows = [
    ["气温 °C", s.temperature],
    ["湿度 %", s.humidity],
    ["风速 m/s", s.wind_speed],
    ["风力级", s.wind_power],
    ["气压 kPa", s.pressure_kpa],
    ["PM2.5", s.pm25],
    ["PM10", s.pm10],
    ["噪声 dB", s.noise],
    ["光照", s.light_intensity],
  ];

  const tbody = document.querySelector("#statsTable tbody");
  tbody.innerHTML = rows
    .map(([name, st]) => {
      if (!st) return "";
      return `<tr>
        <td>${name}</td>
        <td>${fmt(st.min)}</td>
        <td>${fmt(st.max)}</td>
        <td>${fmt(st.avg)}</td>
        <td>${fmt(st.latest)}</td>
      </tr>`;
    })
    .join("");
}

/**
 * 创建双轴折线图
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
      plugins: {
        legend: { position: "top" },
        tooltip: {
          callbacks: {
            title: (items) => {
              const i = items[0]?.dataIndex;
              return window.__SERIES_FULL_TIMES__?.[i] || labels[i] || "";
            },
          },
        },
      },
      scales: {
        x: {
          ticks: {
            autoSkip: false,
            maxRotation: 0,
            callback: sparseTicks(labels),
          },
          grid: { color: "rgba(30,64,175,0.06)" },
        },
        ...scales,
      },
      elements: {
        line: { tension: 0.22, borderWidth: 2 },
        point: { radius: 0, hitRadius: 6, hoverRadius: 3 },
      },
      animation: { duration: 650 },
    },
  });
  charts.push(chart);
  return chart;
}

/**
 * 渲染全部趋势图
 * @param {any} data
 */
function renderSeries(data) {
  const series = data.series;
  const labels = series.times;
  window.__SERIES_FULL_TIMES__ = series.full_times;

  makeLineChart(
    "tempHumidity",
    labels,
    [
      {
        label: "气温 °C",
        data: series.temperature,
        borderColor: PALETTE.temp,
        backgroundColor: "rgba(234, 88, 12, 0.12)",
        fill: true,
        yAxisID: "y",
      },
      {
        label: "湿度 %",
        data: series.humidity,
        borderColor: PALETTE.humidity,
        yAxisID: "y1",
        borderDash: [4, 4],
      },
    ],
    {
      y: {
        title: { display: true, text: "°C" },
        grid: { color: "rgba(30,64,175,0.08)" },
      },
      y1: {
        position: "right",
        title: { display: true, text: "%" },
        grid: { drawOnChartArea: false },
      },
    }
  );

  makeLineChart(
    "windChart",
    labels,
    [
      {
        label: "风速 m/s",
        data: series.wind_speed,
        borderColor: PALETTE.secondary,
        backgroundColor: "rgba(59, 130, 246, 0.12)",
        fill: true,
        yAxisID: "y",
      },
      {
        label: "风力级",
        data: series.wind_power,
        borderColor: PALETTE.gust,
        yAxisID: "y1",
        borderDash: [5, 4],
      },
    ],
    {
      y: {
        title: { display: true, text: "m/s" },
        grid: { color: "rgba(30,64,175,0.08)" },
      },
      y1: {
        position: "right",
        title: { display: true, text: "级" },
        grid: { drawOnChartArea: false },
      },
    }
  );

  makeLineChart(
    "pressureChart",
    labels,
    [
      {
        label: "气压 kPa",
        data: series.pressure_kpa,
        borderColor: PALETTE.pressure,
        backgroundColor: "rgba(30, 58, 138, 0.12)",
        fill: true,
        yAxisID: "y",
      },
    ],
    {
      y: {
        title: { display: true, text: "kPa" },
        grid: { color: "rgba(30,64,175,0.08)" },
      },
    }
  );

  makeLineChart(
    "rainChart",
    labels,
    [
      {
        label: "瞬时降水 mm",
        data: series.instantaneous_rainfall,
        borderColor: PALETTE.rain,
        backgroundColor: "rgba(14, 165, 233, 0.2)",
        fill: true,
        yAxisID: "y",
      },
      {
        label: "今日累计 mm",
        data: series.today_rainfall,
        borderColor: PALETTE.primary,
        yAxisID: "y1",
        borderDash: [4, 4],
      },
    ],
    {
      y: {
        title: { display: true, text: "瞬时 mm" },
        grid: { color: "rgba(30,64,175,0.08)" },
      },
      y1: {
        position: "right",
        title: { display: true, text: "今日 mm" },
        grid: { drawOnChartArea: false },
      },
    }
  );

  makeLineChart(
    "pmChart",
    labels,
    [
      {
        label: "PM2.5",
        data: series.pm25,
        borderColor: PALETTE.pm25,
        yAxisID: "y",
      },
      {
        label: "PM10",
        data: series.pm10,
        borderColor: PALETTE.pm10,
        yAxisID: "y",
        borderDash: [5, 4],
      },
    ],
    {
      y: {
        title: { display: true, text: "浓度" },
        grid: { color: "rgba(30,64,175,0.08)" },
      },
    }
  );

  makeLineChart(
    "noiseChart",
    labels,
    [
      {
        label: "噪声 dB",
        data: series.noise,
        borderColor: PALETTE.noise,
        backgroundColor: "rgba(5, 150, 105, 0.12)",
        fill: true,
        yAxisID: "y",
      },
    ],
    {
      y: {
        title: { display: true, text: "dB" },
        grid: { color: "rgba(30,64,175,0.08)" },
      },
    }
  );
}

/**
 * 填充摘要与页脚
 * @param {any} data
 */
function renderInsights(data) {
  document.getElementById("insightList").innerHTML = data.insights
    .map((text) => `<li>${text}</li>`)
    .join("");

  const st = data.station;
  const L = data.latest;
  document.getElementById("briefBody").textContent =
    `${st.name}（设备 ${st.device_id}）位于${st.location}。` +
    `采样间隔${st.interval_note}。最新：气温 ${fmt(L.temperature)} °C，` +
    `湿度 ${fmt(L.humidity)} %，风速 ${fmt(L.wind_speed)} m/s，` +
    `气压 ${fmt(L.pressure_kpa)} kPa，今日降水 ${fmt(L.today_rainfall)} mm。`;

  document.getElementById("dataNote").textContent = data.data_note;
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
  document.getElementById("heroEyebrow").textContent =
    `${data.station.location} · 设备 ${data.station.device_id}`;
  document.getElementById("heroTitle").textContent = data.station.name;
  document.getElementById("heroLead").textContent =
    `展示 ${formatWindow(data.window)} 近24小时观测（${data.station_stats.sample_count} 条）。` +
    `最新气温 ${fmt(data.latest.temperature)} °C，风速 ${fmt(data.latest.wind_speed)} m/s，` +
    `气压 ${fmt(data.latest.pressure_kpa)} kPa。`;

  renderKpis(data);
  renderStatsTable(data);
  renderSeries(data);
  renderInsights(data);
}

main().catch((err) => {
  console.error(err);
  document.getElementById("windowLabel").textContent = "数据加载失败";
  document.getElementById("heroLead").textContent = String(err.message || err);
});
