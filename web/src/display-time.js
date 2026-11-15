// Match stored records by instant without interpolating or dropping microseconds.
function epochKey(value) {
  if (typeof value !== 'string') return undefined;
  const match = value.match(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.(\d{1,6}))?(?:Z|[+-]\d{2}:\d{2})$/);
  const milliseconds = Date.parse(value);
  if (!match || !Number.isFinite(milliseconds)) return undefined;
  return `${milliseconds}:${(match[1] ?? '').padEnd(6, '0').slice(3)}`;
}

export function sameDisplayEpoch(a, b) {
  if (a === b) return true;
  const left = epochKey(a);
  return left !== undefined && left === epochKey(b);
}
