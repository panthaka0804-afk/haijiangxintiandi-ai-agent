<template>
  <div class="notfound">
    <div class="nf-code">404</div>
    <div class="nf-title">页面不存在</div>
    <div class="nf-desc">您访问的后台页面已被移除或路径有误，未找到对应模块。</div>
    <button class="nf-btn" @click="goHome">返回智能运营中心</button>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
const router = useRouter()
function goHome() { router.push({ name: 'admin-intelligence' }) }
</script>

<style scoped>
.notfound {
  min-height: 60vh; display: flex; flex-direction: column; align-items: center; justify-content: center;
  text-align: center; padding: 40px 20px; gap: 14px;
}
.nf-code {
  font-size: 96px; font-weight: 900; line-height: 1;
  background: linear-gradient(135deg, #FF7B2C, #E85D04);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; color: transparent;
}
.nf-title { font-size: 22px; font-weight: 700; color: #F2F2F2; }
.nf-desc { font-size: 14px; color: #999; max-width: 420px; line-height: 1.6; }
.nf-btn {
  margin-top: 10px; padding: 10px 24px; border-radius: 10px; cursor: pointer; font-size: 14px; font-weight: 600;
  color: #fff; border: none; background: linear-gradient(135deg, #FF7B2C, #E85D04); transition: .15s;
}
.nf-btn:hover { box-shadow: 0 6px 18px rgba(232, 93, 4, 0.4); }
</style>
