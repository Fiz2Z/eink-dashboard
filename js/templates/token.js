/**
 * 400×300 BWR AI Token panel (matches Python render_token layout).
 * Top: 30D TOTAL | TODAY + 30-day bars
 * Bottom: Codex | Grok only (icon + 30d tokens + % + bar)
 */

const RED = "#D71920";
const BLACK = "#000000";
const WHITE = "#FFFFFF";
const MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];

const iconCache = new Map();
const ICON_PATHS = {
  codex: "assets/icons/openai.svg",
  grok: "assets/icons/grok.svg",
};

function loadIcon(src) {
  if (iconCache.has(src)) {
    const c = iconCache.get(src);
    if (c.complete && c.naturalWidth > 0) return Promise.resolve(c);
  }
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      iconCache.set(src, img);
      resolve(img);
    };
    img.onerror = () => reject(new Error(src));
    img.src = src;
  });
}

async function ensureIcons() {
  await Promise.all(Object.values(ICON_PATHS).map((p) => loadIcon(p).catch(() => null)));
}

function formatValueParts(n) {
  n = Math.abs(Number(n) || 0);
  if (n < 1000) return [String(Math.round(n)), ""];
  const chain = [
    ["K", 1e3],
    ["M", 1e6],
    ["B", 1e9],
    ["T", 1e12],
  ];
  let idx = 0;
  for (let i = 0; i < chain.length; i++) {
    if (n >= chain[i][1]) idx = i;
  }
  let unit = chain[idx][0];
  let div = chain[idx][1];
  let s = sigStr(n / div, 4);
  while (parseFloat(s) >= 1000 && idx + 1 < chain.length) {
    idx++;
    unit = chain[idx][0];
    div = chain[idx][1];
    s = sigStr(n / div, 4);
  }
  return [s, unit];
}

function sigStr(v, sig = 4) {
  if (v === 0) return "0";
  const order = Math.floor(Math.log10(Math.abs(v)));
  const decimals = Math.max(0, sig - order - 1);
  let rounded = Number(v.toFixed(decimals));
  if (rounded >= 1000) return String(Math.round(rounded));
  if (decimals === 0) return String(Math.round(rounded));
  return rounded.toFixed(decimals).replace(/\.?0+$/, "");
}

function setFont(ctx, size, weight = "700") {
  ctx.font = `${weight} ${size}px "Segoe UI", "Arial Narrow", "Arial", "Microsoft YaHei", sans-serif`;
}

function strokeRoundRect(ctx, x, y, w, h, r, line) {
  ctx.strokeStyle = BLACK;
  ctx.lineWidth = line;
  const rr = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + rr, y);
  ctx.arcTo(x + w, y, x + w, y + h, rr);
  ctx.arcTo(x + w, y + h, x, y + h, rr);
  ctx.arcTo(x, y + h, x, y, rr);
  ctx.arcTo(x, y, x + w, y, rr);
  ctx.closePath();
  ctx.stroke();
}

function drawValue(ctx, x, y, n, numSize, color, maxW) {
  let [numS, unit] = formatValueParts(n);
  let size = numSize;
  setFont(ctx, size, "800");
  let unitSize = Math.max(10, Math.round(size * 0.58));
  setFont(ctx, unitSize, "700");
  const measure = () => {
    setFont(ctx, size, "800");
    const nw = ctx.measureText(numS).width;
    setFont(ctx, unitSize, "700");
    const uw = unit ? ctx.measureText(unit).width : 0;
    const gap = unit ? Math.max(2, size / 12) : 0;
    return nw + gap + uw;
  };
  while (maxW && measure() > maxW && size > 14) {
    size -= 1;
    unitSize = Math.max(9, Math.round(size * 0.58));
  }
  setFont(ctx, size, "800");
  ctx.fillStyle = color;
  ctx.textBaseline = "alphabetic";
  const nw = ctx.measureText(numS).width;
  ctx.fillText(numS, x, y);
  if (unit) {
    setFont(ctx, unitSize, "700");
    ctx.fillText(unit, x + nw + Math.max(2, size / 12), y);
  }
}

function dateLabel(d) {
  return `${MONTHS[d.getMonth()]} ${d.getDate()}`;
}

function buildDemoDaily() {
  const daily = [];
  for (let i = 0; i < 29; i++) daily.push(20000 + ((i * 17) % 60) * 1000);
  daily.push(58600);
  return daily;
}

export const tokenTemplate = {
  id: "token",
  name: "AI Token 用量",
  description: "30D TOTAL + TODAY + 30 日柱状图；仅 Codex / Grok。红条需三色。",
  defaults: {
    total30d: "1482000",
    todayTotal: "58600",
    codex30d: "986000",
    grok30d: "496000",
  },
  fields: [
    { key: "total30d", label: "30D TOTAL", type: "text" },
    { key: "todayTotal", label: "TODAY", type: "text" },
    { key: "codex30d", label: "Codex 30d", type: "text" },
    { key: "grok30d", label: "Grok 30d", type: "text" },
  ],

  async render(ctx, canvas, config) {
    await ensureIcons();
    const W = canvas.width;
    const H = canvas.height;
    ctx.imageSmoothingEnabled = false;
    ctx.fillStyle = WHITE;
    ctx.fillRect(0, 0, W, H);

    const total30d = num(config.total30d ?? config.total);
    const todayTotal = num(config.todayTotal);
    const codex30d = num(config.codex30d ?? config.codex);
    const grok30d = num(config.grok30d ?? config.grok);
    const sum = codex30d + grok30d;
    const codexPct = sum > 0 ? Math.round((codex30d / sum) * 100) : 0;
    const grokPct = sum > 0 ? 100 - codexPct : 0;

    let daily = config._data?.daily || config.daily;
    if (!Array.isArray(daily) || daily.length !== 30) daily = buildDemoDaily();

    const end = new Date();
    const start = new Date(end);
    start.setDate(start.getDate() - 29);
    const startLabel = dateLabel(start);
    const endLabel = dateLabel(end);

    const margin = 4;
    const gap = 5;
    const border = 2;
    const cardR = 7;

    // top card
    const topX = margin;
    const topY = margin;
    const topW = W - margin * 2;
    const topH = 200;
    strokeRoundRect(ctx, topX, topY, topW, topH, cardR, border);

    const metricsH = 78;
    const splitX = topX + Math.floor(topW * 0.56);
    ctx.strokeStyle = BLACK;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(splitX, topY + 14);
    ctx.lineTo(splitX, topY + metricsH - 8);
    ctx.stroke();

    setFont(ctx, 13, "700");
    ctx.fillStyle = BLACK;
    ctx.textBaseline = "top";
    ctx.fillText("30D TOTAL", topX + 12, topY + 10);
    ctx.fillText("TODAY", splitX + 14, topY + 10);

    ctx.textBaseline = "alphabetic";
    drawValue(ctx, topX + 12, topY + 58, total30d, 42, BLACK, splitX - topX - 24);
    drawValue(ctx, splitX + 14, topY + 58, todayTotal, 42, RED, topX + topW - splitX - 26);

    // bars
    const chartTop = topY + metricsH;
    const chartBot = topY + topH - 22;
    const chartH = chartBot - chartTop;
    const nBars = 30;
    const gapB = 2;
    let barW = Math.max(2, Math.floor((topW - 28 - gapB * (nBars - 1)) / nBars));
    const totalBarsW = barW * nBars + gapB * (nBars - 1);
    let chartLeft = topX + 14 + Math.floor((topW - 28 - totalBarsW) / 2);
    const maxV = Math.max(1, ...daily);

    for (let i = 0; i < 30; i++) {
      const v = daily[i] || 0;
      const isRecent5 = i >= 25;
      const isToday = i === 29;
      const bw = barW + (isToday ? 1 : 0);
      const x = chartLeft + i * (barW + gapB);
      let h = Math.max(2, Math.floor((chartH * v) / maxV));
      if (isToday) h = Math.min(chartH, Math.floor(h * 1.08) + 2);
      ctx.fillStyle = isRecent5 ? RED : BLACK;
      ctx.fillRect(x, chartBot - h, bw, h);
    }

    setFont(ctx, 11, "600");
    ctx.fillStyle = BLACK;
    ctx.textBaseline = "top";
    ctx.fillText(startLabel, topX + 12, topY + topH - 16);
    const ew = ctx.measureText(endLabel).width;
    ctx.fillText(endLabel, topX + topW - 12 - ew, topY + topH - 16);

    // bottom cards
    const bottomY = topY + topH + gap;
    const bottomH = H - margin - bottomY;
    const cardW = Math.floor((W - margin * 2 - gap) / 2);

    drawVendor(ctx, margin, bottomY, cardW, bottomH, "codex", codex30d, codexPct, border, cardR);
    drawVendor(
      ctx,
      margin + cardW + gap,
      bottomY,
      cardW,
      bottomH,
      "grok",
      grok30d,
      grokPct,
      border,
      cardR
    );
  },
};

function drawVendor(ctx, x, y, w, h, key, tokens, pct, border, cardR) {
  // icon + number share one vertical center line above the progress bar
  strokeRoundRect(ctx, x, y, w, h, cardR, border);
  const pad = 10;
  const iconSize = 38;
  const iconGap = 10;
  const barH = 10;
  const barY = y + h - pad - barH;
  const midY = Math.floor((y + pad + barY - 4) / 2);
  const pctGutter = 44;

  const img = iconCache.get(ICON_PATHS[key]);
  let textLeft = x + pad;
  if (img && img.complete) {
    ctx.drawImage(img, x + pad, midY - iconSize / 2, iconSize, iconSize);
    textLeft = x + pad + iconSize + iconGap;
  }

  setFont(ctx, 15, "700");
  ctx.fillStyle = BLACK;
  ctx.textBaseline = "middle";
  const pctS = `${pct}%`;
  const pw = ctx.measureText(pctS).width;
  ctx.fillText(pctS, x + w - pad - pw, midY);

  // number + unit on same midY (middle baseline)
  let [numS, unit] = formatValueParts(tokens);
  let size = 28;
  const maxW = Math.max(24, x + w - pad - pctGutter - textLeft);
  setFont(ctx, size, "800");
  const measure = () => {
    setFont(ctx, size, "800");
    const nw = ctx.measureText(numS).width;
    const us = Math.max(12, Math.round(size * 0.58));
    setFont(ctx, us, "700");
    const uw = unit ? ctx.measureText(unit).width : 0;
    const gap = unit ? Math.max(2, size / 12) : 0;
    return nw + gap + uw;
  };
  while (measure() > maxW && size > 14) size -= 1;

  setFont(ctx, size, "800");
  ctx.textBaseline = "middle";
  ctx.fillStyle = BLACK;
  ctx.fillText(numS, textLeft, midY);
  if (unit) {
    const nw = ctx.measureText(numS).width;
    const us = Math.max(12, Math.round(size * 0.58));
    setFont(ctx, us, "700");
    ctx.fillText(unit, textLeft + nw + Math.max(2, size / 12), midY);
  }

  strokeRoundRect(ctx, x + pad, barY, w - pad * 2, barH, 3, 1);
  const fillW = Math.floor(((w - pad * 2) * Math.min(100, pct)) / 100);
  if (fillW > 2) {
    ctx.fillStyle = RED;
    ctx.fillRect(x + pad + 1, barY + 1, fillW - 2, barH - 2);
  }
}

function num(v) {
  const n = Number(String(v ?? "0").replace(/[,_\s]/g, ""));
  return Number.isFinite(n) ? n : 0;
}
