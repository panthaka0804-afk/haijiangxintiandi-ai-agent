<template>
  <div class="platform-page admin-layout">
    <el-container style="height: 100vh;">
      <el-aside width="200px" class="sidebar">
        <div class="sidebar-header">
          <span class="logo">🦊 平台管理</span>
        </div>
        <el-menu
          default-active="1"
          background-color="#3E3E3E"
          text-color="#C9C9C9"
          active-text-color="#999999"
        >
          <el-menu-item index="1">
            <el-icon><OfficeBuilding /></el-icon>
            <span>租户管理</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <el-container>
        <el-header class="top-header">
          <span>多租户管理中心</span>
          <el-button text type="danger" @click="handleLogout">退出</el-button>
        </el-header>
        <el-main class="main-content">
          <el-card shadow="never">
            <template #header>
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span>租户列表</span>
                <el-button type="primary" size="small" @click="showAddDialog">+ 新增租户</el-button>
              </div>
            </template>
            <el-table :data="tenants" stripe v-loading="loading" style="width: 100%;">
              <el-table-column prop="id" label="ID" width="60" />
              <el-table-column prop="name" label="租户名称" min-width="180" />
              <el-table-column prop="phone" label="联系电话" width="130" />
              <el-table-column prop="address" label="地址" min-width="200" />
              <el-table-column prop="created_at" label="创建时间" width="160" />
              <el-table-column label="操作" width="120">
                <template #default="{ row }">
                  <el-button size="small" @click="editTenant(row)">编辑</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-main>
      </el-container>
    </el-container>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="dialogVisible" title="编辑租户" width="500px">
      <el-form :model="tenantForm" label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="tenantForm.name" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="tenantForm.phone" />
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="tenantForm.address" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveTenant">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { OfficeBuilding } from '@element-plus/icons-vue'
import { getTenants, updateTenant, logout } from '@/api'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
const saving = ref(false)
const tenants = ref([])
const dialogVisible = ref(false)
const editingId = ref(null)
const tenantForm = ref({ name: '', phone: '', address: '' })

async function loadTenants() {
  loading.value = true
  try {
    const res = await getTenants()
    tenants.value = Array.isArray(res) ? res : (res.tenants || [])
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

function showAddDialog() {
  editingId.value = null
  tenantForm.value = { name: '', phone: '', address: '' }
  dialogVisible.value = true
}

function editTenant(row) {
  editingId.value = row.id
  tenantForm.value = { ...row }
  dialogVisible.value = true
}

async function saveTenant() {
  saving.value = true
  try {
    if (editingId.value) {
      await updateTenant(editingId.value, tenantForm.value)
      ElMessage.success('保存成功')
    } else {
      // 新增暂通过 updateTenant（简化）
      ElMessage.info('请在数据库中创建新租户')
    }
    dialogVisible.value = false
    loadTenants()
  } catch {
    ElMessage.error('操作失败')
  } finally {
    saving.value = false
  }
}

async function handleLogout() {
  await logout()
  userStore.clearUser()
  router.push('/manage')
}

onMounted(loadTenants)
</script>

<style scoped>
.sidebar {
  background: #1A1A1A;
}

.sidebar-header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}

.sidebar-header .logo {
  color: #fff;
  font-size: 16px;
  font-weight: 700;
}

.top-header {
  background: #1A1A1A;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #e6e6e6;
  height: 60px;
}

.main-content {
  background: #1A1A1A;
}
</style>
