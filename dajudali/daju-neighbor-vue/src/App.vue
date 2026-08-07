<template>
  <router-view />
</template>

<script setup>
import { onMounted } from 'vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

onMounted(async () => {
  await userStore.checkSession()
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB',
    'Microsoft YaHei', 'Helvetica Neue', Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  font-size: 14px;
}

#app {
  height: 100vh;
}

/* 大字模式：整体 zoom 2 倍 */
html[data-large] body {
  zoom: 2;
}
/* 修正 zoom 放大后的溢出 */
html[data-large] .tb-row { flex-wrap: wrap; }
html[data-large] .tb-btn { padding: 6px 2px; font-size: 8px; }
html[data-large] .search-row { flex-wrap: wrap; }
html[data-large] .search-btn { padding: 8px 4px; }
html[data-large] .search-btn-text { font-size: 10px; }
html[data-large] .chat-input-area { font-size: 9px; }
html[data-large] .chat-messages { font-size: 10px; }
</style>
