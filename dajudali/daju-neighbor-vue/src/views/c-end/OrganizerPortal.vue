<template>
  <div class="op-root">
    <header class="op-hdr">
      <h1>主理人中心</h1>
      <span class="op-sub">品牌入驻 · 活动排期 · 场地预定 · 结算查询</span>
    </header>

    <!-- Tab切换 -->
    <div class="op-tabs">
      <button v-for="t in tabs" :key="t.key" :class="{ active: activeTab === t.key }" @click="activeTab = t.key">{{ t.label }}</button>
    </div>

    <!-- ====== 入驻申请 ====== -->
    <section v-if="activeTab === 'apply'" class="op-section">
      <div class="op-card">
        <div class="op-card-hdr">品牌入驻申请</div>
        <div class="op-form">
          <input v-model="apply.name" placeholder="联系人姓名" class="op-input" />
          <input v-model="apply.phone" placeholder="手机号" class="op-input" />
          <input v-model="apply.brand" placeholder="品牌/公司名称" class="op-input" />
          <select v-model="apply.bizType" class="op-input"><option value="">经营品类</option><option v-for="b in bizTypes" :key="b" :value="b">{{ b }}</option></select>
          <select v-model="apply.area" class="op-input"><option value="">需求面积</option><option v-for="a in areas" :key="a" :value="a">{{ a }}</option></select>
          <textarea v-model="apply.remark" placeholder="补充说明（选址偏好/合作模式/其他需求）" class="op-input op-textarea" rows="3"></textarea>
          <button class="op-btn op-btn-primary" @click="submitApply" :disabled="applying">{{ applying ? '提交中...' : '提交入驻申请' }}</button>
        </div>
      </div>
    </section>

    <!-- ====== 活动排期 ====== -->
    <section v-if="activeTab === 'schedule'" class="op-section">
      <div class="op-card">
        <div class="op-card-hdr">活动排期报备</div>
        <div class="op-form">
          <input v-model="sched.name" placeholder="主办方姓名" class="op-input" />
          <input v-model="sched.phone" placeholder="手机号" class="op-input" />
          <input v-model="sched.eventName" placeholder="活动名称" class="op-input" />
          <select v-model="sched.eventType" class="op-input"><option value="">活动类型</option><option v-for="et in eventTypes" :key="et" :value="et">{{ et }}</option></select>
          <select v-model="sched.venue" class="op-input"><option value="">活动场地</option><option v-for="v in venues" :key="v" :value="v">{{ v }}</option></select>
          <div class="op-row2">
            <input v-model="sched.startDate" type="date" class="op-input" />
            <input v-model="sched.endDate" type="date" class="op-input" />
          </div>
          <input v-model="sched.attendance" type="number" placeholder="预计人数" class="op-input" />
          <textarea v-model="sched.desc" placeholder="活动描述" class="op-input op-textarea" rows="2"></textarea>
          <button class="op-btn op-btn-primary" @click="submitSchedule" :disabled="scheduling">{{ scheduling ? '提交中...' : '提交排期报备' }}</button>
        </div>
      </div>
      <!-- 我的排期 -->
      <div class="op-card" v-if="mySchedules.length">
        <div class="op-card-hdr">我的排期</div>
        <div v-for="s in mySchedules" :key="s.id" class="op-list-item">
          <div class="op-li-main">
            <span class="op-li-name">{{ s.event_name }}</span>
            <span class="op-li-status" :class="'status-'+s.status">{{ s.status }}</span>
          </div>
          <div class="op-li-sub">{{ s.venue }} · {{ s.start_date }} ~ {{ s.end_date }}</div>
        </div>
      </div>
    </section>

    <!-- ====== 场地预定 ====== -->
    <section v-if="activeTab === 'venue'" class="op-section">
      <div class="op-card">
        <div class="op-card-hdr">场地时段预定</div>
        <div class="op-form">
          <select v-model="book.venueType" class="op-input" @change="loadSlots"><option value="">场地类型</option><option v-for="vt in venueTypes" :key="vt.key" :value="vt.key">{{ vt.label }}</option></select>
          <select v-model="book.venueName" class="op-input" @change="loadSlots"><option value="">具体场地</option><option v-for="vn in venueOptions" :key="vn" :value="vn">{{ vn }}</option></select>
          <input v-model="book.date" type="date" class="op-input" @change="loadSlots" />
          <div v-if="book.venueName && book.date" class="op-slots">
            <div class="op-slots-label">可选时段 (绿色=可用 / 灰色=已定)</div>
            <div class="op-slots-grid">
              <button v-for="s in slots" :key="s.time" :class="{ available: s.available, selected: book.startTime === s.time }" :disabled="!s.available" @click="selectSlot(s)">{{ s.time }}</button>
            </div>
          </div>
          <input v-model="book.name" placeholder="联系人" class="op-input" />
          <input v-model="book.phone" placeholder="手机号" class="op-input" />
          <input v-model="book.purpose" placeholder="用途说明" class="op-input" />
          <button class="op-btn op-btn-primary" @click="submitBooking" :disabled="booking">{{ booking ? '提交中...' : '预定场地' }}</button>
        </div>
      </div>
      <!-- 我的预定 -->
      <div class="op-card" v-if="myBookings.length">
        <div class="op-card-hdr">我的预定</div>
        <div v-for="b in myBookings" :key="b.id" class="op-list-item">
          <div class="op-li-main"><span class="op-li-name">{{ b.venue_name }}</span><span class="op-li-fee">¥{{ b.fee }}</span></div>
          <div class="op-li-sub">{{ b.booking_date }} {{ b.start_time }} · {{ b.status }}</div>
        </div>
      </div>
    </section>

    <!-- ====== 结算查询 + 我的工单 ====== -->
    <section v-if="activeTab === 'settlement'" class="op-section">
      <div class="op-card" v-if="!phone">
        <div class="op-card-hdr">请输入手机号查询</div>
        <div class="op-form">
          <input v-model="settlePhone" placeholder="手机号" class="op-input" />
          <button class="op-btn op-btn-primary" @click="loadSettlement">查询</button>
        </div>
      </div>
      <div v-if="phone">
        <div class="op-card">
          <div class="op-card-hdr">结算概览</div>
          <div class="op-stats">
            <div class="op-stat"><span class="op-stat-num">{{ settleData.total_events }}</span><span>活动排期</span></div>
            <div class="op-stat"><span class="op-stat-num">{{ settleData.total_bookings }}</span><span>场地预定</span></div>
          </div>
          <div class="op-card-hdr" style="margin-top:16px">结算记录</div>
          <div v-if="settleData.settlements.length" class="op-list-item" v-for="s in settleData.settlements" :key="s.id">
            <div class="op-li-main"><span class="op-li-name">{{ s.event_name || '场地结算' }}</span><span class="op-li-fee">¥{{ s.net_payout }}</span></div>
            <div class="op-li-sub">{{ s.status }} · {{ s.settled_at || '待结算' }}</div>
          </div>
          <div v-else class="op-empty">暂无结算记录</div>
        </div>

        <div class="op-card">
          <div class="op-card-hdr">我的工单</div>
          <div v-if="myOrders.length" class="op-list-item" v-for="o in myOrders" :key="o.id">
            <div class="op-li-main"><span class="op-li-name">{{ o.title }}</span><span class="op-li-status" :class="'status-'+o.status">{{ o.status }}</span></div>
            <div class="op-li-sub">{{ o.type }} · {{ o.created_at }}</div>
          </div>
          <div v-else class="op-empty">暂无工单</div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'

const tabs = [
  { key: 'apply', label: '入驻申请' },
  { key: 'schedule', label: '活动排期' },
  { key: 'venue', label: '场地预定' },
  { key: 'settlement', label: '结算/工单' }
]
const activeTab = ref('apply')

const bizTypes = ['特色餐饮','时尚零售','亲子娱乐','生活服务','教育培训','科技数码']
const areas = ['50㎡以下','50-100㎡','100-200㎡','200-500㎡','500㎡以上']
const eventTypes = ['市集','快闪','沙龙','课程/培训','演出','展览','品牌发布','社群活动','其他']
const venues = ['B1中庭','1F中庭','户外广场','共享教室(小型)','共享教室(中型)','共享教室(大型)','公共会客厅(标准)','公共会客厅(精品)','公共会客厅(VIP)']
const venueTypes = [
  { key: 'booth', label: '多经摊位 (300元/天)' },
  { key: 'classroom', label: '共享教室 (120元/时起)' },
  { key: 'lounge', label: '会客厅 (300元/半天起)' },
  { key: 'ad', label: '广告位 (500元起)' }
]
const venueOptionsMap = {
  booth: ['B1通道摊位','1F中庭摊位','户外广场摊位'],
  classroom: ['共享教室(小型15人)','共享教室(中型30人)','共享教室(大型50人)'],
  lounge: ['公共会客厅(标准20人)','公共会客厅(精品40人)','公共会客厅(VIP60人)'],
  ad: ['电梯口灯箱','中庭吊旗','LED大屏','停车场道闸']
}

// 入驻申请
const apply = reactive({ name: '', phone: '', brand: '', bizType: '', area: '', remark: '' })
const applying = ref(false)

// 活动排期
const sched = reactive({ name: '', phone: '', eventName: '', eventType: '', venue: '', startDate: '', endDate: '', attendance: '', desc: '' })
const scheduling = ref(false)
const mySchedules = ref([])

// 场地预定
const book = reactive({ venueType: '', venueName: '', date: '', startTime: '', endTime: '', name: '', phone: '', purpose: '' })
const booking = ref(false)
const slots = ref([])
const myBookings = ref([])
const venueOptions = ref([])

// 结算
const phone = ref('')
const settlePhone = ref('')
const settleData = reactive({ settlements: [], events: [], bookings: [], total_events: 0, total_bookings: 0 })
const myOrders = ref([])

// 场地类型变化 → 更新场地选项
function watchVenueType() {
  venueOptions.value = venueOptionsMap[book.venueType] || []
  book.venueName = ''
}

async function loadSlots() {
  if (!book.venueName || !book.date) {
    slots.value = []
    return
  }
  try {
    const resp = await fetch(`/api/venue/slots?date=${book.date}&venue=${encodeURIComponent(book.venueName)}`)
    const data = await resp.json()
    if (data.ok) slots.value = data.data.slots
  } catch (e) { slots.value = [] }
}

function selectSlot(s) {
  book.startTime = s.time
  book.endTime = s.time
}

async function submitApply() {
  if (!apply.phone || !apply.name || !apply.brand) return alert('请填写姓名、手机号和品牌')
  applying.value = true
  try {
    const resp = await fetch('/api/organizer/apply', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(apply) })
    const data = await resp.json()
    alert(data.ok ? data.data.message : (data.error || '提交失败'))
    if (data.ok) { Object.assign(apply, { name: '', phone: '', brand: '', bizType: '', area: '', remark: '' }) }
  } catch (e) { alert('网络错误') }
  applying.value = false
}

async function submitSchedule() {
  if (!sched.phone || !sched.name || !sched.eventName || !sched.startDate) return alert('请填写完整信息')
  scheduling.value = true
  try {
    const resp = await fetch('/api/event/schedule', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
      phone: sched.phone, name: sched.name, event_name: sched.eventName, event_type: sched.eventType,
      venue: sched.venue, start_date: sched.startDate, end_date: sched.endDate,
      expected_attendance: parseInt(sched.attendance) || 0, description: sched.desc
    })})
    const data = await resp.json()
    alert(data.ok ? data.data.message : (data.error || '提交失败'))
    if (data.ok) loadMySchedules()
  } catch (e) { alert('网络错误') }
  scheduling.value = false
}

async function submitBooking() {
  if (!book.phone || !book.venueName || !book.date || !book.startTime) return alert('请选择场地、日期和时段')
  booking.value = true
  try {
    const resp = await fetch('/api/venue/book', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
      phone: book.phone, name: book.name, venue_name: book.venueName, venue_type: book.venueType,
      date: book.date, start_time: book.startTime, end_time: book.endTime, purpose: book.purpose
    })})
    const data = await resp.json()
    alert(data.ok ? data.data.message : (data.error || '预定失败'))
    if (data.ok) { loadSlots(); loadMyBookings() }
  } catch (e) { alert('网络错误') }
  booking.value = false
}

async function loadSettlement() {
  if (!settlePhone.value) return alert('请输入手机号')
  phone.value = settlePhone.value
  try {
    const resp = await fetch('/api/organizer/settlement?phone=' + phone.value)
    const d = await resp.json()
    if (d.ok) Object.assign(settleData, d.data)
    const resp2 = await fetch('/api/organizer/applications?phone=' + phone.value)
    const d2 = await resp2.json()
    if (d2.ok) myOrders.value = d2.data
  } catch (e) {}
}

async function loadMySchedules() {
  if (!sched.phone) return
  try {
    const resp = await fetch('/api/organizer/my-schedules?phone=' + sched.phone)
    const d = await resp.json()
    if (d.ok) mySchedules.value = d.data
  } catch (e) {}
}

async function loadMyBookings() {
  if (!book.phone) return
  try {
    const resp = await fetch('/api/venue/bookings?phone=' + book.phone)
    const d = await resp.json()
    if (d.ok) myBookings.value = d.data
  } catch (e) {}
}

onMounted(() => {
  watchVenueType()
  setInterval(watchVenueType, 500)
})
</script>

<style scoped>
.op-root { min-height: 100vh; background: #0a0a0a; color: #ddd; padding: 16px; font-family: 'PingFang SC', sans-serif; max-width: 480px; margin: 0 auto; }
.op-hdr { text-align: center; padding: 24px 0 16px; }
.op-hdr h1 { margin: 0 0 6px; font-size: 22px; color: #C4923A; }
.op-sub { font-size: 13px; color: #666; }

.op-tabs { display: flex; gap: 6px; margin-bottom: 20px; overflow-x: auto; }
.op-tabs button { padding: 8px 14px; border-radius: 8px; border: 1px solid #333; background: #1a1a1a; color: #888; font-size: 13px; cursor: pointer; white-space: nowrap; }
.op-tabs button.active { background: #C4923A; color: #fff; border-color: #C4923A; }

.op-card { background: #141414; border-radius: 12px; padding: 16px; margin-bottom: 14px; border: 1px solid #222; }
.op-card-hdr { font-size: 15px; font-weight: 600; color: #eee; margin-bottom: 12px; }
.op-form { display: flex; flex-direction: column; gap: 10px; }
.op-input { padding: 10px 12px; border-radius: 8px; border: 1px solid #333; background: #1a1a1a; color: #ddd; font-size: 14px; }
.op-input::placeholder { color: #555; }
.op-textarea { resize: vertical; min-height: 60px; }
.op-row2 { display: flex; gap: 10px; }
.op-row2 .op-input { flex: 1; }

.op-btn { padding: 10px; border-radius: 8px; border: none; font-size: 15px; font-weight: 600; cursor: pointer; }
.op-btn:disabled { opacity: 0.5; cursor: default; }
.op-btn-primary { background: #C4923A; color: #fff; }

.op-slots { margin: 4px 0 8px; }
.op-slots-label { font-size: 12px; color: #666; margin-bottom: 6px; }
.op-slots-grid { display: flex; flex-wrap: wrap; gap: 6px; }
.op-slots-grid button { padding: 6px 12px; border-radius: 6px; border: 1px solid #333; background: #1a1a1a; color: #555; font-size: 12px; cursor: pointer; }
.op-slots-grid button.available { color: #4CAF50; border-color: #2D7D46; }
.op-slots-grid button.selected { background: #2D7D46; color: #fff; border-color: #2D7D46; }
.op-slots-grid button:disabled { opacity: 0.3; cursor: default; }

.op-list-item { padding: 12px 0; border-bottom: 1px solid #1a1a1a; }
.op-list-item:last-child { border-bottom: none; }
.op-li-main { display: flex; justify-content: space-between; align-items: center; }
.op-li-name { font-size: 14px; color: #ddd; }
.op-li-status { font-size: 12px; padding: 2px 8px; border-radius: 4px; background: #333; color: #999; }
.op-li-status.status-pending { background: #332; color: #C4923A; }
.op-li-status.status-approved { background: #232; color: #4CAF50; }
.op-li-status.status-confirmed { background: #232; color: #4CAF50; }
.op-li-fee { font-size: 16px; font-weight: 700; color: #C4923A; }
.op-li-sub { font-size: 12px; color: #666; margin-top: 4px; }

.op-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 8px; }
.op-stat { background: #1a1a1a; border-radius: 8px; padding: 12px; text-align: center; }
.op-stat-num { display: block; font-size: 28px; font-weight: 700; color: #C4923A; }
.op-empty { text-align: center; color: #555; padding: 20px 0; font-size: 13px; }
</style>
