<template>
  <div class="ad-page">
    <!-- 头图 -->
    <div class="ad-header" :style="{background: activity.gradient || '#333'}">
      <div class="ad-back" @click="$router.back()">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
      </div>
      <div class="ad-hero">
        <div class="ad-title">{{ activity.title }}</div>
        <div class="ad-meta">
          <span>{{ activity.start_date }} ~ {{ activity.end_date }}</span>
          <span>{{ activity.venue }}</span>
        </div>
      </div>
    </div>

    <div class="ad-body">
      <!-- 活动详情 -->
      <div class="ad-section-title">活动详情</div>
      <div class="ad-card">
        <p>{{ activity.desc }}</p>
        <div class="ad-price-row" v-if="activity.price > 0 || activity.points_price > 0">
          <span class="ad-price" v-if="activity.price > 0">¥{{ activity.price }}/人</span>
          <span class="ad-points" v-if="activity.points_price > 0">或 {{ activity.points_price }} 积分</span>
          <span class="ad-price" v-if="activity.price === 0 && activity.points_price === 0" style="color:#878787">免费</span>
        </div>
      </div>

      <!-- 场次选择 -->
      <div class="ad-section-title">选择场次</div>
      <div class="ad-sessions" v-if="sessions.length">
        <div
          v-for="s in sessions"
          :key="s.id"
          class="ad-session-item"
          :class="{ selected: selectedSession === s.id, full: s.enrolled >= s.max_people }"
          @click="selectSession(s)"
        >
          <div class="asi-date">{{ s.session_date }}</div>
          <div class="asi-time">{{ s.session_time }}</div>
          <div class="asi-venue">{{ s.venue }}</div>
          <div class="asi-left">{{ s.max_people - s.enrolled }} 剩余</div>
        </div>
      </div>
      <div v-else class="ad-card" style="color:#666; text-align:center">暂无场次</div>

      <!-- 报名表单 -->
      <div class="ad-section-title">报名信息</div>
      <div class="ad-card ad-form">
        <div class="ad-field">
          <label>姓名</label>
          <div class="ad-input-wrap"><input v-model="form.name" placeholder="请输入姓名" /></div>
        </div>
        <div class="ad-field">
          <label>手机号</label>
          <div class="ad-input-wrap"><input v-model="form.phone" type="tel" placeholder="请输入手机号" /></div>
        </div>
        <div class="ad-field">
          <label>人数</label>
          <div class="ad-input-wrap"><input v-model="form.count" type="number" min="1" placeholder="1" /></div>
        </div>

        <!-- 支付方式 -->
        <div class="ad-field" v-if="activity.price > 0 || activity.points_price > 0">
          <label>支付方式</label>
          <div class="ad-pay-row">
            <button class="ad-pay-btn" :class="{ on: form.payMethod === 'pay' }" @click="form.payMethod = 'pay'">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>
              在线支付 ¥{{ estimatedAmount }}
            </button>
            <button class="ad-pay-btn" :class="{ on: form.payMethod === 'points' }" @click="form.payMethod = 'points'" v-if="activity.points_price > 0">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
              积分抵扣 {{ activity.points_price * form.count }}分
            </button>
          </div>
        </div>
      </div>

      <!-- 会员信息提示 -->
      <div class="ad-member-tip" v-if="memberInfo">
        当前会员：{{ memberInfo.level }} · 
        <span v-if="form.payMethod === 'pay'">享{{ memberInfo.discount_rate }}折优惠 · 实付 ¥{{ estimatedAmount }}</span>
        <span v-else>可用积分 {{ memberInfo.points }}</span>
      </div>

      <!-- 报名按钮 -->
      <button class="ad-submit" :disabled="!canSubmit || submitting" @click="doRegister">
        {{ submitting ? '提交中...' : canSubmit ? '立即报名' : '请完善信息' }}
      </button>

      <!-- ====== 报名结果 / 电子凭证 ====== -->
      <div v-if="ticket" class="ad-ticket">
        <div class="at-card">
          <div class="at-h">🎫 报名成功</div>
          <div class="at-body">
            <div class="at-row"><span class="at-lbl">活动</span><span>{{ ticket.activity_title }}</span></div>
            <div class="at-row"><span class="at-lbl">场次</span><span>{{ ticket.session }}</span></div>
            <div class="at-row"><span class="at-lbl">地点</span><span>{{ ticket.venue }}</span></div>
            <div class="at-row"><span class="at-lbl">票号</span><span class="at-code">{{ ticket.ticket_code }}</span></div>
            <div class="at-row" v-if="ticket.amount > 0"><span class="at-lbl">金额</span><span>¥{{ ticket.amount }}</span></div>
            <div class="at-row" v-if="ticket.points_used > 0"><span class="at-lbl">积分</span><span>-{{ ticket.points_used }}分</span></div>
          </div>
          <div class="at-actions">
            <button class="at-btn" @click="showMyRegs = true">查看我的报名</button>
            <button class="at-btn secondary" @click="ticket = null">关闭</button>
          </div>
        </div>
      </div>

      <!-- ====== 我的报名列表 ====== -->
      <div v-if="showMyRegs" class="ad-reg-list">
        <div class="ad-section-title">
          我的报名
          <button class="arl-close" @click="showMyRegs = false">✕</button>
        </div>
        <div v-if="myRegs.length === 0" class="ad-card" style="color:#666;text-align:center">暂无报名记录</div>
        <div v-for="r in myRegs" :key="r.id" class="arl-item">
          <div class="arli-top">
            <span class="arli-title">{{ r.activity_title }}</span>
            <span class="arli-status" :class="r.status">{{ statusMap[r.status] || r.status }}</span>
          </div>
          <div class="arli-info">{{ r.session_date }} {{ r.session_time }} · {{ r.people_count }}人</div>
          <div class="arli-code" v-if="r.ticket_code">凭证：{{ r.ticket_code }}</div>
          <div class="arli-actions" v-if="r.status === 'confirmed'">
            <button class="arli-btn" @click="doReschedule(r)">改签</button>
            <button class="arli-btn danger" @click="doRefund(r)">退款</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api'

const route = useRoute()
const activity = ref({ title: '加载中...', gradient: '#333' })
const sessions = ref([])
const selectedSession = ref(null)
const submitting = ref(false)
const ticket = ref(null)
const showMyRegs = ref(false)
const myRegs = ref([])
const memberInfo = ref(null)

// 本地兜底（后台异常时也能展示详情）
const FALLBACK_DETAIL = {
  1: { id: 1, title: '夏日亲子嘉年华', desc: '带上宝贝来海江新天地玩！趣味游戏、DIY手工、亲子运动会，赢取精美礼品。', venue: '中庭广场', start_date: '2026-08-07', end_date: '2026-08-16', gradient: 'linear-gradient(135deg, #00704A, #00A85A)', price: 0, points_price: 0 },
  2: { id: 2, title: '美食节·川味专场', desc: '麻辣鲜香，一口入魂。川味品牌联合推出限定套餐。', venue: 'B1美食广场', start_date: '2026-08-18', end_date: '2026-08-22', gradient: 'linear-gradient(135deg, #C41E3A, #EF5350)', price: 0, points_price: 0 },
  7: { id: 7, title: '周末瑜伽体验', desc: '专业导师带你放松身心，零基础也可参与。', venue: '5F 活动空间', start_date: '2026-08-23', end_date: '2026-08-23', gradient: 'linear-gradient(135deg, #6A5B8C, #9B8BC0)', price: 39, points_price: 390 },
}

const form = reactive({ name: '', phone: '', count: 1, payMethod: 'pay' })
const statusMap = { confirmed: '已确认', refunding: '退款中', cancelled: '已取消' }

const estimatedAmount = computed(() => {
  const base = (activity.value.price || 0) * (form.count || 1)
  if (form.payMethod === 'points') return 0
  if (memberInfo.value) {
    const disc = { '普卡': 0.98, '银卡': 0.95, '金卡': 0.9, '钻石卡': 0.88 }
    return Math.round(base * (disc[memberInfo.value.level] || 1) * 100) / 100
  }
  return base
})

const canSubmit = computed(() => {
  return form.name.trim() && form.phone.trim() && form.count > 0 && selectedSession.value
})

function selectSession(s) {
  if (s.enrolled >= s.max_people) return
  selectedSession.value = s.id
}

async function loadDetail() {
  try {
    const id = route.params.id
    const res = await api.get(`/api/activities/${id}`)
    if (res && res.activity) {
      activity.value = res.activity
      sessions.value = res.sessions || []
    } else {
      const fb = FALLBACK_DETAIL[id] || { id, title: '活动详情', desc: '精彩活动即将开始，敬请期待。', venue: '海江新天地', start_date: '2026-08-01', end_date: '2026-08-31', gradient: '#333', price: 0, points_price: 0 }
      activity.value = fb
      sessions.value = res && res.sessions ? res.sessions : [{ id: 1, session_date: fb.start_date, session_time: '14:00', venue: fb.venue, max_people: 50, enrolled: 0 }]
    }
  } catch(e) {
    console.error(e)
    const fb = FALLBACK_DETAIL[route.params.id] || { id: route.params.id, title: '活动详情', desc: '精彩活动即将开始，敬请期待。', venue: '海江新天地', start_date: '2026-08-01', end_date: '2026-08-31', gradient: '#333', price: 0, points_price: 0 }
    activity.value = fb
    sessions.value = [{ id: 1, session_date: fb.start_date, session_time: '14:00', venue: fb.venue, max_people: 50, enrolled: 0 }]
  }
}

async function checkMember(phone) {
  if (!phone || phone.length < 11) return
  try {
    const res = await api.get('/api/member/query', { params: { phone } })
    if (res.ok && res.member) {
      const m = res.member
      const disc = { '普卡': 98, '银卡': 95, '金卡': 90, '钻石卡': 88 }
      memberInfo.value = { level: m.membership_level, points: m.points, discount_rate: disc[m.membership_level] || 98 }
      form.payMethod = 'pay'
    } else {
      memberInfo.value = null
    }
  } catch(e) { memberInfo.value = null }
}

async function doRegister() {
  if (!canSubmit.value) return
  submitting.value = true
  try {
    const res = await api.post('/api/activities/register', {
      activity_id: activity.value.id,
      session_id: selectedSession.value,
      phone: form.phone,
      name: form.name,
      people_count: form.count,
      pay_method: form.payMethod,
    })
    ticket.value = res.data
    form.name = ''; form.count = 1; selectedSession.value = null
  } catch(e) {
    alert(res.error || e.message || '报名失败')
  }
  submitting.value = false
}

async function loadMyRegs() {
  if (!form.phone || form.phone.length < 11) return
  try {
    const res = await api.get('/api/activities/registrations', { params: { phone: form.phone } })
    myRegs.value = res.data || []
  } catch(e) {}
}

async function doRefund(r) {
  if (!confirm('确认申请退款？')) return
  try {
    await api.post('/api/activities/refund', { registration_id: r.id })
    alert('退款申请已提交')
    loadMyRegs()
  } catch(e) {}
}

async function doReschedule(r) {
  // 简单改签到同活动的其他场次
  const newSid = prompt('请输入新场次编号（查看活动详情获取场次列表）')
  if (!newSid) return
  try {
    await api.post('/api/activities/reschedule', { registration_id: r.id, new_session_id: parseInt(newSid) })
    alert('改签成功')
    loadMyRegs()
  } catch(e) { alert(res?.error || '改签失败') }
}

// 手机号变化时查会员
import { watch } from 'vue'
watch(() => form.phone, async (v) => {
  if (v && v.length >= 11) {
    await checkMember(v)
  }
})

onMounted(() => {
  loadDetail()
})
</script>

<style scoped>
.ad-page { min-height: 100vh; background: #1A1A1A; }

.ad-header { height: 180px; position: relative; overflow: hidden; display: flex; flex-direction: column; justify-content: flex-end; }
.ad-back { position: absolute; top: 16px; left: 12px; padding: 6px; cursor: pointer; z-index: 2; }
.ad-hero { position: relative; z-index: 1; padding: 0 20px 24px; display: flex; flex-direction: column; gap: 8px; }
.ad-title { font-size: 22px; font-weight: 700; color: #fff; }
.ad-meta { display: flex; gap: 16px; font-size: 13px; color: rgba(255,255,255,0.8); }

.ad-body { padding: 16px 12px; display: flex; flex-direction: column; gap: 10px; }
.ad-section-title { font-size: 14px; font-weight: 600; color: #999; padding-left: 4px; display: flex; align-items: center; justify-content: space-between; }
.ad-card { background: #222; border-radius: 12px; padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.3); font-size: 15px; color: #AAA; line-height: 1.7; }
.ad-card p { margin: 0; }

.ad-price-row { margin-top: 12px; display: flex; gap: 12px; align-items: center; }
.ad-price { color: #999999; font-size: 18px; font-weight: 700; }
.ad-points { color: #BDBDBD; font-size: 14px; }

/* 场次 */
.ad-sessions { display: flex; gap: 10px; overflow-x: auto; padding: 0 4px; }
.ad-session-item {
  flex-shrink: 0; width: 140px; background: #222; border: 1px solid #333; border-radius: 12px;
  padding: 12px; cursor: pointer; transition: all 0.15s; display: flex; flex-direction: column; gap: 4px;
}
.ad-session-item.selected { border-color: #999999; background: #1A1A1A; }
.ad-session-item.full { opacity: 0.4; cursor: not-allowed; }
.asi-date { font-size: 14px; font-weight: 600; color: #F0F0F0; }
.asi-time { font-size: 13px; color: #999999; font-weight: 600; }
.asi-venue { font-size: 12px; color: #777; }
.asi-left { font-size: 12px; color: #878787; }

/* 报名表单 */
.ad-form { display: flex; flex-direction: column; gap: 12px; }
.ad-field { display: flex; flex-direction: column; gap: 6px; }
.ad-field label { font-size: 13px; color: #999; font-weight: 500; }
.ad-input-wrap { background: #2A2A2A; border: 1px solid #444; border-radius: 12px; transition: border-color 0.15s; }
.ad-input-wrap:focus-within { border-color: #999999; }
.ad-input-wrap input { width: 100%; padding: 12px 14px; border: none; background: none; outline: none; font-size: 15px; color: #F0F0F0; font-family: inherit; }
.ad-input-wrap input::placeholder { color: #666; }

.ad-pay-row { display: flex; gap: 8px; }
.ad-pay-btn {
  flex: 1; display: flex; align-items: center; justify-content: center; gap: 6px;
  padding: 10px; border: 1px solid #444; border-radius: 12px;
  background: #2A2A2A; color: #999; font-size: 14px; font-family: inherit; cursor: pointer;
  transition: all 0.15s;
}
.ad-pay-btn.on { border-color: #999999; color: #999999; background: #1A1A1A; }

.ad-member-tip {
  background: #1A1A1A; border: 1px solid #2D2D2D; border-radius: 10px;
  padding: 10px 14px; font-size: 13px; color: #BDBDBD;
}

.ad-submit {
  width: 100%; padding: 14px; border: none; border-radius: 12px;
  background: #1A1A1A; color: #fff; font-size: 16px; font-weight: 700;
  cursor: pointer; font-family: inherit; transition: opacity 0.15s; margin-top: 6px;
}
.ad-submit:disabled { background: #444; color: #777; cursor: not-allowed; }
.ad-submit:not(:disabled):active { opacity: 0.8; }

/* 电子凭证 */
.ad-ticket {
  position: fixed; inset: 0; background: rgba(0,0,0,0.7);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.at-card {
  background: #222; border-radius: 16px; padding: 24px; width: 90%; max-width: 360px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.5);
}
.at-h { font-size: 18px; font-weight: 700; color: #999999; margin-bottom: 16px; text-align: center; }
.at-body { display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px; }
.at-row { display: flex; justify-content: space-between; font-size: 14px; }
.at-lbl { color: #777; }
.at-code { color: #999999; font-weight: 700; font-family: monospace; }
.at-actions { display: flex; gap: 8px; }
.at-btn {
  flex: 1; padding: 10px; border: none; border-radius: 10px;
  background: #1A1A1A; color: #fff; font-size: 14px; font-weight: 600; cursor: pointer; font-family: inherit;
}
.at-btn.secondary { background: #333; color: #AAA; }

/* 报名列表 */
.ad-reg-list { display: flex; flex-direction: column; gap: 10px; }
.arl-close { border: none; background: none; color: #666; font-size: 18px; cursor: pointer; }
.arl-item {
  background: #222; border-radius: 12px; padding: 14px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
.arli-top { display: flex; justify-content: space-between; align-items: center; }
.arli-title { font-size: 15px; font-weight: 600; color: #F0F0F0; }
.arli-status { font-size: 12px; padding: 3px 8px; border-radius: 6px; }
.arli-status.confirmed { background: #1A1A1A; color: #878787; }
.arli-status.refunding { background: #1A1A1A; color: #BDBDBD; }
.arli-status.cancelled { background: #1A1A1A; color: #767676; }
.arli-info { font-size: 13px; color: #999; margin-top: 6px; }
.arli-code { font-size: 12px; color: #999999; font-family: monospace; margin-top: 4px; }
.arli-actions { display: flex; gap: 8px; margin-top: 10px; }
.arli-btn {
  padding: 6px 14px; border: 1px solid #444; border-radius: 8px;
  background: #333; color: #AAA; font-size: 13px; cursor: pointer; font-family: inherit;
}
.arli-btn.danger { border-color: #2D2D2D; color: #767676; }
</style>
