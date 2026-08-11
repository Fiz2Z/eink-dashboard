import { clearWhite, drawFooter, setFont } from "./base.js";

/**
 * 大字文本 / 便签 / 一句话
 */
export const quoteTemplate = {
  id: "quote",
  name: "大字便签",
  description: "适合一句提醒、待办、金句。自动按宽度换行。",
  defaults: {
    text: "先完成最重要的一件事。",
    author: "",
  },
  fields: [
    { key: "text", label: "正文", type: "textarea" },
    { key: "author", label: "署名（可选）", type: "text" },
  ],

  async render(ctx, canvas, config) {
    clearWhite(ctx, canvas);
    const pad = Math.max(18, Math.floor(canvas.width * 0.06));
    const maxW = canvas.width - pad * 2;
    const text = String(config.text || "").trim() || "…";

    // pick font size by length
    let size = Math.min(42, Math.floor(canvas.width / 9));
    if (text.length > 40) size = Math.floor(size * 0.75);
    if (text.length > 80) size = Math.floor(size * 0.75);

    setFont(ctx, size, "700");
    const lines = wrapText(ctx, text, maxW);
    const lineH = Math.floor(size * 1.35);
    const blockH = lines.length * lineH;
    let y = Math.max(pad, Math.floor((canvas.height - blockH) / 2) - 10);

    for (const line of lines) {
      const w = ctx.measureText(line).width;
      ctx.fillText(line, Math.floor((canvas.width - w) / 2), y);
      y += lineH;
    }

    if (config.author) {
      setFont(ctx, Math.max(14, Math.floor(size * 0.45)), "400");
      const a = `— ${config.author}`;
      const w = ctx.measureText(a).width;
      ctx.fillText(a, canvas.width - pad - w, canvas.height - pad - 8);
    } else {
      drawFooter(ctx, canvas, "note");
    }
  },
};

function wrapText(ctx, text, maxWidth) {
  const chars = [...text];
  const lines = [];
  let line = "";
  for (const ch of chars) {
    const trial = line + ch;
    if (ctx.measureText(trial).width > maxWidth && line) {
      lines.push(line);
      line = ch;
    } else {
      line = trial;
    }
  }
  if (line) lines.push(line);
  return lines;
}
