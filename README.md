# eink-dashboard

[English](./README.en.md) | 简体中文

面向 **EPD-nRF5 兼容固件**（如 [tsl0922/EPD-nRF5](https://github.com/tsl0922/EPD-nRF5)）的 **Web Bluetooth 上位机**：预设模板切换、画布预览、蓝牙推送到墨水屏。

> 设备端固件仍使用 EPD-nRF5（或兼容固件）。本仓库只提供 **浏览器上位机 + Docker 镜像**，方便自建与二次开发。

[![Docker](https://img.shields.io/badge/ghcr.io-fiz2z%2Feink--dashboard-blue)](https://github.com/Fiz2Z/eink-dashboard/pkgs/container/eink-dashboard)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

---

## 功能

- **预设模板**：Token 看板 / 状态看板 / 大字便签，下拉切换
- **参数表单**：每个模板独立配置，改完即时预览
- **分辨率 & 颜色模式**：适配常见 4.2″ 等尺寸；三色模式可清红通道杂点
- **Web Bluetooth 推送**：协议兼容 EPD-nRF5（`INIT` → `WRITE_IMG` → `REFRESH`）
- **可扩展**：新增一个 JS 模板文件即可扩展业务画面
- **Docker / GHCR**：推送到 `main` 后自动构建多架构镜像

---

## 快速开始（Docker）

### 拉取镜像（CI 构建完成后）

```bash
docker pull ghcr.io/fiz2z/eink-dashboard:latest
docker run --rm -p 8080:80 ghcr.io/fiz2z/eink-dashboard:latest
```

浏览器打开：**http://localhost:8080**

> Web Bluetooth 要求安全上下文：`http://localhost` 可用。远程 IP 访问需自行配 HTTPS。

### 使用 Compose

```bash
git clone https://github.com/Fiz2Z/eink-dashboard.git
cd eink-dashboard
docker compose up -d --build
```

访问 http://localhost:8080

### 本地不装 Docker

```bash
# 在项目根目录
python -m http.server 8080
# 或 npx serve -l 8080
```

用 **Chrome / Edge** 打开 `http://localhost:8080`。

---

## 使用步骤

1. 墨水屏已刷 **EPD-nRF5**（或兼容）固件，蓝牙名类似 `NRF_EPD_xxxx`
2. 打开本上位机 → 选择 **模板** → 调整参数 → **刷新预览**
3. 分辨率与设备一致（4.2″ 常见 `400×300`）
4. 三色屏建议颜色模式选 **三色**（会额外推送全白红通道，减轻红点）
5. **连接蓝牙** → 选设备 → **推送到墨水屏**
6. 刷屏后设备休眠断开属正常，下次推送重新连接即可

**手机**：Android 用 Chrome；iOS 系统 Safari 不支持 Web Bluetooth，需 Bluefy 等。

---

## 新增模板

1. 新建 `js/templates/myboard.js`：

```js
import { clearWhite, drawHeader, setFont, drawFooter } from "./base.js";

export const myBoardTemplate = {
  id: "myboard",
  name: "我的看板",
  description: "一句话说明",
  defaults: { title: "Hello", value: "42" },
  fields: [
    { key: "title", label: "标题", type: "text" },
    { key: "value", label: "数值", type: "text" },
  ],
  async render(ctx, canvas, config) {
    clearWhite(ctx, canvas);
    drawHeader(ctx, canvas, config.title);
    setFont(ctx, 48, "800");
    ctx.fillText(String(config.value), 16, 80);
    drawFooter(ctx, canvas, "myboard");
  },
};
```

2. 在 `js/templates/index.js` 中 `import` 并加入 `templates` 数组。  
3. 刷新页面即可切换。

绘图建议：纯黑 `#000` / 纯白 `#fff`，大字粗线，少用灰阶。

---

## 项目结构

```text
eink-dashboard/
  index.html
  css/app.css
  js/
    app.js                 # 模板切换、预览、推送
    ble/epd.js             # EPD-nRF5 兼容 BLE 客户端
    templates/             # 预设模板（在此扩展）
  docker/nginx.conf
  Dockerfile
  docker-compose.yml
  .github/workflows/docker-publish.yml
  README.md / README.en.md
  LICENSE / NOTICE.md
```

---

## 镜像与 CI

| 项 | 说明 |
|----|------|
| 镜像 | `ghcr.io/fiz2z/eink-dashboard` |
| 触发 | 推送到 `main` / `master`、打 `v*` 标签、手动 `workflow_dispatch` |
| 架构 | `linux/amd64`、`linux/arm64` |
| 标签 | `latest`、分支名、`sha-xxxx`、semver（打 tag 时） |

首次使用 GHCR 私有/公开包：仓库 **Settings → Actions → General** 确保 Actions 可写 packages；公开仓库一般无需额外 token（使用 `GITHUB_TOKEN`）。

若包默认 private，可在 GitHub Packages 页面设为 Public，便于 `docker pull`。

---

## 协议 License

- **本项目（上位机 UI / Docker）**：**[MIT](./LICENSE)**
- **设备固件 [EPD-nRF5](https://github.com/tsl0922/EPD-nRF5)**：GPL-3.0（使用其固件/原版上位机源码时请遵守 GPL）

本仓库为独立实现的 Web 上位机，协议兼容 EPD-nRF5，**不是**固件仓库的 fork。详见 [NOTICE.md](./NOTICE.md)。

选用 MIT 的原因：本仓库代码为自研静态页与 BLE 客户端封装，便于二次开发与闭源集成 UI 层；固件侧义务不因 MIT 而改变。

---

## 致谢 / 参考

- [tsl0922/EPD-nRF5](https://github.com/tsl0922/EPD-nRF5) — nRF 墨水屏固件与官方 Web Bluetooth 上位机  
- [waveshareteam/e-Paper](https://github.com/waveshareteam/e-Paper)  
- [ZinggJM/GxEPD2](https://github.com/ZinggJM/GxEPD2)

---

## 路线图（后续迭代）

- [ ] 更多预设模板（天气 / 待办 / 日历摘要）
- [ ] 数据源插件（HTTP API / 本地文件）
- [ ] 可选定时推送旁路（宿主机脚本 + BLE）
- [ ] 官方 dithering / RLE 完整对齐

欢迎 Issue / PR。
