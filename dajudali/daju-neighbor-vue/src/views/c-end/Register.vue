<template>
  <div class="register-page">
    <van-nav-bar title="注册会员" left-text="返回" left-arrow @click-left="$router.back()" fixed placeholder />

    <van-form @submit="onSubmit" style="margin-top: 20px;">
      <van-cell-group inset>
        <van-field
          v-model="form.displayName"
          name="displayName"
          label="姓名"
          placeholder="请输入您的姓名"
          :rules="[{ required: true, message: '请输入姓名' }]"
        />
        <van-field
          v-model="form.phone"
          name="phone"
          label="手机号"
          type="tel"
          maxlength="11"
          placeholder="请输入手机号"
          :rules="[
            { required: true, message: '请输入手机号' },
            { pattern: /^1\d{10}$/, message: '手机号格式不正确' }
          ]"
        />
      </van-cell-group>

      <div style="margin: 16px">
        <van-button round block type="primary" native-type="submit" :loading="submitting">
          注 册
        </van-button>
      </div>

      <div class="tips">
        <p>🎁 注册即送 <b>500积分</b>，享普卡会员 <b>98折</b>优惠</p>
      </div>
    </van-form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { registerMember } from '@/api'

const router = useRouter()
const submitting = ref(false)
const form = ref({ displayName: '', phone: '' })

async function onSubmit() {
  submitting.value = true
  try {
    const res = await registerMember(form.value.displayName, form.value.phone)
    if (res.ok) {
      showToast('注册成功！')
      setTimeout(() => router.push('/'), 1500)
    } else {
      showToast(res.error || '注册失败')
    }
  } catch {
    showToast('网络错误')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.register-page {
  min-height: 100vh;
  background: #1A1A1A;
}

.tips {
  text-align: center;
  padding: 16px;
  color: #AAA;
  font-size: 14px;
}

.tips b {
  color: #999999;
}

:deep(.van-nav-bar) {
  background: linear-gradient(135deg, #1A1A1A, #1A1A1A);
}

:deep(.van-nav-bar__title),
:deep(.van-nav-bar__text),
:deep(.van-nav-bar .van-icon) {
  color: #fff;
}
</style>
