<template>
  <div class="kb-page">
    <div class="page-header">
      <h3>知识库管理</h3>
      <el-button type="primary" @click="showAddDialog">+ 新增知识</el-button>
    </div>

    <!-- 搜索 -->
    <el-card shadow="never" style="margin-bottom: 16px;">
      <el-row :gutter="16">
        <el-col :span="6">
          <el-input v-model="searchQuery" placeholder="搜索关键词" clearable @input="loadData" />
        </el-col>
        <el-col :span="6">
          <el-select v-model="searchCategory" placeholder="分类筛选" clearable @change="loadData">
            <el-option label="商场服务" value="service" />
            <el-option label="品牌商铺" value="store" />
            <el-option label="优惠活动" value="promo" />
            <el-option label="社群活动" value="event" />
            <el-option label="商务合作" value="biz" />
            <el-option label="物业报修" value="repair" />
          </el-select>
        </el-col>
      </el-row>
    </el-card>

    <!-- 表格 -->
    <el-card shadow="never">
      <el-table :data="list" stripe v-loading="loading" style="width: 100%;">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="category" label="分类" width="100" />
        <el-table-column prop="question" label="问题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="answer" label="回答" min-width="300" show-overflow-tooltip />
        <el-table-column prop="keywords" label="关键词" width="150" show-overflow-tooltip />
        <el-table-column label="操作" width="160" fixed="right">
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

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑知识' : '新增知识'"
      width="600px"
      @close="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="分类" prop="category">
          <el-select v-model="form.category" placeholder="选择分类" style="width: 100%;">
            <el-option label="商场服务" value="service" />
            <el-option label="品牌商铺" value="store" />
            <el-option label="优惠活动" value="promo" />
            <el-option label="社群活动" value="event" />
            <el-option label="商务合作" value="biz" />
            <el-option label="物业报修" value="repair" />
            <el-option label="导航点位" value="navigation" />
          </el-select>
        </el-form-item>
        <el-form-item label="问题" prop="question">
          <el-input v-model="form.question" placeholder="用户可能问的问题" />
        </el-form-item>
        <el-form-item label="回答" prop="answer">
          <el-input v-model="form.answer" type="textarea" :rows="5" placeholder="AI回答的内容" />
        </el-form-item>
        <el-form-item label="关键词" prop="keywords">
          <el-input v-model="form.keywords" placeholder="逗号分隔的关键词，用于检索匹配" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveKb">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getKnowledgeBase, createKnowledge, updateKnowledge, deleteKnowledge } from '@/api'

const loading = ref(false)
const saving = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const searchQuery = ref('')
const searchCategory = ref('')
const dialogVisible = ref(false)
const editingId = ref(null)

const formRef = ref(null)
const form = ref({
  category: 'service',
  question: '',
  answer: '',
  keywords: ''
})

const rules = {
  category: [{ required: true, message: '请选择分类' }],
  question: [{ required: true, message: '请输入问题' }],
  answer: [{ required: true, message: '请输入回答' }]
}

async function loadData() {
  loading.value = true
  try {
    const params = { page: page.value, limit: 20 }
    if (searchQuery.value) params.search = searchQuery.value
    if (searchCategory.value) params.category = searchCategory.value

    const res = await getKnowledgeBase(params)
    if (res.ok) {
      list.value = res.items || []
      total.value = res.total || 0
    }
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

function showAddDialog() {
  editingId.value = null
  form.value = { category: 'service', question: '', answer: '', keywords: '' }
  dialogVisible.value = true
}

function editRow(row) {
  editingId.value = row.id
  form.value = { ...row }
  dialogVisible.value = true
}

async function saveKb() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    if (editingId.value) {
      await updateKnowledge(editingId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await createKnowledge(form.value)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    loadData()
  } catch {
    ElMessage.error('操作失败')
  } finally {
    saving.value = false
  }
}

async function deleteRow(id) {
  try {
    await deleteKnowledge(id)
    ElMessage.success('删除成功')
    loadData()
  } catch {
    ElMessage.error('删除失败')
  }
}

function resetForm() {
  formRef.value?.resetFields()
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
