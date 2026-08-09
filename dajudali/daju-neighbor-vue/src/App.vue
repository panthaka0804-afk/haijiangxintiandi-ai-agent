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

/* 大字模式（关怀模式）
   - 桌面端：整页 zoom 2（用户认可网页端 OK），字体与按钮同步放大且不变形
   - 移动端：窄屏整页 zoom 2 会把有效可视宽度砍掉一半，所有内容被挤进半屏串行/重叠（即"乱"）。
             故移动端关闭 zoom，改为放大字号与按钮尺寸、保持单栏自适应，
             效果等同放大且不变形、不乱、券码可换行 */
html[data-large] {
  zoom: 2;
}

@media (max-width: 820px) {
  /* 移动端：关掉整页缩放，避免半屏挤压导致串行/重叠 */
  html[data-large] {
    zoom: 1 !important;
  }
  html[data-large] body {
    font-size: 22px;
    line-height: 1.7;
  }
  /* 放大 vant 组件字号（!important 压过组件默认 px） */
  html[data-large] .van-button {
    font-size: 19px !important;
    min-height: 48px;
    padding: 0 20px;
  }
  html[data-large] .van-cell__title,
  html[data-large] .van-cell__label,
  html[data-large] .van-field__label,
  html[data-large] .van-field__control {
    font-size: 18px !important;
  }
  html[data-large] .van-cell__value {
    font-size: 16px !important;
    white-space: normal !important;
    word-break: break-all;
  }
  html[data-large] .van-nav-bar__title {
    font-size: 21px !important;
  }
  html[data-large] .van-tabbar-item__text,
  html[data-large] .van-tab__text {
    font-size: 15px !important;
  }
  /* 放大本项目主要页面类（会员中心 / 更多页 / 首页按钮等） */
  html[data-large] .card-name,
  html[data-large] .info-row,
  html[data-large] .member-hint,
  html[data-large] .uc-name,
  html[data-large] .uc-points,
  html[data-large] .fn-label,
  html[data-large] .level-badge,
  html[data-large] .dd-btn,
  html[data-large] .biz-hero-btn {
    font-size: 18px !important;
  }
  html[data-large] .info-row .value.highlight,
  html[data-large] .card-name {
    font-size: 24px !important;
  }
}
</style>
