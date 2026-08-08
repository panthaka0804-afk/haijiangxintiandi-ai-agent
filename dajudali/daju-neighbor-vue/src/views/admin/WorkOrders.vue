<template>
  <div class="orders-page">
    <div class="page-header">
      <h3>工单管理</h3>
      <el-select v-model="statusFilter" placeholder="状态筛选" clearable @change="loadData" style="width: 150px;">
        <el-option label="待处理" value="pending" />
        <el-option label="处理中" value="processing" />
        <el-option label="已完成" value="done" />
        <el-option label="已关闭" value="closed" />
      </el-select>
    </div>

    <el-card shadow="never">
      <div class="table-x">
      <el-table :data="list" stripe v-loading="loading" style="width: 100%;">
        <el-table-column prop="id" label="工单号" width="80" class-name="m-hide" />
        <el-table-column prop="type" label="类型" width="100" class-name="m-hide" />
        <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160" class-name="m-hide" />
        <el-table-column label="操作" width="180">
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
      </div>

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
            <el-tag :type="statusType(currentOrder.status)">{{ currentOrder.status }}</el-tag>
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
const detailVisible = ref(false)
const currentOrder = ref(null)

function statusType(status) {
  const map = {
    pending: 'warning',
    processing: 'primary',
    done: 'success',
    closed: 'info'
  }
  return map[status] || 'info'
}

async function loadData() {
  loading.value = true
  try {
    const params = { page: page.value, limit: 20 }
    if (statusFilter.value) params.status = statusFilter.value

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
</style>
