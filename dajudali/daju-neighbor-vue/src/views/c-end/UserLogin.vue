<template>
  <div class="login-page">
    <div class="login-card">
      <!-- 标题：完整中文「海江新天地」 -->
      <div class="login-head">
        <span class="brand-cn">海江新天地</span>
        <span class="brand-sub">用户登录</span>
      </div>

      <van-form @submit="onSubmit">
        <!-- 输入区：干净白底圆角块，去掉多余边框线 -->
        <div class="login-fields">
          <van-cell-group inset>
            <van-field
              v-model="form.username"
              name="username"
              label="用户名"
              placeholder="请输入用户名"
              :rules="[{ required: true, message: '请输入用户名' }]"
            />
            <van-field
              v-model="form.password"
              type="password"
              name="password"
              label="密码"
              placeholder="请输入密码"
              :rules="[{ required: true, message: '请输入密码' }]"
            />
          </van-cell-group>
        </div>

        <div class="login-btn-wrap">
          <van-button round block type="primary" native-type="submit" :loading="submitting">
            登 录
          </van-button>
        </div>
      </van-form>

      <div class="links">
        <span @click="$router.push('/register')">注册会员</span>
        <span @click="$router.push('/')">游客模式</span>
      </div>
      <div class="agree-line">
        <a href="/vue/user-agreement.html" target="_blank" rel="noopener">《用户协议》</a>
        <span class="dot">·</span>
        <a href="/vue/privacy-policy.html" target="_blank" rel="noopener">《隐私政策》</a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { login } from '@/api'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const submitting = ref(false)
const form = ref({ username: '', password: '' })

async function onSubmit() {
  submitting.value = true
  try {
    const res = await login(form.value.username, form.value.password)
    if (res.ok) {
      userStore.setUser(res.user)
      showToast('登录成功')
      router.push('/')
    } else {
      showToast(res.error || '用户名或密码错误')
    }
  } catch {
    showToast('网络错误')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
/* 页面背景：纯黑（整站统一） */
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000000;
  padding: 20px;
}

/* 登录卡片：与整站多彩实色卡同一语言（亮橙实色底 + 3px 同色边框 + 内高光 + 圆角18px + 投影） */
.login-card {
  width: 100%;
  max-width: 380px;
  background-color: #161618;
  border: 1px solid rgba(255, 255, 255, 0.10);
  border-radius: 18px;
  padding: 30px 22px 24px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

/* 标题块：完整中文「海江新天地」 */
.login-head { display: flex; flex-direction: column; align-items: center; margin-bottom: 22px; }
.brand-cn {
  font-family: var(--font-primary);
  font-size: 24px; font-weight: 800; letter-spacing: 1px; line-height: 1.2;
  color: #FFFFFF;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.4);
}
.brand-sub {
  font-size: 13px; font-weight: 400; color: rgba(255, 255, 255, 0.85); margin-top: 6px;
}

/* 输入区：干净白底圆角块（无多余框线） */
.login-fields {
  background: #0E0E10;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.10);
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.5);
}
:deep(.van-cell-group--inset) { margin: 0; background: transparent; }
:deep(.van-cell) { background: transparent; color: #fff; padding: 14px 12px; }
:deep(.van-cell::after) { border-color: rgba(255, 255, 255, 0.1); left: 12px; right: 12px; }
:deep(.van-field__label) { color: rgba(255, 255, 255, 0.7); width: 56px; }
:deep(.van-field__control) { color: #fff; font-size: var(--fs-body); }
:deep(.van-field__control::placeholder) { color: rgba(255, 255, 255, 0.4); }

/* 登录按钮：金棕凹陷（覆盖 Vant 默认 primary，禁止白色扁平按钮） */
.login-btn-wrap { margin: 18px 0 4px; }
:deep(.van-button--primary) {
  background: #9A7425;
  border: 3px solid #9A7425;
  border-radius: 20px !important;
  box-shadow: inset 3px 3px 7px rgba(0, 0, 0, 0.45), inset -2px -2px 5px rgba(196, 146, 58, 0.45);
  color: #fff; font-weight: 800; letter-spacing: 4px;
  filter: drop-shadow(0 0.6px 1px rgba(0, 0, 0, 0.4));
}
:deep(.van-button--primary:active) {
  box-shadow: inset 5px 5px 10px rgba(0, 0, 0, 0.55), inset -2px -2px 5px rgba(196, 146, 58, 0.35);
}

/* 底部链接：白色（橙卡上橙字看不清，改白） */
.links { display: flex; justify-content: center; gap: 24px; margin-top: 18px; }
.links span { color: rgba(255, 255, 255, 0.92); font-size: 13px; cursor: pointer; }

/* 协议入口 */
.agree-line { text-align: center; margin-top: 14px; font-size: 12px; color: rgba(255, 255, 255, 0.85); }
.agree-line a, .agree-line span { color: rgba(255, 255, 255, 0.85); cursor: pointer; text-decoration: none; }
.agree-line .dot { color: rgba(255, 255, 255, 0.5); margin: 0 6px; cursor: default; }
</style>
