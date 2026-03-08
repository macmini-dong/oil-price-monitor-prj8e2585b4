const chartCanvas = document.getElementById("oil-chart");
const chartEmpty = document.getElementById("chart-empty");
const statusNode = document.getElementById("collector-status");
const updatedNode = document.getElementById("updated-at");
const appVersionNode = document.getElementById("app-version");
const appUpdatedAtNode = document.getElementById("app-updated-at");
const wtiPriceNode = document.getElementById("wti-price");
const wtiTimeNode = document.getElementById("wti-time");
const brentPriceNode = document.getElementById("brent-price");
const brentTimeNode = document.getElementById("brent-time");
const rangeButtons = Array.from(document.querySelectorAll(".range-btn"));

let currentHours = 336;

function formatDate(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}

function formatPrice(value, currency = "USD") {
  if (typeof value !== "number" || Number.isNaN(value)) return "--";
  return `${value.toFixed(2)} ${currency}`;
}

function drawLine(ctx, points, xMap, yMap, color) {
  if (!points.length) return;
  ctx.beginPath();
  ctx.strokeStyle = color;
  ctx.lineWidth = 2.2;
  points.forEach((point, index) => {
    const x = xMap(index, points.length);
    const y = yMap(point.price);
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();
}

function drawChart(series) {
  const rect = chartCanvas.getBoundingClientRect();
  const width = Math.max(320, Math.floor(rect.width));
  const height = Math.max(240, Math.floor(rect.height));
  const dpr = window.devicePixelRatio || 1;

  chartCanvas.width = Math.floor(width * dpr);
  chartCanvas.height = Math.floor(height * dpr);

  const ctx = chartCanvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);

  const allPoints = series.flatMap((item) => item.points || []);
  if (!allPoints.length) {
    chartEmpty.classList.remove("hidden");
    return;
  }
  chartEmpty.classList.add("hidden");

  const padding = { top: 16, right: 14, bottom: 28, left: 52 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  const values = allPoints.map((item) => item.price);
  let minPrice = Math.min(...values);
  let maxPrice = Math.max(...values);
  if (minPrice === maxPrice) {
    minPrice -= 1;
    maxPrice += 1;
  }
  const pricePadding = (maxPrice - minPrice) * 0.12;
  minPrice -= pricePadding;
  maxPrice += pricePadding;

  const yMap = (value) => {
    const ratio = (value - minPrice) / (maxPrice - minPrice);
    return padding.top + chartHeight - ratio * chartHeight;
  };
  const xMap = (index, total) => {
    if (total <= 1) return padding.left + chartWidth / 2;
    return padding.left + (index / (total - 1)) * chartWidth;
  };

  ctx.strokeStyle = "rgba(21, 51, 71, 0.12)";
  ctx.lineWidth = 1;
  ctx.font = "12px Avenir Next, sans-serif";
  ctx.fillStyle = "rgba(74, 101, 117, 0.9)";

  for (let i = 0; i <= 5; i += 1) {
    const ratio = i / 5;
    const y = padding.top + ratio * chartHeight;
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(width - padding.right, y);
    ctx.stroke();
    const priceValue = maxPrice - ratio * (maxPrice - minPrice);
    ctx.fillText(priceValue.toFixed(2), 8, y + 4);
  }

  const wti = series.find((item) => item.symbol === "CL=F");
  const brent = series.find((item) => item.symbol === "BZ=F");
  if (wti) {
    drawLine(ctx, wti.points, xMap, yMap, "#0f9d8a");
  }
  if (brent) {
    drawLine(ctx, brent.points, xMap, yMap, "#ef6a33");
  }
}

function updateLatest(latest) {
  const wti = latest.find((item) => item.symbol === "CL=F");
  const brent = latest.find((item) => item.symbol === "BZ=F");

  wtiPriceNode.textContent = wti ? formatPrice(wti.price, wti.currency) : "--";
  wtiTimeNode.textContent = wti ? `采集时间 ${formatDate(wti.captured_at)}` : "--";

  brentPriceNode.textContent = brent ? formatPrice(brent.price, brent.currency) : "--";
  brentTimeNode.textContent = brent ? `采集时间 ${formatDate(brent.captured_at)}` : "--";
}

async function refresh() {
  try {
    const response = await fetch(`/api/v1/prices?hours=${currentHours}`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    drawChart(payload.series || []);
    updateLatest(payload.latest || []);

    const collector = payload.collector || {};
    if (collector.last_error) {
      statusNode.textContent = `采集失败：${collector.last_error}`;
      statusNode.style.color = "#b53c14";
    } else if (collector.last_success_at) {
      statusNode.textContent = "采集正常";
      statusNode.style.color = "#195f87";
    } else {
      statusNode.textContent = "等待首次采集";
      statusNode.style.color = "#195f87";
    }
    updatedNode.textContent = collector.last_success_at
      ? `最近成功：${formatDate(collector.last_success_at)}`
      : "最近成功：--";

    const appMeta = payload.app || {};
    if (appMeta.version) {
      appVersionNode.textContent = `v${String(appMeta.version).replace(/^v/i, "")}`;
    }
    if (appMeta.updated_at) {
      appUpdatedAtNode.textContent = appMeta.updated_at;
    }
  } catch (error) {
    statusNode.textContent = `页面刷新失败：${error.message}`;
    statusNode.style.color = "#b53c14";
  }
}

rangeButtons.forEach((button) => {
  button.addEventListener("click", () => {
    currentHours = Number(button.dataset.hours || "72");
    rangeButtons.forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    refresh();
  });
});

window.addEventListener("resize", () => refresh());
refresh();
setInterval(refresh, 60000);
