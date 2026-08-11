# Python 推送工具（bleak + Pillow）

在电脑后台把画面推到 **EPD-nRF5** 兼容墨水屏，协议与 Web 上位机一致。

## 安装

```bash
cd python
python -m venv .venv

# Windows
.venv\Scripts\activate
pip install -r requirements.txt
```

## 快速开始

### 1. 扫描设备

```bash
python -m eink_push scan
```

记下 `NRF_EPD_xxxx` 的地址（Windows 上可能是 UUID 形态）。

### 2. 只出预览图（不连蓝牙）

```bash
python -m eink_push preview --source demo --out preview.png
```

### 3. 推送到墨水屏（演示数据）

先唤醒设备，靠近电脑：

```bash
python -m eink_push push --source demo --name-prefix NRF_EPD
```

或写配置：

```bash
copy config.example.yaml config.yaml
# 编辑 address / api 等
python -m eink_push -c config.yaml push
```

### 4. 从 API 拉用量再推

`config.yaml`：

```yaml
source: api
api:
  url: "https://your.api/token-usage"
  headers:
    Authorization: "Bearer xxx"
```

接口 JSON 示例：

```json
{
  "total": 2480000,
  "limit": 3500000,
  "reset_days": 20,
  "codex": 986000,
  "claude": 742000,
  "grok": 496000,
  "deepseek": 256000
}
```

```bash
python -m eink_push -c config.yaml push --source api
```

### 5. 推本地任意图

```bash
python -m eink_push push --source image --image my.png --width 400 --height 300
```

## 每小时自动跑（Windows 任务计划）

1. 确认手动 `push` 成功  
2. 任务计划程序 → 创建基本任务 → 每小时  
3. 操作：

```text
程序: C:\path\to\python\ .venv\Scripts\python.exe
参数: -m eink_push -c C:\path\to\config.yaml push
起始于: C:\path\to\eink-dashboard\python
```

或：

```powershell
schtasks /Create /TN "EinkTokenPush" `
  /TR "C:\path\to\.venv\Scripts\python.exe -m eink_push -c C:\path\to\config.yaml push" `
  /SC HOURLY /ST 09:00
```

电脑需开机、蓝牙可用；设备在附近。刷完断开属正常。

## 命令一览

| 命令 | 作用 |
|------|------|
| `scan` | 扫描 BLE |
| `preview` | 只渲染 PNG |
| `push` | 渲染 + 传图 |

## 注意

- 需 **Windows 蓝牙**（或本机适配器）；Docker 容器默认无主机蓝牙  
- 首次建议 `--source demo` 验证链路  
- 三色屏用 `color_mode: threeColor`（默认）  
- 日志里出现刷屏后断开是正常现象  

## 协议参考

[tsl0922/EPD-nRF5](https://github.com/tsl0922/EPD-nRF5) · 与本仓库 `js/ble/epd.js` 对齐。
