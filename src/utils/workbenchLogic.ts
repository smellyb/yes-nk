import {
  AutomationTask,
  ClientSettings,
  DesktopCloneSettings,
  GeometryVerdict,
  RunMode,
  TriggerRule,
} from '../types';

const BASE_WIDTH = 1920;
const BASE_HEIGHT = 1080;
const TARGET_RATIO = 16 / 9;
const RATIO_TOLERANCE = 0.015;

export function sanitizeDesktopName(rawName: string): string {
  const cleaned = rawName.replace(/[^A-Za-z0-9_-]/g, '_').replace(/^_+|_+$/g, '');
  return cleaned.slice(0, 48) || 'YES_NK_Desktop';
}

export function resolveInteractionBackend(runMode: RunMode): string {
  if (runMode === 'desktop_clone') return 'ForegroundPostMessage';
  if (runMode === 'background_post_message') return 'PostMessage';
  return 'Pynput';
}

export function evaluateClientGeometry(
  clientWidth: number,
  clientHeight: number,
  dpiScalePercent: number = 100
): GeometryVerdict {
  if (!Number.isFinite(clientWidth) || !Number.isFinite(clientHeight) || clientWidth <= 0 || clientHeight <= 0) {
    return {
      aspectRatio: 0,
      ratioErrorPercent: 100,
      scaleX: 0,
      scaleY: 0,
      status: 'too_small',
      isValid: false,
      label: '尺寸无效',
      recommendation: '请输入有效的窗口客户区宽高，且确认游戏窗口未被最小化。',
    };
  }

  const aspectRatio = clientWidth / clientHeight;
  const ratioError = Math.abs(aspectRatio - TARGET_RATIO) / TARGET_RATIO;
  const scaleX = clientWidth / BASE_WIDTH;
  const scaleY = clientHeight / BASE_HEIGHT;
  const dpiHint =
    dpiScalePercent > 100
      ? ` 当前系统 DPI 为 ${dpiScalePercent}%，启动时将自动开启 Per-Monitor DPI v2 感知。`
      : '';

  if (clientWidth < 1280 || clientHeight < 720) {
    return {
      aspectRatio: Number(aspectRatio.toFixed(4)),
      ratioErrorPercent: Number((ratioError * 100).toFixed(2)),
      scaleX: Number(scaleX.toFixed(3)),
      scaleY: Number(scaleY.toFixed(3)),
      status: 'too_small',
      isValid: false,
      label: '低于最低尺寸 (1280×720)',
      recommendation: `当前客户区 ${clientWidth}×${clientHeight} 过小，建议设为 1600×900 窗口化或在桌面分身内运行 1920×1080 无边框全屏。${dpiHint}`,
    };
  }

  if (ratioError > RATIO_TOLERANCE) {
    return {
      aspectRatio: Number(aspectRatio.toFixed(4)),
      ratioErrorPercent: Number((ratioError * 100).toFixed(2)),
      scaleX: Number(scaleX.toFixed(3)),
      scaleY: Number(scaleY.toFixed(3)),
      status: 'non_16_9',
      isValid: false,
      label: '非标准 16:9（疑似被任务栏挤压）',
      recommendation: `客户区 ${clientWidth}×${clientHeight} 偏离 16:9 达 ${(ratioError * 100).toFixed(1)}%。1080P 屏幕上窗口化易受标题栏和任务栏挤压，建议切入桌面分身跑 1920×1080 无边框，或在主桌面改为 1600×900 窗口。${dpiHint}`,
    };
  }

  if (clientWidth === BASE_WIDTH && clientHeight === BASE_HEIGHT) {
    return {
      aspectRatio: Number(aspectRatio.toFixed(4)),
      ratioErrorPercent: Number((ratioError * 100).toFixed(2)),
      scaleX: 1,
      scaleY: 1,
      status: 'optimal_1080p',
      isValid: true,
      label: '1080P 基准完美匹配 (1:1)',
      recommendation: `客户区严格等于 1920×1080 (16:9)，COCO 模板与 ROI 零缩放命中，推荐配合桌面分身无边框运行。${dpiHint}`,
    };
  }

  return {
    aspectRatio: Number(aspectRatio.toFixed(4)),
    ratioErrorPercent: Number((ratioError * 100).toFixed(2)),
    scaleX: Number(scaleX.toFixed(3)),
    scaleY: Number(scaleY.toFixed(3)),
    status: 'valid_scaled_16_9',
    isValid: true,
    label: `16:9 等比缩放兼容 (${scaleX.toFixed(2)}x)`,
    recommendation: `客户区 ${clientWidth}×${clientHeight} 符合 16:9 规范，适合 1080P 主桌面窗口化使用，ok-script 会自动等比缩放模板与 ROI。${dpiHint}`,
  };
}

export function reorderTasks(
  tasks: AutomationTask[],
  taskId: string,
  direction: -1 | 1
): AutomationTask[] {
  const index = tasks.findIndex((t) => t.id === taskId);
  const nextIndex = index + direction;
  if (index < 0 || nextIndex < 0 || nextIndex >= tasks.length) {
    return tasks;
  }
  const copy = [...tasks];
  const [moved] = copy.splice(index, 1);
  copy.splice(nextIndex, 0, moved);
  return copy;
}

export function buildLaunchCommand(desktopClone: DesktopCloneSettings): string {
  if (desktopClone.run_mode === 'desktop_clone') {
    return 'python main.py --desktop-clone';
  }
  return 'python main.py';
}

export function buildYesNkExportConfig(
  settings: ClientSettings,
  desktopClone: DesktopCloneSettings,
  tasks: AutomationTask[],
  triggers: TriggerRule[]
) {
  return {
    project: 'YES-NK',
    framework: 'ok-script',
    target_game: '胜利女神：新的希望 (国服 PC / WeGame)',
    desktop_clone: {
      run_mode: desktopClone.run_mode,
      desktop_name: sanitizeDesktopName(desktopClone.desktop_name),
      switch_hotkey: desktopClone.switch_hotkey,
      auto_close_desktop_on_exit: desktopClone.auto_close_desktop_on_exit,
      prefer_borderless_1080p: desktopClone.prefer_borderless_1080p,
      resolved_interaction: resolveInteractionBackend(desktopClone.run_mode),
    },
    client: {
      exe: settings.exeName,
      windowTitle: settings.windowTitle,
      resolution: settings.resolution,
      captureMethod: settings.captureMethod,
      ocrEngine: settings.ocrEngine,
      ocrConfidence: settings.ocrConfidence,
      templateThreshold: settings.templateThreshold,
      autoReturnLobby: settings.autoReturnLobby,
    },
    onetime_tasks: tasks.map((t, index) => ({
      order: index + 1,
      module: t.pythonModule,
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
}
