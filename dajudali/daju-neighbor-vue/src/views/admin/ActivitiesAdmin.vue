<template>
  <div class="activities-admin">
    <div class="aa-header">
      <h2>活动管理</h2>
      <button class="aa-add-btn" @click="showForm = true; editId = null; resetForm()">+ 新建活动</button>
    </div>

    <div class="aa-table-wrap">
      <table class="aa-table">
        <thead>
          <tr><th>ID</th><th>标题</th><th>日期</th><th>状态</th><th>报名</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="a in activities" :key="a.id">
            <td>{{ a.id }}</td>
            <td>{{ a.title }}</td>
            <td>{{ a.start_date }} ~ {{ a.end_date }}</td>
            <td><span class="aa-tag" :class="a.status">{{ statusMap[a.status] }}</span></td>
            <td>{{ a.enrolled || 0 }}/{{ a.max_people || '-' }}</td>
            <td>
              <button class="aa-btn-sm" @click="editActivity(a)">编辑</button>
              <button class="aa-btn-sm aa-btn-warn" @click="toggleStatus(a)">{{ a.status === 'open' ? '关闭' : '开启' }}</button>
              <button class="aa-btn-sm aa-btn-danger" @click="deleteActivity(a.id)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="!activities.length" class="aa-empty">暂无活动数据</div>
    </div>

    <!-- 编辑弹窗 -->
    <div class="aa-modal" v-if="showForm">
      <div class="aa-modal-mask" @click="showForm = false"></div>
      <div class="aa-modal-body">
        <h3>{{ editId ? '编辑活动' : '新建活动' }}</h3>
        <div class="aa-form">
          <label>标题</label><input v-model="form.title" />
          <label>描述</label><textarea v-model="form.desc" rows="2"></textarea>
          <label>地点</label><input v-model="form.venue" />
          <label>开始日期</label><input type="date" v-model="form.start_date" />
          <label>结束日期</label><input type="date" v-model="form.end_date" />
          <label>价格 (元)</label><input type="number" v-model="form.price" />
          <label>积分兑换</label><input type="number" v-model="form.points_price" />
          <label>总名额</label><input type="number" v-model="form.max_people" />
          <label>绑定优惠券（活动 ROI 真实核销链路）</label>
          <div class="aa-offers">
            <label v-for="o in offers" :key="o.id" class="aa-offer">
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
          <div class="aa-sessions">
            <label>场次 <button type="button" class="aa-btn-sm" @click="addSession">+ 添加</button></label>
            <div v-for="(s, i) in form.sessions" :key="i" class="aa-session-item">
              <input type="date" v-model="s.session_date" />
              <input v-model="s.session_time" placeholder="时间" style="width:80px" />
              <input v-model="s.venue" placeholder="地点" style="flex:1" />
              <input type="number" v-model="s.max_people" placeholder="名额" style="width:60px" />
              <button type="button" class="aa-btn-sm aa-btn-danger" @click="form.sessions.splice(i,1)">x</button>
            </div>
          </div>
        </div>
        <div class="aa-modal-actions">
          <button class="aa-btn" @click="showForm = false">取消</button>
          <button class="aa-btn aa-btn-primary" @click="saveActivity">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const activities = ref([])
const offers = ref([])
const showForm = ref(false)
const editId = ref(null)
const form = ref({})
const statusMap = { open: '开放', closed: '关闭', draft: '草稿' }

function resetForm() {
  form.value = {
    title: '', desc: '', venue: '', start_date: '', end_date: '',
    price: 0, points_price: 0, max_people: 0, gradient: '', cover_url: '', status: 'open',
    offer_ids: [], budget: 0,
    sessions: []
  }
}
resetForm()

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
.activities-admin { padding: 0; }
.aa-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.aa-header h2 { margin: 0; color: #F0F0F0; font-size: 18px; }
.aa-add-btn { padding: 8px 20px; background: #1A1A1A; color: #fff; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; }

.aa-table-wrap { background: #1A1A1A; border-radius: 14px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.aa-table { width: 100%; border-collapse: collapse; }
.aa-table th { text-align: left; padding: 12px 16px; background: #1A1A1A; color: #BBBBBB; font-size: 13px; font-weight: 600; border-bottom: 1px solid #eee; }
.aa-table td { padding: 10px 16px; border-bottom: 1px solid #f0f0f0; font-size: 14px; color: #F0F0F0; }
.aa-table tr:last-child td { border-bottom: none; }
.aa-tag { padding: 2px 10px; border-radius: 10px; font-size: 12px; }
.aa-tag.open { background: #1A1A1A; color: #BBBBBB; }
.aa-tag.closed { background: #1A1A1A; color: #BBBBBB; }
.aa-tag.draft { background: #1A1A1A; color: #BBBBBB; }
.aa-empty { padding: 40px; text-align: center; color: #999; font-size: 14px; }

.aa-offers { display: flex; flex-direction: column; gap: 4px; max-height: 132px; overflow-y: auto; padding: 6px 8px; border: 1px solid #333; border-radius: 8px; background: #151515; }
.aa-offer { font-size: 13px; color: #DDDDDD; display: flex; align-items: center; gap: 6px; cursor: pointer; }
.aa-offer input { accent-color: #FF7B2C; }

.aa-btn-sm { padding: 4px 12px; border: 1px solid #e0e0e0; background: #1A1A1A; border-radius: 6px; cursor: pointer; font-size: 12px; color: #BBBBBB; margin-right: 4px; }
.aa-btn-sm:hover { border-color: #999999; color: #999999; }
.aa-btn-warn { color: #ABABAB; border-color: #DDDDDD; }
.aa-btn-danger { color: #BBBBBB; border-color: #D4D4D4; }

/* Modal */
.aa-modal { position: fixed; inset: 0; z-index: 100; display: flex; align-items: center; justify-content: center; }
.aa-modal-mask { position: absolute; inset: 0; background: rgba(0,0,0,0.4); }
.aa-modal-body { position: relative; background: #1A1A1A; border-radius: 16px; padding: 24px; width: 90%; max-width: 560px; max-height: 85vh; overflow-y: auto; }
.aa-modal-body h3 { margin: 0 0 16px; color: #F0F0F0; }

.aa-form { display: flex; flex-direction: column; gap: 8px; }
.aa-form label { font-size: 13px; color: #BBBBBB; font-weight: 600; margin-top: 4px; }
.aa-form input, .aa-form textarea, .aa-form select { padding: 8px 12px; border: 1px solid #e0e0e0; border-radius: 8px; font-size: 14px; color: #F0F0F0; background: #1A1A1A; }
.aa-form input:focus, .aa-form textarea:focus, .aa-form select:focus { outline: none; border-color: #999999; }

.aa-sessions { border-top: 1px solid #eee; padding-top: 8px; margin-top: 4px; }
.aa-session-item { display: flex; gap: 6px; align-items: center; margin-top: 6px; }
.aa-session-item input { flex: 1; }

.aa-modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px; }
.aa-btn { padding: 8px 24px; border: 1px solid #e0e0e0; background: #1A1A1A; border-radius: 8px; cursor: pointer; font-size: 14px; color: #BBBBBB; }
.aa-btn-primary { background: #1A1A1A; color: #fff; border-color: #999999; }
</style>
