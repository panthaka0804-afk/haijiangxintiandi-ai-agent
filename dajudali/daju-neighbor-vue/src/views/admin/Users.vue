<template>
  <div class="users-page">
    <div class="page-header">
      <h3>用户管理</h3>
      <el-button type="primary" @click="showAddDialog">+ 新增用户</el-button>
    </div>

    <el-card shadow="never">
      <div class="table-x">
      <el-table :data="list" stripe v-loading="loading" style="width: 100%;">
        <el-table-column prop="id" label="ID" width="60" class-name="m-hide" />
        <el-table-column prop="username" label="用户名" width="130" />
        <el-table-column prop="display_name" label="显示名" width="120" />
        <el-table-column prop="role" label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="row.role === 'super_admin' ? 'danger' : row.role === 'tenant_admin' ? 'warning' : 'info'">
              {{ roleLabel(row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="tenant_id" label="租户ID" width="80" class-name="m-hide" />
        <el-table-column prop="created_at" label="创建时间" width="160" class-name="m-hide" />
      </el-table>
      </div>
    </el-card>

    <!-- 新增用户弹窗 -->
    <el-dialog v-model="dialogVisible" title="新增用户" width="500px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="登录用户名" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="登录密码" />
        </el-form-item>
        <el-form-item label="显示名" prop="display_name">
          <el-input v-model="form.display_name" placeholder="显示名称" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="form.role" style="width: 100%;">
            <el-option label="普通用户" value="user" />
            <el-option label="租户管理员" value="tenant_admin" />
            <el-option label="超级管理员" value="super_admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveUser">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getUsers, createUser } from '@/api'

const loading = ref(false)
const saving = ref(false)
const list = ref([])
const dialogVisible = ref(false)
const formRef = ref(null)
const form = ref({ username: '', password: '', display_name: '', role: 'user' })

const rules = {
  username: [{ required: true, message: '请输入用户名' }],
  password: [{ required: true, message: '请输入密码' }],
  display_name: [{ required: true, message: '请输入显示名' }],
  role: [{ required: true, message: '请选择角色' }]
}

function roleLabel(role) {
  const map = { user: '普通用户', tenant_admin: '租户管理员', super_admin: '超级管理员' }
  return map[role] || role
}

async function loadData() {
  loading.value = true
  try {
    const res = await getUsers()
    if (res.ok) {
      list.value = res.users || res.items || []
    }
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

function showAddDialog() {
  form.value = { username: '', password: '', display_name: '', role: 'user' }
  dialogVisible.value = true
}

async function saveUser() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    await createUser(form.value)
    ElMessage.success('新增成功')
    dialogVisible.value = false
    loadData()
  } catch {
    ElMessage.error('操作失败')
  } finally {
    saving.value = false
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
