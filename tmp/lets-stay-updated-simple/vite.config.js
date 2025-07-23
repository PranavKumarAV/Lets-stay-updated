import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react()],
  root: 'client',
  build: {
    outDir: '../dist/public',
    emptyOutDir: true,
  },
  resolve: {
    alias: {
      '@': resolve(process.cwd(), 'client/src'),
      '@assets': resolve(process.cwd(), 'attached_assets'),
    },
  },
})