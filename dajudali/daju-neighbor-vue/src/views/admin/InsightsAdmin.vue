<template>
  <div class="in-page">
    <div class="page-header">
      <h3>运营洞察</h3>
      <el-button size="small" @click="loadAll">刷新</el-button>
    </div>

    <!-- 优化建议卡片 -->
    <div class="in-insights">
      <div v-if="insights.suggestions && insights.suggestions.length" class="in-suggest-card">
        <div class="in-suggest-hdr">📈 优化建议</div>
        <div v-for="(s, i) in insights.suggestions" :key="i" class="in-suggest-item">· {{ s }}</div>
      </div>
      <div class="in-stat-grid">
        <div class="in-stat">
          <div class="in-stat-num">{{ insights.complaint_total || 0 }}</div>
          <div class="in-stat-label">投诉总数</div>
        </div>
        <div class="in-stat">
          <div class="in-stat-num">{{ insights.pending_total || 0 }}</div>
          <div class="in-stat-label">待优化问题</div>
        </div>
        <div class="in-stat">
          <div class="in-stat-num">{{ insights.low_feedback_count || 0 }}</div>
          <div class="in-stat-label">低分评价</div>
        </div>
      </div>
      <div v-if="insights.top_complaints && insights.top_complaints.length" class="in-top">
        <div class="in-top-hdr">高频投诉类别</div>
        <div class="in-top-tags">
          <span v-for="t in insights.top_complaints" :key="t.category" class="in-top-tag">{{ t.category }} × {{ t.count }}</span>
        </div>
      </div>
    </div>

    <!-- 知识库待优化列表 -->
    <el-card shadow="never">
      <template #header>
        <div class="in-card-hdr">
          <span>知识库待优化问题（{{ pendingTotal }}）</span>
          <span class="in-hint">用户未命中的问题，一键补充入库提升 AI 准确率</span>
        </div>
      </template>

      <div v-if="!pending.length" class="in-empty">暂无待优化问题</div>
      <div v-for="p in pending" :key="p.id" class="in-pending-item">
        <div class="in-p-item-top">
          <div class="in-p-question">{{ p.question }}</div>
          <el-tag size="small" type="info">{{ sourceName(p.source) }}</el-tag>
        </div>
        <div class="in-p-actions">
          <template v-if="editingId !== p.id">
            <el-button size="small" type="primary" @click="startEdit(p)">补充入库</el-button>
            <el-button size="small" @click="dismiss(p.id)">忽略</el-button>
          </template>
          <template v-else>
            <div class="in-edit">
              <el-select v-model="editCategory" size="small" style="width: 120px;">
                <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
              </el-select>
              <el-input v-model="editAnswer" size="small" placeholder="填写答案" style="flex: 1;" />
              <el-button size="small" type="success" @click="importItem(p)">确认入库</el-button>
              <el-button size="small" @click="editingId = 0">取消</el-button>
            </div>
          </template>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

const pending = ref([])
const pendingTotal = ref(0)
const insights = reactive({ suggestions: [], complaint_total: 0, pending_total: 0, low_feedback_count: 0, top_complaints: [] })
const editingId = ref(0)
const editAnswer = ref('')
const editCategory = ref('service')
const categories = ['service', '优惠', '停车', '导航', '活动', '会员', '商户', '其他']

function sourceName(s) {
  const map = { chat: 'AI未命中', complaint: '投诉反馈', feedback: '用户反馈' }
  return map[s] || s
}

async function loadAll() {
  await Promise.all([loadInsights(), loadPending()])
}

async function loadInsights() {
  try {
    const resp = await fetch('/api/admin/insights')
    const d = await resp.json()
    if (d.ok) Object.assign(insights, d.data)
  } catch {}
}

async function loadPending() {
  try {
    const resp = await fetch('/api/admin/kb-pending?status=pending')
    const d = await resp.json()
    if (d.ok) {
      pending.value = d.items || []
      pendingTotal.value = d.pending_total || 0
    }
  } catch {}
}

function startEdit(p) {
  editingId.value = p.id
  editAnswer.value = ''
  editCategory.value = 'service'
}

async function importItem(p) {
  if (!editAnswer.value.trim()) return ElMessage.warning('请填写答案')
  try {
    const resp = await fetch('/api/admin/kb-pending/' + p.id + '/import', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answer: editAnswer.value, category: editCategory.value })
    })
    const d = await resp.json()
    if (d.ok) {
      ElMessage.success('已补充入库')
      editingId.value = 0
      loadAll()
    } else {
      ElMessage.error(d.error || '入库失败')
    }
  } catch { ElMessage.error('操作失败') }
}

async function dismiss(id) {
  try {
    await fetch('/api/admin/kb-pending/' + id + '/dismiss', { method: 'POST' })
    ElMessage.success('已忽略')
    loadPending()
  } catch { ElMessage.error('操作失败') }
}

onMounted(loadAll)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h3 { margin: 0; color: #303133; font-size: 18px; }

.in-insights { margin-bottom: 16px; }
.in-suggest-card { background: #fff7e6; border: 1px solid #ffe0b3; border-radius: 8px; padding: 14px 16px; margin-bottom: 12px; }
.in-suggest-hdr { font-size: 14px; font-weight: 600; color: #d48806; margin-bottom: 6px; }
.in-suggest-item { font-size: 13px; color: #8a5a00; line-height: 1.8; }
.in-stat-grid { display: flex; gap: 12px; margin-bottom: 12px; }
.in-stat { flex: 1; background: #fff; border-radius: 8px; padding: 14px; text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
.in-stat-num { font-size: 22px; font-weight: 700; color: #C9823F; }
.in-stat-label { font-size: 12px; color: #999; margin-top: 4px; }
.in-top { background: #fff; border-radius: 8px; padding: 14px 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
.in-top-hdr { font-size: 13px; color: #666; margin-bottom: 8px; }
.in-top-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.in-top-tag { padding: 4px 12px; background: #f5f5f5; border-radius: 14px; font-size: 12px; color: #555; }

.in-card-hdr { display: flex; justify-content: space-between; align-items: center; }
.in-hint { font-size: 12px; color: #999; }
.in-empty { text-align: center; color: #999; padding: 30px 0; font-size: 14px; }
.in-pending-item { padding: 12px 0; border-bottom: 1px solid #f0f0f0; }
.in-pending-item:last-child { border-bottom: none; }
.in-p-item-top { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
.in-p-question { font-size: 14px; color: #333; flex: 1; }
.in-p-actions { margin-top: 8px; }
.in-edit { display: flex; gap: 8px; align-items: center; }
</style>
