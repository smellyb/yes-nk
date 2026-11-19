import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildLaunchCommand,
  buildYesNkExportConfig,
  computeRunSummaryStats,
  evaluateClientGeometry,
  formatDurationClock,
  partitionDailyAndWeeklyTasks,
  reorderTasks,
  resolveInteractionBackend,
  sanitizeDesktopName,
} from './workbenchLogic';
import {
  INITIAL_DESKTOP_CLONE,
  INITIAL_SETTINGS,
  INITIAL_TASKS,
  INITIAL_TRIGGERS,
} from '../data/presetData';

test('evaluateClientGeometry approves 1080p borderless and 1600x900 scaled windows', () => {
  const optimal = evaluateClientGeometry(1920, 1080, 100);
  assert.equal(optimal.isValid, true);
  assert.equal(optimal.status, 'optimal_1080p');
  assert.equal(optimal.scaleX, 1);

  const scaled = evaluateClientGeometry(1600, 900, 125);
  assert.equal(scaled.isValid, true);
  assert.equal(scaled.status, 'valid_scaled_16_9');
  assert.match(scaled.recommendation, /125%/);
});

test('evaluateClientGeometry rejects taskbar-squished 1920x1009 and sub-720p windows', () => {
  const squished = evaluateClientGeometry(1920, 1009, 100);
  assert.equal(squished.isValid, false);
  assert.equal(squished.status, 'non_16_9');

  const small = evaluateClientGeometry(1024, 576, 100);
  assert.equal(small.isValid, false);
  assert.equal(small.status, 'too_small');
});

test('desktop clone helpers sanitize name and map interaction backends', () => {
  assert.equal(sanitizeDesktopName('YES NK 分身#01'), 'YES_NK____01');
  assert.equal(sanitizeDesktopName('   '), 'YES_NK_Desktop');
  assert.equal(resolveInteractionBackend('desktop_clone'), 'ForegroundPostMessage');
  assert.equal(resolveInteractionBackend('background_post_message'), 'PostMessage');
  assert.equal(resolveInteractionBackend('foreground_compat'), 'Pynput');
  assert.equal(buildLaunchCommand(INITIAL_DESKTOP_CLONE), 'python main.py --desktop-clone');
});

test('reorderTasks moves items safely within bounds', () => {
  const moved = reorderTasks(INITIAL_TASKS, INITIAL_TASKS[1].id, -1);
  assert.equal(moved[0].id, INITIAL_TASKS[1].id);
  assert.equal(moved[1].id, INITIAL_TASKS[0].id);

  const unchanged = reorderTasks(INITIAL_TASKS, INITIAL_TASKS[0].id, -1);
  assert.equal(unchanged[0].id, INITIAL_TASKS[0].id);
});

test('buildYesNkExportConfig emits Python-compatible desktop_clone, daily_toggles, and all 22 pipelines', () => {
  assert.equal(INITIAL_TASKS.length, 22);
  const exported = buildYesNkExportConfig(
    INITIAL_SETTINGS,
    INITIAL_DESKTOP_CLONE,
    INITIAL_TASKS,
    INITIAL_TRIGGERS
  );
  assert.equal(exported.project, 'YES-NK');
  assert.equal(exported.desktop_clone.run_mode, 'desktop_clone');
  assert.equal(exported.desktop_clone.resolved_interaction, 'ForegroundPostMessage');
  assert.equal(exported.client.exe, 'nikke.exe');
  assert.equal(exported.onetime_tasks.length, 22);
  assert.equal(Object.keys(exported.daily_toggles).length, 22);
  assert.equal(exported.daily_toggles['拦截战挑战与快速扫荡'], true);
  assert.equal(exported.daily_toggles['同步器与循环室升级'], false);
  assert.equal(exported.daily_toggles['大型活动刷取与签到'], false);
  assert.equal(exported.onetime_tasks[0].module, INITIAL_TASKS[0].pythonModule);
});

test('YES-BD2 shell helpers partition tasks, format clocks, and compute summary stats', () => {
  const { daily, weeklyOrEvent } = partitionDailyAndWeeklyTasks(INITIAL_TASKS);
  assert.equal(daily.length + weeklyOrEvent.length, 22);
  assert.ok(weeklyOrEvent.length >= 2);
  assert.equal(formatDurationClock(0), '0:00');
  assert.equal(formatDurationClock(125), '2:05');

  const sample = INITIAL_TASKS.slice(0, 4);
  const stats = computeRunSummaryStats(sample, {
    [sample[0].id]: 'completed',
    [sample[1].id]: 'completed',
    [sample[2].id]: 'skipped',
  });
  assert.deepEqual(stats, { done: 2, skipped: 1, failed: 0, remaining: 1 });
});

