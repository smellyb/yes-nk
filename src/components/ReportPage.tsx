import { CheckCircle2, Play, XCircle } from 'lucide-react';
import { RunRecord } from '../types';
import { formatDurationClock } from '../utils/workbenchLogic';

interface ReportPageProps {
  records: RunRecord[];
  onStartDaily: () => void;
}

export default function ReportPage({ records, onStartDaily }: ReportPageProps) {
  const now = new Date();
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
  const headerSub = `${now.getMonth() + 1}月${now.getDate()}日 ${weekdays[now.getDay()]} · 游戏日从 05:00 开始`;

  // Group records by task name preserving order
  const grouped = new Map<string, RunRecord[]>();
  for (const rec of records) {
    const existing = grouped.get(rec.taskName) ?? [];
    existing.push(rec);
    grouped.set(rec.taskName, existing);
  }
  const entries = Array.from(grouped.entries());

  return (
    <div className="max-w-4xl mx-auto space-y-5">
      <header className="space-y-0.5">
        <h1 className="text-[23px] font-bold text-[var(--yes-ink)] tracking-tight">今日报表</h1>
        <p className="text-[13px] text-[var(--yes-ink2)]">{headerSub}</p>
      </header>

      <section className="yes-card p-5">
        {entries.length === 0 ? (
          <div className="py-12 text-center space-y-3">
            <p className="text-sm text-[var(--yes-ink2)]">
              今天还没有运行记录。执行一次日常后，这里会按时间线记录每项任务的耗时与结果。
            </p>
            <button
              type="button"
              onClick={onStartDaily}
              className="inline-flex items-center gap-1.5 h-9 px-5 rounded-full text-[13px] bg-[var(--yes-primary)] hover:bg-[var(--yes-primary-hover)] text-white transition-colors cursor-pointer"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              现在试跑一键日常
            </button>
          </div>
        ) : (
          <div className="divide-y divide-[var(--yes-line)]">
            {entries.map(([taskName, runs]) => {
              const hasDone = runs.some((r) => r.state === 'done');
              return (
                <div key={taskName} className="py-3.5 first:pt-1 last:pb-1 flex items-start gap-3">
                  {hasDone ? (
                    <CheckCircle2 className="w-4 h-4 text-[var(--yes-ok)] mt-0.5 shrink-0" />
                  ) : (
                    <XCircle className="w-4 h-4 text-[var(--yes-bad)] mt-0.5 shrink-0" />
                  )}

                  <div className="flex-1 min-w-0 space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[14px] font-medium text-[var(--yes-ink)] truncate">
                        {taskName}
                      </span>
                      {runs.length > 1 && (
                        <span className="text-xs text-[var(--yes-ink3)] shrink-0">
                          跑了 {runs.length} 次
                        </span>
                      )}
                    </div>

                    {/* YES-BD2 RunDot Timeline */}
                    <div className="space-y-1.5">
                      {runs.map((run, idx) => {
                        const isLast = idx === runs.length - 1;
                        const dotBg =
                          run.state === 'done'
                            ? 'bg-[var(--yes-ok)]'
                            : run.state === 'fail'
                            ? 'bg-[var(--yes-bad)]'
                            : 'bg-[var(--yes-warn)]';
                        const ringBg =
                          run.state === 'done'
                            ? 'bg-[var(--yes-ok-soft)]'
                            : run.state === 'fail'
                            ? 'bg-[var(--yes-bad-soft)]'
                            : 'bg-[var(--yes-warn-soft)]';
                        const stateLabel =
                          run.state === 'done' ? '完成' : run.state === 'fail' ? '失败' : '跳过';

                        return (
                          <div
                            key={run.id}
                            className="grid grid-cols-[44px_22px_1fr_auto] items-start gap-2 text-xs"
                          >
                            <span className="font-mono tabular-nums text-[var(--yes-ink3)] pt-0.5">
                              {run.finishedAt.slice(0, 5)}
                            </span>
                            <div className="flex flex-col items-center">
                              <span
                                className={`w-5 h-5 rounded-full flex items-center justify-center ${ringBg}`}
                              >
                                <span className={`w-2 h-2 rounded-full ${dotBg}`} />
                              </span>
                              {!isLast && (
                                <span className="w-px h-4 bg-[var(--yes-line2)] mt-0.5" />
                              )}
                            </div>
                            <div className="pt-0.5 min-w-0">
                              <span className="text-[var(--yes-ink)]">
                                {run.via} · {stateLabel}
                              </span>
                              {run.note && (
                                <p className="text-[var(--yes-ink3)] mt-0.5">{run.note}</p>
                              )}
                            </div>
                            <span className="font-mono tabular-nums text-[var(--yes-ink3)] pt-0.5">
                              {formatDurationClock(run.durationSec)}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
