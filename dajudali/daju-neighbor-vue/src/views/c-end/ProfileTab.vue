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

    <!-- ── 版块标题：Member Benefit / 会员权益（与首页统一） ── -->
    <div class="section-label">
      <span class="section-en">Member Benefit</span>
      <span class="section-cn">会员权益</span>
    </div>

    <!-- ── 会员权益卡片：海江之友(可切换等级) + 成长值(完整成长中心) ── -->
    <div class="benefit-cards">
      <div class="tier-carousel">
        <div class="tier-viewport" ref="tierViewport" @scroll="onTierScroll">
          <div v-for="(t, i) in tiers" :key="t.name" class="tier-slide">
            <img :src="t.mountain" alt="" class="tier-mtn-img" :class="t.cls" />
            <div class="tier-card" :class="t.cls">
              <div class="tier-body">
                <div class="bc-header">
                  <div class="bc-hd-left">
                    <div class="bc-title">{{ t.name }}</div>
                    <div class="bc-level">{{ t.tag }}</div>
                  </div>
                  <button v-if="i === memberLevelIndex" class="bc-sign-btn" :class="{ signed: signedToday }" :disabled="signedToday" @click="doSignCard">{{ signedToday ? '今日已签' : '签到' }}</button>
                </div>
                <div class="bc-sign-line" v-if="i === memberLevelIndex">已连续签到 <b>{{ consecutiveDays }}</b> 天 · 累计 {{ totalCheckin }} 天</div>
                <div class="tier-concepts">
                  <div class="tier-line" v-for="(c, ci) in t.concepts" :key="ci">{{ c }}</div>
                </div>
                <!-- 成长值进度（合并进当前等级卡，与 GrowthCenter 同一套 LEVELS 逻辑） -->
                <div class="growth-in-card" v-if="i === memberLevelIndex">
                  <div class="gib-points">{{ growth.points }} <em>成长值</em></div>
                  <div class="gib-bar"><div class="gib-fill" :style="{ width: growth.pct + '%', background: t.accent }"></div></div>
                  <div class="gib-hint" v-if="growth.nextName">距离「{{ growth.nextName }}」还差 {{ growth.gap }} 成长值</div>
                  <div class="gib-hint" v-else>已是最高等级，尊享全部权益</div>
                </div>
                <!-- 成就徽章（镶嵌进当前等级卡，仅显示已解锁，横向滑动） -->
                <div class="card-badges" v-if="i === memberLevelIndex && earnedBadges.length">
                  <div class="cb-title">成就徽章 <span class="cb-sub">已点亮 {{ earnedBadges.length }} 枚</span></div>
                  <div class="cb-strip">
                    <div v-for="b in earnedBadges" :key="b.code" class="cb-item">
                      <div class="cb-icon">{{ b.name.slice(0, 1) }}</div>
                      <div class="cb-name">{{ b.name }}</div>
                    </div>
                  </div>
                </div>
                <div class="card-badges-empty" v-else-if="i === memberLevelIndex">还没有成就徽章，去签到解锁吧~</div>
                <div class="tier-current" v-if="i === tierCurrent">● 当前等级</div>
              </div>
            </div>
          </div>
        </div>
    </div>
      <GrowthCenter />
    </div>

    <!-- ── 会员专属入口（独立界面：新品试吃 / 内测名额 / 专属体验） ── -->
    <div class="excl-entry" @click="go('/exclusive')">
      <div class="excl-entry-icon">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7l4 4 5-6 5 6 4-4v10H3z"/><path d="M3 17h18"/></svg>
      </div>
      <div class="excl-entry-text">
        <div class="excl-entry-title">会员专属</div>
        <div class="excl-entry-sub">新品试吃 · 内测名额 · 专属体验</div>
      </div>
      <div class="excl-entry-arrow">进入 ›</div>
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
import { showSuccessToast, showFailToast } from 'vant'
import { getCheckinStatus, doCheckin } from '@/api'
import GrowthCenter from '@/components/c-end/GrowthCenter.vue'
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
  const phone = member.value && member.value.phone
  if (phone) {
    fetch(`/api/community/badges?phone=${encodeURIComponent(phone)}`)
      .then(r => r.json())
      .then(res => { if (res.ok) badges.value = res.data })
      .catch(() => {})
    getCheckinStatus(phone)
      .then(res => { if (res.ok) { signedToday.value = res.data.today_checked; consecutiveDays.value = res.data.streak; totalCheckin.value = res.data.total } })
      .catch(() => {})
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

// ── 成长值进度（合并进会员当前等级卡；与 GrowthCenter 同一套 LEVELS 逻辑） ──
const GROWTH_LEVELS = [
  { name: '普卡', min: 0, next: 2000 },
  { name: '银卡', min: 2000, next: 5000 },
  { name: '金卡', min: 5000, next: 20000 },
  { name: '钻石卡', min: 20000, next: null },
]
const memberLevelIndex = computed(() => {
  const lv = member.value && member.value.membership_level
  return lv && levelToIndex[lv] != null ? levelToIndex[lv] : 0
})
const growth = computed(() => {
  const lv = (member.value && member.value.membership_level) || '普卡'
  const cur = GROWTH_LEVELS.find(l => l.name === lv) || GROWTH_LEVELS[0]
  const pts = member.value ? (member.value.points || 0) : 0
  if (!cur.next) return { pct: 100, gap: 0, nextName: null, points: pts }
  const pct = Math.max(0, Math.min(100, (pts - cur.min) / (cur.next - cur.min) * 100))
  const gap = Math.max(0, cur.next - pts)
  const nextName = GROWTH_LEVELS[GROWTH_LEVELS.findIndex(l => l.name === lv) + 1]?.name
  return { pct, gap, nextName, points: pts }
})

const tierCurrent = ref(0)
const tierViewport = ref(null)
const badges = ref([])
const earnedBadges = computed(() => badges.value.filter(b => b.earned))
const signedToday = ref(false)
const consecutiveDays = ref(0)
const totalCheckin = ref(0)
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
  { label: '室内导航', route: '/nav', icon: '<polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/>' },
  { label: '会员中心', route: '/member', icon: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>' },
  { label: '关于我们', route: '/about', icon: '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>' },
]

function go(route) { if (route) router.push(route) }

async function doSignCard() {
  if (signedToday.value) return
  const phone = member.value && member.value.phone
  if (!phone) { router.push('/member'); return }
  try {
    const res = await doCheckin(phone)
    if (res.ok) {
      signedToday.value = true
      consecutiveDays.value = (consecutiveDays.value || 0) + 1
      totalCheckin.value = (totalCheckin.value || 0) + 1
      showSuccessToast(`签到 +${res.data.points_gained || 0}分`)
    } else {
      showFailToast(res.error || '签到失败')
    }
  } catch (e) {
    showFailToast('网络错误')
  }
}
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
.uc-name, .uc-phone, .mem-title, .mem-sub,
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
.tier-concepts { margin-top: 4px; }

/* ── 等级卡头部：标题 + 签到钮 ── */
.bc-hd-left { display: flex; align-items: center; gap: 10px; }
.bc-sign-btn {
  flex-shrink: 0; padding: 9px 20px; border-radius: 18px;
  border: 2px solid rgba(255,255,255,0.55);
  background: rgba(255,255,255,0.20); color: #fff;
  font-size: 14px; font-weight: 700; cursor: pointer;
  backdrop-filter: blur(2px); -webkit-backdrop-filter: blur(2px);
  text-shadow: 0 1px 1px rgba(0,0,0,0.30);
}
.bc-sign-btn:active { transform: scale(0.97); }
.bc-sign-btn.signed { background: rgba(0,0,0,0.25); border-color: rgba(255,255,255,0.30); color: rgba(255,255,255,0.85); cursor: default; }
.bc-sign-line { font-size: 12px; color: rgba(255,255,255,0.90); margin-top: 8px; text-shadow: 0 1px 1px rgba(0,0,0,0.25); }
.bc-sign-line b { color: #FFF3D6; }

/* ── 成长值进度（合并进当前等级卡） ── */
.growth-in-card { margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.18); }
.gib-points { font-size: 22px; font-weight: 700; color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,0.30); }
.gib-points em { font-style: normal; font-size: 12px; color: rgba(255,255,255,0.85); font-weight: 400; margin-left: 4px; }
.gib-bar { height: 7px; background: rgba(0,0,0,0.22); border-radius: 4px; overflow: hidden; margin: 6px 0; }
.gib-fill { height: 100%; border-radius: 4px; transition: width 0.4s; }
.gib-hint { font-size: 12px; color: rgba(255,255,255,0.92); text-shadow: 0 1px 1px rgba(0,0,0,0.25); }

/* ── 镶嵌进等级卡的成就徽章：横向滑动，仅显示已解锁 ── */
.card-badges { margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.18); }
.cb-title { font-size: 14px; font-weight: 600; color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,0.35); margin-bottom: 10px; }
.cb-sub { font-size: 11px; color: rgba(255,255,255,0.72); font-weight: 400; margin-left: 4px; }
.cb-strip { display: flex; gap: 10px; overflow-x: auto; scroll-snap-type: x mandatory; -webkit-overflow-scrolling: touch; padding-bottom: 4px; scrollbar-width: none; }
.cb-strip::-webkit-scrollbar { display: none; }
.cb-item { flex: 0 0 auto; width: 76px; box-sizing: border-box; scroll-snap-align: start; text-align: center; }
.cb-icon { width: 42px; height: 42px; border-radius: 50%; margin: 0 auto 6px; display: flex; align-items: center; justify-content: center; font-size: 18px; font-weight: 700; background: linear-gradient(135deg, #C4923A, #A8761F); border: 1px solid #7E5413; color: #fff; box-shadow: inset 0 1px 0 rgba(255,255,255,0.30), 0 2px 6px rgba(196,146,58,0.40); }
.cb-name { font-size: 12px; color: #fff; text-shadow: 0 1px 1px rgba(0,0,0,0.35); }
.card-badges-empty { margin-top: 12px; font-size: 12px; color: rgba(255,255,255,0.75); text-shadow: 0 1px 1px rgba(0,0,0,0.25); }
.tier-line { font-size: 14px; font-weight: 600; line-height: 1.6; opacity: 0.96;
  text-shadow: 0 1px 2px rgba(0,0,0,0.35); }
.tier-current { margin-top: 10px; font-size: 12px; font-weight: 700; letter-spacing: 1px; color: #FFE8B0; opacity: 0.95; }
.bc-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
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

/* ── 会员专属入口卡（跳转独立界面） ── */
.excl-entry {
  position: relative;
  margin: 0 16px 18px;
  background-color: #C9956C;
  border: 3px solid #A87C48;
  border-radius: 16px;
  padding: 16px 18px;
  display: flex; align-items: center; gap: 14px;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20);
}
.excl-entry:active { transform: scale(0.985); }
.excl-entry::before {
  content: ""; position: absolute; inset: 0; border-radius: inherit; pointer-events: none;
  box-shadow: inset 0 2px 3px rgba(255,255,255,0.30), inset 0 -3px 6px rgba(0,0,0,0.20);
  background-image: linear-gradient(135deg, rgba(255,255,255,0.32) 0%, rgba(255,255,255,0.06) 24%, rgba(255,255,255,0) 48%, rgba(0,0,0,0.16) 100%);
}
.excl-entry-icon {
  position: relative; z-index: 1;
  width: 50px; height: 50px; border-radius: 14px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: rgba(255,255,255,0.16);
  box-shadow: inset 1px 1px 2px rgba(255,255,255,0.30), inset -1px -1px 3px rgba(0,0,0,0.20);
}
.excl-entry-icon svg { stroke: #FFFFFF; filter: drop-shadow(0 0.4px 0.5px rgba(0,0,0,0.45)); }
.excl-entry-text { position: relative; z-index: 1; flex: 1; min-width: 0; }
.excl-entry-title { font-size: 17px; font-weight: 800; color: #fff; text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.25); }
.excl-entry-sub { font-size: 12px; color: #fff; margin-top: 3px; opacity: 0.95; text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.2); }
.excl-entry-arrow { position: relative; z-index: 1; flex-shrink: 0; font-size: 14px; font-weight: 700; color: #fff; text-shadow: 0 -1px 1px rgba(0,0,0,0.4); }
</style>
