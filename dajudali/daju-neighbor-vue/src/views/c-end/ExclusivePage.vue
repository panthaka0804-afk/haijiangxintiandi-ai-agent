<template>
  <div class="exclusive-page">
    <van-nav-bar title="会员专属" left-text="返回" left-arrow @click-left="$router.back()" fixed placeholder>
      <template #right>
        <van-button size="small" round plain @click="userStore.largeFont = !userStore.largeFont" :style="{ color: userStore.largeFont ? '#FFB877' : '#777', borderColor: userStore.largeFont ? '#FFB877' : '#444', fontWeight: '700' }">关怀模式</van-button>
      </template>
    </van-nav-bar>

    <!-- 会员专属内容（新品试吃 / 内测名额 / 专属体验），独立收纳于此界面 -->
    <MemberExclusive :hide-header="true" />
  </div>
</template>

<script setup>
import { useUserStore } from '@/stores/user'
import { useMemberStore } from '@/stores/member'
import MemberExclusive from '@/components/c-end/MemberExclusive.vue'

const userStore = useUserStore()
const memberStore = useMemberStore()
// 进入页面时先从 sessionStorage 恢复登录态（与首页/会员中心/更多页共享）
memberStore.restore()
</script>

<style scoped>
.exclusive-page {
  min-height: 100vh;
  background: #000;
}
:deep(.van-nav-bar) {
  background: #000000;
}
:deep(.van-nav-bar__title),
:deep(.van-nav-bar__text),
:deep(.van-nav-bar .van-icon) {
  color: #fff;
}
</style>
