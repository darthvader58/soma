if (new URLSearchParams(location.search).get('mode') === 'archive') {
  await import('./archive.js');
} else {
  await import('./workbench.js');
}
