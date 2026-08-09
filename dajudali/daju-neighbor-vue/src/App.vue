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

/* 大字模式（关怀模式）：整页等比放大，手机端兼容、不变形
   - 作用在 html 而非 body：position:fixed 的导航栏/底部 Tab 也会一起等比缩放，避免错位
   - 用 zoom 整体放大，字体与按钮同步变大且保持比例（不会拉伸变形）
   - 移除原先对聊天/工具栏手动缩到 8~10px 的规则（那会在手机端把文字缩成无法阅读的乱状） */
html[data-large] {
  zoom: 2;
}
</style>
