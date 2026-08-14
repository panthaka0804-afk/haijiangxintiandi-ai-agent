<template>
  <div class="in-page">
    <div class="page-header">
      <div class="ph-left">
        <div class="ph-title"><span class="ph-bar"></span><h3>工单管理</h3></div>
        <div class="ph-sub">客服 / 报修 / 商务工单 · 共 {{ total }} 条</div>
      </div>
      <div class="ph-filters">
        <select v-model="typeFilter" class="dark-select" @change="reloadData">
          <option value="">全部类型</option>
          <option v-for="t in orderTypes" :key="t" :value="t">{{ t }}</option>
        </select>
        <select v-model="statusFilter" class="dark-select" @change="reloadData">
          <option value="">全部状态</option>
          <option value="pending">待处理</option>
          <option value="processing">处理中</option>
          <option value="done">已完成</option>
          <option value="closed">已关闭</option>
        </select>
      </div>
    </div>

    <div class="panel">
      <div class="panel-head">
        <span class="dot" style="background:#D4A59A"></span>
        <h2>工单列表</h2>
        <span v-if="loading" class="engine">加载中…</span>
        <span v-else class="engine ok">已加载</span>
      </div>
      <div class="tbl-wrap">
        <table class="mc-table">
          <thead>
            <tr>
              <th width="70">工单号</th><th width="96">类型</th><th width="80">级别</th>
              <th>标题</th><th width="90">状态</th><th width="150">创建时间</th><th width="150">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in list" :key="row.id">
              <td class="muted">{{ row.id }}</td>
              <td>{{ row.type || '-' }}</td>
              <td><span class="pill" :class="priorityClass(row.priority)">{{ priorityText(row.priority) }}</span></td>
              <td>{{ row.title }}</td>
              <td><span class="pill" :class="statusClass(row.status)">{{ statusTextMap[row.status] || row.status }}</span></td>
              <td class="muted">{{ row.created_at }}</td>
              <td>
                <button class="lnk" @click="viewDetail(row)">查看</button>
                <select v-model="row._newStatus" class="row-select" @change="changeStatus(row)">
                  <option value="">变更状态</option>
                  <option value="processing">处理中</option>
                  <option value="done">已完成</option>
                  <option value="closed">关闭</option>
                </select>
              </td>
            </tr>
            <tr v-if="!list.length"><td colspan="7" class="empty">暂无工单</td></tr>
          </tbody>
        </table>
      </div>
      <div class="pager" v-if="total > pageSize">
        <button class="pg" :disabled="page <= 1" @click="goPage(page - 1)">上一页</button>
        <span class="pg-info">第 {{ page }} 页 / 共 {{ Math.ceil(total / pageSize) }} 页</span>
        <button class="pg" :disabled="page >= Math.ceil(total / pageSize)" @click="goPage(page + 1)">下一页</button>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <div v-if="detailVisible" class="modal-mask" @click.self="detailVisible = false">
      <div class="modal-card">
        <div class="modal-head">
          <span class="mh-bar"></span>
          <h3>工单详情</h3>
          <button class="modal-x" @click="detailVisible = false">×</button>
        </div>
        <div class="modal-body" v-if="currentOrder">
          <div class="detail-grid">
            <div class="dg"><label>工单号</label><span>{{ currentOrder.id }}</span></div>
            <div class="dg"><label>类型</label><span>{{ currentOrder.type }}</span></div>
            <div class="dg"><label>级别</label><span class="pill" :class="priorityClass(currentOrder.priority)">{{ priorityText(currentOrder.priority) }}</span></div>
            <div class="dg"><label>状态</label><span class="pill" :class="statusClass(currentOrder.status)">{{ statusTextMap[currentOrder.status] || currentOrder.status }}</span></div>
            <div class="dg" style="grid-column: 1 / -1"><label>标题</label><span>{{ currentOrder.title }}</span></div>
            <div class="dg" style="grid-column: 1 / -1"><label>创建时间</label><span class="muted">{{ currentOrder.created_at }}</span></div>
            <div class="dg" style="grid-column: 1 / -1"><label>内容</label><span>{{ currentOrder.content || currentOrder.description || '-' }}</span></div>
          </div>
        </div>
        <div class="modal-foot"><button class="btn-ghost" @click="detailVisible = false">关闭</button></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getOrders, updateOrder } from '@/api'

const loading = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const statusFilter = ref('')
const typeFilter = ref('')
const detailVisible = ref(false)
const currentOrder = ref(null)

const orderTypes = ['场地看场', '商务意向', '团建定制', '入驻申请', '活动排期', '场地预定', '报修', '投诉建议', '人工客服', '升级工单', '预约', 'inquiry', 'venue_quotation', 'points_redeem']

const statusTextMap = { pending: '待处理', processing: '处理中', done: '已完成', closed: '已关闭' }
function statusClass(s) {
  return { pending: 'gold', processing: 'blue', done: 'green', closed: 'gray' }[s] || 'gray'
}
function priorityText(p) {
  return { critical: '重大', urgent: '紧急', normal: '一般', high: '紧急' }[p] || p || '一般'
}
function priorityClass(p) {
  return { critical: 'red', urgent: 'gold', high: 'orange', normal: 'gray' }[p] || 'gray'
}

function reloadData() { page.value = 1; loadData() }
function goPage(p) { page.value = p; loadData() }

async function loadData() {
  loading.value = true
  try {
    const params = { page: page.value, limit: pageSize }
    if (statusFilter.value) params.status = statusFilter.value
    if (typeFilter.value) params.type = typeFilter.value
    const res = await getOrders(params)
    if (res.ok) {
      list.value = (res.items || res.orders || []).map(o => ({ ...o, _newStatus: '' }))
      total.value = res.total || 0
    }
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

function viewDetail(row) {
  currentOrder.value = row
  detailVisible.value = true
}

async function changeStatus(row) {
  if (!row._newStatus) return
  try {
    await updateOrder(row.id, { status: row._newStatus })
    row.status = row._newStatus
    row._newStatus = ''
    ElMessage.success('状态已更新')
  } catch {
    ElMessage.error('操作失败')
  }
}

onMounted(loadData)
</script>

<style scoped>
.ph-filters { display: flex; gap: 8px; }
.dark-select {
  padding: 9px 12px; border: 1px solid #2a2a2a; border-radius: 8px; background: #1f2125; color: #e8e8e8;
  font-size: 13px; cursor: pointer; appearance: none; min-width: 130px;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6'><path d='M0 0l5 6 5-6z' fill='%23888'/></svg>");
  background-repeat: no-repeat; background-position: right 10px center; padding-right: 28px;
}
.dark-select:focus { outline: none; border-color: #FF7B2C; box-shadow: 0 0 0 3px rgba(255,123,44,0.16); }
.lnk { background: none; border: none; color: #FF8F47; cursor: pointer; font-size: 13px; padding: 2px 4px; }
.lnk:hover { text-decoration: underline; }
.row-select {
  margin-left: 6px; padding: 4px 8px; border: 1px solid #2a2a2a; border-radius: 7px; background: #1f2125; color: #e8e8e8;
  font-size: 12px; cursor: pointer; appearance: none;
}
.row-select:focus { outline: none; border-color: #FF7B2C; }

.pager { display: flex; align-items: center; justify-content: center; gap: 14px; padding: 14px 0 4px; }
.pg { background: #1f2125; border: 1px solid #3a3d43; color: #e6e6e6; padding: 6px 14px; border-radius: 8px; cursor: pointer; font-size: 13px; }
.pg:hover:not(:disabled) { background: #2a2d33; border-color: #4a4d53; }
.pg:disabled { opacity: 0.4; cursor: default; }
.pg-info { font-size: 13px; color: #9aa0a6; }

.modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,0.62); display: flex; align-items: center; justify-content: center; z-index: 2000; }
.modal-card { width: 600px; max-width: 92vw; max-height: 88vh; overflow: auto; background: #15171a; border: 1px solid #26282c; border-radius: 14px; box-shadow: 0 24px 60px rgba(0,0,0,0.55); }
.modal-head { display: flex; align-items: center; gap: 10px; padding: 16px 18px; border-bottom: 1px solid #26282c; position: relative; }
.modal-head h3 { margin: 0; font-size: 16px; color: #F2F2F2; font-weight: 700; }
.mh-bar { width: 4px; height: 16px; background: #FF7B2C; border-radius: 2px; }
.modal-x { position: absolute; right: 14px; top: 12px; background: none; border: none; color: #888; font-size: 22px; cursor: pointer; line-height: 1; }
.modal-x:hover { color: #fff; }
.modal-body { padding: 18px; }
.modal-foot { display: flex; justify-content: flex-end; padding: 14px 18px; border-top: 1px solid #26282c; }
.btn-ghost { background: #1f2125; border: 1px solid #3a3d43; color: #e6e6e6; padding: 9px 16px; border-radius: 8px; font-size: 13px; cursor: pointer; }
.btn-ghost:hover { background: #2a2d33; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px 18px; }
.dg { display: flex; flex-direction: column; gap: 5px; }
.dg label { font-size: 12px; color: #9aa0a6; }
.dg span { font-size: 13px; color: #e8e8e8; }
.dg .muted { color: #888; }
</style>
