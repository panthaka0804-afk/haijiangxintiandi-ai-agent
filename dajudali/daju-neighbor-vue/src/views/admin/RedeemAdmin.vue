<template>
  <div class="redeem-admin">
    <div class="aa-header">
      <div>
        <h2>积分商城管理</h2>
        <p class="aa-sub">上架、编辑、下架你的积分商品 · 共 {{ goods.length }} 项（上架中 {{ activeCount }}）</p>
      </div>
      <button class="ra-add" @click="openAdd">＋ 新增商品</button>
    </div>

    <div class="aa-search">
      <input v-model="kw" placeholder="搜索商品名称 / 分类" />
    </div>

    <div class="aa-table-wrap">
      <table class="aa-table">
        <thead>
          <tr><th>商品</th><th>分类</th><th>所需积分</th><th>库存</th><th>状态</th><th class="op-col">操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="g in filtered" :key="g.id">
            <td>
              <span class="ra-dot" :style="{ background: g.gradient || '#6A6A6E' }"></span>
              <span class="ra-name">{{ g.name }}</span>
              <span class="ra-id">{{ g.id }}</span>
            </td>
            <td><span class="ra-cat">{{ g.category }}</span></td>
            <td><b>{{ g.points }}</b> 分</td>
            <td>{{ g.stock < 0 ? '不限' : g.stock }}</td>
            <td><span class="ra-tag" :class="g.status">{{ g.status === 'active' ? '上架中' : '已下架' }}</span></td>
            <td class="op-col">
              <button class="ra-op" @click="openEdit(g)">编辑</button>
              <button class="ra-op" :class="g.status === 'active' ? 'down' : 'up'" @click="toggle(g)">
                {{ g.status === 'active' ? '下架' : '上架' }}
              </button>
              <button class="ra-op del" @click="remove(g)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="!filtered.length" class="aa-empty">暂无积分商品，点右上角「新增商品」上架第一个吧</div>
    </div>

    <!-- 新增 / 编辑 弹窗 -->
    <div v-if="showForm" class="ra-mask" @click.self="closeForm">
      <div class="ra-modal">
        <div class="ra-modal-head">
          <h3>{{ editing ? '编辑商品' : '新增积分商品' }}</h3>
          <button class="ra-x" @click="closeForm">×</button>
        </div>

        <div class="ra-field">
          <label>商品名称 <i>*</i></label>
          <input v-model="form.name" placeholder="如：星巴克 拿铁券" />
        </div>

        <div class="ra-row">
          <div class="ra-field">
            <label>分类</label>
            <select v-model="form.category">
              <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
            </select>
          </div>
          <div class="ra-field">
            <label>所需积分 <i>*</i></label>
            <input v-model.number="form.points" type="number" min="1" placeholder="0" />
          </div>
        </div>

        <div class="ra-field">
          <label>库存 <span class="ra-hint">（-1 表示不限量）</span></label>
          <input v-model.number="form.stock" type="number" placeholder="-1" />
        </div>

        <div class="ra-field">
          <label>卡片配色</label>
          <div class="ra-swatches">
            <button v-for="p in presets" :key="p.value" class="ra-sw"
                    :class="{ on: form.gradient === p.value }"
                    :style="{ background: p.value }" :title="p.label"
                    @click="form.gradient = p.value"></button>
          </div>
        </div>

        <div class="ra-field">
          <label>上架状态</label>
          <div class="ra-radios">
            <label class="ra-radio"><input type="radio" value="active" v-model="form.status" /> 立即上架</label>
            <label class="ra-radio"><input type="radio" value="inactive" v-model="form.status" /> 暂存下架</label>
          </div>
        </div>

        <div class="ra-modal-foot">
          <button class="ra-cancel" @click="closeForm">取消</button>
          <button class="ra-save" :disabled="saving" @click="save">{{ saving ? '保存中…' : (editing ? '保存修改' : '确认上架') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const goods = ref([])
const kw = ref('')
const showForm = ref(false)
const editing = ref(false)
const saving = ref(false)

const categories = ['餐饮', '购物', '娱乐', '停车', '生活服务', '亲子', '其他']
const presets = [
  { label: '金黄', value: 'linear-gradient(135deg, #C4923A, #E0B45C)' },
  { label: '浅橙棕', value: 'linear-gradient(135deg, #C9956C, #E6B894)' },
  { label: '深红棕', value: 'linear-gradient(135deg, #9B4A3E, #C97A6E)' },
  { label: '灰紫', value: 'linear-gradient(135deg, #8B8B90, #B5B5BA)' },
  { label: '深灰绿', value: 'linear-gradient(135deg, #6B6E64, #9AA39A)' },
  { label: '品牌橙', value: 'linear-gradient(135deg, #FF7B2C, #FFA866)' },
  { label: '蓝', value: 'linear-gradient(135deg, #4A90D9, #7DB8F0)' },
  { label: '紫', value: 'linear-gradient(135deg, #9B7BD4, #C9B6E8)' },
  { label: '绿', value: 'linear-gradient(135deg, #3E8E41, #6FBF73)' },
  { label: '粉', value: 'linear-gradient(135deg, #E8809E, #F0AAC0)' },
]

const form = ref({ id: '', name: '', category: '餐饮', points: 0, stock: -1, gradient: presets[0].value, status: 'active' })

const activeCount = computed(() => goods.value.filter(g => g.status === 'active').length)
const filtered = computed(() => {
  const q = kw.value.trim().toLowerCase()
  if (!q) return goods.value
  return goods.value.filter(g =>
    (g.name || '').toLowerCase().includes(q) ||
    (g.category || '').includes(q))
})

async function load() {
  try {
    const res = await fetch('/api/admin/redeem-goods')
    const d = await res.json()
    if (d && d.ok) goods.value = d.data
  } catch (e) { console.error(e) }
}

function openAdd() {
  editing.value = false
  form.value = { id: '', name: '', category: '餐饮', points: 0, stock: -1, gradient: presets[0].value, status: 'active' }
  showForm.value = true
}
function openEdit(g) {
  editing.value = true
  form.value = { id: g.id, name: g.name, category: g.category, points: g.points, stock: g.stock, gradient: g.gradient || presets[0].value, status: g.status }
  showForm.value = true
}
function closeForm() { showForm.value = false }

async function save() {
  if (!form.value.name.trim()) { alert('请填写商品名称'); return }
  if (!form.value.points || form.value.points <= 0) { alert('所需积分必须大于 0'); return }
  saving.value = true
  try {
    const url = editing.value ? `/api/admin/redeem-goods/${form.value.id}` : '/api/admin/redeem-goods'
    const method = editing.value ? 'PUT' : 'POST'
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: form.value.name.trim(),
        category: form.value.category,
        points: form.value.points,
        stock: form.value.stock == null ? -1 : form.value.stock,
        gradient: form.value.gradient,
        status: form.value.status
      })
    })
    const d = await res.json()
    if (d && d.ok) {
      showForm.value = false
      await load()
    } else {
      alert(d && d.error ? d.error : '保存失败')
    }
  } catch (e) {
    alert('网络错误，请稍后重试')
  } finally {
    saving.value = false
  }
}

async function toggle(g) {
  try {
    const res = await fetch(`/api/admin/redeem-goods/${g.id}/toggle`, { method: 'POST' })
    const d = await res.json()
    if (d && d.ok) {
      g.status = d.data.status
    } else {
      alert(d && d.error ? d.error : '操作失败')
    }
  } catch (e) { alert('网络错误') }
}

async function remove(g) {
  if (!confirm(`确定删除「${g.name}」？此操作不可恢复。`)) return
  try {
    const res = await fetch(`/api/admin/redeem-goods/${g.id}`, { method: 'DELETE' })
    const d = await res.json()
    if (d && d.ok) {
      await load()
    } else {
      alert(d && d.error ? d.error : '删除失败')
    }
  } catch (e) { alert('网络错误') }
}

onMounted(load)
</script>

<style scoped>
.redeem-admin { padding: 0; }
.aa-header { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 16px; }
.aa-header h2 { margin: 0; color: #F0F0F0; font-size: 18px; }
.aa-sub { margin: 4px 0 0; color: #999; font-size: 12px; }
.ra-add {
  background: linear-gradient(135deg, #FF7B2C, #FFA866); color: #1A1A1A; border: none;
  padding: 9px 16px; border-radius: 10px; font-size: 14px; font-weight: 600; cursor: pointer;
  box-shadow: 0 4px 14px rgba(255,123,44,.3);
}
.ra-add:hover { filter: brightness(1.05); }

.aa-search { margin-bottom: 12px; }
.aa-search input {
  width: 100%; padding: 10px 14px; border: 1px solid #2E2E2E; border-radius: 8px;
  font-size: 14px; color: #F0F0F0; background: #1A1A1A; box-sizing: border-box;
}
.aa-search input:focus { outline: none; border-color: #FF7B2C; }

.aa-table-wrap { background: #1A1A1A; border-radius: 14px; overflow: hidden; }
.aa-table { width: 100%; border-collapse: collapse; }
.aa-table th { text-align: left; padding: 12px 16px; background: #161616; color: #BBBBBB; font-size: 13px; font-weight: 600; border-bottom: 1px solid #2E2E2E; }
.aa-table td { padding: 11px 16px; border-bottom: 1px solid #262626; font-size: 13px; color: #F0F0F0; vertical-align: middle; }
.aa-table tr:last-child td { border-bottom: none; }
.ra-dot { display: inline-block; width: 12px; height: 12px; border-radius: 4px; margin-right: 8px; vertical-align: middle; }
.ra-name { font-weight: 600; }
.ra-id { color: #666; font-size: 11px; margin-left: 6px; }
.ra-cat { display: inline-block; padding: 2px 9px; border-radius: 9px; background: rgba(255,255,255,.06); color: #CFCFCF; font-size: 12px; }
.ra-tag { padding: 2px 10px; border-radius: 10px; font-size: 12px; }
.ra-tag.active { background: rgba(255,123,44,.16); color: #FF9D5C; }
.ra-tag.inactive { background: rgba(255,255,255,.07); color: #999; }

.op-col { text-align: right; white-space: nowrap; }
.ra-op {
  background: #262626; color: #E0E0E0; border: 1px solid #333; border-radius: 8px;
  padding: 5px 10px; font-size: 12px; cursor: pointer; margin-left: 6px;
}
.ra-op:hover { border-color: #FF7B2C; color: #FF9D5C; }
.ra-op.down:hover { border-color: #F0A93C; color: #F0C44C; }
.ra-op.up:hover { border-color: #67C23A; color: #8BE08B; }
.ra-op.del:hover { border-color: #F56C6C; color: #FF8A8A; }

.aa-empty { padding: 40px; text-align: center; color: #999; font-size: 14px; }

/* 弹窗 */
.ra-mask { position: fixed; inset: 0; background: rgba(0,0,0,.6); display: flex; align-items: center; justify-content: center; z-index: 999; padding: 20px; }
.ra-modal { width: 100%; max-width: 440px; background: #1C1C1C; border: 1px solid #2E2E2E; border-radius: 16px; padding: 20px; box-sizing: border-box; }
.ra-modal-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.ra-modal-head h3 { margin: 0; color: #F0F0F0; font-size: 16px; }
.ra-x { background: none; border: none; color: #999; font-size: 22px; cursor: pointer; line-height: 1; }
.ra-x:hover { color: #fff; }

.ra-field { margin-bottom: 14px; }
.ra-row { display: flex; gap: 12px; }
.ra-row .ra-field { flex: 1; }
.ra-field label { display: block; color: #BBB; font-size: 12px; margin-bottom: 6px; }
.ra-field label i { color: #FF7B2C; font-style: normal; }
.ra-hint { color: #777; font-size: 11px; }
.ra-field input, .ra-field select {
  width: 100%; padding: 9px 12px; border: 1px solid #333; border-radius: 9px;
  background: #141414; color: #F0F0F0; font-size: 14px; box-sizing: border-box;
}
.ra-field input:focus, .ra-field select:focus { outline: none; border-color: #FF7B2C; }

.ra-swatches { display: flex; flex-wrap: wrap; gap: 8px; }
.ra-sw { width: 30px; height: 30px; border-radius: 8px; border: 2px solid transparent; cursor: pointer; }
.ra-sw.on { border-color: #fff; box-shadow: 0 0 0 2px #FF7B2C; }

.ra-radios { display: flex; gap: 18px; }
.ra-radio { display: flex; align-items: center; gap: 6px; color: #DDD; font-size: 13px; cursor: pointer; }
.ra-radio input { accent-color: #FF7B2C; }

.ra-modal-foot { display: flex; gap: 12px; margin-top: 18px; }
.ra-cancel { flex: 1; background: #262626; color: #DDD; border: 1px solid #333; border-radius: 10px; padding: 10px; font-size: 14px; cursor: pointer; }
.ra-cancel:hover { border-color: #555; }
.ra-save { flex: 1; background: linear-gradient(135deg, #FF7B2C, #FFA866); color: #1A1A1A; border: none; border-radius: 10px; padding: 10px; font-size: 14px; font-weight: 600; cursor: pointer; }
.ra-save:disabled { opacity: .6; cursor: default; }
</style>
