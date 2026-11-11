import react from '@vitejs/plugin-react';
import { resolve } from 'node:path';
import { defineConfig } from 'vite';

// Self-contained IIFE bundle (React included, CSS inlined into the JS for the
// Shadow DOM) written straight into the Python package's static folder.
export default defineConfig({
  plugins: [react()],
  define: { 'process.env.NODE_ENV': JSON.stringify('production') },
  build: {
    outDir: resolve(__dirname, '../src/snapnote/static/snapnote'),
    emptyOutDir: false,
    lib: {
      entry: resolve(__dirname, 'src/main.tsx'),
      name: 'Snapnote',
      formats: ['iife'],
      fileName: () => 'snapnote.js',
    },
    minify: true,
  },
  test: { environment: 'jsdom' },
});
