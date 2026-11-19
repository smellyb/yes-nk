import {
  ArrowDown,
  ArrowUp,
  CheckCircle2,
  Gift,
  Play,
  RotateCcw,
  ShoppingBag,
  SlidersHorizontal,
  Sparkles,
  Swords,
  Users,
} from 'lucide-react';
import { AutomationTask, TaskStatus } from '../types';

interface TaskPageProps {
  tasks: AutomationTask[];
  selectedTaskId: string;
  taskStatuses: Record<string, TaskStatus>;
  onSelectTask: (taskId: string) => void;
  onToggleTask: (taskId: string) => void;
  onMoveTask: (taskId: string, direction: -1 | 1) => void;
  onUpdateOption: (taskId: string, optionKey: string, val: boolean | string | number) => void;
  onRunSingle: (task: AutomationTask) => void;
  onStartDaily: () => void;
  onApplyPreset: (mode: 'basic' | 'all' | 'default') => void;
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

export default function TaskPage({
  tasks,
  selectedTaskId,
  taskStatuses,
  onSelectTask,
  onToggleTask,
  onMoveTask,
  onUpdateOption,
  onRunSingle,
  onStartDaily,
  onApplyPreset,
}: TaskPageProps) {
  const included = tasks.filter((t) => t.enabled);
  const excluded = tasks.filter((t) => !t.enabled);
  const doneCount = included.filter((t) => taskStatuses[t.id] === 'completed').length;
  const selectedTask = tasks.find((t) => t.id === selectedTaskId) ?? tasks[0];
  const globalIndex = tasks.findIndex((t) => t.id === selectedTask.id);

  const renderRow = (task: AutomationTask) => {
    const Icon = getCategoryIcon(task.category);
    const active = task.id === selectedTask.id;
    const isDone = taskStatuses[task.id] === 'completed';

    return (
      <button
        key={task.id}
        type="button"
        onClick={() => onSelectTask(task.id)}
        className={`w-full h-10 px-2.5 flex items-center justify-between gap-2 rounded-[12px] text-left transition-colors cursor-pointer ${
          active
            ? 'bg-[var(--yes-row-on)]'
            : 'hover:bg-[var(--yes-ink)]/5'
        }`}
      >
        <span className="flex items-center gap-2.5 min-w-0">
          <span
            className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${
              task.enabled
                ? 'bg-[var(--yes-accent-soft)] text-[var(--yes-primary)]'
                : 'bg-[var(--yes-well)] text-[var(--yes-ink3)]'
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
          </span>
          <span
            className={`text-[13px] truncate ${
              task.enabled ? 'text-[var(--yes-ink)]' : 'text-[var(--yes-ink3)]'
            }`}
          >
            {task.name}
          </span>
        </span>
        <span className="flex items-center gap-1 text-[11px] shrink-0">
          {isDone ? (
            <>
              <CheckCircle2 className="w-3.5 h-3.5 text-[var(--yes-ok)]" />
              <span className="text-[var(--yes-ok)]">完成</span>
            </>
          ) : !task.enabled ? (
            <span className="text-[var(--yes-ink3)]">不跑</span>
          ) : (
            <span className="text-[var(--yes-ink3)]">未完成</span>
          )}
        </span>
      </button>
    );
  };

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      {/* Header matching YES-BD2 TaskPage */}
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div className="space-y-0.5">
          <h1 className="text-[23px] font-bold text-[var(--yes-ink)] tracking-tight">任务设定</h1>
          <p className="text-[13px] text-[var(--yes-ink2)]">
            一键运行会照左边的顺序跑 {included.length} 项 · 今天做完 {doneCount} 项
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => onApplyPreset('basic')}
            className="h-8 px-3 rounded-full text-xs bg-[var(--yes-fill)] hover:bg-[var(--yes-fill-hover)] text-[var(--yes-ink)] transition-colors cursor-pointer whitespace-nowrap"
          >
            仅基础日常
          </button>
          <button
            type="button"
            onClick={() => onApplyPreset('all')}
            className="h-8 px-3 rounded-full text-xs bg-[var(--yes-fill)] hover:bg-[var(--yes-fill-hover)] text-[var(--yes-ink)] transition-colors cursor-pointer whitespace-nowrap"
          >
            全部启用
          </button>
          <button
            type="button"
            onClick={() => onApplyPreset('default')}
            className="inline-flex items-center gap-1 h-8 px-3 rounded-full text-xs bg-[var(--yes-fill)] hover:bg-[var(--yes-fill-hover)] text-[var(--yes-ink)] transition-colors cursor-pointer whitespace-nowrap"
          >
            <RotateCcw className="w-3 h-3" />
            恢复默认
          </button>
          <button
            type="button"
            disabled={included.length === 0}
            onClick={onStartDaily}
            className="inline-flex items-center gap-1.5 h-9 px-4 rounded-full text-[13px] font-medium bg-[var(--yes-primary)] hover:bg-[var(--yes-primary-hover)] disabled:opacity-40 text-white transition-colors cursor-pointer whitespace-nowrap"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            一键完成日常
          </button>
        </div>
      </header>

      {/* Master-Detail Columns (Left 312px list_card + Right detail card) */}
      <div className="grid grid-cols-1 lg:grid-cols-[312px_1fr] gap-4 items-start">
        <section aria-label="一键运行任务列表" className="yes-card p-3 space-y-1">
          <div className="px-2.5 pt-1 pb-1.5 text-xs text-[var(--yes-ink3)]">
            一键运行的顺序（{included.length}）
          </div>
          {included.length === 0 ? (
            <div className="px-2.5 py-4 text-xs text-[var(--yes-ink3)]">
              当前没有加入一键日常的项目
            </div>
          ) : (
            included.map(renderRow)
          )}

          {excluded.length > 0 && (
            <>
              <div className="pt-3 pb-1 px-2.5 border-t border-[var(--yes-line)] mt-2 text-xs text-[var(--yes-ink3)]">
                不在一键日常里（{excluded.length}）
              </div>
              {excluded.map(renderRow)}
            </>
          )}
        </section>

        {/* Right Detail Card */}
        <section aria-label="选中任务参数详情" className="yes-card p-6 space-y-5 lg:sticky lg:top-0">
          <div className="flex flex-wrap items-start justify-between gap-4 pb-4 border-b border-[var(--yes-line)]">
            <div className="space-y-1 flex-1 min-w-[240px]">
              <div className="text-xs text-[var(--yes-ink3)]">
                {selectedTask.category} · {selectedTask.className} · 预计 {selectedTask.estimatedSec}s
              </div>
              <h2 className="text-[20px] font-bold text-[var(--yes-ink)]">{selectedTask.name}</h2>
              <p className="text-[13px] text-[var(--yes-ink2)] leading-relaxed">
                {selectedTask.summary}
              </p>
            </div>

            <div className="flex items-center gap-1.5 shrink-0">
              <button
                type="button"
                aria-label={`上移 ${selectedTask.name}`}
                disabled={globalIndex <= 0}
                onClick={() => onMoveTask(selectedTask.id, -1)}
                className="w-8 h-8 rounded-full bg-[var(--yes-fill)] hover:bg-[var(--yes-fill-hover)] disabled:opacity-35 text-[var(--yes-ink)] flex items-center justify-center cursor-pointer"
              >
                <ArrowUp className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                aria-label={`下移 ${selectedTask.name}`}
                disabled={globalIndex >= tasks.length - 1}
                onClick={() => onMoveTask(selectedTask.id, 1)}
                className="w-8 h-8 rounded-full bg-[var(--yes-fill)] hover:bg-[var(--yes-fill-hover)] disabled:opacity-35 text-[var(--yes-ink)] flex items-center justify-center cursor-pointer"
              >
                <ArrowDown className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => onRunSingle(selectedTask)}
                className="inline-flex items-center gap-1.5 h-8 px-3.5 rounded-full text-xs font-medium bg-[var(--yes-primary)] hover:bg-[var(--yes-primary-hover)] text-white transition-colors cursor-pointer whitespace-nowrap"
              >
                <Play className="w-3 h-3 fill-current" />
                单独跑这一项
              </button>
            </div>
          </div>

          {/* Join Daily Batch Toggle Row */}
          <div className="flex items-center justify-between gap-4 py-1">
            <div>
              <div className="text-[14px] text-[var(--yes-ink)]">加入一键日常</div>
              <div className="text-xs text-[var(--yes-ink3)]">
                关闭后该任务不会随「一键完成日常」或「在桌面分身跑」自动执行
              </div>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={selectedTask.enabled}
              aria-label={`切换 ${selectedTask.name} 加入一键日常`}
              onClick={() => onToggleTask(selectedTask.id)}
              className={`w-11 h-[26px] rounded-full transition-colors relative shrink-0 cursor-pointer ${
                selectedTask.enabled ? 'bg-[var(--yes-primary)]' : 'bg-[var(--yes-well2)]'
              }`}
            >
              <span
                className={`block w-5 h-5 rounded-full bg-white shadow-xs transition-transform ${
                  selectedTask.enabled ? 'translate-x-[21px]' : 'translate-x-[3px]'
                }`}
              />
            </button>
          </div>

          {/* Task Options */}
          <div className="pt-4 border-t border-[var(--yes-line)] space-y-3">
            <div className="flex items-center gap-2 text-xs font-semibold text-[var(--yes-ink2)]">
              <SlidersHorizontal className="w-3.5 h-3.5 text-[var(--yes-primary)]" />
              任务参数配置 (default_config)
            </div>
            <div className="divide-y divide-[var(--yes-line)]">
              {selectedTask.options.map((opt) => (
                <div
                  key={opt.key}
                  className="py-2.5 flex items-center justify-between gap-4"
                >
                  <label
                    htmlFor={`opt-${selectedTask.id}-${opt.key}`}
                    className="text-[13px] text-[var(--yes-ink)]"
                  >
                    {opt.label}
                  </label>
                  {opt.type === 'boolean' && (
                    <button
                      id={`opt-${selectedTask.id}-${opt.key}`}
                      type="button"
                      role="switch"
                      aria-checked={Boolean(opt.value)}
                      onClick={() => onUpdateOption(selectedTask.id, opt.key, !opt.value)}
                      className={`w-9 h-[22px] rounded-full transition-colors relative shrink-0 cursor-pointer ${
                        opt.value ? 'bg-[var(--yes-primary)]' : 'bg-[var(--yes-well2)]'
                      }`}
                    >
                      <span
                        className={`block w-4 h-4 rounded-full bg-white shadow-xs transition-transform ${
                          opt.value ? 'translate-x-[17px]' : 'translate-x-[3px]'
                        }`}
                      />
                    </button>
                  )}
                  {opt.type === 'select' && (
                    <select
                      id={`opt-${selectedTask.id}-${opt.key}`}
                      value={String(opt.value)}
                      onChange={(e) => onUpdateOption(selectedTask.id, opt.key, e.target.value)}
                      className="h-8 px-3 rounded-full text-xs bg-[var(--yes-fill)] text-[var(--yes-ink)] border-none outline-none cursor-pointer"
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
                        onUpdateOption(selectedTask.id, opt.key, Number(e.target.value))
                      }
                      className="w-20 h-8 px-3 text-right font-mono tabular-nums text-xs rounded-full bg-[var(--yes-fill)] text-[var(--yes-ink)] border-none outline-none"
                    />
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* ok-script State Machine Steps & Metadata */}
          <div className="pt-4 border-t border-[var(--yes-line)] space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-[var(--yes-ink3)]">
              <span className="font-semibold text-[var(--yes-ink2)]">ok-script 状态机执行链路</span>
              <span className="font-mono">{selectedTask.pythonModule}</span>
            </div>
            <ol className="space-y-2">
              {selectedTask.steps.map((step, idx) => (
                <li
                  key={step}
                  className="flex items-start gap-2.5 text-xs text-[var(--yes-ink2)] leading-relaxed"
                >
                  <span className="font-mono tabular-nums text-[var(--yes-primary)] shrink-0">
                    0{idx + 1}.
                  </span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>
            <div className="text-xs text-[var(--yes-ink3)] pt-1">
              关联 COCO 特征：<span className="font-mono">{selectedTask.cocoFeatures.join(' · ')}</span>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
