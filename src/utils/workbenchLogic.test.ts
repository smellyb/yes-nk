import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildLaunchCommand,
  buildYesNkExportConfig,
  evaluateClientGeometry,
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

test('buildYesNkExportConfig emits Python-compatible desktop_clone and client schema', () => {
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
  assert.equal(exported.onetime_tasks.length, INITIAL_TASKS.length);
  assert.equal(exported.onetime_tasks[0].module, INITIAL_TASKS[0].pythonModule);
});
