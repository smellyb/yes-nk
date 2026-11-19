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
  Moon,
  Play,
  RotateCcw,
  Search,
  Settings2,
  SlidersHorizontal,
  Square,
  Sun,
  Terminal,
  Trash2,
  Zap,
} from 'lucide-react';
import {
  INITIAL_SETTINGS,
  INITIAL_TASKS,
  INITIAL_TRIGGERS,
  RECOGNITION_MAPPINGS,
} from './data/presetData';
import {
  AutomationTask,
  ClientSettings,
  LogEntry,
  NavSection,
  RecognitionMode,
  TaskStatus,
  TriggerRule,
} from './types';

function formatTime(date: Date): string {
  return date.toTimeString().slice(0, 8);
}

const MODE_LABELS: Record<RecognitionMode, string> = {
  ocr: 'OCR 文字优先',
  template: '模板特征匹配',
  hybrid: 'OCR + 模板混合',
};

export default function App() {
  const [darkMode, setDarkMode] = useState<boolean>(false);
  const [activeNav, setActiveNav] = useState<NavSection>('tasks');
  const [tasks, setTasks] = useState<AutomationTask[]>(INITIAL_TASKS);
  const [triggers, setTriggers] = useState<TriggerRule[]>(INITIAL_TRIGGERS);
  const [settings, setSettings] = useState<ClientSettings>(INITIAL_SETTINGS);
  const [selectedTaskId, setSelectedTaskId] = useState<string>(INITIAL_TASKS[0].id);
  const [categoryFilter, setCategoryFilter] = useState<string>('全部');

  // Mapping search & filter
  const [mappingQuery, setMappingQuery] = useState<string>('');
  const [mappingModeFilter, setMappingModeFilter] = useState<'all' | RecognitionMode>('all');

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
      message: '控制工作台已就绪。当前模式为浏览器流程仿真与配置编排，点击任意任务可预览 ok-script 执行链路。',
    },
  ]);
  const [logFilter, setLogFilter] = useState<'ALL' | LogEntry['level']>('ALL');
  const [copiedConfig, setCopiedConfig] = useState<boolean>(false);

  const timersRef = useRef<number[]>([]);

  useEffect(() => {
    const root = document.documentElement;
    if (darkMode) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
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

  const filteredMappings = useMemo(() => {
    const q = mappingQuery.trim().toLowerCase();
    return RECOGNITION_MAPPINGS.filter((item) => {
      const matchesMode = mappingModeFilter === 'all' || item.mode === mappingModeFilter;
      const matchesQuery =
        !q ||
        item.scene.toLowerCase().includes(q) ||
        item.maaNode.toLowerCase().includes(q) ||
        item.okMethod.toLowerCase().includes(q) ||
        item.targetTextOrAsset.toLowerCase().includes(q);
      return matchesMode && matchesQuery;
    });
  }, [mappingQuery, mappingModeFilter]);

  const filteredLogs = useMemo(() => {
    if (logFilter === 'ALL') return logs;
    return logs.filter((entry) => entry.level === logFilter);
  }, [logs, logFilter]);

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
      appendLog('WARN', 'Scheduler', '用户手动终止任务队列，已安全释放状态机。');
    }
    setIsRunning(false);
    setRunningTaskId(null);
  };

  const runTaskQueue = (queue: AutomationTask[]) => {
    if (queue.length === 0) {
      appendLog('WARN', 'Scheduler', '没有已启用的任务，请至少勾选 1 个日常任务后再运行。');
      return;
    }

    stopSimulation();
    setIsRunning(true);
    setTaskStatuses({});

    appendLog(
      'INFO',
      'ok.OK',
      `启动仿真队列：共 ${queue.length} 项任务 · 目标窗口 ${settings.windowTitle} (${settings.resolution}) · 引擎 ${settings.ocrEngine}`
    );

    let delay = 350;
    queue.forEach((task) => {
      const startTimer = window.setTimeout(() => {
        setRunningTaskId(task.id);
        setTaskStatuses((prev) => ({ ...prev, [task.id]: 'running' }));
        appendLog('INFO', task.className, `开始执行：${task.name} (参考节点 ${task.maaRefNode})`);
      }, delay);
      timersRef.current.push(startTimer);
      delay += 450;

      task.steps.forEach((step, idx) => {
        const stepTimer = window.setTimeout(() => {
          const level: LogEntry['level'] = idx % 2 === 0 ? 'OCR' : 'ACTION';
          appendLog(level, task.className, step);
        }, delay);
        timersRef.current.push(stepTimer);
        delay += 420;
      });

      const doneTimer = window.setTimeout(() => {
        setTaskStatuses((prev) => ({ ...prev, [task.id]: 'completed' }));
        appendLog('INFO', task.className, `完成：${task.name}`);
      }, delay);
      timersRef.current.push(doneTimer);
      delay += 300;
    });

    const finishTimer = window.setTimeout(() => {
      setIsRunning(false);
      setRunningTaskId(null);
      appendLog('INFO', 'Scheduler', '队列执行完毕，所有已启用任务均已通过状态机校验。');
    }, delay + 150);
    timersRef.current.push(finishTimer);
  };

  const toggleTaskEnabled = (taskId: string) => {
    setTasks((prev) =>
      prev.map((t) => (t.id === taskId ? { ...t, enabled: !t.enabled } : t))
    );
  };

  const moveTask = (taskId: string, direction: -1 | 1) => {
    setTasks((prev) => {
      const index = prev.findIndex((t) => t.id === taskId);
      const nextIndex = index + direction;
      if (index < 0 || nextIndex < 0 || nextIndex >= prev.length) return prev;
      const copy = [...prev];
      const [moved] = copy.splice(index, 1);
      copy.splice(nextIndex, 0, moved);
      return copy;
    });
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

  const exportedConfigJson = useMemo(() => {
    const payload = {
      project: 'YES-NK',
      framework: 'ok-script',
      client: settings,
      onetime_tasks: tasks.map((t, index) => ({
        order: index + 1,
        class: t.className,
        enabled: t.enabled,
        recognition: t.recognitionMode,
        config: Object.fromEntries(t.options.map((o) => [o.key, o.value])),
      })),
      trigger_tasks: triggers.map((tr) => ({
        class: tr.className,
        enabled: tr.enabled,
        interval_ms: tr.intervalMs,
      })),
    };
    return JSON.stringify(payload, null, 2);
  }, [settings, tasks, triggers]);

  const handleCopyConfig = async () => {
    try {
      await navigator.clipboard.writeText(exportedConfigJson);
      setCopiedConfig(true);
      window.setTimeout(() => setCopiedConfig(false), 1800);
    } catch {
      appendLog('WARN', 'Export', '剪贴板写入受限，请改用“下载配置文件”按钮导出 JSON。');
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
    appendLog('INFO', 'Export', '已导出配置文件 yes_nk_config.json。');
  };

  const navItems: { id: NavSection; label: string; icon: typeof ListChecks; count?: number }[] = [
    { id: 'tasks', label: '日常任务', icon: ListChecks, count: enabledTasks.length },
    {
      id: 'triggers',
      label: '触发守护',
      icon: Zap,
      count: triggers.filter((t) => t.enabled).length,
    },
    {
      id: 'mappings',
      label: '识别与素材映射',
      icon: FileCode2,
      count: RECOGNITION_MAPPINGS.length,
    },
    { id: 'logs', label: '运行日志', icon: Terminal, count: logs.length },
    { id: 'settings', label: '全局与导出', icon: Settings2 },
  ];

  const sectionBreadcrumbs: Record<NavSection, string> = {
    tasks: 'YES-NK / 日常任务编排',
    triggers: 'YES-NK / 后台触发守护',
    mappings: 'YES-NK / MaaNikke 识别重构映射',
    logs: 'YES-NK / 状态机运行日志',
    settings: 'YES-NK / 客户端参数与配置导出',
  };

  const categories = ['全部', '基础日常', '基地与养成', '日常副本', '活动与登录'];

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
          <div className="flex items-center justify-between">
            <span>目标客户端</span>
            <span className="font-mono text-slate-700 dark:text-slate-200 truncate max-w-[120px]">
              {settings.windowTitle}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span>分辨率基准</span>
            <span className="font-mono tabular-nums text-slate-700 dark:text-slate-200">
              {settings.resolution}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span>预计耗时</span>
            <span className="font-mono tabular-nums text-slate-700 dark:text-slate-200">
              {Math.ceil(totalEstimatedSec / 60)} 分 {totalEstimatedSec % 60} 秒
            </span>
          </div>
        </div>
      </aside>

      {/* Main Content Shell */}
      <div className="flex-1 min-w-0 flex flex-col">
        {/* Top Bar Contract: Breadcrumb on Left, Primary Actions on Right */}
        <header className="h-14 px-6 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-[#1C1F24] flex items-center justify-between gap-6">
          <div className="flex items-center gap-3 min-w-0">
            <h1 className="text-sm font-semibold text-slate-900 dark:text-slate-100 truncate">
              {sectionBreadcrumbs[activeNav]}
            </h1>
            {isRunning && (
              <span className="text-xs text-[#0067C0] dark:text-[#4CC2FF] whitespace-nowrap shrink-0">
                正在仿真执行队列
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
                停止运行
              </button>
            ) : (
              <button
                type="button"
                onClick={() => runTaskQueue(enabledTasks)}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium bg-[#0067C0] hover:bg-[#005A9E] dark:bg-[#4CC2FF] dark:hover:bg-[#3BB2F0] text-white dark:text-slate-950 transition-colors whitespace-nowrap shrink-0"
              >
                <Play className="w-3.5 h-3.5" />
                仿真运行已选任务 ({enabledTasks.length})
              </button>
            )}
          </div>
        </header>

        {/* Main Viewport */}
        <main className="flex-1 p-6 overflow-y-auto">
          {activeNav === 'tasks' && (
            <div className="max-w-6xl mx-auto space-y-6">
              {/* Summary Strip (Unboxed clean metrics) */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 pb-5 border-b border-slate-200 dark:border-slate-800">
                <div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">已启用日常任务</div>
                  <div className="mt-1 text-2xl font-semibold font-mono tabular-nums text-slate-900 dark:text-white">
                    {enabledTasks.length} / {tasks.length}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">后台触发守护</div>
                  <div className="mt-1 text-2xl font-semibold font-mono tabular-nums text-slate-900 dark:text-white">
                    {triggers.filter((t) => t.enabled).length} 项生效
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">默认识别策略</div>
                  <div className="mt-1 text-base font-semibold text-slate-900 dark:text-white">
                    {settings.ocrEngine}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">单轮预估耗时</div>
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
                      setTasks((prev) => prev.map((t) => ({ ...t, enabled: true })))
                    }
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
                    恢复默认顺序
                  </button>
                </div>
              </div>

              {/* Split View: YES-BD2 Style Task List + Inspector */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                <section className="lg:col-span-7 bg-white dark:bg-[#1C1F24] border border-slate-200 dark:border-slate-800 rounded-xl divide-y divide-slate-200 dark:divide-slate-800">
                  {filteredTasks.map((task) => {
                    const status = taskStatuses[task.id] ?? 'idle';
                    const isSelected = task.id === selectedTask.id;
                    const globalIndex = tasks.findIndex((t) => t.id === task.id);

                    return (
                      <div
                        key={task.id}
                        onClick={() => setSelectedTaskId(task.id)}
                        className={`p-4 flex items-center justify-between gap-4 cursor-pointer transition-colors ${
                          isSelected
                            ? 'bg-slate-50 dark:bg-[#23272F]'
                            : 'hover:bg-slate-50/70 dark:hover:bg-[#20242B]'
                        }`}
                      >
                        <div className="flex items-start gap-3.5 min-w-0">
                          <button
                            type="button"
                            role="switch"
                            aria-checked={task.enabled}
                            aria-label={`启用或停用 ${task.name}`}
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleTaskEnabled(task.id);
                            }}
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

                          <div className="min-w-0">
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
                          </div>
                        </div>

                        <div
                          className="flex items-center gap-1 shrink-0"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <button
                            type="button"
                            aria-label="上移任务"
                            disabled={globalIndex === 0}
                            onClick={() => moveTask(task.id, -1)}
                            className="p-1.5 rounded-md text-slate-500 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/70 dark:hover:bg-slate-700 disabled:opacity-30 transition-colors"
                          >
                            <ArrowUp className="w-3.5 h-3.5" />
                          </button>
                          <button
                            type="button"
                            aria-label="下移任务"
                            disabled={globalIndex === tasks.length - 1}
                            onClick={() => moveTask(task.id, 1)}
                            className="p-1.5 rounded-md text-slate-500 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/70 dark:hover:bg-slate-700 disabled:opacity-30 transition-colors"
                          >
                            <ArrowDown className="w-3.5 h-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => runTaskQueue([task])}
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
                <aside className="lg:col-span-5 bg-white dark:bg-[#1C1F24] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-5">
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
                    <div className="pt-1 text-xs text-slate-500 dark:text-slate-400">
                      参考 MaaNikke 流程：<span className="font-mono">{selectedTask.maaRefNode}</span>
                    </div>
                  </div>

                  {/* Per-Task Parameters */}
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 text-xs font-semibold text-slate-700 dark:text-slate-200">
                      <SlidersHorizontal className="w-3.5 h-3.5" />
                      任务参数配置
                    </div>
                    <div className="space-y-3">
                      {selectedTask.options.map((opt) => (
                        <div
                          key={opt.key}
                          className="flex items-center justify-between gap-4 py-1.5"
                        >
                          <label className="text-sm text-slate-700 dark:text-slate-300">
                            {opt.label}
                          </label>
                          {opt.type === 'boolean' && (
                            <input
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
                              value={String(opt.value)}
                              onChange={(e) =>
                                updateTaskOption(selectedTask.id, opt.key, e.target.value)
                              }
                              className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-[#141619] text-slate-900 dark:text-slate-100"
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
                      ok-script 状态机执行步骤
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

          {activeNav === 'triggers' && (
            <div className="max-w-5xl mx-auto space-y-4">
              <div>
                <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                  后台触发任务 (TriggerTask)
                </h2>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                  参照 YES-BD2 的触发式守护机制，在主任务空闲或阻塞时自动介入处理异常弹窗、网络重连与结算界面。
                </p>
              </div>

              <div className="bg-white dark:bg-[#1C1F24] border border-slate-200 dark:border-slate-800 rounded-xl divide-y divide-slate-200 dark:divide-slate-800">
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

          {activeNav === 'mappings' && (
            <div className="max-w-6xl mx-auto space-y-5">
              <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                  <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                    MaaNikke 流程到 ok-script 识别方案映射
                  </h2>
                  <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                    针对 MaaFramework 纯模板匹配易受动态背景与分辨率偏移影响的问题，改用局部 ROI + OCR 校验与 Python 状态机容错。
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <div className="relative">
                    <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      value={mappingQuery}
                      onChange={(e) => setMappingQuery(e.target.value)}
                      placeholder="搜索场景、节点或 ROI..."
                      className="pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-[#1C1F24] text-slate-900 dark:text-slate-100 w-56"
                    />
                  </div>
                  <div className="flex items-center gap-1 p-1 rounded-lg bg-slate-200/70 dark:bg-[#1C1F24] border border-slate-200 dark:border-slate-800">
                    {(['all', 'ocr', 'hybrid', 'template'] as const).map((mode) => (
                      <button
                        key={mode}
                        type="button"
                        onClick={() => setMappingModeFilter(mode)}
                        className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                          mappingModeFilter === mode
                            ? 'bg-white dark:bg-[#2A2F38] text-slate-900 dark:text-white'
                            : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                        }`}
                      >
                        {mode === 'all' ? '全部' : MODE_LABELS[mode]}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="bg-white dark:bg-[#1C1F24] border border-slate-200 dark:border-slate-800 rounded-xl overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-800 text-xs text-slate-500 dark:text-slate-400">
                      <th className="py-3 px-4 font-medium">游戏场景</th>
                      <th className="py-3 px-4 font-medium">MaaNikke 原节点与常见痛点</th>
                      <th className="py-3 px-4 font-medium">YES-NK (ok-script) 替代方案</th>
                      <th className="py-3 px-4 font-medium">ROI 相对区域与目标特征</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-sm">
                    {filteredMappings.length === 0 ? (
                      <tr>
                        <td
                          colSpan={4}
                          className="py-10 px-4 text-center text-sm text-slate-500 dark:text-slate-400"
                        >
                          没有匹配当前筛选条件的识别规则，请清空搜索词后重试。
                        </td>
                      </tr>
                    ) : (
                      filteredMappings.map((row) => (
                        <tr
                          key={row.id}
                          className="hover:bg-slate-50 dark:hover:bg-[#23272F] transition-colors align-top"
                        >
                          <td className="py-3.5 px-4 whitespace-nowrap">
                            <div className="font-medium text-slate-900 dark:text-white">
                              {row.scene}
                            </div>
                            <div className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                              {MODE_LABELS[row.mode]}
                            </div>
                          </td>
                          <td className="py-3.5 px-4 max-w-xs">
                            <div className="text-xs font-mono text-slate-700 dark:text-slate-300">
                              {row.maaNode}
                            </div>
                            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                              {row.maaPainPoint}
                            </p>
                          </td>
                          <td className="py-3.5 px-4 max-w-xs">
                            <div className="text-xs font-mono text-[#0067C0] dark:text-[#4CC2FF] leading-relaxed">
                              {row.okMethod}
                            </div>
                          </td>
                          <td className="py-3.5 px-4">
                            <div className="text-xs font-mono tabular-nums text-slate-700 dark:text-slate-300">
                              {row.roiBox}
                            </div>
                            <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                              {row.targetTextOrAsset}
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

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
                      当前没有可显示的运行日志。点击右上角“仿真运行已选任务”以观察状态机输出。
                    </p>
                    <button
                      type="button"
                      onClick={() => runTaskQueue(enabledTasks.slice(0, 2))}
                      className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium rounded-lg bg-[#0067C0] text-white hover:bg-[#005A9E] transition-colors"
                    >
                      <Play className="w-3.5 h-3.5" />
                      试运行前 2 个日常任务
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
                        <span className="text-slate-500 dark:text-slate-400 w-40 shrink-0 truncate">
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
                  客户端与识别引擎配置
                </h2>

                <div className="space-y-3.5 text-sm">
                  <div className="space-y-1">
                    <label className="text-xs text-slate-500 dark:text-slate-400">
                      目标服务器与运行环境
                    </label>
                    <select
                      value={settings.server}
                      onChange={(e) =>
                        setSettings((prev) => ({
                          ...prev,
                          server: e.target.value as ClientSettings['server'],
                        }))
                      }
                      className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-[#141619]"
                    >
                      <option value="国服 PC 端 (WeGame / 新的希望)">
                        国服 PC 端 (WeGame / 新的希望)
                      </option>
                      <option value="国际服 PC 端 (NIKKE Launcher)">
                        国际服 PC 端 (NIKKE Launcher)
                      </option>
                      <option value="安卓模拟器 (ADB)">安卓模拟器 (ADB)</option>
                    </select>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <label className="text-xs text-slate-500 dark:text-slate-400">
                        窗口标题匹配
                      </label>
                      <input
                        type="text"
                        value={settings.windowTitle}
                        onChange={(e) =>
                          setSettings((prev) => ({ ...prev, windowTitle: e.target.value }))
                        }
                        className="w-full px-3 py-2 text-sm font-mono rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-[#141619]"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs text-slate-500 dark:text-slate-400">
                        基准分辨率 (16:9)
                      </label>
                      <select
                        value={settings.resolution}
                        onChange={(e) =>
                          setSettings((prev) => ({
                            ...prev,
                            resolution: e.target.value as ClientSettings['resolution'],
                          }))
                        }
                        className="w-full px-3 py-2 text-sm font-mono rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-[#141619]"
                      >
                        <option value="1920x1080">1920x1080</option>
                        <option value="1600x900">1600x900</option>
                        <option value="1280x720">1280x720</option>
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <label className="text-xs text-slate-500 dark:text-slate-400">
                        截图采集通道
                      </label>
                      <select
                        value={settings.captureMethod}
                        onChange={(e) =>
                          setSettings((prev) => ({
                            ...prev,
                            captureMethod: e.target.value as ClientSettings['captureMethod'],
                          }))
                        }
                        className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-[#141619]"
                      >
                        <option value="WindowsGraphicsCapture">WindowsGraphicsCapture</option>
                        <option value="BitBlt">BitBlt</option>
                        <option value="ADB Screencap">ADB Screencap</option>
                      </select>
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs text-slate-500 dark:text-slate-400">
                        OCR 推理引擎
                      </label>
                      <select
                        value={settings.ocrEngine}
                        onChange={(e) =>
                          setSettings((prev) => ({
                            ...prev,
                            ocrEngine: e.target.value as ClientSettings['ocrEngine'],
                          }))
                        }
                        className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-[#141619]"
                      >
                        <option value="RapidOCR (ONNX)">RapidOCR (ONNX)</option>
                        <option value="PaddleOCR">PaddleOCR</option>
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <label className="text-xs text-slate-500 dark:text-slate-400">
                        OCR 置信度阈值
                      </label>
                      <input
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
                      <label className="text-xs text-slate-500 dark:text-slate-400">
                        模板匹配阈值
                      </label>
                      <input
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

                  <div className="pt-2 space-y-2.5 border-t border-slate-200 dark:border-slate-800">
                    <label className="flex items-center justify-between gap-3 cursor-pointer">
                      <span className="text-slate-700 dark:text-slate-300">
                        每个子任务前强制校验并返回大厅
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
                    <label className="flex items-center justify-between gap-3 cursor-pointer">
                      <span className="text-slate-700 dark:text-slate-300">
                        检测到鼠标人工介入时自动暂停任务
                      </span>
                      <input
                        type="checkbox"
                        checked={settings.pauseOnManualInput}
                        onChange={(e) =>
                          setSettings((prev) => ({
                            ...prev,
                            pauseOnManualInput: e.target.checked,
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
                  <h2 className="text-base font-semibold text-slate-900 dark:text-white">
                    配置预览 (yes_nk_config.json)
                  </h2>
                  <div className="flex items-center gap-2">
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

                <pre className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#141619] border border-slate-200 dark:border-slate-800 text-xs font-mono text-slate-700 dark:text-slate-300 overflow-auto max-h-[420px] leading-relaxed">
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
