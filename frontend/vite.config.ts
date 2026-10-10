import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The backend runs on :8000; proxying keeps the frontend free of absolute URLs and CORS.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': { target: 'ws://localhost:8000', ws: true },
    },
  },
})
