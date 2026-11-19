import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      // v1 pages: Express + SQLite demo backend (node server/index.js)
      '/api': 'http://localhost:3001',
      // Copilot page: the Python FastAPI service (make api)
      '/copilot-api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/copilot-api/, ''),
      },
    }
  }
})
