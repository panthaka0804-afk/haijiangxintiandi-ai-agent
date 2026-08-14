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

    <!-- 执行闭环结果横幅：点选建议执行后展示，跳转触达日志 -->
    <div class="exec-banner" v-if="lastExec" @click="goNotify">
      ✅ 已推送 <b>{{ lastExec.pushed }}</b> 条「{{ execLabel(lastExec.key) }}」短信 · 点击前往触达中心查看日志 →
    </div>

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
            <div class="alert-title">{{ a.title }} <span v-if="isAlertHandled(a.title)" class="handled-tag">已处理</span></div>
            <div class="alert-detail">{{ a.detail }}</div>
          </div>
          <button v-if="!isAlertHandled(a.title)" class="alert-handle" @click="handleAlert(a)">一键处置</button>
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
          <div class="suggest-act" v-if="s.action === 'send-coupon'">
            <span v-if="isSugExecuted(s.key)" class="done-tag">已执行 ✓</span>
            <span v-else>群发定向券 →</span>
          </div>
          <div class="suggest-act" v-else>{{ s.target ? '前往处理 →' : '在此补充 ↓' }}</div>
        </div>
      </div>
    </section>

    <!-- H. AI 对话洞察反哺（客服小江到底在答什么 / 哪些没答上） -->
    <section class="mc-card mc-card-blue panel">
      <div class="panel-head">
        <h2><span class="dot" style="background:#4A90D9"></span>AI 对话洞察（客服小江在答什么）</h2>
        <span class="engine" v-if="chatTotal">样本 {{ chatTotal }} 条</span>
        <span class="engine" v-else>暂无</span>
      </div>
      <div v-if="!chatTotal" class="empty">暂无对话数据（可在看板「种入演示数据」后查看真实分布）</div>
      <div v-else class="chat-top">
        <div class="chat-col">
          <div class="chat-col-h">🔥 高频提问 Top10</div>
          <div class="topic-list">
            <div class="topic-item" v-for="(t, i) in (insights.chat_topics || []).slice(0, 10)" :key="i">
              <span class="topic-rank">{{ i + 1 }}</span>
              <span class="topic-q" :title="t.question">{{ t.question }}</span>
              <span class="topic-cnt">{{ t.count }}</span>
            </div>
          </div>
        </div>
        <div class="chat-col">
          <div class="chat-col-h">🩺 AI 答不上的</div>
          <div class="unans-box" :class="{ clickable: (insights.unanswered_count || 0) > 0 }" @click="goKb">
            <div class="unans-num">{{ insights.unanswered_count || 0 }}</div>
            <div class="unans-lab">待优化问题（点击去知识库补充）</div>
          </div>
          <button class="recall-btn" @click="exportRecall">导出沉默召回名单 CSV</button>
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

    <!-- I. 商户情感榜（真实商户维度） -->
    <section class="mc-card mc-card-pink panel">
      <div class="panel-head">
        <h2><span class="dot" style="background:#D4A59A"></span>商户情感榜（差评风险排序）</h2>
        <button class="export-mini" @click="exportSentiment">导出 CSV</button>
        <span class="engine ok" v-if="merchantSentiment.real">真实数据</span>
        <span class="engine" v-else>暂无</span>
      </div>
      <div v-if="!merchantSentiment.list.length" class="empty">暂无评价数据</div>
      <div v-else class="sent-list">
        <div v-for="(m, i) in merchantSentiment.list.slice(0, 8)" :key="m.shop_id || i" class="sent-item">
          <div class="sent-rank">{{ i + 1 }}</div>
          <div class="sent-body">
            <div class="sent-name">{{ m.shop_name }} <span class="sent-cat" v-if="m.category">{{ m.category }}</span></div>
            <div class="sent-sub">评价 {{ m.cnt }} 条 · 差评率 {{ m.neg_rate }}%</div>
          </div>
          <div class="sent-score" :class="scoreCls(m.avg_rating)">{{ m.avg_rating }}</div>
        </div>
      </div>
      <div class="cat-row" v-if="merchantSentiment.by_category.length">
        <span class="cat-chip" v-for="c in merchantSentiment.by_category.slice(0, 6)" :key="c.category">{{ c.category }} 差评{{ c.neg_rate }}%</span>
      </div>
    </section>

    <!-- J. 活动 ROI（真实核销金额） -->
    <section class="mc-card mc-card-gold panel">
      <div class="panel-head"><h2><span class="dot" style="background:#C4923A"></span>活动 ROI（真实核销金额）</h2></div>
      <div v-if="!activityRoi.list.length" class="empty">暂无活动数据</div>
      <div v-else class="roi-list">
        <div v-for="(a, i) in activityRoi.list" :key="a.id" class="roi-item">
          <div class="roi-body">
            <div class="roi-name">{{ a.title }} <span class="roi-status" v-if="a.status">{{ a.status }}</span></div>
            <div class="roi-sub">报名 {{ a.enrolled }} 人 · 核销 {{ a.redeem_count }} 次 · 核销金额 ¥{{ a.redeem_amount }}</div>
          </div>
          <div class="roi-roi" :class="a.real ? 'good' : 'flat'">{{ a.real ? 'ROI ' + a.roi : 'ROI —' }}</div>
        </div>
      </div>
    </section>

    <!-- 群发定向券弹窗（从建议直接发起动作） -->
    <el-dialog v-model="showCouponDialog" title="群发定向券" width="440px">
      <div class="coupon-form">
        <label>券说明</label>
        <el-input v-model="couponForm.label" placeholder="如：回来看看·满50减10" />
        <label>面额（元）</label>
        <el-input v-model="couponForm.amount" type="number" placeholder="30" />
        <label>有效期至</label>
        <el-input v-model="couponForm.expire" placeholder="2026-12-31" />
        <label>目标人群</label>
        <el-select v-model="couponForm.target_level" placeholder="全部会员" style="width: 100%;">
          <el-option label="全部会员" value="" />
          <el-option label="普通会员" value="普通会员" />
          <el-option label="高级会员（金卡/钻石）" value="高级会员" />
        </el-select>
      </div>
      <template #footer>
        <el-button @click="showCouponDialog = false">取消</el-button>
        <el-button type="primary" :loading="submittingCoupon" @click="submitCoupon">创建并推送</el-button>
      </template>
    </el-dialog>

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
import { getMerchantSentiment, getActivityRoi, handleInsightAlert, execInsightSuggestion, createOffer, getRecallList } from '@/api'
import { exportCsv } from '@/utils/export'

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

const merchantSentiment = reactive({ list: [], by_category: [], real: false })
const activityRoi = reactive({ list: [] })
const handledAlerts = ref([])
const executedSuggestions = ref([])
const showCouponDialog = ref(false)
const couponKey = ref('')
const couponForm = reactive({ label: '', amount: 30, expire: '2026-12-31', target_level: '' })
const submittingCoupon = ref(false)
const lastExec = ref(null)

function goKb() { router.push({ name: 'admin-kb' }) }
function goNotify() { router.push({ name: 'admin-notify' }) }
function execLabel(k) { return ({ silent_recall: '沉默召回', redeem_boost: '核销提醒' })[k] || '定向' }
function dateStr() {
  const d = new Date()
  const p = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}`
}
const chatTotal = computed(() => (insights.chat_topics || []).reduce((a, t) => a + (t.count || 0), 0))

async function exportRecall() {
  try {
    const d = await getRecallList()
    if (d.ok && d.list && d.list.length) {
      const rows = d.list.map(m => ({ 手机号: m.phone, 姓名: m.name, 等级: m.level, 最后到店: m.last_visit, 沉默天数: m.silent_days }))
      if (!exportCsv(rows, `沉默召回名单_${dateStr()}.csv`,
        [{ key: '手机号', title: '手机号' }, { key: '姓名', title: '姓名' }, { key: '等级', title: '等级' }, { key: '最后到店', title: '最后到店' }, { key: '沉默天数', title: '沉默天数' }])) {
        ElMessage.warning('暂无沉默会员')
      }
    } else ElMessage.warning('暂无沉默会员')
  } catch { ElMessage.error('导出失败') }
}
function exportSentiment() {
  const rows = merchantSentiment.list.map(m => ({ 商户: m.shop_name, 分类: m.category || '', 评价数: m.cnt, 差评率: m.neg_rate + '%', 均分: m.avg_rating }))
  if (!exportCsv(rows, `商户情感榜_${dateStr()}.csv`,
    [{ key: '商户', title: '商户' }, { key: '分类', title: '分类' }, { key: '评价数', title: '评价数' }, { key: '差评率', title: '差评率' }, { key: '均分', title: '均分' }])) {
    ElMessage.warning('暂无评价数据')
  }
}

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

function scoreCls(v) {
  if (v == null) return 'flat'
  if (v >= 4) return 'good'
  if (v <= 3) return 'bad'
  return 'flat'
}

function runSuggestion(s) {
  if (s.action === 'send-coupon') { openSendCoupon(s); return }
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
    if (d.ok) {
      Object.assign(insights, d.data)
      handledAlerts.value = d.data.handled_alerts || []
      executedSuggestions.value = d.data.executed_suggestions || []
    }
  } catch {}
  loading.value = false
}

async function loadSentiment() {
  try {
    const d = await getMerchantSentiment()
    if (d.ok) {
      merchantSentiment.list = d.data.list || []
      merchantSentiment.by_category = d.data.by_category || []
      merchantSentiment.real = !!d.data.real
    }
  } catch {}
}

async function loadRoi() {
  try {
    const d = await getActivityRoi()
    if (d.ok) activityRoi.list = d.data.list || []
  } catch {}
}

async function handleAlert(a) {
  try {
    const d = await handleInsightAlert(a.title)
    if (d.ok) { handledAlerts.value.push(a.title); ElMessage.success('已标记为处理') }
    else ElMessage.error(d.error || '操作失败')
  } catch { ElMessage.error('操作失败') }
}

function openSendCoupon(s) {
  couponKey.value = s.key || ''
  couponForm.label = ''
  couponForm.amount = 30
  couponForm.expire = '2026-12-31'
  couponForm.target_level = ''
  showCouponDialog.value = true
}

async function submitCoupon() {
  if (!couponForm.label.trim()) return ElMessage.warning('请填写券说明')
  if (!couponForm.amount || Number(couponForm.amount) <= 0) return ElMessage.warning('请填写有效面额')
  submittingCoupon.value = true
  try {
    const d = await createOffer({
      shop_name: '海江新天地', label: couponForm.label.trim(), amount: Number(couponForm.amount),
      expire: couponForm.expire, category: 'food', color: '#FF7B2C', status: 'active',
      target_level: couponForm.target_level
    })
    if (d.ok) {
      ElMessage.success('定向券已创建并上架')
      if (couponKey.value) {
        const ex = await execInsightSuggestion(couponKey.value)
        if (ex.ok) {
          executedSuggestions.value.push(couponKey.value)
          lastExec.value = { key: couponKey.value, pushed: ex.pushed || 0, target: ex.target || '/admin/notify' }
          ElMessage.success(`已推送 ${ex.pushed || 0} 条，前往触达中心查看日志`)
        }
      }
      showCouponDialog.value = false
    } else ElMessage.error(d.error || '创建失败')
  } catch { ElMessage.error('操作失败') }
  submittingCoupon.value = false
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
  loadSentiment()
  loadRoi()
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

function isAlertHandled(t) { return handledAlerts.value.includes(t) }
function isSugExecuted(k) { return executedSuggestions.value.includes(k) }

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
.mc-card-blue::before { --mc-bar: #4A90D9; }

.panel-head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.panel-head h2 { margin: 0; font-size: 15px; color: #f0f0f0; font-weight: 600; display: flex; align-items: center; gap: 8px; }
.dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
.engine { margin-left: auto; font-size: 12px; color: #BABABA; background: #222; padding: 3px 10px; border-radius: 20px; }
.engine.ok { color: #A9BBA0; background: rgba(107,110,100,0.2); }
.engine.warn { color: #E3BB6A; background: rgba(196,146,58,0.18); }
.empty { color: #777; font-size: 13px; padding: 16px 0; text-align: center; }

/* 执行闭环结果横幅 */
.exec-banner { background: linear-gradient(90deg, rgba(62,142,65,0.18), rgba(62,142,65,0)); border: 1px solid rgba(62,142,65,0.4); color: #C9E6CB; border-radius: 10px; padding: 11px 14px; font-size: 13px; margin-bottom: 14px; cursor: pointer; transition: .15s; }
.exec-banner:hover { background: rgba(62,142,65,0.22); }
.exec-banner b { color: #A9E0AC; font-size: 15px; }

/* 导出小按钮（面板头内） */
.export-mini { margin-left: 10px; padding: 4px 12px; border: 1px solid #3a3a3a; border-radius: 14px; font-size: 12px; font-weight: 600; color: #E3BB6A; background: #202020; cursor: pointer; transition: .15s; }
.export-mini:hover { border-color: #E3BB6A; }

/* AI 对话洞察 */
.chat-top { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.chat-col-h { font-size: 13px; color: #cdd8e6; margin-bottom: 8px; font-weight: 600; }
.topic-list { display: flex; flex-direction: column; gap: 6px; }
.topic-item { display: flex; align-items: center; gap: 8px; background: #1d1d1d; border-radius: 8px; padding: 7px 10px; }
.topic-rank { width: 20px; height: 20px; border-radius: 5px; flex: none; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; color: #fff; background: #4A90D9; }
.topic-q { flex: 1; min-width: 0; font-size: 12px; color: #ddd; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.topic-cnt { flex: none; font-size: 12px; font-weight: 700; color: #9ec5ec; background: rgba(74,144,217,0.18); border-radius: 10px; padding: 1px 8px; }
.unans-box { background: #1d1d1d; border: 1px dashed #444; border-radius: 10px; padding: 16px; text-align: center; cursor: default; }
.unans-box.clickable { border-color: #C9956C; cursor: pointer; }
.unans-box.clickable:hover { background: #24211d; }
.unans-num { font-size: 28px; font-weight: 800; color: #DD8E7C; }
.unans-lab { font-size: 12px; color: #aaa; margin-top: 4px; }
.recall-btn { margin-top: 12px; width: 100%; padding: 9px; border: none; border-radius: 9px; font-size: 13px; font-weight: 600; color: #fff; background: linear-gradient(135deg,#FF7B2C,#E85D04); cursor: pointer; transition: .15s; }
.recall-btn:hover { box-shadow: 0 4px 12px rgba(232,93,4,.3); }
@media (max-width: 767px) { .chat-top { grid-template-columns: 1fr; } }

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

/* 预警一键处置 */
.alert-item { align-items: center; }
.alert-handle { flex: none; margin-left: 8px; padding: 5px 12px; border: 1px solid #3a3a3a; border-radius: 16px; font-size: 12px; font-weight: 600; color: #E3BB6A; background: #202020; cursor: pointer; transition: .15s; }
.alert-handle:active { opacity: 0.8; }
.handled-tag { font-size: 11px; color: #A9BBA0; background: rgba(107,110,100,0.22); padding: 1px 8px; border-radius: 10px; margin-left: 6px; }
.done-tag { color: #A9BBA0; }

/* 商户情感榜 */
.sent-list { display: flex; flex-direction: column; gap: 8px; }
.sent-item { display: flex; align-items: center; gap: 12px; background: #1d1d1d; border-radius: 10px; padding: 10px 12px; }
.sent-rank { width: 22px; height: 22px; border-radius: 6px; flex: none; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; color: #fff; background: #6b6b6b; }
.sent-body { flex: 1; min-width: 0; }
.sent-name { font-size: 13px; color: #f0f0f0; font-weight: 600; }
.sent-cat { font-size: 11px; color: #999; background: #2a2a2a; padding: 1px 8px; border-radius: 10px; margin-left: 6px; }
.sent-sub { font-size: 12px; color: #aaa; margin-top: 2px; }
.sent-score { flex: none; width: 38px; text-align: center; font-size: 16px; font-weight: 700; border-radius: 8px; padding: 4px 0; }
.sent-score.good { color: #A9BBA0; background: rgba(107,110,100,0.18); }
.sent-score.bad { color: #DD8E7C; background: rgba(155,74,62,0.2); }
.sent-score.flat { color: #ccc; background: #262626; }
.cat-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.cat-chip { font-size: 11px; color: #ddd; background: #222; border: 1px solid #333; border-radius: 12px; padding: 3px 10px; }

/* 活动 ROI */
.roi-list { display: flex; flex-direction: column; gap: 8px; }
.roi-item { display: flex; align-items: center; gap: 12px; background: #1d1d1d; border-radius: 10px; padding: 10px 12px; }
.roi-body { flex: 1; min-width: 0; }
.roi-name { font-size: 13px; color: #f0f0f0; font-weight: 600; }
.roi-status { font-size: 11px; color: #999; background: #2a2a2a; padding: 1px 8px; border-radius: 10px; margin-left: 6px; }
.roi-sub { font-size: 12px; color: #aaa; margin-top: 2px; }
.roi-roi { flex: none; font-size: 14px; font-weight: 700; padding: 4px 10px; border-radius: 8px; }
.roi-roi.good { color: #A9BBA0; background: rgba(107,110,100,0.18); }
.roi-roi.flat { color: #bbb; background: #262626; }

/* 群发定向券弹窗 */
.coupon-form { display: flex; flex-direction: column; gap: 6px; }
.coupon-form label { font-size: 12px; color: #aaa; margin-top: 8px; }
.coupon-form label:first-child { margin-top: 0; }
</style>
