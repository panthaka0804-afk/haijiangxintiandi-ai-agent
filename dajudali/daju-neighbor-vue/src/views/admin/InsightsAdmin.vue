<template>
  <div class="in-page">
    <div class="page-header">
      <h3>运营洞察</h3>
      <div class="hdr-right">
        <el-radio-group v-model="days" size="small" @change="loadInsights">
          <el-radio-button :value="7">近 7 天</el-radio-button>
          <el-radio-button :value="30">近 30 天</el-radio-button>
          <el-radio-button :value="90">近 90 天</el-radio-button>
        </el-radio-group>
        <el-button size="small" :loading="loading" @click="loadAll">刷新</el-button>
      </div>
    </div>

    <div class="hint-bar">数据来源：会员 / 评价 / 投诉 / 券核销 / 消费 / 知识库等真实业务表，按所选时间窗实时聚合</div>

    <!-- E. 智能预警雷达 -->
    <section class="mc-card mc-card-red panel">
      <div class="panel-head">
        <h2><span class="dot" style="background:#F56C6C"></span>智能预警雷达</h2>
        <span class="engine" v-if="insights.alerts.length">待处理 {{ insights.alerts.length }}</span>
        <span class="engine ok" v-else>一切正常</span>
      </div>
      <div v-if="!insights.alerts.length" class="empty">近 {{ days }} 天未触发预警阈值</div>
      <div v-else class="alert-list">
        <div v-for="(a, i) in insights.alerts" :key="i" class="alert-item" :class="a.level">
          <span class="alert-badge">{{ a.level === 'high' ? '高' : a.level === 'mid' ? '中' : '低' }}</span>
          <div class="alert-body">
            <div class="alert-title">{{ a.title }}</div>
            <div class="alert-detail">{{ a.detail }}</div>
          </div>
        </div>
      </div>
    </section>

    <!-- G. 可点选优化建议 -->
    <section class="mc-card mc-card-orange panel">
      <div class="panel-head"><h2><span class="dot" style="background:#C9956C"></span>优化建议（可点选执行）</h2></div>
      <div v-if="!insights.suggestions.length" class="empty">暂无建议</div>
      <div v-else class="suggest-grid">
        <div v-for="(s, i) in insights.suggestions" :key="i" class="suggest-card" @click="runSuggestion(s)">
          <div class="suggest-ico">💡</div>
          <div class="suggest-text">{{ s.text }}</div>
          <div class="suggest-act">{{ s.target ? '前往处理 →' : '在此补充 ↓' }}</div>
        </div>
      </div>
    </section>

    <!-- A. 投诉 / 评分趋势 + 环比 -->
    <section class="mc-card mc-card-purple panel">
      <div class="panel-head"><h2><span class="dot" style="background:#8B8B90"></span>投诉与口碑趋势（近 {{ days }} 天）</h2></div>
      <div class="pop-row">
        <div class="pop" :class="delta(insights.comp_cur, insights.comp_prev, true).cls">
          <b>{{ insights.comp_cur }}</b><span>投诉量</span>
          <em>{{ delta(insights.comp_cur, insights.comp_prev, true).txt }}</em>
        </div>
        <div class="pop" :class="delta(insights.rating_cur, insights.rating_prev, false).cls">
          <b>{{ insights.rating_cur }}</b><span>均评分</span>
          <em>{{ delta(insights.rating_cur, insights.rating_prev, false).txt }}</em>
        </div>
        <div class="pop" :class="delta(insights.lowrate_cur, insights.lowrate_prev, true).cls">
          <b>{{ insights.lowrate_cur }}%</b><span>低分率</span>
          <em>{{ delta(insights.lowrate_cur, insights.lowrate_prev, true).txt }}</em>
        </div>
      </div>
      <div class="charts-2">
        <div class="chart-box">
          <div class="chart-cap">每日投诉量</div>
          <svg viewBox="0 0 300 78" class="trend" preserveAspectRatio="none">
            <defs><linearGradient id="g-comp" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#8B8B90" stop-opacity="0.4" />
              <stop offset="100%" stop-color="#8B8B90" stop-opacity="0" />
            </linearGradient></defs>
            <polygon v-if="charts.complaint.area" :points="charts.complaint.area" :fill="`url(#g-comp)`" />
            <polyline v-if="charts.complaint.line" :points="charts.complaint.line" fill="none" stroke="#8B8B90" stroke-width="2" stroke-linejoin="round" />
          </svg>
        </div>
        <div class="chart-box">
          <div class="chart-cap">每日均评分</div>
          <svg viewBox="0 0 300 78" class="trend" preserveAspectRatio="none">
            <defs><linearGradient id="g-rating" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#C4923A" stop-opacity="0.4" />
              <stop offset="100%" stop-color="#C4923A" stop-opacity="0" />
            </linearGradient></defs>
            <polygon v-if="charts.rating.area" :points="charts.rating.area" :fill="`url(#g-rating)`" />
            <polyline v-if="charts.rating.line" :points="charts.rating.line" fill="none" stroke="#C4923A" stroke-width="2" stroke-linejoin="round" />
          </svg>
        </div>
      </div>
    </section>

    <!-- B. 会员新增 / 活跃 / 沉默趋势 -->
    <section class="mc-card mc-card-green panel">
      <div class="panel-head">
        <h2><span class="dot" style="background:#6B6E64"></span>会员活跃与流失趋势</h2>
        <span class="engine warn" v-if="insights.silent_ratio >= 40">沉默占比 {{ insights.silent_ratio }}%</span>
      </div>
      <div class="pop-row">
        <div class="pop"><b>{{ insights.member_total }}</b><span>会员总数</span></div>
        <div class="pop bad"><b>{{ insights.silent_count }}</b><span>沉默会员(>90天)</span></div>
        <div class="pop" :class="insights.silent_ratio >= 40 ? 'bad' : 'good'"><b>{{ insights.silent_ratio }}%</b><span>沉默占比</span></div>
      </div>
      <div class="chart-box">
        <div class="chart-cap">每日活跃（签到/打卡/消费去重）vs 新增会员</div>
        <svg viewBox="0 0 600 90" class="trend-lg" preserveAspectRatio="none">
          <defs><linearGradient id="g-act" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#6B6E64" stop-opacity="0.4" />
            <stop offset="100%" stop-color="#6B6E64" stop-opacity="0" />
          </linearGradient></defs>
          <polygon v-if="charts.active.area" :points="charts.active.area" :fill="`url(#g-act)`" />
          <polyline v-if="charts.active.line" :points="charts.active.line" fill="none" stroke="#6B6E64" stroke-width="2.2" />
          <polyline v-if="charts.new.line" :points="charts.new.line" fill="none" stroke="#FF7B2C" stroke-width="2.2" stroke-dasharray="5 4" />
        </svg>
        <div class="legend"><i style="background:#6B6E64"></i>活跃<i style="background:#FF7B2C"></i>新增</div>
      </div>
    </section>

    <!-- C. 营销转化漏斗 -->
    <section class="mc-card mc-card-gold panel">
      <div class="panel-head"><h2><span class="dot" style="background:#C4923A"></span>营销转化漏斗（券）</h2><span class="engine">核销率 {{ insights.funnel.redeem_rate }}%</span></div>
      <div class="funnel">
        <div class="fnl-row" v-for="s in funnelSteps" :key="s.label">
          <div class="fnl-label">{{ s.label }}</div>
          <div class="fnl-track"><i :style="{ width: s.pct + '%', background: s.color }"></i></div>
          <div class="fnl-val">{{ s.value }}</div>
        </div>
      </div>
      <div class="mini-grid">
        <div class="mini"><b>{{ insights.funnel.issued }}</b><span>在架券（发放）</span></div>
        <div class="mini"><b>{{ insights.funnel.claimed }}</b><span>已领取</span></div>
        <div class="mini"><b>{{ insights.funnel.redeemed }}</b><span>已核销</span></div>
        <div class="mini"><b>{{ insights.funnel.claim_rate }}%</b><span>领取率</span></div>
      </div>
      <div class="act-line">🎯 活动转化：{{ insights.funnel.act_count }} 场活动 · 报名 {{ insights.funnel.act_enrolled }} 人次 · 通过绑定券核销 {{ insights.funnel.act_redeemed }} 次</div>
    </section>

    <!-- D. AI 命中率 / 知识库健康度 -->
    <section class="mc-card mc-card-pink panel">
      <div class="panel-head"><h2><span class="dot" style="background:#D4A59A"></span>AI 命中率 / 知识库健康度</h2><span class="engine" :class="insights.kb_health.hit_rate >= 60 ? 'ok' : 'warn'">健康度 {{ insights.kb_health.hit_rate }}%</span></div>
      <div class="kb-top">
        <div class="ring" :style="{ '--p': insights.kb_health.hit_rate }">
          <div class="ring-num">{{ insights.kb_health.hit_rate }}%</div>
          <div class="ring-cap">已处理占比</div>
        </div>
        <div class="kb-stats">
          <div class="kb-s"><b>{{ insights.kb_health.total }}</b><span>问题池</span></div>
          <div class="kb-s"><b style="color:#DD8E7C">{{ insights.kb_health.pending }}</b><span>待补充</span></div>
          <div class="kb-s"><b style="color:#A9BBA0">{{ insights.kb_health.imported }}</b><span>已入库</span></div>
          <div class="kb-s"><b style="color:#BABABA">{{ insights.kb_health.dismissed }}</b><span>已忽略</span></div>
        </div>
      </div>
      <div class="chart-box">
        <div class="chart-cap">每日新增未命中问题</div>
        <svg viewBox="0 0 300 70" class="trend" preserveAspectRatio="none">
          <defs><linearGradient id="g-kb" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#D4A59A" stop-opacity="0.4" />
            <stop offset="100%" stop-color="#D4A59A" stop-opacity="0" />
          </linearGradient></defs>
          <polygon v-if="charts.kbpending.area" :points="charts.kbpending.area" :fill="`url(#g-kb)`" />
          <polyline v-if="charts.kbpending.line" :points="charts.kbpending.line" fill="none" stroke="#D4A59A" stroke-width="2" />
        </svg>
      </div>
    </section>

    <!-- F. GMV / 客单价 / 人均趋势 -->
    <section class="mc-card mc-card-red panel">
      <div class="panel-head"><h2><span class="dot" style="background:#9B4A3E"></span>GMV 与客单趋势</h2></div>
      <div class="pop-row">
        <div class="pop" :class="delta(insights.gmv_cur, insights.gmv_prev, false).cls">
          <b>¥{{ insights.gmv_cur }}</b><span>GMV（{{ days }}天）</span>
          <em>{{ delta(insights.gmv_cur, insights.gmv_prev, false).txt }}</em>
        </div>
        <div class="pop"><b>¥{{ insights.aov_cur }}</b><span>客单价</span></div>
        <div class="pop"><b>¥{{ insights.percap_cur }}</b><span>人均消费</span></div>
      </div>
      <div class="chart-box">
        <div class="chart-cap">每日 GMV</div>
        <svg viewBox="0 0 600 90" class="trend-lg" preserveAspectRatio="none">
          <defs><linearGradient id="g-gmv" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#9B4A3E" stop-opacity="0.45" />
            <stop offset="100%" stop-color="#9B4A3E" stop-opacity="0" />
          </linearGradient></defs>
          <polygon v-if="charts.gmv.area" :points="charts.gmv.area" :fill="`url(#g-gmv)`" />
          <polyline v-if="charts.gmv.line" :points="charts.gmv.line" fill="none" stroke="#9B4A3E" stroke-width="2.2" />
        </svg>
      </div>
    </section>

    <!-- 知识库待优化列表（保留） -->
    <el-card ref="kbRef" shadow="never" class="kb-card">
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
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()
const days = ref(30)
const loading = ref(false)
const kbRef = ref(null)

const insights = reactive({
  complaint_total: 0, top_complaints: [], pending_total: 0, top_pending: [], low_feedback_count: 0,
  complaint_trend: [], rating_trend: [], comp_cur: 0, comp_prev: 0, rating_cur: 0, rating_prev: 0, lowrate_cur: 0, lowrate_prev: 0,
  member_trend: [], silent_count: 0, silent_ratio: 0, silent_trend: [], member_total: 0,
  funnel: { issued: 0, claimed: 0, redeemed: 0, claim_rate: 0, redeem_rate: 0, act_count: 0, act_enrolled: 0, act_with_offer: 0, act_redeemed: 0 },
  kb_health: { total: 0, pending: 0, imported: 0, dismissed: 0, hit_rate: 0, pending_trend: [], escalation_trend: [] },
  gmv_trend: [], aov_trend: [], percap_trend: [], gmv_cur: 0, gmv_prev: 0, aov_cur: 0, percap_cur: 0,
  alerts: [], suggestions: [], d: 30
})

const pending = ref([])
const pendingTotal = ref(0)
const editingId = ref(0)
const editAnswer = ref('')
const editCategory = ref('service')
const categories = ['service', '优惠', '停车', '导航', '活动', '会员', '商户', '其他']

function sourceName(s) {
  const map = { chat: 'AI未命中', complaint: '投诉反馈', feedback: '用户反馈' }
  return map[s] || s
}

// ---------- SVG 折线图辅助 ----------
function lineChart(series, valKey) {
  const w = 600, h = 90, pad = 8
  const vals = series.map(s => s[valKey]).filter(v => v != null && !isNaN(v))
  const max = vals.length ? Math.max(...vals) : 1
  const min = vals.length ? Math.min(...vals) : 0
  const n = series.length
  const iw = w - pad * 2, ih = h - pad * 2
  const pts = []
  series.forEach((s, i) => {
    const v = s[valKey]
    const x = pad + (n <= 1 ? iw / 2 : (i / (n - 1)) * iw)
    const y = (v == null || isNaN(v)) ? null : (pad + ih - ((v - min) / ((max - min) || 1)) * ih)
    pts.push({ x, y })
  })
  const valid = pts.filter(p => p.y != null)
  const line = valid.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
  const area = valid.length ? `${pad},${h - pad} ` + valid.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ') + ` ${pad + iw},${h - pad}` : ''
  return { line, area, has: valid.length > 0 }
}

const charts = computed(() => ({
  complaint: lineChart(insights.complaint_trend, 'value'),
  rating: lineChart(insights.rating_trend, 'avg'),
  active: lineChart(insights.member_trend, 'active'),
  new: lineChart(insights.member_trend, 'new'),
  gmv: lineChart(insights.gmv_trend, 'value'),
  kbpending: lineChart(insights.kb_health.pending_trend, 'value')
}))

const funnelSteps = computed(() => {
  const f = insights.funnel
  const max = f.issued || 1
  return [
    { label: '发放（在架券）', value: f.issued, pct: 100, color: 'linear-gradient(90deg,#C4923A,#E3BB6A)' },
    { label: '领取', value: f.claimed, pct: Math.round(f.claimed / max * 100) || (f.claimed ? 4 : 0), color: 'linear-gradient(90deg,#C9956C,#E0B58C)' },
    { label: '核销', value: f.redeemed, pct: Math.round(f.redeemed / max * 100) || (f.redeemed ? 3 : 0), color: 'linear-gradient(90deg,#6B6E64,#9AA088)' }
  ]
})

function delta(cur, prev, invert) {
  if (prev == null || prev === 0) return { txt: '新', cls: 'flat' }
  const pct = ((cur - prev) / prev) * 100
  const up = pct >= 0
  const good = invert ? !up : up
  return { txt: (up ? '↑' : '↓') + Math.abs(pct).toFixed(0) + '%', cls: good ? 'good' : 'bad' }
}

function runSuggestion(s) {
  if (s.target) {
    router.push(s.target)
  } else if (s.action === 'scroll-kb') {
    nextTick(() => kbRef.value && kbRef.value.$el && kbRef.value.$el.scrollIntoView({ behavior: 'smooth' }))
  }
}

async function loadInsights() {
  loading.value = true
  try {
    const resp = await fetch(`/api/admin/insights?days=${days.value}`)
    const d = await resp.json()
    if (d.ok) Object.assign(insights, d.data)
  } catch {}
  loading.value = false
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

function loadAll() {
  loadInsights()
  loadPending()
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
    } else ElMessage.error(d.error || '入库失败')
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
.in-page { padding: 4px 2px 40px; color: #e8e8e8; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.page-header h3 { margin: 0; color: #F2F2F2; font-size: 18px; border-left: 4px solid #FF7B2C; padding-left: 12px; line-height: 1.2; }
.hdr-right { display: flex; align-items: center; gap: 10px; }
.hint-bar { font-size: 12px; color: #8a8a8a; background: #161616; border: 1px solid #2a2a2a; border-radius: 8px; padding: 8px 12px; margin-bottom: 14px; }

.panel { background: #161616; border: 1px solid #2a2a2a; border-radius: 14px; padding: 14px 16px; margin-bottom: 14px; position: relative; overflow: hidden; }
.panel::before { content: ''; position: absolute; left: 0; top: 0; right: 0; height: 3px; background: linear-gradient(90deg, var(--mc-bar, #FF7B2C), transparent); }
.mc-card-purple::before { --mc-bar: #8B8B90; }
.mc-card-orange::before { --mc-bar: #C9956C; }
.mc-card-green::before { --mc-bar: #6B6E64; }
.mc-card-gold::before { --mc-bar: #C4923A; }
.mc-card-pink::before { --mc-bar: #D4A59A; }
.mc-card-red::before { --mc-bar: #9B4A3E; }

.panel-head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.panel-head h2 { margin: 0; font-size: 15px; color: #f0f0f0; font-weight: 600; display: flex; align-items: center; gap: 8px; }
.dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
.engine { margin-left: auto; font-size: 12px; color: #BABABA; background: #222; padding: 3px 10px; border-radius: 20px; }
.engine.ok { color: #A9BBA0; background: rgba(107,110,100,0.2); }
.engine.warn { color: #E3BB6A; background: rgba(196,146,58,0.18); }
.empty { color: #777; font-size: 13px; padding: 16px 0; text-align: center; }

/* 预警 */
.alert-list { display: flex; flex-direction: column; gap: 8px; }
.alert-item { display: flex; gap: 10px; align-items: flex-start; background: #1d1d1d; border-radius: 10px; padding: 10px 12px; border-left: 3px solid #555; }
.alert-item.high { border-left-color: #F56C6C; }
.alert-item.mid { border-left-color: #E6A23C; }
.alert-item.low { border-left-color: #8B8B90; }
.alert-badge { flex: none; width: 22px; height: 22px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; color: #fff; background: #6b6b6b; }
.alert-item.high .alert-badge { background: #F56C6C; }
.alert-item.mid .alert-badge { background: #E6A23C; }
.alert-title { font-size: 13px; color: #f0f0f0; font-weight: 600; }
.alert-detail { font-size: 12px; color: #aaa; margin-top: 2px; }

/* 建议 */
.suggest-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 10px; }
.suggest-card { background: #1d1d1d; border: 1px solid #333; border-radius: 10px; padding: 12px; cursor: pointer; transition: .15s; display: flex; gap: 10px; align-items: flex-start; }
.suggest-card:hover { border-color: #FF7B2C; transform: translateY(-2px); }
.suggest-ico { font-size: 18px; }
.suggest-text { flex: 1; font-size: 13px; color: #ddd; line-height: 1.5; }
.suggest-act { font-size: 12px; color: #FF7B2C; white-space: nowrap; }

/* PoP 卡片 */
.pop-row { display: flex; gap: 10px; margin-bottom: 12px; }
.pop { flex: 1; background: #1d1d1d; border-radius: 10px; padding: 10px 12px; text-align: center; position: relative; }
.pop b { display: block; font-size: 20px; color: #f0f0f0; }
.pop span { font-size: 12px; color: #999; }
.pop em { display: block; font-size: 11px; margin-top: 3px; font-style: normal; color: #888; }
.pop.good b, .pop.good em { color: #A9BBA0; }
.pop.bad b, .pop.bad em { color: #DD8E7C; }
.pop.flat em { color: #888; }

/* 图表 */
.charts-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.chart-box { background: #1d1d1d; border-radius: 10px; padding: 10px 12px; }
.chart-cap { font-size: 12px; color: #aaa; margin-bottom: 6px; }
.trend { width: 100%; height: 78px; display: block; }
.trend-lg { width: 100%; height: 90px; display: block; }
.legend { display: flex; gap: 14px; font-size: 11px; color: #999; margin-top: 4px; }
.legend i { display: inline-block; width: 12px; height: 4px; border-radius: 2px; margin-right: 4px; vertical-align: middle; }

/* 漏斗 */
.funnel { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }
.fnl-row { display: flex; align-items: center; gap: 10px; }
.fnl-label { width: 110px; font-size: 12px; color: #ccc; flex: none; text-align: right; }
.fnl-track { flex: 1; height: 22px; background: #1d1d1d; border-radius: 6px; overflow: hidden; }
.fnl-track i { display: block; height: 100%; border-radius: 6px; min-width: 3px; }
.fnl-val { width: 56px; font-size: 13px; color: #f0f0f0; font-weight: 600; flex: none; }
.mini-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 10px; }
.mini { background: #1d1d1d; border-radius: 8px; padding: 8px; text-align: center; }
.mini b { display: block; color: #E3BB6A; font-size: 16px; }
.mini span { font-size: 11px; color: #999; }
.act-line { font-size: 12px; color: #bbb; background: #1d1d1d; border-radius: 8px; padding: 8px 12px; }

/* KB 健康度 */
.kb-top { display: flex; gap: 18px; align-items: center; margin-bottom: 12px; }
.ring { width: 92px; height: 92px; border-radius: 50%; flex: none; display: flex; flex-direction: column; align-items: center; justify-content: center;
  background: conic-gradient(#D4A59A calc(var(--p) * 1%), #2a2a2a 0); position: relative; }
.ring::before { content: ''; position: absolute; inset: 9px; border-radius: 50%; background: #161616; }
.ring-num { position: relative; font-size: 20px; font-weight: 700; color: #f0f0f0; }
.ring-cap { position: relative; font-size: 11px; color: #999; }
.kb-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; flex: 1; }
.kb-s { background: #1d1d1d; border-radius: 8px; padding: 10px; text-align: center; }
.kb-s b { display: block; font-size: 18px; color: #f0f0f0; }
.kb-s span { font-size: 11px; color: #999; }

/* 知识库卡片 */
.kb-card { background: #161616 !important; border: 1px solid #2a2a2a !important; border-radius: 14px !important; margin-bottom: 14px; }
.kb-card :deep(.el-card__header) { background: #161616; border-bottom: 1px solid #2a2a2a; }
.kb-card :deep(.el-card__body) { background: #161616; }
.in-card-hdr { display: flex; justify-content: space-between; align-items: center; color: #f0f0f0; }
.in-hint { font-size: 12px; color: #999; }
.in-empty { text-align: center; color: #999; padding: 30px 0; font-size: 14px; }
.in-pending-item { padding: 12px 0; border-bottom: 1px solid #2a2a2a; }
.in-pending-item:last-child { border-bottom: none; }
.in-p-item-top { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
.in-p-question { font-size: 14px; color: #e0e0e0; flex: 1; }
.in-p-actions { margin-top: 8px; }
.in-edit { display: flex; gap: 8px; align-items: center; }
</style>
