import test from 'node:test';
import assert from 'node:assert/strict';
import { observeMoonContent } from '../../web/src/workbench-viewer.js';

class DisplayEvent {
  listeners = new Set();
  addEventListener(listener) { this.listeners.add(listener); return () => this.listeners.delete(listener); }
  raiseEvent() { for (const listener of this.listeners) listener(); }
}
const tileset = () => ({ initialTilesLoaded: new DisplayEvent(), allTilesLoaded: new DisplayEvent(), tileVisible: new DisplayEvent() });

test('first visible Moon content reveals once without waiting for settled LOD', () => {
  const moon = tileset(); let reveals = 0;
  const dispose = observeMoonContent(moon, () => reveals++);
  assert.equal(reveals, 0);
  moon.tileVisible.raiseEvent(); assert.equal(reveals, 1);
  moon.tileVisible.raiseEvent(); moon.allTilesLoaded.raiseEvent(); moon.initialTilesLoaded.raiseEvent();
  assert.equal(reveals, 1);
  dispose(); assert.ok(Object.values(moon).every(event => event.listeners.size === 0));
});

test('metadata and complete-loading events alone cannot hide the context Moon', () => {
  const moon = tileset(); let reveals = 0;
  const dispose = observeMoonContent(moon, () => reveals++);
  moon.initialTilesLoaded.raiseEvent(); moon.allTilesLoaded.raiseEvent();
  assert.equal(reveals, 0);
  moon.tileVisible.raiseEvent(); assert.equal(reveals, 1);
  dispose();
});

test('disposing a pending Moon handoff prevents a late visible-content event', () => {
  const moon = tileset(); let reveals = 0;
  const dispose = observeMoonContent(moon, () => reveals++);
  dispose(); moon.tileVisible.raiseEvent();
  assert.equal(reveals, 0);
  assert.ok(Object.values(moon).every(event => event.listeners.size === 0));
});
