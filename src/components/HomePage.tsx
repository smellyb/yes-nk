import {
  Check,
  CheckCircle2,
  Circle,
  Clock,
  ListChecks,
  Loader2,
  Monitor,
  Pause,
  Play,
  ShieldCheck,
  Sparkles,
  Square,
  Swords,
  ShoppingBag,
  Gift,
  Users,
  XCircle,
} from 'lucide-react';
import {
  AutomationTask,
  DesktopCloneSettings,
  GeometryVerdict,
  LogEntry,
  NavSection,
  RunRecord,
  TaskStatus,
} from '../types';
import {
  computeRunSummaryStats,
  formatDurationClock,
  partitionDailyAndWeeklyTasks,
} from '../utils/workbenchLogic';

export type HomeViewMode = 'idle' | 'running' | 'summary';

interface HomePageProps {
  mode: HomeViewMode;
  tasks: AutomationTask[];
  taskStatuses: Record<string, TaskStatus>;
  runQueue: AutomationTask[];
  runningTaskId: string | null;
  isPaused: boolean;
  elapsedSec: number;
  logs: LogEntry[];
  runRecords: RunRecord[];
  desktopClone: DesktopCloneSettings;
  geometryVerdict: GeometryVerdict;
  autorunEnabled: boolean;
  autorunInClone: boolean;
  scheduleEnabled: boolean;
  scheduleTime: string;
  onToggleAutorun: (val: boolean) => void;
  onToggleAutorunClone: (val: boolean) => void;
  onToggleSchedule: (val: boolean) => void;
  onChangeScheduleTime: (time: string) => void;
  onToggleTask: (taskId: string) => void;
  onOpenTaskDetail: (taskId: string) => void;
  onStartDaily: (inClone: boolean) => void;
  onTogglePause: () => void;
  onStopRun: () => void;
  onLeaveSummary: () => void;
  onNavigate: (nav: NavSection) => void;
}

function getCategoryIcon(category: AutomationTask['category']) {
  switch (category) {
    case '启动与奖励':
      return Gift;
    case '商店相关':
      return ShoppingBag;
    case '日常养成':
      return Sparkles;
    case '副本挑战':
      return Swords;
    case '联盟与活动':
      return Users;
  }
}

function getTodayHeaderText(): string {
  const now = new Date();
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
  return `${now.getMonth() + 1}月${now.getDate()}日 ${weekdays[now.getDay()]} · 下次刷新 明天 05:00`;
}

export default function HomePage({
  mode,
  tasks,
  taskStatuses,
  runQueue,
  runningTaskId,
  isPaused,
  elapsedSec,
  logs,
  runRecords,
  desktopClone,
  geometryVerdict,
  autorunEnabled,
  autorunInClone,
  scheduleEnabled,
  scheduleTime,
  onToggleAutorun,
  onToggleAutorunClone,
  onToggleSchedule,
  onChangeScheduleTime,
  onToggleTask,
  onOpenTaskDetail,
  onStartDaily,
  onTogglePause,
  onStopRun,
  onLeaveSummary,
  onNavigate,
}: HomePageProps) {
  const enabledTasks = tasks.filter((t) => t.enabled);
  const doneEnabledCount = enabledTasks.filter((t) => taskStatuses[t.id] === 'completed').length;
  const remainingCount = Math.max(0, enabledTasks.length - doneEnabledCount);
  const estimatedMin = Math.max(
    1,
    Math.ceil(
      enabledTasks
        .filter((t) => taskStatuses[t.id] !== 'completed')
        .reduce((sum, t) => sum + t.estimatedSec, 0) / 60
    )
  );

  const { daily, weeklyOrEvent } = partitionDailyAndWeeklyTasks(tasks);

  // SVG Ring geometry (118px diameter, 11px stroke — exact YES-BD2 Ring(118, 11))
  const ringSize = 118;
  const strokeWidth = 11;
  const radius = (ringSize - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progressRatio = enabledTasks.length > 0 ? doneEnabledCount / enabledTasks.length : 0;
  const strokeDashoffset = circumference * (1 - progressRatio);

  const renderBoardTile = (task: AutomationTask) => {
    const Icon = getCategoryIcon(task.category);
    const status = taskStatuses[task.id] ?? 'idle';
    const isDone = status === 'completed';

    return (
      <div
        key={task.id}
        className="yes-card p-3.5 flex flex-col justify-between gap-2.5 transition-transform duration-150 hover:-translate-y-0.5"
      >
        <div className="flex items-center justify-between gap-2">
          <div
            className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
              task.enabled
                ? 'bg-[var(--yes-accent-soft)] text-[var(--yes-primary)]'
                : 'bg-[var(--yes-well)] text-[var(--yes-ink3)]'
            }`}
          >
            <Icon className="w-4 h-4" />
          </div>
          <input
            type="checkbox"
            aria-label={`勾选 ${task.name} 加入一键日常`}
            checked={task.enabled}
            onChange={() => onToggleTask(task.id)}
            className="w-4 h-4 rounded accent-[var(--yes-primary)] cursor-pointer"
          />
        </div>

        <button
          type="button"
          onClick={() => onOpenTaskDetail(task.id)}
          className="text-left space-y-1 cursor-pointer group"
        >
          <div
            className={`text-[13px] font-medium leading-snug line-clamp-2 group-hover:text-[var(--yes-primary)] transition-colors ${
              task.enabled ? 'text-[var(--yes-ink)]' : 'text-[var(--yes-ink3)]'
            }`}
          >
            {task.name}
          </div>
          <div className="flex items-center gap-1 text-[11px]">
            {isDone ? (
              <>
                <CheckCircle2 className="w-3.5 h-3.5 text-[var(--yes-ok)] shrink-0" />
                <span className="text-[var(--yes-ok)]">已完成</span>
              </>
            ) : !task.enabled ? (
              <span className="text-[var(--yes-ink3)]">不在一键日常里</span>
            ) : (
              <span className="text-[var(--yes-ink3)]">未完成</span>
            )}
          </div>
        </button>
      </div>
    );
  };

  // ======================================================== RUNNING MODE
  if (mode === 'running') {
    const stats = computeRunSummaryStats(runQueue, taskStatuses);
    const currentTask = runQueue.find((t) => t.id === runningTaskId) ?? runQueue[0];
    const recentLogs = logs.slice(-3);

    return (
      <div className="max-w-5xl mx-auto space-y-4">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="text-xs text-[var(--yes-ink3)]">一键完成日常</div>
            <h1 className="text-[23px] font-bold text-[var(--yes-ink)] tracking-tight">
              {isPaused ? '已暂停' : currentTask ? `正在跑：${currentTask.name}` : '正在运行'}
            </h1>
            <p className="text-[13px] text-[var(--yes-ink2)]">
              {desktopClone.run_mode === 'desktop_clone'
                ? '在独立 1920×1080 桌面分身中执行，主桌面键鼠不受干扰'
                : '在主桌面通过 ok-script 状态机执行'}
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={onTogglePause}
              className="inline-flex items-center gap-1.5 h-9 px-4 rounded-full text-[13px] bg-[var(--yes-fill)] hover:bg-[var(--yes-fill-hover)] text-[var(--yes-ink)] transition-colors cursor-pointer whitespace-nowrap"
            >
              {isPaused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
              {isPaused ? '继续' : '暂停'}
            </button>
            <button
              type="button"
              onClick={onStopRun}
              className="inline-flex items-center gap-1.5 h-9 px-4 rounded-full text-[13px] bg-[var(--yes-bad-soft)] text-[var(--yes-bad)] hover:opacity-90 transition-opacity cursor-pointer whitespace-nowrap"
            >
              <Square className="w-3.5 h-3.5" />
              停止
            </button>
          </div>
        </header>

        {/* SegBar Progress Card */}
        <section className="yes-card p-5 space-y-3" aria-label="运行进度条">
          <div className="flex items-center gap-1 h-2.5">
            {runQueue.map((item) => {
              const st = taskStatuses[item.id] ?? 'idle';
              const barColor =
                st === 'completed'
                  ? 'bg-[var(--yes-ok)]'
                  : st === 'running'
                  ? 'bg-[var(--yes-primary)]'
                  : st === 'failed'
                  ? 'bg-[var(--yes-bad)]'
                  : 'bg-[var(--yes-well)]';
              return (
                <div
                  key={item.id}
                  title={item.name}
                  className={`flex-1 h-full rounded-full transition-colors duration-200 ${barColor}`}
                />
              );
            })}
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2 text-[13px] text-[var(--yes-ink2)]">
            <span className="tabular-nums">
              {stats.done} / {runQueue.length} 完成
              {stats.skipped > 0 ? ` · ${stats.skipped} 项跳过` : ''}
            </span>
            <span className="font-mono tabular-nums">
              已运行 {formatDurationClock(elapsedSec)}
            </span>
          </div>
        </section>

        {/* 2-Column Body: LiveView + Timeline */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
          <section className="lg:col-span-7 yes-card p-4 space-y-4">
            <div className="relative aspect-video rounded-[14px] bg-[var(--yes-shot)] overflow-hidden flex flex-col items-center justify-center p-6 text-center">
              <span className="absolute top-3 left-3 px-2 py-0.5 rounded bg-black/55 text-white text-[11px]">
                实时画面 · {desktopClone.clientWidth}×{desktopClone.clientHeight}
              </span>
              <Monitor className="w-10 h-10 text-white/40 mb-2" />
              <div className="text-sm font-medium text-white/90">
                {currentTask?.name ?? '等待游戏画面帧'}
              </div>
              <div className="mt-1 text-xs text-white/60 max-w-md">
                {currentTask?.steps[0] ?? 'ok-script WGC / BitBlt 正在捕捉 16:9 画面并运行 RapidOCR + COCO 识别'}
              </div>
            </div>

            {currentTask && (
              <div className="flex items-center justify-between gap-3 px-1">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-10 h-10 rounded-full bg-[var(--yes-accent-soft)] text-[var(--yes-primary)] flex items-center justify-center shrink-0">
                    <Loader2 className={`w-5 h-5 ${isPaused ? '' : 'animate-spin'}`} />
                  </div>
                  <div className="min-w-0">
                    <div className="text-[15px] font-semibold text-[var(--yes-ink)] truncate">
                      {currentTask.name}
                    </div>
                    <div className="text-xs text-[var(--yes-ink2)] truncate">
                      {currentTask.className} · {currentTask.pythonModule}
                    </div>
                  </div>
                </div>
                <div className="text-2xl font-bold font-mono tabular-nums text-[var(--yes-primary)] shrink-0">
                  {formatDurationClock(elapsedSec)}
                </div>
              </div>
            )}

            <div className="border-t border-[var(--yes-line)] pt-3 space-y-1.5">
              {recentLogs.map((entry) => (
                <div
                  key={entry.id}
                  className="text-xs text-[var(--yes-ink3)] truncate font-mono tabular-nums"
                >
                  {entry.timestamp} [{entry.source}] {entry.message}
                </div>
              ))}
            </div>
          </section>

          <section className="lg:col-span-5 yes-card p-3.5 divide-y divide-[var(--yes-line)]">
            {runQueue.map((item) => {
              const st = taskStatuses[item.id] ?? 'idle';
              const active = st === 'running';
              return (
                <div
                  key={item.id}
                  className={`px-2.5 py-2 flex items-center justify-between gap-2.5 rounded-[10px] ${
                    active ? 'bg-[var(--yes-row-on)]' : ''
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    {st === 'completed' ? (
                      <CheckCircle2 className="w-4 h-4 text-[var(--yes-ok)] shrink-0" />
                    ) : st === 'running' ? (
                      <Loader2 className="w-4 h-4 text-[var(--yes-primary)] animate-spin shrink-0" />
                    ) : st === 'failed' ? (
                      <XCircle className="w-4 h-4 text-[var(--yes-bad)] shrink-0" />
                    ) : (
                      <Circle className="w-4 h-4 text-[var(--yes-skip)] shrink-0" />
                    )}
                    <span
                      className={`text-[13px] truncate ${
                        st === 'idle' ? 'text-[var(--yes-ink3)]' : 'text-[var(--yes-ink)]'
                      }`}
                    >
                      {item.name}
                    </span>
                  </div>
                  <span className="text-xs font-mono tabular-nums text-[var(--yes-ink3)] shrink-0">
                    {formatDurationClock(item.estimatedSec)}
                  </span>
                </div>
              );
            })}
          </section>
        </div>
      </div>
    );
  }

  // ======================================================== SUMMARY MODE
  if (mode === 'summary') {
    const stats = computeRunSummaryStats(runQueue, taskStatuses);
    return (
      <div className="max-w-5xl mx-auto space-y-5">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-[23px] font-bold text-[var(--yes-ink)] tracking-tight">
              跑完了
            </h1>
            <p className="text-[13px] text-[var(--yes-ink2)]">
              本次共运行 {runQueue.length} 项日常流水线，结果已同步写入今日报表
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onNavigate('logs')}
              className="h-9 px-4 rounded-full text-[13px] bg-[var(--yes-fill)] hover:bg-[var(--yes-fill-hover)] text-[var(--yes-ink)] transition-colors cursor-pointer whitespace-nowrap"
            >
              看运行日志
            </button>
            <button
              type="button"
              onClick={onLeaveSummary}
              className="h-9 px-4 rounded-full text-[13px] bg-[var(--yes-primary)] hover:bg-[var(--yes-primary-hover)] text-white transition-colors cursor-pointer whitespace-nowrap"
            >
              回首页
            </button>
          </div>
        </header>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="yes-card p-4">
            <div className="text-xs text-[var(--yes-ink3)]">总用时</div>
            <div className="mt-1 text-2xl font-bold font-mono tabular-nums text-[var(--yes-ink)]">
              {formatDurationClock(elapsedSec)}
            </div>
          </div>
          <div className="yes-card p-4">
            <div className="text-xs text-[var(--yes-ink3)]">完成</div>
            <div className="mt-1 text-2xl font-bold font-mono tabular-nums text-[var(--yes-ok)]">
              {stats.done}
            </div>
          </div>
          <div className="yes-card p-4">
            <div className="text-xs text-[var(--yes-ink3)]">跳过</div>
            <div className="mt-1 text-2xl font-bold font-mono tabular-nums text-[var(--yes-ink2)]">
              {stats.skipped}
            </div>
          </div>
          <div className="yes-card p-4">
            <div className="text-xs text-[var(--yes-ink3)]">失败</div>
            <div className="mt-1 text-2xl font-bold font-mono tabular-nums text-[var(--yes-bad)]">
              {stats.failed}
            </div>
          </div>
        </div>

        <section className="yes-card p-4 divide-y divide-[var(--yes-line)]">
          {runQueue.map((item) => {
            const st = taskStatuses[item.id] ?? 'completed';
            return (
              <div key={item.id} className="py-2.5 px-2 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2.5 min-w-0">
                  <CheckCircle2 className="w-4 h-4 text-[var(--yes-ok)] shrink-0" />
                  <span className="text-[14px] text-[var(--yes-ink)] truncate">{item.name}</span>
                </div>
                <span className="text-xs font-mono tabular-nums text-[var(--yes-ink3)]">
                  {st === 'completed' ? '完成' : '跳过'} · {formatDurationClock(item.estimatedSec)}
                </span>
              </div>
            );
          })}
        </section>
      </div>
    );
  }

  // ======================================================== IDLE MODE (DEFAULT)
  const reportDone = runRecords.filter((r) => r.state === 'done').length;
  const reportFailed = runRecords.filter((r) => r.state === 'fail').length;
  const reportRatio = runRecords.length > 0 ? Math.round((reportDone / runRecords.length) * 100) : 0;

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      {/* Page Header */}
      <header className="space-y-0.5">
        <h1 className="text-[23px] font-bold text-[var(--yes-ink)] tracking-tight">今天</h1>
        <p className="text-[13px] text-[var(--yes-ink2)]">{getTodayHeaderText()}</p>
      </header>

      {/* Hero Card: Ring + Title/Sub + Start Buttons & Autorun Checkboxes */}
      <section className="yes-card px-6 py-5 flex flex-col md:flex-row items-center gap-6">
        {/* 118px Circular Progress Ring */}
        <div className="relative w-[118px] h-[118px] shrink-0">
          <svg width={ringSize} height={ringSize} className="-rotate-90">
            <circle
              cx={ringSize / 2}
              cy={ringSize / 2}
              r={radius}
              fill="none"
              stroke="var(--yes-well)"
              strokeWidth={strokeWidth}
            />
            <circle
              cx={ringSize / 2}
              cy={ringSize / 2}
              r={radius}
              fill="none"
              stroke="var(--yes-primary)"
              strokeWidth={strokeWidth}
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              className="transition-all duration-300"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-[26px] font-bold leading-none font-mono tabular-nums text-[var(--yes-ink)]">
              {doneEnabledCount}
            </span>
            <span className="mt-1 text-xs font-mono tabular-nums text-[var(--yes-ink3)]">
              / {enabledTasks.length}
            </span>
          </div>
        </div>

        {/* Middle Copy */}
        <div className="flex-1 min-w-0 text-center md:text-left space-y-1">
          <div className="text-xs text-[var(--yes-ink3)]">今日日常</div>
          <h2 className="text-[28px] font-bold leading-tight text-[var(--yes-ink)]">
            {enabledTasks.length === 0
              ? '一键日常里没有项目'
              : remainingCount > 0
              ? `还剩 ${remainingCount} 项`
              : '今天的日常都做完了'}
          </h2>
          <p className="text-[13px] text-[var(--yes-ink2)]">
            {enabledTasks.length === 0
              ? '到「任务设定」或下方勾选要跑的国服日常项目'
              : remainingCount > 0
              ? `预计 ${estimatedMin} 分钟（已转换 Shinarin/MaaNikke 全部 22 条流水线）`
              : '明天 05:00 自动刷新，可在今日报表查看明细'}
          </p>
          <div className="pt-2">
            <button
              type="button"
              onClick={() => onNavigate('report')}
              className="inline-flex items-center gap-1.5 h-8 px-3.5 rounded-full text-[13px] bg-[var(--yes-fill)] hover:bg-[var(--yes-fill-hover)] text-[var(--yes-ink)] transition-colors cursor-pointer whitespace-nowrap"
            >
              <ListChecks className="w-3.5 h-3.5" />
              看今日报表
            </button>
          </div>
        </div>

        {/* Right Action Column */}
        <div className="flex flex-col items-stretch gap-2 w-full md:w-[196px] shrink-0">
          <button
            type="button"
            disabled={enabledTasks.length === 0}
            onClick={() => onStartDaily(false)}
            className="inline-flex items-center justify-center gap-2 h-10 px-5 rounded-full text-sm font-medium bg-[var(--yes-primary)] hover:bg-[var(--yes-primary-hover)] disabled:opacity-40 text-white transition-colors cursor-pointer whitespace-nowrap"
          >
            <Play className="w-4 h-4 fill-current" />
            一键完成日常
          </button>
          <button
            type="button"
            disabled={enabledTasks.length === 0}
            onClick={() => onStartDaily(true)}
            className="inline-flex items-center justify-center gap-2 h-9 px-4 rounded-full text-[13px] bg-[var(--yes-fill)] hover:bg-[var(--yes-fill-hover)] disabled:opacity-40 text-[var(--yes-ink)] transition-colors cursor-pointer whitespace-nowrap"
          >
            <Monitor className="w-3.5 h-3.5" />
            在桌面分身跑
          </button>

          <div className="pt-1.5 pl-1 space-y-1.5 text-xs">
            <label className="flex items-center gap-2 text-[var(--yes-ink)] cursor-pointer select-none">
              <input
                type="checkbox"
                checked={autorunEnabled}
                onChange={(e) => onToggleAutorun(e.target.checked)}
                className="w-4 h-4 rounded accent-[var(--yes-primary)] cursor-pointer"
              />
              <span>打开就自动跑日常</span>
            </label>
            <label
              className={`flex items-center gap-2 select-none ${
                autorunEnabled
                  ? 'text-[var(--yes-ink)] cursor-pointer'
                  : 'text-[var(--yes-ink3)] opacity-60 cursor-not-allowed'
              }`}
            >
              <input
                type="checkbox"
                disabled={!autorunEnabled}
                checked={autorunInClone}
                onChange={(e) => onToggleAutorunClone(e.target.checked)}
                className="w-4 h-4 rounded accent-[var(--yes-primary)]"
              />
              <span>在桌面分身跑</span>
            </label>
          </div>
        </div>
      </section>

      {/* 3-Column Stat Row (matching YES-BD2 StatCard + ScheduleCard) */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-3.5" aria-label="快捷状态统计">
        {/* Card 1: 今日报表 */}
        <button
          type="button"
          onClick={() => onNavigate('report')}
          className="yes-card p-4 text-left space-y-2.5 transition-transform duration-150 hover:-translate-y-0.5 cursor-pointer"
        >
          <div className="flex items-center gap-2">
            <span className="w-7 h-7 rounded-full bg-[var(--yes-accent-soft)] text-[var(--yes-primary)] flex items-center justify-center shrink-0">
              <ListChecks className="w-4 h-4" />
            </span>
            <span className="text-[13px] text-[var(--yes-ink2)]">今日报表</span>
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-[26px] font-bold leading-none font-mono tabular-nums text-[var(--yes-ink)]">
              {runRecords.length > 0 ? runRecords.length : '-'}
            </span>
            <span className="text-xs text-[var(--yes-ink3)]">
              {runRecords.length > 0 ? '项已记录' : '今天还没跑'}
            </span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-[var(--yes-well)] overflow-hidden">
            <div
              className="h-full rounded-full bg-[var(--yes-primary)] transition-all"
              style={{ width: `${reportRatio}%` }}
            />
          </div>
          <div className="text-xs text-[var(--yes-ink3)] truncate">
            {runRecords.length > 0
              ? `完成 ${reportDone} 项 · 失败 ${reportFailed} 项 · 点这里看全部`
              : '跑完会在这里看到今天的结果'}
          </div>
        </button>

        {/* Card 2: 桌面分身 */}
        <button
          type="button"
          onClick={() => onNavigate('desktop')}
          className="yes-card p-4 text-left space-y-2.5 transition-transform duration-150 hover:-translate-y-0.5 cursor-pointer"
        >
          <div className="flex items-center gap-2">
            <span className="w-7 h-7 rounded-full bg-[var(--yes-accent-soft)] text-[var(--yes-primary)] flex items-center justify-center shrink-0">
              <Monitor className="w-4 h-4" />
            </span>
            <span className="text-[13px] text-[var(--yes-ink2)]">桌面分身</span>
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-[26px] font-bold leading-none text-[var(--yes-ink)]">
              子会话
            </span>
            <span className="text-xs font-mono tabular-nums text-[var(--yes-ink3)]">
              1920×1080
            </span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-[var(--yes-well)] overflow-hidden">
            <div
              className="h-full rounded-full bg-[var(--yes-primary)]"
              style={{ width: desktopClone.run_mode === 'desktop_clone' ? '100%' : '50%' }}
            />
          </div>
          <div className="text-xs text-[var(--yes-ink3)] truncate">
            独立窗口最小化照跑 · 点这里体检与设定
          </div>
        </button>

        {/* Card 3: 定时启动 */}
        <div className="yes-card p-4 space-y-2.5">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="w-7 h-7 rounded-full bg-[var(--yes-accent-soft)] text-[var(--yes-primary)] flex items-center justify-center shrink-0">
                <Clock className="w-4 h-4" />
              </span>
              <span className="text-[13px] text-[var(--yes-ink2)]">定时启动</span>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={scheduleEnabled}
              aria-label="开关定时启动"
              onClick={() => onToggleSchedule(!scheduleEnabled)}
              className={`w-9 h-[22px] rounded-full transition-colors relative cursor-pointer ${
                scheduleEnabled ? 'bg-[var(--yes-primary)]' : 'bg-[var(--yes-well2)]'
              }`}
            >
              <span
                className={`block w-4 h-4 rounded-full bg-white shadow-xs transition-transform ${
                  scheduleEnabled ? 'translate-x-[17px]' : 'translate-x-[3px]'
                }`}
              />
            </button>
          </div>
          <div className="flex items-center justify-between gap-2">
            <span className="text-[26px] font-bold leading-none font-mono tabular-nums text-[var(--yes-ink)]">
              {scheduleEnabled ? scheduleTime : '关'}
            </span>
            {scheduleEnabled && (
              <input
                type="time"
                aria-label="定时启动时间"
                value={scheduleTime}
                onChange={(e) => onChangeScheduleTime(e.target.value)}
                className="text-xs font-mono tabular-nums px-2 py-1 rounded-lg bg-[var(--yes-inset)] text-[var(--yes-ink)] border border-[var(--yes-line2)]"
              />
            )}
          </div>
          <div className="text-xs text-[var(--yes-ink3)] truncate">
            {scheduleEnabled
              ? `每天 ${scheduleTime} 自动执行日常（国服 05:00 刷新后）`
              : '打开开关设定每天几点自动跑'}
          </div>
        </div>
      </section>

      {/* 今日任务 BoardTile Grid */}
      <section className="space-y-3" aria-label="今日任务">
        <div className="flex flex-wrap items-center justify-between gap-2 px-1">
          <div className="flex items-baseline gap-2.5">
            <h2 className="text-[15px] font-semibold text-[var(--yes-ink)]">今日任务</h2>
            <span className="text-xs text-[var(--yes-ink3)]">
              共 {daily.length} 项 · 点卡片进入任务设定
            </span>
          </div>
          <div className="flex items-center gap-3 text-xs text-[var(--yes-ink3)]">
            <span className="inline-flex items-center gap-1">
              <Check className="w-3.5 h-3.5 text-[var(--yes-ok)]" />
              已完成
            </span>
            <span>·</span>
            <span>未完成</span>
            <span>·</span>
            <span>不在一键日常里</span>
          </div>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5 gap-2.5">
          {daily.map(renderBoardTile)}
        </div>
      </section>

      {/* 本周与活动任务 BoardTile Grid */}
      <section className="space-y-3" aria-label="本周与活动任务">
        <div className="flex flex-wrap items-center justify-between gap-2 px-1">
          <h2 className="text-[15px] font-semibold text-[var(--yes-ink)]">本周与活动任务</h2>
          <span className="text-xs text-[var(--yes-ink3)]">
            联盟突袭、大型活动与单人突袭按需勾选加入一键日常
          </span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5 gap-2.5">
          {weeklyOrEvent.map(renderBoardTile)}
        </div>
      </section>

      {/* Game Window Size Footer Card (mirrors YES-BD2 GameSizeCard) */}
      <section className="yes-card px-5 py-3.5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <span className="w-8 h-8 rounded-full bg-[var(--yes-ok-soft)] text-[var(--yes-ok)] flex items-center justify-center shrink-0">
            <ShieldCheck className="w-4 h-4" />
          </span>
          <div className="min-w-0">
            <div className="text-[13px] font-medium text-[var(--yes-ink)]">
              游戏窗口 {desktopClone.clientWidth}×{desktopClone.clientHeight} · {geometryVerdict.label}
            </div>
            <div className="text-xs text-[var(--yes-ink3)] truncate">
              {geometryVerdict.recommendation}
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={() => onNavigate('desktop')}
          className="h-8 px-3.5 rounded-full text-xs bg-[var(--yes-fill)] hover:bg-[var(--yes-fill-hover)] text-[var(--yes-ink)] transition-colors cursor-pointer whitespace-nowrap shrink-0"
        >
          分身与 1080P 设置
        </button>
      </section>
    </div>
  );
}
