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

      <!-- 签到区 -->
      <div class="sign-card">
        <div class="sign-info">
          <div class="sign-title">每日签到</div>
          <div class="sign-days">已连续签到 <b>{{ consecutiveDays }}</b> 天 · 连续 7 天额外 +20</div>
        </div>
        <button class="sign-btn" :class="{ signed: signedToday }" :disabled="signedToday" @click="doSign">
          {{ signedToday ? '今日已签' : '签到 +5' }}
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
import { showToast } from 'vant'

const memberStore = useMemberStore()

const phone = ref('')
const points = ref(0)
const level = ref('普卡')
const signedToday = ref(false)
const consecutiveDays = ref(0)
const badges = ref([])
const logs = ref([])

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
    const [statusRes, badgeRes, logRes] = await Promise.all([
      fetch(`/api/community/sign-status?phone=${phone.value}`).then(r => r.json()),
      fetch(`/api/community/badges?phone=${phone.value}`).then(r => r.json()),
      fetch(`/api/community/points/log?phone=${phone.value}`).then(r => r.json()),
    ])
    if (statusRes.ok) {
      signedToday.value = statusRes.data.signed_today
      consecutiveDays.value = statusRes.data.consecutive_days || 0
    }
    if (badgeRes.ok) badges.value = badgeRes.data
    if (logRes.ok) logs.value = logRes.data
  } catch (e) {
    console.error(e)
  }
}

async function doSign() {
  if (signedToday.value) return
  try {
    const res = await fetch('/api/community/sign-in', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone: phone.value }),
    }).then(r => r.json())
    if (res.ok) {
      const d = res.data
      points.value = d.points
      level.value = d.level || level.value
      signedToday.value = true
      consecutiveDays.value = d.consecutive_days
      showToast(`签到成功 +${d.award} 成长值`)
      if (d.level_up) showToast(`恭喜升级为${d.level_up}！`)
      if (d.new_badges && d.new_badges.length) showToast(`获得新徽章！`)
      load()
    } else {
      showToast(res.error || '签到失败')
    }
  } catch (e) {
    showToast('网络错误')
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

.growth-card { margin: 16px; padding: 18px 16px; background: #1a1a1a; border: 1px solid #2e2e2e; border-radius: 16px; }
.growth-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.growth-level { padding: 4px 12px; border-radius: 14px; border: 1px solid; font-size: 13px; color: #fff; }
.growth-points { font-size: 26px; font-weight: 700; color: #fff; }
.growth-points em { font-style: normal; font-size: 13px; color: #999; font-weight: 400; margin-left: 4px; }
.growth-bar { height: 8px; background: #2e2e2e; border-radius: 4px; overflow: hidden; margin-bottom: 8px; }
.growth-bar-fill { height: 100%; border-radius: 4px; transition: width 0.4s; }
.growth-hint { font-size: 12px; color: #999; }

.sign-card { margin: 0 16px 16px; padding: 16px; background: #1a1a1a; border: 1px solid #2e2e2e; border-radius: 16px; display: flex; align-items: center; justify-content: space-between; }
.sign-title { font-size: 16px; color: #fff; font-weight: 600; }
.sign-days { font-size: 12px; color: #999; margin-top: 4px; }
.sign-days b { color: #FF7B2C; }
.sign-btn { padding: 12px 22px; border-radius: 22px; border: none; background: linear-gradient(135deg, #FF7B2C, #E85D04); color: #fff; font-size: 15px; font-weight: 600; cursor: pointer; }
.sign-btn.signed { background: #2e2e2e; color: #888; cursor: default; }

.badge-section { margin: 0 16px 16px; }
.section-title { font-size: 16px; color: #fff; font-weight: 600; margin-bottom: 12px; }
.section-sub { font-size: 12px; color: #999; font-weight: 400; }
.badge-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.badge-item { background: #1a1a1a; border: 1px solid #2e2e2e; border-radius: 12px; padding: 12px 6px; text-align: center; }
.badge-icon { width: 40px; height: 40px; border-radius: 50%; margin: 0 auto 8px; display: flex; align-items: center; justify-content: center; font-size: 18px; font-weight: 700; background: #2e2e2e; color: #666; border: 1px solid #444; }
.badge-item.earned .badge-icon { background: #C4923A; border-color: #9A7425; color: #fff; }
.badge-name { font-size: 13px; color: #eee; }
.badge-item:not(.earned) .badge-name { color: #888; }
.badge-desc { font-size: 10px; color: #666; margin-top: 3px; line-height: 1.3; }

.log-section { margin: 0 16px; }
.log-list { background: #1a1a1a; border: 1px solid #2e2e2e; border-radius: 12px; overflow: hidden; }
.log-item { display: flex; align-items: center; justify-content: space-between; padding: 12px 14px; border-bottom: 1px solid #2e2e2e; }
.log-item:last-child { border-bottom: none; }
.log-remark { font-size: 14px; color: #eee; }
.log-time { font-size: 11px; color: #666; margin-top: 2px; }
.log-points { font-size: 16px; font-weight: 700; color: #FF7B2C; }
.log-points.minus { color: #3E8E41; }
.log-empty { padding: 24px; text-align: center; color: #888; font-size: 13px; }
</style>
