import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],

  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },

  server: {
    port: 5173,
    // Proxy API calls (incl. SSE streams, same /api prefix) to FastAPI.
    // Configurable via VITE_BACKEND_PORT (default: 8000)
    proxy: {
      '/api': {
        target: `http://localhost:${process.env.VITE_BACKEND_PORT || process.env.BACKEND_PORT || '8000'}`,
        changeOrigin: true,
        secure: false,
      },
    },
  },

  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        // Split vendor chunks for better caching
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'query-vendor': ['@tanstack/react-query'],
          'chart-vendor': ['recharts'],
          'motion-vendor': ['motion/react'],
          'ui-vendor': ['lucide-react', 'clsx', 'date-fns', 'axios'],
        },
      },
    },
  },
})
