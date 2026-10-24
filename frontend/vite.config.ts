import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In sviluppo (npm run dev) le chiamate /api vanno al backend locale.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': process.env.API_URL ?? 'http://localhost:8000' },
  },
})
