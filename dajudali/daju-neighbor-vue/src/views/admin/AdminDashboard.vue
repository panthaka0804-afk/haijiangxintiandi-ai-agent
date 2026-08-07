<template>
  <div class="admin-dashboard">
    <h3>数据看板</h3>

    <!-- 统计卡片 -->
    <div class="stat-grid">
      <div class="stat-card" v-for="card in statCards" :key="card.label" :style="{ '--card-color': card.color }">
        <div class="stat-icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" :stroke="card.color" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path v-if="card.key==='chats'" d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
            <template v-else-if="card.key==='members'"><circle cx="12" cy="8" r="4"/><path d="M4 21v-1a6 6 0 0112 0v1"/></template>
            <template v-else-if="card.key==='orders'"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></template>
            <template v-else-if="card.key==='rate'"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></template>
            <template v-else-if="card.key==='activities'"><circle cx="12" cy="12" r="10"/><polygon points="10 8 16 12 10 16 10 8"/></template>
            <template v-else-if="card.key==='regs'"><rect x="3" y="5" width="18" height="14" rx="2"/><line x1="3" y1="10" x2="21" y2="10"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="16" y1="2" x2="16" y2="6"/></template>
          </svg>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ card.value }}</span>
          <span class="stat-label">{{ card.label }}</span>
        </div>
      </div>
    </div>

    <!-- 数据区域 -->
    <div class="chart-grid">
      <div class="db-card">
        <div class="db-card-h">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#666" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-3px;margin-right:6px"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
          服务效率
        </div>
        <div class="kpi-list">
          <div class="kpi-item"><span>咨询总量</span><strong>{{ stats?.today_chats || 0 }}</strong></div>
          <div class="kpi-item"><span>AI 解决率</span><strong>{{ stats?.ai_rate || '82%' }}</strong></div>
          <div class="kpi-item"><span>工单办结率</span><strong>{{ stats?.order_done_rate || '91%' }}</strong></div>
          <div class="kpi-item"><span>待处理工单</span><strong>{{ stats?.pending_orders || 0 }}</strong></div>
          <div class="kpi-item"><span>用户满意度</span><strong>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#FF7B2C" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-2px;margin-right:2px"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
            {{ stats?.satisfaction || '4.8' }}
          </strong></div>
        </div>
      </div>

      <div class="db-card">
        <div class="db-card-h">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FF7B2C" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-3px;margin-right:6px"><path d="M17.66 18l-3.55-6.53a1 1 0 00-1.73.01L8.83 18"/><polyline points="6 11 10.59 3 15.18 11"/><line x1="2" y1="22" x2="22" y2="22"/></svg>
          热门活动 TOP5
        </div>
        <div class="hot-list" v-if="stats?.hot_activities?.length">
          <div v-for="(a, i) in stats.hot_activities" :key="a.id" class="hot-item">
            <span class="hot-rank" :style="i === 0 ? 'background:#FF7B2C;color:#fff' : ''">{{ i + 1 }}</span>
            <span class="hot-text">{{ a.title }}</span>
            <span class="hot-count">{{ a.enrolled || 0 }}人</span>
          </div>
        </div>
        <div v-else class="hot-empty">暂无活动数据</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'

const stats = ref(null)

const statCards = reactive([
  { key: 'chats', label: '今日咨询', value: '--', color: '#409EFF' },
  { key: 'members', label: '活跃会员', value: '--', color: '#67C23A' },
  { key: 'orders', label: '工单总数', value: '--', color: '#E6A23C' },
  { key: 'rate', label: '好评率', value: '--', color: '#F56C6C' },
  { key: 'activities', label: '活动总数', value: '--', color: '#FF7B2C' },
  { key: 'regs', label: '活动报名', value: '--', color: '#9C27B0' },
])

onMounted(async () => {
  try {
    const res = await fetch('/api/dashboard')
    const d = await res.json()
    if (d.ok) {
      stats.value = d
      statCards[0].value = d.today_chats || '--'
      statCards[1].value = d.active_members || '--'
      statCards[2].value = d.total_orders || '--'
      statCards[3].value = d.satisfaction || '--'
      statCards[4].value = d.activity_count || '--'
      statCards[5].value = d.reg_count || '--'
    }
  } catch {}
})
</script>

<style scoped>
.admin-dashboard { padding: 0; background: transparent; }
.admin-dashboard h3 { margin: 0 0 16px; color: #333; font-size: 18px; }

.stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 20px; }
.stat-card {
  background: #fff; border-radius: 14px; padding: 16px;
  display: flex; align-items: center; gap: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.stat-icon { width: 42px; height: 42px; border-radius: 10px; display: flex; align-items: center; justify-content: center; background: color-mix(in srgb, var(--card-color) 15%, transparent); }
.stat-info { display: flex; flex-direction: column; }
.stat-value { font-size: 22px; font-weight: 800; color: #333; line-height: 1.2; }
.stat-label { font-size: 12px; color: #999; margin-top: 2px; }

.chart-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 767px) {
  .chart-grid { grid-template-columns: 1fr; }
  .stat-grid { grid-template-columns: repeat(2, 1fr); gap: 8px; }
  .stat-card { padding: 12px; }
  .stat-value { font-size: 18px; }
  .stat-icon { width: 34px; height: 34px; }
}

.db-card { background: #fff; border-radius: 14px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.db-card-h { padding: 14px 16px; font-weight: 600; color: #333; font-size: 15px; border-bottom: 1px solid #eee; }
.hot-empty { padding: 20px; text-align: center; color: #999; font-size: 13px; }

.kpi-list { padding: 4px 0; }
.kpi-item { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-bottom: 1px solid #eee; font-size: 14px; color: #666; }
.kpi-item:last-child { border-bottom: none; }
.kpi-item strong { color: #333; font-size: 16px; }

.hot-list { padding: 4px 0; }
.hot-item { display: flex; align-items: center; gap: 10px; padding: 12px 16px; border-bottom: 1px solid #eee; font-size: 14px; }
.hot-item:last-child { border-bottom: none; }
.hot-rank { width: 22px; height: 22px; border-radius: 6px; background: #F0F0F0; color: #999; font-size: 12px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.hot-text { flex: 1; color: #333; }
.hot-count { color: #999; font-size: 12px; }
</style>
