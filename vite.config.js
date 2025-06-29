import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist', // ✅ important for Vercel
    emptyOutDir: true
  },
  server: {
    port: 3000
  }
});
