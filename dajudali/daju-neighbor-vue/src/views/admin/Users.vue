<template>
  <div class="users-page">
    <div class="page-header">
      <div class="ph-left">
        <div class="ph-title"><span class="ph-bar"></span><h3>用户管理</h3></div>
        <div class="ph-sub">共 {{ list.length }} 位用户</div>
      </div>
      <el-button type="primary" @click="showAddDialog">+ 新增用户</el-button>
    </div>

    <el-card shadow="never" class="mem-card">
      <el-table :data="list" v-loading="loading" class="mem-table" style="width: 100%;">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="用户名" width="130" />
        <el-table-column prop="display_name" label="显示名" width="120" />
        <el-table-column prop="role" label="角色" width="120">
          <template #default="{ row }">
            <span class="role-pill" :class="roleClass(row.role)">{{ roleLabel(row.role) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="tenant_id" label="租户ID" width="80" />
        <el-table-column prop="created_at" label="创建时间" width="160" />
      </el-table>
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
function roleClass(role) {
  if (role === 'super_admin') return 'role-sa'
  if (role === 'tenant_admin') return 'role-ta'
  return 'role-u'
}

async function loadData() {
  loading.value = true
  try {
    const res = await getUsers()
    list.value = Array.isArray(res) ? res : (res.users || res.items || [])
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
.users-page {
  padding: 22px 24px 30px;
  background: transparent;
  min-height: 100%;
  box-sizing: border-box;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 18px;
}
.ph-left { display: flex; flex-direction: column; gap: 6px; }
.ph-title { display: flex; align-items: center; gap: 10px; }
.ph-bar {
  width: 4px; height: 20px; border-radius: 3px;
  background: linear-gradient(180deg, #FF7B2C, #E85D04);
}
.page-header h3 {
  margin: 0;
  font-size: 19px;
  font-weight: 800;
  color: #F0F0F0;
  letter-spacing: 0.5px;
}
.ph-sub { font-size: 13px; color: #9aa0a8; padding-left: 14px; }

.mem-card {
  border-radius: 14px;
  border: 1px solid #26282c;
  background: #15171a;
  box-shadow: 0 6px 22px rgba(0, 0, 0, 0.35);
}
:deep(.mem-card .el-card__body) { padding: 8px 8px 16px; background: #15171a; }

.mem-table {
  --el-table-border-color: #26282c;
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: #1d1f23;
  --el-table-header-text-color: #FF7B2C;
  --el-table-text-color: #e6e6e6;
  --el-table-row-hover-bg-color: rgba(255, 123, 44, 0.10);
  font-size: 14px;
  border-radius: 10px;
  overflow: hidden;
  background: transparent;
}
:deep(.mem-table th.el-table__cell) {
  background: #1d1f23;
  color: #FF7B2C;
  font-weight: 700;
  font-size: 13px;
}
:deep(.mem-table td.el-table__cell) {
  padding: 14px 0;
  color: #e6e6e6;
  background: transparent;
}
:deep(.mem-table .el-table__row:hover > td) { background: rgba(255, 123, 44, 0.10); }
:deep(.mem-table .el-table__inner-wrapper::before),
:deep(.mem-table::before) { background-color: #26282c; }

.role-pill {
  display: inline-flex; align-items: center;
  padding: 4px 14px; border-radius: 20px;
  font-size: 12px; font-weight: 700; color: #fff;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.3);
  letter-spacing: 0.5px;
}
.role-sa { background: linear-gradient(135deg, #E8503A, #C9351F); }
.role-ta { background: linear-gradient(135deg, #FF7B2C, #E85D04); }
.role-u { background: linear-gradient(135deg, #5a8dc0, #3f6ea5); }

:deep(.el-dialog) {
  background: #15171a; border: 1px solid #26282c; border-radius: 14px;
}
:deep(.el-dialog__title) { font-weight: 800; color: #F0F0F0; }
:deep(.el-dialog__header) { border-bottom: 1px solid #26282c; margin-right: 0; padding-bottom: 16px; }
:deep(.el-form-item__label) { color: #c0c0c0; }
:deep(.el-input__wrapper) {
  background: #1f2125; box-shadow: 0 0 0 1px #2a2d33 inset; border-radius: 8px;
}
:deep(.el-input__inner) { color: #e6e6e6; }
:deep(.el-select__wrapper) { background: #1f2125; box-shadow: 0 0 0 1px #2a2d33 inset; border-radius: 8px; }
:deep(.el-dialog .el-button:not(.el-button--primary)) {
  background: #1f2125; border-color: #3a3d43; color: #e6e6e6;
}
:deep(.el-dialog .el-button:not(.el-button--primary):hover) {
  background: #2a2d33; border-color: #4a4d53;
}
:deep(.el-button) { border-radius: 8px; }
:deep(.el-button--primary) { background: #FF7B2C; border-color: #FF7B2C; }
:deep(.el-button--primary:hover) { background: #ff8c45; border-color: #ff8c45; }
</style>
