<template>
  <div class="cd-root" ref="rootEl">
    <!-- 头部 -->
    <header class="cd-hdr">
      <div class="cd-hdr-shop">{{ info.shop_name }}</div>
      <div class="cd-hdr-stats">
        <span>排队 {{ queues.length }} 组</span>
        <span class="cd-divider">|</span>
        <span>今日 {{ info.today_total }} 号</span>
        <span class="cd-divider">|</span>
        <span :class="{ peak: info.peak_hours }">{{ info.peak_hours ? '高峰' : '普通' }}</span>
      </div>
    </header>

    <!-- 当前叫号 -->
    <section class="cd-current">
      <div class="cd-cur-label">当前叫号</div>
      <div class="cd-cur-num" :class="{ animate: curAnim }">{{ currentQueue.queue_number || '—' }}</div>
      <div class="cd-cur-info" v-if="currentQueue.queue_number">
        {{ currentQueue.customer_name || '未留名' }} · {{ currentQueue.party_size }}人
      </div>
    </section>

    <!-- 等待列表 -->
    <section class="cd-waiting">
      <div class="cd-wait-hdr">
        <span>等待列表</span>
        <span class="cd-wait-count">{{ queues.length }} 组</span>
      </div>
      <div class="cd-wait-grid" v-if="queues.length">
        <div v-for="q in queues" :key="q.id" class="cd-wait-item" :class="{ highlight: q.id === currentQueue.id }">
          <div class="cd-wi-num">{{ q.queue_number }}</div>
          <div class="cd-wi-info">
            <div>{{ q.customer_name || '未留名' }}</div>
            <div class="cd-wi-people">{{ q.party_size }}人</div>
          </div>
          <div class="cd-wi-wait">约{{ q.estimated_wait }}分钟</div>
        </div>
      </div>
      <div v-else class="cd-empty">暂无排队，欢迎光临</div>
    </section>

    <!-- 预订列表 -->
    <section class="cd-reservations" v-if="reservations.length">
      <div class="cd-wait-hdr">
        <span>今日预订</span>
        <span class="cd-wait-count">{{ reservations.length }} 笔</span>
      </div>
      <div class="cd-res-list">
        <div v-for="r in reservations" :key="r.id" class="cd-res-item">
          <span class="cd-res-time">{{ r.reserve_time }}</span>
          <span>{{ r.customer_name }} · {{ r.party_size }}人</span>
          <span class="cd-res-phone">{{ r.customer_phone }}</span>
        </div>
      </div>
    </section>

    <!-- 底部 -->
    <footer class="cd-footer">
      <span>{{ info.shop_hours }}</span>
      <span>{{ now }}</span>
    </footer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const shopId = route.query.shop_id || ''
const token = route.query.token || ''
const now = ref('')
const curAnim = ref(false)

const info = reactive({ shop_name: '', shop_hours: '', today_total: 0, peak_hours: false })
const queues = ref([])
const reservations = ref([])
const currentQueue = reactive({ id: null, queue_number: '', customer_name: '', party_size: 0 })

let eventSource = null
let lastSynth = ''
let clockTimer = null

function updateClock() {
  const d = new Date()
  now.value = d.toLocaleTimeString('zh-CN', { hour12: false })
}

function speak(text) {
  if (text === lastSynth) return
  lastSynth = text
  try {
    const u = new SpeechSynthesisUtterance(text)
    u.lang = 'zh-CN'
    u.rate = 0.9
    u.volume = 0.8
    speechSynthesis.cancel()
    speechSynthesis.speak(u)
  } catch (e) { /* 静默降级 */ }
}

function fetchAndConnect() {
  // 先获取初始数据
  fetch(`/api/merchant/dashboard?shop_id=${shopId}&token=${token}`)
    .then(r => r.json())
    .then(d => {
      if (!d.ok) return
      info.shop_name = d.data.shop_name
      info.shop_hours = d.data.shop_hours
      info.today_total = d.data.today_total
      info.peak_hours = d.data.peak_hours
      queues.value = d.data.queues
      reservations.value = d.data.reservations
      if (queues.value.length) {
        Object.assign(currentQueue, queues.value[0])
      }
    })

  // SSE 实时连接
  eventSource = new EventSource(`/api/merchant/stream?shop_id=${shopId}&token=${token}`)
  eventSource.onmessage = (e) => {
    try {
      const d = JSON.parse(e.data)
      const oldLen = queues.value.length
      const oldFirst = queues.value[0]?.id
      queues.value = d.queues
      reservations.value = d.reservations
      info.today_total = d.today_total
      info.peak_hours = d.peak_hours

      // 新排队到来
      if (d.queues.length > oldLen) {
        const newest = d.queues[d.queues.length - 1]
        speak(`${newest.queue_number}号，${newest.party_size}位顾客，请取号`)
      }

      // 叫号变化（第一个变了说明叫号了）
      if (d.queues.length && d.queues[0].id !== oldFirst) {
        const cur = d.queues[0]
        Object.assign(currentQueue, cur)
        curAnim.value = true
        setTimeout(() => curAnim.value = false, 600)
        speak(`${cur.queue_number}号，${cur.customer_name || '顾客'}，${cur.party_size}位，请您用餐`)
      }
      if (!d.queues.length) {
        Object.assign(currentQueue, { id: null, queue_number: '', customer_name: '', party_size: 0 })
      }
    } catch (ex) { /* ignore */ }
  }
  eventSource.onerror = () => {
    // SSE 断开后 5 秒重连
    setTimeout(() => {
      if (eventSource) eventSource.close()
      fetchAndConnect()
    }, 5000)
  }
}

onMounted(() => {
  fetchAndConnect()
  updateClock()
  clockTimer = setInterval(updateClock, 30000)
})

onUnmounted(() => {
  if (eventSource) eventSource.close()
  if (clockTimer) clearInterval(clockTimer)
  speechSynthesis.cancel()
})
</script>

<style scoped>
.cd-root {
  min-height: 100vh; background: #0a0a0a; color: #fff;
  font-family: 'PingFang SC', sans-serif; padding: 0; margin: 0;
  display: flex; flex-direction: column; max-width: 100vw; overflow: hidden;
}
.cd-hdr {
  display: flex; justify-content: space-between; align-items: center;
  padding: 20px 24px; background: #111; border-bottom: 1px solid #222;
}
.cd-hdr-shop { font-size: 24px; font-weight: 700; color: #C4923A; }
.cd-hdr-stats { font-size: 14px; color: #888; display: flex; gap: 10px; }
.cd-hdr-stats .peak { color: #E8552A; font-weight: 600; }
.cd-divider { color: #444; }

.cd-current {
  text-align: center; padding: 40px 20px 30px;
  background: linear-gradient(180deg, #1a1a1a 0%, #0a0a0a 100%);
}
.cd-cur-label { font-size: 18px; color: #666; margin-bottom: 8px; }
.cd-cur-num {
  font-size: 120px; font-weight: 900; color: #C4923A; line-height: 1;
  transition: transform 0.3s, color 0.3s;
}
.cd-cur-num.animate { transform: scale(1.2); color: #FFD700; }
.cd-cur-info { font-size: 20px; color: #aaa; margin-top: 12px; }

.cd-waiting { padding: 16px 24px; flex: 1; }
.cd-wait-hdr {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 16px; color: #888; margin-bottom: 12px;
}
.cd-wait-count { color: #C4923A; font-weight: 600; }
.cd-empty { text-align: center; color: #444; padding: 60px 0; font-size: 24px; }

.cd-wait-grid { display: flex; flex-wrap: wrap; gap: 12px; }
.cd-wait-item {
  display: flex; align-items: center; gap: 14px;
  background: #161616; border-radius: 10px; padding: 14px 18px;
  width: calc(50% - 6px); border: 1px solid #222;
}
.cd-wait-item.highlight { border-color: #C4923A; background: #1a1810; }
.cd-wi-num { font-size: 32px; font-weight: 800; color: #C4923A; min-width: 56px; text-align: center; }
.cd-wi-info { flex: 1; font-size: 16px; color: #ddd; }
.cd-wi-people { font-size: 13px; color: #777; margin-top: 2px; }
.cd-wi-wait { font-size: 13px; color: #666; white-space: nowrap; }

.cd-reservations { padding: 0 24px 16px; }
.cd-res-list { display: flex; flex-wrap: wrap; gap: 8px; }
.cd-res-item {
  display: flex; gap: 16px; align-items: center;
  background: #161616; border-radius: 8px; padding: 10px 16px;
  font-size: 14px; color: #aaa; border: 1px solid #222;
}
.cd-res-time { color: #8E9FE6; font-weight: 600; }
.cd-res-phone { color: #5a7; }

.cd-footer {
  display: flex; justify-content: space-between; padding: 14px 24px;
  font-size: 13px; color: #444; background: #0a0a0a; border-top: 1px solid #1a1a1a;
}

@media (max-width: 600px) {
  .cd-cur-num { font-size: 80px; }
  .cd-wait-item { width: 100%; }
}
</style>
