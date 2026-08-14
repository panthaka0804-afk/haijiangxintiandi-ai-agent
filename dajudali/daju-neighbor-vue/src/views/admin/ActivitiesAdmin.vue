<template>
  <div class="in-page">
    <div class="page-header">
      <h3>活动管理</h3>
      <button class="primary-btn" @click="openCreate">+ 新建活动</button>
    </div>
    <div class="hint-bar">数据来源：活动主表 / 报名记录 / 绑定券核销，真实链路实时汇总</div>

    <!-- 统计卡片 -->
    <div class="stat-row">
      <div class="mc-card mc-card-gold stat"><div class="stat-num">{{ activities.length }}</div><div class="stat-label">活动总数</div></div>
      <div class="mc-card mc-card-green stat"><div class="stat-num">{{ openCount }}</div><div class="stat-label">开放中</div></div>
      <div class="mc-card mc-card-orange stat"><div class="stat-num">{{ totalEnrolled }}</div><div class="stat-label">累计报名</div></div>
      <div class="mc-card mc-card-purple stat"><div class="stat-num">{{ budgetSum }}</div><div class="stat-label">预算合计(元)</div></div>
    </div>

    <section class="mc-card mc-card-blue panel">
      <div class="panel-head">
        <h2><span class="dot" style="background:#4A90D9"></span>活动列表</h2>
        <span class="engine" v-if="activities.length">共 {{ activities.length }} 个</span>
        <span class="engine" v-else>暂无</span>
      </div>
      <div class="tbl-wrap">
        <table class="mc-table">
          <thead>
            <tr><th>ID</th><th>标题</th><th>日期</th><th>状态</th><th>报名</th><th>操作</th></tr>
          </thead>
          <tbody>
            <tr v-for="a in activities" :key="a.id">
              <td class="muted">{{ a.id }}</td>
              <td class="title">{{ a.title }}</td>
              <td class="muted">{{ a.start_date }} ~ {{ a.end_date }}</td>
              <td><span class="pill" :class="statusClass(a.status)">{{ statusMap[a.status] }}</span></td>
              <td>{{ a.enrolled || 0 }}/{{ a.max_people || '-' }}</td>
              <td class="ops">
                <button class="op" @click="editActivity(a)">编辑</button>
                <button class="op warn" @click="toggleStatus(a)">{{ a.status === 'open' ? '关闭' : '开启' }}</button>
                <button class="op danger" @click="deleteActivity(a.id)">删除</button>
              </td>
            </tr>
            <tr v-if="!activities.length"><td colspan="6" class="empty">暂无活动数据</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- 编辑弹窗 -->
    <div class="modal" v-if="showForm">
      <div class="modal-mask" @click="showForm = false"></div>
      <div class="modal-body">
        <h3>{{ editId ? '编辑活动' : '新建活动' }}</h3>
        <div class="form">
          <label>标题</label><input v-model="form.title" />
          <label>描述</label><textarea v-model="form.desc" rows="2"></textarea>
          <label>地点</label><input v-model="form.venue" />
          <label>开始日期</label><input type="date" v-model="form.start_date" />
          <label>结束日期</label><input type="date" v-model="form.end_date" />
          <label>价格 (元)</label><input type="number" v-model="form.price" />
          <label>积分兑换</label><input type="number" v-model="form.points_price" />
          <label>总名额</label><input type="number" v-model="form.max_people" />
          <label>绑定优惠券（活动 ROI 真实核销链路）</label>
          <div class="offers">
            <label v-for="o in offers" :key="o.id" class="offer">
              <input type="checkbox" :value="o.id" v-model="form.offer_ids" /> {{ o.shop_name }} · {{ o.label }}
            </label>
          </div>
          <label>活动预算成本 (元)</label><input type="number" v-model="form.budget" />
          <label>渐变色</label><input v-model="form.gradient" placeholder="例: linear-gradient(135deg, #838383, #626262)" />
          <label>封面图 URL</label><input v-model="form.cover_url" />
          <label>状态</label>
          <select v-model="form.status">
            <option value="open">开放</option>
            <option value="closed">关闭</option>
            <option value="draft">草稿</option>
          </select>

          <!-- 场次管理 -->
          <div class="sessions">
            <label class="sess-head">场次 <button type="button" class="op" @click="addSession">+ 添加</button></label>
            <div v-for="(s, i) in form.sessions" :key="i" class="session-item">
              <input type="date" v-model="s.session_date" />
              <input v-model="s.session_time" placeholder="时间" class="t" />
              <input v-model="s.venue" placeholder="地点" class="loc" />
              <input type="number" v-model="s.max_people" placeholder="名额" class="cap" />
              <button type="button" class="op danger" @click="form.sessions.splice(i,1)">x</button>
            </div>
          </div>
        </div>
        <div class="modal-actions">
          <button class="ghost-btn" @click="showForm = false">取消</button>
          <button class="primary-btn" @click="saveActivity">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'

const activities = ref([])
const offers = ref([])
const showForm = ref(false)
const editId = ref(null)
const form = ref({})
const statusMap = { open: '开放', closed: '关闭', draft: '草稿' }

const openCount = computed(() => activities.value.filter(a => a.status === 'open').length)
const totalEnrolled = computed(() => activities.value.reduce((s, a) => s + (a.enrolled || 0), 0))
const budgetSum = computed(() => activities.value.reduce((s, a) => s + (Number(a.budget) || 0), 0))
function statusClass(s) {
  return { open: 'green', closed: 'gray', draft: 'gold' }[s] || 'gray'
}

function resetForm() {
  form.value = {
    title: '', desc: '', venue: '', start_date: '', end_date: '',
    price: 0, points_price: 0, max_people: 0, gradient: '', cover_url: '', status: 'open',
    offer_ids: [], budget: 0,
    sessions: []
  }
}
resetForm()

function openCreate() {
  showForm.value = true
  editId.value = null
  resetForm()
}

async function loadActivities() {
  try {
    const res = await fetch('/api/activities')
    const d = await res.json()
    if (d.ok) activities.value = d.data || []
  } catch {}
  try {
    const res2 = await fetch('/api/offers')
    const d2 = await res2.json()
    if (d2.ok) offers.value = d2.data || []
  } catch {}
}

function editActivity(a) {
  editId.value = a.id
  form.value = {
    title: a.title, desc: a.desc || '', venue: a.venue || '',
    start_date: a.start_date || '', end_date: a.end_date || '',
    price: a.price || 0, points_price: a.points_price || 0,
    max_people: a.max_people || 0, gradient: a.gradient || '', cover_url: a.cover_url || '',
    offer_ids: (a.offer_ids ? String(a.offer_ids).split(',').map(s => parseInt(s, 10)).filter(n => !isNaN(n)) : []),
    budget: a.budget || 0,
    status: a.status || 'open',
    sessions: (a.sessions && a.sessions.length)
      ? a.sessions.map(s => ({ session_date: s.session_date || '', session_time: s.session_time || '', venue: s.venue || '', max_people: s.max_people || 0 }))
      : []
  }
  showForm.value = true
}

async function saveActivity() {
  const url = editId.value ? `/api/admin/activities/${editId.value}` : '/api/admin/activities'
  const method = editId.value ? 'PUT' : 'POST'
  // 编辑时若未加载到场次（原列表不含场次），不提交 sessions 以免清空已有场次
  const body = { ...form.value }
  body.offer_ids = (form.value.offer_ids || []).join(',')
  if (editId.value && (!body.sessions || body.sessions.length === 0)) {
    delete body.sessions
  }
  try {
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    const d = await res.json()
    if (d.ok) { showForm.value = false; loadActivities() }
  } catch {}
}

async function toggleStatus(a) {
  const newStatus = a.status === 'open' ? 'closed' : 'open'
  try {
    const res = await fetch(`/api/admin/activities/${a.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus })
    })
    const d = await res.json()
    if (d.ok) loadActivities()
  } catch {}
}

async function deleteActivity(id) {
  if (!confirm('确认删除？')) return
  try {
    const res = await fetch(`/api/admin/activities/${id}`, { method: 'DELETE' })
    const d = await res.json()
    if (d.ok) loadActivities()
  } catch {}
}

function addSession() {
  if (!form.value.sessions) form.value.sessions = []
  form.value.sessions.push({ session_date: '', session_time: '', venue: '', max_people: 0 })
}

onMounted(loadActivities)
</script>

<style scoped>
.stat-row { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.primary-btn { padding: 8px 20px; background: linear-gradient(135deg,#FF7B2C,#E85D04); color: #fff; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600; box-shadow: 0 4px 12px rgba(232,93,4,.28); transition: .15s; }
.primary-btn:hover { box-shadow: 0 6px 18px rgba(232,93,4,.42); }
.title { color: #f0f0f0; font-weight: 600; }
.ops { white-space: nowrap; }
.op { padding: 4px 12px; border: 1px solid #3a3a3a; background: #202020; border-radius: 6px; cursor: pointer; font-size: 12px; color: #cfcfcf; margin-right: 4px; transition: .15s; }
.op:hover { border-color: #FF7B2C; color: #fff; }
.op.warn { color: #E3BB6A; border-color: #5a4f33; }
.op.danger { color: #DD8E7C; border-color: #5a3a36; }
.op.danger:hover { border-color: #DD8E7C; }

/* Modal */
.modal { position: fixed; inset: 0; z-index: 100; display: flex; align-items: center; justify-content: center; }
.modal-mask { position: absolute; inset: 0; background: rgba(0,0,0,.55); }
.modal-body { position: relative; background: #161616; border: 1px solid #2a2a2a; border-radius: 16px; padding: 22px 24px; width: 90%; max-width: 560px; max-height: 85vh; overflow-y: auto; }
.modal-body h3 { margin: 0 0 16px; color: #f0f0f0; border-left: 4px solid #FF7B2C; padding-left: 12px; line-height: 1.2; }

.form { display: flex; flex-direction: column; gap: 6px; }
.form label { font-size: 13px; color: #bbb; font-weight: 600; margin-top: 6px; }
.form input, .form textarea, .form select { padding: 8px 12px; border: 1px solid #333; border-radius: 8px; font-size: 14px; color: #e8e8e8; background: #1d1d1d; }
.form input:focus, .form textarea:focus, .form select:focus { outline: none; border-color: #FF7B2C; box-shadow: 0 0 0 3px rgba(255,123,44,.15); }

.offers { display: flex; flex-direction: column; gap: 4px; max-height: 132px; overflow-y: auto; padding: 6px 8px; border: 1px solid #333; border-radius: 8px; background: #1d1d1d; }
.offer { font-size: 13px; color: #ddd; display: flex; align-items: center; gap: 6px; cursor: pointer; }
.offer input { accent-color: #FF7B2C; }

.sessions { border-top: 1px solid #2a2a2a; padding-top: 8px; margin-top: 6px; }
.sess-head { display: flex; align-items: center; gap: 10px; }
.session-item { display: flex; gap: 6px; align-items: center; margin-top: 6px; }
.session-item .t { width: 80px; }
.session-item .loc { flex: 1; }
.session-item .cap { width: 60px; }

.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px; }
.ghost-btn { padding: 8px 24px; border: 1px solid #3a3a3a; background: #202020; border-radius: 8px; cursor: pointer; font-size: 14px; color: #cfcfcf; transition: .15s; }
.ghost-btn:hover { border-color: #777; color: #fff; }
</style>
