<template>
  <div class="oa">
    <div class="oa-head">
      <div>
        <h2>优惠券管理</h2>
        <p class="oa-sub">上架 / 编辑 / 下架 / 删除，会员端优惠券专区实时同步</p>
      </div>
      <div class="oa-head-right">
        <span class="oa-count">共 {{ offers.length }} 张（生效 {{ activeCount }}）</span>
        <button class="oa-btn oa-btn-primary" @click="openAdd">＋ 新增优惠券</button>
      </div>
    </div>

    <div class="oa-search">
      <input v-model="kw" placeholder="搜索商户 / 券说明" />
    </div>

    <div class="oa-table-wrap">
      <table class="oa-table">
        <thead>
          <tr><th>ID</th><th>商户</th><th>券说明</th><th>面额</th><th>分类</th><th>有效期</th><th>状态</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="o in filtered" :key="o.id" :class="{ 'row-off': o.status !== 'active' }">
            <td>{{ o.id }}</td>
            <td>{{ o.shop_name }}</td>
            <td>{{ o.label }}</td>
            <td><b>¥{{ o.amount }}</b></td>
            <td><span class="oa-cat" :style="{ background: catColor(o.category) }">{{ catLabel(o.category) }}</span></td>
            <td>{{ o.expire || '-' }}</td>
            <td><span class="oa-tag" :class="o.status">{{ statusLabel(o.status) }}</span></td>
            <td class="oa-ops">
              <button class="oa-op" @click="openEdit(o)">编辑</button>
              <button class="oa-op" :class="o.status === 'active' ? 'down' : 'up'" @click="toggle(o)">
                {{ o.status === 'active' ? '下架' : '上架' }}
              </button>
              <button class="oa-op danger" @click="remove(o)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="!filtered.length" class="oa-empty">暂无优惠券数据</div>
    </div>

    <!-- 新增 / 编辑弹窗 -->
    <div v-if="showForm" class="oa-mask" @click.self="closeForm">
      <div class="oa-modal">
        <div class="oa-modal-head">
          <h3>{{ editId ? '编辑优惠券' : '新增优惠券' }}</h3>
          <button class="oa-close" @click="closeForm">×</button>
        </div>
        <div class="oa-form">
          <label>商户名称</label>
          <input v-model="form.shop_name" placeholder="如：霸王茶姬" />

          <label>券说明</label>
          <input v-model="form.label" placeholder="如：指定饮品买一赠一" />

          <div class="oa-row">
            <div>
              <label>面额（元）</label>
              <input type="number" v-model="form.amount" />
            </div>
            <div>
              <label>有效期至</label>
              <input v-model="form.expire" placeholder="2026-12-31" />
            </div>
          </div>

          <label>分类</label>
          <div class="oa-cats">
            <button v-for="c in catOptions" :key="c.key" type="button"
                    class="oa-cat-opt" :class="{ on: form.category === c.key }"
                    :style="{ borderColor: form.category === c.key ? c.color : '#333' }"
                    @click="form.category = c.key; form.color = c.color">
              {{ c.label }}
            </button>
          </div>

          <label>卡片配色</label>
          <div class="oa-colors">
            <button v-for="col in colorPresets" :key="col" type="button"
                    class="oa-color" :class="{ on: form.color === col }"
                    :style="{ background: col }" @click="form.color = col"></button>
          </div>

          <label class="oa-switch">
            <input type="checkbox" v-model="form.active" />
            <span>{{ form.active ? '立即上架（会员端可见）' : '暂存下架' }}</span>
          </label>
        </div>
        <div class="oa-modal-foot">
          <button class="oa-btn" @click="closeForm">取消</button>
          <button class="oa-btn oa-btn-primary" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存' }}</button>
        </div>
      </div>
    </div>

    <div v-if="toast" class="oa-toast">{{ toast }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const offers = ref([])
const kw = ref('')
const showForm = ref(false)
const editId = ref(null)
const saving = ref(false)
const toast = ref('')

const colorPresets = [
  '#FF7B2C', '#C4923A', '#9B4A3E', '#C9956C', '#D4A59A',
  '#4A90D9', '#9B7BD4', '#E8809E', '#3E8E41', '#6B6E64'
]
const catOptions = [
  { key: 'food', label: '餐饮券', color: '#C4923A' },
  { key: 'retail', label: '零售券', color: '#4A90D9' },
  { key: 'fun', label: '娱乐券', color: '#9B7BD4' },
  { key: 'kids', label: '亲子券', color: '#E8809E' },
  { key: 'service', label: '生活服务券', color: '#3E8E41' },
  { key: 'parking', label: '停车券', color: '#6B6E64' }
]

const form = ref({ shop_name: '', label: '', amount: 0, expire: '', category: 'food', color: '#FF7B2C', active: true })

const activeCount = computed(() => offers.value.filter(o => o.status === 'active').length)
const filtered = computed(() => {
  const q = kw.value.trim().toLowerCase()
  if (!q) return offers.value
  return offers.value.filter(o =>
    (o.shop_name || '').toLowerCase().includes(q) ||
    (o.label || '').toLowerCase().includes(q))
})

function catLabel(c) {
  return (catOptions.find(x => x.key === c) || {}).label || c || '-'
}
function catColor(c) {
  return (catOptions.find(x => x.key === c) || {}).color || '#888'
}
function statusLabel(s) {
  return { active: '生效中', inactive: '已停用' }[s] || s || '-'
}

async function load() {
  try {
    const res = await fetch('/api/admin/offers')
    const d = await res.json()
    if (d && d.data) offers.value = d.data
  } catch (e) { console.error(e) }
}

function showToast(msg) {
  toast.value = msg
  setTimeout(() => { toast.value = '' }, 1800)
}

function resetForm() {
  form.value = { shop_name: '', label: '', amount: 0, expire: '', category: 'food', color: '#FF7B2C', active: true }
}
function openAdd() {
  editId.value = null
  resetForm()
  showForm.value = true
}
function openEdit(o) {
  editId.value = o.id
  form.value = {
    shop_name: o.shop_name, label: o.label, amount: o.amount,
    expire: o.expire || '', category: o.category || 'food', color: o.color || '#FF7B2C',
    active: o.status === 'active'
  }
  showForm.value = true
}
function closeForm() { showForm.value = false }

async function save() {
  if (!form.value.shop_name.trim()) return showToast('请填写商户名称')
  if (!form.value.label.trim()) return showToast('请填写券说明')
  if (!String(form.value.amount).trim() || Number(form.value.amount) < 0) return showToast('面额不能为负')
  saving.value = true
  const payload = {
    shop_name: form.value.shop_name.trim(),
    label: form.value.label.trim(),
    amount: Number(form.value.amount) || 0,
    expire: form.value.expire.trim(),
    category: form.value.category,
    color: form.value.color,
    status: form.value.active ? 'active' : 'inactive'
  }
  try {
    let res
    if (editId.value) {
      res = await fetch('/api/admin/offers/' + editId.value, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
      })
    } else {
      res = await fetch('/api/admin/offers', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
      })
    }
    const d = await res.json()
    if (d && d.ok) {
      showToast(editId.value ? '已更新' : (form.value.active ? '已上架' : '已添加（下架）'))
      showForm.value = false
      await load()
    } else {
      showToast((d && d.error) || '保存失败')
    }
  } catch (e) {
    showToast('保存失败')
  } finally {
    saving.value = false
  }
}

async function toggle(o) {
  try {
    const res = await fetch('/api/admin/offers/' + o.id + '/toggle', { method: 'POST' })
    const d = await res.json()
    if (d && d.ok) {
      showToast(d.data.message)
      await load()
    } else showToast((d && d.error) || '操作失败')
  } catch (e) { showToast('操作失败') }
}

async function remove(o) {
  if (!confirm('确定删除该优惠券？已领券的用户记录不受影响。')) return
  try {
    const res = await fetch('/api/admin/offers/' + o.id, { method: 'DELETE' })
    const d = await res.json()
    if (d && d.ok) { showToast('已删除'); await load() }
    else showToast((d && d.error) || '删除失败')
  } catch (e) { showToast('删除失败') }
}

onMounted(load)
</script>

<style scoped>
.oa { padding: 0; color: #F0F0F0; }
.oa-head { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 14px; gap: 12px; flex-wrap: wrap; }
.oa-head h2 { margin: 0; font-size: 18px; color: #F0F0F0; }
.oa-sub { margin: 4px 0 0; font-size: 12px; color: #888; }
.oa-head-right { display: flex; align-items: center; gap: 12px; }
.oa-count { font-size: 12px; color: #999; }
.oa-btn { padding: 8px 14px; border-radius: 8px; border: 1px solid #333; background: #1A1A1A; color: #E0E0E0; font-size: 13px; cursor: pointer; }
.oa-btn-primary { background: linear-gradient(135deg, #FF7B2C, #E85D04); border: none; color: #fff; font-weight: 600; }
.oa-btn-primary:disabled { opacity: .6; cursor: default; }

.oa-search { margin-bottom: 12px; }
.oa-search input { width: 100%; padding: 10px 14px; border: 1px solid #333; border-radius: 8px; font-size: 14px; color: #F0F0F0; background: #151515; box-sizing: border-box; }
.oa-search input:focus { outline: none; border-color: #FF7B2C; }

.oa-table-wrap { background: #151515; border-radius: 14px; overflow: hidden; }
.oa-table { width: 100%; border-collapse: collapse; }
.oa-table th { text-align: left; padding: 12px 16px; background: #1A1A1A; color: #BBB; font-size: 13px; font-weight: 600; border-bottom: 1px solid #2E2E2E; }
.oa-table td { padding: 11px 16px; border-bottom: 1px solid #262626; font-size: 13px; color: #E8E8E8; vertical-align: middle; }
.oa-table tr:last-child td { border-bottom: none; }
.oa-table .row-off td { opacity: .55; }
.oa-cat { padding: 2px 10px; border-radius: 10px; font-size: 12px; color: #fff; }
.oa-tag { padding: 2px 10px; border-radius: 10px; font-size: 12px; }
.oa-tag.active { background: rgba(255,123,44,.15); color: #FF9A52; }
.oa-tag.inactive { background: #2A2A2A; color: #999; }
.oa-ops { display: flex; gap: 6px; }
.oa-op { padding: 5px 10px; border-radius: 7px; border: 1px solid #333; background: #1F1F1F; color: #DDD; font-size: 12px; cursor: pointer; }
.oa-op.down { border-color: #5a4a2a; color: #E8B873; }
.oa-op.up { border-color: #2a5a3a; color: #8FE0A0; }
.oa-op.danger { border-color: #5a2a2a; color: #E88A8A; }
.oa-empty { padding: 40px; text-align: center; color: #999; font-size: 14px; }

.oa-mask { position: fixed; inset: 0; background: rgba(0,0,0,.6); display: flex; align-items: center; justify-content: center; z-index: 50; }
.oa-modal { width: 440px; max-width: 92vw; background: #1A1A1A; border-radius: 16px; border: 1px solid #2E2E2E; padding: 18px 20px 20px; box-shadow: 0 12px 40px rgba(0,0,0,.5); }
.oa-modal-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.oa-modal-head h3 { margin: 0; font-size: 16px; color: #F0F0F0; }
.oa-close { background: none; border: none; color: #999; font-size: 24px; cursor: pointer; line-height: 1; }
.oa-form label { display: block; font-size: 12px; color: #AAA; margin: 12px 0 6px; }
.oa-form input[type=text], .oa-form input[type=number], .oa-form input:not([type]) { width: 100%; padding: 9px 12px; border: 1px solid #333; border-radius: 8px; background: #121212; color: #EEE; font-size: 13px; box-sizing: border-box; }
.oa-form input:focus { outline: none; border-color: #FF7B2C; }
.oa-row { display: flex; gap: 12px; }
.oa-row > div { flex: 1; }
.oa-cats { display: flex; flex-wrap: wrap; gap: 6px; }
.oa-cat-opt { padding: 6px 10px; border-radius: 8px; border: 1px solid #333; background: #121212; color: #DDD; font-size: 12px; cursor: pointer; }
.oa-cat-opt.on { background: #1F1F1F; color: #fff; }
.oa-colors { display: flex; flex-wrap: wrap; gap: 8px; }
.oa-color { width: 26px; height: 26px; border-radius: 50%; border: 2px solid transparent; cursor: pointer; }
.oa-color.on { border-color: #fff; box-shadow: 0 0 0 2px #000; }
.oa-switch { display: flex; align-items: center; gap: 8px; margin-top: 14px; cursor: pointer; color: #DDD !important; }
.oa-switch input { width: auto; }
.oa-modal-foot { display: flex; justify-content: flex-end; gap: 10px; margin-top: 18px; }

.oa-toast { position: fixed; left: 50%; top: 18%; transform: translateX(-50%); background: rgba(20,20,20,.95); color: #fff; padding: 10px 18px; border-radius: 10px; font-size: 13px; border: 1px solid #333; z-index: 60; }
</style>
