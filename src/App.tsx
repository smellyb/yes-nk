import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Check,
  ChevronRight,
  Copy,
  Download,
  Monitor,
  Play,
  Settings,
  SlidersHorizontal,
  Trash2,
} from 'lucide-react';
import DesktopClonePanel from './components/DesktopClonePanel';
import HomePage, { HomeViewMode } from './components/HomePage';
import MappingsPanel from './components/MappingsPanel';
import ReportPage from './components/ReportPage';
import TaskPage from './components/TaskPage';
import YesSidebar from './components/YesSidebar';
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
  RunRecord,
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

export default function App() {
  const [darkMode, setDarkMode] = useState<boolean>(false);
  const [activeNav, setActiveNav] = useState<NavSection>('home');
  const [tasks, setTasks] = useState<AutomationTask[]>(INITIAL_TASKS);
  const [triggers, setTriggers] = useState<TriggerRule[]>(INITIAL_TRIGGERS);
  const [settings, setSettings] = useState<ClientSettings>(INITIAL_SETTINGS);
  const [desktopClone, setDesktopClone] = useState<DesktopCloneSettings>(INITIAL_DESKTOP_CLONE);
  const [selectedTaskId, setSelectedTaskId] = useState<string>(INITIAL_TASKS[0].id);

  // YES-BD2 HomePage options
  const [autorunEnabled, setAutorunEnabled] = useState<boolean>(false);
  const [autorunInClone, setAutorunInClone] = useState<boolean>(true);
  const [scheduleEnabled, setScheduleEnabled] = useState<boolean>(false);
  const [scheduleTime, setScheduleTime] = useState<string>('06:30');

  // Live run / summary / report state
  const [homeMode, setHomeMode] = useState<HomeViewMode>('idle');
  const [runQueue, setRunQueue] = useState<AutomationTask[]>([]);
  const [runningTaskId, setRunningTaskId] = useState<string | null>(null);
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const [elapsedSec, setElapsedSec] = useState<number>(0);
  const [taskStatuses, setTaskStatuses] = useState<Record<string, TaskStatus>>({});
  const [runRecords, setRunRecords] = useState<RunRecord[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([
    {
      id: 'init-1',
      timestamp: formatTime(new Date()),
      level: 'INFO',
      source: 'YES-NK',
      message:
        '已对齐 YES-BD2 淡紫/深色界面架构，内置 22 条 MaaNikke 转换流水线与 40 项实测 COCO 模板。',
    },
  ]);
  const [logFilter, setLogFilter] = useState<'ALL' | LogEntry['level']>('ALL');
  const [copiedConfig, setCopiedConfig] = useState<boolean>(false);

  const timersRef = useRef<number[]>([]);
  const clockRef = useRef<number | null>(null);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode);
  }, [darkMode]);

  useEffect(() => {
    return () => {
      timersRef.current.forEach((id) => window.clearTimeout(id));
      if (clockRef.current !== null) window.clearInterval(clockRef.current);
    };
  }, []);

  const enabledTasks = useMemo(() => tasks.filter((t) => t.enabled), [tasks]);
  const doneEnabledCount = useMemo(
    () => enabledTasks.filter((t) => taskStatuses[t.id] === 'completed').length,
    [enabledTasks, taskStatuses]
  );

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

  const clearTimers = () => {
    timersRef.current.forEach((id) => window.clearTimeout(id));
    timersRef.current = [];
    if (clockRef.current !== null) {
      window.clearInterval(clockRef.current);
      clockRef.current = null;
    }
  };

  const stopRun = () => {
    clearTimers();
    if (homeMode === 'running') {
      appendLog('WARN', 'DailyTask', '已手动停止运行并安全归位状态机。');
      setHomeMode('summary');
    }
    setRunningTaskId(null);
    setIsPaused(false);
  };

  const startQueue = (
    queue: AutomationTask[],
    via: RunRecord['via'] = '一键日常',
    inClone?: boolean
  ) => {
    if (queue.length === 0) {
      appendLog('WARN', 'DailyTask', '未启用任何任务，请至少勾选 1 项日常流水线。');
      return;
    }

    clearTimers();
    if (typeof inClone === 'boolean') {
      setDesktopClone((prev) => ({
        ...prev,
        run_mode: inClone ? 'desktop_clone' : prev.run_mode,
      }));
    }

    setActiveNav('home');
    setHomeMode('running');
    setRunQueue(queue);
    setRunningTaskId(queue[0].id);
    setIsPaused(false);
    setElapsedSec(0);

    clockRef.current = window.setInterval(() => {
      setElapsedSec((s) => s + 1);
    }, 1000);

    appendLog(
      'INFO',
      'ok.OK',
      `开始「${via}」：共 ${queue.length} 项 · 窗口 ${desktopClone.clientWidth}×${desktopClone.clientHeight}`
    );

    let delay = 250;
    queue.forEach((task) => {
      const startTimer = window.setTimeout(() => {
        setRunningTaskId(task.id);
        setTaskStatuses((prev) => ({ ...prev, [task.id]: 'running' }));
        appendLog('INFO', task.className, `开始执行：${task.name}`);
      }, delay);
      timersRef.current.push(startTimer);
      delay += 340;

      task.steps.slice(0, 2).forEach((step, idx) => {
        const stepTimer = window.setTimeout(() => {
          appendLog(idx % 2 === 0 ? 'OCR' : 'ACTION', task.className, step);
        }, delay);
        timersRef.current.push(stepTimer);
        delay += 280;
      });

      const doneTimer = window.setTimeout(() => {
        setTaskStatuses((prev) => ({ ...prev, [task.id]: 'completed' }));
        setRunRecords((prev) => [
          ...prev,
          {
            id: `${Date.now()}-${task.id}`,
            taskId: task.id,
            taskName: task.name,
            finishedAt: formatTime(new Date()),
            via,
            state: 'done',
            durationSec: task.estimatedSec,
          },
        ]);
        appendLog('INFO', task.className, `完成：${task.name}`);
      }, delay);
      timersRef.current.push(doneTimer);
      delay += 220;
    });

    const finishTimer = window.setTimeout(() => {
      if (clockRef.current !== null) {
        window.clearInterval(clockRef.current);
        clockRef.current = null;
      }
      setRunningTaskId(null);
      setHomeMode('summary');
      appendLog('INFO', 'DailyTask', `${via}全部执行完毕，已返回大厅。`);
    }, delay + 140);
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

  const applyPreset = (mode: 'basic' | 'all' | 'default') => {
    if (mode === 'basic') {
      setTasks((prev) => prev.map((t) => ({ ...t, enabled: BASIC_DAILY_IDS.has(t.id) })));
    } else if (mode === 'all') {
      setTasks((prev) => prev.map((t) => ({ ...t, enabled: true })));
    } else {
      setTasks(INITIAL_TASKS);
    }
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
      appendLog('WARN', 'Export', '剪贴板写入受限，请改用「下载配置」保存 yes_nk_config.json。');
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
    appendLog('INFO', 'Export', '已下载 yes_nk_config.json，放置仓库根目录即可被桌面客户端自动加载。');
  };

  const runningTaskName = useMemo(
    () => runQueue.find((t) => t.id === runningTaskId)?.name ?? null,
    [runQueue, runningTaskId]
  );
  const runFinishedCount = useMemo(
    () => runQueue.filter((t) => taskStatuses[t.id] === 'completed').length,
    [runQueue, taskStatuses]
  );

  const handleSidebarNav = (nav: NavSection) => {
    if (nav === 'home' && homeMode === 'summary') {
      setHomeMode('idle');
    }
    setActiveNav(nav);
  };

  return (
    <div className="min-h-screen md:h-screen md:overflow-hidden bg-[var(--yes-bg)] text-[var(--yes-ink)] p-2.5 sm:p-3 flex flex-col md:flex-row gap-3">
      {/* Left Floating Rounded Sidebar (YES-BD2 exact layout) */}
      <YesSidebar
        activeNav={activeNav}
        onSelectNav={handleSidebarNav}
        darkMode={darkMode}
        onChangeTheme={setDarkMode}
        doneCount={doneEnabledCount}
        enabledCount={enabledTasks.length}
        triggerEnabledCount={triggers.filter((t) => t.enabled).length}
        mappingCount={RECOGNITION_MAPPINGS.length}
        isRunning={homeMode === 'running'}
        runningTaskName={runningTaskName}
        runFinishedCount={runFinishedCount}
        runTotalCount={runQueue.length}
        settings={settings}
        desktopClone={desktopClone}
      />

      {/* Main Content Area (No cluttered top bar — YES-BD2 clean page header per screen) */}
      <main className="flex-1 min-w-0 px-3 sm:px-5 py-3 overflow-y-auto">
        {activeNav === 'home' && (
          <HomePage
            mode={homeMode}
            tasks={tasks}
            taskStatuses={taskStatuses}
            runQueue={runQueue}
            runningTaskId={runningTaskId}
            isPaused={isPaused}
            elapsedSec={elapsedSec}
            logs={logs}
            runRecords={runRecords}
            desktopClone={desktopClone}
            geometryVerdict={geometryVerdict}
            autorunEnabled={autorunEnabled}
            autorunInClone={autorunInClone}
            scheduleEnabled={scheduleEnabled}
            scheduleTime={scheduleTime}
            onToggleAutorun={setAutorunEnabled}
            onToggleAutorunClone={setAutorunInClone}
            onToggleSchedule={setScheduleEnabled}
            onChangeScheduleTime={setScheduleTime}
            onToggleTask={toggleTaskEnabled}
            onOpenTaskDetail={(id) => {
              setSelectedTaskId(id);
              setActiveNav('tasks');
            }}
            onStartDaily={(inClone) =>
              startQueue(enabledTasks, inClone ? '桌面分身' : '一键日常', inClone)
            }
            onTogglePause={() => setIsPaused((p) => !p)}
            onStopRun={stopRun}
            onLeaveSummary={() => setHomeMode('idle')}
            onNavigate={setActiveNav}
          />
        )}

        {activeNav === 'report' && (
          <ReportPage
            records={runRecords}
            onStartDaily={() => startQueue(enabledTasks, '一键日常')}
          />
        )}

        {activeNav === 'tasks' && (
          <TaskPage
            tasks={tasks}
            selectedTaskId={selectedTaskId}
            taskStatuses={taskStatuses}
            onSelectTask={setSelectedTaskId}
            onToggleTask={toggleTaskEnabled}
            onMoveTask={moveTask}
            onUpdateOption={updateTaskOption}
            onRunSingle={(task) => startQueue([task], '单项运行')}
            onStartDaily={() => startQueue(enabledTasks, '一键日常')}
            onApplyPreset={applyPreset}
          />
        )}

        {activeNav === 'desktop' && (
          <DesktopClonePanel
            desktopClone={desktopClone}
            onChange={setDesktopClone}
            onApplyResolution={(res) => setSettings((prev) => ({ ...prev, resolution: res }))}
          />
        )}

        {activeNav === 'triggers' && (
          <div className="max-w-4xl mx-auto space-y-5">
            <header className="space-y-0.5">
              <h1 className="text-[23px] font-bold text-[var(--yes-ink)] tracking-tight">
                触发守护
              </h1>
              <p className="text-[13px] text-[var(--yes-ink2)]">
                对应 yes_nk/tasks/PopupGuardTrigger.py，在主任务空闲或阻塞时自动介入处理断线重连与限时弹窗
              </p>
            </header>

            <section className="yes-card px-5 py-2 divide-y divide-[var(--yes-line)]">
              {triggers.map((tr) => (
                <div
                  key={tr.id}
                  className="py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                >
                  <div className="space-y-1 max-w-2xl">
                    <div className="flex items-center gap-2">
                      <span className="text-[14px] font-medium text-[var(--yes-ink)]">
                        {tr.name}
                      </span>
                      <span className="text-xs font-mono text-[var(--yes-ink3)]">
                        {tr.className}
                      </span>
                    </div>
                    <p className="text-[13px] text-[var(--yes-ink2)]">{tr.description}</p>
                    <div className="text-xs text-[var(--yes-ink3)] flex items-center gap-1">
                      <ChevronRight className="w-3.5 h-3.5" />
                      <span>触发动作：{tr.actionSummary}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 shrink-0">
                    <label className="flex items-center gap-2 text-xs text-[var(--yes-ink3)]">
                      <span>轮询间隔</span>
                      <input
                        type="number"
                        step={100}
                        min={200}
                        max={10000}
                        value={tr.intervalMs}
                        onChange={(e) => updateTriggerInterval(tr.id, Number(e.target.value))}
                        className="w-20 h-8 px-2.5 text-right font-mono tabular-nums rounded-full bg-[var(--yes-fill)] text-[var(--yes-ink)] border-none outline-none"
                      />
                      <span className="font-mono">ms</span>
                    </label>

                    <button
                      type="button"
                      role="switch"
                      aria-checked={tr.enabled}
                      aria-label={`启用或停用 ${tr.name}`}
                      onClick={() => toggleTrigger(tr.id)}
                      className={`w-11 h-[26px] rounded-full transition-colors relative cursor-pointer ${
                        tr.enabled ? 'bg-[var(--yes-primary)]' : 'bg-[var(--yes-well2)]'
                      }`}
                    >
                      <span
                        className={`block w-5 h-5 rounded-full bg-white shadow-xs transition-transform ${
                          tr.enabled ? 'translate-x-[21px]' : 'translate-x-[3px]'
                        }`}
                      />
                    </button>
                  </div>
                </div>
              ))}
            </section>
          </div>
        )}

        {activeNav === 'mappings' && <MappingsPanel mappings={RECOGNITION_MAPPINGS} />}

        {activeNav === 'logs' && (
          <div className="max-w-5xl mx-auto space-y-5">
            <header className="flex flex-wrap items-center justify-between gap-4">
              <div className="space-y-0.5">
                <h1 className="text-[23px] font-bold text-[var(--yes-ink)] tracking-tight">
                  运行日志
                </h1>
                <p className="text-[13px] text-[var(--yes-ink2)]">
                  实时记录状态机流转、OCR 识别与动作点击历史
                </p>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1 p-1 rounded-full bg-[var(--yes-well)]">
                  {(['ALL', 'INFO', 'OCR', 'ACTION', 'WARN'] as const).map((lvl) => (
                    <button
                      key={lvl}
                      type="button"
                      onClick={() => setLogFilter(lvl)}
                      className={`h-7 px-3 text-xs font-mono rounded-full transition-colors cursor-pointer whitespace-nowrap ${
                        logFilter === lvl
                          ? 'bg-[var(--yes-raised)] text-[var(--yes-ink)] shadow-xs font-medium'
                          : 'text-[var(--yes-ink2)] hover:text-[var(--yes-ink)]'
                      }`}
                    >
                      {lvl}
                    </button>
                  ))}
                </div>
                <button
                  type="button"
                  onClick={() => setLogs([])}
                  className="inline-flex items-center gap-1.5 h-8 px-3.5 text-xs rounded-full bg-[var(--yes-fill)] hover:bg-[var(--yes-fill-hover)] text-[var(--yes-ink)] transition-colors cursor-pointer"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  清空日志
                </button>
              </div>
            </header>

            <section className="yes-card overflow-hidden">
              {filteredLogs.length === 0 ? (
                <div className="py-12 px-4 text-center space-y-3">
                  <p className="text-sm text-[var(--yes-ink3)]">
                    暂无运行日志。点击下方按钮试跑前 2 项任务查看日志输出。
                  </p>
                  <button
                    type="button"
                    onClick={() => startQueue(enabledTasks.slice(0, 2), '一键日常')}
                    className="inline-flex items-center gap-1.5 h-9 px-4 text-xs rounded-full bg-[var(--yes-primary)] hover:bg-[var(--yes-primary-hover)] text-white transition-colors cursor-pointer"
                  >
                    <Play className="w-3.5 h-3.5 fill-current" />
                    试运行前 2 项任务
                  </button>
                </div>
              ) : (
                <div className="divide-y divide-[var(--yes-line)] font-mono text-xs">
                  {filteredLogs.map((entry) => (
                    <div
                      key={entry.id}
                      className="px-5 py-2.5 flex items-baseline gap-3 hover:bg-[var(--yes-inset)]"
                    >
                      <span className="tabular-nums text-[var(--yes-ink3)] shrink-0">
                        {entry.timestamp}
                      </span>
                      <span
                        className={`w-14 shrink-0 font-semibold ${
                          entry.level === 'WARN'
                            ? 'text-[var(--yes-warn)]'
                            : entry.level === 'OCR'
                            ? 'text-[var(--yes-primary)]'
                            : entry.level === 'ACTION'
                            ? 'text-[var(--yes-ok)]'
                            : 'text-[var(--yes-ink2)]'
                        }`}
                      >
                        {entry.level}
                      </span>
                      <span className="text-[var(--yes-ink3)] w-36 shrink-0 truncate">
                        {entry.source}
                      </span>
                      <span className="text-[var(--yes-ink)] font-sans text-[13px] leading-relaxed">
                        {entry.message}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>
        )}

        {activeNav === 'settings' && (
          <div className="max-w-5xl mx-auto space-y-5">
            <header className="space-y-0.5">
              <h1 className="text-[23px] font-bold text-[var(--yes-ink)] tracking-tight">设置</h1>
              <p className="text-[13px] text-[var(--yes-ink2)]">
                国服客户端参数、识别阈值与 yes_nk_config.json 配置导出（与桌面端双向互通）
              </p>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
              {/* Left HubRow Settings Card */}
              <section className="lg:col-span-6 yes-card px-5 py-2 divide-y divide-[var(--yes-line)]">
                <div className="py-3.5 flex items-center gap-3">
                  <span className="w-8 h-8 rounded-full bg-[var(--yes-accent-soft)] text-[var(--yes-primary)] flex items-center justify-center shrink-0">
                    <Monitor className="w-4 h-4" />
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="text-[14px] text-[var(--yes-ink)]">目标客户端与交互后端</div>
                    <div className="text-xs text-[var(--yes-ink3)] truncate">
                      {settings.server} · {resolveInteractionBackend(desktopClone.run_mode)}
                    </div>
                  </div>
                </div>

                <div className="py-3.5 flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="w-8 h-8 rounded-full bg-[var(--yes-accent-soft)] text-[var(--yes-primary)] flex items-center justify-center shrink-0">
                      <Settings className="w-4 h-4" />
                    </span>
                    <div>
                      <label htmlFor="setting-window-title" className="text-[14px] text-[var(--yes-ink)]">
                        游戏窗口标题
                      </label>
                      <div className="text-xs text-[var(--yes-ink3)]">用于自动定位国服窗口句柄</div>
                    </div>
                  </div>
                  <input
                    id="setting-window-title"
                    type="text"
                    value={settings.windowTitle}
                    onChange={(e) =>
                      setSettings((prev) => ({ ...prev, windowTitle: e.target.value }))
                    }
                    className="w-36 h-8 px-3 text-xs font-mono rounded-full bg-[var(--yes-fill)] text-[var(--yes-ink)] border-none outline-none"
                  />
                </div>

                <div className="py-3.5 flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="w-8 h-8 rounded-full bg-[var(--yes-accent-soft)] text-[var(--yes-primary)] flex items-center justify-center shrink-0">
                      <Monitor className="w-4 h-4" />
                    </span>
                    <div>
                      <label htmlFor="setting-resolution" className="text-[14px] text-[var(--yes-ink)]">
                        16:9 目标客户区
                      </label>
                      <div className="text-xs text-[var(--yes-ink3)]">桌面分身自动 1920×1080</div>
                    </div>
                  </div>
                  <select
                    id="setting-resolution"
                    value={settings.resolution}
                    onChange={(e) => {
                      const nextRes = e.target.value as ClientSettings['resolution'];
                      setSettings((prev) => ({ ...prev, resolution: nextRes }));
                      const [w, h] = nextRes.split('x').map(Number);
                      setDesktopClone((prev) => ({ ...prev, clientWidth: w, clientHeight: h }));
                    }}
                    className="h-8 px-3 text-xs font-mono rounded-full bg-[var(--yes-fill)] text-[var(--yes-ink)] border-none outline-none cursor-pointer"
                  >
                    <option value="1920x1080">1920×1080</option>
                    <option value="1600x900">1600×900</option>
                    <option value="1280x720">1280×720</option>
                  </select>
                </div>

                <div className="py-3.5 flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="w-8 h-8 rounded-full bg-[var(--yes-accent-soft)] text-[var(--yes-primary)] flex items-center justify-center shrink-0">
                      <SlidersHorizontal className="w-4 h-4" />
                    </span>
                    <div>
                      <label htmlFor="setting-ocr-conf" className="text-[14px] text-[var(--yes-ink)]">
                        OCR 置信度 / 模板阈值
                      </label>
                      <div className="text-xs text-[var(--yes-ink3)]">RapidOCR & COCO 匹配门槛</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <input
                      id="setting-ocr-conf"
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
                      className="w-16 h-8 px-2 text-right text-xs font-mono tabular-nums rounded-full bg-[var(--yes-fill)] text-[var(--yes-ink)] border-none outline-none"
                    />
                    <input
                      aria-label="COCO 模板阈值"
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
                      className="w-16 h-8 px-2 text-right text-xs font-mono tabular-nums rounded-full bg-[var(--yes-fill)] text-[var(--yes-ink)] border-none outline-none"
                    />
                  </div>
                </div>
              </section>

              {/* Right JSON Export Card */}
              <section className="lg:col-span-6 yes-card p-5 space-y-3">
                <div className="flex items-center justify-between gap-2">
                  <h2 className="text-[15px] font-semibold text-[var(--yes-ink)]">
                    yes_nk_config.json
                  </h2>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={handleCopyConfig}
                      className="inline-flex items-center gap-1 h-8 px-3 rounded-full text-xs bg-[var(--yes-fill)] hover:bg-[var(--yes-fill-hover)] text-[var(--yes-ink)] transition-colors cursor-pointer"
                    >
                      {copiedConfig ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-[var(--yes-ok)]" />
                          已复制
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5" />
                          复制
                        </>
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={handleDownloadConfig}
                      className="inline-flex items-center gap-1 h-8 px-3.5 rounded-full text-xs bg-[var(--yes-primary)] hover:bg-[var(--yes-primary-hover)] text-white transition-colors cursor-pointer"
                    >
                      <Download className="w-3.5 h-3.5" />
                      下载配置
                    </button>
                  </div>
                </div>
                <pre className="p-3.5 rounded-[14px] bg-[var(--yes-inset)] text-xs font-mono text-[var(--yes-ink2)] overflow-auto max-h-[340px] leading-relaxed">
                  {exportedConfigJson}
                </pre>
              </section>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
