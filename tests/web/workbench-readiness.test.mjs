import test from 'node:test';
import assert from 'node:assert/strict';
import { observeMoonContent } from '../../web/src/workbench-viewer.js';

class DisplayEvent {
  listeners = new Set();
  addEventListener(listener) { this.listeners.add(listener); return () => this.listeners.delete(listener); }
  raiseEvent() { for (const listener of this.listeners) listener(); }
}
const tileset = () => ({ initialTilesLoaded: new DisplayEvent(), allTilesLoaded: new DisplayEvent(), tileVisible: new DisplayEvent() });

for (const order of [
  ['initialTilesLoaded', 'tileVisible'],
  ['tileVisible', 'initialTilesLoaded'],
  ['allTilesLoaded', 'tileVisible'],
  ['tileVisible', 'allTilesLoaded'],
]) test(`Moon handoff waits for both readiness signals: ${order.join(' then ')}`, () => {
  const moon = tileset(); let reveals = 0;
  const dispose = observeMoonContent(moon, () => reveals++);
  moon[order[0]].raiseEvent(); assert.equal(reveals, 0);
  moon[order[1]].raiseEvent(); assert.equal(reveals, 1);
  moon.initialTilesLoaded.raiseEvent(); moon.allTilesLoaded.raiseEvent(); moon.tileVisible.raiseEvent();
  assert.equal(reveals, 1);
  dispose(); assert.ok(Object.values(moon).every(event => event.listeners.size === 0));
});

test('disposing a pending Moon handoff prevents a late visible-content event', () => {
  const moon = tileset(); let reveals = 0;
  const dispose = observeMoonContent(moon, () => reveals++);
  moon.initialTilesLoaded.raiseEvent(); dispose(); moon.tileVisible.raiseEvent();
  assert.equal(reveals, 0);
});
