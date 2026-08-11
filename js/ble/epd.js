/**
 * EPD-nRF5 BLE protocol client (subset used for image push).
 * Compatible with tsl0922/EPD-nRF5 Web Bluetooth flow.
 */

export const EPD_SERVICE = "62750001-d828-918d-fb46-b6c11c675aec";
export const EPD_CHAR = "62750002-d828-918d-fb46-b6c11c675aec";
export const EPD_VERSION_CHAR = "62750003-d828-918d-fb46-b6c11c675aec";

export const EpdCmd = {
  INIT: 0x01,
  CLEAR: 0x02,
  REFRESH: 0x05,
  SLEEP: 0x06,
  SET_TIME: 0x20,
  WRITE_IMG: 0x30,
  SYS_SLEEP: 0x92,
};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export function imageDataToBwPacked(imageData, threshold = 128) {
  const { width, height, data } = imageData;
  const bytesPerRow = Math.ceil(width / 8);
  const out = new Uint8Array(bytesPerRow * height);
  let oi = 0;

  for (let y = 0; y < height; y++) {
    for (let xb = 0; xb < bytesPerRow; xb++) {
      let byte = 0;
      for (let bit = 0; bit < 8; bit++) {
        const x = xb * 8 + bit;
        if (x >= width) {
          byte = (byte << 1) | 1;
          continue;
        }
        const i = (y * width + x) * 4;
        const lum = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
        byte = (byte << 1) | (lum >= threshold ? 1 : 0);
      }
      out[oi++] = byte;
    }
  }
  return out;
}

export function canvasToBwPacked(canvas, threshold = 128) {
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  return imageDataToBwPacked(ctx.getImageData(0, 0, canvas.width, canvas.height), threshold);
}

/**
 * Force canvas pixels to pure black/white (kills gray anti-alias fringe that
 * becomes speckles / false red on 3-color panels).
 */
export function quantizeCanvasToBw(canvas, threshold = 160) {
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
  const d = imageData.data;
  for (let i = 0; i < d.length; i += 4) {
    const lum = 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2];
    const v = lum >= threshold ? 255 : 0;
    d[i] = d[i + 1] = d[i + 2] = v;
    d[i + 3] = 255;
  }
  ctx.putImageData(imageData, 0, 0);
  return imageData;
}

/** Official non-RLE flags: first 0x0F, rest 0xFF for BW */
function writeImgFlag(isFirst, { red = false, rle = false, rleMode = false } = {}) {
  if (rleMode) {
    let f = red ? 0x01 : 0x00;
    if (isFirst) f |= 0x02;
    if (rle) f |= 0x04;
    return f;
  }
  return (red ? 0x00 : 0x0f) | (isFirst ? 0x00 : 0xf0);
}

export class EpdBleClient {
  constructor({
    onLog = () => {},
    onMtu = () => {},
    onStatus = () => {},
    onDisconnected = () => {},
  } = {}) {
    this.onLog = onLog;
    this.onMtu = onMtu;
    this.onStatus = onStatus;
    this.onDisconnected = onDisconnected;
    this.device = null;
    this.server = null;
    this.characteristic = null;
    this.mtu = 244;
    this.rleSupport = false;
    this._msgIndex = 0;
    this._notifyHandler = null;
    this._disconnectHandler = null;
    this._intentionalDisconnect = false;
    this._connecting = false;
    this.lastPushAt = 0;
    this._readyAt = 0;
  }

  get connected() {
    return !!(this.server && this.server.connected && this.characteristic);
  }

  get deviceName() {
    return this.device?.name || "";
  }

  async connect() {
    if (!navigator.bluetooth) {
      throw new Error("当前浏览器不支持 Web Bluetooth，请用 Chrome / Edge");
    }

    this._connecting = true;
    this._intentionalDisconnect = false;

    try {
      this.onStatus("选择设备…");
      let device;
      try {
        device = await navigator.bluetooth.requestDevice({
          optionalServices: [EPD_SERVICE],
          // Prefer named ESL if browser supports filters + fallback
          acceptAllDevices: true,
        });
      } catch (e) {
        const msg = String(e.message || e);
        if (/cancel/i.test(msg)) {
          throw new Error("已取消选择设备（在弹窗里点了取消或关闭）");
        }
        throw e;
      }

      this.device = device;
      this._bindDisconnectHandler();

      // Soft reset any stale GATT link from a previous session
      await this._forceDisconnectGatt();
      await sleep(400);

      const maxAttempts = 5;
      let lastErr;

      for (let attempt = 1; attempt <= maxAttempts; attempt++) {
        this.onStatus(`连接中… (${attempt}/${maxAttempts})`);
        this.onLog(
          attempt === 1
            ? `正在连接: ${device.name || "(unnamed)"}`
            : `重试连接 ${attempt}/${maxAttempts}…`
        );

        try {
          await this._connectOnce(device);
          this._readyAt = Date.now();
          this.onStatus("已连接");
          this.onLog("连接成功");
          return;
        } catch (e) {
          lastErr = e;
          const msg = String(e.message || e);
          this.onLog(`连接尝试 ${attempt} 失败: ${msg}`);

          await this._forceDisconnectGatt();
          // Backoff — device may still be waking / advertising
          await sleep(500 + attempt * 400);
        }
      }

      throw new Error(
        this._friendlyConnectError(lastErr) +
          " 可尝试：靠近设备、按一下板子按键/唤醒、等 10 秒后再连，或关掉手机上已打开的上位机。"
      );
    } finally {
      this._connecting = false;
    }
  }

  async _connectOnce(device) {
    if (!device.gatt) {
      throw new Error("设备无 GATT 接口");
    }

    // connect() — may already be connected on some stacks
    let server;
    try {
      server = await device.gatt.connect();
    } catch (e) {
      // Sometimes "already connecting" — wait and retry once
      await sleep(300);
      server = await device.gatt.connect();
    }

    if (!server || !server.connected) {
      throw new Error("gatt.connect 后仍未连接");
    }

    // Critical on Windows: services not ready immediately; also link can drop in 50–200ms
    await sleep(350);

    if (!device.gatt.connected) {
      throw new Error("连接后立刻断开（设备可能在休眠/忙）");
    }

    this.server = server;

    let service;
    try {
      service = await server.getPrimaryService(EPD_SERVICE);
    } catch (e) {
      // One more wait + retry getPrimaryService (common Windows race)
      await sleep(400);
      if (!device.gatt.connected) {
        throw new Error("获取服务前连接已断开");
      }
      service = await server.getPrimaryService(EPD_SERVICE);
    }

    this.characteristic = await service.getCharacteristic(EPD_CHAR);

    try {
      const verChar = await service.getCharacteristic(EPD_VERSION_CHAR);
      const ver = await verChar.readValue();
      this.onLog(`固件协议版本字节: 0x${ver.getUint8(0).toString(16)}`);
    } catch {
      this.onLog("无法读取版本特征（可忽略）");
    }

    this._msgIndex = 0;
    this._notifyHandler = (event) => this._onNotify(event.target.value);
    await this.characteristic.startNotifications();
    this.characteristic.addEventListener("characteristicvaluechanged", this._notifyHandler);

    await sleep(100);
    await this.write(EpdCmd.INIT, null, true);
    await sleep(450); // allow config + mtu notify
  }

  _bindDisconnectHandler() {
    if (!this.device) return;
    if (this._disconnectHandler) {
      try {
        this.device.removeEventListener("gattserverdisconnected", this._disconnectHandler);
      } catch {
        /* ignore */
      }
    }
    this._disconnectHandler = () => this._handleDisconnect();
    this.device.addEventListener("gattserverdisconnected", this._disconnectHandler);
  }

  async _forceDisconnectGatt() {
    try {
      if (this.characteristic && this._notifyHandler) {
        try {
          this.characteristic.removeEventListener(
            "characteristicvaluechanged",
            this._notifyHandler
          );
        } catch {
          /* ignore */
        }
      }
    } catch {
      /* ignore */
    }
    this.characteristic = null;
    this.server = null;
    try {
      if (this.device?.gatt?.connected) {
        this.device.gatt.disconnect();
      }
    } catch {
      /* ignore */
    }
  }

  _friendlyConnectError(err) {
    const msg = String(err?.message || err || "未知错误");
    if (/disconnected|Cannot retrieve services|connect first/i.test(msg)) {
      return "GATT 连接不稳定，未能读取服务。";
    }
    return msg;
  }

  async disconnect() {
    this._intentionalDisconnect = true;
    await this._forceDisconnectGatt();
    this.onStatus("未连接");
    this.onLog("已手动断开");
  }

  _handleDisconnect() {
    // Ignore disconnect events while we are in a connect-retry loop
    if (this._connecting) {
      this.characteristic = null;
      this.server = null;
      return;
    }

    if (!this.server && !this.characteristic) return;

    const afterPush = this.lastPushAt > 0 && Date.now() - this.lastPushAt < 60_000;
    const intentional = this._intentionalDisconnect;

    this.characteristic = null;
    this.server = null;

    if (intentional) {
      this.onStatus("未连接");
      this.onDisconnected({ reason: "manual", afterPush: false });
      return;
    }

    if (afterPush) {
      this.onLog("蓝牙已断开：刷屏后设备休眠属正常。下次请重新连接。");
      this.onStatus("未连接（刷屏后休眠）");
      this.onDisconnected({ reason: "sleep_after_refresh", afterPush: true });
      return;
    }

    this.onLog("蓝牙已断开（链路中断）。可重新连接后再推送。");
    this.onStatus("未连接");
    this.onDisconnected({ reason: "lost", afterPush: false });
  }

  _onNotify(value) {
    const data = new Uint8Array(value.buffer, value.byteOffset, value.byteLength);
    const idx = this._msgIndex++;
    if (idx === 0) {
      this.onLog(
        `配置: ${[...data].map((b) => b.toString(16).padStart(2, "0")).join("")}`
      );
      return;
    }
    const msg = new TextDecoder().decode(data);
    this.onLog(`⇓ ${msg}`);
    if (msg.startsWith("mtu=") && msg.length > 4) {
      const mtuSize = parseInt(msg.substring(4), 10);
      if (!Number.isNaN(mtuSize) && mtuSize >= 23) {
        this.mtu = mtuSize;
        this.onMtu(mtuSize);
        this.onLog(`MTU 更新为 ${mtuSize}`);
      }
      if (msg.includes("rle=1")) {
        this.rleSupport = true;
        this.onLog("设备支持 RLE");
      }
    }
  }

  async write(cmd, data = null, withResponse = true) {
    if (!this.characteristic || !this.server?.connected) {
      throw new Error("未连接设备");
    }
    let payload;
    if (data == null) {
      payload = Uint8Array.of(cmd);
    } else if (data instanceof Uint8Array) {
      payload = new Uint8Array(1 + data.length);
      payload[0] = cmd;
      payload.set(data, 1);
    } else if (Array.isArray(data)) {
      payload = Uint8Array.of(cmd, ...data);
    } else {
      throw new Error("data 类型无效");
    }

    const maxLen = Math.max(20, (this.mtu || 244) - 3);
    if (payload.length > maxLen) {
      throw new Error(`单包过大 ${payload.length} > ${maxLen}（MTU=${this.mtu}）`);
    }

    if (withResponse) {
      await this.characteristic.writeValueWithResponse(payload);
    } else {
      await this.characteristic.writeValueWithoutResponse(payload);
    }
  }

  async writeRetry(cmd, data, withResponse, retries = 4) {
    let lastErr;
    for (let attempt = 0; attempt < retries; attempt++) {
      try {
        if (!this.connected) throw new Error("连接已断开");
        await this.write(cmd, data, withResponse);
        return;
      } catch (e) {
        lastErr = e;
        withResponse = true;
        await sleep(30 + attempt * 40);
        if (!this.connected) break;
        this.onLog(`写包重试 ${attempt + 1}/${retries}: ${e.message || e}`);
      }
    }
    throw lastErr || new Error("写包失败");
  }

  effectiveChunkSize(mtu = this.mtu) {
    const m = Number(mtu) || 244;
    const safe = Math.min(m, 185);
    return Math.max(16, safe - 5);
  }

  /**
   * Stream one plane (BW or red) via WRITE_IMG.
   * @param {'bw'|'red'} plane
   */
  async _pushPlane(packed, plane, opts) {
    const mtu = opts.mtu ?? this.mtu ?? 244;
    const interleaved = opts.interleaved ?? 0;
    const chunkDelayMs = opts.chunkDelayMs ?? 4;
    const onProgress = opts.onProgress ?? (() => {});
    const chunkSize = this.effectiveChunkSize(mtu);
    const useRleMode = this.rleSupport;
    const isRed = plane === "red";
    const total = Math.ceil(packed.length / chunkSize) || 1;
    let noReplyLeft = interleaved;
    const label = isRed ? "红通道" : "黑白通道";

    this.onLog(`${label}: ${packed.length}B, 分包 ${chunkSize}B × ${total}`);

    for (let i = 0; i < total; i++) {
      if (!this.connected) throw new Error("传输中途连接断开");

      const piece = packed.subarray(i * chunkSize, (i + 1) * chunkSize);
      const flag = writeImgFlag(i === 0, {
        red: isRed,
        rle: false,
        rleMode: useRleMode,
      });
      const body = new Uint8Array(1 + piece.length);
      body[0] = flag;
      body.set(piece, 1);

      const withResponse = interleaved <= 0 || noReplyLeft <= 0;
      await this.writeRetry(EpdCmd.WRITE_IMG, body, withResponse, 4);

      if (withResponse) noReplyLeft = interleaved;
      else noReplyLeft -= 1;

      if (chunkDelayMs > 0) await sleep(chunkDelayMs);
      onProgress(i + 1, total, plane);
    }
  }

  /**
   * Push image.
   * @param {Uint8Array} packedBw 1-bit BW plane (0=black, 1=white)
   * @param {{ colorMode?: 'bw'|'threeColor', mtu?: number, interleaved?: number, chunkDelayMs?: number, onProgress?: Function }} opts
   *
   * threeColor: also sends a full-white red plane (0xFF). Missing/dirty red plane
   * is the usual cause of "random red dots" on BWR panels.
   */
  async pushBwImage(packedBw, opts = {}) {
    const colorMode = opts.colorMode || "threeColor";
    const mtu = opts.mtu ?? this.mtu ?? 244;
    const interleaved = opts.interleaved ?? 0;

    const sinceReady = Date.now() - (this._readyAt || 0);
    if (sinceReady < 300) await sleep(300 - sinceReady);

    this.onLog(
      `传输参数: 模式=${colorMode}, MTU≈${mtu}, 交错无应答=${interleaved}, BW=${packedBw.length}B`
    );

    await this.writeRetry(EpdCmd.INIT, null, true);
    await sleep(200);

    // progress across 1 or 2 planes
    const planes = colorMode === "threeColor" ? 2 : 1;
    await this._pushPlane(packedBw, "bw", {
      ...opts,
      onProgress: (i, total) => {
        if (opts.onProgress) opts.onProgress(i, total * planes, "bw");
      },
    });

    if (colorMode === "threeColor") {
      // 0xFF = white on red plane → no red pixels
      const redWhite = new Uint8Array(packedBw.length).fill(0xff);
      await this._pushPlane(redWhite, "red", {
        ...opts,
        onProgress: (i, total) => {
          if (opts.onProgress) opts.onProgress(total + i, total * planes, "red");
        },
      });
    }

    await sleep(50);
    await this.writeRetry(EpdCmd.REFRESH, null, true);
    this.lastPushAt = Date.now();
  }
}
