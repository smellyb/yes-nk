export type NavSection = 'tasks' | 'triggers' | 'mappings' | 'logs' | 'settings';

export type RecognitionMode = 'ocr' | 'template' | 'hybrid';

export type TaskStatus = 'idle' | 'running' | 'completed' | 'skipped';

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
  name: string;
  category: '基础日常' | '基地与养成' | '日常副本' | '活动与登录';
  summary: string;
  enabled: boolean;
  estimatedSec: number;
  recognitionMode: RecognitionMode;
  maaRefNode: string;
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
  scene: string;
  maaNode: string;
  maaPainPoint: string;
  okMethod: string;
  mode: RecognitionMode;
  roiBox: string;
  targetTextOrAsset: string;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  level: 'INFO' | 'OCR' | 'ACTION' | 'WARN';
  source: string;
  message: string;
}

export interface ClientSettings {
  server: '国服 PC 端 (WeGame / 新的希望)' | '国际服 PC 端 (NIKKE Launcher)' | '安卓模拟器 (ADB)';
  windowTitle: string;
  resolution: '1920x1080' | '1600x900' | '1280x720';
  captureMethod: 'WindowsGraphicsCapture' | 'BitBlt' | 'ADB Screencap';
  ocrEngine: 'RapidOCR (ONNX)' | 'PaddleOCR';
  ocrConfidence: number;
  templateThreshold: number;
  autoReturnLobby: boolean;
  pauseOnManualInput: boolean;
}
