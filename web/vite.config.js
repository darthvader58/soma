import { defineConfig } from 'vite';

export default defineConfig({
  server: { port: 5173, strictPort: true },
  preview: { port: 4173, strictPort: true },
  define: { CESIUM_BASE_URL: JSON.stringify('/cesium/') },
  build: { chunkSizeWarningLimit: 5000 },
});
