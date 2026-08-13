<template>
  <div class="profile-tab">

    <!-- ── 顶部栏：海江新天地品牌 ── -->
    <div class="profile-header">
      <div class="ph-brand">
        <span class="ph-name-en">More</span>
        <span class="ph-name">更多</span>
      </div>
      <div class="ph-actions">
        <div class="ph-btn ph-dots">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="#FFFFFF" stroke="none"><circle cx="5" cy="12" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="19" cy="12" r="2"/></svg>
        </div>
        <div class="ph-btn ph-avatar-sm">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M4 21v-1a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v1"/></svg>
        </div>
      </div>
    </div>

    <!-- ── 用户信息卡片（浅橙棕） ── -->
    <div class="user-card">
      <div class="uc-avatar">
        <img v-if="member && member.headimgurl" :src="member.headimgurl" class="uc-avatar-img" alt="" />
        <svg v-else width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
      </div>
      <div class="uc-info">
        <div class="uc-name-row">
          <span class="uc-name">{{ member && member.display_name ? member.display_name : '海江会员' }}</span>
          <span class="uc-points" v-if="member">积分 {{ member.points }}</span>
          <svg class="uc-edit" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
        </div>
        <div class="uc-phone">{{ maskPhone(member && member.phone) }}</div>
      </div>
      <div class="uc-actions">
        <div class="uc-action-btn">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
        </div>
        <div class="uc-action-btn">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
        </div>
      </div>
    </div>

    <!-- ── 双会员卡横排：海江卡(金黄) + 社区聚乐部年卡(浅粉棕) ── -->
    <div class="mem-cards-row">
      <div class="mem-card mem-gold">
        <div class="mem-icon-box">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20"/><circle cx="17" cy="14" r="1.5"/></svg>
        </div>
        <div class="mem-text">
          <div class="mem-title">海江卡</div>
          <div class="mem-sub">暂无海江卡</div>
        </div>
      </div>
      <div class="mem-card mem-pink">
        <div class="mem-badge-pill">年卡</div>
        <div class="mem-text">
          <div class="mem-title">社区聚乐部<br/>年卡</div>
          <div class="mem-sub">暂无聚乐部年卡</div>
        </div>
      </div>
    </div>

    <!-- ── 数据统计行（深灰绿） ── -->
    <div class="stats-card">
      <div class="stat-item">
        <div class="stat-num">{{ member ? member.points : 0 }}</div>
        <div class="stat-label">积分</div>
      </div>
      <div class="stat-item">
        <div class="stat-num">{{ member ? (member.membership_level || '普卡') : '普卡' }}</div>
        <div class="stat-label">等级</div>
      </div>
      <div class="stat-item">
        <div class="stat-num">{{ member && member.coupon_count ? member.coupon_count : 5 }}</div>
        <div class="stat-label">优惠券</div>
      </div>
    </div>

    <!-- ── 版块标题：Member Benefit / 会员权益（与首页统一） ── -->
    <div class="section-label">
      <span class="section-en">Member Benefit</span>
      <span class="section-cn">会员权益</span>
    </div>

    <!-- ── 会员权益卡片：海江之友(可切换等级) + 成长值(深红棕) ── -->
    <div class="benefit-cards">
      <div class="tier-carousel">
        <div class="tier-viewport" ref="tierViewport" @scroll="onTierScroll">
          <div v-for="(t, i) in tiers" :key="t.name" class="tier-slide">
            <img :src="t.mountain" alt="" class="tier-mtn-img" :class="t.cls" />
            <div class="tier-card" :class="t.cls">
              <div class="tier-body">
                <div class="bc-header">
                  <div class="bc-title">{{ t.name }}</div>
                  <div class="bc-level">{{ t.tag }}</div>
                </div>
                <div class="tier-concepts">
                  <div class="tier-line" v-for="(c, ci) in t.concepts" :key="ci">{{ c }}</div>
                </div>
                <div class="tier-current" v-if="i === tierCurrent">● 当前等级</div>
              </div>
            </div>
          </div>
        </div>
    </div>
      <div class="benefit-card benefit-red">
        <div class="bc-header">
          <div class="bc-title">成长值</div>
          <div class="bc-level">查看明细</div>
        </div>
        <div class="bc-big-num">3,250</div>
        <div class="bc-status">距离 Lv.2 还差 6,750 成长值</div>
      </div>
    </div>

    <!-- ── 功能快捷入口（9 宫格，每格一色，与首页统一） ── -->
    <div class="fn-grid">
      <div v-for="fn in functions" :key="fn.label" class="fn-item" @click="go(fn.route)">
        <div class="fn-icon">
          <svg v-html="fn.icon" width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"></svg>
        </div>
        <span class="fn-label">{{ fn.label }}</span>
      </div>
    </div>

    <!-- ── 更多设置（深灰绿） ── -->
    <div class="settings-list">
      <div class="s-item" @click="$router.push('/parking/bind')">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M14 7h-4v10h4a3 3 0 0 0 0-6h-3"/></svg>
        <span>我的车辆</span>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.6)" stroke-width="2" stroke-linecap="round"><polyline points="9 18 15 12 9 6"/></svg>
      </div>
      <div class="s-item" @click="emit('switchTab', 'chat')">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        <span>联系客服</span>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.6)" stroke-width="2" stroke-linecap="round"><polyline points="9 18 15 12 9 6"/></svg>
      </div>
      <div class="s-item" @click="$router.push('/settings')">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
        <span>设置</span>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.6)" stroke-width="2" stroke-linecap="round"><polyline points="9 18 15 12 9 6"/></svg>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onActivated } from 'vue'
import { useRouter } from 'vue-router'
import { useMemberStore } from '@/stores/member'
import mtnPu from '@/assets/mountain-pu.png'
import mtnYin from '@/assets/mountain-yin.png'
const emit = defineEmits(['switchTab'])
const router = useRouter()
const memberStore = useMemberStore()
// 与首页会员卡、会员中心共用同一份登录态（微信昵称 / 头像 / 积分 / 等级同步）
const member = computed(() => memberStore.member)
const levelToIndex = { '普卡': 0, '银卡': 1, '金卡': 2, '铂金卡': 3, '钻石卡': 4, '黑钻卡': 5 }
function maskPhone(p) {
  if (!p) return '195****1648'
  return p.slice(0, 3) + '****' + p.slice(7)
}
function syncMemberTier() {
  memberStore.restore()
  const lv = member.value && member.value.membership_level
  if (lv && levelToIndex[lv] != null) {
    tierCurrent.value = levelToIndex[lv]
    requestAnimationFrame(() => goTier(tierCurrent.value))
  }
}
onMounted(syncMemberTier)
onActivated(syncMemberTier)

// 海江之友等级卡（可切换）：普卡/银卡/金卡/铂金卡/钻石卡/黑钻卡
// 等级主题色统一取自 memberStore.levelTheme（与首页会员卡、会员中心、兑换页一致）
const tiers = [
  { name: '普卡', tag: 'Lv.1', cls: 'tier-pu', peaks: 1, mountain: mtnPu, concepts: ['注册即会员，0门槛', '基础积分累积', '生日专属祝福'] },
  { name: '银卡', tag: 'Lv.2', cls: 'tier-yin', peaks: 2, mountain: mtnPu, concepts: ['消费满2万自动升级', '全场9.5折优惠', '每月1张特惠券'] },
  { name: '金卡', tag: 'Lv.3', cls: 'tier-jin', peaks: 3, mountain: mtnPu, concepts: ['全场9折+专属折扣', '生日双倍积分', '免费停车2小时/天'] },
  { name: '铂金卡', tag: 'Lv.4', cls: 'tier-bo', peaks: 4, mountain: mtnPu, concepts: ['全场8.5折', '专属客服一对一', '免费停车+快递代收'] },
  { name: '钻石卡', tag: 'Lv.5', cls: 'tier-zuan', peaks: 5, mountain: mtnPu, concepts: ['全场8折', '月度尊享礼遇', '亲友卡权益共享'] },
  { name: '黑钻卡', tag: 'Lv.6', cls: 'tier-hei', peaks: 6, mountain: mtnPu, concepts: ['顶级黑钻特权', '私人管家服务', '全年免费+专属活动'] },
].map(t => {
  const th = memberStore.levelTheme(t.name)
  return { ...t, bg: th.bg, bd: th.bd, accent: th.accent }
})
// 海江之友各等级使用各自的山峰图（t.mountain），普卡已配置，其余待替换
const tierCurrent = ref(0)
const tierViewport = ref(null)
function goTier(i) {
  tierCurrent.value = i
  const v = tierViewport.value
  if (v) {
    const step = v.children[0].offsetWidth + 14
    v.scrollTo({ left: step * i, behavior: 'smooth' })
  }
}
function onTierScroll(e) {
  const v = e.target
  const step = v.children[0].offsetWidth + 14
  const i = Math.round(v.scrollLeft / step)
  if (i !== tierCurrent.value) tierCurrent.value = i
}

const functions = [
  { label: '积分兑换', route: '/redeem', icon: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>' },
  { label: '我的优惠券', route: '/offers', icon: '<path d="M20 12v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-8"/><path d="M22 7H2v5h20z"/>' },
  { label: '停车管理', route: '/parking', icon: '<circle cx="12" cy="12" r="10"/><path d="M14 7h-4v10h4a3 3 0 0 0 0-6h-3"/>' },
  { label: '活动报名', route: '/activities', icon: '<rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>' },
  { label: '商户收藏', route: '/shops', icon: '<path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>' },
  { label: '室内导航', route: '/nav', icon: '<polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/>' },
  { label: '兑换记录', route: '/redeem', icon: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>' },
  { label: '会员中心', route: '/member', icon: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>' },
  { label: '关于我们', route: '/about', icon: '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>' },
]

function go(route) { if (route) router.push(route) }
</script>

<style scoped>
@font-face { font-family: 'Gayathri'; src: url('@/assets/fonts/Gayathri-Bold.ttf') format('truetype'); font-weight: 700; font-style: normal; font-display: swap; }

.profile-tab { padding: 0 0 80px; }

/* ── 顶部栏 ── */
.profile-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 16px;
}
.ph-brand { display: flex; flex-direction: column; align-items: flex-start; gap: 2px; }
.ph-name-en {
  font-family: 'Gayathri', var(--font-primary); font-size: 22px; font-weight: 900;
  letter-spacing: 1px; line-height: 1.1; color: rgba(255,255,255,0.92);
  text-transform: capitalize; -webkit-text-stroke: 0.5px rgba(255,255,255,0.3);
}
.ph-name {
  font-family: var(--font-primary); font-size: 17px; font-weight: 800;
  color: #FFFFFF; letter-spacing: 0.5px;
}
.ph-actions { display: flex; align-items: center; gap: 12px; }
.ph-btn { width: 34px; height: 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; }
.ph-dots { background: rgba(255,255,255,0.08); }
.ph-avatar-sm { border: 1.5px solid rgba(255,255,255,0.25); }

/* ── 通用：白字 + 凹陷阴影 ── */
.uc-name, .uc-phone, .mem-title, .mem-sub, .stat-num, .stat-label,
.bc-title, .bc-level, .bc-expire, .bc-status, .bc-next, .bc-big-num,
.fn-label, .s-item span {
  color: #FFFFFF;
  text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.25);
}

/* ── 用户信息卡片：浅橙棕 ── */
.user-card {
  margin: 4px 16px 18px;
  background-color: #C9956C;
  border: 3px solid #A87C48;
  border-radius: 18px;
  padding: 20px 18px;
  display: flex; align-items: center; gap: 14px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20);
}
.uc-avatar {
  width: 56px; height: 56px; border-radius: 50%;
  background: rgba(255,255,255,0.18);
  border: 1.5px solid rgba(255,255,255,0.30);
  display: flex; align-items: center; justify-content: center;
  overflow: hidden; flex-shrink: 0;
}
.uc-avatar-img { width: 100%; height: 100%; object-fit: cover; }
.uc-info { flex: 1; min-width: 0; }
.uc-name-row { display: flex; align-items: center; gap: 6px; }
.uc-name { font-size: var(--fs-body); font-weight: 700; }
.uc-points { font-size: 11px; font-weight: 700; color: #FFB877; background: rgba(255,184,119,0.14); border: 1px solid rgba(255,184,119,0.35); padding: 1px 8px; border-radius: 10px; white-space: nowrap; }
.uc-edit { flex-shrink: 0; cursor: pointer; opacity: 0.85; }
.uc-phone { font-size: var(--fs-secondary); margin-top: 3px; opacity: 0.9; }
.uc-actions { display: flex; flex-direction: column; gap: 10px; flex-shrink: 0; }
.uc-action-btn {
  width: 38px; height: 38px; border-radius: 50%;
  background: rgba(255,255,255,0.18);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
}

/* ── 双会员卡横排 ── */
.mem-cards-row { display: flex; gap: 12px; margin: 0 16px 18px; }
.mem-card {
  flex: 1;
  border-radius: 16px;
  padding: 16px;
  display: flex; flex-direction: column; gap: 8px;
  position: relative;
  min-height: 96px;
  box-sizing: border-box;
  box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20);
}
.mem-gold { background-color: #C4923A; border: 3px solid #9A7425; }
.mem-pink { background-color: #D4A59A; border: 3px solid #A67D72; }
.mem-icon-box {
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  width: 44px; height: 44px;
}
.mem-badge-pill {
  position: absolute; top: 12px; right: 12px;
  background: rgba(255,255,255,0.22);
  border: 1px solid rgba(255,255,255,0.30);
  border-radius: 8px;
  padding: 3px 10px;
  font-size: 11px; font-weight: 700;
  color: #FFFFFF;
  letter-spacing: 1px;
}
.mem-title { font-size: var(--fs-body); font-weight: 700; line-height: 1.35; }
.mem-sub { font-size: var(--fs-aux); opacity: 0.85; }

/* ── 数据统计行：深灰绿 ── */
.stats-card {
  display: flex; margin: 0 16px 22px;
  background-color: #6B6E64;
  border: 3px solid #4E5049;
  border-radius: 16px;
  padding: 18px 0;
  box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20);
}
.stat-item { flex: 1; text-align: center; border-right: 0.5px solid rgba(255,255,255,0.25); }
.stat-item:last-child { border-right: none; }
.stat-num { font-size: 28px; font-weight: 800; line-height: 1.2; }
.stat-label { font-size: var(--fs-aux); margin-top: 4px; opacity: 0.9; }

/* ── 版块标题（与首页统一） ── */
.section-label { display: flex; flex-direction: column; margin: 22px 16px 18px; }
.section-en { font-family: 'Gayathri', var(--font-primary); font-size: 22px; font-weight: 900; letter-spacing: 1px; line-height: 1.2; color: rgba(255,255,255,0.92); text-transform: capitalize; -webkit-text-stroke: 0.5px rgba(255,255,255,0.3); }
.section-cn { font-size: var(--fs-headline); font-weight: 400; color: #FFFFFF; margin-top: 10px; text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.18); }

/* ── 会员权益卡片：实色（与首页统一，无渐变） ── */
.benefit-cards {
  display: flex; flex-direction: column; gap: 12px; margin: 0 16px 18px;
}
.benefit-card {
  flex: none; width: 100%;
  border-radius: 18px;
  padding: 22px 20px;
  min-height: 180px;
  box-sizing: border-box;
  position: relative; overflow: hidden;
  box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20);
}
.benefit-red { background-color: #9B4A3E; border: 3px solid #6E332A; }

/* ── 高端质感：斜向金属高光 + 内描边压印（去掉交叉织纹/华夫格，避免廉价感） ── */
.mem-card,
.tier-card,
.benefit-red {
  background-image:
    linear-gradient(135deg,
      rgba(255,255,255,0.32) 0%,
      rgba(255,255,255,0.06) 24%,
      rgba(255,255,255,0) 48%,
      rgba(0,0,0,0.16) 100%);
}
/* 顶部内高光 + 底部内阴影：营造厚实压印/烫印的立体感（替代网格纹路） */
.mem-card::before,
.tier-card::before,
.benefit-red::before {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  box-shadow:
    inset 0 2px 3px rgba(255,255,255,0.30),
    inset 0 -3px 6px rgba(0,0,0,0.20);
}

/* ── 海江之友：可切换等级轮播 ── */
.benefit-cards, .tier-carousel, .tier-viewport, .tier-slide {
  background: transparent !important;
}
.tier-carousel { flex: none; width: 100%; position: relative; overflow: visible; margin-top: -45px; }
.tier-viewport { display: flex; gap: 14px; padding: 45px 0 14px; overflow-x: auto; scroll-snap-type: x mandatory; -webkit-overflow-scrolling: touch; scrollbar-width: none; }
.tier-viewport::-webkit-scrollbar { display: none; }
.tier-slide {
  flex: 0 0 100%; box-sizing: border-box; scroll-snap-align: start;
  position: relative; overflow: visible;
}
/* 雪山：直接放在 .tier-slide 内、与卡片同属一个被滚动的元素，100%同步、零独立动画；山顶 top:-40px 从 slide 顶上探40px，因 .tier-viewport 的 padding-top 有 45px，该探出段落在视口可见 padding 区内(viewport_y≈5px)，不会被 overflow-x:auto 隐式裁切 y；卡片 margin-top:25px 留出山峰区并压住山脚约1/3（?t=170 用户认可坐标，山高、峰突出） */
.tier-mtn-img {
  position: absolute;
  top: -40px; left: 0; right: 0;
  z-index: 0; pointer-events: none;
  width: 100%; height: auto;
  display: block;
  background: transparent !important;
  border: none !important;
  border-radius: 0 0 18px 18px !important;
}
/* 卡片：承载背景/圆角/阴影，压在雪山前面，圆角干净不被挡；上提压住山图透明处 */
.tier-card {
  position: relative; z-index: 1;
  box-sizing: border-box; width: 100%;
  margin-top: 25px;
  min-height: 180px;
  border-radius: 18px;
  border-width: 3px; border-style: solid;
  padding: 22px 20px;
  display: flex; flex-direction: column; justify-content: center;
  box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20);
}
/* 文字内容：在卡片内垂直居中（上下与卡片边距相等），不再额外下移 */
.tier-body {
  position: relative; z-index: 2;
  margin-top: 0;
}
.tier-pu   { background-color: #8B8B90; border-color: #6A6A6E; }
.tier-yin  { background-color: #9CA1A8; border-color: #7A7E84; }
.tier-jin  { background-color: #C4923A; border-color: #9A7425; }
.tier-bo   { background-color: #9DA7B5; border-color: #7C8593; }
.tier-zuan { background-color: #4F9CC9; border-color: #3A7BA0; }
.tier-hei  { background-color: #6B6E64; border-color: #3C3E36; }
.tier-concepts { margin-top: 6px; }
.tier-line { font-size: 15px; font-weight: 600; line-height: 1.8; opacity: 0.96;
  text-shadow: 0 1px 2px rgba(0,0,0,0.35); }
.tier-current { margin-top: 10px; font-size: 12px; font-weight: 700; letter-spacing: 1px; color: #FFE8B0; opacity: 0.95; }
.bc-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.bc-title { font-size: 20px; font-weight: 800; }
.bc-level {
  font-size: 12px; font-weight: 600;
  background: rgba(0,0,0,0.22);
  padding: 4px 12px; border-radius: 10px;
}
.bc-expire { font-size: var(--fs-secondary); margin-bottom: 14px; opacity: 0.9; }
.bc-progress-track { position: relative; height: 6px; background: rgba(255,255,255,0.28); border-radius: 3px; margin-bottom: 12px; overflow: visible; }
.bc-progress-fill { position: absolute; left: 0; top: 0; height: 100%; width: 72%; background: rgba(255,255,255,0.85); border-radius: 3px; }
.bc-dot { position: absolute; right: 28%; top: 50%; transform: translateY(-50%); width: 14px; height: 14px; background: #fff; border-radius: 50%; box-shadow: 0 0 6px rgba(255,255,255,0.5); }
.bc-status { font-size: var(--fs-secondary); margin-bottom: 4px; opacity: 0.92; }
.bc-next { font-size: var(--fs-aux); opacity: 0.85; }
.bc-highlight { color: #FFE8B0; font-weight: 700; }
.bc-big-num { font-size: 36px; font-weight: 800; line-height: 1.2; margin-bottom: 8px; }

/* ── 功能 9 宫格：每格一色（与首页统一） ── */
.fn-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 0 16px 16px; }
.fn-item {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 14px 4px; border-radius: 16px; cursor: pointer;
  box-sizing: border-box;
  box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20);
  transition: transform 0.15s;
}
.fn-item:nth-child(1) { background-color: #C4923A; border: 3px solid #9A7425; }
.fn-item:nth-child(2) { background-color: #D4A59A; border: 3px solid #A67D72; }
.fn-item:nth-child(3) { background-color: #9B4A3E; border: 3px solid #6E332A; }
.fn-item:nth-child(4) { background-color: #C9956C; border: 3px solid #A87C48; }
.fn-item:nth-child(5) { background-color: #8B8B90; border: 3px solid #6A6A6E; }
.fn-item:nth-child(6) { background-color: #6B6E64; border: 3px solid #4E5049; }
.fn-item:nth-child(7) { background-color: #C4923A; border: 3px solid #9A7425; }
.fn-item:nth-child(8) { background-color: #D4A59A; border: 3px solid #A67D72; }
.fn-item:nth-child(9) { background-color: #9B4A3E; border: 3px solid #6E332A; }
.fn-item:active { transform: scale(0.97); }
.fn-icon {
  width: 52px; height: 52px;
  display: flex; align-items: center; justify-content: center;
  color: #FFFFFF;
}
.fn-icon svg { filter: drop-shadow(0 0.4px 0.5px rgba(0,0,0,0.45)); }
.fn-label { font-size: 13px; font-weight: 600; }

/* ── 设置列表：深灰绿 ── */
.settings-list {
  margin: 0 16px;
  background-color: #6B6E64;
  border: 3px solid #4E5049;
  border-radius: 16px; overflow: hidden;
  box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20);
}
.s-item {
  display: flex; align-items: center; gap: 14px; padding: 14px 16px;
  cursor: pointer; transition: background 0.15s;
  font-size: 15px;
}
.s-item:not(:last-child) { border-bottom: 0.5px solid rgba(255,255,255,0.18); }
.s-item:active { background: rgba(255,255,255,0.08); }
.s-item :last-child { margin-left: auto; }

.spacer { height: 24px; }
</style>
