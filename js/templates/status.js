import { clearWhite, drawFooter, drawHeader, fitText, setFont } from "./base.js";

/**
 * 通用状态板：标题 + 若干行 KV + 大数字
 */
export const statusTemplate = {
  id: "status",
  name: "状态看板",
  description: "通用模板：大标题、主数值、自定义多行文本（每行 key: value）。",
  defaults: {
    title: "System",
    headline: "OK",
    lines: "CPU: 12%\nRAM: 8.2 / 32 GB\nDisk: 412 GB free\nTasks: 3 running",
  },
  fields: [
    { key: "title", label: "标题", type: "text" },
    { key: "headline", label: "主状态 / 大字", type: "text" },
    { key: "lines", label: "明细（多行）", type: "textarea" },
  ],

  async render(ctx, canvas, config) {
    clearWhite(ctx, canvas);
    const contentTop = drawHeader(ctx, canvas, config.title || "Status");

    const pad = 16;
    let y = contentTop + 4;

    setFont(ctx, Math.max(36, Math.floor(canvas.width / 10)), "800");
    ctx.fillText(fitText(ctx, String(config.headline || ""), canvas.width - pad * 2), pad, y);
    y += Math.max(48, Math.floor(canvas.height / 5));

    setFont(ctx, Math.max(15, Math.floor(canvas.width / 26)), "500");
    const lines = String(config.lines || "")
      .split(/\r?\n/)
      .map((s) => s.trim())
      .filter(Boolean);

    const lineH = Math.max(24, Math.floor(canvas.height / 12));
    for (const line of lines) {
      if (y > canvas.height - 36) break;
      ctx.fillText(fitText(ctx, line, canvas.width - pad * 2), pad, y);
      y += lineH;
    }

    const now = new Date();
    drawFooter(
      ctx,
      canvas,
      `${now.getFullYear()}-${pad2(now.getMonth() + 1)}-${pad2(now.getDate())} ${pad2(now.getHours())}:${pad2(now.getMinutes())}`
    );
  },
};

function pad2(n) {
  return String(n).padStart(2, "0");
}
