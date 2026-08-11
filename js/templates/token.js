import { clearWhite, drawFooter, drawHeader, setFont } from "./base.js";

/**
 * AI Token 用量看板（数据可手填；也可把 loadData 换成你的接口）
 */
export const tokenTemplate = {
  id: "token",
  name: "AI Token 用量",
  description: "展示今日/本月 Token；参数可手改。以后可在 loadData 里接真实 API。",
  defaults: {
    title: "AI Token",
    todayIn: "120000",
    todayOut: "45000",
    monthIn: "3200000",
    monthOut: "890000",
    quotaPct: "78",
    note: "",
  },
  fields: [
    { key: "title", label: "标题", type: "text" },
    { key: "todayIn", label: "今日 Input", type: "text" },
    { key: "todayOut", label: "今日 Output", type: "text" },
    { key: "monthIn", label: "本月 Input", type: "text" },
    { key: "monthOut", label: "本月 Output", type: "text" },
    { key: "quotaPct", label: "额度使用 %", type: "number" },
    { key: "note", label: "备注", type: "text" },
  ],

  async render(ctx, canvas, config) {
    clearWhite(ctx, canvas);
    const contentTop = drawHeader(ctx, canvas, config.title || "AI Token", "Usage dashboard");

    const pad = 16;
    const lineH = Math.max(28, Math.floor(canvas.height / 10));
    let y = contentTop + 8;

    const rows = [
      ["Today  in", formatNum(config.todayIn)],
      ["Today out", formatNum(config.todayOut)],
      ["Month  in", formatNum(config.monthIn)],
      ["Month out", formatNum(config.monthOut)],
    ];

    setFont(ctx, Math.max(16, Math.floor(canvas.width / 24)), "600");
    for (const [k, v] of rows) {
      ctx.fillText(k, pad, y);
      const tw = ctx.measureText(v).width;
      ctx.fillText(v, canvas.width - pad - tw, y);
      y += lineH;
    }

    // progress bar
    y += 6;
    const pct = Math.min(100, Math.max(0, Number(config.quotaPct) || 0));
    const barW = canvas.width - pad * 2;
    const barH = Math.max(14, Math.floor(canvas.height / 18));
    ctx.strokeStyle = "#000";
    ctx.lineWidth = 2;
    ctx.strokeRect(pad, y, barW, barH);
    ctx.fillRect(pad, y, Math.floor((barW * pct) / 100), barH);

    y += barH + 10;
    setFont(ctx, Math.max(13, Math.floor(canvas.width / 28)), "500");
    ctx.fillText(`Quota  ${pct}%`, pad, y);

    if (config.note) {
      y += lineH * 0.85;
      ctx.fillText(String(config.note), pad, y);
    }

    const now = new Date();
    const stamp = `${pad2(now.getMonth() + 1)}-${pad2(now.getDate())} ${pad2(now.getHours())}:${pad2(now.getMinutes())}`;
    drawFooter(ctx, canvas, `updated ${stamp}`);
  },
};

function formatNum(v) {
  const n = Number(String(v).replace(/,/g, ""));
  if (Number.isFinite(n)) return n.toLocaleString("en-US");
  return String(v ?? "");
}

function pad2(n) {
  return String(n).padStart(2, "0");
}
