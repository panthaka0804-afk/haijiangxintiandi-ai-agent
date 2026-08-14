<template>
  <div class="members-page">
    <div class="page-header">
      <div class="ph-left">
        <div class="ph-title"><span class="ph-bar"></span><h3>会员管理</h3></div>
        <div class="ph-sub">共 {{ total }} 位会员 · 支持按手机号检索</div>
      </div>
      <el-input v-model="searchPhone" placeholder="搜索手机号" clearable @input="onSearch" class="ph-search" />
    </div>

    <el-card shadow="never" class="mem-card">
      <el-table :data="list" v-loading="loading" class="mem-table" style="width: 100%;">
        <el-table-column prop="id" label="ID" width="64" />
        <el-table-column label="姓名" width="150">
          <template #default="{ row }">
            <div class="cell-member">
              <span class="ava" :class="avaClass(row.membership_level)">{{ (row.display_name || '?').charAt(0) }}</span>
              <span class="m-name">{{ row.display_name || '-' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="phone" label="手机号" width="130">
          <template #default="{ row }">
            {{ row.phone || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="membership_level" label="等级" width="110">
          <template #default="{ row }">
            <span class="lv-tag" :class="lvClass(row.membership_level)">{{ row.membership_level }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="points" label="积分" width="100">
          <template #default="{ row }">
            <span class="pts">{{ row.points }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" min-width="160" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" class="op-edit" @click="editRow(row)">编辑</el-button>
            <el-popconfirm title="确定删除该会员？" @confirm="deleteRow(row.id)">
              <template #reference>
                <el-button size="small" class="op-del">删除</el-button>
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
        <el-form-item label="姓名">
          <el-input v-model="form.display_name" placeholder="会员姓名" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="form.phone" placeholder="手机号" />
        </el-form-item>
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

const LV = {
  '普卡': { tag: 'lv-pu', ava: 'ava-pu' },
  '银卡': { tag: 'lv-yin', ava: 'ava-yin' },
  '金卡': { tag: 'lv-jin', ava: 'ava-jin' },
  '钻石卡': { tag: 'lv-zuan', ava: 'ava-zuan' }
}
function lvClass(level) { return (LV[level] || LV['普卡']).tag }
function avaClass(level) { return (LV[level] || LV['普卡']).ava }

function onSearch() {
  page.value = 1
  loadData()
}

async function loadData() {
  loading.value = true
  try {
    const params = { page: page.value, limit: 20 }
    if (searchPhone.value) params.search = searchPhone.value

    const res = await getAdminMembers(params)
    if (res.ok) {
      list.value = res.members || res.items || []
      total.value = res.total || (res.members ? res.members.length : 0)
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
    display_name: row.display_name || '',
    phone: row.phone || '',
    membership_level: row.membership_level,
    points: row.points
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
.members-page {
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

.cell-member { display: flex; align-items: center; gap: 10px; }
.ava {
  width: 34px; height: 34px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-weight: 700; font-size: 14px; flex-shrink: 0;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.35), 0 2px 4px rgba(0, 0, 0, 0.4);
}
.ava-pu { background: linear-gradient(135deg, #9097a0, #6f757e); }
.ava-yin { background: linear-gradient(135deg, #c3c9d1, #9aa1ab); color: #2a2f36; }
.ava-jin { background: linear-gradient(135deg, #E8A33D, #C4923A); }
.ava-zuan { background: linear-gradient(135deg, #8E7CE8, #6C5CE0); }
.m-name { font-weight: 600; color: #e6e6e6; }

.lv-tag {
  display: inline-flex; align-items: center;
  padding: 4px 14px; border-radius: 20px;
  font-size: 12px; font-weight: 700; color: #fff;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.3);
  letter-spacing: 0.5px;
}
.lv-pu { background: linear-gradient(135deg, #9097a0, #6f757e); }
.lv-yin { background: linear-gradient(135deg, #c3c9d1, #9aa1ab); color: #2a2f36; }
.lv-jin { background: linear-gradient(135deg, #E8A33D, #C4923A); }
.lv-zuan { background: linear-gradient(135deg, #8E7CE8, #6C5CE0); }

.pts { font-weight: 700; color: #FF7B2C; }

.op-edit { border-radius: 8px; background: #FF7B2C; border-color: #FF7B2C; color: #fff; }
.op-edit:hover { background: #ff8c45; border-color: #ff8c45; }
.op-del { border-radius: 8px; }

:deep(.el-pagination) { color: #c0c0c0; }
:deep(.el-pagination .el-pager li) { background: transparent; color: #c0c0c0; }
:deep(.el-pagination .el-pager li.is-active) {
  background: #FF7B2C; border-color: #FF7B2C; color: #fff;
}
:deep(.el-pagination button) { background: transparent; color: #c0c0c0; }
:deep(.el-pagination .el-pagination__total) { color: #9aa0a8; }

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
:deep(.el-input-number) { background: #1f2125; border-radius: 8px; }
:deep(.el-input-number .el-input__wrapper) { background: transparent; box-shadow: none; }
:deep(.el-dialog .el-button:not(.el-button--primary)) {
  background: #1f2125; border-color: #3a3d43; color: #e6e6e6;
}
:deep(.el-dialog .el-button:not(.el-button--primary):hover) {
  background: #2a2d33; border-color: #4a4d53;
}
:deep(.el-button) { border-radius: 8px; }
:deep(.ph-search .el-input__wrapper) { border-radius: 20px; }
:deep(.el-button--primary) { background: #FF7B2C; border-color: #FF7B2C; }
:deep(.el-button--primary:hover) { background: #ff8c45; border-color: #ff8c45; }
</style>
