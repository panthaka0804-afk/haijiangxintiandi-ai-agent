<template>
  <div class="intel-page">
    <!-- 1. RFM 会员分层 + 流失预警 -->
    <section class="panel">
      <div class="panel-head">
        <h2><span class="dot" style="background:#FF7B2C"></span>会员智能分层（RFM）+ 流失预警</h2>
        <button class="refresh" @click="loadRfm">刷新</button>
      </div>
      <div v-if="rfmLoading" class="loading">加载中…</div>
      <template v-else>
        <div class="stat-row">
          <div class="stat"><b>{{ rfm.total }}</b><span>会员总数</span></div>
          <div class="stat danger"><b>{{ rfm.churn_high }}</b><span>高流失风险</span></div>
          <div class="stat warn"><b>{{ rfm.churn_mid }}</b><span>中风险</span></div>
        </div>
        <div class="seg-chips">
          <span v-for="(cnt, seg) in rfm.segments" :key="seg" class="seg-chip" :style="{ '--c': segColor(seg) }">{{ seg }} · {{ cnt }}</span>
        </div>
        <div class="tbl">
          <div class="tr th">
            <span>会员</span><span>等级</span><span>R</span><span>F</span><span>M</span><span>分层</span><span>流失</span>
          </div>
          <div class="tr" v-for="(m, i) in rfm.list" :key="i">
            <span class="cell-member">{{ maskPhone(m.phone) }}<i v-if="m.name"> {{ m.name }}</i></span>
            <span>{{ m.level }}</span>
            <span class="score" :class="scoreCls(m.R)">{{ m.R }}</span>
            <span class="score" :class="scoreCls(m.F)">{{ m.F }}</span>
            <span class="score" :class="scoreCls(m.M)">{{ m.M }}</span>
            <span class="tag" :style="{ '--c': segColor(m.segment) }">{{ m.segment }}</span>
            <span class="tag" :style="{ '--c': churnColor(m.churn) }">{{ churnLabel(m.churn) }}</span>
          </div>
          <div v-if="!rfm.list.length" class="empty">暂无会员数据</div>
        </div>
      </template>
    </section>

    <!-- 2. 评价情感分析 -->
    <section class="panel">
      <div class="panel-head">
        <h2><span class="dot" style="background:#C9956C"></span>评价情感分析</h2>
        <span class="engine" :class="sent.engine === 'llm' ? 'on' : ''">{{ sent.engine === 'llm' ? '大模型驱动' : '词典兜底' }}</span>
        <button class="refresh" @click="loadSentiment">刷新</button>
      </div>
      <div v-if="sentLoading" class="loading">加载中…</div>
      <template v-else>
        <div class="stat-row wrap">
          <div class="stat"><b>{{ sent.total }}</b><span>评价样本</span></div>
          <div class="stat" v-for="(c, s) in sent.by_sentiment" :key="s" :style="{ '--c': sentColor(s) }">
            <b>{{ c }}</b><span>{{ s }}</span>
          </div>
        </div>
        <div class="topic-chips">
          <span v-for="(c, t) in sent.by_topic" :key="t" class="topic-chip">{{ t }} · {{ c }}</span>
        </div>
        <h3 class="sub">负面 / 投诉（{{ sent.negatives.length }}）</h3>
        <div class="neg-list">
          <div class="neg" v-for="(n, i) in sent.negatives" :key="i">
            <span class="tag" :style="{ '--c': sentColor(n.sentiment) }">{{ n.sentiment }}</span>
            <span class="tag gray">{{ n.topic }}</span>
            <span class="neg-text">{{ n.text || '（无文本）' }}</span>
            <span class="neg-meta">{{ n.rating }}★ · {{ fmtDate(n.created_at) }}</span>
          </div>
          <div v-if="!sent.negatives.length" class="empty">暂无负面评价 🎉</div>
        </div>
      </template>
    </section>

    <!-- 3. AI 经营日报 -->
    <section class="panel">
      <div class="panel-head">
        <h2><span class="dot" style="background:#C4923A"></span>AI 经营日报</h2>
        <span class="engine" :class="report.engine === 'llm' ? 'on' : ''">{{ report.engine === 'llm' ? '大模型生成' : '模板生成' }}</span>
        <button class="refresh" @click="loadReport">生成</button>
      </div>
      <div v-if="repLoading" class="loading">生成中…</div>
      <template v-else>
        <div class="report-paper">{{ report.report }}</div>
        <div class="metric-grid">
          <div class="metric" v-for="(v, k) in report.metrics" :key="k" v-show="k !== 'date'">
            <b>{{ v }}</b><span>{{ metricLabel(k) }}</span>
          </div>
        </div>
      </template>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getAdminRfm, getFeedbackSentiment, getDailyReport } from '@/api'

const rfm = ref({ total: 0, churn_high: 0, churn_mid: 0, segments: {}, list: [] })
const sent = ref({ engine: 'heuristic', total: 0, by_sentiment: {}, by_topic: {}, negatives: [] })
const report = ref({ engine: 'heuristic', report: '', metrics: {} })
const rfmLoading = ref(false)
const sentLoading = ref(false)
const repLoading = ref(false)

async function loadRfm() {
  rfmLoading.value = true
  const d = await getAdminRfm()
  if (d.ok) rfm.value = d.data
  rfmLoading.value = false
}
async function loadSentiment() {
  sentLoading.value = true
  const d = await getFeedbackSentiment()
  if (d.ok) sent.value = d.data
  sentLoading.value = false
}
async function loadReport() {
  repLoading.value = true
  const d = await getDailyReport()
  if (d.ok) report.value = d.data
  repLoading.value = false
}

onMounted(() => {
  loadRfm()
  loadSentiment()
  loadReport()
})

function maskPhone(p) {
  if (!p || p.length < 7) return p || '—'
  return p.slice(0, 3) + '****' + p.slice(-4)
}
function segColor(s) {
  return { '高价值': '#C4923A', '潜力客户': '#D4A59A', '新客活跃': '#C9956C', '稳定常客': '#6B6E64', '沉睡/流失风险': '#9B4A3E' }[s] || '#888'
}
function churnColor(c) {
  return { high: '#F56C6C', mid: '#E6A23C', low: '#67C23A' }[c] || '#888'
}
function churnLabel(c) {
  return { high: '高', mid: '中', low: '低' }[c] || c
}
function sentColor(s) {
  return { '正面': '#67C23A', '中性': '#909399', '负面': '#E6A23C', '投诉': '#F56C6C' }[s] || '#888'
}
function scoreCls(v) {
  return v >= 4 ? 's-good' : v >= 3 ? 's-mid' : 's-low'
}
function metricLabel(k) {
  return {
    total_members: '会员总数', new_members_week: '本周新增', active_members_week: '本周活跃',
    churn_risk_members: '流失风险', coupons_total: '券累计领', coupons_today: '今日领券',
    activities_open: '进行中活动', feedback_total: '评价总数', feedback_today: '今日评价',
    feedback_avg: '平均评分', low_feedback: '差评数'
  }[k] || k
}
function fmtDate(s) {
  if (!s) return ''
  return String(s).slice(0, 16)
}
</script>

<style scoped>
.intel-page { display: flex; flex-direction: column; gap: 18px; }
.panel {
  background: #0A0A0A; border: 1px solid #1A1A1A; border-radius: 14px;
  padding: 18px; box-shadow: 0 4px 18px rgba(0,0,0,0.4);
}
.panel-head { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.panel-head h2 { font-size: 16px; font-weight: 700; color: #F2F2F2; display: flex; align-items: center; gap: 8px; margin: 0; }
.dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; box-shadow: 0 0 8px currentColor; }
.refresh {
  margin-left: auto; padding: 6px 16px; border-radius: 8px; cursor: pointer;
  background: rgba(255,123,44,0.12); border: 1px solid rgba(255,123,44,0.5); color: #FF7B2C; font-size: 13px;
  transition: all .2s;
}
.refresh:hover { background: rgba(255,123,44,0.22); color: #FF8F47; }
.engine {
  font-size: 12px; padding: 3px 10px; border-radius: 999px; color: #8A8A8A;
  background: rgba(255,255,255,0.06); border: 1px solid #2A2A2A;
}
.engine.on { color: #FF7B2C; background: rgba(255,123,44,0.14); border-color: rgba(255,123,44,0.5); }
.loading { color: #999; padding: 30px 0; text-align: center; }

.stat-row { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 14px; }
.stat-row.wrap { margin-bottom: 10px; }
.stat {
  flex: 1; min-width: 110px; background: #111; border: 1px solid #1F1F1F; border-radius: 10px;
  padding: 12px 14px; --c: #FF7B2C;
}
.stat b { display: block; font-size: 24px; font-weight: 800; color: var(--c); }
.stat span { font-size: 12px; color: #999; }
.stat.danger { --c: #F56C6C; }
.stat.warn { --c: #E6A23C; }

.seg-chips, .topic-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
.seg-chip, .topic-chip {
  font-size: 13px; padding: 5px 12px; border-radius: 999px; color: #fff;
  background: color-mix(in srgb, var(--c) 22%, #111); border: 1px solid var(--c);
}
.topic-chip { color: #ddd; background: #141414; border-color: #2A2A2A; }

.tbl { border: 1px solid #1F1F1F; border-radius: 10px; overflow: hidden; }
.tr { display: grid; grid-template-columns: 2fr 1fr .5fr .5fr .5fr 1.4fr .8fr; align-items: center; gap: 6px; padding: 10px 12px; font-size: 13px; }
.tr.th { background: #141414; color: #aaa; font-weight: 600; }
.tr:not(.th):nth-child(even) { background: #0E0E0E; }
.cell-member { color: #E8E8E8; }
.cell-member i { color: #999; font-style: normal; font-size: 12px; }
.score { display: inline-flex; align-items: center; justify-content: center; width: 22px; height: 22px; border-radius: 50%; font-weight: 700; color: #fff; }
.score.s-good { background: #2E7D32; }
.score.s-mid { background: #B7791F; }
.score.s-low { background: #9B4A3E; }
.tag { font-size: 12px; padding: 3px 9px; border-radius: 999px; color: #fff; background: var(--c); white-space: nowrap; }
.tag.gray { background: #2A2A2A; color: #bbb; }

.sub { font-size: 14px; color: #ccc; margin: 6px 0 10px; }
.neg-list { display: flex; flex-direction: column; gap: 8px; }
.neg { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; background: #0E0E0E; border: 1px solid #1A1A1A; border-radius: 8px; padding: 9px 11px; }
.neg-text { flex: 1; min-width: 160px; color: #ddd; font-size: 13px; }
.neg-meta { font-size: 11px; color: #777; }

.report-paper {
  background: linear-gradient(180deg, #14110C, #0E0E0E); border: 1px solid rgba(196,146,58,0.35);
  border-radius: 10px; padding: 16px; color: #ECECEC; font-size: 14px; line-height: 1.8; white-space: pre-wrap;
}
.metric-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 10px; margin-top: 14px; }
.metric { background: #111; border: 1px solid #1F1F1F; border-radius: 10px; padding: 10px 12px; }
.metric b { display: block; font-size: 20px; font-weight: 800; color: #FF7B2C; }
.metric span { font-size: 12px; color: #999; }

.empty { color: #777; text-align: center; padding: 18px 0; font-size: 13px; }
</style>
