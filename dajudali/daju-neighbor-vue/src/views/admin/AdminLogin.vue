<template>
  <div class="admin-login">
    <div class="login-box">
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
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1A1A1A 0%, #1A1A1A 100%);
}

.login-box {
  width: 400px;
  background: #1A1A1A;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.08);
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
  color: #999999;
  margin: 8px 0 4px;
}

.login-logo p {
  color: #999;
  font-size: 14px;
}

.login-btn {
  width: 100%;
}
</style>
