# Notices

## This project

**eink-dashboard** is original web UI code released under the **MIT License**.

It is a **host / dashboard** for pushing images over Web Bluetooth. It is **not** a fork of the device firmware.

## Protocol reference

Bluetooth service UUIDs, command opcodes (`INIT` / `WRITE_IMG` / `REFRESH`, etc.) and the image transfer flow are **compatible with** the open-source firmware project:

- **[tsl0922/EPD-nRF5](https://github.com/tsl0922/EPD-nRF5)**  
  E-paper display firmware for Nordic nRF51/nRF52, with image transfer and OTA.  
  Firmware and official web tools are licensed under **GPL-3.0**.

Our `js/ble/epd.js` client is an independent reimplementation of the documented Web Bluetooth behaviour for interoperability.  
If you use or redistribute **EPD-nRF5 firmware or its original web sources**, you must comply with **GPL-3.0**.

## Other references (ecosystem)

- [waveshareteam/e-Paper](https://github.com/waveshareteam/e-Paper) — e-paper driver examples  
- [ZinggJM/GxEPD2](https://github.com/ZinggJM/GxEPD2) — Arduino e-paper library (used upstream by many EPD projects)

## Holiday data

`js/data/cn-holidays.js` encodes PRC public holiday / makeup-work schedules from
State Council General Office notices (e.g. 国办发明电〔2025〕7号 for year 2026),
as republished on government portals such as
[beijing.gov.cn](https://www.beijing.gov.cn/cs/gncs/zcwj/202603/t20260327_4568275.html).
Official texts remain authoritative; this file is a convenience for offline e-ink rendering.

## Brand icons

Monochrome SVG marks under `assets/icons/` are sourced from public icon collections
([Simple Icons](https://simpleicons.org/), [Lobe Icons](https://github.com/lobehub/lobe-icons)) for identification only.
OpenAI, Anthropic, Claude, xAI, Grok, DeepSeek and related marks are trademarks of their respective owners.
This project is unofficial and not affiliated with those companies.

## Trademark / product note

“E-ink / 墨水屏” product names remain with their respective owners. This repository is unofficial community software.
