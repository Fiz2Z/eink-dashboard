import {
  EpdBleClient,
  canvasToBwPacked,
  canvasToBwRedPlanes,
  quantizeCanvasToBw,
  quantizeCanvasBwRed,
} from "./ble/epd.js";
import { templates, getTemplate } from "./templates/index.js";

const $ = (id) => document.getElementById(id);

const els = {
  templateSelect: $("templateSelect"),
  templateDesc: $("templateDesc"),
  canvasSize: $("canvasSize"),
  colorMode: $("colorMode"),
  configForm: $("configForm"),
  canvas: $("canvas"),
  previewMeta: $("previewMeta"),
  btnPreview: $("btnPreview"),
  btnConnect: $("btnConnect"),
  btnPush: $("btnPush"),
  bleStatus: $("bleStatus"),
  log: $("log"),
  mtuSize: $("mtuSize"),
  interleaved: $("interleaved"),
  showAllBle: $("showAllBle"),
  namePrefixes: $("namePrefixes"),
};

/** @type {Record<string, object>} */
const configStore = {};

const log = (msg) => {
  const t = new Date().toLocaleTimeString();
  els.log.textContent = `[${t}] ${msg}\n` + els.log.textContent;
};

const setBleStatus = (text, cls = "") => {
  els.bleStatus.textContent = text;
  els.bleStatus.className = "ble-status" + (cls ? ` ${cls}` : "");
};

function syncConnectUi() {
  const ok = client.connected;
  els.btnConnect.textContent = ok ? "断开" : "连接蓝牙";
  els.btnPush.disabled = !ok;
}

const client = new EpdBleClient({
  onLog: log,
  onStatus: (s) => {
    let cls = "";
    if (s.includes("已连接") && !s.includes("未")) cls = "ok";
    else if (s.includes("…") || s.includes("推送") || s.includes("传输")) cls = "busy";
    setBleStatus(s, cls);
  },
  onMtu: (mtu) => {
    els.mtuSize.value = String(mtu);
  },
  onDisconnected: () => {
    syncConnectUi();
  },
});

function parseSize(value) {
  const [w, h] = value.split("x").map(Number);
  return { width: w, height: h };
}

function currentTemplateId() {
  return els.templateSelect.value || templates[0].id;
}

function getConfig(id = currentTemplateId()) {
  const tpl = getTemplate(id);
  if (!configStore[id]) {
    configStore[id] = { ...tpl.defaults };
  }
  return configStore[id];
}

function buildTemplateSelect() {
  els.templateSelect.innerHTML = "";
  for (const t of templates) {
    const opt = document.createElement("option");
    opt.value = t.id;
    opt.textContent = t.name;
    els.templateSelect.appendChild(opt);
  }
}

function buildConfigForm() {
  const tpl = getTemplate(currentTemplateId());
  const cfg = getConfig(tpl.id);
  els.templateDesc.textContent = tpl.description || "";
  els.configForm.innerHTML = "";

  const fields = tpl.fields?.length
    ? tpl.fields
    : Object.keys(tpl.defaults || {}).map((key) => ({
        key,
        label: key,
        type: "text",
      }));

  for (const f of fields) {
    const label = document.createElement("label");
    label.className = "field";
    const span = document.createElement("span");
    span.textContent = f.label || f.key;
    label.appendChild(span);

    let input;
    if (f.type === "textarea") {
      input = document.createElement("textarea");
    } else {
      input = document.createElement("input");
      input.type = f.type === "number" ? "number" : f.type === "url" ? "url" : "text";
    }
    input.dataset.key = f.key;
    input.value = cfg[f.key] ?? "";
    if (f.placeholder) input.placeholder = f.placeholder;
    input.addEventListener("change", () => {
      cfg[f.key] = input.value;
      renderPreview().catch((e) => log(String(e.message || e)));
    });
    input.addEventListener("input", () => {
      cfg[f.key] = input.value;
    });
    label.appendChild(input);
    els.configForm.appendChild(label);
  }
}

function applyCanvasSize() {
  const { width, height } = parseSize(els.canvasSize.value);
  els.canvas.width = width;
  els.canvas.height = height;
  els.previewMeta.textContent = `${width} × ${height}`;
}

async function renderPreview() {
  applyCanvasSize();
  const tpl = getTemplate(currentTemplateId());
  const cfg = { ...getConfig(tpl.id) };

  if (typeof tpl.loadData === "function") {
    try {
      cfg._data = await tpl.loadData(cfg);
    } catch (e) {
      log(`loadData 失败: ${e.message || e}`);
    }
  }

  const ctx = els.canvas.getContext("2d");
  // Avoid gray anti-alias fringes that become speckles on EPD
  ctx.imageSmoothingEnabled = false;
  ctx.save();
  ctx.fillStyle = "#fff";
  ctx.fillRect(0, 0, els.canvas.width, els.canvas.height);
  ctx.restore();

  await tpl.render(ctx, els.canvas, cfg);
  const colorMode = els.colorMode?.value || "threeColor";
  if (colorMode === "threeColor") {
    // Keep intentional red; snap gray AA to B/W/R
    quantizeCanvasBwRed(els.canvas);
  } else {
    quantizeCanvasToBw(els.canvas, 160);
  }
  log(`预览: ${tpl.name}`);
}

async function onConnect() {
  if (client.connected) {
    await client.disconnect();
    syncConnectUi();
    return;
  }
  try {
    els.btnConnect.disabled = true;
    els.btnPush.disabled = true;
    setBleStatus("连接中…", "busy");
    const prefixes = String(els.namePrefixes?.value || "NRF_EPD,EPD")
      .split(/[,，\s]+/)
      .map((s) => s.trim())
      .filter(Boolean);
    await client.connect({
      showAllDevices: !!els.showAllBle?.checked,
      namePrefixes: prefixes,
      preferRemembered: true,
    });
    if (client.deviceName) {
      log(`已连接: ${client.deviceName}`);
    }
    syncConnectUi();
  } catch (e) {
    log(`连接失败: ${e.message || e}`);
    setBleStatus("未连接");
    syncConnectUi();
  } finally {
    els.btnConnect.disabled = false;
    syncConnectUi();
  }
}

async function onPush() {
  if (!client.connected) {
    log("请先连接设备");
    return;
  }
  try {
    els.btnPush.disabled = true;
    els.btnConnect.disabled = true;
    setBleStatus("推送中…", "busy");
    await renderPreview();
    const colorMode = els.colorMode?.value || "threeColor";
    let packed;
    let packedRed = null;
    if (colorMode === "threeColor") {
      const planes = canvasToBwRedPlanes(els.canvas);
      packed = planes.bw;
      packedRed = planes.red;
    } else {
      packed = canvasToBwPacked(els.canvas, 160);
    }
    log(`位图 ${packed.length} bytes，模式=${colorMode}，开始传输…`);
    const t0 = performance.now();
    const interleaved = Number(els.interleaved.value);
    await client.pushBwImage(packed, {
      colorMode,
      packedRed,
      mtu: Number(els.mtuSize.value) || client.mtu || 244,
      interleaved: Number.isFinite(interleaved) ? interleaved : 0,
      chunkDelayMs: 4,
      onProgress: (i, total) => {
        if (i === total || i % 5 === 0) {
          setBleStatus(`传输 ${i}/${total}`, "busy");
        }
      },
    });
    const sec = ((performance.now() - t0) / 1000).toFixed(1);
    log(`推送完成，耗时 ${sec}s。请等待屏幕刷新结束。`);
    log("提示：刷屏完成后设备常会自动断开蓝牙休眠，这是正常的。");
    if (client.connected) {
      setBleStatus("已连接（即将可能休眠）", "ok");
    }
  } catch (e) {
    log(`推送失败: ${e.message || e}`);
    if (/GATT|disconnect|断开/i.test(String(e.message || e))) {
      log("建议：等 2 秒 → 重新「连接蓝牙」→ 再推送。高级设置里「交错无应答」保持 0 更稳。");
    }
    setBleStatus(client.connected ? "已连接" : "未连接", client.connected ? "ok" : "");
  } finally {
    els.btnConnect.disabled = false;
    syncConnectUi();
  }
}

function bind() {
  buildTemplateSelect();
  buildConfigForm();
  applyCanvasSize();

  els.templateSelect.addEventListener("change", () => {
    buildConfigForm();
    renderPreview().catch((e) => log(String(e.message || e)));
  });
  els.canvasSize.addEventListener("change", () => {
    renderPreview().catch((e) => log(String(e.message || e)));
  });
  els.btnPreview.addEventListener("click", () => {
    els.configForm.querySelectorAll("[data-key]").forEach((el) => {
      getConfig()[el.dataset.key] = el.value;
    });
    renderPreview().catch((e) => log(String(e.message || e)));
  });
  els.btnConnect.addEventListener("click", onConnect);
  els.btnPush.addEventListener("click", onPush);

  renderPreview().catch((e) => log(String(e.message || e)));
  log("就绪。请用 Chrome/Edge 打开（localhost）。");
  log("说明：设备名类似 NRF_EPD_xxxx；传图成功后蓝牙断开多为固件休眠，重新连接即可再推。");
}

bind();
