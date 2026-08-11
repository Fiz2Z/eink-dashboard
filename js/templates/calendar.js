/**
 * 中国公历月历模板：法定节假日（休）+ 调休上班（班）
 * 布局参考常见墨水屏月历：顶栏年月/干支、周一至日、底栏图例。
 * 节假日数据见 js/data/cn-holidays.js（国办通知）。
 */

import {
  getHolidayIndex,
  cnMonthName,
  ymd,
  holidaysInMonth,
  supportedHolidayYears,
} from "../holidays/cn-holidays.js";

const RED = "#E60000";
const WEEK = ["一", "二", "三", "四", "五", "六", "日"];

export const calendarTemplate = {
  id: "calendar",
  name: "中国月历",
  description:
    "公历月历，标注国务院法定节假日（休）与调休上班（班）。默认当前月；数据含 2026 年国办安排。",
  defaults: {
    year: "", // empty = this year
    month: "", // empty = this month 1-12
  },
  fields: [
    {
      key: "year",
      label: `年份（空=今年；已收录 ${supportedHolidayYears().join("、")}）`,
      type: "number",
    },
    { key: "month", label: "月份 1–12（空=本月）", type: "number" },
  ],

  async render(ctx, canvas, config) {
    const now = new Date();
    let year = parseInt(String(config.year || "").trim(), 10);
    let month = parseInt(String(config.month || "").trim(), 10);
    if (!Number.isFinite(year) || year < 2000) year = now.getFullYear();
    if (!Number.isFinite(month) || month < 1 || month > 12) {
      month = now.getMonth() + 1;
    }

    const W = canvas.width;
    const H = canvas.height;
    const s = Math.min(W / 400, H / 300);

    ctx.imageSmoothingEnabled = false;
    ctx.fillStyle = "#fff";
    ctx.fillRect(0, 0, W, H);

    const idx = getHolidayIndex(year);
    const daysInMonth = new Date(year, month, 0).getDate();
    // Monday=0 … Sunday=6
    let startDow = new Date(year, month - 1, 1).getDay();
    startDow = startDow === 0 ? 6 : startDow - 1;

    const m = Math.max(3, Math.round(5 * s));
    const headerH = Math.max(30, Math.round(38 * s));
    const footerH = Math.max(28, Math.round(34 * s));
    const weekH = Math.max(18, Math.round(22 * s));
    const border = Math.max(2, Math.round(2.5 * s));

    // —— Header ——
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, W, headerH);
    ctx.fillStyle = "#fff";
    setFont(ctx, Math.max(16, Math.round(22 * s)), "800");
    ctx.textBaseline = "middle";
    const title = `${year} ${cnMonthName(month)}`;
    ctx.fillText(title, m + 4, headerH / 2);
    if (idx.ganZhi) {
      setFont(ctx, Math.max(13, Math.round(16 * s)), "700");
      const gw = ctx.measureText(idx.ganZhi).width;
      ctx.fillText(idx.ganZhi, W - m - 4 - gw, headerH / 2);
    }

    // —— Weekday row ——
    const gridTop = headerH;
    const gridBot = H - footerH;
    const gridLeft = 0;
    const gridW = W;
    const colW = gridW / 7;
    const bodyTop = gridTop + weekH;
    const bodyH = gridBot - bodyTop;
    const rows = 6;
    const rowH = bodyH / rows;

    // weekday header band
    ctx.strokeStyle = "#000";
    ctx.lineWidth = border;
    ctx.beginPath();
    ctx.moveTo(0, gridTop + weekH);
    ctx.lineTo(W, gridTop + weekH);
    ctx.stroke();

    setFont(ctx, Math.max(12, Math.round(14 * s)), "700");
    ctx.fillStyle = "#000";
    ctx.textBaseline = "middle";
    ctx.textAlign = "center";
    for (let i = 0; i < 7; i++) {
      const cx = colW * i + colW / 2;
      // weekend header in red
      ctx.fillStyle = i >= 5 ? RED : "#000";
      ctx.fillText(WEEK[i], cx, gridTop + weekH / 2);
    }
    ctx.textAlign = "start";

    // grid lines
    ctx.strokeStyle = "#000";
    ctx.lineWidth = Math.max(1, Math.round(1.5 * s));
    for (let c = 0; c <= 7; c++) {
      const x = Math.round(colW * c) + 0.5;
      ctx.beginPath();
      ctx.moveTo(x, bodyTop);
      ctx.lineTo(x, gridBot);
      ctx.stroke();
    }
    for (let r = 0; r <= rows; r++) {
      const y = Math.round(bodyTop + rowH * r) + 0.5;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(W, y);
      ctx.stroke();
    }

    // —— Days ——
    for (let day = 1; day <= daysInMonth; day++) {
      const cell = startDow + day - 1;
      const r = Math.floor(cell / 7);
      const c = cell % 7;
      if (r >= rows) break;

      const x0 = colW * c;
      const y0 = bodyTop + rowH * r;
      const key = ymd(year, month, day);
      const isRest = idx.rest.has(key);
      const isWork = idx.work.has(key);
      const dow = c; // 0=Mon … 6=Sun
      const isWeekend = dow >= 5;
      // red date: holiday rest, or weekend that is not makeup work
      const dateRed = isRest || (isWeekend && !isWork);
      const label = idx.labels[key] || "";

      // day number
      const numSize = Math.max(16, Math.round(22 * s));
      setFont(ctx, numSize, "800");
      ctx.fillStyle = dateRed ? RED : "#000";
      ctx.textBaseline = "top";
      ctx.textAlign = "left";
      const numX = x0 + Math.round(4 * s);
      const numY = y0 + Math.round(3 * s);
      ctx.fillText(String(day), numX, numY);

      // 休 / 班 badge top-right
      const badge = isRest ? "休" : isWork ? "班" : "";
      if (badge) {
        const bs = Math.max(10, Math.round(12 * s));
        setFont(ctx, bs, "800");
        const tw = ctx.measureText(badge).width;
        const padX = Math.round(2 * s);
        const padY = Math.round(1 * s);
        const bx = x0 + colW - tw - padX * 2 - Math.round(3 * s);
        const by = y0 + Math.round(3 * s);
        const bw = tw + padX * 2;
        const bh = bs + padY * 2;
        if (isRest) {
          ctx.fillStyle = RED;
          roundRect(ctx, bx, by, bw, bh, Math.round(2 * s));
          ctx.fill();
          ctx.fillStyle = "#fff";
        } else {
          ctx.fillStyle = "#000";
          roundRect(ctx, bx, by, bw, bh, Math.round(2 * s));
          ctx.fill();
          ctx.fillStyle = "#fff";
        }
        ctx.textBaseline = "middle";
        ctx.fillText(badge, bx + padX, by + bh / 2);
      }

      // holiday name under number
      if (label) {
        setFont(ctx, Math.max(9, Math.round(10 * s)), "600");
        ctx.fillStyle = RED;
        ctx.textBaseline = "top";
        ctx.textAlign = "left";
        ctx.fillText(label, numX, numY + numSize + Math.round(1 * s));
      }

      // red underline for continuous rest span (bottom of cell)
      if (isRest) {
        ctx.fillStyle = RED;
        const uh = Math.max(2, Math.round(3 * s));
        ctx.fillRect(x0 + 1, y0 + rowH - uh - 1, colW - 2, uh);
      }
    }

    // —— Footer legend ——
    const fy = H - footerH;
    ctx.strokeStyle = "#000";
    ctx.lineWidth = border;
    ctx.beginPath();
    ctx.moveTo(0, fy);
    ctx.lineTo(W, fy);
    ctx.stroke();

    const fmid = fy + footerH / 2;
    const legendSize = Math.max(10, Math.round(11 * s));
    setFont(ctx, legendSize, "700");
    ctx.textBaseline = "middle";

    let lx = m + 2;
    // 休 badge
    drawMiniBadge(ctx, lx, fmid, "休", RED, legendSize, s);
    lx += Math.round(18 * s);
    ctx.fillStyle = "#000";
    ctx.fillText("法定节假日", lx, fmid);
    lx += ctx.measureText("法定节假日").width + Math.round(12 * s);

    drawMiniBadge(ctx, lx, fmid, "班", "#000", legendSize, s);
    lx += Math.round(18 * s);
    ctx.fillStyle = "#000";
    ctx.fillText("调休上班", lx, fmid);

    // month holiday summary (right)
    const monthHols = holidaysInMonth(year, month);
    let summary = "";
    if (monthHols.length === 1) {
      const h = monthHols[0];
      summary = `${h.name}假期 ${h.days} 天`;
    } else if (monthHols.length > 1) {
      summary = monthHols.map((h) => `${h.name}${h.days}天`).join(" · ");
    } else if (!idx.blocks.length) {
      summary = `${year} 节假日数据未收录`;
    }
    if (summary) {
      setFont(ctx, legendSize, "700");
      ctx.fillStyle = RED;
      const sw = ctx.measureText(summary).width;
      ctx.fillText(summary, W - m - 2 - sw, fmid);
    }

    ctx.textAlign = "start";
  },
};

function setFont(ctx, sizePx, weight = "600") {
  ctx.font = `${weight} ${sizePx}px "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif`;
}

function roundRect(ctx, x, y, w, h, r) {
  const rr = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + rr, y);
  ctx.arcTo(x + w, y, x + w, y + h, rr);
  ctx.arcTo(x + w, y + h, x, y + h, rr);
  ctx.arcTo(x, y + h, x, y, rr);
  ctx.arcTo(x, y, x + w, y, rr);
  ctx.closePath();
}

function drawMiniBadge(ctx, x, y, text, bg, fontSize, s) {
  setFont(ctx, fontSize, "800");
  const tw = ctx.measureText(text).width;
  const padX = Math.round(2 * s);
  const padY = Math.round(1 * s);
  const bw = tw + padX * 2;
  const bh = fontSize + padY * 2;
  const bx = x;
  const by = y - bh / 2;
  ctx.fillStyle = bg;
  roundRect(ctx, bx, by, bw, bh, Math.round(2 * s));
  ctx.fill();
  ctx.fillStyle = "#fff";
  ctx.textBaseline = "middle";
  ctx.fillText(text, bx + padX, y);
}
