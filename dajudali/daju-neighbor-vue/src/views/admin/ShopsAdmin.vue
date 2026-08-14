<template>
  <div class="in-page">
    <div class="page-header">
      <div class="ph-left">
        <div class="ph-title"><span class="ph-bar"></span><h3>商户管理</h3></div>
        <div class="ph-sub">商场入驻商户 · 共 {{ shops.length }} 家</div>
      </div>
      <div class="ph-actions">
        <input v-model="kw" class="kw-input" placeholder="搜索商户名称 / 品类" />
        <button class="btn-primary" @click="showAddDialog">+ 新增商户</button>
      </div>
    </div>

    <div class="stat-row">
      <div class="mc-card stat mc-card-gold"><div class="stat-num">{{ shops.length }}</div><div class="stat-label">商户总数</div></div>
      <div class="mc-card stat mc-card-orange"><div class="stat-num">{{ couponCount }}</div><div class="stat-label">含券商户</div></div>
      <div class="mc-card stat mc-card-blue"><div class="stat-num">{{ floorCount }}</div><div class="stat-label">覆盖楼层</div></div>
      <div class="mc-card stat mc-card-green"><div class="stat-num">{{ categoryCount }}</div><div class="stat-label">经营品类</div></div>
    </div>

    <div class="panel">
      <div class="panel-head">
        <span class="dot" style="background:#9B4A3E"></span>
        <h2>商户列表</h2>
        <span class="engine">实时</span>
      </div>
      <div class="tbl-wrap">
        <table class="mc-table">
          <thead>
            <tr>
              <th>名称</th><th>楼层</th><th>品类</th><th>电话</th><th>营业时间</th><th>标签</th><th>优惠券</th><th width="120">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in filtered" :key="s.id">
              <td>
                <span class="sa-dot" :style="{background: s.color || '#C9956C'}"></span>
                {{ s.name }}
              </td>
              <td>{{ s.floor ? s.floor + 'F' : '-' }}</td>
              <td>{{ s.category || '-' }}</td>
              <td>{{ s.phone || '-' }}</td>
              <td>{{ s.hours || '-' }}</td>
              <td class="sa-tags">
                <span v-for="t in (s.tags || [])" :key="t" class="pill orange" style="margin-right:4px">{{ t }}</span>
                <span v-if="!(s.tags && s.tags.length)" class="muted">-</span>
              </td>
              <td>
                <span v-if="s.has_coupon" class="pill gold">满{{ s.coupon_condition }}减{{ s.coupon_amount }}</span>
                <span v-else class="muted">—</span>
              </td>
              <td>
                <button class="lnk" @click="showEditDialog(s)">编辑</button>
                <button class="lnk danger" @click="removeShop(s)">删除</button>
              </td>
            </tr>
            <tr v-if="!filtered.length"><td colspan="8" class="empty">暂无商户数据</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 新增 / 编辑弹窗 -->
    <div v-if="dialogVisible" class="modal-mask" @click.self="dialogVisible = false">
      <div class="modal-card">
        <div class="modal-head">
          <span class="mh-bar"></span>
          <h3>{{ isEdit ? '编辑商户' : '新增商户' }}</h3>
          <button class="modal-x" @click="dialogVisible = false">×</button>
        </div>
        <div class="modal-body">
          <div class="fld"><label>商户名称 *</label><input v-model="form.name" placeholder="如：星巴克" /></div>
          <div class="fld-row">
            <div class="fld"><label>楼层</label><input v-model="form.floor" placeholder="如：1" /></div>
            <div class="fld"><label>区域</label><input v-model="form.zone" placeholder="如：1区" /></div>
          </div>
          <div class="fld"><label>品类</label><input v-model="form.category" placeholder="如：餐饮 / 零售" /></div>
          <div class="fld"><label>标签（逗号分隔）</label><input v-model="form.tags" placeholder="如：咖啡,连锁,会员日" /></div>
          <div class="fld-row">
            <div class="fld"><label>电话</label><input v-model="form.phone" placeholder="可选" /></div>
            <div class="fld"><label>营业时间</label><input v-model="form.hours" placeholder="如：10:00-22:00" /></div>
          </div>
          <div class="fld"><label>主题色</label>
            <div class="color-row">
              <input type="color" v-model="form.color" />
              <input class="color-hex" v-model="form.color" placeholder="#C9956C" />
            </div>
          </div>
          <div class="fld"><label>简介</label><textarea v-model="form.description" rows="2" placeholder="商户一句话介绍"></textarea></div>
          <div class="coupon-box">
            <label class="cb-line"><input type="checkbox" v-model="form.has_coupon" /> 提供到店优惠券</label>
            <div v-if="form.has_coupon" class="fld-row">
              <div class="fld"><label>满（元）</label><input type="number" v-model="form.coupon_condition" /></div>
              <div class="fld"><label>减（元）</label><input type="number" v-model="form.coupon_amount" /></div>
            </div>
            <div v-if="form.has_coupon" class="fld"><label>有效期至</label><input v-model="form.coupon_expire" placeholder="如：2026-12-31" /></div>
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn-ghost" @click="dialogVisible = false">取消</button>
          <button class="btn-primary" :disabled="saving" @click="saveShop">{{ saving ? '保存中…' : '保存' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getShops, createShop, updateShop, deleteShop } from '@/api'

const shops = ref([])
const kw = ref('')
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)

const filtered = computed(() => {
  const q = kw.value.trim().toLowerCase()
  if (!q) return shops.value
  return shops.value.filter(s =>
    (s.name || '').toLowerCase().includes(q) ||
    (s.category || '').includes(q))
})

const couponCount = computed(() => shops.value.filter(s => s.has_coupon).length)
const floorCount = computed(() => new Set(shops.value.map(s => s.floor).filter(Boolean)).size)
const categoryCount = computed(() => new Set(shops.value.map(s => s.category).filter(Boolean)).size)

const emptyForm = () => ({
  id: null, name: '', floor: '', zone: '', category: '', tags: '', color: '#C9956C',
  phone: '', hours: '', description: '', has_coupon: false, coupon_condition: 0, coupon_amount: 0, coupon_expire: ''
})
const form = reactive(emptyForm())

async function loadShops() {
  loading.value = true
  try {
    const res = await getShops()
    if (res && res.data) shops.value = res.data
  } catch (e) { console.error(e) } finally { loading.value = false }
}

function showAddDialog() {
  Object.assign(form, emptyForm())
  isEdit.value = false
  dialogVisible.value = true
}

function showEditDialog(s) {
  Object.assign(form, {
    id: s.id, name: s.name || '', floor: s.floor || '', zone: s.zone || '',
    category: s.category || '', tags: Array.isArray(s.tags) ? s.tags.join('、') : (s.tags || ''),
    color: s.color || '#C9956C', phone: s.phone || '', hours: s.hours || '',
    description: s.description || '', has_coupon: !!s.has_coupon,
    coupon_condition: s.coupon_condition || 0, coupon_amount: s.coupon_amount || 0,
    coupon_expire: s.coupon_expire || ''
  })
  isEdit.value = true
  dialogVisible.value = true
}

async function saveShop() {
  if (!form.name.trim()) { ElMessage.warning('请填写商户名称'); return }
  saving.value = true
  const payload = {
    name: form.name.trim(), floor: form.floor.trim(), zone: form.zone.trim(),
    category: form.category.trim(), tags: form.tags.trim(), color: form.color,
    phone: form.phone.trim(), hours: form.hours.trim(), description: form.description.trim(),
    has_coupon: form.has_coupon, coupon_condition: Number(form.coupon_condition) || 0,
    coupon_amount: Number(form.coupon_amount) || 0, coupon_expire: form.coupon_expire.trim()
  }
  try {
    if (isEdit.value) {
      const res = await updateShop(form.id, payload)
      if (!res.ok) throw new Error(res.error || '更新失败')
      ElMessage.success('已更新')
    } else {
      const res = await createShop(payload)
      if (!res.ok) throw new Error(res.error || '新增失败')
      ElMessage.success('已新增')
    }
    dialogVisible.value = false
    await loadShops()
  } catch (e) {
    ElMessage.error(e.message || '操作失败')
  } finally {
    saving.value = false
  }
}

async function removeShop(s) {
  try {
    await ElMessageBox.confirm(`确定删除商户「${s.name}」？该操作不可恢复。`, '删除确认', { type: 'warning' })
  } catch { return }
  try {
    const res = await deleteShop(s.id)
    if (!res.ok) throw new Error(res.error || '删除失败')
    ElMessage.success('已删除')
    await loadShops()
  } catch (e) {
    ElMessage.error(e.message || '删除失败')
  }
}

onMounted(loadShops)
</script>

<style scoped>
.kw-input {
  width: 220px; padding: 9px 12px; border: 1px solid #2a2a2a; border-radius: 8px;
  background: #1f2125; color: #e8e8e8; font-size: 13px; box-sizing: border-box;
}
.kw-input::placeholder { color: #6b6b6b; }
.kw-input:focus { outline: none; border-color: #FF7B2C; box-shadow: 0 0 0 3px rgba(255,123,44,0.16); }
.btn-primary {
  background: linear-gradient(135deg, #FF7B2C, #E85D04); color: #fff; border: none;
  padding: 9px 16px; border-radius: 8px; font-size: 13px; cursor: pointer; font-weight: 600;
  box-shadow: 0 6px 16px rgba(232,93,4,0.30);
}
.btn-primary:hover { background: linear-gradient(135deg, #FF8F47, #F26A0E); }
.btn-primary:disabled { opacity: 0.6; cursor: default; }
.btn-ghost { background: #1f2125; border: 1px solid #3a3d43; color: #e6e6e6; padding: 9px 16px; border-radius: 8px; font-size: 13px; cursor: pointer; }
.btn-ghost:hover { background: #2a2d33; border-color: #4a4d53; }

.stat-row { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.sa-dot { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 6px; vertical-align: middle; }
.sa-tags { color: #ccc; }
.lnk { background: none; border: none; color: #FF8F47; cursor: pointer; font-size: 13px; padding: 2px 6px; }
.lnk:hover { text-decoration: underline; }
.lnk.danger { color: #DD8E7C; }

/* 自定义暗色弹窗 */
.modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,0.62); display: flex; align-items: center; justify-content: center; z-index: 2000; }
.modal-card { width: 560px; max-width: 92vw; max-height: 88vh; overflow: auto; background: #15171a; border: 1px solid #26282c; border-radius: 14px; box-shadow: 0 24px 60px rgba(0,0,0,0.55); }
.modal-head { display: flex; align-items: center; gap: 10px; padding: 16px 18px; border-bottom: 1px solid #26282c; position: relative; }
.modal-head h3 { margin: 0; font-size: 16px; color: #F2F2F2; font-weight: 700; }
.mh-bar { width: 4px; height: 16px; background: #FF7B2C; border-radius: 2px; }
.modal-x { position: absolute; right: 14px; top: 12px; background: none; border: none; color: #888; font-size: 22px; cursor: pointer; line-height: 1; }
.modal-x:hover { color: #fff; }
.modal-body { padding: 18px; }
.modal-foot { display: flex; justify-content: flex-end; gap: 10px; padding: 14px 18px; border-top: 1px solid #26282c; }
.fld { margin-bottom: 13px; display: flex; flex-direction: column; }
.fld-row { display: flex; gap: 12px; }
.fld-row .fld { flex: 1; }
.fld label { font-size: 12px; color: #9aa0a6; margin-bottom: 6px; }
.fld input, .fld textarea { padding: 9px 11px; border: 1px solid #2a2a2a; border-radius: 8px; background: #1f2125; color: #e8e8e8; font-size: 13px; box-sizing: border-box; font-family: inherit; }
.fld input:focus, .fld textarea:focus { outline: none; border-color: #FF7B2C; box-shadow: 0 0 0 3px rgba(255,123,44,0.16); }
.fld textarea { resize: vertical; }
.color-row { display: flex; align-items: center; gap: 10px; }
.color-row input[type=color] { width: 44px; height: 34px; padding: 0; border: 1px solid #2a2a2a; border-radius: 8px; background: #1f2125; cursor: pointer; }
.color-hex { width: 120px; }
.coupon-box { margin-top: 4px; padding: 12px; border: 1px dashed #2a2a2a; border-radius: 10px; background: #131416; }
.cb-line { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #e0e0e0; cursor: pointer; margin-bottom: 10px; }
.cb-line input { width: 16px; height: 16px; accent-color: #FF7B2C; }
</style>
