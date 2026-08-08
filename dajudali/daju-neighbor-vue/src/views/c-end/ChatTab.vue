<template>
  <div class="chat-tab">
    <!-- 聊天消息 -->
    <div class="chat-messages" ref="msgContainer">
      <div
        v-for="(msg, i) in chatStore.messages"
        :key="i"
        class="message-wrapper"
        :class="msg.role"
      >
        <template v-if="msg.role === 'user'">
          <div class="msg-bubble user-bubble">{{ msg.content }}</div>
        </template>
        <template v-else>
          <div class="msg-avatar"><SvgIcon name="message" :size="22" color="#9E9E9E" /></div>
          <div class="msg-bubble ai-bubble" v-html="formatMsg(msg.content)"></div>
          <!-- 智能快捷操作按钮 -->
          <div v-if="getQuickActions(msg.content).length" class="quick-actions-row">
            <button
              v-for="(act, ai) in getQuickActions(msg.content)"
              :key="ai"
              class="quick-action-btn"
              @click="doQuickAction(act)"
            >
              <svg class="qa-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <template v-if="act.label === '车辆管理'">
                  <rect x="1" y="3" width="15" height="13"/>
                  <polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/>
                  <circle cx="5.5" cy="18.5" r="2.5"/>
                  <circle cx="18.5" cy="18.5" r="2.5"/>
                </template>
                <template v-else-if="act.label === '积分商城'">
                  <polyline points="20 12 20 22 4 22 4 12"/>
                  <rect x="2" y="7" width="20" height="5"/>
                  <line x1="12" y1="22" x2="12" y2="7"/>
                  <path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z"/>
                  <path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z"/>
                </template>
                <template v-else-if="act.label === '优惠活动'">
                  <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/>
                  <line x1="7" y1="7" x2="7.01" y2="7"/>
                </template>
                <template v-else-if="act.label === '会员中心'">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                  <circle cx="12" cy="7" r="4"/>
                </template>
              </svg>
              {{ act.label }}
            </button>
          </div>
          <div v-if="msg.card" class="ai-card" @click.stop="onCardClick($event, msg.card)">
            <div
              v-for="(item, idx) in msg.card.items"
              :key="idx"
              class="ai-card-item"
            >
              <div class="ai-card-left">
                <div class="ai-card-name">{{ item.name }}</div>
                <div class="ai-card-desc">{{ item.desc || item.time }}</div>
              </div>
              <div class="ai-card-right">
                <span class="ai-card-tag">{{ item.tag }}</span>
                <span class="ai-card-price">{{ item.price }}</span>
              </div>
            </div>
            <div class="ai-card-footer">{{ msg.card.footer }}</div>
          </div>
        </template>
        <div class="msg-time">{{ msg.time }}</div>
      </div>

      <!-- 打字动画 -->
      <div class="message-wrapper ai" v-if="typing">
        <div class="msg-avatar"><SvgIcon name="message" :size="22" color="#9E9E9E" /></div>
        <div class="msg-bubble ai-bubble typing-bubble">
          <span class="dot"></span><span class="dot"></span><span class="dot"></span>
        </div>
      </div>
    </div>

    <!-- 底部输入 微信风格 -->
    <div class="input-area">
      <!-- 语音模式 -->
      <div v-if="voiceMode" class="voice-input">
        <div class="voice-text-panel" v-if="recording || liveText">
          <div class="voice-text">{{ liveText || '正在聆听...' }}</div>
          <div class="voice-waves-inline">
            <span v-for="i in 5" :key="i" class="wave-bar-inline" :style="{ animationDelay: (i * 0.12) + 's' }"></span>
          </div>
        </div>
        <div class="voice-label" v-else>按住 说话</div>
        <button
          class="voice-btn"
          @touchstart.prevent="startVoice"
          @touchend.prevent="stopVoice"
          @mousedown.prevent="startVoice"
          @mouseup.prevent="stopVoice"
          @touchcancel.prevent="stopVoice"
          @contextmenu.prevent
        >
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" :stroke="recording ? '#fff' : '#9E9E9E'" stroke-width="1.5" stroke-linecap="round">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
            <line x1="12" y1="19" x2="12" y2="23"/>
            <line x1="8" y1="23" x2="16" y2="23"/>
          </svg>
        </button>
        <!-- 语音模式下也保留文字输入 -->
        <div class="voice-text-input-row">
          <input
            v-model="inputText"
            class="voice-mini-input"
            type="text"
            placeholder="或直接打字..."
            @keyup.enter="sendMsg"
          />
          <button v-if="inputText.trim()" class="wx-send-btn" @click="sendMsg" :disabled="!inputText.trim()">发送</button>
        </div>
        <svg class="voice-toggle" @click="voiceMode = false" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#777" stroke-width="2" stroke-linecap="round">
          <rect x="3" y="3" width="18" height="18" rx="2"/>
          <line x1="3" y1="9" x2="21" y2="9"/>
          <line x1="9" y1="21" x2="9" y2="9"/>
        </svg>
      </div>
      <!-- 文字模式 微信风格 -->
      <div v-else class="text-input wx-input">
        <svg v-if="!inputText.trim()" class="wx-voice-icon" @click="enterVoiceMode" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#999" stroke-width="1.5" stroke-linecap="round">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
          <line x1="12" y1="19" x2="12" y2="23"/>
          <line x1="8" y1="23" x2="16" y2="23"/>
        </svg>
        <input
          v-model="inputText"
          ref="textInputRef"
          class="wx-input-field"
          type="text"
          placeholder="按住 说话"
          @keyup.enter="sendMsg"
          :disabled="chatStore.loading"
        />
        <button v-if="inputText.trim()" class="wx-send-btn" @click="sendMsg" :disabled="chatStore.loading || !inputText.trim()">
          {{ chatStore.loading ? '...' : '发送' }}
        </button>
        <svg v-if="inputText.trim()" class="wx-voice-icon-right" @click="inputText = ''" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#999" stroke-width="2" stroke-linecap="round">
          <line x1="18" y1="6" x2="6" y2="18"/>
          <line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, watch, onUnmounted } from 'vue'
import { showToast } from 'vant'
import { useChatStore } from '@/stores/chat'
import { sendChat } from '@/api'
import SvgIcon from '@/components/c-end/SvgIcon.vue'

const chatStore = useChatStore()

const inputText = ref('')
const typing = ref(false)
const msgContainer = ref(null)

// 语音识别
const voiceMode = ref(false)
const recording = ref(false)
const liveText = ref('')

// 非微信环境：Web Speech API
const SpeechRecognition = typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition)
let recognition = null
let finalTranscript = ''

// 微信 JSSDK
const wxReady = ref(false)
const isWechat = /micromessenger/i.test(navigator.userAgent || '')
let wxRecorderManager = null
let wxRecorderTimeout = null

// ============ Web Speech API 实时识别 ============
function initSpeechRecognition() {
  if (!SpeechRecognition) return null
  const r = new SpeechRecognition()
  r.lang = 'zh-CN'
  r.interimResults = true
  r.continuous = true
  r.maxAlternatives = 1
  r.onresult = (event) => {
    let interim = ''
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const result = event.results[i]
      if (result.isFinal) {
        finalTranscript += result[0].transcript
      } else {
        interim += result[0].transcript
      }
    }
    liveText.value = finalTranscript + interim
  }
  r.onerror = (event) => {
    console.log('[Speech] error:', event.error)
    if (event.error === 'no-speech') {
      liveText.value = finalTranscript || '未检测到语音...'
    }
  }
  r.onend = () => {
    // 如果还在录音状态且不是手动停止，自动重启
    if (recording.value && !finalTranscript) {
      try { r.start() } catch (e) {}
    }
  }
  return r
}

// ============ 微信 JSSDK ============
function initWxSdk() {
  if (!isWechat) return
  if (typeof wx === 'undefined') {
    setTimeout(initWxSdk, 1000)
    return
  }
  const url = window.location.href.split('#')[0]
  fetch(`/api/wx-config?url=${encodeURIComponent(url)}`)
    .then(resp => resp.json())
    .then(data => {
      if (!data.ok) {
        console.log('[WX] config error:', data.error)
        return
      }
      wx.config({
        debug: false,
        appId: data.appId,
        timestamp: data.timestamp,
        nonceStr: data.nonceStr,
        signature: data.signature,
        jsApiList: ['startRecord', 'stopRecord', 'onVoiceRecordEnd', 'uploadVoice', 'downloadVoice', 'playVoice', 'translateVoice', 'getRecorderManager']
      })
      wx.ready(() => {
        wxReady.value = true
        console.log('[WX] jssdk ready')
      })
      wx.error((err) => {
        console.log('[WX] jssdk error:', JSON.stringify(err))
        if (err && err.errMsg) {
          console.log('[WX] error detail:', err.errMsg)
        }
      })
    })
    .catch(e => console.log('[WX] init failed:', e))
}

if (isWechat) {
  initWxSdk()
}


// ============ 开始录音 ============
function startVoice() {
  if (recording.value) return
  finalTranscript = ''
  liveText.value = ''

  // 微信环境：用 JS-SDK startRecord
  if (isWechat && wxReady.value) {
    liveText.value = '正在聆听...'
    // 每次录音前先重置
    wx.startRecord({
      success() {
        recording.value = true
        console.log('[WX] started recording')
      },
      fail(err) {
        console.log('[WX] startRecord failed:', JSON.stringify(err))
        recording.value = false
        liveText.value = ''
        // 把微信返回的错误码显示在页面上
        let info = (err || {}).errMsg || String(err || '未知')
        showToast(info.substring(0, 50))
        // 如果没权限尝试 RecorderManager
        if (info.indexOf('permission') !== -1 && typeof wx.getRecorderManager === 'function') {
          try {
            if (!wxRecorderManager) {
              wxRecorderManager = wx.getRecorderManager()
              wxRecorderManager.onStop((res) => {
                recording.value = false
                if (res.localId) { liveText.value = '识别中...'; sendWxVoice(res.localId) }
                else { liveText.value = ''; showToast('录音失败') }
              })
              wxRecorderManager.onError((e2) => {
                recording.value = false
                liveText.value = ''
                showToast('录音异常: ' + (e2.errMsg || '').substring(0, 30))
              })
            }
            wxRecorderManager.start({ duration: 60000, sampleRate: 16000, numberOfChannels: 1, encodeBitRate: 24000, format: 'mp3' })
            recording.value = true
            liveText.value = '正在聆听...'
          } catch(e2) { console.log('[WX] recorder start failed:', e2) }
        }
      }
    })
      return
  }

  // 微信环境但 SDK 还没就绪
  if (isWechat && !wxReady.value) {
    showToast('微信初始化中，请稍后')
    return
  }

  // Web Speech API 实时识别（Chrome/Safari）
  if (SpeechRecognition) {
    try {
      recognition = initSpeechRecognition()
      if (recognition) {
        recognition.start()
        recording.value = true
        liveText.value = '正在聆听...'
        return
      }
    } catch (e) {
      console.log('[Speech] init failed:', e)
    }
  }

  // 降级：MediaRecorder 录音（不实时）
  if (!(typeof navigator !== 'undefined' && navigator.mediaDevices && navigator.mediaDevices.getUserMedia)) {
    showToast('当前环境不支持录音')
    voiceMode.value = false
    return
  }
  // Use IIFE for async media recorder fallback
  ;(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      const chunks = []
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.push(e.data)
      }
      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())
        recording.value = false
        liveText.value = '识别中...'
        if (!chunks.length) return
        const blob = new Blob(chunks, { type: 'audio/webm' })
        const formData = new FormData()
        formData.append('audio', blob, 'recording.webm')
        try {
          const res = await fetch('/api/asr', { method: 'POST', body: formData })
          const data = await res.json()
          if (data.ok && data.text) {
            liveText.value = data.text
            inputText.value = data.text
            setTimeout(() => { liveText.value = '' }, 1000)
            sendMsg()
          } else {
            showToast(data.error || '语音识别失败')
            liveText.value = ''
          }
        } catch (err) {
          showToast('识别服务异常，请重试')
          liveText.value = ''
        }
      }
      mediaRecorder.start()
      recording.value = true
      liveText.value = '正在聆听...'
    } catch (err) {
      console.warn('Mic error:', err)
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        showToast('请授权麦克风权限')
      } else {
        showToast('无法使用麦克风')
      }
    }
  })()
}

// ============ 停止录音 ============
function stopVoice() {
  if (!recording.value) return

  // 微信环境
  if (isWechat && wxReady.value) {
    if (wxRecorderManager) {
      try { wxRecorderManager.stop() } catch(e) {}
      return
    }
    wx.stopRecord({
      success(res) {
        recording.value = false
        liveText.value = '识别中...'
        sendWxVoice(res.localId)
      },
      fail(err) {
        recording.value = false
        liveText.value = ''
        console.log('[WX] stopRecord failed:', JSON.stringify(err))
        showToast('停止录音失败')
      }
    })
    return
  }

  // Web Speech API
  if (recognition) {
    try {
      recognition.stop()
    } catch (e) {}
    recording.value = false
    // 把识别结果填到输入框并发送
    if (finalTranscript.trim()) {
      const text = finalTranscript.trim()
      inputText.value = text
      liveText.value = text
      setTimeout(() => { liveText.value = '' }, 1000)
      sendMsg()
    } else {
      liveText.value = ''
    }
    return
  }

  // MediaRecorder 由 onstop 处理
  if (typeof window.__voiceRecorder !== 'undefined' && window.__voiceRecorder.state !== 'inactive') {
    window.__voiceRecorder.stop()
  } else {
    recording.value = false
    liveText.value = ''
  }
}

// ============ 微信语音上传 + 识别 ============
async function sendWxVoice(localId) {
  try {
    wx.uploadVoice({
      localId,
      isShowProgressTips: 0,
      success(res) {
        processWxVoice(res.serverId)
      },
      fail(err) {
        console.log('[WX] uploadVoice failed:', JSON.stringify(err))
        showToast('语音上传失败: ' + (err.errMsg || '未知错误'))
        liveText.value = ''
      }
    })
  } catch (e) {
    console.log('[WX] send voice error:', e)
    liveText.value = ''
  }
}

async function processWxVoice(serverId) {
  try {
    const resp = await fetch('/api/wx-voice', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ serverId })
    })
    const data = await resp.json()
    if (data.ok && data.text) {
      liveText.value = data.text
      inputText.value = data.text
      setTimeout(() => { liveText.value = '' }, 1000)
      sendMsg()
    } else {
      showToast(data.error || '语音识别失败')
      liveText.value = ''
    }
  } catch (err) {
    showToast('识别服务异常')
    liveText.value = ''
  }
}

function enterVoiceMode() {
  // 微信环境：切到带语音属性输入框，微信键盘自带语音输入
  if (isWechat) {
    voiceMode.value = true
    return
  }
  voiceMode.value = true
}

function now() {
  return new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function getLocalReply(text) {
  const replies = {
    '营业时间': '海江新天地营业时间:<br>· 商场:每天 10:00 - 22:00<br>· 超市:每天 8:00 - 22:30<br>· 餐饮区:11:00 - 22:00(部分商户至凌晨)<br>· 电影院:10:00 - 次日 01:00<br>如有特殊节假日调整会提前公告~',
    '停车': '海江新天地停车场:<br>· 10元/小时,30分钟内免费<br>· 会员折扣:普卡98折、银卡95折、金卡9折、钻石卡88折<br>· 积分可抵停车费(100积分=1元)<br>· 按底部「找车位」按钮可查询缴费~',
    '优惠': '当前热门优惠:<br>· 火锅套餐满300减50<br>· 亲子欢聚套餐299元起<br>· 夜宵时段22:00后8折<br>· 会员积分兑换星巴克券<br>更多优惠请查看「优惠套餐目录」',
    '活动': '近期活动一览:<br>· 周末亲子市集(每周六日)<br>· 七夕浪漫双人套餐(8月限时)<br>· 儿童轮滑体验课(预约制)<br>· 会员生日月双倍积分<br>详情请关注公众号推送~',
    '店铺': '海江新天地楼层导览:<br>B1:美食广场、超市<br>F1:服饰美妆、咖啡甜品<br>F2:亲子教培、儿童乐园<br>F3:餐饮、电影院<br>F4:休闲娱乐、健身<br>点击顶部的室内导航可以查看详情~',
    '积分': '积分兑换目录(性价比排序):<br>1. 星巴克券 1000分≈¥35<br>2. 蜀大侠券 3000分≈¥100<br>3. 电影票 2000分≈¥60<br>4. 乐园门票 5000分≈¥128<br>5. 停车券 500分≈¥10<br>登录后点击「我的」→ 积分兑换~',
    '会员': '会员等级与权益:<br>· 普卡(注册即送500分)→ 98折<br>· 银卡(3000分升级)→ 95折<br>· 金卡(6000分升级)→ 9折<br>· 钻石卡(20000分升级)→ 88折<br>立即注册:消费即享折扣,积分可兑好礼!',
    '注册': '新会员注册送500积分!<br>点击「我的」→ 登录/注册 → 选择「注册」→ 填写姓名+手机号<br>注册后即享:普卡会员98折、积分兑换、生日月双倍积分等权益~',
  }

  const t = text.toLowerCase()
  for (const [key, reply] of Object.entries(replies)) {
    if (t.includes(key)) return reply
  }

  return '我是海江新天地的AI客服小江\n有什么可以帮你的?可以直接问我问题,也可以点击上方快捷按钮~'
}

async function sendMsg() {
  const text = inputText.value.trim()
  if (!text || chatStore.loading.value) return
  if (text.length > 500) {
    showToast('消息太长了，请精简到500字以内')
    return
  }

  chatStore.addMessage({ role: 'user', content: text, time: now() })
  inputText.value = ''
  typing.value = true
  chatStore.loading = true
  await scrollBottom()

  try {
    const res = await sendChat(text)
    typing.value = false
    if (res.ok) {
      chatStore.addMessage({
        role: 'ai',
        content: res.reply || '小江暂时不知道该怎么回答呢~',
        time: now(),
        card: res.card || null
      })
    } else {
      chatStore.addMessage({ role: 'ai', content: getLocalReply(text), time: now() })
    }
  } catch {
    typing.value = false
    chatStore.addMessage({ role: 'ai', content: getLocalReply(text), time: now() })
  } finally {
    chatStore.loading = false
    await scrollBottom()
  }
}

async function scrollBottom() {
  await nextTick()
  if (msgContainer.value) {
    msgContainer.value.scrollTop = msgContainer.value.scrollHeight
  }
}

function formatMsg(text) {
  if (!text) return ''
  let html = text
  html = html
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')
  return html
}

function onCardClick(e, card) {
  // placeholder
}

const emit = defineEmits(['switchTab'])

// 快捷操作关键词匹配
function getQuickActions(text) {
  if (!text) return []
  const actions = []
  const t = text.toLowerCase()
  if (t.includes('停车场') || t.includes('停车') || t.includes('车位')) {
    actions.push({ label: '车辆管理', tab: 'profile' })
  }
  if (t.includes('积分') || t.includes('兑换') || t.includes('积分商城')) {
    actions.push({ label: '积分商城', tab: 'profile' })
  }
  if (t.includes('优惠') || t.includes('折扣') || t.includes('活动')) {
    actions.push({ label: '优惠活动', tab: 'offers' })
  }
  if (t.includes('会员') || t.includes('注册') || t.includes('登录')) {
    actions.push({ label: '会员中心', tab: 'profile' })
  }
  return actions
}

function doQuickAction(action) {
  if (action.tab) {
    emit('switchTab', action.tab)
  }
}

onMounted(async () => {
  if (chatStore.messages.length === 0) {
    chatStore.addMessage({
      role: 'ai',
      content: '嗨!我是海江新天地的客服小江\n有什么可以帮你的?可以直接问我问题哦~',
      time: now()
    })
  }
})

watch(() => chatStore.messages.length, () => {
  scrollBottom()
})
</script>

<style scoped>
.chat-tab {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  height: 100%;
  background: #1A1A1A;
}

/* ===== 聊天消息 ===== */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.message-wrapper {
  display: flex;
  flex-direction: column;
  gap: 2px;
  animation: msgIn 0.3s ease-out;
}

@keyframes msgIn {
  from { opacity: 0; transform: translateY(8px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.message-wrapper.user {
  align-items: flex-end;
}

.message-wrapper.ai {
  align-items: flex-start;
}

.msg-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #222222;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
  margin-bottom: 2px;
  flex-shrink: 0;
}

.msg-bubble {
  max-width: 78%;
  padding: 10px 16px;
  font-size: 17px;
  line-height: 1.4;
  word-break: break-word;
}

.user-bubble {
  background: #1A1A1A;
  color: #FFFFFF;
  border-radius: 18px 18px 4px 18px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}

.ai-bubble {
  background: #2A2A2A;
  color: #F0F0F0;
  border-radius: 18px 18px 18px 4px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}

.msg-time {
  font-size: 11px;
  color: #BBBBBB;
  padding: 1px 8px;
  font-weight: 400;
}

/* ===== 打字动画 ===== */
.typing-bubble {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 12px 18px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #999;
  animation: bounce 1.4s infinite ease-in-out;
}

.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 80%, 100% { opacity: 0.3; transform: scale(0.6); }
  40% { opacity: 1; transform: scale(1); }
}

/* ===== 输入区域 ===== */
.input-area {
  background: rgba(26,26,26,0.92);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-top: none;
  flex-shrink: 0;
  padding-bottom: env(safe-area-inset-bottom, 8px);
}

/* 语音模式 */
.voice-input {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 8px 16px 12px;
  gap: 8px;
  position: relative;
}

/* 实时文字白框 */
.voice-text-panel {
  width: 100%;
  background: #1A1A1A;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 0.5px solid rgba(255,255,255,0.15);
  border-radius: 14px;
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  max-height: 120px;
  overflow-y: auto;
}
.voice-text {
  font-size: 17px;
  color: #F0F0F0;
  text-align: center;
  word-break: break-word;
  line-height: 1.5;
}
.voice-waves-inline {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 20px;
}
.wave-bar-inline {
  width: 3px;
  background: #1A1A1A;
  border-radius: 2px;
  animation: waveInline 0.5s ease-in-out infinite alternate;
}
@keyframes waveInline {
  0% { height: 6px; }
  100% { height: 20px; }
}

.voice-btn {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  border: none;
  background: #222222;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease-out;
  touch-action: manipulation;
  -webkit-touch-callout: none;
  -webkit-user-select: none;
  user-select: none;
}
.voice-btn:active {
  background: #1A1A1A;
  box-shadow: none;
  transform: scale(0.95);
}

.voice-label {
  position: absolute;
  top: -22px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 13px;
  color: #999;
  white-space: nowrap;
}
.voice-toggle {
  flex-shrink: 0;
  cursor: pointer;
}

/* 文字模式 */
.text-input {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 4px;
}
/* 微信风格输入框 */
.text-input.wx-input {
  background: #2A2A2A;
  border-radius: 24px;
  padding: 6px 12px;
  gap: 10px;
  height: 44px;
  flex: 1;
}
.wx-input-field {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  font-size: 16px;
  color: #D4D4D4;
  font-family: 'PingFang SC', -apple-system, sans-serif;
  padding: 0;
  min-width: 0;
}
.wx-input-field::placeholder {
  color: #BBBBBB;
}
.wx-input-field:disabled {
  opacity: 0.6;
}
.wx-voice-icon {
  flex-shrink: 0;
  cursor: pointer;
  padding: 4px;
  border-radius: 50%;
  transition: background 0.15s;
}
.wx-voice-icon:active {
  background: #3A3A3A;
}
.wx-voice-icon-right {
  flex-shrink: 0;
  cursor: pointer;
  padding: 2px;
  border-radius: 50%;
  opacity: 0.6;
}

/* 微信语音替代输入框 */
.voice-input.wx-voice-alt {
  display: flex;
  align-items: center;
  background: #2A2A2A;
  border-radius: 24px;
  padding: 6px 12px;
  gap: 10px;
  height: 44px;
}
.wx-voice-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  font-size: 16px;
  color: #D4D4D4;
  font-family: 'PingFang SC', -apple-system, sans-serif;
  padding: 0;
  min-width: 0;
}
.wx-voice-input::placeholder {
  color: #BBBBBB;
}
.voice-text-input-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 0 4px;
}
.voice-mini-input {
  flex: 1;
  background: #333;
  border: 1px solid #444;
  border-radius: 18px;
  padding: 8px 14px;
  font-size: 15px;
  color: #D4D4D4;
  font-family: 'PingFang SC', -apple-system, sans-serif;
  outline: none;
  min-width: 0;
}
.voice-mini-input::placeholder {
  color: #BBBBBB;
  font-size: 14px;
}
.voice-mini-input:focus {
  border-color: #9E9E9E;
}

/* 快捷操作按钮 */
.quick-actions-row {
  display: flex;
  gap: 8px;
  padding: 6px 0 4px 44px;
  flex-wrap: wrap;
}
.quick-action-btn {
  background: #2A2A2A;
  border: 1px solid #444;
  border-radius: 8px;
  padding: 7px 14px;
  font-size: 13px;
  color: #CCC;
  font-family: 'PingFang SC', -apple-system, sans-serif;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s;
  display: flex;
  align-items: center;
  gap: 5px;
}
.qa-icon {
  flex-shrink: 0;
  color: #9E9E9E;
}
.quick-action-btn:active {
  background: #1A1A1A;
  color: #fff;
  border-color: #9E9E9E;
}
.quick-action-btn:active .qa-icon {
  color: #fff;
}
.wx-send-btn {
  flex-shrink: 0;
  background: linear-gradient(135deg, #1A1A1A, #1A1A1A);
  color: #fff;
  border: none;
  border-radius: 18px;
  padding: 6px 16px;
  font-size: 14px;
  font-weight: 500;
  font-family: 'PingFang SC', -apple-system, sans-serif;
  cursor: pointer;
  white-space: nowrap;
}
.wx-send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
/* 兼容旧 Vant 样式 */
.text-input .van-field {
  flex: 1;
}

:deep(.text-input .van-field__control) {
  background: #2A2A2A;
  border-radius: 24px;
  box-shadow: none;
  border: none !important;
  padding: 10px 16px !important;
  color: #D4D4D4 !important;
}
:deep(.text-input .van-field__control::placeholder) {
  color: #BBBBBB !important;
}
:deep(.text-input .van-field) {
  background: transparent !important;
  border-radius: 24px;
}

/* ===== 结构化卡片 ===== */
.ai-card {
  background: #2A2A2A;
  border-radius: 16px;
  overflow: hidden;
  margin: 4px 0 0;
  max-width: 280px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
.ai-card-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid #2E2E2E;
  gap: 8px;
}
.ai-card-item:last-of-type { border-bottom: none; }
.ai-card-left { flex: 1; min-width: 0; }
.ai-card-name { font-size: 16px; font-weight: 500; color: #F0F0F0; line-height: 1.3; }
.ai-card-desc { font-size: 13px; color: #999; margin-top: 2px; line-height: 1.2; }
.ai-card-right { display: flex; flex-direction: column; align-items: flex-end; gap: 3px; flex-shrink: 0; }
.ai-card-tag { font-size: 11px; color: #999999; background: #1A1A1A; padding: 2px 6px; border-radius: 4px; font-weight: 500; white-space: nowrap; }
.ai-card-price { font-size: 15px; font-weight: 600; color: #999999; white-space: nowrap; }
.ai-card-footer { font-size: 13px; color: #999; padding: 10px 14px; background: #222222; line-height: 1.4; border-top: 1px solid #2E2E2E; }
</style>
