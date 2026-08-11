/**
 * AI Token dashboard — TOTAL USED reference layout:
 * header | big centered total + red underline | 2×2 icon+value+pct+bar
 * No vendor names, no LIMIT/RESET footer.
 */

const RED = "#E60000";
const MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];

/** @type {Map<string, HTMLImageElement>} */
const iconCache = new Map();

const ICON_PATHS = {
  codex: "assets/icons/openai.svg",
  claude: "assets/icons/anthropic.svg",
  grok: "assets/icons/grok.svg",
  deepseek: "assets/icons/deepseek.svg",
};

function loadIcon(src) {
  if (iconCache.has(src)) {
    const cached = iconCache.get(src);
    if (cached.complete && cached.naturalWidth > 0) return Promise.resolve(cached);
  }
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.decoding = "async";
    img.onload = () => {
      iconCache.set(src, img);
      resolve(img);
    };
    img.onerror = () => reject(new Error(`图标加载失败: ${src}`));
    img.src = src;
  });
}

async function ensureIcons() {
  await Promise.all(Object.values(ICON_PATHS).map((p) => loadIcon(p).catch(() => null)));
}

export const tokenTemplate = {
  id: "token",
  name: "AI Token 用量",
  description:
    "TOTAL USED 大数字 + 四宫格（仅图标/用量/占比/进度条）。红条需三色模式。",
  defaults: {
    dateLabel: "",
    total: "2480000",
    limit: "3500000",
    resetDays: "20",
    codex: "986000",
    claude: "742000",
    grok: "496000",
    deepseek: "256000",
  },
  fields: [
    { key: "dateLabel", label: "日期（空=今天）", type: "text" },
    { key: "total", label: "TOTAL USED", type: "text" },
    { key: "limit", label: "LIMIT（算百分比用，可不显示）", type: "text" },
    { key: "resetDays", label: "RESET 天数（保留字段）", type: "number" },
    { key: "codex", label: "Codex", type: "text" },
    { key: "claude", label: "Claude", type: "text" },
    { key: "grok", label: "Grok", type: "text" },
    { key: "deepseek", label: "DeepSeek", type: "text" },
  ],

  async render(ctx, canvas, config) {
    await ensureIcons();

    const W = canvas.width;
    const H = canvas.height;
    const s = Math.min(W / 400, H / 300);

    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.fillStyle = "#fff";
    ctx.fillRect(0, 0, W, H);

    const total = num(config.total);
    const providers = [
      { id: "codex", value: num(config.codex), icon: ICON_PATHS.codex },
      { id: "claude", value: num(config.claude), icon: ICON_PATHS.claude },
      { id: "grok", value: num(config.grok), icon: ICON_PATHS.grok },
      { id: "deepseek", value: num(config.deepseek), icon: ICON_PATHS.deepseek },
    ];
    const sum = providers.reduce((a, p) => a + p.value, 0) || 1;
    providers.forEach((p) => {
      p.pct = Math.round((p.value / sum) * 100);
    });

    const m = Math.max(6, Math.round(8 * s));
    const headerH = Math.max(30, Math.round(38 * s));
    const gap = Math.max(5, Math.round(7 * s));
    const radius = Math.max(6, Math.round(8 * s));
    const border = Math.max(2, Math.round(2.5 * s));

    // Header
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, W, headerH);
    ctx.fillStyle = "#fff";
    setFont(ctx, Math.max(15, Math.round(18 * s)), "800");
    ctx.textBaseline = "middle";
    ctx.fillText("AI TOKEN", m, headerH / 2);
    const dateStr = (config.dateLabel && String(config.dateLabel).trim()) || defaultDateLabel();
    const dw = ctx.measureText(dateStr).width;
    ctx.fillText(dateStr, W - m - dw, headerH / 2);

    // TOTAL USED card
    const totalX0 = m;
    const totalY0 = headerH + gap;
    const totalX1 = W - m;
    const totalH = Math.max(72, Math.round(88 * s));
    const totalY1 = totalY0 + totalH;
    strokeRoundRect(ctx, totalX0, totalY0, totalX1 - totalX0, totalH, radius, border);

    setFont(ctx, Math.max(13, Math.round(15 * s)), "700");
    ctx.fillStyle = "#000";
    ctx.textBaseline = "top";
    ctx.fillText("TOTAL USED", totalX0 + Math.round(12 * s), totalY0 + Math.round(10 * s));

    const totalText = formatCompact(total);
    setFont(ctx, Math.max(40, Math.round(52 * s)), "900");
    ctx.textBaseline = "middle";
    ctx.textAlign = "center";
    const tcx = (totalX0 + totalX1) / 2;
    const tcy = totalY0 + totalH / 2 + Math.round(6 * s);
    ctx.fillText(totalText, tcx, tcy);

    // red underline under number
    const tw = ctx.measureText(totalText).width;
    const ulW = Math.max(28, Math.floor(tw * 0.28));
    const ulH = Math.max(3, Math.round(4 * s));
    const ulY = tcy + Math.max(18, Math.round(26 * s));
    ctx.fillStyle = RED;
    ctx.fillRect(tcx - ulW / 2, ulY, ulW, ulH);
    ctx.textAlign = "start";

    // 2×2 cards
    const gridTop = totalY1 + gap;
    const gridBot = H - m;
    const gridLeft = m;
    const gridW = W - m * 2;
    const gridH = gridBot - gridTop;
    const cellW = (gridW - gap) / 2;
    const cellH = (gridH - gap) / 2;

    const cells = [
      { p: providers[0], x: gridLeft, y: gridTop },
      { p: providers[1], x: gridLeft + cellW + gap, y: gridTop },
      { p: providers[2], x: gridLeft, y: gridTop + cellH + gap },
      { p: providers[3], x: gridLeft + cellW + gap, y: gridTop + cellH + gap },
    ];

    for (const { p, x, y } of cells) {
      drawProviderCard(ctx, x, y, cellW, cellH, p, s, border, radius);
    }
  },
};

function drawProviderCard(ctx, x, y, w, h, p, s, border, radius) {
  strokeRoundRect(ctx, x, y, w, h, radius, border);

  const pad = Math.max(8, Math.round(10 * s));
  const iconSize = Math.max(30, Math.round(38 * s));
  const barH = Math.max(8, Math.round(10 * s));
  const barY = y + h - pad - barH;
  const contentMidY = (y + barY) / 2;

  const img = iconCache.get(p.icon);
  let textLeft = x + pad;
  if (img && img.complete && img.naturalWidth > 0) {
    const iconY = contentMidY - iconSize / 2;
    ctx.save();
    ctx.imageSmoothingEnabled = true;
    ctx.drawImage(img, x + pad, iconY, iconSize, iconSize);
    ctx.restore();
    textLeft = x + pad + iconSize + Math.round(10 * s);
  }

  ctx.fillStyle = "#000";
  ctx.textBaseline = "middle";

  setFont(ctx, Math.max(13, Math.round(15 * s)), "700");
  const pct = `${p.pct}%`;
  const pctW = ctx.measureText(pct).width;
  ctx.fillText(pct, x + w - pad - pctW, contentMidY);

  setFont(ctx, Math.max(20, Math.round(26 * s)), "800");
  ctx.fillText(formatCompact(p.value), textLeft, contentMidY);

  // progress bar
  const barX0 = x + pad;
  const barW = w - pad * 2;
  strokeRoundRect(ctx, barX0, barY, barW, barH, Math.max(2, barH / 2), Math.max(1, border - 1));
  const fillW = Math.max(0, Math.floor((barW * Math.min(100, p.pct)) / 100));
  if (fillW > 2) {
    ctx.fillStyle = RED;
    const inset = 1;
    ctx.fillRect(barX0 + inset, barY + inset, Math.max(1, fillW - inset * 2), barH - inset * 2);
  }
}

function strokeRoundRect(ctx, x, y, w, h, r, line) {
  ctx.strokeStyle = "#000";
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

function setFont(ctx, sizePx, weight = "600") {
  ctx.font = `${weight} ${sizePx}px "Segoe UI", "Arial Black", "Arial", "Microsoft YaHei", sans-serif`;
}

function num(v) {
  const n = Number(String(v ?? "0").replace(/[,_\s]/g, ""));
  return Number.isFinite(n) ? n : 0;
}

function formatCompact(n) {
  n = Math.abs(Number(n) || 0);
  if (n >= 1e9) return trimNum(n / 1e9) + "B";
  if (n >= 1e6) return trimNum(n / 1e6) + "M";
  if (n >= 1e3) return trimNum(n / 1e3) + "K";
  return String(Math.round(n));
}

function trimNum(x) {
  const t = x >= 10 ? x.toFixed(1) : x.toFixed(2);
  return t.replace(/\.?0+$/, "");
}

function defaultDateLabel() {
  const d = new Date();
  return `${MONTHS[d.getMonth()]} ${d.getDate()}`;
}
