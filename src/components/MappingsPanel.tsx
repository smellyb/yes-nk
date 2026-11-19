import { useMemo, useState } from 'react';
import { Check, Copy, Search } from 'lucide-react';
import { RecognitionMapping, RecognitionMode } from '../types';

interface MappingsPanelProps {
  mappings: RecognitionMapping[];
}

const MODE_LABELS: Record<RecognitionMode, string> = {
  ocr: 'OCR 文字优先',
  template: '模板特征匹配',
  hybrid: 'COCO + OCR 混合',
};

const CONVERT_CMD =
  'python tools/convert_maa_assets.py --maa-dir D:\\MaaNikke\\resource\\base\\image';

export default function MappingsPanel({ mappings }: MappingsPanelProps) {
  const [query, setQuery] = useState('');
  const [modeFilter, setModeFilter] = useState<'all' | RecognitionMode>('all');
  const [copied, setCopied] = useState(false);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return mappings.filter((item) => {
      const matchMode = modeFilter === 'all' || item.mode === modeFilter;
      const matchQuery =
        !q ||
        item.scene.toLowerCase().includes(q) ||
        item.featureName.toLowerCase().includes(q) ||
        item.maaNode.toLowerCase().includes(q) ||
        item.okMethod.toLowerCase().includes(q) ||
        item.ocrFallback.toLowerCase().includes(q);
      return matchMode && matchQuery;
    });
  }, [mappings, query, modeFilter]);

  const handleCopyCmd = async () => {
    try {
      await navigator.clipboard.writeText(CONVERT_CMD);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div className="space-y-0.5">
          <h1 className="text-[23px] font-bold text-[var(--yes-ink)] tracking-tight">素材映射</h1>
          <p className="text-[13px] text-[var(--yes-ink2)]">
            已内置 40 项从 Shinarin/MaaNikke 转换的 1280×720 COCO 模板与局部 ROI OCR 兜底策略
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-[var(--yes-ink3)] absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              aria-label="搜索场景、特征名或 OCR 关键词"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="搜索特征名、场景或关键词..."
              className="h-8 pl-8 pr-3 text-xs rounded-full bg-[var(--yes-card)] text-[var(--yes-ink)] border border-[var(--yes-line2)] w-52 outline-none focus:border-[var(--yes-primary)]"
            />
          </div>

          <div className="flex items-center gap-1 p-1 rounded-full bg-[var(--yes-well)]">
            {(['all', 'hybrid', 'ocr', 'template'] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => setModeFilter(mode)}
                className={`h-7 px-3 text-xs rounded-full transition-colors cursor-pointer whitespace-nowrap shrink-0 ${
                  modeFilter === mode
                    ? 'bg-[var(--yes-raised)] text-[var(--yes-ink)] shadow-xs font-medium'
                    : 'text-[var(--yes-ink2)] hover:text-[var(--yes-ink)]'
                }`}
              >
                {mode === 'all' ? '全部' : MODE_LABELS[mode]}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* CLI Converter Bar */}
      <div className="yes-card px-5 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <div className="text-xs font-medium text-[var(--yes-ink2)]">
            从 MaaNikke 重新刷新国服模板至 ok-script COCO 特征包 (assets/result.json)
          </div>
          <code className="block text-xs font-mono text-[var(--yes-primary)] truncate">
            {CONVERT_CMD}
          </code>
        </div>
        <button
          type="button"
          onClick={handleCopyCmd}
          className="inline-flex items-center gap-1.5 h-8 px-3.5 text-xs rounded-full bg-[var(--yes-fill)] hover:bg-[var(--yes-fill-hover)] text-[var(--yes-ink)] transition-colors cursor-pointer whitespace-nowrap shrink-0"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-[var(--yes-ok)]" />
              已复制命令
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              复制转换命令
            </>
          )}
        </button>
      </div>

      {/* Mapping Table */}
      <div className="yes-card overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[var(--yes-line)] text-xs text-[var(--yes-ink3)]">
              <th className="py-3.5 px-5 font-medium">场景与 COCO 特征名</th>
              <th className="py-3.5 px-4 font-medium">MaaNikke 原节点与痛点</th>
              <th className="py-3.5 px-4 font-medium">YES-NK 识别策略</th>
              <th className="py-3.5 px-5 font-medium">16:9 归一化 ROI 与 OCR 兜底词</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--yes-line)] text-sm">
            {filtered.length === 0 ? (
              <tr>
                <td
                  colSpan={4}
                  className="py-10 px-5 text-center text-sm text-[var(--yes-ink3)]"
                >
                  没有匹配当前筛选条件的特征记录，请清空搜索词后重试。
                </td>
              </tr>
            ) : (
              filtered.map((row) => (
                <tr
                  key={row.id}
                  className="hover:bg-[var(--yes-inset)] transition-colors align-top"
                >
                  <td className="py-3.5 px-5 whitespace-nowrap">
                    <div className="font-medium text-[var(--yes-ink)]">{row.scene}</div>
                    <div className="mt-0.5 text-xs font-mono text-[var(--yes-ink3)]">
                      {row.featureName}
                    </div>
                    <div className="mt-0.5 text-xs text-[var(--yes-ink3)]">
                      {MODE_LABELS[row.mode]}
                    </div>
                  </td>
                  <td className="py-3.5 px-4 max-w-xs">
                    <div className="text-xs font-mono text-[var(--yes-ink2)]">{row.maaNode}</div>
                    <p className="mt-1 text-xs text-[var(--yes-ink3)] leading-relaxed">
                      {row.maaPainPoint}
                    </p>
                  </td>
                  <td className="py-3.5 px-4 max-w-xs">
                    <div className="text-xs font-mono text-[var(--yes-primary)] leading-relaxed">
                      {row.okMethod}
                    </div>
                  </td>
                  <td className="py-3.5 px-5">
                    <div className="text-xs font-mono tabular-nums text-[var(--yes-ink2)]">
                      {row.roiBox}
                    </div>
                    <div className="mt-1 text-xs text-[var(--yes-ink3)]">{row.ocrFallback}</div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
