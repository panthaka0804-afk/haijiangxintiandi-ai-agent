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
        <p>新人礼 · 注册即送 <b>500积分</b>，享普卡会员 <b>98折</b>优惠</p>
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
  background: #000000;
}

.tips {
  text-align: center;
  padding: 16px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 14px;
}

.tips b {
  color: #C4923A;
}

:deep(.van-nav-bar) {
  background: #000000;
}

:deep(.van-nav-bar__title),
:deep(.van-nav-bar__text),
:deep(.van-nav-bar .van-icon) {
  color: #fff;
}

/* 表单暗色化，与整站纯黑底+白字一致 */
:deep(.van-cell-group--inset) { background: #161618; border-radius: 12px; margin: 0 16px; }
:deep(.van-cell) { background: transparent; color: #fff; padding: 14px 12px; }
:deep(.van-cell::after) { border-color: rgba(255, 255, 255, 0.1); left: 12px; right: 12px; }
:deep(.van-field__label) { color: rgba(255, 255, 255, 0.7); width: 56px; }
:deep(.van-field__control) { color: #fff; font-size: var(--fs-body); }
:deep(.van-field__control::placeholder) { color: rgba(255, 255, 255, 0.4); }

/* 提交按钮：金棕凹陷（覆盖 Vant 默认 primary） */
:deep(.van-button--primary) {
  background: #9A7425;
  border: 3px solid #9A7425;
  border-radius: 20px !important;
  box-shadow: inset 3px 3px 7px rgba(0, 0, 0, 0.45), inset -2px -2px 5px rgba(196, 146, 58, 0.45);
  color: #fff; font-weight: 700; letter-spacing: 2px;
  filter: drop-shadow(0 0.6px 1px rgba(0, 0, 0, 0.4));
}
:deep(.van-button--primary:active) {
  box-shadow: inset 5px 5px 10px rgba(0, 0, 0, 0.55), inset -2px -2px 5px rgba(196, 146, 58, 0.35);
}
</style>
