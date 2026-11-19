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

const CONVERT_CMD = 'python tools/convert_maa_assets.py --maa-dir D:\\MaaNikke\\resource\\base\\image';

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
    <div className="max-w-6xl mx-auto space-y-5">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
            COCO 特征清单与 MaaNikke 素材转换映射
          </h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            完全对齐 YES-BD2 的 COCO 模板 + 归一化局部 ROI OCR 混合策略，所有特征均登记于 assets/coco_manifest.json。
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              aria-label="搜索场景、特征名或 OCR 关键词"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="搜索特征名、场景或关键词..."
              className="pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-[#1C1F24] text-slate-900 dark:text-slate-100 w-56"
            />
          </div>

          <div className="flex items-center gap-1 p-1 rounded-lg bg-slate-200/70 dark:bg-[#1C1F24] border border-slate-200 dark:border-slate-800">
            {(['all', 'hybrid', 'ocr', 'template'] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => setModeFilter(mode)}
                className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                  modeFilter === mode
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

      {/* CLI Converter Bar */}
      <div className="bg-white dark:bg-[#1C1F24] border border-slate-200 dark:border-slate-800 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <div className="text-xs font-medium text-slate-700 dark:text-slate-200">
            一键从 MaaNikke 导入国服模板至 ok-script COCO 特征包 (assets/result.json)
          </div>
          <code className="block text-xs font-mono text-[#0067C0] dark:text-[#4CC2FF] truncate">
            {CONVERT_CMD}
          </code>
        </div>
        <button
          type="button"
          onClick={handleCopyCmd}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-[#16A34A]" />
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
      <div className="bg-white dark:bg-[#1C1F24] border border-slate-200 dark:border-slate-800 rounded-xl overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-800 text-xs text-slate-500 dark:text-slate-400">
              <th className="py-3 px-4 font-medium">场景与 COCO 特征名</th>
              <th className="py-3 px-4 font-medium">MaaNikke 原节点与识别痛点</th>
              <th className="py-3 px-4 font-medium">YES-NK (ok-script) 识别策略</th>
              <th className="py-3 px-4 font-medium">16:9 归一化 ROI 与 OCR 兜底词</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-sm">
            {filtered.length === 0 ? (
              <tr>
                <td
                  colSpan={4}
                  className="py-10 px-4 text-center text-sm text-slate-500 dark:text-slate-400"
                >
                  没有匹配当前筛选条件的特征记录，请清空搜索词后重试。
                </td>
              </tr>
            ) : (
              filtered.map((row) => (
                <tr
                  key={row.id}
                  className="hover:bg-slate-50 dark:hover:bg-[#23272F] transition-colors align-top"
                >
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    <div className="font-medium text-slate-900 dark:text-white">
                      {row.scene}
                    </div>
                    <div className="mt-0.5 text-xs font-mono text-slate-500 dark:text-slate-400">
                      {row.featureName}
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
                      {row.ocrFallback}
                    </div>
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
