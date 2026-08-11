"""EPD-nRF5 BLE client (bleak), protocol-compatible with the web host."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Callable

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice

log = logging.getLogger("eink_push.ble")

EPD_SERVICE = "62750001-d828-918d-fb46-b6c11c675aec"
EPD_CHAR = "62750002-d828-918d-fb46-b6c11c675aec"
EPD_VERSION_CHAR = "62750003-d828-918d-fb46-b6c11c675aec"

CMD_INIT = 0x01
CMD_REFRESH = 0x05
CMD_WRITE_IMG = 0x30


def write_img_flag(is_first: bool, *, red: bool = False) -> int:
    # legacy non-RLE (official web UI)
    return (0x00 if red else 0x0F) | (0x00 if is_first else 0xF0)


class EpdBleClient:
    def __init__(self) -> None:
        self.mtu = 244
        self.rle_support = False
        self._client: BleakClient | None = None
        self._notify_count = 0

    async def scan(
        self,
        timeout: float = 10.0,
        name_prefix: str = "NRF_EPD",
    ) -> list[BLEDevice]:
        log.info("Scanning %.0fs for BLE devices…", timeout)
        devices = await BleakScanner.discover(timeout=timeout, return_adv=True)
        found: list[BLEDevice] = []
        for dev, adv in devices.values():
            name = dev.name or adv.local_name or ""
            line = f"  {dev.address}  RSSI={adv.rssi}  name={name!r}"
            if name_prefix and name_prefix.upper() in name.upper():
                log.info("★ %s", line)
                found.append(dev)
            else:
                log.info("  %s", line)
        return found

    async def connect(
        self,
        *,
        address: str | None = None,
        name_prefix: str = "NRF_EPD",
        timeout: float = 12.0,
        retries: int = 5,
    ) -> None:
        device = await self._resolve_device(address=address, name_prefix=name_prefix, timeout=timeout)
        last_err: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                log.info("Connect attempt %s/%s → %s (%s)", attempt, retries, device.name, device.address)
                client = BleakClient(device, timeout=30.0)
                await client.connect()
                await asyncio.sleep(0.35)
                if not client.is_connected:
                    raise RuntimeError("connected flag false after connect()")

                self._client = client
                self._notify_count = 0
                await client.start_notify(EPD_CHAR, self._on_notify)
                await asyncio.sleep(0.15)
                await self._write_cmd(CMD_INIT, with_response=True)
                await asyncio.sleep(0.45)
                log.info("Connected. MTU≈%s rle=%s", self.mtu, self.rle_support)
                return
            except Exception as e:
                last_err = e
                log.warning("Connect failed: %s", e)
                await self.disconnect()
                await asyncio.sleep(0.5 + attempt * 0.4)
        raise RuntimeError(f"无法连接设备: {last_err}")

    async def _resolve_device(
        self,
        *,
        address: str | None,
        name_prefix: str,
        timeout: float,
    ) -> BLEDevice:
        if address:
            log.info("Looking for address %s …", address)
            dev = await BleakScanner.find_device_by_address(address, timeout=timeout)
            if not dev:
                raise RuntimeError(f"未找到地址 {address}，设备是否在附近且已唤醒？")
            return dev

        log.info("Looking for name containing %r …", name_prefix)
        devices = await BleakScanner.discover(timeout=timeout, return_adv=True)
        matches: list[tuple[BLEDevice, int]] = []
        for dev, adv in devices.values():
            name = (dev.name or adv.local_name or "")
            if name_prefix.upper() in name.upper():
                matches.append((dev, adv.rssi or -999))
        if not matches:
            raise RuntimeError(
                f"未扫描到名称含 {name_prefix!r} 的设备。可先: python -m eink_push scan"
            )
        matches.sort(key=lambda x: x[1], reverse=True)
        dev, rssi = matches[0]
        log.info("Selected %s (%s) RSSI=%s", dev.name, dev.address, rssi)
        return dev

    def _on_notify(self, _handle: int, data: bytearray) -> None:
        idx = self._notify_count
        self._notify_count += 1
        if idx == 0:
            log.info("配置: %s", data.hex())
            return
        try:
            msg = data.decode("utf-8", errors="replace")
        except Exception:
            msg = data.hex()
        log.info("⇓ %s", msg)
        m = re.match(r"mtu=(\d+)", msg)
        if m:
            self.mtu = int(m.group(1))
            log.info("MTU → %s", self.mtu)
        if "rle=1" in msg:
            self.rle_support = True

    async def _write_cmd(
        self,
        cmd: int,
        payload: bytes = b"",
        *,
        with_response: bool = True,
    ) -> None:
        if not self._client or not self._client.is_connected:
            raise RuntimeError("未连接")
        data = bytes([cmd]) + payload
        max_len = max(20, self.mtu - 3)
        if len(data) > max_len:
            raise RuntimeError(f"单包过大 {len(data)} > {max_len}")
        await self._client.write_gatt_char(EPD_CHAR, data, response=with_response)

    async def _write_retry(
        self,
        cmd: int,
        payload: bytes = b"",
        *,
        with_response: bool = True,
        retries: int = 4,
    ) -> None:
        last: Exception | None = None
        use_resp = with_response
        for attempt in range(retries):
            try:
                await self._write_cmd(cmd, payload, with_response=use_resp)
                return
            except Exception as e:
                last = e
                use_resp = True
                await asyncio.sleep(0.03 + attempt * 0.04)
                log.warning("写包重试 %s/%s: %s", attempt + 1, retries, e)
        raise RuntimeError(f"写包失败: {last}")

    def _chunk_size(self) -> int:
        safe = min(self.mtu or 244, 185)
        return max(16, safe - 5)

    async def push_planes(
        self,
        bw: bytes,
        red: bytes | None = None,
        *,
        three_color: bool = True,
        interleaved: int = 0,
        chunk_delay: float = 0.004,
        on_progress: Callable[[int, int, str], None] | None = None,
    ) -> None:
        if three_color and red is None:
            red = bytes([0xFF] * len(bw))
        if red is not None and len(red) != len(bw):
            raise ValueError("bw/red 长度必须一致")

        chunk = self._chunk_size()
        log.info(
            "Push: %s bytes/plane, chunk=%s, three_color=%s, interleaved=%s",
            len(bw),
            chunk,
            three_color,
            interleaved,
        )
        await self._write_retry(CMD_INIT, with_response=True)
        await asyncio.sleep(0.2)

        await self._push_plane(
            bw,
            red=False,
            chunk=chunk,
            interleaved=interleaved,
            chunk_delay=chunk_delay,
            on_progress=on_progress,
        )
        if three_color and red is not None:
            await self._push_plane(
                red,
                red=True,
                chunk=chunk,
                interleaved=interleaved,
                chunk_delay=chunk_delay,
                on_progress=on_progress,
            )

        await asyncio.sleep(0.05)
        await self._write_retry(CMD_REFRESH, with_response=True)
        log.info("REFRESH sent — wait for panel update, then device may sleep.")

    async def _push_plane(
        self,
        plane: bytes,
        *,
        red: bool,
        chunk: int,
        interleaved: int,
        chunk_delay: float,
        on_progress: Callable[[int, int, str], None] | None,
    ) -> None:
        label = "red" if red else "bw"
        total = max(1, (len(plane) + chunk - 1) // chunk)
        no_reply = interleaved
        log.info("Plane %s: %s chunks", label, total)
        for i in range(total):
            piece = plane[i * chunk : (i + 1) * chunk]
            flag = write_img_flag(i == 0, red=red)
            body = bytes([flag]) + piece
            with_response = interleaved <= 0 or no_reply <= 0
            await self._write_retry(
                CMD_WRITE_IMG, body, with_response=with_response, retries=4
            )
            if with_response:
                no_reply = interleaved
            else:
                no_reply -= 1
            if chunk_delay > 0:
                await asyncio.sleep(chunk_delay)
            if on_progress and (i + 1 == total or (i + 1) % 5 == 0):
                on_progress(i + 1, total, label)

    async def disconnect(self) -> None:
        client = self._client
        self._client = None
        if not client:
            return
        try:
            if client.is_connected:
                try:
                    await client.stop_notify(EPD_CHAR)
                except Exception:
                    pass
                await client.disconnect()
        except Exception as e:
            log.debug("disconnect: %s", e)
