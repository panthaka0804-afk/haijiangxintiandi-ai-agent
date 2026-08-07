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
            <td>{{ a.enrolled || 0 }}/{{ a.capacity || '-' }}</td>
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
          <label>描述</label><textarea v-model="form.description" rows="2"></textarea>
          <label>地点</label><input v-model="form.location" />
          <label>开始日期</label><input type="date" v-model="form.start_date" />
          <label>结束日期</label><input type="date" v-model="form.end_date" />
          <label>价格 (元)</label><input type="number" v-model="form.price" />
          <label>积分兑换</label><input type="number" v-model="form.points_cost" />
          <label>总名额</label><input type="number" v-model="form.capacity" />
          <label>渐变色</label><input v-model="form.gradient" placeholder="例: linear-gradient(135deg, #667eea, #764ba2)" />
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
              <input type="date" v-model="s.date" />
              <input v-model="s.time" placeholder="时间" style="width:80px" />
              <input v-model="s.location" placeholder="地点" style="flex:1" />
              <input type="number" v-model="s.capacity" placeholder="名额" style="width:60px" />
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
const showForm = ref(false)
const editId = ref(null)
const form = ref({})
const statusMap = { open: '开放', closed: '关闭', draft: '草稿' }

function resetForm() {
  form.value = {
    title: '', description: '', location: '', start_date: '', end_date: '',
    price: 0, points_cost: 0, capacity: 0, gradient: '', cover_url: '', status: 'open',
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
}

function editActivity(a) {
  editId.value = a.id
  form.value = {
    title: a.title, description: a.description || '', location: a.location || '',
    start_date: a.start_date || '', end_date: a.end_date || '',
    price: a.price || 0, points_cost: a.points_cost || 0,
    capacity: a.capacity || 0, gradient: a.gradient || '', cover_url: a.cover_url || '',
    status: a.status || 'open',
    sessions: a.sessions ? [...a.sessions] : []
  }
  showForm.value = true
}

async function saveActivity() {
  const url = editId.value ? `/api/admin/activities/${editId.value}` : '/api/admin/activities'
  const method = editId.value ? 'PUT' : 'POST'
  try {
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form.value)
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
  form.value.sessions.push({ date: '', time: '', location: '', capacity: 0 })
}

onMounted(loadActivities)
</script>

<style scoped>
.activities-admin { padding: 0; }
.aa-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.aa-header h2 { margin: 0; color: #333; font-size: 18px; }
.aa-add-btn { padding: 8px 20px; background: #FF7B2C; color: #fff; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; }

.aa-table-wrap { background: #fff; border-radius: 14px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.aa-table { width: 100%; border-collapse: collapse; }
.aa-table th { text-align: left; padding: 12px 16px; background: #fafafa; color: #666; font-size: 13px; font-weight: 600; border-bottom: 1px solid #eee; }
.aa-table td { padding: 10px 16px; border-bottom: 1px solid #f0f0f0; font-size: 14px; color: #333; }
.aa-table tr:last-child td { border-bottom: none; }
.aa-tag { padding: 2px 10px; border-radius: 10px; font-size: 12px; }
.aa-tag.open { background: #e8f5e9; color: #388e3c; }
.aa-tag.closed { background: #fce4ec; color: #c62828; }
.aa-tag.draft { background: #f3e5f5; color: #7b1fa2; }
.aa-empty { padding: 40px; text-align: center; color: #999; font-size: 14px; }

.aa-btn-sm { padding: 4px 12px; border: 1px solid #e0e0e0; background: #fff; border-radius: 6px; cursor: pointer; font-size: 12px; color: #666; margin-right: 4px; }
.aa-btn-sm:hover { border-color: #FF7B2C; color: #FF7B2C; }
.aa-btn-warn { color: #e6a23c; border-color: #f5dab1; }
.aa-btn-danger { color: #f56c6c; border-color: #fbc4c4; }

/* Modal */
.aa-modal { position: fixed; inset: 0; z-index: 100; display: flex; align-items: center; justify-content: center; }
.aa-modal-mask { position: absolute; inset: 0; background: rgba(0,0,0,0.4); }
.aa-modal-body { position: relative; background: #fff; border-radius: 16px; padding: 24px; width: 90%; max-width: 560px; max-height: 85vh; overflow-y: auto; }
.aa-modal-body h3 { margin: 0 0 16px; color: #333; }

.aa-form { display: flex; flex-direction: column; gap: 8px; }
.aa-form label { font-size: 13px; color: #666; font-weight: 600; margin-top: 4px; }
.aa-form input, .aa-form textarea, .aa-form select { padding: 8px 12px; border: 1px solid #e0e0e0; border-radius: 8px; font-size: 14px; color: #333; background: #fafafa; }
.aa-form input:focus, .aa-form textarea:focus, .aa-form select:focus { outline: none; border-color: #FF7B2C; }

.aa-sessions { border-top: 1px solid #eee; padding-top: 8px; margin-top: 4px; }
.aa-session-item { display: flex; gap: 6px; align-items: center; margin-top: 6px; }
.aa-session-item input { flex: 1; }

.aa-modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px; }
.aa-btn { padding: 8px 24px; border: 1px solid #e0e0e0; background: #fff; border-radius: 8px; cursor: pointer; font-size: 14px; color: #666; }
.aa-btn-primary { background: #FF7B2C; color: #fff; border-color: #FF7B2C; }
</style>
