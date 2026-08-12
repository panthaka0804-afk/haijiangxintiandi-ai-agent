<template>
  <div class="hca-root">
    <div class="hca-hdr">
      <h2>人工客服工作台</h2>
      <button class="hca-refresh" @click="loadSessions">刷新</button>
    </div>

    <div class="hca-layout">
      <!-- 左侧：会话列表 -->
      <div class="hca-sidebar">
        <div class="hca-side-hdr">待处理会话 ({{ sessions.length }})</div>
        <div v-for="s in sessions" :key="s.session_id" class="hca-session" :class="{ active: activeSid === s.session_id }" @click="openSession(s)">
          <div class="hca-ses-name">{{ s.user_name || s.user_phone || '匿名用户' }}</div>
          <div class="hca-ses-msg">{{ s.last_msg?.slice(0, 40) || '无消息' }}</div>
          <div class="hca-ses-meta">
            <span>{{ s.last_time?.slice(5, 16) || '' }}</span>
            <span class="hca-ses-badge" v-if="!s.agent_replies">新会话</span>
          </div>
        </div>
        <div v-if="!sessions.length" class="hca-empty">暂无人工客服会话</div>
      </div>

      <!-- 右侧：聊天区 -->
      <div class="hca-chat">
        <template v-if="activeSid">
          <div class="hca-chat-hdr">
            <span>{{ activeSession?.user_name || activeSession?.user_phone || '匿名用户' }}</span>
            <span class="hca-chat-phone" v-if="activeSession?.user_phone">{{ activeSession.user_phone }}</span>
          </div>
          <div class="hca-msgs" ref="msgBox">
            <div v-if="!messages.length" class="hca-empty">选择左侧会话开始回复</div>
            <div v-for="m in messages" :key="m.id" :class="['hca-msg', m.role === 'agent' ? 'agent' : 'user']">
              <div class="hca-msg-bubble">{{ m.content }}</div>
              <div class="hca-msg-time">{{ m.created_at?.slice(5, 16) || '' }}</div>
            </div>
            <div v-if="sending" class="hca-msg agent">
              <div class="hca-msg-bubble sending">发送中...</div>
            </div>
          </div>
          <div class="hca-input-row">
            <textarea v-model="replyText" @keydown.enter.exact.prevent="sendReply" placeholder="输入回复... (Enter 发送)" rows="2" class="hca-input"></textarea>
            <button class="hca-send" @click="sendReply" :disabled="!replyText.trim()">发送</button>
          </div>
        </template>
        <div v-else class="hca-empty">选择左侧会话开始回复</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, onUnmounted } from 'vue'

const sessions = ref([])
const messages = ref([])
const activeSid = ref('')
const activeSession = ref(null)
const replyText = ref('')
const sending = ref(false)
const msgBox = ref(null)
let pollTimer = null

async function loadSessions() {
  try {
    const resp = await fetch('/api/admin/human-chats')
    const data = await resp.json()
    if (data.ok) sessions.value = data.data
  } catch {}
}

function openSession(s) {
  activeSid.value = s.session_id
  activeSession.value = s
  replyText.value = ''
  loadMessages()
}

async function loadMessages() {
  if (!activeSid.value) return
  try {
    const resp = await fetch('/api/human-chat/session?session_id=' + activeSid.value)
    const data = await resp.json()
    if (data.ok) messages.value = data.data.messages || []
    await nextTick()
    if (msgBox.value) msgBox.value.scrollTop = msgBox.value.scrollHeight
  } catch {}
}

async function sendReply() {
  const text = replyText.value.trim()
  if (!text || !activeSid.value) return
  sending.value = true
  try {
    await fetch('/api/human-chat/reply', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: activeSid.value, message: text })
    })
    replyText.value = ''
    await loadMessages()
    await loadSessions()
  } catch { alert('发送失败') }
  sending.value = false
}

onMounted(() => {
  loadSessions()
  pollTimer = setInterval(() => { loadSessions(); if (activeSid.value) loadMessages() }, 8000)
})
onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })
</script>

<style scoped>
.hca-root { height: 100vh; display: flex; flex-direction: column; background: #0a0a0a; color: #e0e0e0; font-family: 'PingFang SC', sans-serif; }
.hca-hdr { display: flex; justify-content: space-between; align-items: center; padding: 14px 20px; background: #111; border-bottom: 1px solid #222; }
.hca-hdr h2 { margin: 0; font-size: 18px; color: #C4923A; }
.hca-refresh { padding: 6px 14px; border-radius: 6px; border: 1px solid #444; background: #222; color: #ccc; cursor: pointer; font-size: 13px; }

.hca-layout { display: flex; flex: 1; overflow: hidden; }
.hca-sidebar { width: 280px; border-right: 1px solid #222; overflow-y: auto; flex-shrink: 0; }
.hca-side-hdr { padding: 12px 16px; font-size: 13px; color: #888; border-bottom: 1px solid #1a1a1a; }
.hca-session { padding: 12px 16px; cursor: pointer; border-bottom: 1px solid #1a1a1a; transition: background 0.15s; }
.hca-session:hover { background: #141414; }
.hca-session.active { background: #1a1810; border-left: 3px solid #C4923A; }
.hca-ses-name { font-size: 14px; color: #ddd; font-weight: 500; }
.hca-ses-msg { font-size: 12px; color: #777; margin: 4px 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.hca-ses-meta { display: flex; justify-content: space-between; font-size: 11px; color: #555; }
.hca-ses-badge { color: #E8552A; font-weight: 600; }

.hca-chat { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.hca-chat-hdr { padding: 12px 20px; border-bottom: 1px solid #222; font-size: 15px; color: #ddd; display: flex; justify-content: space-between; }
.hca-chat-phone { font-size: 12px; color: #888; }
.hca-msgs { flex: 1; overflow-y: auto; padding: 16px 20px; display: flex; flex-direction: column; gap: 12px; }
.hca-msg { max-width: 75%; }
.hca-msg.user { align-self: flex-end; }
.hca-msg.agent { align-self: flex-start; }
.hca-msg-bubble { padding: 10px 14px; border-radius: 10px; font-size: 14px; line-height: 1.5; }
.hca-msg.user .hca-msg-bubble { background: #C4923A; color: #fff; border-bottom-right-radius: 3px; }
.hca-msg.agent .hca-msg-bubble { background: #2a2a2a; color: #ddd; border-bottom-left-radius: 3px; }
.hca-msg-bubble.sending { opacity: 0.5; }
.hca-msg-time { font-size: 10px; color: #555; margin-top: 4px; padding: 0 4px; }
.hca-msg.user .hca-msg-time { text-align: right; }

.hca-input-row { display: flex; gap: 10px; padding: 12px 20px; border-top: 1px solid #222; background: #111; }
.hca-input { flex: 1; padding: 10px 12px; border-radius: 8px; border: 1px solid #333; background: #1a1a1a; color: #ddd; font-size: 14px; resize: none; }
.hca-input::placeholder { color: #555; }
.hca-send { padding: 8px 20px; border-radius: 8px; border: none; background: #C4923A; color: #fff; font-size: 14px; font-weight: 600; cursor: pointer; }
.hca-send:disabled { opacity: 0.4; cursor: default; }

.hca-empty { text-align: center; color: #555; padding: 40px; font-size: 14px; }
</style>
