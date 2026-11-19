# YES-NK — 《胜利女神：新的希望》国服 PC 端自动化项目

仿照 **[YES-BD2](https://github.com/nobell001/YES-BD2)**（基于 `ok-script` 框架）的桌面分身工作方式与混合识别机制打造，借鉴 **[MaaNikke](https://github.com/Shinarin/MaaNikke)** 的国服日常业务流程，面向 **国服 PC 端（WeGame / `nikke.exe`）**，提供稳定可靠的**基础日常一条龙**自动化与 1080P 屏幕适配方案。

---

## 核心特性

1. **完全对齐 YES-BD2 的混合识别方案**
   - 静态图标使用 `ok-script` 标准 COCO 模板匹配（`find_one` / `assets/result.json`）；
   - 动态按钮与文字使用归一化局部区域 OCR（`box_of_screen` + RapidOCR），彻底规避大厅动态 Live2D 立绘、换装与弹窗干扰；
   - 全部核心操作内置大厅锚点校验（`ensure_in_lobby`）与安全护栏（商店与一举歼灭严禁误花珠宝/钻石）。
2. **与 YES-BD2 完全一致的桌面分身（独立窗口 · 最小化继续跑 · 不抢主桌面键鼠）**
   - 完整复刻 YES-BD2 的 **Windows 子会话（`WTSEnableChildSessions`）+ 独立 RDP 窗口 (`CloneDesktop.exe`)** 架构（需 Windows 10/11 专业版/企业版/教育版）；
   - 通过 `tools/clone_desktop/setup.ps1` 一次性编译生成分身窗口程序并开启子会话，分身内固定 `1920×1080` 画面且最小化后仍持续渲染（`RemoteDesktop_SuppressWhenMinimized = 2`），同时支持一键**还原桌面分身**（`-Undo`）；
   - 内置三档运行模式可切换：`桌面分身窗口模式（首选）`、`后台消息模式 (PostMessage · 家庭版可用)`、`前台兼容兜底模式`。
3. **1080P 显示器双轨无偏移适配**
   - **推荐 A（桌面分身内）**：在分身桌面中让游戏以 **`1920×1080` 无边框全屏** 运行，客户区 1:1 零缩放，完全不受任务栏挤压；
   - **推荐 B（1080P 主桌面窗口化）**：以 **`1600×900`** 或 **`1280×720`**（严格 16:9 客户区）运行，自动按比例缩放所有 ROI 与 COCO 模板，并主动启用 Per-Monitor DPI v2 感知。
4. **完整承接 Shinarin/MaaNikke 全部 22 条生产流水线（并已预置直接转换的 40 项 COCO 模板）**

> 本仓库已直接从 `Shinarin/MaaNikke` 提取并转换好 40 项 `1280×720` 基准 `ok-script` COCO 特征图（位于 `assets/images/` 与 `assets/result.json`，运行时自动按比例适配 `1920×1080` / `1600×900` / `1280×720`），剩余 4 项纯文字按钮由内置局部 ROI OCR 直接识别，**拉取即可开箱运行，无需手动重新转换**。

| 分类 | MaaNikke 原流水线 | YES-NK 原生任务模块 | 安全护栏与识别优化 |
| :--- | :--- | :--- | :--- |
| 启动与奖励 | 启动与登录奖励 | `AutoLoginTask` | 标题页 OCR 轮询 + 签到领取 + 登录公告清理 |
| 启动与奖励 | 邮件领取 | `MailTask` | 右上角 ROI 模板/OCR 双轨命中 + 全部领取 |
| 启动与奖励 | 每日/每周奖励 | `DailyMissionTask` | 活跃度宝箱 + 每周任务页签一键领取 |
| 启动与奖励 | PASS 奖励 | `PassRewardTask` | 通行证任务与奖励收取，自动跳过高级版推广弹窗 |
| 商店相关 | 付费商店免费礼包 | `CashShopFreeTask` | `is_safe_free_cash_shop_text()` 严禁点击任何 `￥/¥/元/珠宝` |
| 商店相关 | 道具商店每日购买 | `ShopTask` | `shop_guard` 严防钻石商品 + 免费刷新二次扫货 + 可选竞技场商店技能书 |
| 日常养成 | 前哨基地防御收菜 | `OutpostDefenseTask` | 领取防御奖励 + 强制校验弹窗含“免费”才执行一举歼灭 |
| 日常养成 | 派遣公告栏 | `DispatchTask` | 直达/二级双路径进入，一键收取并全部重派 |
| 日常养成 | 好友点数 | `FriendPointTask` | 一键赠送并收取友情点 |
| 日常养成 | 社交点招募 | `SocialRecruitTask` | `is_social_recruit_banner()` 强校验卡池标题，严防误抽珠宝池 |
| 日常养成 | 咨询与送礼 | `AdviseGiftTask` | 优先国服“快速咨询” + 可选好感送礼 |
| 日常养成 | 装备升级 | `EquipmentUpgradeTask` | 低阶素材日常 1 次强化（默认关闭按需开启） |
| 日常养成 | 同步器与循环室 | `LoopRoomAndSyncTask` | 前哨基地循环室研究 + 同步器升级（默认不消耗时间盒子道具） |
| 日常养成 | 更生馆 | `LiberationTask` | 收取解放任务点数，绝不耗钻刷新 |
| 副本挑战 | 拦截战 | `InterceptionTask` | 支持异常个体/特殊个体，优先“快速战斗”扫荡 |
| 副本挑战 | 模拟室 | `SimulationRoomTask` | 5-C 难度快速战斗 + 增益弹窗自动“不选择”快速结算 |
| 副本挑战 | 竞技场 | `ArenaTask` | 特殊竞技场收菜 + 新人竞技场强校验“免费”挑战指定顺位 |
| 副本挑战 | 无限之塔 | `TribeTowerTask` | 企业塔每日推进，支持识别“战斗失败”后立即停止 |
| 联盟与活动 | 协同作战 | `CoopOperationTask` | 开放期自动匹配准备与结算，非活动期安全跳过 |
| 联盟与活动 | 单人突击 | `SoloRaidTask` | 开放期每日快速战斗扫荡，非活动期安全跳过 |
| 联盟与活动 | 联盟突袭 (Beta) | `UnionRaidTask` | 联盟入口进入突袭消耗出刀次数（默认关闭） |
| 联盟与活动 | 大型活动刷取 | `EventStoryTask` | 活动签到/成就领取 + 指定关卡（如 1-11）消耗门票重复扫荡 |
| 后台守护 | 弹窗与断线处理 | `PopupGuardTrigger` | 后台低频巡检网络重连与突发活动/礼包弹窗 |

---

## Windows 桌面客户端（开箱即用 / 仿 YES-BD2 体验）

### 方式 A：双击脚本一键启动原生桌面客户端（源码用户推荐）

将仓库拉取到纯英文路径（例如 `D:\YES-NK`），直接双击：
- **`scripts\start_yes_nk.bat`**：首次自动创建 `.venv` 并安装依赖，弹出原生 PySide6 Fluent 桌面客户端（分组勾选全部 22 条日常流水线、YES-BD2 同款桌面分身 6 项自动检查与一键设定/启动/还原、一键校准 1080P 窗口为 `1600×900`、图形化导入 MaaNikke 图像与 Pipeline）。
- **`scripts\start_desktop_clone.bat`**：一键打开 YES-BD2 同款独立桌面分身窗口并自动在分身内运行日常。

### 方式 B：打包免安装 `YES-NK.exe` 或使用 GitHub Actions 自动构建

- **本地打包**：在 Windows 上双击 `scripts\build_windows_exe.bat`，将自动使用 `yes_nk.spec` 生成便携版 `dist\YES-NK\YES-NK.exe`。
- **云端自动打包（推荐）**：在 GitHub 仓库的 **Actions** 页签手动触发 `Build Windows Desktop Client (YES-NK.exe)`，或推送 `v*` 标签（如 `git tag v0.1.0 && git push --tags`），自动产出 `YES-NK-win64-portable.zip` 并在 Releases 发布。

### 方式 C：命令行开发调试

```bash
pip install -r requirements.txt

# 启动原生桌面客户端窗口
python desktop_launcher.py

# 第一次设定桌面分身（编译 CloneDesktop.exe 并开启 Windows 子会话）
python main.py --setup-clone

# 在与 YES-BD2 一致的独立桌面分身窗口中启动（不抢占主桌面键鼠）
python main.py --desktop-clone

# 结束桌面分身 / 还原系统设定
python main.py --end-clone
python main.py --undo-clone

# 直接在主桌面启动 ok-script 核心界面
python main.py

# 调试模式（输出详细 OCR / 模板匹配日志）
python main_debug.py

# 命令行导入 MaaNikke 模板素材并分析 Pipeline JSON 覆盖率
python tools/convert_maa_assets.py --maa-dir D:\MaaNikke\resource\base\image --maa-pipeline-dir D:\MaaNikke\resource\base\pipeline

# 校验 1080P 窗口客户区比例
python tools/check_env_1080p.py --width 1600 --height 900 --dpi 125
```

> 若从桌面客户端或 Web 配套工作台保存/导出了 `yes_nk_config.json` 并放在仓库根目录，`yes_nk/config.py` 与 `DailyTask` 启动时会自动读取覆盖全部 22 条任务开关、桌面分身与窗口设置。

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
