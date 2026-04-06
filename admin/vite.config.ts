import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@zhiqu/shared': resolve(__dirname, '../packages/shared/src'),
    },
  },
  server: {
    port: 3001,
    host: true,
    allowedHosts: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
    },
  },
  optimizeDeps: {
    exclude: ['@zhiqu/shared'],
  },
});
