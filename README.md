# YES-NK — 《胜利女神：新的希望》国服 PC 端自动化项目

仿照 **[YES-BD2](https://github.com/nobell001/YES-BD2)**（基于 `ok-script` 框架）的桌面分身工作方式与混合识别机制打造，借鉴 **[MaaNikke](https://github.com/Shinarin/MaaNikke)** 的国服日常业务流程，面向 **国服 PC 端（WeGame / `nikke.exe`）**，提供稳定可靠的**基础日常一条龙**自动化与 1080P 屏幕适配方案。

---

## 核心特性

1. **完全对齐 YES-BD2 的混合识别方案**
   - 静态图标使用 `ok-script` 标准 COCO 模板匹配（`find_one` / `assets/result.json`）；
   - 动态按钮与文字使用归一化局部区域 OCR（`box_of_screen` + RapidOCR），彻底规避大厅动态 Live2D 立绘、换装与弹窗干扰；
   - 全部核心操作内置大厅锚点校验（`ensure_in_lobby`）与安全护栏（商店与一举歼灭严禁误花珠宝/钻石）。
2. **仿 YES-BD2 桌面分身（不抢主桌面键鼠）**
   - 基于 Win32 `CreateDesktopW` / `SwitchDesktop` 隔离桌面会话运行，挂机清日常的同时不影响主桌面正常办公与娱乐；
   - 内置三档运行模式可切换：`桌面分身模式（首选）`、`后台消息模式 (PostMessage)`、`前台兼容兜底模式`。
3. **1080P 显示器双轨无偏移适配**
   - **推荐 A（桌面分身内）**：在分身桌面中让游戏以 **`1920×1080` 无边框全屏** 运行，客户区 1:1 零缩放，完全不受任务栏挤压；
   - **推荐 B（1080P 主桌面窗口化）**：以 **`1600×900`** 或 **`1280×720`**（严格 16:9 客户区）运行，自动按比例缩放所有 ROI 与 COCO 模板，并主动启用 Per-Monitor DPI v2 感知。
4. **基础日常一条龙 (`DailyTask`)**
   - 大厅初始化与公告/签到/礼包弹窗清理
   - 邮箱一键领取 (`MailTask`)
   - 好友友情点互赠 (`FriendPointTask`)
   - 前哨基地防御收菜 + 每日免费一举歼灭 (`OutpostDefenseTask`)
   - 公告栏派遣一键收取与重新派遣 (`DispatchTask`)
   - 普通商店免费商品购买 + 免费刷新二次扫货 (`ShopTask`)
   - 每日/每周任务活跃度奖励一键领取 (`DailyMissionTask`)
   - 后台弹窗与网络波动断线重连守护 (`PopupGuardTrigger`)

---

## Windows 本地运行（Python `ok-script` 桌面端）

### 1. 安装依赖（建议使用纯英文路径，如 `D:\YES-NK`，Python 3.11+）

```bash
pip install -r requirements.txt
```

### 2. 导入 MaaNikke 模板素材（可选，缺失项自动启用 ROI OCR 兜底）

如果你本地已有 `Shinarin/MaaNikke` 仓库，可一键将其模板转换为 `ok-script` 所需的 COCO 特征包：

```bash
python tools/convert_maa_assets.py --maa-dir D:\MaaNikke\resource\base\image
```

### 3. 启动 YES-NK

```bash
# 常规启动（支持后台 PostMessage 或前台模式）
python main.py

# 仿 YES-BD2 在独立桌面分身中启动（不抢占主桌面键鼠）
python main.py --desktop-clone

# 调试模式（输出详细 OCR / 模板匹配日志）
python main_debug.py

# 校验 1080P 窗口客户区比例
python tools/check_env_1080p.py --width 1600 --height 900 --dpi 125
```

> 若从 Web 配套工作台导出了 `yes_nk_config.json`，直接放在仓库根目录，`yes_nk/config.py` 启动时会自动读取覆盖桌面分身与窗口设置。

---

## Web 配套配置与流程工作台

本仓库同时内置基于 Vite + React 的 **YES-NK Fluent 控制与配置工作台**，可在浏览器中直观编排日常子任务顺序、配置桌面分身与 1080P 适配参数、检索 COCO 特征映射并一键导出 `yes_nk_config.json`：

```bash
npm install
npm run dev
```

## 运行自动化单测

```bash
# Python 核心状态机、1080P 校验、桌面分身、商店安全护栏与 Maa 转换器单测
python3 -m unittest discover -s tests -v

# TypeScript Web 工作台纯逻辑单测
npx --yes tsx --test src/utils/workbenchLogic.test.ts
```
