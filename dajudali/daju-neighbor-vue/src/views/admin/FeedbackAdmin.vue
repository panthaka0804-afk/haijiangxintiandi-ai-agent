<template>
  <div class="fb-page">
    <div class="page-header">
      <h3>满意度评价</h3>
    </div>

    <!-- 汇总卡片 -->
    <div class="fb-stats">
      <div class="fb-stat">
        <div class="fb-stat-num">{{ data.avg_rating || 0 }}</div>
        <div class="fb-stat-label">平均评分</div>
      </div>
      <div class="fb-stat">
        <div class="fb-stat-num">{{ data.total || 0 }}</div>
        <div class="fb-stat-label">评价总数</div>
      </div>
      <div class="fb-stat" v-for="t in data.by_type || []" :key="t.feedback_type">
        <div class="fb-stat-num">{{ t.avg_r ? t.avg_r.toFixed(1) : 0 }}</div>
        <div class="fb-stat-label">{{ typeName(t.feedback_type) }}（{{ t.cnt }}）</div>
      </div>
    </div>

    <el-card shadow="never">
      <el-table :data="data.list || []" stripe style="width: 100%;">
        <el-table-column label="评分" width="100">
          <template #default="{ row }">
            <span class="fb-stars">{{ '★'.repeat(row.rating) }}{{ '☆'.repeat(5 - row.rating) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ typeName(row.feedback_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="biz_type" label="业务" width="100" />
        <el-table-column prop="feedback_text" label="反馈内容" min-width="200" show-overflow-tooltip />
        <el-table-column prop="user_phone" label="手机号" width="130" />
        <el-table-column prop="created_at" label="时间" width="160" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

const data = reactive({ list: [], total: 0, avg_rating: 0, by_type: [] })

function typeName(t) {
  const map = { chat_ai: 'AI 应答', chat_human: '人工服务', business: '业务办理' }
  return map[t] || t
}

async function loadData() {
  try {
    const resp = await fetch('/api/admin/feedback')
    const d = await resp.json()
    if (d.ok) {
      data.list = d.data.list || []
      data.total = d.data.total || 0
      data.avg_rating = d.data.avg_rating || 0
      data.by_type = d.data.by_type || []
    }
  } catch {
    ElMessage.error('加载失败')
  }
}

onMounted(loadData)
</script>

<style scoped>
.page-header { margin-bottom: 16px; }
.page-header h3 { margin: 0; color: #303133; font-size: 18px; }

.fb-stats { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.fb-stat {
  background: #fff; border-radius: 8px; padding: 16px 20px;
  text-align: center; min-width: 100px; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.fb-stat-num { font-size: 24px; font-weight: 700; color: #C9823F; }
.fb-stat-label { font-size: 12px; color: #999; margin-top: 4px; }

.fb-stars { color: #FFB400; font-size: 14px; letter-spacing: 1px; }
</style>
