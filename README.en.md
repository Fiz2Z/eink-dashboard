# eink-dashboard

[简体中文](./README.md) | English

A **Web Bluetooth host** for **EPD-nRF5-compatible** e-ink panels (e.g. [tsl0922/EPD-nRF5](https://github.com/tsl0922/EPD-nRF5)): switchable preset templates, canvas preview, and BLE image push.

> Device firmware remains EPD-nRF5 (or compatible). This repo ships only the **browser dashboard + Docker image** for self-hosting and extension.

[![Docker](https://img.shields.io/badge/ghcr.io-fiz2z%2Feink--dashboard-blue)](https://github.com/Fiz2Z/eink-dashboard/pkgs/container/eink-dashboard)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

---

## Features

- **Preset templates**: Token usage / status board / large-text note — switch from a dropdown
- **Per-template settings**: live form → preview
- **Resolution & color mode**: common sizes (e.g. 4.2″ 400×300); three-color mode clears the red plane (fewer red speckles)
- **Web Bluetooth push**: EPD-nRF5-compatible flow (`INIT` → `WRITE_IMG` → `REFRESH`)
- **Extensible**: add a JS template file to ship new layouts
- **Docker / GHCR**: multi-arch image builds on every push to `main`

---

## Quick start (Docker)

### Pull (after CI has published)

```bash
docker pull ghcr.io/fiz2z/eink-dashboard:latest
docker run --rm -p 8080:80 ghcr.io/fiz2z/eink-dashboard:latest
```

Open **http://localhost:8080**

> Web Bluetooth needs a secure context: `http://localhost` is fine. Remote IP access needs HTTPS you provide.

### Compose

```bash
git clone https://github.com/Fiz2Z/eink-dashboard.git
cd eink-dashboard
docker compose up -d --build
```

### Without Docker

```bash
python -m http.server 8080
```

Use **Chrome / Edge** at `http://localhost:8080`.

---

## Usage

1. Flash **EPD-nRF5** (or compatible) firmware; device name often looks like `NRF_EPD_xxxx`
2. Open the dashboard → pick a **template** → edit fields → **Refresh preview**
3. Match **resolution** to the panel (4.2″ often `400×300`)
4. For BWR panels prefer **three-color** mode (sends an all-white red plane)
5. **Connect** → select device → **Push**
6. Disconnect after refresh is normal (device sleep); reconnect for the next push

**Mobile**: Android Chrome works; iOS Safari does not support Web Bluetooth (try Bluefy).

---

## Adding a template

1. Create `js/templates/myboard.js` exporting a template object (`id`, `name`, `defaults`, `fields`, `render`).
2. Register it in `js/templates/index.js`.
3. Reload the page.

Prefer pure black/white, large type, thick lines.

---

## Image & CI

| | |
|--|--|
| Image | `ghcr.io/fiz2z/eink-dashboard` |
| Triggers | push to `main`/`master`, `v*` tags, manual dispatch |
| Platforms | `linux/amd64`, `linux/arm64` |
| Tags | `latest`, branch, `sha-…`, semver on tags |

Make the package **Public** under GitHub Packages if anonymous `docker pull` is desired.

---

## License

- **This repository (dashboard UI / Docker)**: **[MIT](./LICENSE)**
- **[EPD-nRF5](https://github.com/tsl0922/EPD-nRF5) firmware / original web tools**: **GPL-3.0**

This is an independent host for interoperability, **not** a fork of the firmware. See [NOTICE.md](./NOTICE.md).

MIT is chosen so the dashboard layer is easy to reuse; obligations around the GPL firmware itself are unchanged.

---

## Credits

- [tsl0922/EPD-nRF5](https://github.com/tsl0922/EPD-nRF5)
- [waveshareteam/e-Paper](https://github.com/waveshareteam/e-Paper)
- [ZinggJM/GxEPD2](https://github.com/ZinggJM/GxEPD2)

---

## Roadmap

- [ ] More presets (weather / todos / calendar)
- [ ] Data-source plugins
- [ ] Optional scheduled push helper
- [ ] Full RLE / dithering parity with the official web UI

Issues and PRs welcome.
