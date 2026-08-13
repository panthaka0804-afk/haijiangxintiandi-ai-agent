<template>
  <div class="bc-root">
    <header class="bc-hdr">
      <h1>商务合作</h1>
      <span class="bc-sub">场地租赁 · 品牌入驻 · 团建定制</span>
    </header>

    <!-- Tab切换 -->
    <div class="bc-tabs">
      <button v-for="t in tabs" :key="t.key" :class="{ active: activeTab === t.key }" @click="activeTab = t.key">{{ t.label }}</button>
    </div>

    <!-- ====== 场地预约看场 ====== -->
    <section v-if="activeTab === 'visit'" class="bc-section">
      <div class="bc-card">
        <div class="bc-card-hdr">场地预约看场</div>
        <div class="bc-hint">选择意向场地与日期，AI 自动校验可用性，预约成功后市场专员跟进</div>
        <div class="bc-form">
          <select v-model="visit.venueName" class="bc-input">
            <option value="">选择意向场地</option>
            <option v-for="v in visitVenues" :key="v" :value="v">{{ v }}</option>
          </select>
          <input v-model="visit.date" type="date" class="bc-input" />
          <select v-model="visit.time" class="bc-input">
            <option value="">选择时段</option>
            <option v-for="h in timeSlots" :key="h" :value="h">{{ h }}</option>
          </select>
          <input v-model="visit.purpose" placeholder="看场用途（如品牌快闪/团建/展会）" class="bc-input" />
          <input v-model="visit.name" placeholder="联系人姓名" class="bc-input" />
          <input v-model="visit.phone" placeholder="手机号" class="bc-input" />
          <button class="bc-btn bc-btn-primary" @click="submitVisit" :disabled="visiting">{{ visiting ? '提交中...' : '预约看场' }}</button>
        </div>
      </div>
    </section>

    <!-- ====== 意向登记 ====== -->
    <section v-if="activeTab === 'intent'" class="bc-section">
      <div class="bc-card">
        <div class="bc-card-hdr">意向登记</div>
        <div class="bc-hint">品牌入驻 / 多经合作 / 广告投放，在线提交，24 小时内专人对接</div>
        <div class="bc-form">
          <select v-model="intent.intentType" class="bc-input">
            <option value="">意向类型</option>
            <option v-for="t in intentTypes" :key="t" :value="t">{{ t }}</option>
          </select>
          <input v-model="intent.brand" placeholder="品牌/公司名称" class="bc-input" />
          <input v-model="intent.area" placeholder="需求面积（如 50-100㎡）" class="bc-input" />
          <input v-model="intent.name" placeholder="联系人姓名" class="bc-input" />
          <input v-model="intent.phone" placeholder="手机号" class="bc-input" />
          <textarea v-model="intent.remark" placeholder="需求说明（选址偏好/预算/合作模式等）" class="bc-input bc-textarea" rows="3"></textarea>
          <button class="bc-btn bc-btn-primary" @click="submitIntent" :disabled="intenting">{{ intenting ? '提交中...' : '提交意向' }}</button>
        </div>
      </div>
    </section>

    <!-- ====== 团建/活动定制 ====== -->
    <section v-if="activeTab === 'team'" class="bc-section">
      <div class="bc-card">
        <div class="bc-card-hdr">团建 / 活动定制</div>
        <div class="bc-hint">企业团建、社区公益活动定制，AI 初步匹配方案与报价，转人工深化</div>
        <div class="bc-form">
          <input v-model="team.orgName" placeholder="企业/组织名称" class="bc-input" />
          <input v-model="team.name" placeholder="联系人姓名" class="bc-input" />
          <input v-model="team.phone" placeholder="手机号" class="bc-input" />
          <div class="bc-row2">
            <input v-model="team.people" type="number" placeholder="预计人数" class="bc-input" />
            <input v-model="team.date" type="date" class="bc-input" />
          </div>
          <input v-model="team.budget" type="number" placeholder="预算（元，可选）" class="bc-input" />
          <textarea v-model="team.description" placeholder="活动需求描述（主题/形式/期望等）" class="bc-input bc-textarea" rows="3"></textarea>
          <button class="bc-btn bc-btn-primary" @click="submitTeam" :disabled="teaming">{{ teaming ? '匹配中...' : '提交需求' }}</button>
        </div>
        <!-- AI 匹配结果 -->
        <div v-if="teamSuggestion" class="bc-suggestion">
          <div class="bc-sug-hdr">AI 初步匹配方案</div>
          <div class="bc-sug-body">{{ teamSuggestion }}</div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'

const tabs = [
  { key: 'visit', label: '场地看场' },
  { key: 'intent', label: '意向登记' },
  { key: 'team', label: '团建定制' }
]
const activeTab = ref('visit')

const visitVenues = ['B1中庭','1F中庭','户外广场','共享教室(小型)','共享教室(中型)','共享教室(大型)','公共会客厅(标准)','公共会客厅(精品)','公共会客厅(VIP)']
const timeSlots = ['10:00','11:00','13:00','14:00','15:00','16:00','17:00','18:00','19:00']
const intentTypes = ['品牌入驻开店','多经合作（市集/快闪）','广告位投放','共享教室租赁','会客厅/沙龙场地','合作/分成模式咨询','其他商务合作']

const visit = reactive({ venueName: '', date: '', time: '', purpose: '', name: '', phone: '' })
const intent = reactive({ intentType: '', brand: '', area: '', name: '', phone: '', remark: '' })
const team = reactive({ orgName: '', name: '', phone: '', people: '', date: '', budget: '', description: '' })

const visiting = ref(false)
const intenting = ref(false)
const teaming = ref(false)
const teamSuggestion = ref('')

function validPhone(p) { return /^1\d{10}$/.test(p) }

async function submitVisit() {
  if (!visit.venueName || !visit.date || !visit.name || !validPhone(visit.phone)) return alert('请填写完整信息（场地/日期/联系人/手机号）')
  visiting.value = true
  try {
    const resp = await fetch('/api/biz/visit', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(visit) })
    const data = await resp.json()
    alert(data.ok ? data.data.message : (data.error || '提交失败'))
    if (data.ok) Object.assign(visit, { venueName: '', date: '', time: '', purpose: '', name: '', phone: '' })
  } catch (e) { alert('网络错误') }
  visiting.value = false
}

async function submitIntent() {
  if (!intent.intentType || !intent.name || !validPhone(intent.phone)) return alert('请填写意向类型、联系人和手机号')
  intenting.value = true
  try {
    const resp = await fetch('/api/biz/intent', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(intent) })
    const data = await resp.json()
    alert(data.ok ? data.data.message : (data.error || '提交失败'))
    if (data.ok) Object.assign(intent, { intentType: '', brand: '', area: '', name: '', phone: '', remark: '' })
  } catch (e) { alert('网络错误') }
  intenting.value = false
}

async function submitTeam() {
  if (!team.name || !validPhone(team.phone) || !team.description) return alert('请填写联系人、手机号和需求描述')
  teaming.value = true
  try {
    const resp = await fetch('/api/biz/team-building', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(team) })
    const data = await resp.json()
    if (data.ok) {
      teamSuggestion.value = data.data.suggestion
      alert(data.data.message)
    } else {
      alert(data.error || '提交失败')
    }
  } catch (e) { alert('网络错误') }
  teaming.value = false
}
</script>

<style scoped>
.bc-root { min-height: 100vh; background: #000000; color: #fff; padding: 16px; font-family: 'PingFang SC', sans-serif; max-width: 480px; margin: 0 auto; }
.bc-hdr { text-align: center; padding: 24px 0 16px; }
.bc-hdr h1 { margin: 0 0 6px; font-size: 22px; color: #C4923A; text-shadow: 0 1px 2px rgba(0,0,0,.35); }
.bc-sub { font-size: 13px; color: rgba(255,255,255,.6); }

.bc-tabs { display: flex; gap: 6px; margin-bottom: 20px; overflow-x: auto; }
.bc-tabs button { padding: 8px 14px; border-radius: 20px; border: 3px solid #4E5049; background: #6B6E64; color: #fff; font-size: 13px; cursor: pointer; white-space: nowrap;
  box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(107,110,100,.45); }
.bc-tabs button.active { background: #C4923A; color: #fff; border-color: #9A7425;
  box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(196,146,58,.45); }

.bc-card { background: #6B6E64; border: 3px solid #4E5049; border-radius: 12px; padding: 16px; margin-bottom: 14px; box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20); }
.bc-card-hdr { font-size: 15px; font-weight: 600; color: #fff; margin-bottom: 8px; text-shadow: 0 1px 2px rgba(0,0,0,.35); }
.bc-hint { font-size: 12px; color: rgba(255,255,255,.8); margin-bottom: 14px; line-height: 1.5; }
.bc-form { display: flex; flex-direction: column; gap: 10px; }
.bc-input { padding: 10px 12px; border-radius: 8px; border: 3px solid #4E5049; background: #000; color: #fff; font-size: 14px;
  box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(107,110,100,.25); }
.bc-input::placeholder { color: rgba(255,255,255,.4); }
.bc-textarea { resize: vertical; min-height: 60px; }
.bc-row2 { display: flex; gap: 10px; }
.bc-row2 .bc-input { flex: 1; }

.bc-btn { padding: 10px; border-radius: 20px; border: 3px solid #9A7425; font-size: 15px; font-weight: 600; cursor: pointer; font-family: inherit;
  background: #9A7425; color: #fff;
  box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(196,146,58,.45);
  filter: drop-shadow(0 0.6px 1px rgba(0,0,0,0.4)); }
.bc-btn:active { box-shadow: inset 5px 5px 10px rgba(0,0,0,.55), inset -2px -2px 5px rgba(196,146,58,.35); }
.bc-btn:disabled { opacity: 0.5; cursor: default; }
.bc-btn-primary { background: #9A7425; border-color: #9A7425; color: #fff; }

.bc-suggestion { margin-top: 14px; padding: 12px 14px; background: #8B8B90; border: 3px solid #6A6A6E; border-radius: 10px; box-shadow: inset 0 1px 0 rgba(255,255,255,.2); }
.bc-sug-hdr { font-size: 13px; font-weight: 600; color: #C4923A; margin-bottom: 6px; text-shadow: 0 1px 2px rgba(0,0,0,.35); }
.bc-sug-body { font-size: 13px; color: #fff; line-height: 1.6; }
</style>
