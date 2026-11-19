import { useState } from 'react';
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Copy,
  Monitor,
  ShieldCheck,
} from 'lucide-react';
import { DesktopCloneSettings, RunMode } from '../types';
import {
  buildLaunchCommand,
  evaluateClientGeometry,
  resolveInteractionBackend,
  sanitizeDesktopName,
} from '../utils/workbenchLogic';

interface DesktopClonePanelProps {
  desktopClone: DesktopCloneSettings;
  onChange: (next: DesktopCloneSettings) => void;
  onApplyResolution: (res: '1920x1080' | '1600x900' | '1280x720') => void;
}

const PC_CHECK_ROWS: {
  label: string;
  text: string;
  tone: 'ok' | 'warn';
  note?: string;
}[] = [
  {
    label: 'Windows',
    text: 'Windows 10/11 专业版、企业版或教育版可用（家庭版不含子会话）',
    tone: 'ok',
  },
  {
    label: '第一次设定',
    text: '桌面客户端点击「第一次设定」自动编译 CloneDesktop.exe 并开启 WTSEnableChildSessions',
    tone: 'warn',
    note: 'setup.ps1',
  },
  {
    label: '远程桌面服务',
    text: '依赖系统 TermService（若被优化工具停用，桌面端可一键「帮我打开」）',
    tone: 'ok',
  },
  {
    label: '登录账户',
    text: '支持微软账户与本地账户，凭据仅保存于本机 Windows 凭据管理器',
    tone: 'ok',
  },
  {
    label: '要打的密码',
    text: '微软账户密码或本地账户密码（注意：不是开机 PIN，也不是人脸）',
    tone: 'ok',
  },
  {
    label: 'Windows Hello',
    text: '如开启了「仅允许 Windows Hello 登录」，桌面端支持一键「帮我关掉」',
    tone: 'ok',
  },
];

const FIRST_USE_STEPS = [
  '首页按「在桌面分身跑」（或先按「第一次设定」）',
  'Windows 管理员确认按「是」',
  '打上面写的账户密码（非 PIN），勾「记住」',
];

const TROUBLESHOOT_QA: { q: string; steps: string[] }[] = [
  {
    q: '提示「登录失败」',
    steps: [
      '密码打上面「要打的密码」那组，不是 PIN。',
      '平常只用 PIN 或人脸开机：按 Win+L 锁屏，选钥匙图标，用账户密码登录电脑一次。',
      '再按一次桌面端首页的「在桌面分身跑」。',
    ],
  },
  {
    q: '提示「连不上桌面分身」（代码 516 等）',
    steps: [
      '关掉工具，重新打开再按一次。',
      '重启电脑后再试（刚开启子会话时 Windows 常需要重启一次生效）。',
      '装过系统精简工具或 RDP Wrapper 的电脑可能无法使用子会话。',
    ],
  },
  {
    q: '提示「分身程序不见了」',
    steps: [
      '在防毒软件（如 360、火绒）中将 %LOCALAPPDATA%\\yes-nk\\clone-desktop 设为信任。',
      '在桌面端「桌面分身」页点击「第一次设定」重新编译 CloneDesktop.exe。',
    ],
  },
  {
    q: '首页无法启动「在桌面分身跑」',
    steps: [
      'Windows 子会话桌面分身要求专业版 / 企业版 / 教育版，家庭版不支持。',
      '家庭版请直接使用「后台窗口消息模式 (PostMessage)」运行。',
    ],
  },
  {
    q: '账户没有设密码',
    steps: [
      '没有密码的账户进不了子会话（Windows 系统安全规定）。',
      '到 Windows「设置 > 账户 > 登录选项」先为当前账户添加一组密码。',
    ],
  },
  {
    q: '还是不行怎么排查',
    steps: [
      '在桌面客户端点击「打开分身文件夹」，查看 viewer.log 与 launch-result.txt。',
      '若需彻底清理，点击「还原桌面分身」或运行 setup.ps1 -Undo 即可无痕还原。',
    ],
  },
];

const RUN_MODE_CARDS: {
  mode: RunMode;
  title: string;
  subtitle: string;
  detail: string;
}[] = [
  {
    mode: 'desktop_clone',
    title: '桌面分身模式（YES-BD2 同款）',
    subtitle: 'Windows 子会话 (Child Session) + CloneDesktop.exe',
    detail:
      '在主桌面打开 1360×820 独立窗口（内部固定 1920×1080），最小化照跑且不抢鼠标键盘。',
  },
  {
    mode: 'background_post_message',
    title: '后台窗口消息模式',
    subtitle: 'PostMessage + WGC/BitBlt 后台截图',
    detail: '家庭版首选：向未最小化的 nikke.exe 后台发送窗口消息，无需开启子会话。',
  },
  {
    mode: 'foreground_compat',
    title: '前台兼容兜底模式',
    subtitle: 'Pynput 标准输入 · 最高兼容',
    detail: '针对 WeGame / ACE 严格权限环境下的兜底执行方案，保持游戏窗口置前运行。',
  },
];

const GEOMETRY_PRESETS: {
  label: string;
  width: number;
  height: number;
  dpi: number;
  note: string;
}[] = [
  { label: '分身 1080P 无边框', width: 1920, height: 1080, dpi: 100, note: '1:1 最佳' },
  { label: '主桌面窗口 (900p)', width: 1600, height: 900, dpi: 125, note: '16:9 缩放' },
  { label: '主桌面小窗 (720p)', width: 1280, height: 720, dpi: 100, note: '最低合规' },
  { label: '任务栏挤压异常示例', width: 1920, height: 1009, dpi: 100, note: '需校准' },
];

export default function DesktopClonePanel({
  desktopClone,
  onChange,
  onApplyResolution,
}: DesktopClonePanelProps) {
  const [copiedKey, setCopiedKey] = useState<'launch' | 'setup' | null>(null);
  const [openQaIndex, setOpenQaIndex] = useState<number | null>(0);

  const verdict = evaluateClientGeometry(
    desktopClone.clientWidth,
    desktopClone.clientHeight,
    desktopClone.dpiScalePercent
  );
  const launchCmd = buildLaunchCommand(desktopClone);
  const setupCmd = 'powershell -ExecutionPolicy Bypass -File tools\\clone_desktop\\setup.ps1';
  const sanitizedName = sanitizeDesktopName(desktopClone.desktop_name);
  const interactionBackend = resolveInteractionBackend(desktopClone.run_mode);

  const handleCopy = async (text: string, key: 'launch' | 'setup') => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedKey(key);
      window.setTimeout(() => setCopiedKey(null), 1800);
    } catch {
      setCopiedKey(null);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      {/* Header matching YES-BD2 CloneGuidePage */}
      <header className="space-y-0.5">
        <h1 className="text-[23px] font-bold text-[var(--yes-ink)] tracking-tight">桌面分身</h1>
        <p className="text-[13px] text-[var(--yes-ink2)]">
          边跑边用电脑；Windows 子会话 (Child Session) + CloneDesktop.exe 独立窗口，进不去就照这页做
        </p>
      </header>

      {/* 1. 这台电脑（自动检查） */}
      <section className="space-y-2.5" aria-label="本机子会话检查清单">
        <h2 className="text-[15px] font-semibold text-[var(--yes-ink)] px-1">
          这台电脑（Windows 桌面端自动检查项）
        </h2>
        <div className="yes-card px-5 py-3.5 divide-y divide-[var(--yes-line)]">
          {PC_CHECK_ROWS.map((row) => (
            <div
              key={row.label}
              className="py-2.5 flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3"
            >
              <div className="flex items-center gap-2.5 sm:w-36 shrink-0">
                {row.tone === 'ok' ? (
                  <CheckCircle2 className="w-4 h-4 text-[var(--yes-ok)] shrink-0" />
                ) : (
                  <AlertTriangle className="w-4 h-4 text-[var(--yes-warn)] shrink-0" />
                )}
                <span className="text-xs text-[var(--yes-ink3)]">{row.label}</span>
              </div>
              <div className="text-[13px] text-[var(--yes-ink)] flex-1">{row.text}</div>
              {row.note && (
                <button
                  type="button"
                  onClick={() => handleCopy(setupCmd, 'setup')}
                  className="inline-flex items-center gap-1 h-7 px-3 rounded-full text-xs bg-[var(--yes-primary)] hover:bg-[var(--yes-primary-hover)] text-white transition-colors cursor-pointer whitespace-nowrap self-start sm:self-auto"
                >
                  {copiedKey === 'setup' ? (
                    <>
                      <Check className="w-3 h-3" />
                      已复制设定命令
                    </>
                  ) : (
                    <>
                      <Copy className="w-3 h-3" />
                      复制首次设定
                    </>
                  )}
                </button>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* 2. 第一次怎么用（3 步圆形编号卡片） */}
      <section className="space-y-2.5" aria-label="第一次使用步骤">
        <h2 className="text-[15px] font-semibold text-[var(--yes-ink)] px-1">第一次怎么用</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {FIRST_USE_STEPS.map((step, idx) => (
            <div key={step} className="yes-card p-4 flex items-start gap-3">
              <span className="w-7 h-7 rounded-full bg-[var(--yes-accent-soft)] text-[var(--yes-ghost-ink)] text-xs font-bold font-mono flex items-center justify-center shrink-0">
                {idx + 1}
              </span>
              <p className="text-[14px] text-[var(--yes-ink)] leading-snug">{step}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 3. 遇到问题（点开看做法） */}
      <section className="space-y-2.5" aria-label="桌面分身常见问题">
        <h2 className="text-[15px] font-semibold text-[var(--yes-ink)] px-1">
          遇到问题（点开看做法）
        </h2>
        <div className="yes-card px-5 py-2.5 divide-y divide-[var(--yes-line)]">
          {TROUBLESHOOT_QA.map((item, idx) => {
            const expanded = openQaIndex === idx;
            return (
              <div key={item.q} className="py-2">
                <button
                  type="button"
                  aria-expanded={expanded}
                  onClick={() => setOpenQaIndex(expanded ? null : idx)}
                  className="w-full py-1.5 flex items-center gap-2 text-left text-[14px] text-[var(--yes-ink)] hover:text-[var(--yes-primary)] transition-colors cursor-pointer"
                >
                  {expanded ? (
                    <ChevronDown className="w-4 h-4 text-[var(--yes-ink3)] shrink-0" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-[var(--yes-ink3)] shrink-0" />
                  )}
                  <span>{item.q}</span>
                </button>
                {expanded && (
                  <ol className="mt-1.5 mb-2 ml-6 p-3 rounded-[14px] bg-[var(--yes-inset)] space-y-1.5 text-[13px] text-[var(--yes-ink2)]">
                    {item.steps.map((line, i) => (
                      <li key={line}>
                        {i + 1}. {line}
                      </li>
                    ))}
                  </ol>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* 4. 运行模式与 1080P 窗口适配 */}
      <section className="space-y-3" aria-label="运行模式与1080P窗口适配">
        <h2 className="text-[15px] font-semibold text-[var(--yes-ink)] px-1">
          运行模式与 1080P 客户区校准
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {RUN_MODE_CARDS.map((card) => {
            const active = desktopClone.run_mode === card.mode;
            return (
              <button
                key={card.mode}
                type="button"
                onClick={() => onChange({ ...desktopClone, run_mode: card.mode })}
                className={`yes-card p-4 text-left transition-all cursor-pointer border-2 ${
                  active
                    ? 'border-[var(--yes-primary)]'
                    : 'border-transparent hover:border-[var(--yes-line2)]'
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[14px] font-semibold text-[var(--yes-ink)]">
                    {card.title}
                  </span>
                  {active && (
                    <span className="text-xs font-medium text-[var(--yes-primary)] shrink-0">
                      已选定
                    </span>
                  )}
                </div>
                <div className="mt-1 text-xs font-mono text-[var(--yes-ink3)]">{card.subtitle}</div>
                <p className="mt-2 text-xs text-[var(--yes-ink2)] leading-relaxed">{card.detail}</p>
              </button>
            );
          })}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
          {/* Left: Session params */}
          <div className="lg:col-span-5 yes-card p-5 space-y-4">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-[15px] font-semibold text-[var(--yes-ink)]">分身会话参数</h3>
              <span className="text-xs font-mono text-[var(--yes-ink3)]">{interactionBackend}</span>
            </div>

            <div className="space-y-3 text-sm">
              <div className="space-y-1">
                <label htmlFor="clone-desktop-name" className="text-xs text-[var(--yes-ink3)]">
                  会话标识（清洗后：{sanitizedName}）
                </label>
                <input
                  id="clone-desktop-name"
                  type="text"
                  value={desktopClone.desktop_name}
                  onChange={(e) => onChange({ ...desktopClone, desktop_name: e.target.value })}
                  className="w-full h-9 px-3 text-xs font-mono rounded-xl bg-[var(--yes-inset)] text-[var(--yes-ink)] border border-[var(--yes-line2)]"
                />
              </div>

              <label className="flex items-center justify-between gap-3 py-1 cursor-pointer">
                <span className="text-[13px] text-[var(--yes-ink)]">
                  分身内固定 1920×1080 无边框全屏
                </span>
                <input
                  type="checkbox"
                  checked={desktopClone.prefer_borderless_1080p}
                  onChange={(e) =>
                    onChange({ ...desktopClone, prefer_borderless_1080p: e.target.checked })
                  }
                  className="w-4 h-4 accent-[var(--yes-primary)]"
                />
              </label>

              <label className="flex items-center justify-between gap-3 py-1 cursor-pointer">
                <span className="text-[13px] text-[var(--yes-ink)]">
                  退出程序时自动注销分身子会话
                </span>
                <input
                  type="checkbox"
                  checked={desktopClone.auto_close_desktop_on_exit}
                  onChange={(e) =>
                    onChange({ ...desktopClone, auto_close_desktop_on_exit: e.target.checked })
                  }
                  className="w-4 h-4 accent-[var(--yes-primary)]"
                />
              </label>
            </div>

            <div className="pt-3 border-t border-[var(--yes-line)] space-y-1.5">
              <div className="text-xs text-[var(--yes-ink3)]">Windows 命令行启动</div>
              <div className="flex items-center justify-between gap-2 px-3 py-2 rounded-xl bg-[var(--yes-inset)]">
                <code className="text-xs font-mono text-[var(--yes-ink)] truncate">{launchCmd}</code>
                <button
                  type="button"
                  onClick={() => handleCopy(launchCmd, 'launch')}
                  className="inline-flex items-center gap-1 h-7 px-2.5 rounded-full text-xs bg-[var(--yes-fill)] hover:bg-[var(--yes-fill-hover)] text-[var(--yes-ink)] shrink-0 cursor-pointer"
                >
                  {copiedKey === 'launch' ? (
                    <>
                      <Check className="w-3 h-3 text-[var(--yes-ok)]" />
                      已复制
                    </>
                  ) : (
                    <>
                      <Copy className="w-3 h-3" />
                      复制
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Right: 1080P Client Geometry Simulator */}
          <div className="lg:col-span-7 yes-card p-5 space-y-4">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Monitor className="w-4 h-4 text-[var(--yes-primary)]" />
                <h3 className="text-[15px] font-semibold text-[var(--yes-ink)]">
                  1080P 屏幕窗口客户区实时校验
                </h3>
              </div>
              <span className="text-xs font-mono text-[var(--yes-ink3)]">window_1080p.py</span>
            </div>

            <div className="flex flex-wrap gap-2">
              {GEOMETRY_PRESETS.map((preset) => (
                <button
                  key={preset.label}
                  type="button"
                  onClick={() => {
                    onChange({
                      ...desktopClone,
                      clientWidth: preset.width,
                      clientHeight: preset.height,
                      dpiScalePercent: preset.dpi,
                    });
                    if (preset.width === 1920 && preset.height === 1080) {
                      onApplyResolution('1920x1080');
                    } else if (preset.width === 1600 && preset.height === 900) {
                      onApplyResolution('1600x900');
                    } else if (preset.width === 1280 && preset.height === 720) {
                      onApplyResolution('1280x720');
                    }
                  }}
                  className="h-8 px-3 rounded-full text-xs bg-[var(--yes-fill)] hover:bg-[var(--yes-fill-hover)] text-[var(--yes-ink)] transition-colors cursor-pointer whitespace-nowrap"
                >
                  {preset.label} · {preset.note}
                </button>
              ))}
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1">
                <label htmlFor="client-width" className="text-xs text-[var(--yes-ink3)]">
                  客户区宽度 (px)
                </label>
                <input
                  id="client-width"
                  type="number"
                  min={640}
                  max={3840}
                  value={desktopClone.clientWidth}
                  onChange={(e) =>
                    onChange({ ...desktopClone, clientWidth: Number(e.target.value) })
                  }
                  className="w-full h-9 px-3 text-sm font-mono tabular-nums rounded-xl bg-[var(--yes-inset)] text-[var(--yes-ink)] border border-[var(--yes-line2)]"
                />
              </div>
              <div className="space-y-1">
                <label htmlFor="client-height" className="text-xs text-[var(--yes-ink3)]">
                  客户区高度 (px)
                </label>
                <input
                  id="client-height"
                  type="number"
                  min={360}
                  max={2160}
                  value={desktopClone.clientHeight}
                  onChange={(e) =>
                    onChange({ ...desktopClone, clientHeight: Number(e.target.value) })
                  }
                  className="w-full h-9 px-3 text-sm font-mono tabular-nums rounded-xl bg-[var(--yes-inset)] text-[var(--yes-ink)] border border-[var(--yes-line2)]"
                />
              </div>
              <div className="space-y-1">
                <label htmlFor="dpi-scale" className="text-xs text-[var(--yes-ink3)]">
                  Windows DPI 缩放
                </label>
                <select
                  id="dpi-scale"
                  value={desktopClone.dpiScalePercent}
                  onChange={(e) =>
                    onChange({ ...desktopClone, dpiScalePercent: Number(e.target.value) })
                  }
                  className="w-full h-9 px-3 text-sm font-mono tabular-nums rounded-xl bg-[var(--yes-inset)] text-[var(--yes-ink)] border border-[var(--yes-line2)]"
                >
                  <option value={100}>100%</option>
                  <option value={125}>125%</option>
                  <option value={150}>150%</option>
                  <option value={175}>175%</option>
                </select>
              </div>
            </div>

            <div className="pt-3 border-t border-[var(--yes-line)] space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  {verdict.isValid ? (
                    <ShieldCheck className="w-4 h-4 text-[var(--yes-ok)] shrink-0" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 text-[var(--yes-warn)] shrink-0" />
                  )}
                  <span
                    className={`text-sm font-semibold ${
                      verdict.isValid ? 'text-[var(--yes-ok)]' : 'text-[var(--yes-warn)]'
                    }`}
                  >
                    {verdict.label}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-xs font-mono tabular-nums text-[var(--yes-ink3)]">
                  <span>纵横比 {verdict.aspectRatio}</span>
                  <span aria-hidden="true">·</span>
                  <span>误差 {verdict.ratioErrorPercent}%</span>
                  <span aria-hidden="true">·</span>
                  <span>缩放 {verdict.scaleX}x</span>
                </div>
              </div>
              <p className="text-xs text-[var(--yes-ink2)] leading-relaxed">
                {verdict.recommendation}
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
