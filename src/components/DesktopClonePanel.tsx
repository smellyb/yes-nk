import { useState } from 'react';
import { Check, Copy, Monitor, ShieldCheck, AlertTriangle } from 'lucide-react';
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

const RUN_MODE_CARDS: {
  mode: RunMode;
  title: string;
  subtitle: string;
  detail: string;
}[] = [
  {
    mode: 'desktop_clone',
    title: '桌面分身模式（与 YES-BD2 完全一致）',
    subtitle: 'Windows 子会话 (Child Session) + CloneDesktop.exe 独立窗口',
    detail:
      '需 Win10/11 专业版。在主桌面打开 1920×1080 独立虚拟桌面窗口（最小化也会继续画），完全不抢占主桌面鼠标键盘；支持一键设定与一键还原。',
  },
  {
    mode: 'background_post_message',
    title: '后台窗口消息模式',
    subtitle: 'PostMessage + WGC/BitBlt 后台截图',
    detail:
      '无需切换桌面，直接向被其他窗口遮挡（未最小化）的 nikke.exe 发送窗口消息；若遇个别界面拖拽受限可随时切至桌面分身。',
  },
  {
    mode: 'foreground_compat',
    title: '前台兼容兜底模式',
    subtitle: 'Pynput 标准输入 · 高兼容性',
    detail:
      '针对国服 WeGame / ACE 严格权限环境下的最终兜底方案，保持游戏窗口置前并执行完整日常一条龙。',
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
  { label: '1080P 主桌面窗口 (900p)', width: 1600, height: 900, dpi: 125, note: '16:9 缩放' },
  { label: '1080P 主桌面小窗 (720p)', width: 1280, height: 720, dpi: 100, note: '最低合规' },
  { label: '任务栏挤压异常示例', width: 1920, height: 1009, dpi: 100, note: '需校准' },
];

export default function DesktopClonePanel({
  desktopClone,
  onChange,
  onApplyResolution,
}: DesktopClonePanelProps) {
  const [copiedCmd, setCopiedCmd] = useState(false);

  const verdict = evaluateClientGeometry(
    desktopClone.clientWidth,
    desktopClone.clientHeight,
    desktopClone.dpiScalePercent
  );
  const launchCmd = buildLaunchCommand(desktopClone);
  const sanitizedName = sanitizeDesktopName(desktopClone.desktop_name);
  const interactionBackend = resolveInteractionBackend(desktopClone.run_mode);

  const handleCopyLaunch = async () => {
    try {
      await navigator.clipboard.writeText(launchCmd);
      setCopiedCmd(true);
      window.setTimeout(() => setCopiedCmd(false), 1800);
    } catch {
      setCopiedCmd(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
          桌面分身运行模式与 1080P 显示器适配
        </h2>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          与 YES-BD2 完全一致的 Windows 子会话（Child Session）桌面分身方案：通过 tools/clone_desktop/setup.ps1 一次性编译独立分身窗口 CloneDesktop.exe，内嵌 1920×1080 画面且最小化持续运行。
        </p>
      </div>

      {/* 3-tier Run Mode Selection */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-4" aria-label="运行模式选择">
        {RUN_MODE_CARDS.map((card) => {
          const active = desktopClone.run_mode === card.mode;
          return (
            <button
              key={card.mode}
              type="button"
              onClick={() => onChange({ ...desktopClone, run_mode: card.mode })}
              className={`text-left p-5 rounded-xl border transition-colors ${
                active
                  ? 'bg-white dark:bg-[#23272F] border-[#0067C0] dark:border-[#4CC2FF]'
                  : 'bg-white dark:bg-[#1C1F24] border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-semibold text-slate-900 dark:text-white">
                  {card.title}
                </span>
                {active && (
                  <span className="text-xs font-medium text-[#0067C0] dark:text-[#4CC2FF] whitespace-nowrap shrink-0">
                    已选定
                  </span>
                )}
              </div>
              <div className="mt-1 text-xs font-mono text-slate-500 dark:text-slate-400">
                {card.subtitle}
              </div>
              <p className="mt-2.5 text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                {card.detail}
              </p>
            </button>
          );
        })}
      </section>

      {/* Split Panel: Desktop Clone Config + 1080P Client Geometry Simulator */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <section className="lg:col-span-5 bg-white dark:bg-[#1C1F24] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold text-slate-900 dark:text-white">
              分身会话与启动参数
            </h3>
            <span className="text-xs font-mono text-slate-500 dark:text-slate-400">
              {interactionBackend}
            </span>
          </div>

          <div className="space-y-3.5 text-sm">
            <div className="space-y-1">
              <label
                htmlFor="clone-desktop-name"
                className="text-xs text-slate-500 dark:text-slate-400"
              >
                分身会话标识（数据目录 %LOCALAPPDATA%\yes-nk\clone-desktop）
              </label>
              <input
                id="clone-desktop-name"
                type="text"
                value={desktopClone.desktop_name}
                onChange={(e) =>
                  onChange({ ...desktopClone, desktop_name: e.target.value })
                }
                className="w-full px-3 py-2 text-sm font-mono rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-[#141619]"
              />
              <div className="text-xs font-mono text-slate-500 dark:text-slate-400">
                首次设定：powershell -ExecutionPolicy Bypass -File tools\clone_desktop\setup.ps1（会话 {sanitizedName}）
              </div>
            </div>

            <div className="space-y-1">
              <label
                htmlFor="clone-hotkey"
                className="text-xs text-slate-500 dark:text-slate-400"
              >
                主桌面 / 分身切换热键
              </label>
              <input
                id="clone-hotkey"
                type="text"
                value={desktopClone.switch_hotkey}
                onChange={(e) =>
                  onChange({ ...desktopClone, switch_hotkey: e.target.value })
                }
                className="w-full px-3 py-2 text-sm font-mono rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-[#141619]"
              />
            </div>

            <div className="pt-2 space-y-2.5 border-t border-slate-200 dark:border-slate-800">
              <label className="flex items-center justify-between gap-3 cursor-pointer">
                <span className="text-slate-700 dark:text-slate-300">
                  分身内默认推荐 1920×1080 无边框全屏
                </span>
                <input
                  type="checkbox"
                  checked={desktopClone.prefer_borderless_1080p}
                  onChange={(e) =>
                    onChange({
                      ...desktopClone,
                      prefer_borderless_1080p: e.target.checked,
                    })
                  }
                  className="w-4 h-4 accent-[#0067C0]"
                />
              </label>

              <label className="flex items-center justify-between gap-3 cursor-pointer">
                <span className="text-slate-700 dark:text-slate-300">
                  退出程序时自动释放分身桌面句柄
                </span>
                <input
                  type="checkbox"
                  checked={desktopClone.auto_close_desktop_on_exit}
                  onChange={(e) =>
                    onChange({
                      ...desktopClone,
                      auto_close_desktop_on_exit: e.target.checked,
                    })
                  }
                  className="w-4 h-4 accent-[#0067C0]"
                />
              </label>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-200 dark:border-slate-800 space-y-2">
            <div className="text-xs text-slate-500 dark:text-slate-400">
              Windows 本地推荐启动命令
            </div>
            <div className="flex items-center justify-between gap-2 px-3 py-2 rounded-lg bg-slate-50 dark:bg-[#141619] border border-slate-200 dark:border-slate-800">
              <code className="text-xs font-mono text-slate-800 dark:text-slate-200 truncate">
                {launchCmd}
              </code>
              <button
                type="button"
                onClick={handleCopyLaunch}
                className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-md hover:bg-slate-200/70 dark:hover:bg-slate-800 transition-colors shrink-0"
              >
                {copiedCmd ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-[#16A34A]" />
                    已复制
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    复制
                  </>
                )}
              </button>
            </div>
          </div>
        </section>

        {/* 1080P Screen & 16:9 Client Area Diagnostic */}
        <section className="lg:col-span-7 bg-white dark:bg-[#1C1F24] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-5">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Monitor className="w-4 h-4 text-[#0067C0] dark:text-[#4CC2FF]" />
              <h3 className="text-base font-semibold text-slate-900 dark:text-white">
                1080P 屏幕窗口客户区实时校验
              </h3>
            </div>
            <span className="text-xs font-mono text-slate-500 dark:text-slate-400">
              window_1080p.py
            </span>
          </div>

          {/* Preset Quick Buttons */}
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
                className="px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-[#141619] hover:border-[#0067C0] dark:hover:border-[#4CC2FF] transition-colors whitespace-nowrap shrink-0"
              >
                {preset.label} · {preset.note}
              </button>
            ))}
          </div>

          {/* Live Numeric Inputs */}
          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-1">
              <label
                htmlFor="client-width"
                className="text-xs text-slate-500 dark:text-slate-400"
              >
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
                className="w-full px-3 py-2 text-sm font-mono tabular-nums rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-[#141619]"
              />
            </div>
            <div className="space-y-1">
              <label
                htmlFor="client-height"
                className="text-xs text-slate-500 dark:text-slate-400"
              >
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
                className="w-full px-3 py-2 text-sm font-mono tabular-nums rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-[#141619]"
              />
            </div>
            <div className="space-y-1">
              <label
                htmlFor="dpi-scale"
                className="text-xs text-slate-500 dark:text-slate-400"
              >
                Windows DPI 缩放
              </label>
              <select
                id="dpi-scale"
                value={desktopClone.dpiScalePercent}
                onChange={(e) =>
                  onChange({ ...desktopClone, dpiScalePercent: Number(e.target.value) })
                }
                className="w-full px-3 py-2 text-sm font-mono tabular-nums rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-[#141619]"
              >
                <option value={100}>100%</option>
                <option value={125}>125%</option>
                <option value={150}>150%</option>
                <option value={175}>175%</option>
              </select>
            </div>
          </div>

          {/* Diagnostic Verdict Readout */}
          <div className="pt-4 border-t border-slate-200 dark:border-slate-800 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                {verdict.isValid ? (
                  <ShieldCheck className="w-4 h-4 text-[#16A34A] shrink-0" />
                ) : (
                  <AlertTriangle className="w-4 h-4 text-[#D97706] shrink-0" />
                )}
                <span
                  className={`text-sm font-semibold ${
                    verdict.isValid ? 'text-[#16A34A]' : 'text-[#D97706]'
                  }`}
                >
                  {verdict.label}
                </span>
              </div>

              <div className="flex items-center gap-3 text-xs font-mono tabular-nums text-slate-500 dark:text-slate-400">
                <span>纵横比 {verdict.aspectRatio}</span>
                <span aria-hidden="true">·</span>
                <span>误差 {verdict.ratioErrorPercent}%</span>
                <span aria-hidden="true">·</span>
                <span>缩放 {verdict.scaleX}x</span>
              </div>
            </div>

            <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
              {verdict.recommendation}
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
