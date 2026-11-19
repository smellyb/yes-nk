import {
  CalendarCheck,
  FileCode2,
  House,
  ListChecks,
  Loader2,
  Monitor,
  Settings,
  Terminal,
  Zap,
} from 'lucide-react';
import { ClientSettings, DesktopCloneSettings, NavSection } from '../types';

interface YesSidebarProps {
  activeNav: NavSection;
  onSelectNav: (nav: NavSection) => void;
  darkMode: boolean;
  onChangeTheme: (dark: boolean) => void;
  doneCount: number;
  enabledCount: number;
  triggerEnabledCount: number;
  mappingCount: number;
  isRunning: boolean;
  runningTaskName: string | null;
  runFinishedCount: number;
  runTotalCount: number;
  settings: ClientSettings;
  desktopClone: DesktopCloneSettings;
}

interface NavSpec {
  id: NavSection;
  label: string;
  icon: typeof House;
  badge?: string;
}

export default function YesSidebar({
  activeNav,
  onSelectNav,
  darkMode,
  onChangeTheme,
  doneCount,
  enabledCount,
  triggerEnabledCount,
  mappingCount,
  isRunning,
  runningTaskName,
  runFinishedCount,
  runTotalCount,
  settings,
  desktopClone,
}: YesSidebarProps) {
  const mainNav: NavSpec[] = [
    { id: 'home', label: '首页', icon: House },
    { id: 'report', label: '今日报表', icon: ListChecks },
    {
      id: 'tasks',
      label: '任务设定',
      icon: CalendarCheck,
      badge: `${doneCount}/${enabledCount}`,
    },
    {
      id: 'triggers',
      label: '触发守护',
      icon: Zap,
      badge: `${triggerEnabledCount}`,
    },
    {
      id: 'mappings',
      label: '素材映射',
      icon: FileCode2,
      badge: `${mappingCount}`,
    },
  ];

  const bottomNav: NavSpec[] = [
    { id: 'desktop', label: '桌面分身', icon: Monitor },
    { id: 'logs', label: '运行日志', icon: Terminal },
    { id: 'settings', label: '设置', icon: Settings },
  ];

  const renderNavItem = (item: NavSpec) => {
    const Icon = item.icon;
    const active = activeNav === item.id;
    return (
      <button
        key={item.id}
        type="button"
        onClick={() => onSelectNav(item.id)}
        className={`group w-full h-10 px-1.5 flex items-center justify-between rounded-full text-[13px] transition-all duration-150 whitespace-nowrap shrink-0 cursor-pointer ${
          active
            ? 'bg-[var(--yes-nav-on)] text-[var(--yes-ink)] shadow-xs'
            : 'text-[var(--yes-ink)] hover:bg-[var(--yes-ink)]/5'
        }`}
      >
        <span className="flex items-center gap-2.5 min-w-0">
          <span
            className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 transition-colors ${
              active
                ? 'bg-[var(--yes-primary)] text-white'
                : 'bg-[var(--yes-card)] text-[var(--yes-nav-icon)] border border-[var(--yes-ring)]'
            }`}
          >
            <Icon className="w-3.5 h-3.5" strokeWidth={2} />
          </span>
          <span className="truncate">{item.label}</span>
        </span>
        {item.badge && (
          <span
            className={`mr-1.5 px-2 py-0.5 text-[11px] font-mono tabular-nums rounded-full shrink-0 ${
              active
                ? 'bg-[var(--yes-accent-soft)] text-[var(--yes-ghost-ink)]'
                : 'bg-[var(--yes-accent-soft)] text-[var(--yes-ink3)]'
            }`}
          >
            {item.badge}
          </span>
        )}
      </button>
    );
  };

  const progressPct =
    runTotalCount > 0 ? Math.min(100, Math.round((runFinishedCount / runTotalCount) * 100)) : 0;

  return (
    <aside
      aria-label="主侧边栏"
      className="w-[216px] shrink-0 bg-[var(--yes-side)] rounded-[20px] p-3 flex flex-col justify-between select-none"
    >
      {/* Top: Brand + Primary Navigation */}
      <div className="space-y-4">
        <div className="flex items-center gap-2.5 px-1.5 pt-1">
          <div className="w-8 h-8 rounded-[10px] bg-[var(--yes-primary)] text-white font-bold text-xs flex items-center justify-center shrink-0 tracking-tight">
            NK
          </div>
          <div className="min-w-0 leading-tight">
            <div className="text-[14px] font-semibold text-[var(--yes-ink)] truncate">
              YES-NK
            </div>
            <div className="text-[11px] text-[var(--yes-ink3)] truncate">
              NIKKE 自动日常
            </div>
          </div>
        </div>

        <nav className="space-y-1" aria-label="核心功能">
          {mainNav.map(renderNavItem)}
        </nav>
      </div>

      {/* Bottom: Utility Navigation + Theme Switch + Status Footer */}
      <div className="space-y-3 pt-4">
        <nav className="space-y-1" aria-label="工具与系统">
          {bottomNav.map(renderNavItem)}
        </nav>

        {/* YES-BD2 淡紫 / 深色 Segmented Switch */}
        <div
          role="group"
          aria-label="主题切换"
          className="grid grid-cols-2 p-1 rounded-full bg-[var(--yes-well)]"
        >
          <button
            type="button"
            aria-pressed={!darkMode}
            onClick={() => onChangeTheme(false)}
            className={`h-7 rounded-full text-xs transition-all cursor-pointer whitespace-nowrap ${
              !darkMode
                ? 'bg-[var(--yes-raised)] text-[var(--yes-ink)] shadow-xs font-medium'
                : 'text-[var(--yes-ink2)] hover:text-[var(--yes-ink)]'
            }`}
          >
            淡紫
          </button>
          <button
            type="button"
            aria-pressed={darkMode}
            onClick={() => onChangeTheme(true)}
            className={`h-7 rounded-full text-xs transition-all cursor-pointer whitespace-nowrap ${
              darkMode
                ? 'bg-[var(--yes-raised)] text-[var(--yes-ink)] shadow-xs font-medium'
                : 'text-[var(--yes-ink2)] hover:text-[var(--yes-ink)]'
            }`}
          >
            深色
          </button>
        </div>

        {/* YES-BD2 _StatusFooter */}
        <button
          type="button"
          onClick={() => onSelectNav(isRunning ? 'home' : 'desktop')}
          className="w-full text-left rounded-[14px] bg-[var(--yes-card)] px-3 py-2.5 space-y-1 transition-opacity hover:opacity-95 cursor-pointer"
        >
          <div className="flex items-center gap-2">
            {isRunning ? (
              <Loader2 className="w-3.5 h-3.5 text-[var(--yes-primary)] animate-spin shrink-0" />
            ) : (
              <span className="w-2.5 h-2.5 rounded-full bg-[var(--yes-ok)] shrink-0" />
            )}
            <span className="text-[13px] font-medium text-[var(--yes-ink)] truncate">
              {isRunning ? '正在跑' : '已配置国服 PC'}
            </span>
          </div>

          {isRunning ? (
            <>
              <div className="h-1 w-full rounded-full bg-[var(--yes-well)] overflow-hidden">
                <div
                  className="h-full rounded-full bg-[var(--yes-primary)] transition-all duration-300"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
              <div className="text-[11px] text-[var(--yes-ink3)] truncate">
                {runningTaskName ?? '准备状态机'}
              </div>
              <div className="text-[11px] font-mono tabular-nums text-[var(--yes-ink3)]">
                完成 {runFinishedCount} / {runTotalCount} 项
              </div>
            </>
          ) : (
            <>
              <div className="text-[11px] font-mono text-[var(--yes-ink3)] truncate">
                {settings.exeName} · {desktopClone.clientWidth}×{desktopClone.clientHeight}
              </div>
              <div className="text-[11px] text-[var(--yes-ink3)] truncate">
                {desktopClone.run_mode === 'desktop_clone'
                  ? 'Windows 子会话分身'
                  : desktopClone.run_mode === 'background_post_message'
                  ? '后台窗口消息'
                  : '标准前台兼容'}
              </div>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
