import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  build: {
    chunkSizeWarningLimit: 650,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (
            id.includes('/node_modules/antd/') ||
            id.includes('/node_modules/@ant-design/') ||
            id.includes('/node_modules/rc-') ||
            id.includes('/node_modules/@rc-component/')
          ) {
            return 'ant-design'
          }
          if (id.includes('/node_modules/react') || id.includes('/node_modules/scheduler/')) {
            return 'react-vendor'
          }
          if (id.includes('/node_modules/@tanstack/')) return 'tanstack-query'
        },
      },
    },
  },
  test: {
    environment: 'node',
  },
})
