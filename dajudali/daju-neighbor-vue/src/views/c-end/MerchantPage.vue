<template>
  <div class="mp-page">
    <div class="mp-back" @click="$router.back()">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#AAA" stroke-width="2" stroke-linecap="round"><polyline points="15 18 9 12 15 6"/></svg>
    </div>

    <div class="mp-hero">
      <div class="mp-hero-icon">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#999999" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
      </div>
      <div class="mp-hero-title">招商合作</div>
      <div class="mp-hero-sub">海江新天地诚邀优质品牌入驻</div>
    </div>

    <div class="mp-card">
      <div class="mp-card-title">项目优势</div>
      <div class="mp-advantage">
        <div class="mp-ad-item">
          <div class="mp-ad-icon">址</div>
          <div class="mp-ad-text">核心商圈 · 日均客流 3 万+</div>
        </div>
        <div class="mp-ad-item">
          <div class="mp-ad-icon">楼</div>
          <div class="mp-ad-text">5 层商业体 · 200+ 商铺</div>
        </div>
        <div class="mp-ad-item">
          <div class="mp-ad-icon">车</div>
          <div class="mp-ad-text">地下停车场 · 500 车位</div>
        </div>
        <div class="mp-ad-item">
          <div class="mp-ad-icon">势</div>
          <div class="mp-ad-text">统一运营 · 品牌推广支持</div>
        </div>
      </div>
    </div>

    <div class="mp-card">
      <div class="mp-card-title">招商类目</div>
      <div class="mp-tags">
        <span class="mp-tag">餐饮美食</span>
        <span class="mp-tag">时尚零售</span>
        <span class="mp-tag">亲子娱乐</span>
        <span class="mp-tag">生活服务</span>
        <span class="mp-tag">教育培训</span>
        <span class="mp-tag">科技数码</span>
      </div>
    </div>

    <!-- 商户扶持计划（并入招商合作页，原后台页迁移） -->
    <div class="mp-card">
      <div class="mp-card-title">商户扶持计划</div>
      <p class="ms-lead">我们不是向商户<strong>收钱</strong>，而是<strong>养商户</strong>：入驻免年费、送曝光、送平台引流券、成交再返点，把流量与补贴真金白银给到商户，一起把场子做热。</p>
      <div class="ms-grid">
        <div class="ms-plan" v-for="p in plans" :key="p.title">
          <div class="ms-plan-ico">{{ p.ico }}</div>
          <div class="ms-plan-title">{{ p.title }}</div>
          <div class="ms-plan-desc">{{ p.desc }}</div>
          <div class="ms-plan-metric">{{ p.metric }}</div>
        </div>
      </div>
    </div>

    <div class="mp-card">
      <div class="mp-card-title">为什么是「养商户」而不是「收商户」</div>
      <div class="ms-flow">
        <template v-for="(s, i) in flow" :key="i">
          <span class="ms-step"><i>{{ i + 1 }}</i>{{ s }}</span>
          <span v-if="i < flow.length - 1" class="ms-arrow">→</span>
        </template>
      </div>
      <p class="ms-note">标准为招商扶持政策口径，具体以实际签约合同为准；引流券核销与返点可在后台「补贴 ROI」看板实时核算。</p>
    </div>

    <div class="mp-card">
      <div class="mp-card-title">扶持成效（演示口径）</div>
      <div class="ms-kpis">
        <div class="ms-kpi"><b>¥{{ fmtMoney(286500) }}</b><span>已发放商户扶持补贴</span></div>
        <div class="ms-kpi"><b>8</b><span>重点扶持商户</span></div>
        <div class="ms-kpi"><b>{{ fmtNum(18620) }}</b><span>补贴带动到店</span></div>
        <div class="ms-kpi"><b>¥{{ fmtMoney(2860000) }}</b><span>补贴带动 GMV</span></div>
      </div>
      <p class="ms-note">数据与后台「补贴 ROI」看板同源，当前为演示种子口径，接真实核销后自动切换实算。</p>
      <a href="tel:4008888888" class="ms-cta">我要申请入驻</a>
    </div>

    <div class="mp-card">
      <div class="mp-card-title">联系方式</div>
      <div class="mp-contact">
        <div class="mp-contact-item" @click="call">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#999999" stroke-width="1.5" stroke-linecap="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
          <span>致电咨询：400-888-8888</span>
        </div>
        <div class="mp-contact-item">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#999999" stroke-width="1.5" stroke-linecap="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
          <span>招商邮箱：merchant@haijiang.com</span>
        </div>
        <div class="mp-contact-item">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#999999" stroke-width="1.5" stroke-linecap="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
          <span>周一至周五 9:00-18:00</span>
        </div>
      </div>
    </div>

    <a href="tel:4008888888" class="mp-call-btn">立即拨打</a>
    <div class="spacer"></div>
  </div>
</template>

<script setup>
const plans = [
  { title: '入驻免年费', ico: '免', desc: '新签商户首年免平台年费，0 门槛入驻；装修筹备期叠加免租扶持，轻装开业。', metric: '首年省 ¥30,000+' },
  { title: '流量曝光扶持', ico: '曝', desc: 'App 首页黄金位、消息推送、邻里社群联合曝光；新店开业送 30 天流量包。', metric: '开业 30 天曝光 50万+' },
  { title: '平台引流券', ico: '券', desc: '平台出资发券（满减 / 0元购），用户到店用券即导流，券成本由平台买单。', metric: '8 类券 · 平台请客' },
  { title: '成交返点补贴', ico: '返', desc: '按券核销与成交额给商户返点补贴，卖得越好补得越多，共生共赢。', metric: '返点最高 8%' },
]

const flow = ['平台发券', '用户领券', '到店核销', '商户成交', '平台返点', '场子变热']

function call() { window.location.href = 'tel:4008888888' }
function fmtMoney(n) { if (n === null || n === undefined || isNaN(n)) return '0'; return Number(n).toLocaleString('zh-CN') }
function fmtNum(n) { if (n === null || n === undefined || isNaN(n)) return '0'; return Number(n).toLocaleString('zh-CN') }
</script>

<style scoped>
.mp-page { padding: 0 12px; min-height: 100vh; background: #000000; }
.mp-back { padding: 10px 0; cursor: pointer; display: inline-block; margin-bottom: 4px; }

.mp-hero { text-align: center; padding: 24px 0 20px; }
.mp-hero-icon { margin-bottom: 12px; }
.mp-hero-title { font-size: 24px; font-weight: 700; color: #fff; }
.mp-hero-sub { font-size: 14px; color: rgba(255,255,255,0.55); margin-top: 6px; }

.mp-card { margin-bottom: 10px; padding: 16px; background: #222; border-radius: 14px;
  border: 1px solid rgba(255,255,255,0.08); box-shadow: inset 0 2px 4px rgba(0,0,0,0.3); }
.mp-card-title { font-size: 15px; font-weight: 600; color: #fff; margin-bottom: 12px; }

.mp-advantage { display: flex; flex-direction: column; gap: 10px; }
.mp-ad-item { display: flex; align-items: center; gap: 10px; }
.mp-ad-icon {
  font-size: 15px; font-weight: 700; width: 32px; height: 32px; border-radius: 8px;
  background: #232323; border: 1px solid #7E5413; color: #C4923A;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.mp-ad-text { font-size: 14px; color: rgba(255,255,255,0.7); }

.mp-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.mp-tag {
  padding: 5px 14px; border-radius: 20px; background: #222; color: rgba(255,255,255,0.65);
  border: 1px solid rgba(255,255,255,0.08);
  font-size: 13px; font-weight: 500;
}

.mp-contact { display: flex; flex-direction: column; gap: 12px; }
.mp-contact-item { display: flex; align-items: center; gap: 10px; font-size: 14px; color: rgba(255,255,255,0.7); cursor: pointer; }

.mp-call-btn {
  display: block; width: 100%; padding: 14px; border: 3px solid #9A7425; border-radius: 14px;
  background: #9A7425; color: #fff; font-size: 16px; font-weight: 700;
  text-align: center; text-decoration: none; cursor: pointer; margin-top: 8px;
  box-shadow: inset 3px 3px 7px rgba(0,0,0,0.45), inset -2px -2px 5px rgba(196,146,58,0.45);
  filter: drop-shadow(0 0.6px 1px rgba(0,0,0,0.4));
}
.mp-call-btn:active {
  box-shadow: inset 5px 5px 10px rgba(0,0,0,0.55), inset -2px -2px 5px rgba(196,146,58,0.35);
}
.spacer { height: 40px; }

/* 商户扶持计划 */
.ms-lead { font-size: 13px; line-height: 1.8; color: rgba(255,255,255,0.6); margin: 0 0 14px; }
.ms-lead strong { color: #C4923A; font-weight: 700; }
.ms-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
@media (max-width: 560px) { .ms-grid { grid-template-columns: 1fr; } }
.ms-plan { background: #1c1c1c; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 14px; }
.ms-plan-ico { width: 34px; height: 34px; border-radius: 9px; background: #232323; border: 1px solid #7E5413; color: #C4923A; font-size: 15px; font-weight: 700; display: flex; align-items: center; justify-content: center; margin-bottom: 10px; }
.ms-plan-title { font-size: 15px; font-weight: 700; color: #fff; }
.ms-plan-desc { font-size: 12px; line-height: 1.7; color: rgba(255,255,255,0.6); margin-top: 6px; }
.ms-plan-metric { display: inline-block; margin-top: 10px; font-size: 12px; font-weight: 700; color: #C4923A; background: rgba(196,146,58,0.12); border: 1px solid rgba(196,146,58,0.4); padding: 3px 10px; border-radius: 999px; }

.ms-flow { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.ms-step { display: inline-flex; align-items: center; gap: 8px; background: #1c1c1c; border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 9px 12px; font-size: 13px; color: rgba(255,255,255,0.85); }
.ms-step i { width: 20px; height: 20px; border-radius: 50%; background: linear-gradient(135deg, #FF7B2C, #E85D04); color: #fff; font-size: 11px; font-style: normal; font-weight: 700; display: flex; align-items: center; justify-content: center; }
.ms-arrow { color: #C4923A; font-weight: 700; }

.ms-kpis { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
@media (max-width: 560px) { .ms-kpis { grid-template-columns: 1fr; } }
.ms-kpi { background: #1c1c1c; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 14px 16px; display: flex; flex-direction: column; gap: 6px; }
.ms-kpi b { font-size: 21px; color: #C4923A; }
.ms-kpi span { font-size: 12px; color: rgba(255,255,255,0.55); }

.ms-note { font-size: 12px; line-height: 1.7; color: rgba(255,255,255,0.45); margin: 12px 0 0; padding: 8px 12px; background: rgba(255,255,255,0.04); border-left: 3px solid #6B6E64; border-radius: 8px; }
.ms-note strong { color: #C9C9C9; }

.ms-cta { display: block; width: 100%; margin-top: 14px; padding: 13px; border: 2px solid #9A7425; border-radius: 14px; background: #9A7425; color: #fff; font-size: 15px; font-weight: 700; text-align: center; text-decoration: none; }
</style>
