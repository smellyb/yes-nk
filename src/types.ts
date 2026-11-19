export type NavSection = 'tasks' | 'desktop' | 'triggers' | 'mappings' | 'logs' | 'settings';

export type RecognitionMode = 'ocr' | 'template' | 'hybrid';

export type TaskStatus = 'idle' | 'running' | 'completed' | 'skipped';

export type RunMode = 'desktop_clone' | 'background_post_message' | 'foreground_compat';

export interface DesktopCloneSettings {
  run_mode: RunMode;
  desktop_name: string;
  switch_hotkey: string;
  auto_close_desktop_on_exit: boolean;
  prefer_borderless_1080p: boolean;
  clientWidth: number;
  clientHeight: number;
  dpiScalePercent: number;
}

export interface GeometryVerdict {
  aspectRatio: number;
  ratioErrorPercent: number;
  scaleX: number;
  scaleY: number;
  status: 'optimal_1080p' | 'valid_scaled_16_9' | 'non_16_9' | 'too_small';
  isValid: boolean;
  label: string;
  recommendation: string;
}

export interface TaskOption {
  key: string;
  label: string;
  type: 'boolean' | 'select' | 'number';
  value: boolean | string | number;
  choices?: string[];
  min?: number;
  max?: number;
}

export interface AutomationTask {
  id: string;
  className: string;
  pythonModule: string;
  name: string;
  category: '基础日常' | '基地与养成' | '商店与结算';
  summary: string;
  enabled: boolean;
  estimatedSec: number;
  recognitionMode: RecognitionMode;
  maaRefNode: string;
  cocoFeatures: string[];
  steps: string[];
  options: TaskOption[];
}

export interface TriggerRule {
  id: string;
  className: string;
  name: string;
  description: string;
  enabled: boolean;
  intervalMs: number;
  actionSummary: string;
}

export interface RecognitionMapping {
  id: string;
  featureName: string;
  scene: string;
  maaNode: string;
  maaPainPoint: string;
  okMethod: string;
  mode: RecognitionMode;
  roiBox: string;
  ocrFallback: string;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  level: 'INFO' | 'OCR' | 'ACTION' | 'WARN';
  source: string;
  message: string;
}

export interface ClientSettings {
  server: '国服 PC 端 (WeGame / 新的希望)';
  exeName: string;
  windowTitle: string;
  resolution: '1920x1080' | '1600x900' | '1280x720';
  captureMethod: 'WGC + BitBlt_RenderFull' | 'WGC' | 'BitBlt_RenderFull';
  ocrEngine: 'RapidOCR (ok-script 内置)';
  ocrConfidence: number;
  templateThreshold: number;
  autoReturnLobby: boolean;
}
