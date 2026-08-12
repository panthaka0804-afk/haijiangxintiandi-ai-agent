<template>
  <div class="orders-page">
    <div class="page-header">
      <h3>工单管理</h3>
      <div class="header-filters">
        <el-select v-model="typeFilter" placeholder="类型筛选" clearable @change="reloadData" style="width: 150px;">
          <el-option v-for="t in orderTypes" :key="t" :label="t" :value="t" />
        </el-select>
        <el-select v-model="statusFilter" placeholder="状态筛选" clearable @change="reloadData" style="width: 150px;">
          <el-option label="待处理" value="pending" />
          <el-option label="处理中" value="processing" />
          <el-option label="已完成" value="done" />
          <el-option label="已关闭" value="closed" />
        </el-select>
      </div>
    </div>

    <el-card shadow="never">
      <el-table :data="list" stripe v-loading="loading" style="width: 100%;">
        <el-table-column prop="id" label="工单号" width="80" />
        <el-table-column prop="type" label="类型" width="100" />
        <el-table-column label="级别" width="90">
          <template #default="{ row }">
            <el-tag :type="priorityType(row.priority)" size="small">{{ priorityText(row.priority) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">{{ statusTextMap[row.status] || row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="viewDetail(row)">查看</el-button>
            <el-select
              v-model="row._newStatus"
              size="small"
              placeholder="变更状态"
              @change="changeStatus(row)"
              style="width: 100px;"
            >
              <el-option label="处理中" value="processing" />
              <el-option label="已完成" value="done" />
              <el-option label="关闭" value="closed" />
            </el-select>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        :page-size="20"
        :total="total"
        layout="total, prev, pager, next"
        style="margin-top: 16px; justify-content: center;"
        @current-change="loadData"
      />
    </el-card>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="工单详情" width="600px">
      <template v-if="currentOrder">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="工单号">{{ currentOrder.id }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ currentOrder.type }}</el-descriptions-item>
          <el-descriptions-item label="标题">{{ currentOrder.title }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusType(currentOrder.status)">{{ statusTextMap[currentOrder.status] || currentOrder.status }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间" :span="2">{{ currentOrder.created_at }}</el-descriptions-item>
          <el-descriptions-item label="内容" :span="2">{{ currentOrder.content || currentOrder.description }}</el-descriptions-item>
        </el-descriptions>
      </template>
    </el-dialog>
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
const statusFilter = ref('')
const typeFilter = ref('')
const detailVisible = ref(false)
const currentOrder = ref(null)

const orderTypes = ['场地看场', '商务意向', '团建定制', '入驻申请', '活动排期', '场地预定', '报修', '投诉建议', '人工客服', '升级工单', '预约', 'inquiry', 'venue_quotation', 'points_redeem']

function statusType(status) {
  const map = {
    pending: 'warning',
    processing: 'primary',
    done: 'success',
    closed: 'info'
  }
  return map[status] || 'info'
}

const statusTextMap = { pending: '待处理', processing: '处理中', done: '已完成', closed: '已关闭' }

function priorityType(p) {
  const map = { critical: 'danger', urgent: 'warning', normal: 'info', high: 'warning' }
  return map[p] || 'info'
}
function priorityText(p) {
  const map = { critical: '重大', urgent: '紧急', normal: '一般', high: '紧急' }
  return map[p] || p || '一般'
}

function reloadData() {
  page.value = 1
  loadData()
}

async function loadData() {
  loading.value = true
  try {
    const params = { page: page.value, limit: 20 }
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
    const statusMap = {
      processing: '处理中',
      done: '已完成',
      closed: '已关闭'
    }
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
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-header h3 {
  margin: 0;
  color: #303133;
  font-size: 18px;
}

.header-filters {
  display: flex;
  gap: 8px;
}
</style>
