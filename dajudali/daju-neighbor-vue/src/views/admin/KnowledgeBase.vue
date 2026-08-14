<template>
  <div class="in-page">
    <div class="page-header">
      <div class="ph-left">
        <div class="ph-title"><span class="ph-bar"></span><h3>知识库管理</h3></div>
        <div class="ph-sub">AI 问答知识条目 · 共 {{ total }} 条</div>
      </div>
      <button class="btn-primary" @click="showAddDialog">+ 新增知识</button>
    </div>

    <div class="toolbar">
      <input v-model="searchQuery" class="kw-input" placeholder="搜索关键词" @input="reloadData" />
      <select v-model="searchCategory" class="dark-select" @change="reloadData">
        <option value="">全部分类</option>
        <option v-for="(label, val) in CATEGORY" :key="val" :value="val">{{ label }}</option>
      </select>
    </div>

    <div class="panel">
      <div class="panel-head">
        <span class="dot" style="background:#6B6E64"></span>
        <h2>知识条目</h2>
        <span v-if="loading" class="engine">加载中…</span>
        <span v-else class="engine ok">已加载</span>
      </div>
      <div class="tbl-wrap">
        <table class="mc-table">
          <thead>
            <tr>
              <th width="56">ID</th><th width="100">分类</th><th>问题</th><th>回答</th><th width="150">关键词</th><th width="140">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in list" :key="row.id">
              <td class="muted">{{ row.id }}</td>
              <td><span class="pill green">{{ CATEGORY[row.category] || row.category }}</span></td>
              <td>{{ row.question }}</td>
              <td class="answer">{{ row.answer }}</td>
              <td class="muted">{{ row.keywords || '-' }}</td>
              <td>
                <button class="lnk" @click="editRow(row)">编辑</button>
                <button class="lnk danger" @click="deleteRow(row.id)">删除</button>
              </td>
            </tr>
            <tr v-if="!list.length"><td colspan="6" class="empty">暂无知识条目</td></tr>
          </tbody>
        </table>
      </div>
      <div class="pager" v-if="total > pageSize">
        <button class="pg" :disabled="page <= 1" @click="goPage(page - 1)">上一页</button>
        <span class="pg-info">第 {{ page }} 页 / 共 {{ Math.ceil(total / pageSize) }} 页</span>
        <button class="pg" :disabled="page >= Math.ceil(total / pageSize)" @click="goPage(page + 1)">下一页</button>
      </div>
    </div>

    <!-- 新增 / 编辑弹窗 -->
    <div v-if="dialogVisible" class="modal-mask" @click.self="dialogVisible = false">
      <div class="modal-card">
        <div class="modal-head">
          <span class="mh-bar"></span>
          <h3>{{ editingId ? '编辑知识' : '新增知识' }}</h3>
          <button class="modal-x" @click="dialogVisible = false">×</button>
        </div>
        <div class="modal-body">
          <div class="fld"><label>分类 *</label>
            <select v-model="form.category" class="dark-select full">
              <option v-for="(label, val) in CATEGORY" :key="val" :value="val">{{ label }}</option>
            </select>
          </div>
          <div class="fld"><label>问题 *</label><input v-model="form.question" placeholder="用户可能问的问题" /></div>
          <div class="fld"><label>回答 *</label><textarea v-model="form.answer" rows="5" placeholder="AI 回答的内容"></textarea></div>
          <div class="fld"><label>关键词</label><input v-model="form.keywords" placeholder="逗号分隔的关键词，用于检索匹配" /></div>
        </div>
        <div class="modal-foot">
          <button class="btn-ghost" @click="dialogVisible = false">取消</button>
          <button class="btn-primary" :disabled="saving" @click="saveKb">{{ saving ? '保存中…' : '保存' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getKnowledgeBase, createKnowledge, updateKnowledge, deleteKnowledge } from '@/api'

const loading = ref(false)
const saving = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const searchQuery = ref('')
const searchCategory = ref('')
const dialogVisible = ref(false)
const editingId = ref(null)

const CATEGORY = {
  service: '商场服务', store: '品牌商铺', promo: '优惠活动', event: '社群活动',
  biz: '商务合作', repair: '物业报修', navigation: '导航点位'
}

const form = ref({ category: 'service', question: '', answer: '', keywords: '' })

function reloadData() { page.value = 1; loadData() }
function goPage(p) { page.value = p; loadData() }

async function loadData() {
  loading.value = true
  try {
    const params = { page: page.value, limit: pageSize }
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
  if (!form.value.question.trim() || !form.value.answer.trim()) {
    ElMessage.warning('请填写问题和回答')
    return
  }
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
    await ElMessageBox.confirm('确定删除该知识条目？', '删除确认', { type: 'warning' })
  } catch { return }
  try {
    await deleteKnowledge(id)
    ElMessage.success('删除成功')
    loadData()
  } catch {
    ElMessage.error('删除失败')
  }
}

onMounted(loadData)
</script>

<style scoped>
.toolbar { display: flex; gap: 10px; margin-bottom: 14px; }
.kw-input {
  flex: 1; max-width: 320px; padding: 9px 12px; border: 1px solid #2a2a2a; border-radius: 8px;
  background: #1f2125; color: #e8e8e8; font-size: 13px; box-sizing: border-box;
}
.kw-input::placeholder { color: #6b6b6b; }
.kw-input:focus { outline: none; border-color: #FF7B2C; box-shadow: 0 0 0 3px rgba(255,123,44,0.16); }
.dark-select {
  padding: 9px 12px; border: 1px solid #2a2a2a; border-radius: 8px; background: #1f2125; color: #e8e8e8;
  font-size: 13px; cursor: pointer; appearance: none; min-width: 140px;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6'><path d='M0 0l5 6 5-6z' fill='%23888'/></svg>");
  background-repeat: no-repeat; background-position: right 10px center; padding-right: 28px;
}
.dark-select.full { width: 100%; }
.dark-select:focus { outline: none; border-color: #FF7B2C; box-shadow: 0 0 0 3px rgba(255,123,44,0.16); }
.btn-primary { background: linear-gradient(135deg, #FF7B2C, #E85D04); color: #fff; border: none; padding: 9px 16px; border-radius: 8px; font-size: 13px; cursor: pointer; font-weight: 600; box-shadow: 0 6px 16px rgba(232,93,4,0.30); }
.btn-primary:hover { background: linear-gradient(135deg, #FF8F47, #F26A0E); }
.btn-primary:disabled { opacity: 0.6; cursor: default; }
.btn-ghost { background: #1f2125; border: 1px solid #3a3d43; color: #e6e6e6; padding: 9px 16px; border-radius: 8px; font-size: 13px; cursor: pointer; }
.btn-ghost:hover { background: #2a2d33; }
.lnk { background: none; border: none; color: #FF8F47; cursor: pointer; font-size: 13px; padding: 2px 6px; }
.lnk:hover { text-decoration: underline; }
.lnk.danger { color: #DD8E7C; }
.answer { color: #cfcfcf; max-width: 360px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

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
.modal-foot { display: flex; justify-content: flex-end; gap: 10px; padding: 14px 18px; border-top: 1px solid #26282c; }
.fld { margin-bottom: 13px; display: flex; flex-direction: column; }
.fld label { font-size: 12px; color: #9aa0a6; margin-bottom: 6px; }
.fld input, .fld textarea { padding: 9px 11px; border: 1px solid #2a2a2a; border-radius: 8px; background: #1f2125; color: #e8e8e8; font-size: 13px; box-sizing: border-box; font-family: inherit; }
.fld input:focus, .fld textarea:focus { outline: none; border-color: #FF7B2C; box-shadow: 0 0 0 3px rgba(255,123,44,0.16); }
.fld textarea { resize: vertical; }
</style>
