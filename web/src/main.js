const entryURL = new URL(location.href);
if (entryURL.searchParams.get('mode') === 'archive') {
  history.replaceState(null, '', '/');
}

await import('./workbench.js');
