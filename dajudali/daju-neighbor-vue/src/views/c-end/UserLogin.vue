<template>
  <div class="login-page">
    <div class="login-card">
      <div class="logo-area">
        <span class="logo-icon">🦊</span>
        <h1>海江新天地</h1>
        <p>用户登录</p>
      </div>

      <van-form @submit="onSubmit">
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

        <div style="margin: 16px">
          <van-button round block type="primary" native-type="submit" :loading="submitting">
            登 录
          </van-button>
        </div>
      </van-form>

      <div class="links">
        <span @click="$router.push('/register')">注册会员</span>
        <span @click="$router.push('/')">游客模式</span>
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
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #1A1A1A;
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 380px;
  background: #222222;
  border-radius: 20px;
  padding: 30px 20px;
  box-shadow: 0 8px 30px #999999;
}

.logo-area {
  text-align: center;
  margin-bottom: 24px;
}

.logo-icon {
  font-size: 48px;
}

.logo-area h1 {
  font-size: 24px;
  color: #999999;
  margin: 8px 0 4px;
}

.logo-area p {
  color: #777;
  font-size: 14px;
}

.links {
  display: flex;
  justify-content: center;
  gap: 24px;
  margin-top: 8px;
}

.links span {
  color: #999999;
  font-size: 13px;
  cursor: pointer;
}
</style>
