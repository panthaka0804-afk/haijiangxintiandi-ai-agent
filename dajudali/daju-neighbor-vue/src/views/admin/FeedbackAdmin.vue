<template>
  <div class="in-page">
    <div class="page-header">
      <h3>满意度评价</h3>
      <button class="ref-btn" @click="loadData">刷新</button>
    </div>
    <div class="hint-bar">数据来源：会员对 AI 应答 / 人工服务 / 业务办理的满意度评价，实时聚合</div>

    <!-- 汇总卡片 -->
    <div class="stat-row">
      <div class="mc-card mc-card-gold stat">
        <div class="stat-num">{{ data.avg_rating || 0 }}</div>
        <div class="stat-label">平均评分</div>
      </div>
      <div class="mc-card mc-card-orange stat">
        <div class="stat-num">{{ data.total || 0 }}</div>
        <div class="stat-label">评价总数</div>
      </div>
      <div class="mc-card mc-card-red stat" v-for="t in (data.by_type || [])" :key="t.feedback_type">
        <div class="stat-num">{{ t.avg_r ? t.avg_r.toFixed(1) : 0 }}</div>
        <div class="stat-label">{{ typeName(t.feedback_type) }}（{{ t.cnt }}）</div>
      </div>
    </div>

    <section class="mc-card mc-card-blue panel">
      <div class="panel-head">
        <h2><span class="dot" style="background:#4A90D9"></span>评价明细</h2>
        <span class="engine" v-if="(data.list||[]).length">共 {{ data.list.length }} 条</span>
        <span class="engine" v-else>暂无</span>
      </div>
      <div class="tbl-wrap">
        <table class="mc-table">
          <thead>
            <tr><th>评分</th><th>类型</th><th>业务</th><th>反馈内容</th><th>手机号</th><th>时间</th></tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in (data.list || [])" :key="i">
              <td><span class="stars">{{ '★'.repeat(row.rating) }}{{ '☆'.repeat(5 - row.rating) }}</span></td>
              <td><span class="pill" :class="typeClass(row.feedback_type)">{{ typeName(row.feedback_type) }}</span></td>
              <td class="muted">{{ row.biz_type || '-' }}</td>
              <td class="fb-text">{{ row.feedback_text || '-' }}</td>
              <td class="muted">{{ row.user_phone || '-' }}</td>
              <td class="muted">{{ row.created_at || '-' }}</td>
            </tr>
            <tr v-if="!(data.list && data.list.length)"><td colspan="6" class="empty">暂无评价数据</td></tr>
          </tbody>
        </table>
      </div>
    </section>
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
function typeClass(t) {
  return { chat_ai: 'blue', chat_human: 'orange', business: 'green' }[t] || 'gray'
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
.stat-row { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.ref-btn { padding: 7px 18px; background: #202020; color: #E3BB6A; border: 1px solid #3a3a3a; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 600; transition: .15s; }
.ref-btn:hover { border-color: #E3BB6A; }
.stars { color: #FFB400; font-size: 14px; letter-spacing: 1px; }
.fb-text { max-width: 340px; color: #cfcfcf; }
</style>
