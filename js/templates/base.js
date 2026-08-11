/**
 * Template contract
 * -----------------
 * {
 *   id: string,
 *   name: string,
 *   description: string,
 *   // default config object (also defines form fields if fields[] provided)
 *   defaults: object,
 *   // optional: UI schema for config form
 *   fields: [{ key, label, type: 'text'|'number'|'textarea'|'url', placeholder? }],
 *   // optional async data loader — merge into config as `_data`
 *   loadData?: async (config) => any,
 *   // draw onto canvas (full size already set)
 *   render: (ctx, canvas, config) => void | Promise<void>
 * }
 */

/** Shared drawing helpers for templates */
export function clearWhite(ctx, canvas) {
  ctx.save();
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.restore();
}

export function setFont(ctx, sizePx, weight = "600") {
  // Prefer fonts that exist on Windows for CJK
  ctx.font = `${weight} ${sizePx}px "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif`;
  ctx.textBaseline = "top";
  ctx.fillStyle = "#000000";
  // Prefer hard edges on e-ink (still quantized later)
  if ("imageSmoothingEnabled" in ctx) ctx.imageSmoothingEnabled = false;
}

export function drawHeader(ctx, canvas, title, subtitle = "") {
  setFont(ctx, Math.max(18, Math.floor(canvas.width / 18)), "700");
  ctx.fillText(title, 16, 14);
  if (subtitle) {
    setFont(ctx, Math.max(12, Math.floor(canvas.width / 32)), "400");
    ctx.fillText(subtitle, 16, 14 + Math.max(22, Math.floor(canvas.width / 16)));
  }
  // divider
  const y = subtitle
    ? 14 + Math.max(22, Math.floor(canvas.width / 16)) + Math.max(16, Math.floor(canvas.width / 28))
    : 14 + Math.max(26, Math.floor(canvas.width / 14));
  ctx.fillRect(16, y, canvas.width - 32, 2);
  return y + 12;
}

export function drawFooter(ctx, canvas, text) {
  setFont(ctx, Math.max(11, Math.floor(canvas.width / 36)), "400");
  const metrics = ctx.measureText(text);
  ctx.fillText(text, canvas.width - 16 - metrics.width, canvas.height - 20);
}

export function fitText(ctx, text, maxWidth) {
  if (ctx.measureText(text).width <= maxWidth) return text;
  let t = text;
  while (t.length > 1 && ctx.measureText(t + "…").width > maxWidth) {
    t = t.slice(0, -1);
  }
  return t + "…";
}
