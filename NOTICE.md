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

## Trademark / product note

“E-ink / 墨水屏” product names remain with their respective owners. This repository is unofficial community software.
