<template>
  <div class="intel-page">
    <!-- Tab 导航 -->
    <div class="tabs">
      <button v-for="t in tabs" :key="t.key" class="tab" :class="{ active: tab === t.key }" @click="tab = t.key">
        <span class="tdot" :style="{ background: t.color }"></span>{{ t.label }}
      </button>
    </div>

    <div v-if="loading" class="loading">智能运营数据加载中…</div>

    <!-- ============ 会员运营 ============ -->
    <div v-show="tab === 'member' && !loading">
      <!-- RFM -->
      <section class="panel">
        <div class="panel-head">
          <h2><span class="dot" style="background:#FF7B2C"></span>会员智能分层（RFM）+ 流失预警</h2>
          <button class="refresh" @click="loadAll">刷新</button>
        </div>
        <div class="stat-row">
          <div class="stat"><b>{{ rfm.total }}</b><span>会员总数</span></div>
          <div class="stat danger"><b>{{ rfm.churn_high }}</b><span>高流失风险</span></div>
          <div class="stat warn"><b>{{ rfm.churn_mid }}</b><span>中风险</span></div>
        </div>
        <div class="seg-chips">
          <span v-for="(cnt, seg) in rfm.segments" :key="seg" class="seg-chip" :style="{ '--c': segColor(seg) }">{{ seg }} · {{ cnt }}</span>
        </div>
        <div class="tbl">
          <div class="tr th"><span>会员</span><span>等级</span><span>R</span><span>F</span><span>M</span><span>分层</span><span>流失</span></div>
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
      </section>

      <!-- 一键召回名单 -->
      <section class="panel">
        <div class="panel-head"><h2><span class="dot" style="background:#9B4A3E"></span>一键召回名单（沉睡 / 流失风险）</h2></div>
        <div class="tbl">
          <div class="tr th"><span>会员</span><span>分层</span><span>流失</span><span>建议券</span><span>建议文案</span></div>
          <div class="tr" v-for="(m, i) in recall.list" :key="i">
            <span class="cell-member">{{ maskPhone(m.phone) }} <i>{{ m.name }}</i></span>
            <span class="tag" :style="{ '--c': segColor(m.segment) }">{{ m.segment }}</span>
            <span class="tag" :style="{ '--c': churnColor(m.churn) }">{{ churnLabel(m.churn) }}</span>
            <span class="coupon">{{ m.suggest_coupon }}</span>
            <span class="copy">{{ m.suggest_copy }}</span>
          </div>
          <div v-if="!recall.list.length" class="empty">暂无待召回会员 🎉</div>
        </div>
      </section>

      <!-- 高价值管家 -->
      <section class="panel">
        <div class="panel-head"><h2><span class="dot" style="background:#C4923A"></span>高价值会员管家 Top 20</h2></div>
        <div class="tbl">
          <div class="tr th"><span>会员</span><span>等级</span><span>累计消费</span><span>频次</span><span>偏好</span></div>
          <div class="tr" v-for="(m, i) in highValue.list" :key="i">
            <span class="cell-member">{{ maskPhone(m.phone) }} <i>{{ m.name }}</i></span>
            <span>{{ m.level }}</span>
            <span class="money">¥{{ m.monetary }}</span>
            <span>{{ m.freq }}</span>
            <span class="tag gray">{{ m.pref || '—' }}</span>
          </div>
          <div v-if="!highValue.list.length" class="empty">暂无消费记录</div>
        </div>
      </section>

      <!-- 等级跃迁 -->
      <section class="panel">
        <div class="panel-head"><h2><span class="dot" style="background:#D4A59A"></span>等级跃迁冲刺（临门一脚）</h2></div>
        <div class="tbl">
          <div class="tr th"><span>会员</span><span>当前</span><span>进度</span><span>差多少分</span><span>下一等级</span></div>
          <div class="tr" v-for="(m, i) in tierSprint.list" :key="i">
            <span class="cell-member">{{ maskPhone(m.phone) }} <i>{{ m.name }}</i></span>
            <span>{{ m.level }}</span>
            <span class="prog"><i :style="{ width: m.progress + '%' }"></i><b>{{ m.progress }}%</b></span>
            <span class="money">{{ m.gap }}</span>
            <span class="tag" :style="{ '--c': '#C4923A' }">{{ m.next_level }}</span>
          </div>
          <div v-if="!tierSprint.list.length" class="empty">暂无临近升级会员</div>
        </div>
      </section>

      <!-- 复购预测 -->
      <section class="panel">
        <div class="panel-head"><h2><span class="dot" style="background:#C9956C"></span>复购 / 到店预测（30 天内）</h2></div>
        <div class="tbl">
          <div class="tr th"><span>会员</span><span>上次消费</span><span>平均周期</span><span>预计下次</span><span>倒计时</span></div>
          <div class="tr" v-for="(m, i) in repurchase.list" :key="i">
            <span class="cell-member">{{ maskPhone(m.phone) }} <i>{{ m.name }}</i></span>
            <span>{{ m.last_buy }}</span>
            <span>{{ m.avg_gap }} 天</span>
            <span class="tag" :style="{ '--c': '#6B6E64' }">{{ m.predict_next }}</span>
            <span :class="m.due_in <= 7 ? 'due hot' : 'due'">{{ m.due_in }} 天</span>
          </div>
          <div v-if="!repurchase.list.length" class="empty">暂无足够消费记录</div>
        </div>
      </section>
    </div>

    <!-- ============ 口碑运营 ============ -->
    <div v-show="tab === 'reput' && !loading">
      <section class="panel">
        <div class="panel-head">
          <h2><span class="dot" style="background:#C9956C"></span>评价情感分析</h2>
          <span class="engine" :class="sent.engine === 'llm' ? 'on' : ''">{{ sent.engine === 'llm' ? '大模型驱动' : '词典兜底' }}</span>
          <button class="refresh" @click="loadAll">刷新</button>
        </div>
        <div class="stat-row wrap">
          <div class="stat"><b>{{ sent.total }}</b><span>评价样本</span></div>
          <div class="stat" v-for="(c, s) in sent.by_sentiment" :key="s" :style="{ '--c': sentColor(s) }"><b>{{ c }}</b><span>{{ s }}</span></div>
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
      </section>

      <!-- 差评告警 -->
      <section class="panel">
        <div class="panel-head"><h2><span class="dot" style="background:#F56C6C"></span>差评实时告警（≤2 星）</h2><span class="engine" v-if="alerts.list.length">待跟进 {{ alerts.list.length }}</span></div>
        <div class="neg-list">
          <div class="neg" v-for="(n, i) in alerts.list" :key="i">
            <span class="tag" :style="{ '--c': '#F56C6C' }">{{ n.age_hours >= 0 ? n.age_hours + 'h前' : '—' }}</span>
            <span class="neg-text">{{ n.text || '（无文本）' }}</span>
            <span class="neg-meta">{{ n.rating }}★ · {{ maskPhone(n.phone) }}</span>
            <button v-if="!n.followed_at" class="follow-btn" @click="followAlert(n.id)">标记跟进</button>
            <span v-else class="followed">已跟进 ✓</span>
          </div>
          <div v-if="!alerts.list.length" class="empty">暂无差评告警 🎉</div>
        </div>
      </section>

      <!-- 痛点聚类 -->
      <section class="panel">
        <div class="panel-head"><h2><span class="dot" style="background:#E6A23C"></span>痛点根因聚类</h2></div>
        <div class="rank-list">
          <div class="rank" v-for="(r, i) in painpoints.ranked" :key="i">
            <span class="rk">{{ i + 1 }}</span>
            <span class="rt">{{ r.topic }}</span>
            <span class="rc">{{ r.count }} 条</span>
            <span class="rbar"><i :style="{ width: (r.count / (painpoints.ranked[0]?.count || 1) * 100) + '%' }"></i></span>
          </div>
          <div v-if="!painpoints.ranked.length" class="empty">暂无负面主题</div>
        </div>
      </section>

      <!-- 商户情感榜 -->
      <section class="panel">
        <div class="panel-head"><h2><span class="dot" style="background:#8B8B90"></span>商户 / 品类情感榜</h2></div>
        <div class="tbl">
          <div class="tr th"><span>维度</span><span>样本</span><span>均分</span><span>差评率</span></div>
          <div class="tr" v-for="(m, i) in merchantSent.list" :key="i">
            <span>{{ m.dim }}</span><span>{{ m.cnt }}</span>
            <span :style="{ color: m.avg_rating >= 4 ? '#67C23A' : m.avg_rating >= 3 ? '#E6A23C' : '#F56C6C' }">{{ m.avg_rating }}</span>
            <span :class="m.neg_rate >= 30 ? 'neg-rate hot' : 'neg-rate'">{{ m.neg_rate }}%</span>
          </div>
          <div v-if="!merchantSent.list.length" class="empty">暂无评价分类</div>
        </div>
      </section>

      <!-- 口碑周趋势 -->
      <section class="panel">
        <div class="panel-head"><h2><span class="dot" style="background:#6B6E64"></span>口碑周趋势 + NPS（近 8 周）</h2></div>
        <div class="heat-row">
          <div class="wk" v-for="(w, i) in trend.weeks" :key="i">
            <span class="wk-nps" :style="{ color: w.nps >= 0 ? '#67C23A' : '#F56C6C' }">{{ w.nps }}</span>
            <span class="wk-bar"><i :style="{ height: (w.avg_rating / 5 * 100) + '%', background: w.avg_rating >= 4 ? '#67C23A' : w.avg_rating >= 3 ? '#E6A23C' : '#F56C6C' }"></i></span>
            <span class="wk-lab">{{ w.week.slice(5) }}</span>
          </div>
        </div>
      </section>
    </div>

    <!-- ============ 经营分析 ============ -->
    <div v-show="tab === 'biz' && !loading">
      <section class="panel">
        <div class="panel-head">
          <h2><span class="dot" style="background:#C4923A"></span>AI 经营日报</h2>
          <span class="engine" :class="report.engine === 'llm' ? 'on' : ''">{{ report.engine === 'llm' ? '大模型生成' : '模板生成' }}</span>
          <button class="refresh" @click="loadAll">生成</button>
        </div>
        <div class="report-paper">{{ report.report }}</div>
        <div class="metric-grid">
          <div class="metric" v-for="(v, k) in report.metrics" :key="k" v-show="k !== 'date'"><b>{{ v }}</b><span>{{ metricLabel(k) }}</span></div>
        </div>
      </section>

      <!-- 周/月报 -->
      <section class="panel">
        <div class="panel-head">
          <h2><span class="dot" style="background:#D4A59A"></span>周期经营报告</h2>
          <div class="seg-toggle">
            <button :class="{ on: period === 'weekly' }" @click="switchPeriod('weekly')">周报</button>
            <button :class="{ on: period === 'monthly' }" @click="switchPeriod('monthly')">月报</button>
          </div>
        </div>
        <div v-if="reportPeriod.report" class="report-paper">{{ reportPeriod.report }}</div>
        <div class="metric-grid">
          <div class="metric" v-for="(v, k) in reportPeriod.metrics" :key="k" v-show="k !== 'period'"><b>{{ v }}</b><span>{{ metricLabel(k) }}</span></div>
        </div>
      </section>

      <!-- 异常预警 -->
      <section class="panel">
        <div class="panel-head"><h2><span class="dot" style="background:#F56C6C"></span>异常指标自动预警</h2></div>
        <div class="alert-list">
          <div class="alert" v-for="(a, i) in anomaly.alerts" :key="i" :class="a.level">
            <span class="a-metric">{{ a.metric }}</span>
            <span class="a-val">今日 {{ a.today }} / 均值 {{ a.avg }}</span>
            <span class="a-pct">{{ a.pct }}%</span>
            <span class="a-tip">环比骤降，建议关注</span>
          </div>
          <div v-if="!anomaly.alerts.length" class="empty">各项指标平稳，无异常 🎉</div>
        </div>
      </section>

      <!-- KPI -->
      <section class="panel">
        <div class="panel-head"><h2><span class="dot" style="background:#FF7B2C"></span>KPI 目标完成率</h2></div>
        <div class="kpi-list">
          <div class="kpi" v-for="(k, i) in kpi.list" :key="i">
            <span class="k-name">{{ metricLabel(k.metric) }}</span>
            <span class="k-bar"><i :class="k.completion >= 100 ? 'full' : ''" :style="{ width: Math.min(k.completion, 100) + '%' }"></i></span>
            <span class="k-comp" :class="k.completion >= 100 ? 'ok' : ''">{{ k.completion }}%</span>
            <span class="k-target"><input type="number" v-model="k.target" @change="saveKpi(k)" /> 目标</span>
          </div>
        </div>
      </section>

      <!-- 活动 ROI -->
      <section class="panel">
        <div class="panel-head"><h2><span class="dot" style="background:#C9956C"></span>活动 ROI 估算</h2></div>
        <div class="tbl">
          <div class="tr th"><span>活动</span><span>报名</span><span>满员率</span><span>预估产出</span><span>状态</span></div>
          <div class="tr" v-for="(a, i) in activityRoi.list" :key="i">
            <span class="cell-member">{{ a.title }}</span>
            <span>{{ a.enrolled }}/{{ a.max_people }}</span>
            <span :class="a.full_rate >= 80 ? 'ok' : ''">{{ a.full_rate }}%</span>
            <span class="money">¥{{ a.est_revenue }}</span>
            <span class="tag gray">{{ a.status }}</span>
          </div>
          <div v-if="!activityRoi.list.length" class="empty">暂无活动</div>
        </div>
      </section>
    </div>

    <!-- ============ 智能助手 ============ -->
    <div v-show="tab === 'assist' && !loading">
      <!-- AI 推送文案 -->
      <section class="panel">
        <div class="panel-head"><h2><span class="dot" style="background:#FF7B2C"></span>AI 推送文案生成</h2></div>
        <div class="form-row">
          <input v-model="pc.segment" placeholder="面向会员（如 流失风险会员）" />
          <input v-model="pc.theme" placeholder="主题（如 回来看看专属券）" />
          <select v-model="pc.channel"><option>短信</option><option>企微</option><option>APP Push</option></select>
          <button class="refresh" @click="genCopy">生成</button>
        </div>
        <div v-if="pushCopy" class="report-paper">{{ pushCopy }}<span class="engine" :class="pushEngine === 'llm' ? 'on' : ''">{{ pushEngine === 'llm' ? '大模型' : '模板' }}</span></div>
      </section>

      <!-- 经营参谋 -->
      <section class="panel">
        <div class="panel-head"><h2><span class="dot" style="background:#C4923A"></span>经营参谋（自然语言问答）</h2></div>
        <div class="form-row">
          <input v-model="qa.question" placeholder="例如：最近流失会员有多少？差评情况如何？" @keyup.enter="askAdvisor" />
          <button class="refresh" @click="askAdvisor">提问</button>
        </div>
        <div v-if="advisorAns" class="report-paper">{{ advisorAns }}</div>
      </section>

      <!-- 智能招商 -->
      <section class="panel">
        <div class="panel-head"><h2><span class="dot" style="background:#8B8B90"></span>智能招商建议</h2></div>
        <div class="sug-list">
          <div class="sug" v-for="(s, i) in leasing.suggestions" :key="i">
            <span class="tag" :style="{ '--c': '#C4923A' }">{{ s.category }}</span>
            <span>需求 {{ s.demand }} · 现有门店 {{ s.shops_now }}</span>
            <span class="sug-advice">{{ s.advice }}</span>
          </div>
          <div v-if="!leasing.suggestions.length" class="empty">暂无明确招商缺口</div>
        </div>
        <div class="dist">
          <span class="dist-lab">品类门店分布：</span>
          <span v-for="(c, k) in leasing.shop_category_dist" :key="k" class="topic-chip">{{ k }} · {{ c }}</span>
        </div>
      </section>

      <!-- 营销日历 -->
      <section class="panel">
        <div class="panel-head"><h2><span class="dot" style="background:#D4A59A"></span>营销日历（未来 14 天）</h2></div>
        <div class="cal-list">
          <div class="cal" v-for="(e, i) in calendar.events" :key="i">
            <span class="cal-date">{{ e.date.slice(5) }}</span>
            <span class="tag" :style="{ '--c': calColor(e.type) }">{{ e.type }}</span>
            <span class="cal-mem">{{ e.member }}</span>
          </div>
          <div v-if="!calendar.events.length" class="empty">未来 14 天暂无排期</div>
        </div>
      </section>

      <!-- 时段冷热 -->
      <section class="panel">
        <div class="panel-head"><h2><span class="dot" style="background:#6B6E64"></span>时段冷热热力（消费记录）</h2><span class="engine" v-if="heat.peak_hour >= 0">高峰 {{ heat.peak_hour }}:00</span></div>
        <div class="heat-row">
          <div class="hc" v-for="(h, i) in heat.heat" :key="i">
            <span class="hc-bar"><i :style="{ height: (h / (Math.max(...heat.heat) || 1) * 100) + '%' }"></i></span>
            <span class="hc-lab">{{ i }}</span>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import {
  getAdminRfm, getFeedbackSentiment, getDailyReport,
  getRecallCandidates, getRepurchase, getHighValue, getTierSprint,
  getFeedbackAlerts, followFeedbackAlert, getFeedbackPainpoints, getMerchantSentiment, getFeedbackTrend,
  getReportPeriod, getAnomaly, getKpi, updateKpi, getActivityRoi,
  getPushCopy, getAdvisor, getLeasing, getMarketingCalendar, getTimeslotHeat
} from '@/api'

const tab = ref('member')
const tabs = [
  { key: 'member', label: '会员运营', color: '#FF7B2C' },
  { key: 'reput', label: '口碑运营', color: '#C9956C' },
  { key: 'biz', label: '经营分析', color: '#C4923A' },
  { key: 'assist', label: '智能助手', color: '#8B8B90' }
]
const loading = ref(true)
const period = ref('weekly')

// 数据
const rfm = ref({ total: 0, churn_high: 0, churn_mid: 0, segments: {}, list: [] })
const sent = ref({ engine: 'heuristic', total: 0, by_sentiment: {}, by_topic: {}, negatives: [] })
const report = ref({ engine: 'heuristic', report: '', metrics: {} })
const recall = ref({ list: [] })
const repurchase = ref({ list: [] })
const highValue = ref({ list: [] })
const tierSprint = ref({ list: [] })
const alerts = ref({ list: [] })
const painpoints = ref({ ranked: [], list: [] })
const merchantSent = ref({ list: [] })
const trend = ref({ weeks: [] })
const reportPeriod = ref({ report: '', metrics: {}, engine: 'heuristic' })
const anomaly = ref({ alerts: [] })
const kpi = ref({ list: [] })
const activityRoi = ref({ list: [] })
const leasing = ref({ suggestions: [], shop_category_dist: {}, topic_demand: {} })
const calendar = ref({ events: [] })
const heat = ref({ heat: [], peak_hour: -1 })

// 助手
const pc = reactive({ segment: '流失风险会员', theme: '回来看看专属券', channel: '短信' })
const pushCopy = ref('')
const pushEngine = ref('')
const qa = reactive({ question: '' })
const advisorAns = ref('')

async function loadAll() {
  loading.value = true
  const [
    a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r
  ] = await Promise.all([
    getAdminRfm(), getFeedbackSentiment(), getDailyReport(),
    getRecallCandidates(), getRepurchase(), getHighValue(), getTierSprint(),
    getFeedbackAlerts(), getFeedbackPainpoints(), getMerchantSentiment(), getFeedbackTrend(),
    getReportPeriod(period.value), getAnomaly(), getKpi(), getActivityRoi(),
    getLeasing(), getMarketingCalendar(), getTimeslotHeat()
  ])
  if (a.ok) rfm.value = a.data
  if (b.ok) sent.value = b.data
  if (c.ok) report.value = c.data
  if (d.ok) recall.value = d.data
  if (e.ok) repurchase.value = e.data
  if (f.ok) highValue.value = f.data
  if (g.ok) tierSprint.value = g.data
  if (h.ok) alerts.value = h.data
  if (i.ok) painpoints.value = i.data
  if (j.ok) merchantSent.value = j.data
  if (k.ok) trend.value = k.data
  if (l.ok) reportPeriod.value = l.data
  if (m.ok) anomaly.value = m.data
  if (n.ok) kpi.value = n.data
  if (o.ok) activityRoi.value = o.data
  if (p.ok) leasing.value = p.data
  if (q.ok) calendar.value = q.data
  if (r.ok) heat.value = r.data
  loading.value = false
}

async function switchPeriod(p) {
  period.value = p
  const d = await getReportPeriod(p)
  if (d.ok) reportPeriod.value = d.data
}

async function followAlert(id) {
  await followFeedbackAlert(id)
  const d = await getFeedbackAlerts()
  if (d.ok) alerts.value = d.data
}

async function saveKpi(k) {
  await updateKpi(k.metric, k.target)
  const d = await getKpi()
  if (d.ok) kpi.value = d.data
}

async function genCopy() {
  const d = await getPushCopy({ ...pc })
  if (d.ok) { pushCopy.value = d.data.copy; pushEngine.value = d.data.engine }
}

async function askAdvisor() {
  if (!qa.question.trim()) return
  const d = await getAdvisor(qa.question)
  if (d.ok) advisorAns.value = d.data.answer
}

onMounted(loadAll)

// ---- helpers ----
function maskPhone(p) { if (!p || p.length < 7) return p || '—'; return p.slice(0, 3) + '****' + p.slice(-4) }
function segColor(s) { return { '高价值': '#C4923A', '潜力客户': '#D4A59A', '新客活跃': '#C9956C', '稳定常客': '#6B6E64', '沉睡/流失风险': '#9B4A3E' }[s] || '#888' }
function churnColor(c) { return { high: '#F56C6C', mid: '#E6A23C', low: '#67C23A' }[c] || '#888' }
function churnLabel(c) { return { high: '高', mid: '中', low: '低' }[c] || c }
function sentColor(s) { return { '正面': '#67C23A', '中性': '#909399', '负面': '#E6A23C', '投诉': '#F56C6C' }[s] || '#888' }
function scoreCls(v) { return v >= 4 ? 's-good' : v >= 3 ? 's-mid' : 's-low' }
function calColor(t) {
  if (t.includes('生日')) return '#D4A59A'
  if (t.includes('周年')) return '#C4923A'
  if (t.includes('会员日')) return '#FF7B2C'
  if (t.includes('活动')) return '#C9956C'
  return '#8B8B90'
}
function metricLabel(k) {
  return {
    total_members: '会员总数', new_members_week: '本周新增', active_members_week: '本周活跃',
    churn_risk_members: '流失风险', coupons_total: '券累计领', coupons_today: '今日领券',
    activities_open: '进行中活动', feedback_total: '评价总数', feedback_today: '今日评价',
    feedback_avg: '平均评分', low_feedback: '差评数', new_members: '新增', active_members: '活跃', coupons: '领券'
  }[k] || k
}
function fmtDate(s) { if (!s) return ''; return String(s).slice(0, 16) }
</script>

<style scoped>
.intel-page { display: flex; flex-direction: column; gap: 18px; }
.tabs { display: flex; gap: 8px; flex-wrap: wrap; }
.tab {
  display: flex; align-items: center; gap: 6px; padding: 8px 16px; border-radius: 10px; cursor: pointer;
  background: #0A0A0A; border: 1px solid #1A1A1A; color: #BBB; font-size: 14px; transition: all .2s;
}
.tab:hover { color: #EEE; border-color: #2A2A2A; }
.tab.active { background: rgba(255,123,44,0.14); border-color: rgba(255,123,44,0.5); color: #FF8F47; }
.tdot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; box-shadow: 0 0 8px currentColor; }

.panel { background: #0A0A0A; border: 1px solid #1A1A1A; border-radius: 14px; padding: 18px; box-shadow: 0 4px 18px rgba(0,0,0,0.4); }
.panel-head { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.panel-head h2 { font-size: 16px; font-weight: 700; color: #F2F2F2; display: flex; align-items: center; gap: 8px; margin: 0; }
.dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; box-shadow: 0 0 8px currentColor; }
.refresh { margin-left: auto; padding: 6px 16px; border-radius: 8px; cursor: pointer; background: rgba(255,123,44,0.12); border: 1px solid rgba(255,123,44,0.5); color: #FF7B2C; font-size: 13px; transition: all .2s; }
.refresh:hover { background: rgba(255,123,44,0.22); color: #FF8F47; }
.engine { font-size: 12px; padding: 3px 10px; border-radius: 999px; color: #8A8A8A; background: rgba(255,255,255,0.06); border: 1px solid #2A2A2A; }
.engine.on { color: #FF7B2C; background: rgba(255,123,44,0.14); border-color: rgba(255,123,44,0.5); }
.loading { color: #999; padding: 40px 0; text-align: center; }

.stat-row { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 14px; }
.stat { min-width: 92px; padding: 12px 14px; border-radius: 12px; background: #111; border: 1px solid #1F1F1F; display: flex; flex-direction: column; gap: 4px; }
.stat b { font-size: 22px; color: #F2F2F2; }
.stat span { font-size: 12px; color: #999; }
.stat.danger b { color: #F56C6C; } .stat.warn b { color: #E6A23C; }

.seg-chips, .topic-chips, .dist { display: flex; gap: 8px; flex-wrap: wrap; margin: 8px 0 14px; }
.seg-chip, .topic-chip { font-size: 12px; padding: 4px 12px; border-radius: 999px; color: #E8E8E8; background: color-mix(in srgb, var(--c) 18%, #111); border: 1px solid color-mix(in srgb, var(--c) 45%, #1A1A1A); }

.tbl { display: flex; flex-direction: column; }
.tr { display: grid; grid-template-columns: 2.4fr 1fr 0.7fr 0.7fr 0.7fr 1.4fr 0.8fr; gap: 8px; align-items: center; padding: 9px 6px; border-bottom: 1px solid #161616; font-size: 13px; color: #DDD; }
.tr.th { color: #888; font-size: 12px; border-bottom: 1px solid #262626; }
.cell-member { color: #F2F2F2; } .cell-member i { color: #BBB; font-style: normal; font-size: 12px; }
.money { color: #C4923A; font-weight: 600; }
.score { text-align: center; font-weight: 700; } .score.s-good { color: #67C23A; } .score.s-mid { color: #E6A23C; } .score.s-low { color: #F56C6C; }
.tag { font-size: 11px; padding: 2px 9px; border-radius: 999px; color: #EEE; background: color-mix(in srgb, var(--c) 22%, #111); border: 1px solid color-mix(in srgb, var(--c) 50%, #1A1A1A); justify-self: start; }
.tag.gray { --c: #8B8B90; }
.coupon { color: #D4A59A; font-size: 12px; } .copy { color: #AAA; font-size: 12px; line-height: 1.4; }
.prog { position: relative; height: 16px; background: #1A1A1A; border-radius: 8px; overflow: hidden; }
.prog i { position: absolute; left: 0; top: 0; bottom: 0; background: linear-gradient(90deg, #C4923A, #FF7B2C); }
.prog b { position: absolute; right: 6px; top: 0; font-size: 10px; color: #FFF; line-height: 16px; }
.due { font-size: 12px; color: #999; } .due.hot { color: #F56C6C; font-weight: 700; }

.sub { font-size: 14px; color: #CCC; margin: 14px 0 8px; }
.neg-list { display: flex; flex-direction: column; gap: 8px; }
.neg { display: flex; align-items: center; gap: 10px; padding: 10px; background: #111; border: 1px solid #1C1C1C; border-radius: 10px; flex-wrap: wrap; }
.neg-text { color: #EEE; font-size: 13px; flex: 1; min-width: 160px; }
.neg-meta { color: #888; font-size: 12px; }
.follow-btn { padding: 4px 12px; border-radius: 7px; cursor: pointer; background: rgba(245,108,108,0.14); border: 1px solid rgba(245,108,108,0.5); color: #F56C6C; font-size: 12px; }
.followed { color: #67C23A; font-size: 12px; }

.rank-list { display: flex; flex-direction: column; gap: 8px; }
.rank { display: grid; grid-template-columns: 28px 110px 60px 1fr; gap: 10px; align-items: center; font-size: 13px; color: #DDD; }
.rk { width: 22px; height: 22px; border-radius: 50%; background: #1A1A1A; color: #FF8F47; text-align: center; line-height: 22px; font-size: 12px; }
.rt { color: #F2F2F2; } .rc { color: #999; }
.rbar { height: 8px; background: #1A1A1A; border-radius: 4px; overflow: hidden; }
.rbar i { display: block; height: 100%; background: linear-gradient(90deg, #E6A23C, #F56C6C); }

.neg-rate { color: #67C23A; } .neg-rate.hot { color: #F56C6C; font-weight: 700; }

.heat-row { display: flex; gap: 6px; align-items: flex-end; height: 90px; }
.wk { display: flex; flex-direction: column; align-items: center; gap: 4px; flex: 1; }
.wk-nps { font-size: 12px; font-weight: 700; }
.wk-bar { width: 16px; height: 48px; background: #1A1A1A; border-radius: 4px; display: flex; align-items: flex-end; overflow: hidden; }
.wk-bar i { width: 100%; border-radius: 4px; }
.wk-lab { font-size: 10px; color: #888; }

.report-paper { white-space: pre-wrap; line-height: 1.7; color: #EAEAEA; background: #111; border: 1px solid #1E1E1E; border-radius: 12px; padding: 16px; font-size: 14px; margin-bottom: 14px; }
.metric-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); gap: 10px; }
.metric { padding: 12px; border-radius: 10px; background: #111; border: 1px solid #1F1F1F; display: flex; flex-direction: column; gap: 4px; }
.metric b { font-size: 18px; color: #F2F2F2; } .metric span { font-size: 12px; color: #999; }

.seg-toggle { margin-left: auto; display: flex; gap: 4px; }
.seg-toggle button { padding: 5px 14px; border-radius: 8px; cursor: pointer; background: #111; border: 1px solid #1F1F1F; color: #999; font-size: 13px; }
.seg-toggle button.on { background: rgba(255,123,44,0.14); border-color: rgba(255,123,44,0.5); color: #FF8F47; }

.alert-list { display: flex; flex-direction: column; gap: 8px; }
.alert { display: grid; grid-template-columns: 110px 1fr 70px 1.4fr; gap: 10px; align-items: center; padding: 10px 12px; border-radius: 10px; background: #111; border: 1px solid #1C1C1C; font-size: 13px; color: #DDD; }
.alert.high { border-color: rgba(245,108,108,0.5); }
.alert.mid { border-color: rgba(230,162,60,0.4); }
.a-metric { color: #F2F2F2; font-weight: 600; } .a-pct { color: #F56C6C; font-weight: 700; } .a-tip { color: #999; font-size: 12px; }

.kpi-list { display: flex; flex-direction: column; gap: 10px; }
.kpi { display: grid; grid-template-columns: 120px 1fr 70px 160px; gap: 12px; align-items: center; font-size: 13px; color: #DDD; }
.k-name { color: #F2F2F2; } .k-bar { height: 12px; background: #1A1A1A; border-radius: 6px; overflow: hidden; }
.k-bar i { display: block; height: 100%; background: linear-gradient(90deg, #C4923A, #FF7B2C); }
.k-bar i.full { background: linear-gradient(90deg, #67C23A, #9BE15D); }
.k-comp { color: #E6A23C; font-weight: 700; } .k-comp.ok { color: #67C23A; }
.k-target { color: #999; font-size: 12px; display: flex; align-items: center; gap: 6px; }
.k-target input { width: 64px; background: #111; border: 1px solid #2A2A2A; border-radius: 6px; color: #EEE; padding: 4px 8px; font-size: 12px; }

.form-row { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
.form-row input, .form-row select { flex: 1; min-width: 140px; background: #111; border: 1px solid #2A2A2A; border-radius: 8px; color: #EEE; padding: 9px 12px; font-size: 13px; }

.sug-list { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }
.sug { display: flex; align-items: center; gap: 10px; padding: 10px; background: #111; border: 1px solid #1C1C1C; border-radius: 10px; font-size: 13px; color: #DDD; flex-wrap: wrap; }
.sug-advice { color: #C4923A; margin-left: auto; }
.dist-lab { color: #999; font-size: 12px; }

.cal-list { display: flex; flex-direction: column; gap: 6px; }
.cal { display: flex; align-items: center; gap: 10px; padding: 8px 10px; background: #111; border: 1px solid #1C1C1C; border-radius: 9px; font-size: 13px; color: #DDD; }
.cal-date { color: #FF8F47; font-weight: 600; font-size: 12px; } .cal-mem { color: #BBB; font-size: 12px; }

.hc { display: flex; flex-direction: column; align-items: center; gap: 4px; flex: 1; }
.hc-bar { width: 14px; height: 60px; background: #1A1A1A; border-radius: 4px; display: flex; align-items: flex-end; overflow: hidden; }
.hc-bar i { width: 100%; background: linear-gradient(0deg, #6B6E64, #FF7B2C); border-radius: 4px; }
.hc-lab { font-size: 10px; color: #888; }

.empty { color: #777; font-size: 13px; padding: 14px 0; text-align: center; }
</style>
