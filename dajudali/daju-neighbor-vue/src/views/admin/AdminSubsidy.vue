<template>
  <div class="sub-page">
    <!-- 顶部主张 -->
    <header class="sub-hero">
      <div class="sub-hero-badge">B端 · 招商扶持</div>
      <h1>商户扶持计划</h1>
      <p>我们不是向商户<strong>收钱</strong>，而是<strong>养商户</strong>：入驻免年费、送曝光、送平台引流券、成交再返点，把流量与补贴真金白银给到商户，一起把场子做热。</p>
    </header>

    <!-- 四大扶持权益 -->
    <section class="sub-grid">
      <div class="sub-card" v-for="p in plans" :key="p.title">
        <div class="sub-card-icon" :style="{ background: p.bg, borderColor: p.bd }">
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" v-html="p.icon"></svg>
        </div>
        <div class="sub-card-title">{{ p.title }}</div>
        <div class="sub-card-desc">{{ p.desc }}</div>
        <div class="sub-card-metric" v-if="p.metric">{{ p.metric }}</div>
      </div>
    </section>

    <!-- 养商户逻辑 -->
    <section class="sub-panel">
      <h2><span class="dot" style="background:#FF7B2C"></span>为什么是"养商户"而不是"收商户"</h2>
      <div class="sub-flow">
        <div class="sub-step" v-for="(s, i) in flow" :key="i">
          <span class="sub-step-no">{{ i + 1 }}</span>
          <span class="sub-step-txt">{{ s }}</span>
          <span v-if="i < flow.length - 1" class="sub-step-arrow">→</span>
        </div>
      </div>
      <p class="sub-note">说明：上述为平台招商扶持的<strong>标准政策口径</strong>，具体以实际签约合同为准；引流券核销与返点数据可在「补贴 ROI」看板实时核算。</p>
    </section>

    <!-- 扶持成效（演示口径，与补贴 ROI 同源） -->
    <section class="sub-panel">
      <h2><span class="dot" style="background:#C4923A"></span>扶持成效（演示口径）</h2>
      <div class="sub-kpis">
        <div class="sub-kpi"><b>¥{{ fmtMoney(286500) }}</b><span>已发放商户扶持补贴</span></div>
        <div class="sub-kpi"><b>8</b><span>重点扶持商户</span></div>
        <div class="sub-kpi"><b>{{ fmtNum(18620) }}</b><span>补贴带动到店</span></div>
        <div class="sub-kpi"><b>¥{{ fmtMoney(2860000) }}</b><span>补贴带动 GMV</span></div>
      </div>
      <p class="sub-note">数据与「补贴 ROI」看板同源，当前为演示种子口径，接真实核销后自动切换实算。</p>
    </section>

    <div class="sub-cta">
      <button class="sub-cta-btn" @click="goMerchant">我要申请入驻</button>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const plans = [
  {
    title: '入驻免年费',
    desc: '新签商户首年免平台年费，0 门槛入驻；装修筹备期叠加免租扶持，轻装开业。',
    metric: '首年省 ¥30,000+',
    bg: '#6B6E64', bd: '#4E5049',
    icon: '<path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/>',
  },
  {
    title: '流量曝光扶持',
    desc: 'App 首页黄金位、消息推送、邻里社群联合曝光；新店开业送 30 天流量包。',
    metric: '开业 30 天曝光 50万+',
    bg: '#C4923A', bd: '#9A7425',
    icon: '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
  },
  {
    title: '平台引流券',
    desc: '平台出资发券（满减 / 0元购），用户到店用券即导流，券成本由平台买单。',
    metric: '8 类券 · 平台请客',
    bg: '#9B4A3E', bd: '#6E332A',
    icon: '<path d="M3 8a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v2a2 2 0 0 0 0 4v2a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-2a2 2 0 0 0 0-4V8z"/><line x1="12" y1="6" x2="12" y2="18" stroke-dasharray="2 2"/>',
  },
  {
    title: '成交返点补贴',
    desc: '按券核销与成交额给商户返点补贴，卖得越好补得越多，共生共赢。',
    metric: '返点最高 8%',
    bg: '#C9956C', bd: '#A87C48',
    icon: '<path d="M12 2l2.4 7.4H22l-6 4.3 2.3 7.3L12 16.7 5.7 21l2.3-7.3-6-4.3h7.6z"/>',
  },
]

const flow = ['平台发券', '用户领券', '到店核销', '商户成交', '平台返点', '场子变热']

function goMerchant() {
  router.push('/merchant')
}

function fmtMoney(n) { if (n === null || n === undefined || isNaN(n)) return '0'; return Number(n).toLocaleString('zh-CN') }
function fmtNum(n) { if (n === null || n === undefined || isNaN(n)) return '0'; return Number(n).toLocaleString('zh-CN') }
</script>

<style scoped>
.sub-page { padding: 20px; color: #EAEAEA; }
.sub-hero { background: #15171a; border: 1px solid #26282c; border-radius: 16px; padding: 22px; margin-bottom: 18px; box-shadow: 0 4px 18px rgba(0,0,0,0.4); }
.sub-hero-badge { display: inline-block; font-size: 12px; font-weight: 700; color: #FF8F47; background: rgba(255,123,44,0.14); border: 1px solid rgba(255,123,44,0.5); padding: 3px 12px; border-radius: 999px; margin-bottom: 12px; }
.sub-hero h1 { font-size: 24px; font-weight: 800; color: #FFFFFF; margin: 0 0 10px; }
.sub-hero p { font-size: 14px; line-height: 1.8; color: #BBBBBB; margin: 0; }
.sub-hero strong { color: #FF8F47; font-weight: 700; }

.sub-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 18px; }
@media (max-width: 560px) { .sub-grid { grid-template-columns: 1fr; } }
.sub-card { background: #15171a; border: 1px solid #26282c; border-radius: 14px; padding: 18px; box-shadow: 0 4px 18px rgba(0,0,0,0.4); }
.sub-card-icon { width: 52px; height: 52px; border-radius: 14px; display: flex; align-items: center; justify-content: center; box-shadow: inset 2px 2px 6px rgba(0,0,0,0.3), inset -1px -1px 3px rgba(255,255,255,0.15); margin-bottom: 12px; }
.sub-card-title { font-size: 17px; font-weight: 700; color: #FFFFFF; }
.sub-card-desc { font-size: 13px; line-height: 1.7; color: #AAAAAA; margin-top: 8px; }
.sub-card-metric { display: inline-block; margin-top: 12px; font-size: 13px; font-weight: 700; color: #FF8F47; background: rgba(255,123,44,0.12); border: 1px solid rgba(255,123,44,0.4); padding: 4px 12px; border-radius: 999px; }

.sub-panel { background: #15171a; border: 1px solid #26282c; border-radius: 14px; padding: 18px; margin-bottom: 18px; box-shadow: 0 4px 18px rgba(0,0,0,0.4); }
.sub-panel h2 { font-size: 16px; font-weight: 700; color: #F2F2F2; display: flex; align-items: center; gap: 8px; margin: 0 0 14px; }
.sub-panel .dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; box-shadow: 0 0 8px currentColor; }

.sub-flow { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.sub-step { display: flex; align-items: center; gap: 8px; background: #1B1D21; border: 1px solid #2A2C30; border-radius: 10px; padding: 10px 12px; }
.sub-step-no { width: 22px; height: 22px; border-radius: 50%; background: linear-gradient(135deg, #FF7B2C, #E85D04); color: #fff; font-size: 12px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.sub-step-txt { font-size: 13px; color: #E2E2E2; white-space: nowrap; }
.sub-step-arrow { color: #FF8F47; font-size: 16px; font-weight: 700; }

.sub-kpis { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
@media (max-width: 560px) { .sub-kpis { grid-template-columns: 1fr; } }
.sub-kpi { background: #1B1D21; border: 1px solid #2A2C30; border-radius: 12px; padding: 14px 16px; display: flex; flex-direction: column; gap: 6px; }
.sub-kpi b { font-size: 22px; color: #FF8F47; }
.sub-kpi span { font-size: 12px; color: #999; }

.sub-note { font-size: 12px; line-height: 1.7; color: #888; margin: 14px 2px 0; padding: 8px 12px; background: rgba(255,255,255,0.04); border-radius: 8px; border-left: 3px solid #6B6E64; }
.sub-note strong { color: #C9C9C9; }

.sub-cta { text-align: center; margin: 8px 0 24px; }
.sub-cta-btn { padding: 13px 36px; border: none; border-radius: 20px; cursor: pointer; font-size: 15px; font-weight: 700; color: #fff; background: linear-gradient(135deg, #FF7B2C, #E85D04); box-shadow: 0 4px 14px rgba(232,93,4,0.4); transition: .15s; }
.sub-cta-btn:active { transform: scale(0.98); opacity: 0.9; }
</style>
