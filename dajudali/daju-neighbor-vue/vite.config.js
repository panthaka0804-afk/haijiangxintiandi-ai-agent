import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import legacy from '@vitejs/plugin-legacy'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import { VantResolver } from '@vant/auto-import-resolver'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  base: './',
  plugins: [
    vue(),
    legacy({
      targets: ['iOS >= 9', 'Android >= 5', 'Chrome >= 55'],
      additionalLegacyPolyfills: ['regenerator-runtime/runtime'],
      modernPolyfills: true
    }),
    AutoImport({
      resolvers: [ElementPlusResolver(), VantResolver()]
    }),
    Components({
      resolvers: [ElementPlusResolver(), VantResolver()]
    })
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  build: {
    target: 'es2015',
    cssTarget: 'chrome56',
    cssCodeSplit: false
  },
  server: {
    port: 5173,
    allowedHosts: true,
    proxy: {
      '/api': 'http://localhost:8765',
      '/login': 'http://localhost:8765',
      '/logout': 'http://localhost:8765'
    }
  },
  preview: {
    port: 4173,
    allowedHosts: true,
    proxy: {
      '/api': 'http://localhost:8765',
      '/login': 'http://localhost:8765',
      '/logout': 'http://localhost:8765'
    }
  }
})
