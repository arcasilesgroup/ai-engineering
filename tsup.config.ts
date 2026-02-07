import { defineConfig } from 'tsup';

export default defineConfig([
  {
    entry: { 'cli/index': 'src/cli/index.ts' },
    format: ['esm'],
    target: 'node20',
    outDir: 'dist',
    clean: true,
    splitting: true,
    sourcemap: true,
    dts: true,
    shims: false,
    banner: {
      js: '#!/usr/bin/env node',
    },
  },
  {
    entry: { index: 'src/compiler/index.ts' },
    format: ['esm'],
    target: 'node20',
    outDir: 'dist',
    splitting: true,
    sourcemap: true,
    dts: true,
    shims: false,
  },
]);
