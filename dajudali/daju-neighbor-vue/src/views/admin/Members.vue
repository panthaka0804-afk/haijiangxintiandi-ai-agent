<template>
  <div class="members-page">
    <div class="page-header">
      <h3>会员管理</h3>
      <el-input v-model="searchPhone" placeholder="搜索手机号" clearable @input="loadData" style="width: 200px;" />
    </div>

    <el-card shadow="never">
      <el-table :data="list" stripe v-loading="loading" style="width: 100%;">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="display_name" label="姓名" width="120" />
        <el-table-column prop="username" label="手机号" width="130">
          <template #default="{ row }">
            {{ row.username?.replace('m', '') || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="membership_level" label="等级" width="100">
          <template #default="{ row }">
            <el-tag :type="levelColor(row.membership_level)">{{ row.membership_level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="points" label="积分" width="100" />
        <el-table-column prop="created_at" label="注册时间" width="160" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="editRow(row)">编辑</el-button>
            <el-popconfirm title="确定删除？" @confirm="deleteRow(row.id)">
              <template #reference>
                <el-button size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
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

    <!-- 编辑弹窗 -->
    <el-dialog v-model="dialogVisible" title="编辑会员" width="500px">
      <el-form ref="formRef" :model="form" label-width="80px">
        <el-form-item label="等级">
          <el-select v-model="form.membership_level" style="width: 100%;">
            <el-option label="普卡" value="普卡" />
            <el-option label="银卡" value="银卡" />
            <el-option label="金卡" value="金卡" />
            <el-option label="钻石卡" value="钻石卡" />
          </el-select>
        </el-form-item>
        <el-form-item label="积分">
          <el-input-number v-model="form.points" :min="0" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveMember">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getAdminMembers, updateAdminMember, deleteAdminMember } from '@/api'

const loading = ref(false)
const saving = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const searchPhone = ref('')
const dialogVisible = ref(false)
const editingId = ref(null)
const formRef = ref(null)
const form = ref({ membership_level: '普卡', points: 0, remark: '' })

function levelColor(level) {
  const map = { '普卡': 'info', '银卡': '', '金卡': 'warning', '钻石卡': 'success' }
  return map[level] || 'info'
}

async function loadData() {
  loading.value = true
  try {
    const params = { page: page.value, limit: 20 }
    if (searchPhone.value) params.phone = searchPhone.value

    const res = await getAdminMembers(params)
    if (res.ok) {
      list.value = res.members || res.items || []
      total.value = res.total || 0
    }
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

function editRow(row) {
  editingId.value = row.id
  form.value = {
    membership_level: row.membership_level,
    points: row.points,
    remark: row.remark || ''
  }
  dialogVisible.value = true
}

async function saveMember() {
  saving.value = true
  try {
    await updateAdminMember(editingId.value, form.value)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    loadData()
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function deleteRow(id) {
  try {
    await deleteAdminMember(id)
    ElMessage.success('删除成功')
    loadData()
  } catch {
    ElMessage.error('删除失败')
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
