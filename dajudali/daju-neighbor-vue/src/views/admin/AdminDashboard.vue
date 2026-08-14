<template>
  <div class="admin-dashboard">
    <h3>数据看板</h3>

    <!-- 工具栏：导出常显；演示数据维护收进折叠面板，降低误触风险 -->
    <div class="db-toolbar">
      <button class="tb-btn tb-ghost" @click="exportBoard">导出看板 CSV</button>
      <button class="tb-btn tb-ghost" @click="printBoard">打印日报 PDF</button>
      <span class="tb-demo" v-if="stats?.demo_active">● 当前为演示数据</span>
      <details class="db-debug">
        <summary class="db-debug-sum">调试工具（演示数据）</summary>
        <div class="db-debug-body">
          <p class="db-debug-warn">⚠ 仅用于演示环境。种入/清空仅影响 demo 标记数据，真实数据不受影响，但请谨慎操作。</p>
          <div class="db-debug-btns">
            <button class="tb-btn" :disabled="seeding" @click="runSeed">{{ seeding ? '种入中…' : '种入演示数据' }}</button>
            <button class="tb-btn tb-ghost" :disabled="clearing" @click="runClear">{{ clearing ? '清空中…' : '清空演示数据' }}</button>
          </div>
        </div>
      </details>
    </div>

    <!-- 周报一句话（亮点 / 最大风险） -->
    <div class="weekly-headline" v-if="weeklyHeadline">
      <span class="wh-ico">📌</span><span>{{ weeklyHeadline }}</span>
    </div>

    <!-- KPI 数字卡 -->
    <div class="stat-grid">
      <div class="stat-card" v-for="card in statCards" :key="card.key" :style="{ '--card-color': card.color }">
        <div class="stat-icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" :stroke="card.color" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path v-if="card.key==='chats'" d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
            <template v-else-if="card.key==='members'"><circle cx="12" cy="8" r="4"/><path d="M4 21v-1a6 6 0 0112 0v1"/></template>
            <template v-else-if="card.key==='orders'"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></template>
            <template v-else-if="card.key==='gmv'"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></template>
            <template v-else-if="card.key==='redeem'"><path d="M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></template>
            <template v-else-if="card.key==='newmem'"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></template>
            <template v-else-if="card.key==='points'"><circle cx="12" cy="12" r="10"/><path d="M12 6v12M8 10h4a2 2 0 010 4H8"/></template>
            <template v-else-if="card.key==='shops'"><path d="M3 9l1-5h16l1 5"/><path d="M4 9v11a1 1 0 001 1h14a1 1 0 001-1V9"/><path d="M9 21V12h6v9"/></template>
          </svg>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ card.value }}</span>
          <span class="stat-label">{{ card.label }}</span>
          <div class="stat-delta" v-if="deltaOf(card.key).dod !== null || deltaOf(card.key).wow !== null">
            <span class="d-chip" :class="deltaCls(card.key, 'dod')" v-if="deltaOf(card.key).dod !== null">
              日 {{ deltaArrow(deltaOf(card.key).dod) }}{{ Math.abs(deltaOf(card.key).dod) }}%
            </span>
            <span class="d-chip" :class="deltaCls(card.key, 'wow')" v-if="deltaOf(card.key).wow !== null">
              周 {{ deltaArrow(deltaOf(card.key).wow) }}{{ Math.abs(deltaOf(card.key).wow) }}%
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 数据区域 -->
    <div class="chart-grid">

      <!-- 核心指标 7 日趋势 -->
      <div class="db-card">
        <div class="db-card-h">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#4A90D9" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-3px;margin-right:6px"><polyline points="3 17 9 11 13 15 21 7"/><polyline points="14 7 21 7 21 14"/></svg>
          核心指标 · 近 7 日趋势
        </div>
        <div class="spark-list">
          <div class="spark-item" v-for="s in sparkMetrics" :key="s.key">
            <div class="spark-meta">
              <span class="spark-label">{{ s.label }}</span>
              <span class="spark-val" :style="{ color: s.color }">{{ s.last }}<small v-if="s.suffix">{{ s.suffix }}</small></span>
            </div>
            <svg class="spark-svg" viewBox="0 0 120 36" preserveAspectRatio="none">
              <polyline :points="s.points" fill="none" :stroke="s.color" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>
            </svg>
          </div>
        </div>
      </div>

      <!-- 服务效率 -->
      <div class="db-card">
        <div class="db-card-h">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#999999" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-3px;margin-right:6px"><path d="M17.66 18l-3.55-6.53a1 1 0 00-1.73.01L8.83 18"/><polyline points="6 11 10.59 3 15.18 11"/><line x1="2" y1="22" x2="22" y2="22"/></svg>
          服务效率
        </div>
        <div class="kpi-list">
          <div class="kpi-item"><span>AI 自助解决率<em class="kpi-unit">近7日</em></span><strong>{{ fmtPct(stats?.ai_rate) }}</strong></div>
          <div class="kpi-item"><span>工单办结率<em class="kpi-unit">累计</em></span><strong>{{ fmtPct(stats?.order_done_rate) }}</strong></div>
          <div class="kpi-item"><span>用户满意度</span><strong>{{ stats?.satisfaction ?? '—' }}</strong></div>
          <div class="kpi-item"><span>待处理工单</span><strong :class="{ danger: (stats?.pending_orders||0) > 0 }">{{ stats?.pending_orders || 0 }}</strong></div>
          <div class="kpi-item"><span>知识库待优化</span><strong :class="{ danger: (stats?.pending_kb||0) > 0 }">{{ stats?.pending_kb || 0 }}</strong></div>
        </div>
        <p class="hint">口径说明：AI 自助解决率按近 7 日窗口统计（转人工外的对话占比）；工单办结率为累计口径=（全部工单−待处理）/全部工单。两者统计周期不同，不宜直接对比。</p>
      </div>

      <!-- 营销转化漏斗 -->
      <div class="db-card">
        <div class="db-card-h">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#C4923A" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-3px;margin-right:6px"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>
          营销转化漏斗（券）
        </div>
        <div class="funnel" v-if="stats?.funnel">
          <div class="funnel-row">
            <span class="funnel-label">发放(张)</span>
            <div class="funnel-bar-wrap"><div class="funnel-bar" style="width:100%;background:#C4923A">{{ stats.funnel.issued }}</div></div>
          </div>
          <div class="funnel-row">
            <span class="funnel-label">领券会员(人)</span>
            <div class="funnel-bar-wrap"><div class="funnel-bar" :style="{ width: Math.max(stats.funnel.claim_rate,4)+'%', background:'#D4A59A' }">{{ stats.funnel.claimed }}</div></div>
            <span class="funnel-rate">会员渗透率 {{ stats.funnel.claim_rate }}%</span>
          </div>
          <div class="funnel-row">
            <span class="funnel-label">核销(张)</span>
            <div class="funnel-bar-wrap"><div class="funnel-bar" :style="{ width: Math.max(stats.funnel.redeem_rate,4)+'%', background:'#3E8E41' }">{{ stats.funnel.redeemed }}</div></div>
            <span class="funnel-rate">核销率 {{ stats.funnel.redeem_rate }}%</span>
          </div>
        </div>
        <p class="hint" v-if="stats?.funnel">口径：发放=已发券张数；领券会员=去重领券人数（≤发放）；核销=已核销张数。会员渗透率=领券会员/发放，核销率=核销/发放，均≤100%。</p>
        <div v-else class="hot-empty">暂无数据</div>
      </div>

      <!-- 会员结构 -->
      <div class="db-card">
        <div class="db-card-h">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#9B7BD4" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-3px;margin-right:6px"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/></svg>
          会员结构
        </div>
        <div class="lv-bars" v-if="stats?.member_levels?.length">
          <div class="lv-row" v-for="lv in stats.member_levels" :key="lv.level">
            <span class="lv-name">{{ lv.level }}</span>
            <div class="lv-bar-wrap"><div class="lv-bar" :style="{ width: lvPct(lv.count)+'%' }"></div></div>
            <span class="lv-count">{{ lv.count }}</span>
          </div>
        </div>
        <div class="seg-row" v-if="stats?.member_segments">
          <div class="seg"><span class="seg-num">{{ stats.member_segments.new_30 }}</span><span class="seg-lab">近30天新增</span></div>
          <div class="seg"><span class="seg-num">{{ stats.member_segments.active_30 }}</span><span class="seg-lab">活跃(30天)</span></div>
          <div class="seg"><span class="seg-num danger">{{ stats.member_segments.silent }}</span><span class="seg-lab">沉默会员</span></div>
        </div>
      </div>

      <!-- 运营预警 + 待办 -->
      <div class="db-card">
        <div class="db-card-h">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#E85D04" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-3px;margin-right:6px"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
          运营预警 · 待办
        </div>
        <div class="alert-list" v-if="stats?.alerts?.length">
          <div class="alert-item" v-for="a in stats.alerts" :key="a.key">
            <span class="alert-dot" :class="a.level"></span>
            <span class="alert-text">{{ a.text }}</span>
          </div>
        </div>
        <div v-else class="alert-ok">✓ 暂无预警</div>
        <div class="todo-row">
          <router-link class="todo-btn" :to="{ name: 'admin-orders' }">待处理工单 {{ stats?.pending_orders || 0 }} →</router-link>
          <router-link class="todo-btn" :to="{ name: 'admin-kb' }">待优化知识库 {{ stats?.pending_kb || 0 }} →</router-link>
        </div>
      </div>

      <!-- 热门活动 TOP5 -->
      <div class="db-card db-card-wide">
        <div class="db-card-h">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#999999" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-3px;margin-right:6px"><path d="M17.66 18l-3.55-6.53a1 1 0 00-1.73.01L8.83 18"/><polyline points="6 11 10.59 3 15.18 11"/><line x1="2" y1="22" x2="22" y2="22"/></svg>
          热门活动 TOP5
        </div>
        <div class="hot-list" v-if="stats?.hot_activities?.length">
          <div v-for="(a, i) in stats.hot_activities" :key="a.id" class="hot-item">
            <span class="hot-rank" :style="i === 0 ? 'background:#E85D04;color:#fff' : ''">{{ i + 1 }}</span>
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
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { seedDemo, seedClear } from '@/api'
import { exportCsv, printReport } from '@/utils/export'

const stats = ref(null)
const deltas = ref({})
const weeklyHeadline = ref('')
const seeding = ref(false)
const clearing = ref(false)

const statCards = reactive([
  { key: 'chats', label: '今日咨询', value: '--', color: '#4A90D9', goodUp: true },
  { key: 'members', label: '会员总数', value: '--', color: '#E85D04' },
  { key: 'orders', label: '工单总数', value: '--', color: '#9B7BD4' },
  { key: 'gmv', label: '今日 GMV', value: '--', color: '#C4923A', goodUp: true },
  { key: 'redeem', label: '今日核销', value: '--', color: '#3E8E41', goodUp: true },
  { key: 'newmem', label: '今日新增会员', value: '--', color: '#E8809E' },
  { key: 'points', label: '积分发放(今日)', value: '--', color: '#D4A59A', goodUp: true },
  { key: 'shops', label: '商户总数', value: '--', color: '#6B6E64' },
])

// 看板返回的环比/周同比字段映射（仅这 4 项有对比基准）
const DELTA_MAP = {
  chats: ['chats_dod', 'chats_wow'],
  gmv: ['gmv_dod', 'gmv_wow'],
  redeem: ['redeemed_dod', 'redeemed_wow'],
  points: ['points_dod', 'points_wow'],
}
function deltaOf(key) {
  const m = DELTA_MAP[key]
  if (!m) return { dod: null, wow: null }
  return { dod: deltas.value[m[0]], wow: deltas.value[m[1]] }
}
function deltaArrow(v) { return v >= 0 ? '▲' : '▼' }
function deltaCls(key, which) {
  const v = deltaOf(key)[which]
  if (v == null) return ''
  const goodUp = statCards.find(c => c.key === key)?.goodUp
  const up = v >= 0
  const good = goodUp ? up : !up
  return good ? 'good' : 'bad'
}
function dateStr() {
  const d = new Date()
  const p = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}`
}

function sparkPoints(series) {
  if (!series || !series.length) return ''
  const vals = series.map(s => Number(s.value) || 0)
  const max = Math.max(...vals, 1)
  const min = Math.min(...vals)
  const range = max - min || 1
  const w = 120, h = 36, pad = 3
  const n = vals.length
  return vals.map((v, i) => {
    const x = pad + (w - 2 * pad) * (i / (n - 1))
    const y = h - pad - (h - 2 * pad) * ((v - min) / range)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
}

const sparkMetrics = computed(() => {
  const s = stats.value
  if (!s) return []
  const mk = (key, label, color, suffix, series) => {
    const arr = series || []
    const last = arr.length ? (Number(arr[arr.length - 1].value) || 0) : 0
    return { key, label, color, suffix: suffix || '', last, points: sparkPoints(arr) }
  }
  return [
    mk('chats', '咨询量', '#4A90D9', '', s.series_chats),
    mk('gmv', 'GMV', '#C4923A', '', s.series_gmv),
    mk('active', '活跃会员', '#9B7BD4', '', s.series_active),
  ]
})

function fmtPct(v) {
  if (typeof v === 'number') return v + '%'
  return v ?? '—'
}
function lvPct(count) {
  const total = (stats.value?.member_levels || []).reduce((a, b) => a + b.count, 0) || 1
  return Math.round(count / total * 100)
}

async function loadDashboard() {
  try {
    const res = await fetch('/api/dashboard')
    const d = await res.json()
    if (d.ok) {
      stats.value = d
      statCards[0].value = d.today_chats ?? '--'
      statCards[1].value = d.active_members ?? '--'
      statCards[2].value = d.total_orders ?? '--'
      statCards[3].value = d.gmv_today ?? '--'
      statCards[4].value = d.redeemed_today ?? '--'
      statCards[5].value = d.new_members_today ?? '--'
      statCards[6].value = d.points_issued_today ?? '--'
      statCards[7].value = d.shops_total ?? '--'
      deltas.value = {
        chats_dod: d.chats_dod, chats_wow: d.chats_wow,
        gmv_dod: d.gmv_dod, gmv_wow: d.gmv_wow,
        redeemed_dod: d.redeemed_dod, redeemed_wow: d.redeemed_wow,
        points_dod: d.points_dod, points_wow: d.points_wow,
      }
      weeklyHeadline.value = d.weekly_headline || ''
    }
  } catch {}
}

async function runSeed() {
  if (!window.confirm('将种入近 90 天仿真历史数据（全部标记 demo，可一键清空，不影响真实数据）。是否继续？')) return
  seeding.value = true
  try {
    const d = await seedDemo(0)
    if (d.ok) {
      if (d.already_seeded) ElMessage.info('演示数据已存在，无需重复种入')
      else ElMessage.success('演示数据已种入，刷新后看板即为真实数字')
      loadDashboard()
    } else ElMessage.error(d.error || '种入失败')
  } catch { ElMessage.error('操作失败') }
  seeding.value = false
}

async function runClear() {
  if (!window.confirm('将清空全部演示数据（仅删 demo 标记行），真实数据不受影响。是否继续？')) return
  clearing.value = true
  try {
    const d = await seedClear()
    if (d.ok) { ElMessage.success('演示数据已清空'); loadDashboard() }
    else ElMessage.error(d.error || '清空失败')
  } catch { ElMessage.error('操作失败') }
  clearing.value = false
}

function exportBoard() {
  const rows = statCards.map(c => ({ 指标: c.label, 数值: c.value }))
  const ok = exportCsv(rows, `看板数据_${dateStr()}.csv`, [{ key: '指标', title: '指标' }, { key: '数值', title: '数值' }])
  if (!ok) ElMessage.warning('暂无可导出数据')
}

function printBoard() {
  printReport('海江新天地 · 运营看板日报', [
    {
      title: '核心指标',
      columns: [{ key: 'label', title: '指标' }, { key: 'value', title: '数值' }],
      rows: statCards.map(c => ({ label: c.label, value: c.value }))
    }
  ])
}

onMounted(loadDashboard)
</script>

<style scoped>
.admin-dashboard { padding: 0; background: transparent; }
.admin-dashboard h3 { margin: 0 0 12px; color: #F0F0F0; font-size: 18px; }

/* 工具栏 */
.db-toolbar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
.tb-btn { padding: 7px 14px; border-radius: 9px; border: none; font-size: 13px; font-weight: 600; cursor: pointer; background: linear-gradient(135deg,#FF7B2C,#E85D04); color: #fff; transition: .15s; }
.tb-btn:disabled { opacity: .6; cursor: not-allowed; }
.tb-btn:not(:disabled):hover { box-shadow: 0 4px 12px rgba(232,93,4,.3); }
.tb-ghost { background: #262626; color: #cfcfcf; }
.tb-ghost:hover { background: #333; }
.tb-sep { width: 1px; height: 22px; background: #2a2a2a; margin: 0 2px; }
.tb-demo { font-size: 12px; color: #E8A33D; background: rgba(232,163,61,.14); border: 1px solid rgba(232,163,61,.45); padding: 4px 10px; border-radius: 999px; margin-left: auto; }

/* 调试工具折叠面板（演示数据维护，默认折叠） */
.db-debug { margin-left: 8px; border: 1px solid #2a2a2a; border-radius: 9px; background: #1A1A1A; overflow: hidden; }
.db-debug-sum { cursor: pointer; padding: 7px 14px; font-size: 13px; font-weight: 600; color: #cfcfcf; user-select: none; list-style: none; }
.db-debug-sum::-webkit-details-marker { display: none; }
.db-debug-sum::before { content: '▸ '; color: #888; }
.db-debug[open] .db-debug-sum::before { content: '▾ '; }
.db-debug-body { padding: 4px 14px 14px; }
.db-debug-warn { font-size: 12px; color: #E8A33D; line-height: 1.6; margin: 0 0 10px; }
.db-debug-btns { display: flex; gap: 8px; flex-wrap: wrap; }

/* 周报一句话 */
.weekly-headline { display: flex; align-items: center; gap: 8px; background: linear-gradient(90deg, rgba(255,123,44,.14), rgba(255,123,44,0)); border: 1px solid rgba(255,123,44,.3); border-radius: 10px; padding: 10px 14px; margin-bottom: 16px; font-size: 14px; color: #f0e6dd; }
.wh-ico { font-size: 15px; }

.stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 20px; }
.stat-card {
  background: #1A1A1A; border-radius: 14px; padding: 16px;
  display: flex; align-items: center; gap: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.stat-icon { width: 42px; height: 42px; border-radius: 10px; display: flex; align-items: center; justify-content: center; background: color-mix(in srgb, var(--card-color) 15%, transparent); }
.stat-info { display: flex; flex-direction: column; }
.stat-value { font-size: 22px; font-weight: 800; color: #F0F0F0; line-height: 1.2; }
.stat-label { font-size: 12px; color: #999; margin-top: 2px; }
.stat-delta { display: flex; gap: 6px; margin-top: 6px; }
.d-chip { font-size: 11px; font-weight: 700; padding: 2px 6px; border-radius: 6px; line-height: 1.3; }
.d-chip.good { color: #FF6A4D; background: rgba(255,106,77,.15); }
.d-chip.bad { color: #4CAF50; background: rgba(76,175,80,.16); }

.chart-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; align-items: start; }
.db-card { background: #1A1A1A; border-radius: 14px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.db-card-wide { grid-column: 1 / -1; }
.db-card-h { padding: 14px 16px; font-weight: 600; color: #F0F0F0; font-size: 15px; border-bottom: 1px solid #2a2a2a; }

/* sparkline */
.spark-list { padding: 8px 4px; }
.spark-item { display: flex; align-items: center; gap: 12px; padding: 8px 12px; }
.spark-meta { width: 120px; display: flex; flex-direction: column; flex-shrink: 0; }
.spark-label { font-size: 12px; color: #999; }
.spark-val { font-size: 18px; font-weight: 800; color: #F0F0F0; }
.spark-val small { font-size: 11px; font-weight: 500; margin-left: 1px; }
.spark-svg { flex: 1; height: 36px; }

/* kpi list */
.kpi-list { padding: 4px 0; }
.kpi-item { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-bottom: 1px solid #2a2a2a; font-size: 14px; color: #BBBBBB; }
.kpi-item:last-child { border-bottom: none; }
.kpi-item strong { color: #F0F0F0; font-size: 16px; }
.kpi-item strong.danger { color: #E8503A; }
.kpi-unit { font-size: 10px; font-weight: 600; color: #E8A33D; background: rgba(232,163,61,.14); border: 1px solid rgba(232,163,61,.4); border-radius: 5px; padding: 1px 5px; margin-left: 6px; font-style: normal; vertical-align: middle; }

/* funnel */
.funnel { padding: 16px; display: flex; flex-direction: column; gap: 14px; }
.funnel-row { display: flex; align-items: center; gap: 10px; }
.funnel-label { width: 32px; font-size: 13px; color: #BBBBBB; flex-shrink: 0; }
.funnel-bar-wrap { flex: 1; background: #262626; border-radius: 8px; height: 28px; overflow: hidden; }
.funnel-bar { height: 100%; border-radius: 8px; display: flex; align-items: center; justify-content: flex-end; padding-right: 10px; color: #fff; font-size: 13px; font-weight: 700; min-width: 28px; transition: width .4s; }
.funnel-rate { width: 92px; font-size: 12px; color: #999; text-align: right; flex-shrink: 0; }

/* member structure */
.lv-bars { padding: 14px 16px 6px; display: flex; flex-direction: column; gap: 10px; }
.lv-row { display: flex; align-items: center; gap: 10px; }
.lv-name { width: 56px; font-size: 13px; color: #BBBBBB; flex-shrink: 0; }
.lv-bar-wrap { flex: 1; background: #262626; border-radius: 6px; height: 18px; overflow: hidden; }
.lv-bar { height: 100%; background: linear-gradient(90deg,#9B7BD4,#C4923A); border-radius: 6px; transition: width .4s; }
.lv-count { width: 32px; text-align: right; font-size: 13px; color: #F0F0F0; font-weight: 700; }
.seg-row { display: flex; border-top: 1px solid #2a2a2a; margin-top: 6px; }
.seg { flex: 1; padding: 12px 8px; text-align: center; border-right: 1px solid #2a2a2a; }
.seg:last-child { border-right: none; }
.seg-num { display: block; font-size: 20px; font-weight: 800; color: #F0F0F0; }
.seg-num.danger { color: #E8503A; }
.seg-lab { font-size: 11px; color: #999; }

/* alerts */
.alert-list { padding: 12px 16px; display: flex; flex-direction: column; gap: 10px; }
.alert-item { display: flex; align-items: center; gap: 10px; }
.alert-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.alert-dot.warn { background: #E8A33D; box-shadow: 0 0 0 3px rgba(232,163,61,.18); }
.alert-dot.danger { background: #E8503A; box-shadow: 0 0 0 3px rgba(232,80,58,.18); }
.alert-text { font-size: 14px; color: #F0F0F0; }
.alert-ok { padding: 16px; text-align: center; color: #3E8E41; font-size: 14px; }
.todo-row { display: flex; gap: 10px; padding: 12px 16px; border-top: 1px solid #2a2a2a; flex-wrap: wrap; }
.todo-btn { flex: 1; min-width: 130px; text-align: center; padding: 10px; border-radius: 10px; background: #262626; color: #E8C9A0; font-size: 13px; font-weight: 600; text-decoration: none; }
.todo-btn:hover { background: #303030; }

/* hot list */
.hot-list { padding: 4px 0; }
.hot-item { display: flex; align-items: center; gap: 10px; padding: 12px 16px; border-bottom: 1px solid #2a2a2a; font-size: 14px; }
.hot-item:last-child { border-bottom: none; }
.hot-rank { width: 22px; height: 22px; border-radius: 6px; background: #262626; color: #999; font-size: 12px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.hot-text { flex: 1; color: #F0F0F0; }
.hot-count { color: #999; font-size: 12px; }
.hot-empty { padding: 20px; text-align: center; color: #999; font-size: 13px; }

@media (max-width: 767px) {
  .chart-grid { grid-template-columns: 1fr; }
  .stat-grid { grid-template-columns: repeat(2, 1fr); gap: 8px; }
  .stat-card { padding: 12px; }
  .stat-value { font-size: 18px; }
  .stat-icon { width: 34px; height: 34px; }
  .spark-meta { width: 84px; }
}
</style>
