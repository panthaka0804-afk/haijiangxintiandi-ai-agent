<template>
  <div class="points-page">
    <van-nav-bar title="激励中心" left-text="返回" left-arrow @click-left="$router.back()" fixed placeholder />

    <!-- 未登录提示 -->
    <div v-if="!phone" class="points-empty">
      <div class="empty-title">请先登录会员</div>
      <div class="empty-hint">登录后可签到、攒成长值、领徽章</div>
      <van-button round block type="primary" style="margin-top:16px" @click="$router.push('/member')">去登录</van-button>
    </div>

    <template v-else>
      <!-- 成长值卡片 -->
      <div class="growth-card">
        <div class="growth-top">
          <span class="growth-level" :style="{ background: theme.bg, borderColor: theme.bd }">{{ level }}</span>
          <span class="growth-points">{{ points }} <em>成长值</em></span>
        </div>
        <div class="growth-bar">
          <div class="growth-bar-fill" :style="{ width: progress.pct + '%', background: theme.accent }"></div>
        </div>
        <div class="growth-hint" v-if="progress.nextName">距离「{{ progress.nextName }}」还差 {{ progress.gap }} 成长值</div>
        <div class="growth-hint" v-else>已是最高等级，尊享全部权益</div>
      </div>

      <!-- 签到抽奖区 -->
      <div class="sign-card" :style="checkinStyle">
        <div class="sign-info">
          <div class="sign-title">每日签到抽奖 🎁</div>
          <div class="sign-days">已连续签到 <b>{{ consecutiveDays }}</b> 天 · 累计 {{ totalCheckin }} 天 · 随机 5–50 分，还有机会抽券</div>
          <div v-if="lastCoupon" class="sign-coupon">🎉 上次抽中：{{ lastCoupon }}</div>
        </div>
        <button class="sign-btn" :class="{ signed: signedToday }" :disabled="signedToday" @click="doSign">
          {{ signedToday ? '今日已签' : '签到抽奖' }}
        </button>
      </div>

      <!-- 周三会员日 -->
      <div class="memberday-card" :style="memberDayStyle">
        <div class="md-info">
          <div class="md-title">周三会员日 ☕🥐</div>
          <div class="md-sub">
            <template v-if="memberDay.claimed">本周已领：<b>{{ memberDay.coupon_label }}</b></template>
            <template v-else-if="isWednesday">星巴克 / 烘焙特价券待领取</template>
            <template v-else>每周三 0 点开抢，星巴克·烘焙专属券</template>
          </div>
          <div v-if="memberDay.claimed" class="md-got">已存入「我的券」</div>
        </div>
        <button class="md-btn" :class="{ got: memberDay.claimed, off: !isWednesday && !memberDay.claimed }"
          :disabled="memberDay.claimed || !isWednesday" @click="claimMd">
          {{ memberDay.claimed ? '已领取' : (isWednesday ? '立即领取' : '周三再来') }}
        </button>
      </div>

      <!-- 徽章墙 -->
      <div class="badge-section">
        <div class="section-title">成就徽章 <span class="section-sub">（{{ earnedCount }} / {{ badges.length }}）</span></div>
        <div class="badge-grid">
          <div v-for="b in badges" :key="b.code" class="badge-item" :class="{ earned: b.earned }">
            <div class="badge-icon" :style="b.earned ? { background: '#C4923A', borderColor: '#9A7425', color: '#fff' } : {}">{{ b.name.slice(0, 1) }}</div>
            <div class="badge-name">{{ b.name }}</div>
            <div class="badge-desc">{{ b.description }}</div>
          </div>
        </div>
      </div>

      <!-- 成长值明细 -->
      <div class="log-section">
        <div class="section-title">成长值明细</div>
        <div v-if="logs.length" class="log-list">
          <div v-for="l in logs" :key="l.id" class="log-item">
            <div class="log-left">
              <div class="log-remark">{{ l.remark }}</div>
              <div class="log-time">{{ l.created_at }}</div>
            </div>
            <div class="log-points" :class="{ minus: l.points < 0 }">{{ l.points > 0 ? '+' : '' }}{{ l.points }}</div>
          </div>
        </div>
        <div v-else class="log-empty">还没有成长值记录，先去签到吧~</div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useMemberStore } from '@/stores/member'
import { showToast, showSuccessToast, showFailToast } from 'vant'
import { getCheckinStatus, doCheckin, getMemberDayStatus, claimMemberDay } from '@/api'

const memberStore = useMemberStore()

const phone = ref('')
const points = ref(0)
const level = ref('普卡')
const signedToday = ref(false)
const consecutiveDays = ref(0)
const totalCheckin = ref(0)
const lastCoupon = ref('')
const badges = ref([])
const logs = ref([])

// 多彩卡片配色（对齐首页）
const checkinStyle = { background: 'linear-gradient(135deg,#C4923A,#A8761F)', borderColor: '#7E5413' }
const memberDayStyle = { background: 'linear-gradient(135deg,#9B4A3E,#7A342B)', borderColor: '#5C241D' }
const isWednesday = computed(() => new Date().getDay() === 3)
const memberDay = ref({ claimed: false, coupon_label: '' })

const theme = computed(() => memberStore.levelTheme(level.value))
const earnedCount = computed(() => badges.value.filter(b => b.earned).length)

const LEVELS = [
  { name: '普卡', min: 0, next: 2000 },
  { name: '银卡', min: 2000, next: 5000 },
  { name: '金卡', min: 5000, next: 20000 },
  { name: '钻石卡', min: 20000, next: null },
]

const progress = computed(() => {
  const cur = LEVELS.find(l => l.name === level.value) || LEVELS[0]
  if (!cur.next) return { pct: 100, gap: 0, nextName: null }
  const pct = Math.max(0, Math.min(100, (points.value - cur.min) / (cur.next - cur.min) * 100))
  const gap = Math.max(0, cur.next - points.value)
  const nextName = LEVELS[LEVELS.findIndex(l => l.name === level.value) + 1]?.name
  return { pct, gap, nextName }
})

async function load() {
  if (!phone.value) return
  try {
    const [statusRes, badgeRes, logRes, checkinRes, mdRes] = await Promise.all([
      fetch(`/api/community/sign-status?phone=${phone.value}`).then(r => r.json()),
      fetch(`/api/community/badges?phone=${phone.value}`).then(r => r.json()),
      fetch(`/api/community/points/log?phone=${phone.value}`).then(r => r.json()),
      getCheckinStatus(phone.value),
      getMemberDayStatus(phone.value),
    ])
    if (statusRes.ok) {
      signedToday.value = statusRes.data.signed_today
      consecutiveDays.value = statusRes.data.consecutive_days || 0
    }
    if (badgeRes.ok) badges.value = badgeRes.data
    if (logRes.ok) logs.value = logRes.data
    if (checkinRes.ok) {
      const d = checkinRes.data
      signedToday.value = d.today_checked
      consecutiveDays.value = d.streak
      totalCheckin.value = d.total
      lastCoupon.value = d.today_coupon || ''
    }
    if (mdRes.ok) memberDay.value = { claimed: mdRes.data.claimed, coupon_label: mdRes.data.coupon_label }
  } catch (e) {
    console.error(e)
  }
}

async function doSign() {
  if (signedToday.value) return
  try {
    const res = await doCheckin(phone.value)
    if (res.ok) {
      const d = res.data
      points.value = (points.value || 0) + (d.points_gained || 0)
      signedToday.value = true
      consecutiveDays.value = (consecutiveDays.value || 0) + 1
      totalCheckin.value = (totalCheckin.value || 0) + 1
      lastCoupon.value = d.coupon_won ? d.coupon_label : ''
      showSuccessToast(d.coupon_won ? (`签到 +${d.points_gained}分，抽中：${d.coupon_label}`) : (`签到 +${d.points_gained}分`))
      load()
    } else {
      showFailToast(res.error || '签到失败')
    }
  } catch (e) {
    showFailToast('网络错误')
  }
}

async function claimMd() {
  if (memberDay.value.claimed || !isWednesday.value) return
  try {
    const res = await claimMemberDay(phone.value)
    if (res.ok) {
      memberDay.value = { claimed: true, coupon_label: res.data.coupon_label }
      showSuccessToast('会员日专享券已到账：' + res.data.coupon_label)
    } else {
      showFailToast(res.error || '领取失败')
    }
  } catch (e) {
    showFailToast('网络错误')
  }
}

onMounted(() => {
  const m = memberStore.member
  if (m && m.phone) {
    phone.value = m.phone
    points.value = m.points || 0
    level.value = m.membership_level || m.level || '普卡'
    load()
  }
})
</script>

<style scoped>
.points-page { min-height: 100vh; background: #000; padding-bottom: 24px; }
.points-empty { padding: 40px 24px; text-align: center; color: #999; }
.empty-title { font-size: 18px; color: #eee; margin-bottom: 8px; }
.empty-hint { font-size: 14px; }
.points-empty .van-button { background: #C4923A; border-color: #9A7425; }

/* 成长值卡片 — 银灰多彩卡（渐变实色底 + 深边框 + 内高光） */
.growth-card { margin: 16px; padding: 18px 16px; background: linear-gradient(135deg, #9CA1A8 0%, #7A7E84 100%); border: 3px solid #6A6E74; border-radius: 18px; box-shadow: inset 0 1px 0 rgba(255,255,255,0.22), 0 4px 14px rgba(0,0,0,0.35); }
.growth-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.growth-level { padding: 4px 12px; border-radius: 14px; border: 1px solid rgba(255,255,255,0.55); font-size: 13px; color: #fff; text-shadow: 0 1px 1px rgba(0,0,0,0.30); }
.growth-points { font-size: 26px; font-weight: 700; color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,0.30); }
.growth-points em { font-style: normal; font-size: 13px; color: rgba(255,255,255,0.85); font-weight: 400; margin-left: 4px; }
.growth-bar { height: 8px; background: rgba(0,0,0,0.22); border-radius: 4px; overflow: hidden; margin-bottom: 8px; }
.growth-bar-fill { height: 100%; border-radius: 4px; transition: width 0.4s; }
.growth-hint { font-size: 12px; color: rgba(255,255,255,0.92); text-shadow: 0 1px 1px rgba(0,0,0,0.25); }

/* 签到抽奖卡 — 金黄多彩卡 */
.sign-card { margin: 0 16px 16px; padding: 16px; background: linear-gradient(135deg, #C4923A 0%, #A8761F 100%); border: 3px solid #7E5413; border-radius: 16px; display: flex; align-items: center; justify-content: space-between; box-shadow: inset 0 1px 0 rgba(255,255,255,0.22), 0 4px 14px rgba(196,146,58,0.35); }
.sign-title { font-size: 16px; color: #fff; font-weight: 600; text-shadow: 0 1px 2px rgba(0,0,0,0.30); }
.sign-days { font-size: 12px; color: rgba(255,255,255,0.92); margin-top: 4px; }
.sign-days b { color: #FFF3D6; }
.sign-btn { padding: 12px 22px; border-radius: 22px; border: none; background: #fff; color: #A8761F; font-size: 15px; font-weight: 700; cursor: pointer; box-shadow: 0 2px 8px rgba(0,0,0,0.25); }
.sign-btn.signed { background: rgba(0,0,0,0.30); color: rgba(255,255,255,0.85); cursor: default; box-shadow: none; }
.sign-coupon { font-size: 12px; color: #FFF3D6; margin-top: 6px; }

/* 周三会员日卡 — 深红棕多彩卡 */
.memberday-card { margin: 0 16px 16px; padding: 16px; background: linear-gradient(135deg, #9B4A3E 0%, #7A342B 100%); border: 3px solid #5C241D; border-radius: 16px; display: flex; align-items: center; justify-content: space-between; box-shadow: inset 0 1px 0 rgba(255,255,255,0.20), 0 4px 14px rgba(155,74,62,0.35); }
.md-title { font-size: 16px; color: #fff; font-weight: 600; text-shadow: 0 1px 2px rgba(0,0,0,0.35); }
.md-sub { font-size: 12px; color: rgba(255,255,255,0.92); margin-top: 4px; }
.md-sub b { color: #FFF3D6; }
.md-got { font-size: 11px; color: #FFF3D6; margin-top: 4px; }
.md-btn { padding: 12px 20px; border-radius: 22px; border: none; background: #fff; color: #7A342B; font-size: 14px; font-weight: 700; cursor: pointer; flex-shrink: 0; }
.md-btn.got { background: rgba(255,255,255,0.25); color: #fff; cursor: default; }
.md-btn.off { background: rgba(255,255,255,0.18); color: rgba(255,255,255,0.8); }

/* 徽章墙 — 玻璃容器 + 多彩徽章 */
.badge-section { margin: 0 16px 16px; }
.section-title { font-size: 16px; color: #fff; font-weight: 600; margin-bottom: 12px; }
.section-sub { font-size: 12px; color: #999; font-weight: 400; }
.badge-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.badge-item { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.14); border-radius: 12px; padding: 12px 6px; text-align: center; }
.badge-icon { width: 40px; height: 40px; border-radius: 50%; margin: 0 auto 8px; display: flex; align-items: center; justify-content: center; font-size: 18px; font-weight: 700; background: rgba(255,255,255,0.10); color: #888; border: 1px solid rgba(255,255,255,0.18); }
.badge-item.earned .badge-icon { background: linear-gradient(135deg, #C4923A, #A8761F); border-color: #7E5413; color: #fff; box-shadow: inset 0 1px 0 rgba(255,255,255,0.30), 0 2px 6px rgba(196,146,58,0.40); }
.badge-name { font-size: 13px; color: #eee; }
.badge-item:not(.earned) .badge-name { color: #888; }
.badge-desc { font-size: 10px; color: #777; margin-top: 3px; line-height: 1.3; }

/* 成长值明细 — 深灰绿多彩卡 */
.log-section { margin: 0 16px; }
.log-list { background: linear-gradient(135deg, #6B6E64 0%, #565952 100%); border: 3px solid #44463F; border-radius: 14px; overflow: hidden; box-shadow: inset 0 1px 0 rgba(255,255,255,0.18), 0 4px 12px rgba(0,0,0,0.30); }
.log-item { display: flex; align-items: center; justify-content: space-between; padding: 12px 14px; border-bottom: 1px solid rgba(0,0,0,0.22); }
.log-item:last-child { border-bottom: none; }
.log-remark { font-size: 14px; color: #fff; text-shadow: 0 1px 1px rgba(0,0,0,0.25); }
.log-time { font-size: 11px; color: rgba(255,255,255,0.70); margin-top: 2px; }
.log-points { font-size: 16px; font-weight: 700; color: #FFF3D6; }
.log-points.minus { color: #D6E8D5; }
.log-empty { padding: 24px; text-align: center; color: rgba(255,255,255,0.80); font-size: 13px; }
</style>
