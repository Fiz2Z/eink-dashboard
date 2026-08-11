/**
 * AI Token usage dashboard — multi-provider card layout.
 * Brand icons: assets/icons/*.svg (Simple Icons / Lobe Icons style marks).
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
    // cache-bust only on first load path; keep stable for e-ink offline docker
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
    "多厂商 Token 看板（官方风格图标）：总额 + Codex/Claude/Grok/DeepSeek + 额度。红条需「三色」模式。",
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
    { key: "dateLabel", label: "日期（空=今天，如 AUG 11）", type: "text" },
    { key: "total", label: "TOTAL Token", type: "text" },
    { key: "limit", label: "LIMIT 上限", type: "text" },
    { key: "resetDays", label: "RESET 天数", type: "number" },
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
    const limit = Math.max(1, num(config.limit));
    const totalPct = Math.min(100, Math.round((total / limit) * 100));

    const providers = [
      { id: "codex", name: "CODEX", value: num(config.codex), icon: ICON_PATHS.codex },
      { id: "claude", name: "CLAUDE", value: num(config.claude), icon: ICON_PATHS.claude },
      { id: "grok", name: "GROK", value: num(config.grok), icon: ICON_PATHS.grok },
      { id: "deepseek", name: "DEEPSEEK", value: num(config.deepseek), icon: ICON_PATHS.deepseek },
    ];
    const sum = providers.reduce((a, p) => a + p.value, 0) || 1;
    providers.forEach((p) => {
      p.pct = Math.round((p.value / sum) * 100);
    });

    const m = Math.max(4, Math.round(6 * s));
    const headerH = Math.max(28, Math.round(36 * s));
    const footerH = Math.max(26, Math.round(32 * s));
    const gap = Math.max(4, Math.round(6 * s));
    const border = Math.max(2, Math.round(3 * s));

    // Header
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, W, headerH);
    ctx.fillStyle = "#fff";
    setFont(ctx, Math.max(14, Math.round(18 * s)), "800");
    ctx.textBaseline = "middle";
    ctx.fillText("AI TOKEN", m + 2, headerH / 2);
    const dateStr = (config.dateLabel && String(config.dateLabel).trim()) || defaultDateLabel();
    const dw = ctx.measureText(dateStr).width;
    ctx.fillText(dateStr, W - m - 2 - dw, headerH / 2);

    const bodyTop = headerH;
    const bodyBot = H - footerH;
    const bodyH = bodyBot - bodyTop;
    strokeRect(ctx, m, bodyTop + m, W - m * 2, bodyH - m * 2, border);

    // TOTAL card
    const totalY = bodyTop + m + gap;
    const totalH = Math.max(48, Math.round(62 * s));
    const totalX = m + gap;
    const totalW = W - m * 2 - gap * 2;
    strokeRect(ctx, totalX, totalY, totalW, totalH, border);

    setFont(ctx, Math.max(14, Math.round(18 * s)), "800");
    ctx.fillStyle = "#000";
    ctx.textBaseline = "middle";
    const ty = totalY + totalH / 2;
    ctx.fillText("TOTAL", totalX + Math.round(10 * s), ty);

    const totalText = formatCompact(total);
    setFont(ctx, Math.max(28, Math.round(40 * s)), "900");
    const badgeW = Math.max(52, Math.round(64 * s));
    const badgeH = Math.max(28, Math.round(36 * s));
    const badgeX = totalX + totalW - Math.round(8 * s) - badgeW;
    const badgeY = totalY + (totalH - badgeH) / 2;
    let numX = totalX + Math.round(10 * s) + Math.round(78 * s);
    if (numX + ctx.measureText(totalText).width > badgeX - 8) {
      setFont(ctx, Math.max(22, Math.round(32 * s)), "900");
    }
    ctx.fillStyle = "#000";
    ctx.fillText(totalText, numX, ty);

    roundFill(ctx, badgeX, badgeY, badgeW, badgeH, Math.round(6 * s), RED);
    ctx.fillStyle = "#fff";
    setFont(ctx, Math.max(16, Math.round(22 * s)), "800");
    const pctStr = `${totalPct}%`;
    const pw = ctx.measureText(pctStr).width;
    ctx.fillText(pctStr, badgeX + (badgeW - pw) / 2, badgeY + badgeH / 2);

    // 2×2 cards
    const gridTop = totalY + totalH + gap;
    const gridBot = bodyBot - m - gap;
    const gridLeft = totalX;
    const gridW = totalW;
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
      drawProviderCard(ctx, x, y, cellW, cellH, p, s, border);
    }

    // Footer
    const fy = H - footerH;
    strokeRect(ctx, m, fy, W - m * 2, footerH - m, border);
    setFont(ctx, Math.max(12, Math.round(15 * s)), "800");
    ctx.fillStyle = "#000";
    ctx.textBaseline = "middle";
    const fmid = fy + (footerH - m) / 2;
    ctx.fillText(`LIMIT  ${formatCompact(limit)}`, m + Math.round(10 * s), fmid);
    const reset = `RESET  ${Math.max(0, Math.floor(num(config.resetDays)))} DAYS`;
    const rw = ctx.measureText(reset).width;
    ctx.fillText(reset, W - m - Math.round(10 * s) - rw, fmid);
  },
};

function drawProviderCard(ctx, x, y, w, h, p, s, border) {
  strokeRect(ctx, x, y, w, h, border);

  const pad = Math.max(6, Math.round(8 * s));
  const iconSize = Math.max(22, Math.round(30 * s));
  const iconX = x + pad;
  const iconY = y + pad + Math.round(2 * s);

  const img = iconCache.get(p.icon);
  if (img && img.complete && img.naturalWidth > 0) {
    // Draw monochrome brand mark
    ctx.save();
    ctx.imageSmoothingEnabled = true;
    ctx.drawImage(img, iconX, iconY, iconSize, iconSize);
    ctx.restore();
  } else {
    // fallback box
    ctx.strokeStyle = "#000";
    ctx.lineWidth = 2;
    ctx.strokeRect(iconX, iconY, iconSize, iconSize);
  }

  const textX = iconX + iconSize + Math.round(8 * s);
  setFont(ctx, Math.max(13, Math.round(16 * s)), "800");
  ctx.fillStyle = "#000";
  ctx.textBaseline = "top";
  ctx.fillText(p.name, textX, y + pad);

  setFont(ctx, Math.max(16, Math.round(20 * s)), "800");
  ctx.fillText(formatCompact(p.value), textX, y + pad + Math.round(18 * s));

  setFont(ctx, Math.max(13, Math.round(16 * s)), "700");
  const pct = `${p.pct}%`;
  const pctW = ctx.measureText(pct).width;
  ctx.fillText(pct, x + w - pad - pctW, y + pad + Math.round(10 * s));

  const barX = x + pad;
  const barW = w - pad * 2;
  const barH = Math.max(8, Math.round(10 * s));
  const barY = y + h - pad - barH - 2;
  strokeRect(ctx, barX, barY, barW, barH, Math.max(1, Math.round(2 * s)));
  const fillW = Math.max(0, Math.floor((barW * Math.min(100, p.pct)) / 100));
  if (fillW > 0) {
    ctx.fillStyle = RED;
    const inset = Math.max(1, Math.round(1 * s));
    ctx.fillRect(barX + inset, barY + inset, Math.max(0, fillW - inset * 2), barH - inset * 2);
  }
}

function strokeRect(ctx, x, y, w, h, line) {
  ctx.strokeStyle = "#000";
  ctx.lineWidth = line;
  ctx.strokeRect(x + line / 2, y + line / 2, w - line, h - line);
}

function roundFill(ctx, x, y, w, h, r, color) {
  ctx.fillStyle = color;
  ctx.beginPath();
  const rr = Math.min(r, w / 2, h / 2);
  ctx.moveTo(x + rr, y);
  ctx.arcTo(x + w, y, x + w, y + h, rr);
  ctx.arcTo(x + w, y + h, x, y + h, rr);
  ctx.arcTo(x, y + h, x, y, rr);
  ctx.arcTo(x, y, x + w, y, rr);
  ctx.closePath();
  ctx.fill();
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
