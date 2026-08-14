<template>
  <div class="admin-login">
    <div class="login-glow login-glow-1"></div>
    <div class="login-glow login-glow-2"></div>
    <div class="login-glow login-glow-3"></div>

    <div class="login-box">
      <div class="login-bar"></div>
      <div class="login-logo">
        <span class="icon">🦊</span>
        <h2>海江新天地</h2>
        <p>后台管理系统</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" size="large" @submit.prevent="onSubmit">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" prefix-icon="User" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码" prefix-icon="Lock" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" native-type="submit" :loading="submitting" class="login-btn">
            登 录
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login } from '@/api'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref(null)
const submitting = ref(false)
const form = ref({ username: 'demo', password: 'demo123' })

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

async function onSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const res = await login(form.value.username, form.value.password, true)
    if (res.ok) {
      userStore.setUser(res.user)
      ElMessage.success('登录成功')
      router.push('/admin')
    } else {
      ElMessage.error(res.error || '用户名或密码错误')
    }
  } catch {
    ElMessage.error('网络错误')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.admin-login {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at 50% 30%, #161210 0%, #000000 70%);
}

/* 彩色光晕（呼应 C 端多彩） */
.login-glow { position: absolute; border-radius: 50%; filter: blur(80px); opacity: 0.5; pointer-events: none; }
.login-glow-1 { width: 360px; height: 360px; background: #FF7B2C; top: -80px; left: -60px; }
.login-glow-2 { width: 300px; height: 300px; background: #9B4A3E; bottom: -60px; right: -40px; }
.login-glow-3 { width: 260px; height: 260px; background: #C4923A; bottom: 40px; left: 30%; opacity: 0.32; }

.login-box {
  position: relative;
  width: 400px;
  max-width: 90vw;
  background: rgba(18, 18, 18, 0.92);
  border: 1px solid rgba(255, 123, 44, 0.22);
  border-radius: 16px;
  padding: 40px;
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(8px);
  overflow: hidden;
}

.login-bar {
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 4px;
  background: linear-gradient(90deg, #FF7B2C, #C4923A, #D4A59A);
}

.login-logo {
  text-align: center;
  margin-bottom: 32px;
}
.login-logo .icon {
  font-size: 48px;
}
.login-logo h2 {
  font-size: 24px;
  margin: 8px 0 4px;
  background: linear-gradient(135deg, #FF7B2C, #E85D04);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  color: transparent;
}
.login-logo p {
  color: #999;
  font-size: 14px;
}

.login-btn {
  width: 100%;
}

.admin-login .el-button--primary {
  background: linear-gradient(135deg, #FF7B2C, #E85D04) !important;
  border: none !important;
  box-shadow: 0 8px 20px rgba(232, 93, 4, 0.35) !important;
  color: #fff !important;
}
.admin-login .el-input__wrapper.is-focus {
  box-shadow: 0 0 0 1px #FF7B2C inset, 0 0 0 3px rgba(255, 123, 44, 0.18) !important;
}
</style>
