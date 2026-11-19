import { useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowDown,
  ArrowUp,
  Check,
  ChevronRight,
  Copy,
  Download,
  FileCode2,
  ListChecks,
  Monitor,
  Moon,
  Play,
  RotateCcw,
  Settings2,
  SlidersHorizontal,
  Square,
  Sun,
  Terminal,
  Trash2,
  Zap,
} from 'lucide-react';
import DesktopClonePanel from './components/DesktopClonePanel';
import MappingsPanel from './components/MappingsPanel';
import {
  BASIC_DAILY_IDS,
  INITIAL_DESKTOP_CLONE,
  INITIAL_SETTINGS,
  INITIAL_TASKS,
  INITIAL_TRIGGERS,
  RECOGNITION_MAPPINGS,
} from './data/presetData';
import {
  AutomationTask,
  ClientSettings,
  DesktopCloneSettings,
  LogEntry,
  NavSection,
  RecognitionMode,
  TaskStatus,
  TriggerRule,
} from './types';
import {
  buildYesNkExportConfig,
  evaluateClientGeometry,
  reorderTasks,
  resolveInteractionBackend,
} from './utils/workbenchLogic';

function formatTime(date: Date): string {
  return date.toTimeString().slice(0, 8);
}

const MODE_LABELS: Record<RecognitionMode, string> = {
  ocr: 'OCR 文字优先',
  template: '模板特征匹配',
  hybrid: 'COCO + OCR 混合',
};

const RUN_MODE_SHORT: Record<DesktopCloneSettings['run_mode'], string> = {
  desktop_clone: '桌面分身 (Windows 子会话)',
  background_post_message: '后台消息 (PostMessage)',
  foreground_compat: '前台兼容 (Pynput)',
};

export default function App() {
  const [darkMode, setDarkMode] = useState<boolean>(false);
  const [activeNav, setActiveNav] = useState<NavSection>('tasks');
  const [tasks, setTasks] = useState<AutomationTask[]>(INITIAL_TASKS);
  const [triggers, setTriggers] = useState<TriggerRule[]>(INITIAL_TRIGGERS);
  const [settings, setSettings] = useState<ClientSettings>(INITIAL_SETTINGS);
  const [desktopClone, setDesktopClone] = useState<DesktopCloneSettings>(INITIAL_DESKTOP_CLONE);
  const [selectedTaskId, setSelectedTaskId] = useState<string>(INITIAL_TASKS[0].id);
  const [categoryFilter, setCategoryFilter] = useState<string>('全部');

  // Dry-run execution state
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [runningTaskId, setRunningTaskId] = useState<string | null>(null);
  const [taskStatuses, setTaskStatuses] = useState<Record<string, TaskStatus>>({});
  const [logs, setLogs] = useState<LogEntry[]>([
    {
      id: 'init-1',
      timestamp: formatTime(new Date()),
      level: 'INFO',
      source: 'YES-NK',
      message:
        '已完整转换 Shinarin/MaaNikke 全部 22 条国服自动化流水线并内置 40 项实测 COCO 模板至 YES-NK ok-script 架构。',
    },
  ]);
  const [logFilter, setLogFilter] = useState<'ALL' | LogEntry['level']>('ALL');
  const [copiedConfig, setCopiedConfig] = useState<boolean>(false);

  const timersRef = useRef<number[]>([]);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode);
  }, [darkMode]);

  useEffect(() => {
    return () => {
      timersRef.current.forEach((id) => window.clearTimeout(id));
    };
  }, []);

  const enabledTasks = useMemo(() => tasks.filter((t) => t.enabled), [tasks]);
  const totalEstimatedSec = useMemo(
    () => enabledTasks.reduce((sum, t) => sum + t.estimatedSec, 0),
    [enabledTasks]
  );

  const selectedTask = useMemo(
    () => tasks.find((t) => t.id === selectedTaskId) ?? tasks[0],
    [tasks, selectedTaskId]
  );

  const filteredTasks = useMemo(() => {
    if (categoryFilter === '全部') return tasks;
    return tasks.filter((t) => t.category === categoryFilter);
  }, [tasks, categoryFilter]);

  const filteredLogs = useMemo(() => {
    if (logFilter === 'ALL') return logs;
    return logs.filter((entry) => entry.level === logFilter);
  }, [logs, logFilter]);

  const geometryVerdict = useMemo(
    () =>
      evaluateClientGeometry(
        desktopClone.clientWidth,
        desktopClone.clientHeight,
        desktopClone.dpiScalePercent
      ),
    [desktopClone.clientWidth, desktopClone.clientHeight, desktopClone.dpiScalePercent]
  );

  const appendLog = (level: LogEntry['level'], source: string, message: string) => {
    setLogs((prev) => [
      ...prev,
      {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        timestamp: formatTime(new Date()),
        level,
        source,
        message,
      },
    ]);
  };

  const stopSimulation = () => {
    timersRef.current.forEach((id) => window.clearTimeout(id));
    timersRef.current = [];
    if (isRunning) {
      appendLog('WARN', 'DailyTask', '已手动终止仿真队列并安全归位状态机。');
    }
    setIsRunning(false);
    setRunningTaskId(null);
  };

  const runTaskQueue = (queue: AutomationTask[]) => {
    if (queue.length === 0) {
      appendLog('WARN', 'DailyTask', '未启用任何子任务，请至少勾选 1 项日常任务。');
      return;
    }

    stopSimulation();
    setIsRunning(true);
    setTaskStatuses({});

    appendLog(
      'INFO',
      'ok.OK',
      `启动基础日常一条龙：共 ${queue.length} 项 · 模式 ${RUN_MODE_SHORT[desktopClone.run_mode]} · 客户区 ${desktopClone.clientWidth}×${desktopClone.clientHeight}`
    );

    let delay = 300;
    queue.forEach((task) => {
      const startTimer = window.setTimeout(() => {
        setRunningTaskId(task.id);
        setTaskStatuses((prev) => ({ ...prev, [task.id]: 'running' }));
        appendLog('INFO', task.className, `开始执行：${task.name} (${task.pythonModule})`);
      }, delay);
      timersRef.current.push(startTimer);
      delay += 380;

      task.steps.forEach((step, idx) => {
        const stepTimer = window.setTimeout(() => {
          const level: LogEntry['level'] = idx % 2 === 0 ? 'OCR' : 'ACTION';
          appendLog(level, task.className, step);
        }, delay);
        timersRef.current.push(stepTimer);
        delay += 360;
      });

      const doneTimer = window.setTimeout(() => {
        setTaskStatuses((prev) => ({ ...prev, [task.id]: 'completed' }));
        appendLog('INFO', task.className, `完成：${task.name}`);
      }, delay);
      timersRef.current.push(doneTimer);
      delay += 260;
    });

    const finishTimer = window.setTimeout(() => {
      setIsRunning(false);
      setRunningTaskId(null);
      appendLog('INFO', 'DailyTask', '基础日常一条龙全部执行完毕，已返回大厅。');
    }, delay + 120);
    timersRef.current.push(finishTimer);
  };

  const toggleTaskEnabled = (taskId: string) => {
    setTasks((prev) =>
      prev.map((t) => (t.id === taskId ? { ...t, enabled: !t.enabled } : t))
    );
  };

  const moveTask = (taskId: string, direction: -1 | 1) => {
    setTasks((prev) => reorderTasks(prev, taskId, direction));
  };

  const updateTaskOption = (
    taskId: string,
    optionKey: string,
    nextValue: boolean | string | number
  ) => {
    setTasks((prev) =>
      prev.map((t) =>
        t.id === taskId
          ? {
              ...t,
              options: t.options.map((opt) =>
                opt.key === optionKey ? { ...opt, value: nextValue } : opt
              ),
            }
          : t
      )
    );
  };

  const toggleTrigger = (triggerId: string) => {
    setTriggers((prev) =>
      prev.map((tr) => (tr.id === triggerId ? { ...tr, enabled: !tr.enabled } : tr))
    );
  };

  const updateTriggerInterval = (triggerId: string, intervalMs: number) => {
    setTriggers((prev) =>
      prev.map((tr) =>
        tr.id === triggerId ? { ...tr, intervalMs: Math.max(200, intervalMs) } : tr
      )
    );
  };

  const exportedConfigJson = useMemo(
    () =>
      JSON.stringify(
        buildYesNkExportConfig(settings, desktopClone, tasks, triggers),
        null,
        2
      ),
    [settings, desktopClone, tasks, triggers]
  );

  const handleCopyConfig = async () => {
    try {
      await navigator.clipboard.writeText(exportedConfigJson);
      setCopiedConfig(true);
      window.setTimeout(() => setCopiedConfig(false), 1800);
    } catch {
      appendLog('WARN', 'Export', '剪贴板写入受限，请改用“下载配置”保存 yes_nk_config.json。');
    }
  };

  const handleDownloadConfig = () => {
    const blob = new Blob([exportedConfigJson], { type: 'application/json;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'yes_nk_config.json';
    link.click();
    URL.revokeObjectURL(url);
    appendLog('INFO', 'Export', '已下载 yes_nk_config.json（放置仓库根目录即可被 yes_nk/config.py 自动加载）。');
  };

  const navItems: { id: NavSection; label: string; icon: typeof ListChecks; count?: number }[] = [
    { id: 'tasks', label: '日常一条龙', icon: ListChecks, count: enabledTasks.length },
    { id: 'desktop', label: '桌面分身与 1080P', icon: Monitor },
    {
      id: 'triggers',
      label: '触发守护',
      icon: Zap,
      count: triggers.filter((t) => t.enabled).length,
    },
    {
      id: 'mappings',
      label: 'COCO 与素材映射',
      icon: FileCode2,
      count: RECOGNITION_MAPPINGS.length,
    },
    { id: 'logs', label: '运行日志', icon: Terminal, count: logs.length },
    { id: 'settings', label: '全局与导出', icon: Settings2 },
  ];

  const sectionBreadcrumbs: Record<NavSection, string> = {
    tasks: 'YES-NK / 全量日常一条龙（22 条 MaaNikke 转换流水线）',
    desktop: 'YES-NK / 仿 YES-BD2 桌面分身与 1080P 适配',
    triggers: 'YES-NK / 后台触发守护',
    mappings: 'YES-NK / COCO 特征与 MaaNikke 素材转换',
    logs: 'YES-NK / 状态机运行日志',
    settings: 'YES-NK / 客户端参数与配置导出',
  };

  const categories = ['全部', '启动与奖励', '商店相关', '日常养成', '副本挑战', '联盟与活动'];

  return (
    <div className="min-h-screen flex bg-[#F3F4F6] text-slate-900 dark:bg-[#141619] dark:text-slate-100">
      {/* Fluent Desktop Sidebar */}
      <aside className="w-64 shrink-0 border-r border-slate-200 dark:border-slate-800 bg-[#F9FAFB] dark:bg-[#181B20] flex flex-col">
        <div className="h-14 px-5 flex items-center justify-between border-b border-slate-200 dark:border-slate-800">
          <span className="text-base font-bold tracking-tight text-slate-900 dark:text-white whitespace-nowrap shrink-0">
            YES-NK
          </span>
          <span className="text-xs font-mono tabular-nums text-slate-500 dark:text-slate-400">
            ok-script
          </span>
        </div>

        <nav className="flex-1 p-3 space-y-1" aria-label="主导航">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = activeNav === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => setActiveNav(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-colors whitespace-nowrap shrink-0 ${
                  active
                    ? 'bg-white dark:bg-[#23272F] text-[#0067C0] dark:text-[#4CC2FF] border border-slate-200 dark:border-slate-700'
                    : 'text-slate-600 dark:text-slate-300 hover:bg-slate-200/60 dark:hover:bg-slate-800/60 border border-transparent'
                }`}
              >
                <span className="flex items-center gap-2.5 truncate">
                  <Icon className="w-4 h-4 shrink-0" />
                  <span className="truncate">{item.label}</span>
                </span>
                {typeof item.count === 'number' && (
                  <span className="text-xs font-mono tabular-nums text-slate-400 dark:text-slate-500">
                    {item.count}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        <div className="p-4 border-t border-slate-200 dark:border-slate-800 space-y-2 text-xs text-slate-500 dark:text-slate-400">
          <div className="flex items-center justify-between gap-2">
            <span>目标进程</span>
            <span className="font-mono text-slate-700 dark:text-slate-200 truncate">
              {settings.exeName}
            </span>
          </div>
          <div className="flex items-center justify-between gap-2">
            <span>运行隔离</span>
            <span className="text-slate-700 dark:text-slate-200 truncate">
              {desktopClone.run_mode === 'desktop_clone'
                ? '桌面分身'
                : desktopClone.run_mode === 'background_post_message'
                ? '后台消息'
                : '前台兼容'}
            </span>
          </div>
          <div className="flex items-center justify-between gap-2">
            <span>客户区校验</span>
            <span
              className={`font-mono tabular-nums ${
                geometryVerdict.isValid ? 'text-[#16A34A]' : 'text-[#D97706]'
              }`}
            >
              {desktopClone.clientWidth}×{desktopClone.clientHeight}
            </span>
          </div>
        </div>
      </aside>

      {/* Main Shell */}
      <div className="flex-1 min-w-0 flex flex-col">
        <header className="h-14 px-6 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-[#1C1F24] flex items-center justify-between gap-6">
          <div className="flex items-center gap-3 min-w-0">
            <h1 className="text-sm font-semibold text-slate-900 dark:text-slate-100 truncate">
              {sectionBreadcrumbs[activeNav]}
            </h1>
            {isRunning && (
              <span className="text-xs text-[#0067C0] dark:text-[#4CC2FF] whitespace-nowrap shrink-0">
                状态机仿真运行中
              </span>
            )}
          </div>

          <div className="flex items-center gap-2.5 shrink-0">
            <button
              type="button"
              onClick={() => setDarkMode((d) => !d)}
              aria-label="切换浅色或深色主题"
              className="p-2 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>

            {isRunning ? (
              <button
                type="button"
                onClick={stopSimulation}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium bg-[#DC2626] hover:bg-[#B91C1C] text-white transition-colors whitespace-nowrap shrink-0"
              >
                <Square className="w-3.5 h-3.5" />
                停止仿真
              </button>
            ) : (
              <button
                type="button"
                onClick={() => runTaskQueue(enabledTasks)}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium bg-[#0067C0] hover:bg-[#005A9E] dark:bg-[#4CC2FF] dark:hover:bg-[#3BB2F0] text-white dark:text-slate-950 transition-colors whitespace-nowrap shrink-0"
              >
                <Play className="w-3.5 h-3.5" />
                仿真运行一条龙 ({enabledTasks.length})
              </button>
            )}
          </div>
        </header>

        <main className="flex-1 p-6 overflow-y-auto">
          {activeNav === 'tasks' && (
            <div className="max-w-6xl mx-auto space-y-6">
              {/* Clean Unboxed KPI Summary */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 pb-5 border-b border-slate-200 dark:border-slate-800">
                <div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">已启用日常子项</div>
                  <div className="mt-1 text-2xl font-semibold font-mono tabular-nums text-slate-900 dark:text-white">
                    {enabledTasks.length} / {tasks.length}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">运行模式与交互</div>
                  <div className="mt-1 text-sm font-semibold text-slate-900 dark:text-white">
                    {RUN_MODE_SHORT[desktopClone.run_mode]}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">1080P 客户区状态</div>
                  <div
                    className={`mt-1 text-sm font-semibold ${
                      geometryVerdict.isValid ? 'text-[#16A34A]' : 'text-[#D97706]'
                    }`}
                  >
                    {geometryVerdict.label}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">一条龙预估耗时</div>
                  <div className="mt-1 text-2xl font-semibold font-mono tabular-nums text-slate-900 dark:text-white">
                    {totalEstimatedSec}s
                  </div>
                </div>
              </div>

              {/* Filter Bar */}
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-1 p-1 rounded-lg bg-slate-200/70 dark:bg-[#1C1F24] border border-slate-200 dark:border-slate-800">
                  {categories.map((cat) => (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => setCategoryFilter(cat)}
                      className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                        categoryFilter === cat
                          ? 'bg-white dark:bg-[#2A2F38] text-slate-900 dark:text-white'
                          : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                      }`}
                    >
                      {cat}
                    </button>
                  ))}
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() =>
                      setTasks((prev) =>
                        prev.map((t) => ({ ...t, enabled: BASIC_DAILY_IDS.has(t.id) }))
                      )
                    }
                    className="px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-[#1C1F24] hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0"
                  >
                    仅基础日常
                  </button>
                  <button
                    type="button"
                    onClick={() => setTasks((prev) => prev.map((t) => ({ ...t, enabled: true })))}
                    className="px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-[#1C1F24] hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0"
                  >
                    全部启用
                  </button>
                  <button
                    type="button"
                    onClick={() => setTasks(INITIAL_TASKS)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-[#1C1F24] hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    恢复默认
                  </button>
                </div>
              </div>

              {/* Split View: Task List + Detail Inspector */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                <section
                  aria-label="基础日常任务列表"
                  className="lg:col-span-7 bg-white dark:bg-[#1C1F24] border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden divide-y divide-slate-200 dark:divide-slate-800"
                >
                  {filteredTasks.map((task) => {
                    const status = taskStatuses[task.id] ?? 'idle';
                    const isSelected = task.id === selectedTask.id;
                    const globalIndex = tasks.findIndex((t) => t.id === task.id);

                    return (
                      <div
                        key={task.id}
                        className={`p-4 flex items-center justify-between gap-4 transition-colors ${
                          isSelected
                            ? 'bg-slate-50 dark:bg-[#23272F]'
                            : 'hover:bg-slate-50/70 dark:hover:bg-[#20242B]'
                        }`}
                      >
                        <div className="flex items-start gap-3.5 min-w-0 flex-1">
                          <button
                            type="button"
                            role="switch"
                            aria-checked={task.enabled}
                            aria-label={`启用或停用 ${task.name}`}
                            onClick={() => toggleTaskEnabled(task.id)}
                            className={`mt-0.5 w-10 h-5 rounded-full transition-colors shrink-0 relative ${
                              task.enabled
                                ? 'bg-[#0067C0] dark:bg-[#4CC2FF]'
                                : 'bg-slate-300 dark:bg-slate-700'
                            }`}
                          >
                            <span
                              className={`block w-4 h-4 rounded-full bg-white dark:bg-slate-950 transition-transform ${
                                task.enabled ? 'translate-x-5' : 'translate-x-0.5'
                              }`}
                            />
                          </button>

                          <button
                            type="button"
                            onClick={() => setSelectedTaskId(task.id)}
                            className="text-left min-w-0 flex-1"
                          >
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-semibold text-slate-900 dark:text-white truncate">
                                {task.name}
                              </span>
                              {runningTaskId === task.id && (
                                <span className="text-xs font-medium text-[#0067C0] dark:text-[#4CC2FF]">
                                  执行中
                                </span>
                              )}
                              {status === 'completed' && runningTaskId !== task.id && (
                                <span className="text-xs font-medium text-[#16A34A]">
                                  已完成
                                </span>
                              )}
                            </div>
                            <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-slate-500 dark:text-slate-400">
                              <span>{task.category}</span>
                              <span aria-hidden="true">·</span>
                              <span className="font-mono">{task.className}</span>
                              <span aria-hidden="true">·</span>
                              <span>{MODE_LABELS[task.recognitionMode]}</span>
                              <span aria-hidden="true">·</span>
                              <span className="font-mono tabular-nums">{task.estimatedSec}s</span>
                            </div>
                          </button>
                        </div>

                        <div className="flex items-center gap-1 shrink-0">
                          <button
                            type="button"
                            aria-label={`上移 ${task.name}`}
                            disabled={globalIndex === 0}
                            onClick={() => moveTask(task.id, -1)}
                            className="p-1.5 rounded-md text-slate-500 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/70 dark:hover:bg-slate-700 disabled:opacity-30 transition-colors"
                          >
                            <ArrowUp className="w-3.5 h-3.5" />
                          </button>
                          <button
                            type="button"
                            aria-label={`下移 ${task.name}`}
                            disabled={globalIndex === tasks.length - 1}
                            onClick={() => moveTask(task.id, 1)}
                            className="p-1.5 rounded-md text-slate-500 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/70 dark:hover:bg-slate-700 disabled:opacity-30 transition-colors"
                          >
                            <ArrowDown className="w-3.5 h-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => runTaskQueue([task])}
                            aria-label={`单步运行 ${task.name}`}
                            className="ml-1 inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs font-medium border border-slate-200 dark:border-slate-700 bg-white dark:bg-[#1C1F24] hover:border-[#0067C0] dark:hover:border-[#4CC2FF] transition-colors whitespace-nowrap shrink-0"
                          >
                            <Play className="w-3 h-3" />
                            单步运行
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </section>

                {/* Right Detail Panel */}
                <aside className="lg:col-span-5 lg:sticky lg:top-0 bg-white dark:bg-[#1C1F24] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-5">
                  <div className="space-y-1.5 pb-4 border-b border-slate-200 dark:border-slate-800">
                    <div className="flex items-center justify-between gap-2">
                      <h2 className="text-base font-semibold text-slate-900 dark:text-white">
                        {selectedTask.name}
                      </h2>
                      <span className="text-xs font-mono text-slate-500 dark:text-slate-400">
                        {selectedTask.className}
                      </span>
                    </div>
                    <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
                      {selectedTask.summary}
                    </p>
                    <div className="pt-1 text-xs text-slate-500 dark:text-slate-400 space-y-0.5">
                      <div>
                        Python 模块：<span className="font-mono">{selectedTask.pythonModule}</span>
                      </div>
                      <div>
                        关联 COCO 特征：
                        <span className="font-mono">{selectedTask.cocoFeatures.join(' · ')}</span>
                      </div>
                    </div>
                  </div>

                  {/* Per-Task Parameters */}
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 text-xs font-semibold text-slate-700 dark:text-slate-200">
                      <SlidersHorizontal className="w-3.5 h-3.5" />
                      任务参数配置 (default_config)
                    </div>
                    <div className="space-y-3">
                      {selectedTask.options.map((opt) => (
                        <div
                          key={opt.key}
                          className="flex items-center justify-between gap-4 py-1"
                        >
                          <label
                            htmlFor={`opt-${selectedTask.id}-${opt.key}`}
                            className="text-sm text-slate-700 dark:text-slate-300"
                          >
                            {opt.label}
                          </label>
                          {opt.type === 'boolean' && (
                            <input
                              id={`opt-${selectedTask.id}-${opt.key}`}
                              type="checkbox"
                              checked={Boolean(opt.value)}
                              onChange={(e) =>
                                updateTaskOption(selectedTask.id, opt.key, e.target.checked)
                              }
                              className="w-4 h-4 accent-[#0067C0] cursor-pointer"
                            />
                          )}
                          {opt.type === 'select' && (
                            <select
                              id={`opt-${selectedTask.id}-${opt.key}`}
                              value={String(opt.value)}
                              onChange={(e) =>
                                updateTaskOption(selectedTask.id, opt.key, e.target.value)
                              }
                              className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-[#141619]"
                            >
                              {opt.choices?.map((choice) => (
                                <option key={choice} value={choice}>
                                  {choice}
                                </option>
                              ))}
                            </select>
                          )}
                          {opt.type === 'number' && (
                            <input
                              id={`opt-${selectedTask.id}-${opt.key}`}
                              type="number"
                              min={opt.min}
                              max={opt.max}
                              value={Number(opt.value)}
                              onChange={(e) =>
                                updateTaskOption(
                                  selectedTask.id,
                                  opt.key,
                                  Number(e.target.value)
                                )
                              }
                              className="w-20 text-right font-mono tabular-nums text-xs px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-[#141619]"
                            />
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* State Machine Steps */}
                  <div className="pt-4 border-t border-slate-200 dark:border-slate-800 space-y-2.5">
                    <div className="text-xs font-semibold text-slate-700 dark:text-slate-200">
                      ok-script 状态机执行链路
                    </div>
                    <ol className="space-y-2">
                      {selectedTask.steps.map((step, idx) => (
                        <li
                          key={step}
                          className="flex items-start gap-2.5 text-xs text-slate-600 dark:text-slate-300 leading-relaxed"
                        >
                          <span className="font-mono tabular-nums text-slate-400 dark:text-slate-500 shrink-0">
                            0{idx + 1}.
                          </span>
                          <span>{step}</span>
                        </li>
                      ))}
                    </ol>
                  </div>
                </aside>
              </div>
            </div>
          )}

          {activeNav === 'desktop' && (
            <DesktopClonePanel
              desktopClone={desktopClone}
              onChange={setDesktopClone}
              onApplyResolution={(res) =>
                setSettings((prev) => ({ ...prev, resolution: res }))
              }
            />
          )}

          {activeNav === 'triggers' && (
            <div className="max-w-5xl mx-auto space-y-4">
              <div>
                <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                  后台触发任务 (TriggerTask)
                </h2>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                  对应 yes_nk/tasks/PopupGuardTrigger.py，在主任务空闲或阻塞时自动介入处理网络重连与限时弹窗。
                </p>
              </div>

              <div className="bg-white dark:bg-[#1C1F24] border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden divide-y divide-slate-200 dark:divide-slate-800">
                {triggers.map((tr) => (
                  <div
                    key={tr.id}
                    className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                  >
                    <div className="space-y-1 max-w-2xl">
                      <div className="flex items-center gap-2.5">
                        <span className="text-sm font-semibold text-slate-900 dark:text-white">
                          {tr.name}
                        </span>
                        <span className="text-xs font-mono text-slate-500 dark:text-slate-400">
                          {tr.className}
                        </span>
                      </div>
                      <p className="text-sm text-slate-600 dark:text-slate-300">
                        {tr.description}
                      </p>
                      <div className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                        <ChevronRight className="w-3.5 h-3.5" />
                        <span>触发动作：{tr.actionSummary}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-4 shrink-0">
                      <label className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                        <span>轮询间隔</span>
                        <input
                          type="number"
                          step={100}
                          min={200}
                          max={10000}
                          value={tr.intervalMs}
                          onChange={(e) =>
                            updateTriggerInterval(tr.id, Number(e.target.value))
                          }
                          className="w-20 text-right font-mono tabular-nums px-2 py-1 rounded-md border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-[#141619] text-slate-900 dark:text-slate-100"
                        />
                        <span className="font-mono">ms</span>
                      </label>

                      <button
                        type="button"
                        role="switch"
                        aria-checked={tr.enabled}
                        aria-label={`启用或停用 ${tr.name}`}
                        onClick={() => toggleTrigger(tr.id)}
                        className={`w-10 h-5 rounded-full transition-colors relative ${
                          tr.enabled
                            ? 'bg-[#0067C0] dark:bg-[#4CC2FF]'
                            : 'bg-slate-300 dark:bg-slate-700'
                        }`}
                      >
                        <span
                          className={`block w-4 h-4 rounded-full bg-white dark:bg-slate-950 transition-transform ${
                            tr.enabled ? 'translate-x-5' : 'translate-x-0.5'
                          }`}
                        />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeNav === 'mappings' && <MappingsPanel mappings={RECOGNITION_MAPPINGS} />}

          {activeNav === 'logs' && (
            <div className="max-w-5xl mx-auto space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-1 p-1 rounded-lg bg-slate-200/70 dark:bg-[#1C1F24] border border-slate-200 dark:border-slate-800">
                  {(['ALL', 'INFO', 'OCR', 'ACTION', 'WARN'] as const).map((lvl) => (
                    <button
                      key={lvl}
                      type="button"
                      onClick={() => setLogFilter(lvl)}
                      className={`px-2.5 py-1 text-xs font-mono rounded-md transition-colors whitespace-nowrap shrink-0 ${
                        logFilter === lvl
                          ? 'bg-white dark:bg-[#2A2F38] text-slate-900 dark:text-white'
                          : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                      }`}
                    >
                      {lvl}
                    </button>
                  ))}
                </div>

                <button
                  type="button"
                  onClick={() => setLogs([])}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-[#1C1F24] hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  清空日志
                </button>
              </div>

              <div className="bg-white dark:bg-[#1C1F24] border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden">
                {filteredLogs.length === 0 ? (
                  <div className="py-12 px-4 text-center space-y-3">
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      暂无运行日志。点击下方按钮试运行基础日常一条龙仿真流程。
                    </p>
                    <button
                      type="button"
                      onClick={() => runTaskQueue(enabledTasks.slice(0, 2))}
                      className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium rounded-lg bg-[#0067C0] text-white hover:bg-[#005A9E] transition-colors"
                    >
                      <Play className="w-3.5 h-3.5" />
                      试运行前 2 项任务
                    </button>
                  </div>
                ) : (
                  <div className="divide-y divide-slate-100 dark:divide-slate-800/80 font-mono text-xs">
                    {filteredLogs.map((entry) => (
                      <div
                        key={entry.id}
                        className="px-4 py-2.5 flex items-baseline gap-3 hover:bg-slate-50 dark:hover:bg-[#23272F]"
                      >
                        <span className="tabular-nums text-slate-400 shrink-0">
                          {entry.timestamp}
                        </span>
                        <span
                          className={`w-14 shrink-0 font-semibold ${
                            entry.level === 'WARN'
                              ? 'text-[#D97706]'
                              : entry.level === 'OCR'
                              ? 'text-[#0067C0] dark:text-[#4CC2FF]'
                              : entry.level === 'ACTION'
                              ? 'text-[#16A34A]'
                              : 'text-slate-600 dark:text-slate-300'
                          }`}
                        >
                          {entry.level}
                        </span>
                        <span className="text-slate-500 dark:text-slate-400 w-36 shrink-0 truncate">
                          {entry.source}
                        </span>
                        <span className="text-slate-800 dark:text-slate-200 font-sans text-xs leading-relaxed">
                          {entry.message}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {activeNav === 'settings' && (
            <div className="max-w-5xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              <section className="lg:col-span-6 bg-white dark:bg-[#1C1F24] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-4">
                <h2 className="text-base font-semibold text-slate-900 dark:text-white">
                  国服客户端与识别阈值配置
                </h2>

                <div className="space-y-3.5 text-sm">
                  <div className="space-y-1">
                    <label className="text-xs text-slate-500 dark:text-slate-400">
                      目标客户端
                    </label>
                    <div className="px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-[#141619] text-slate-700 dark:text-slate-300">
                      {settings.server} · 交互后端 {resolveInteractionBackend(desktopClone.run_mode)}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <label
                        htmlFor="setting-window-title"
                        className="text-xs text-slate-500 dark:text-slate-400"
                      >
                        窗口标题匹配
                      </label>
                      <input
                        id="setting-window-title"
                        type="text"
                        value={settings.windowTitle}
                        onChange={(e) =>
                          setSettings((prev) => ({ ...prev, windowTitle: e.target.value }))
                        }
                        className="w-full px-3 py-2 text-sm font-mono rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-[#141619]"
                      />
                    </div>
                    <div className="space-y-1">
                      <label
                        htmlFor="setting-resolution"
                        className="text-xs text-slate-500 dark:text-slate-400"
                      >
                        16:9 目标客户区
                      </label>
                      <select
                        id="setting-resolution"
                        value={settings.resolution}
                        onChange={(e) => {
                          const nextRes = e.target.value as ClientSettings['resolution'];
                          setSettings((prev) => ({ ...prev, resolution: nextRes }));
                          const [w, h] = nextRes.split('x').map(Number);
                          setDesktopClone((prev) => ({
                            ...prev,
                            clientWidth: w,
                            clientHeight: h,
                          }));
                        }}
                        className="w-full px-3 pr-8 py-2 text-sm font-mono rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-[#141619]"
                      >
                        <option value="1920x1080">1920×1080 · 无边框</option>
                        <option value="1600x900">1600×900 · 窗口化</option>
                        <option value="1280x720">1280×720 · 小窗</option>
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <label
                        htmlFor="setting-ocr-th"
                        className="text-xs text-slate-500 dark:text-slate-400"
                      >
                        OCR 置信度阈值
                      </label>
                      <input
                        id="setting-ocr-th"
                        type="number"
                        step={0.02}
                        min={0.5}
                        max={0.99}
                        value={settings.ocrConfidence}
                        onChange={(e) =>
                          setSettings((prev) => ({
                            ...prev,
                            ocrConfidence: Number(e.target.value),
                          }))
                        }
                        className="w-full px-3 py-2 text-sm font-mono tabular-nums rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-[#141619]"
                      />
                    </div>
                    <div className="space-y-1">
                      <label
                        htmlFor="setting-tpl-th"
                        className="text-xs text-slate-500 dark:text-slate-400"
                      >
                        COCO 模板阈值
                      </label>
                      <input
                        id="setting-tpl-th"
                        type="number"
                        step={0.02}
                        min={0.5}
                        max={0.99}
                        value={settings.templateThreshold}
                        onChange={(e) =>
                          setSettings((prev) => ({
                            ...prev,
                            templateThreshold: Number(e.target.value),
                          }))
                        }
                        className="w-full px-3 py-2 text-sm font-mono tabular-nums rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-[#141619]"
                      />
                    </div>
                  </div>

                  <div className="pt-2 border-t border-slate-200 dark:border-slate-800">
                    <label className="flex items-center justify-between gap-3 cursor-pointer">
                      <span className="text-slate-700 dark:text-slate-300">
                        每个日常子任务前强制校验并返回大厅
                      </span>
                      <input
                        type="checkbox"
                        checked={settings.autoReturnLobby}
                        onChange={(e) =>
                          setSettings((prev) => ({
                            ...prev,
                            autoReturnLobby: e.target.checked,
                          }))
                        }
                        className="w-4 h-4 accent-[#0067C0]"
                      />
                    </label>
                  </div>
                </div>
              </section>

              <section className="lg:col-span-6 bg-white dark:bg-[#1C1F24] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <h2 className="text-base font-semibold text-slate-900 dark:text-white whitespace-nowrap">
                      同步配置导出
                    </h2>
                    <div className="text-xs font-mono text-slate-500 dark:text-slate-400">
                      yes_nk_config.json
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      type="button"
                      onClick={handleCopyConfig}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0"
                    >
                      {copiedConfig ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-[#16A34A]" />
                          已复制
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5" />
                          复制 JSON
                        </>
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={handleDownloadConfig}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-[#0067C0] hover:bg-[#005A9E] text-white transition-colors whitespace-nowrap shrink-0"
                    >
                      <Download className="w-3.5 h-3.5" />
                      下载配置
                    </button>
                  </div>
                </div>

                <p className="text-xs text-slate-500 dark:text-slate-400">
                  下载后放入仓库根目录，运行 <code className="font-mono">python main.py</code> 时将由 <code className="font-mono">yes_nk/config.py</code> 自动读取覆盖桌面分身与窗口设置。
                </p>

                <pre className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#141619] border border-slate-200 dark:border-slate-800 text-xs font-mono text-slate-700 dark:text-slate-300 overflow-auto max-h-[380px] leading-relaxed">
                  {exportedConfigJson}
                </pre>
              </section>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
