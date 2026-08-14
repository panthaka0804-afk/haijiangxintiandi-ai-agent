<template>
  <div class="users-page">
    <div class="page-header">
      <div class="ph-left">
        <div class="ph-title"><span class="ph-bar"></span><h3>用户管理</h3></div>
        <div class="ph-sub">后台员工子账号 · 共 {{ list.length }} 个</div>
      </div>
      <div class="ph-actions">
        <el-input v-model="kw" placeholder="搜索用户名/显示名/手机号" clearable class="kw-input" @input="filterList" />
        <el-button type="primary" @click="showAddDialog">+ 新增账号</el-button>
      </div>
    </div>

    <el-card shadow="never" class="mem-card">
      <el-table :data="pagedList" v-loading="loading" class="mem-table" style="width: 100%;">
        <el-table-column prop="id" label="ID" width="56" />
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="display_name" label="显示名" width="110" />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column prop="role" label="角色" width="110">
          <template #default="{ row }">
            <span class="role-pill" :class="roleClass(row.role)">{{ roleLabel(row.role) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="84">
          <template #default="{ row }">
            <span class="st-pill" :class="row.status === 'disabled' ? 'st-off' : 'st-on'">
              {{ row.status === 'disabled' ? '已停用' : '启用' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="last_login" label="最后登录" width="150">
          <template #default="{ row }">{{ fmtTime(row.last_login) }}</template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="120">
          <template #default="{ row }"><span class="remark">{{ row.remark || '—' }}</span></template>
        </el-table-column>
        <el-table-column label="操作" width="210" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="showEditDialog(row)">编辑</el-button>
            <el-button size="small" @click="showResetDialog(row)">重置密码</el-button>
            <el-button size="small" type="danger" plain @click="removeUser(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pager" v-if="filtered.length > pageSize">
        <el-pagination layout="prev, pager, next" :total="filtered.length" :page-size="pageSize"
          v-model:current-page="page" />
      </div>
    </el-card>

    <!-- 新增 / 编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑账号' : '新增账号'" width="520px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="84px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :disabled="isEdit" placeholder="登录用户名" />
        </el-form-item>
        <el-form-item label="显示名" prop="display_name">
          <el-input v-model="form.display_name" placeholder="显示名称" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="form.phone" placeholder="可选" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="form.role" style="width: 100%;" @change="onRoleChange">
            <el-option label="超级管理员" value="super_admin" />
            <el-option label="管理员" value="admin" />
            <el-option label="运营" value="operator" />
            <el-option label="客服" value="cs" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.statusOn" active-text="启用" inactive-text="停用" />
        </el-form-item>
        <el-form-item :label="isEdit ? '重置密码' : '密码'" :prop="isEdit ? '' : 'password'">
          <el-input v-model="form.password" type="password" :placeholder="isEdit ? '留空则不修改' : '登录密码'" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="可选备注" />
        </el-form-item>
        <div class="perm-preview" v-if="permPreview.length">
          <div class="pp-title">该角色权限</div>
          <div class="pp-tags">
            <span class="pp-tag" v-for="p in permPreview" :key="p">{{ p }}</span>
          </div>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveUser">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getUsers, createUser, updateUser, deleteUser } from '@/api'

const loading = ref(false)
const saving = ref(false)
const list = ref([])
const kw = ref('')
const page = ref(1)
const pageSize = 10

const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)
const form = reactive({ id: null, username: '', display_name: '', phone: '', role: 'operator', statusOn: true, password: '', remark: '' })

const rules = {
  username: [{ required: true, message: '请输入用户名' }],
  display_name: [{ required: true, message: '请输入显示名' }],
  role: [{ required: true, message: '请选择角色' }],
  password: [{ required: true, message: '请输入密码' }]
}

const ROLE_MAP = {
  super_admin: { label: '超级管理员', cls: 'role-sa' },
  admin: { label: '管理员', cls: 'role-ad' },
  tenant_admin: { label: '租户管理员', cls: 'role-ta' },
  operator: { label: '运营', cls: 'role-op' },
  cs: { label: '客服', cls: 'role-cs' },
  user: { label: '普通用户', cls: 'role-u' }
}
function roleLabel(role) { return (ROLE_MAP[role] || { label: role }).label }
function roleClass(role) { return (ROLE_MAP[role] || { cls: 'role-u' }).cls }

// 角色 → 可读权限（用于弹窗预览）
const ROLE_PERM_PREVIEW = {
  super_admin: ['全部功能', '系统设置', '租户管理', '演示数据/调试', '账号管理'],
  admin: ['经营看板', '会员运营/召回', '营销管理', '知识库', '工单', '触达', '运营洞察', 'AI顾问', '账号管理'],
  tenant_admin: ['经营看板', '会员运营/召回', '营销管理', '知识库', '工单', '触达', '运营洞察', 'AI顾问', '账号管理'],
  operator: ['经营看板', '会员运营/召回', '营销管理', '知识库', '工单', '触达', '运营洞察', 'AI顾问'],
  cs: ['客服工作台', '经营看板(只读)', '会员查询', '召回推送', '满意度查看', '触达记录(只读)', '知识库查看']
}
const permPreview = computed(() => ROLE_PERM_PREVIEW[form.role] || [])
function onRoleChange() {}

const filtered = computed(() => {
  const k = kw.value.trim().toLowerCase()
  if (!k) return list.value
  return list.value.filter(u => (u.username || '').toLowerCase().includes(k) || (u.display_name || '').toLowerCase().includes(k) || (u.phone || '').includes(k))
})
const pagedList = computed(() => {
  const start = (page.value - 1) * pageSize
  return filtered.value.slice(start, start + pageSize)
})
function filterList() { page.value = 1 }

function fmtTime(t) {
  if (!t) return '—'
  return String(t).replace('T', ' ').slice(0, 16)
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

function resetForm() {
  Object.assign(form, { id: null, username: '', display_name: '', phone: '', role: 'operator', statusOn: true, password: '', remark: '' })
}
function showAddDialog() {
  resetForm()
  isEdit.value = false
  dialogVisible.value = true
}
function showEditDialog(row) {
  Object.assign(form, {
    id: row.id, username: row.username, display_name: row.display_name,
    phone: row.phone || '', role: row.role, statusOn: row.status !== 'disabled',
    password: '', remark: row.remark || ''
  })
  isEdit.value = true
  dialogVisible.value = true
}
function showResetDialog(row) {
  showEditDialog(row)
  ElMessage.info('在弹窗中填写新密码后保存即可重置')
}

async function saveUser() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const payload = {
      username: form.username, display_name: form.display_name, phone: form.phone,
      role: form.role, status: form.statusOn ? 'active' : 'disabled', remark: form.remark
    }
    if (form.password) payload.password = form.password
    if (isEdit.value) {
      await updateUser(form.id, payload)
      ElMessage.success('已保存')
    } else {
      await createUser(payload)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    loadData()
  } catch (e) {
    ElMessage.error((e && e.message) || '操作失败')
  } finally {
    saving.value = false
  }
}

async function removeUser(row) {
  try {
    await ElMessageBox.confirm(`确认删除账号「${row.display_name || row.username}」？此操作不可恢复。`, '删除确认', { type: 'warning' })
  } catch { return }
  try {
    await deleteUser(row.id)
    ElMessage.success('已删除')
    loadData()
  } catch (e) {
    ElMessage.error((e && e.message) || '删除失败')
  }
}

onMounted(loadData)
</script>

<style scoped>
.users-page { padding: 22px 24px 30px; background: transparent; min-height: 100%; box-sizing: border-box; }
.page-header { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 18px; gap: 12px; flex-wrap: wrap; }
.ph-left { display: flex; flex-direction: column; gap: 6px; }
.ph-title { display: flex; align-items: center; gap: 10px; }
.ph-bar { width: 4px; height: 20px; border-radius: 3px; background: linear-gradient(180deg, #FF7B2C, #E85D04); }
.page-header h3 { margin: 0; font-size: 19px; font-weight: 800; color: #F0F0F0; letter-spacing: 0.5px; }
.ph-sub { font-size: 13px; color: #9aa0a8; padding-left: 14px; }
.ph-actions { display: flex; align-items: center; gap: 10px; }
.kw-input { width: 230px; }
:deep(.kw-input .el-input__wrapper) { background: #1f2125; box-shadow: 0 0 0 1px #2a2d33 inset; border-radius: 8px; }
:deep(.kw-input .el-input__inner) { color: #e6e6e6; }

.mem-card { border-radius: 14px; border: 1px solid #26282c; background: #15171a; box-shadow: 0 6px 22px rgba(0, 0, 0, 0.35); }
:deep(.mem-card .el-card__body) { padding: 8px 8px 16px; background: #15171a; }

.mem-table {
  --el-table-border-color: #26282c; --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent; --el-table-header-bg-color: #1d1f23;
  --el-table-header-text-color: #FF7B2C; --el-table-text-color: #e6e6e6;
  --el-table-row-hover-bg-color: rgba(255, 123, 44, 0.10);
  font-size: 14px; border-radius: 10px; overflow: hidden; background: transparent;
}
:deep(.mem-table th.el-table__cell) { background: #1d1f23; color: #FF7B2C; font-weight: 700; font-size: 13px; }
:deep(.mem-table td.el-table__cell) { padding: 12px 0; color: #e6e6e6; background: transparent; }
:deep(.mem-table .el-table__row:hover > td) { background: rgba(255, 123, 44, 0.10); }
:deep(.mem-table .el-table__inner-wrapper::before), :deep(.mem-table::before) { background-color: #26282c; }
.remark { color: #9aa0a8; }

.role-pill { display: inline-flex; align-items: center; padding: 4px 13px; border-radius: 20px; font-size: 12px; font-weight: 700; color: #fff; box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.3); letter-spacing: 0.5px; }
.role-sa { background: linear-gradient(135deg, #E8503A, #C9351F); }
.role-ad { background: linear-gradient(135deg, #FF7B2C, #E85D04); }
.role-ta { background: linear-gradient(135deg, #D98A2B, #B86E12); }
.role-op { background: linear-gradient(135deg, #4f8fd6, #2f6cb0); }
.role-cs { background: linear-gradient(135deg, #2FB6A8, #1E8C82); }
.role-u { background: linear-gradient(135deg, #5a8dc0, #3f6ea5); }

.st-pill { display: inline-flex; align-items: center; padding: 3px 12px; border-radius: 18px; font-size: 12px; font-weight: 700; }
.st-on { background: rgba(62, 142, 65, 0.18); color: #5fd06a; }
.st-off { background: rgba(232, 80, 58, 0.16); color: #E8806A; }

.pager { display: flex; justify-content: flex-end; padding: 14px 6px 4px; }
:deep(.el-pagination) { color: #c0c0c0; }
:deep(.el-pagination button), :deep(.el-pager li) { background: #1f2125; color: #c0c0c0; }

.perm-preview { margin: 4px 0 2px; padding: 12px 14px; border-radius: 10px; background: #1c1e22; border: 1px solid #2a2d33; }
.pp-title { font-size: 12px; color: #9aa0a8; margin-bottom: 8px; }
.pp-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.pp-tag { font-size: 12px; padding: 3px 10px; border-radius: 6px; background: rgba(255, 123, 44, 0.14); color: #FF9A52; }

:deep(.el-dialog) { background: #15171a; border: 1px solid #26282c; border-radius: 14px; }
:deep(.el-dialog__title) { font-weight: 800; color: #F0F0F0; }
:deep(.el-dialog__header) { border-bottom: 1px solid #26282c; margin-right: 0; padding-bottom: 16px; }
:deep(.el-form-item__label) { color: #c0c0c0; }
:deep(.el-input__wrapper) { background: #1f2125; box-shadow: 0 0 0 1px #2a2d33 inset; border-radius: 8px; }
:deep(.el-input__inner) { color: #e6e6e6; }
:deep(.el-textarea__inner) { background: #1f2125; box-shadow: 0 0 0 1px #2a2d33 inset; border-radius: 8px; color: #e6e6e6; }
:deep(.el-select__wrapper) { background: #1f2125; box-shadow: 0 0 0 1px #2a2d33 inset; border-radius: 8px; }
:deep(.el-dialog .el-button:not(.el-button--primary)) { background: #1f2125; border-color: #3a3d43; color: #e6e6e6; }
:deep(.el-dialog .el-button:not(.el-button--primary):hover) { background: #2a2d33; border-color: #4a4d53; }
:deep(.el-button) { border-radius: 8px; }
:deep(.el-button--primary) { background: #FF7B2C; border-color: #FF7B2C; }
:deep(.el-button--primary:hover) { background: #ff8c45; border-color: #ff8c45; }
:deep(.el-button--danger) { background: transparent; border-color: #E8503A; color: #E8806A; }
</style>
