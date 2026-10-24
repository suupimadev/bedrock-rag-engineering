// Docker Compose内では "api" というサービス名で、ローカル直接起動時は localhost で解決する
const apiTarget = process.env.API_PROXY_TARGET ?? 'http://localhost:8000'

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },
  ssr: false,
  modules: ['@ant-design-vue/nuxt'],
  css: ['ant-design-vue/dist/reset.css', '~/assets/css/main.css'],
  devServer: {
    host: '0.0.0.0',
    port: 5173,
  },
  nitro: {
    devProxy: {
      '/api/chat': { target: `${apiTarget}/chat`, changeOrigin: true },
      '/api/health': { target: `${apiTarget}/health`, changeOrigin: true },
    },
  },
})
