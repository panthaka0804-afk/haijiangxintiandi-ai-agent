<template>
  <!-- 遮罩 -->
  <van-overlay :show="visible" @click="$emit('close')" z-index="1000" />

  <!-- 底部弹出表单 -->
  <transition name="ls-popup">
    <div v-if="visible" class="ls-container">
      <div class="ls-sheet" @click.stop>
        <!-- 拖拽条 -->
        <div class="ls-handle"></div>

        <!-- 标题 + 切换 -->
        <div class="ls-header">
          <h3>{{ mode === 'login' ? '会员登录' : '会员注册' }}</h3>
          <span class="ls-switch" @click="toggleMode">
            {{ mode === 'login' ? '没有账号？去注册 →' : '已有账号？去登录 →' }}
          </span>
        </div>

        <!-- 登录表单 -->
        <template v-if="mode === 'login'">
          <van-cell-group inset>
            <van-field
              v-model="form.phone"
              label="手机号"
              type="tel"
              maxlength="11"
              placeholder="请输入手机号"
              :rules="[{ required: true, message: '请输入手机号' }]"
            />
            <van-field
              v-model="form.code"
              label="验证码"
              maxlength="6"
              placeholder="请输入验证码"
              :rules="[{ required: true, message: '请输入验证码' }]"
            >
              <template #button>
                <van-button
                  size="small"
                  color="#FF8C00" style="background:#FF8C00;border-color:#FF8C00;color:#fff"
                  :disabled="codeSending || codeCountdown > 0"
                  @click="sendCode"
                >
                  {{ codeCountdown > 0 ? codeCountdown + 's' : '获取验证码' }}
                </van-button>
              </template>
            </van-field>
          </van-cell-group>
          <div class="ls-submit">
            <van-button
              round
              block
              color="#FF8C00" style="background:#FF8C00;border-color:#FF8C00;color:#fff"
              :loading="loading"
              @click="doLogin"
            >
              登 录
            </van-button>
          </div>
        </template>

        <!-- 注册表单 -->
        <template v-else>
          <van-cell-group inset>
            <van-field
              v-model="form.name"
              label="姓名"
              placeholder="请输入您的姓名"
              :rules="[{ required: true, message: '请输入姓名' }]"
            />
            <van-field
              v-model="form.phone"
              label="手机号"
              type="tel"
              maxlength="11"
              placeholder="请输入手机号"
              :rules="[{ required: true, message: '请输入手机号' }]"
            />
          </van-cell-group>
          <div class="ls-submit">
            <van-button
              round
              block
              color="#FF8C00" style="background:#FF8C00;border-color:#FF8C00;color:#fff"
              :loading="loading"
              loading-text="注册中..."
              @click="doRegister"
            >
              注 册
            </van-button>
          </div>
          <div class="ls-tip">
            注册即送 <b>500积分</b>，享普卡会员 <b>98折</b>优惠
          </div>
        </template>

        <button class="ls-close" @click="$emit('close')">关闭</button>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, watch } from 'vue'
import { showToast } from 'vant'

const props = defineProps({
  visible: Boolean
})

const emit = defineEmits(['close', 'loginSuccess'])

const mode = ref('login')
const loading = ref(false)
const codeSending = ref(false)
const codeCountdown = ref(0)
const form = ref({ phone: '', name: '', code: '' })

// 弹窗打开时重置
watch(() => props.visible, (v) => {
  if (v) {
    form.value = { phone: '', name: '', code: '' }
    loading.value = false
    codeCountdown.value = 0
  }
})

function toggleMode() {
  mode.value = mode.value === 'login' ? 'register' : 'login'
  form.value = { phone: '', name: '', code: '' }
  codeCountdown.value = 0
}

function sendCode() {
  const phone = form.value.phone.trim()
  if (!phone) { showToast('请先输入手机号'); return }
  if (!/^1\d{10}$/.test(phone)) { showToast('手机号格式不正确'); return }

  codeSending.value = true
  // 模拟发送验证码（后端以后接短信服务）
  setTimeout(() => {
    codeSending.value = false
    showToast('验证码已发送（演示模式：123456）')
    codeCountdown.value = 60
    const timer = setInterval(() => {
      codeCountdown.value--
      if (codeCountdown.value <= 0) {
        clearInterval(timer)
      }
    }, 1000)
  }, 800)
}

function validatePhone() {
  const phone = form.value.phone.trim()
  if (!phone) { showToast('请输入手机号'); return false }
  if (!/^1\d{10}$/.test(phone)) { showToast('手机号格式不正确'); return false }
  return true
}

async function doLogin() {
  if (!validatePhone()) return
  const code = form.value.code.trim()
  if (!code) { showToast('请输入验证码'); return }
  if (code !== '123456') { showToast('验证码错误（演示模式：123456）'); return }

  loading.value = true

  // 调用 store 的 login
  const { useMemberStore } = await import('@/stores/member')
  const memberStore = useMemberStore()
  const res = await memberStore.loginByPhone(form.value.phone)

  loading.value = false
  if (res.ok) {
    showToast('登录成功')
    emit('loginSuccess', memberStore.member)
    emit('close')
  } else {
    showToast(res.error || '该手机号未注册会员')
  }
}

async function doRegister() {
  const phone = form.value.phone.trim()
  const name = form.value.name.trim()
  if (!phone) { showToast('请输入手机号'); return false }
  if (!/^1\d{10}$/.test(phone)) { showToast('手机号格式不正确'); return false }
  if (!name) { showToast('请输入姓名'); return false }

  loading.value = true

  const { useMemberStore } = await import('@/stores/member')
  const memberStore = useMemberStore()
  const res = await memberStore.register(name, phone)

  loading.value = false
  if (res.ok) {
    showToast('注册成功！500积分已到账')
    emit('loginSuccess', memberStore.member)
    emit('close')
  } else {
    showToast(res.error || '注册失败')
  }
}
</script>

<style scoped>
/* 容器：底部弹出 */
.ls-container {
  position: fixed;
  bottom: 0;
  left: 0;
  width: 100%;
  z-index: 1001;
}

.ls-sheet {
  background: #fff;
  border-radius: 20px 20px 0 0;
  padding: 24px;
  max-height: 70vh;
  overflow-y: auto;
}

/* 拖拽条 */
.ls-handle {
  width: 36px;
  height: 4px;
  background: #ddd;
  border-radius: 2px;
  margin: 0 auto 16px;
}

/* 标题 */
.ls-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.ls-header h3 {
  font-size: 18px;
  color: #333;
  margin: 0;
}

.ls-switch {
  font-size: 13px;
  color: #FF7B2C;
  cursor: pointer;
}

.ls-submit {
  margin: 16px;
}

.ls-tip {
  text-align: center;
  font-size: 13px;
  color: #999;
  padding: 0 16px;
}

.ls-tip b {
  color: #FF7B2C;
}

.ls-close {
  display: block;
  width: 100%;
  padding: 10px;
  background: #eee;
  border: none;
  border-radius: 10px;
  margin-top: 12px;
  color: #666;
  font-size: 14px;
  cursor: pointer;
  font-family: inherit;
}

/* 动画 */
.ls-popup-enter-active,
.ls-popup-leave-active {
  transition: all 0.3s ease;
}

.ls-popup-enter-from .ls-sheet,
.ls-popup-leave-to .ls-sheet {
  transform: translateY(100%);
}
</style>
