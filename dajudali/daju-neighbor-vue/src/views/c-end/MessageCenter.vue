<template>
  <div class="msg-page">
    <van-nav-bar title="消息中心" left-text="返回" left-arrow @click-left="$router.back()" fixed placeholder>
      <template #right>
        <span v-if="unread" class="all-read" @click="readAll">全部已读</span>
      </template>
    </van-nav-bar>

    <div v-if="!phone" class="login-tip">
      <p>请先在会员中心绑定手机号后查看消息</p>
      <van-button round type="primary" @click="$router.push('/member')">去会员中心</van-button>
    </div>

    <template v-else>
      <div v-if="loading" class="loading-state">加载中...</div>
      <div v-else-if="!messages.length" class="empty">暂无消息</div>
      <div v-else class="msg-list">
        <div v-for="m in messages" :key="m.id" class="msg-card" :class="{ unread: !m.read }" @click="openMsg(m)">
          <span class="dot" v-if="!m.read"></span>
          <div class="msg-body">
            <div class="msg-title">{{ m.title }}</div>
            <div class="msg-text">{{ m.body }}</div>
            <div class="msg-time">{{ m.created_at }}</div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useMemberStore } from '@/stores/member'
import { showToast } from 'vant'
import { getMemberMessages, readMemberMessage } from '@/api'

const memberStore = useMemberStore()
const phone = ref('')
const loading = ref(true)
const messages = ref([])
const unread = ref(0)

onMounted(async () => {
  memberStore.restore()
  phone.value = memberStore.member?.phone || ''
  if (!phone.value) { loading.value = false; return }
  await load()
})

async function load() {
  loading.value = true
  try {
    const res = await getMemberMessages(phone.value)
    if (res.ok) {
      messages.value = res.messages || []
      unread.value = res.unread || 0
    }
  } catch {}
  loading.value = false
}

async function openMsg(m) {
  if (m.read) return
  try {
    await readMemberMessage(phone.value, m.id)
    m.read = 1
    unread.value = Math.max(0, unread.value - 1)
  } catch { showToast('操作失败') }
}

async function readAll() {
  try {
    await readMemberMessage(phone.value, 'all')
    messages.value.forEach(m => (m.read = 1))
    unread.value = 0
  } catch { showToast('操作失败') }
}
</script>

<style scoped>
.msg-page { min-height: 100vh; background: #000; padding-bottom: 20px; }
.all-read { font-size: 13px; color: #FFB877; font-weight: 600; cursor: pointer; }
.login-tip { text-align: center; padding: 80px 24px; color: rgba(255,255,255,0.6); }
.login-tip p { margin-bottom: 16px; font-size: 14px; }
.loading-state, .empty { text-align: center; padding: 40px 20px; color: rgba(255,255,255,0.5); font-size: 14px; }

.msg-list { padding: 12px 16px; display: flex; flex-direction: column; gap: 12px; }
.msg-card {
  position: relative; display: flex; gap: 12px; align-items: flex-start;
  background: #161616; border: 1px solid #2a2a2a; border-radius: 14px; padding: 14px 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
.msg-card.unread { border-color: #C9956C; background: #1c1714; }
.dot { position: absolute; right: 14px; top: 14px; width: 9px; height: 9px; border-radius: 50%; background: #FF7B2C; }
.msg-body { flex: 1; min-width: 0; }
.msg-title { font-size: 15px; font-weight: 700; color: #f2f2f2; margin-bottom: 4px; }
.msg-text { font-size: 13px; color: #bdbdbd; line-height: 1.55; }
.msg-time { font-size: 11px; color: #777; margin-top: 8px; }
</style>
