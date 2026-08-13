<template>
  <div class="md-root">
    <!-- 头部 -->
    <header class="md-hdr">
      <div class="md-hdr-left">
        <h1 v-if="info.shop_name">{{ info.shop_name }}</h1>
        <span class="md-hdr-sub">{{ info.shop_hours || '商户看板' }}</span>
      </div>
      <div class="md-hdr-right">
        <span class="md-badge" :class="{ peak: info.peak_hours }">
          {{ info.peak_hours ? '高峰' : '普通' }}
        </span>
        <button class="md-refresh" @click="refresh" :disabled="loading">刷新</button>
      </div>
    </header>

    <!-- 统计 -->
    <div class="md-stats">
      <div class="md-stat">
        <div class="md-stat-num">{{ queues.length }}</div>
        <div class="md-stat-label">排队中</div>
      </div>
      <div class="md-stat">
        <div class="md-stat-num">{{ info.today_total }}</div>
        <div class="md-stat-label">今日取号</div>
      </div>
      <div class="md-stat">
        <div class="md-stat-num">{{ reservations.length }}</div>
        <div class="md-stat-label">今日预订</div>
      </div>
    </div>

    <!-- 错误/加载 -->
    <div v-if="error" class="md-error">{{ error }}</div>
    <div v-if="!authed && !error" class="md-loading">正在加载商户看板...</div>

    <!-- 内容区（认证后） -->
    <template v-if="authed">
      <!-- 排队列表 -->
      <section class="md-section">
        <div class="md-sec-hdr">
          <h2>排队列表</h2>
          <span class="md-sec-count">{{ queues.length }} 组等待</span>
        </div>
        <div v-if="queues.length === 0" class="md-empty">暂无排队，休息一下吧</div>
        <div v-for="q in queues" :key="q.id" class="md-card">
          <div class="md-card-main">
            <div class="md-qnum">{{ q.queue_number }}号</div>
            <div class="md-qinfo">
              <div class="md-qname">{{ q.customer_name || '未留名' }} · {{ q.party_size }}人</div>
              <div class="md-qtime">{{ formatTime(q.created_at) }} · 预计{{ q.estimated_wait }}分钟</div>
              <div class="md-qphone" v-if="q.customer_phone">{{ q.customer_phone }}</div>
            </div>
          </div>
          <div class="md-card-actions">
            <button class="md-btn md-btn-primary" @click="callQueue(q.id)">叫号</button>
            <button class="md-btn md-btn-success" @click="seatQueue(q.id)">入座</button>
            <button class="md-btn md-btn-danger" @click="cancelQueue(q.id)">取消</button>
          </div>
        </div>
      </section>

      <!-- 预订列表 -->
      <section class="md-section">
        <div class="md-sec-hdr">
          <h2>今日预订</h2>
          <span class="md-sec-count">{{ reservations.length }} 笔</span>
        </div>
        <div v-if="reservations.length === 0" class="md-empty">暂无预订</div>
        <div v-for="r in reservations" :key="r.id" class="md-card md-card-res">
          <div class="md-card-main">
            <div class="md-res-time">{{ r.reserve_time }}</div>
            <div class="md-qinfo">
              <div class="md-qname">{{ r.customer_name }} · {{ r.party_size }}人</div>
              <div class="md-qtime">{{ r.reserve_date }} · {{ r.customer_phone }}</div>
            </div>
          </div>
          <div class="md-card-actions">
            <button class="md-btn md-btn-success" @click="confirmRes(r.id)">确认到场</button>
          </div>
        </div>
      </section>

      <!-- Webhook 设置 -->
      <section class="md-section md-webhook">
        <div class="md-sec-hdr"><h2>实时推送设置</h2></div>
        <div class="md-wh-row">
          <input v-model="webhookUrl" placeholder="输入 Webhook URL 接收实时通知..." class="md-input" />
          <button class="md-btn md-btn-primary" @click="setWebhook">保存</button>
        </div>
        <div class="md-wh-hint">有新排队/预订时自动推送 JSON 到该地址</div>
      </section>

      <!-- 发券（写入 offers，会员可在优惠券专区领取） -->
      <section class="md-section">
        <div class="md-sec-hdr">
          <h2>发优惠券</h2>
          <span class="md-sec-count">会员领券后可到店核销</span>
        </div>
        <div class="md-coupon-form">
          <input v-model="couponLabel" placeholder="券说明，如：满100减20 代金券" class="md-input" />
          <div class="md-coupon-row">
            <input v-model="couponAmount" type="number" placeholder="面额(元)" class="md-input md-input-sm" />
            <select v-model="couponCategory" class="md-input md-input-sm">
              <option value="food">餐饮</option>
              <option value="retail">零售</option>
              <option value="fun">娱乐</option>
              <option value="kids">亲子</option>
            </select>
          </div>
          <button class="md-btn md-btn-primary" :disabled="issuing" @click="issueCoupon">发布优惠券</button>
        </div>
      </section>
    </template>

    <!-- 底部信息 -->
    <footer class="md-footer" v-if="authed">
      <span>每日 {{ info.shop_hours }} 营业</span>
      <span>自动刷新 · {{ refreshInterval }}秒</span>
    </footer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const loading = ref(false)
const error = ref('')
const authed = ref(false)
const refreshInterval = 15

const info = reactive({
  shop_name: '', shop_hours: '', shop_phone: '',
  today_total: 0, peak_hours: false, token: '', webhook_url: ''
})
const queues = ref([])
const reservations = ref([])
const webhookUrl = ref('')
let timer = null
let eventSource = null

// 发券
const couponLabel = ref('')
const couponAmount = ref('')
const couponCategory = ref('food')
const issuing = ref(false)
async function issueCoupon() {
  if (!couponLabel.value.trim()) { alert('请填写券说明'); return }
  issuing.value = true
  try {
    const res = await fetch('/api/merchant/issue-coupon', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        shop_id: shopId, token,
        label: couponLabel.value.trim(),
        amount: parseInt(couponAmount.value || '0', 10),
        category: couponCategory.value,
        expire: '2026-12-31'
      })
    }).then(r => r.json())
    if (res.ok) {
      alert('发券成功！会员可在优惠券专区领取')
      couponLabel.value = ''
      couponAmount.value = ''
    } else {
      alert(res.error || '发券失败')
    }
  } catch (e) { alert('网络异常') }
  finally { issuing.value = false }
}

const shopId = route.query.shop_id || ''
const token = route.query.token || ''

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts + (ts.length <= 10 ? 'T00:00:00' : ''))
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  return `${h}:${m}`
}

function beep() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.connect(gain); gain.connect(ctx.destination)
    osc.frequency.value = 880; osc.type = 'sine'
    gain.gain.setValueAtTime(0.3, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3)
    osc.start(ctx.currentTime); osc.stop(ctx.currentTime + 0.3)
  } catch(e) {}
}

async function refresh() {
  if (!shopId || !token) {
    error.value = '缺少 shop_id 或 token 参数'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const resp = await fetch(`/api/merchant/dashboard?shop_id=${shopId}&token=${token}`)
    const data = await resp.json()
    if (!data.ok) {
      error.value = data.error || '认证失败'
      authed.value = false
      return
    }
    authed.value = true
    const d = data.data
    info.shop_name = d.shop_name
    info.shop_hours = d.shop_hours
    info.shop_phone = d.shop_phone
    info.today_total = d.today_total
    info.peak_hours = d.peak_hours
    info.token = d.token
    info.webhook_url = d.webhook_url
    const oldLen = queues.value.length
    queues.value = d.queues || []
    reservations.value = d.reservations || []
    webhookUrl.value = d.webhook_url || ''
    if (queues.value.length > oldLen) beep()  // 新排队提醒
  } catch (e) {
    error.value = '网络错误，请检查网络连接'
  } finally {
    loading.value = false
  }
  // SSE 连接（仅首次）
  if (!eventSource) connectSSE()
}

function connectSSE() {
  eventSource = new EventSource(`/api/merchant/stream?shop_id=${shopId}&token=${token}`)
  eventSource.onmessage = (e) => {
    try {
      const d = JSON.parse(e.data)
      const oldLen = queues.value.length
      queues.value = d.queues
      reservations.value = d.reservations
      info.today_total = d.today_total
      info.peak_hours = d.peak_hours
      if (d.queues.length > oldLen) beep()
    } catch(ex) {}
  }
  eventSource.onerror = () => {
    eventSource = null
    setTimeout(connectSSE, 8000)
  }
}

async function callQueue(qid) {
  try {
    const resp = await fetch('/api/merchant/call', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ shop_id: shopId, token, queue_id: qid })
    })
    const data = await resp.json()
    if (data.ok) refresh()
    else alert(data.error || '叫号失败')
  } catch (e) { alert('操作失败') }
}

async function seatQueue(qid) {
  try {
    const resp = await fetch('/api/merchant/seat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ shop_id: shopId, token, queue_id: qid })
    })
    const data = await resp.json()
    if (data.ok) refresh()
    else alert(data.error || '操作失败')
  } catch (e) { alert('操作失败') }
}

async function cancelQueue(qid) {
  if (!confirm('确定取消该排队号？')) return
  try {
    const resp = await fetch('/api/merchant/cancel-queue', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ shop_id: shopId, token, queue_id: qid })
    })
    const data = await resp.json()
    if (data.ok) refresh()
    else alert(data.error || '操作失败')
  } catch (e) { alert('操作失败') }
}

async function confirmRes(rid) {
  try {
    const resp = await fetch('/api/merchant/reservation/confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ shop_id: shopId, token, reservation_id: rid })
    })
    const data = await resp.json()
    if (data.ok) refresh()
    else alert(data.error || '操作失败')
  } catch (e) { alert('操作失败') }
}

async function setWebhook() {
  try {
    const resp = await fetch('/api/merchant/webhook', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ shop_id: shopId, token, webhook_url: webhookUrl.value })
    })
    const data = await resp.json()
    if (data.ok) alert('Webhook 已更新')
    else alert(data.error || '设置失败')
  } catch (e) { alert('操作失败') }
}

onMounted(() => {
  refresh()
})

onUnmounted(() => {
  if (eventSource) eventSource.close()
})
</script>

<style scoped>
.md-root {
  min-height: 100vh;
  background: #000000;
  color: rgba(255,255,255,0.9);
  font-family: 'PingFang SC', sans-serif;
  padding: 16px;
  max-width: 480px;
  margin: 0 auto;
}
.md-hdr {
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: 16px;
}
.md-hdr-left h1 { margin: 0; font-size: 22px; color: #fff; }
.md-hdr-sub { font-size: 13px; color: rgba(255,255,255,0.55); }
.md-hdr-right { display: flex; gap: 8px; align-items: center; }
.md-badge {
  display: inline-block; padding: 3px 10px; border-radius: 10px;
  font-size: 12px; background: #222; color: rgba(255,255,255,0.6);
  border: 1px solid rgba(255,255,255,0.08);
}
.md-badge.peak { background: #9B4A3E; color: #fff; }
.md-refresh {
  padding: 4px 12px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.15);
  background: #222; color: rgba(255,255,255,0.7); font-size: 13px; cursor: pointer;
}
.md-stats {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;
  margin-bottom: 20px;
}
.md-stat {
  background: #222; border-radius: 10px; padding: 14px 10px;
  text-align: center; border: 1px solid rgba(255,255,255,0.08);
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.3);
}
.md-stat-num { font-size: 28px; font-weight: 700; color: #C4923A; }
.md-stat-label { font-size: 12px; color: rgba(255,255,255,0.55); margin-top: 4px; }
.md-error { padding: 20px; color: #9B4A3E; text-align: center; }
.md-loading { padding: 40px; color: rgba(255,255,255,0.5); text-align: center; }
.md-section {
  background: #222; border-radius: 12px; padding: 16px;
  margin-bottom: 16px; border: 1px solid rgba(255,255,255,0.08);
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.3);
}
.md-sec-hdr { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.md-sec-hdr h2 { margin: 0; font-size: 16px; color: #fff; }
.md-sec-count { font-size: 13px; color: rgba(255,255,255,0.5); }
.md-empty { text-align: center; color: rgba(255,255,255,0.4); padding: 24px 0; font-size: 14px; }
.md-card {
  display: flex; flex-direction: column; gap: 10px;
  background: #222; border-radius: 10px; padding: 12px 14px;
  margin-bottom: 10px; border: 1px solid rgba(255,255,255,0.08);
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.3);
}
.md-card-main { display: flex; gap: 14px; align-items: center; }
.md-qnum {
  font-size: 32px; font-weight: 700; color: #C4923A;
  min-width: 56px; text-align: center;
}
.md-res-time {
  font-size: 22px; font-weight: 600; color: #C4923A;
  min-width: 56px; text-align: center;
}
.md-qinfo { flex: 1; }
.md-qname { font-size: 15px; color: #fff; font-weight: 500; }
.md-qtime { font-size: 12px; color: rgba(255,255,255,0.55); margin-top: 2px; }
.md-qphone { font-size: 12px; color: rgba(255,255,255,0.6); margin-top: 2px; }
.md-card-actions { display: flex; gap: 8px; justify-content: flex-end; }
.md-btn {
  padding: 6px 14px; border-radius: 14px; border: 3px solid transparent;
  font-size: 13px; cursor: pointer; font-weight: 600; color: #fff;
  filter: drop-shadow(0 0.6px 1px rgba(0,0,0,0.4));
}
.md-btn:disabled { opacity: 0.4; cursor: default; }
.md-btn:active { box-shadow: inset 5px 5px 10px rgba(0,0,0,0.55), inset -2px -2px 5px rgba(196,146,58,0.35); }
.md-btn-primary { background: #9A7425; border-color: #9A7425;
  box-shadow: inset 3px 3px 7px rgba(0,0,0,0.45), inset -2px -2px 5px rgba(196,146,58,0.45); }
.md-btn-success { background: #2D7D46; border-color: #2D7D46;
  box-shadow: inset 3px 3px 7px rgba(0,0,0,0.45), inset -2px -2px 5px rgba(80,180,110,0.45); }
.md-btn-success:active { box-shadow: inset 5px 5px 10px rgba(0,0,0,0.55), inset -2px -2px 5px rgba(80,180,110,0.35); }
.md-btn-danger { background: #8B3A3A; border-color: #8B3A3A;
  box-shadow: inset 3px 3px 7px rgba(0,0,0,0.45), inset -2px -2px 5px rgba(190,90,90,0.45); }
.md-btn-danger:active { box-shadow: inset 5px 5px 10px rgba(0,0,0,0.55), inset -2px -2px 5px rgba(190,90,90,0.35); }
.md-webhook { padding-bottom: 20px; }
.md-wh-row { display: flex; gap: 8px; margin-bottom: 6px; }
.md-input {
  flex: 1; padding: 8px 12px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.08);
  background: #1a1a1a; color: #fff; font-size: 13px;
  box-shadow: inset 0 1px 2px rgba(0,0,0,0.5);
}
.md-wh-hint { font-size: 11px; color: rgba(255,255,255,0.45); }
.md-coupon-form { display: flex; flex-direction: column; gap: 8px; }
.md-coupon-row { display: flex; gap: 8px; }
.md-input-sm { flex: 1; }
.md-coupon-form select.md-input { cursor: pointer; }
.md-footer {
  text-align: center; padding: 20px 0 40px; font-size: 12px;
  color: rgba(255,255,255,0.45); display: flex; justify-content: space-between;
}
</style>
