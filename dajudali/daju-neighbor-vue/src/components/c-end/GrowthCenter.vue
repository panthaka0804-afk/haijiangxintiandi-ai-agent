<template>
  <div class="gc-wrap">
    <div v-if="!phone" class="gc-empty">
      <div class="empty-title">请先登录会员</div>
      <div class="empty-hint">登录后可签到、攒成长值、领徽章</div>
      <van-button round block type="primary" class="gc-login-btn" @click="goLogin">去登录</van-button>
    </div>

    <template v-else>
      <!-- 周三会员日 -->
      <div class="memberday-card" :style="memberDayStyle">
        <div class="md-info">
          <div class="md-title">周三会员日</div>
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

      <!-- 成长值明细（默认折叠，点击展开） -->
      <div class="log-section">
        <div class="section-title log-toggle" @click="toggleLogs">
          <span>成长值明细</span>
          <span class="log-chevron" :class="{ open: logsOpen }">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
          </span>
        </div>
        <div v-show="logsOpen">
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
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useMemberStore } from '@/stores/member'
import { showSuccessToast, showFailToast } from 'vant'
import { getMemberDayStatus, claimMemberDay } from '@/api'

const memberStore = useMemberStore()

const phone = ref('')
const logs = ref([])
const logsOpen = ref(false)

// 多彩卡片配色（对齐首页）
const memberDayStyle = { background: 'linear-gradient(135deg,#9B4A3E,#7A342B)', borderColor: '#5C241D' }
const isWednesday = computed(() => new Date().getDay() === 3)
const memberDay = ref({ claimed: false, coupon_label: '' })

function toggleLogs() { logsOpen.value = !logsOpen.value }

async function load() {
  if (!phone.value) return
  try {
    const [logRes, mdRes] = await Promise.all([
      fetch(`/api/community/points/log?phone=${phone.value}`).then(r => r.json()),
      getMemberDayStatus(phone.value),
    ])
    if (logRes.ok) logs.value = logRes.data
    if (mdRes.ok) memberDay.value = { claimed: mdRes.data.claimed, coupon_label: mdRes.data.coupon_label }
  } catch (e) {
    console.error(e)
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

function goLogin() {
  router.push('/member')
}

onMounted(() => {
  const m = memberStore.member
  if (m && m.phone) {
    phone.value = m.phone
    load()
  }
})
</script>

<style scoped>
.gc-wrap { margin: 0; }

/* 登录提示 */
.gc-empty { padding: 28px 16px; text-align: center; color: #999; }
.gc-empty .empty-title { font-size: 18px; color: #eee; margin-bottom: 8px; }
.gc-empty .empty-hint { font-size: 14px; }
.gc-login-btn { background: #9A7425; border-color: #9A7425; margin-top: 16px; box-shadow: inset 3px 3px 7px rgba(0, 0, 0, 0.45), inset -2px -2px 5px rgba(196,146,58,0.45); }

/* 周三会员日卡 — 深红棕多彩卡 */
.memberday-card { margin: 0 0 12px; padding: 16px; background: linear-gradient(135deg, #9B4A3E 0%, #7A342B 100%); border: 3px solid #5C241D; border-radius: 16px; display: flex; align-items: center; justify-content: space-between; box-shadow: inset 0 1px 0 rgba(255,255,255,0.20), 0 4px 14px rgba(155,74,62,0.35); }
.md-title { font-size: 16px; color: #fff; font-weight: 600; text-shadow: 0 1px 2px rgba(0,0,0,0.35); }
.md-sub { font-size: 12px; color: rgba(255,255,255,0.92); margin-top: 4px; }
.md-sub b { color: #FFF3D6; }
.md-got { font-size: 11px; color: #FFF3D6; margin-top: 4px; }
.md-btn { padding: 12px 20px; border-radius: 20px; border: 3px solid #9A7425; background-color: #9A7425; color: #FFFFFF; font-size: 14px; font-weight: 600; cursor: pointer; flex-shrink: 0; white-space: nowrap; box-shadow: inset 3px 3px 7px rgba(0, 0, 0, 0.45), inset -2px -2px 5px rgba(196,146,58,0.45); filter: drop-shadow(0 0.6px 1px rgba(0, 0, 0, 0.4)); }
.md-btn.got { background: #5C241D; border-color: #5C241D; color: #fff; cursor: default; box-shadow: inset 3px 3px 7px rgba(0,0,0,0.55), inset -2px -2px 5px rgba(155,74,62,0.45); }
.md-btn.off { background: #5C241D; border-color: #5C241D; color: rgba(255,255,255,0.85); box-shadow: inset 3px 3px 7px rgba(0,0,0,0.55), inset -2px -2px 5px rgba(155,74,62,0.45); }

/* 成长值明细标题（沿用 section-title） */
.section-title { font-size: 16px; color: #fff; font-weight: 600; margin-bottom: 12px; }
.section-sub { font-size: 12px; color: #999; font-weight: 400; }

/* 成长值明细 — 深灰绿多彩卡；标题可点击折叠 */
.log-section { margin: 0; }
.log-toggle { display: flex; align-items: center; justify-content: space-between; cursor: pointer; margin-bottom: 10px; user-select: none; }
.log-chevron { display: inline-flex; color: rgba(255,255,255,0.85); transition: transform 0.25s ease; }
.log-chevron.open { transform: rotate(180deg); }
.log-list { background: linear-gradient(135deg, #6B6E64 0%, #565952 100%); border: 3px solid #44463F; border-radius: 14px; overflow: hidden; box-shadow: inset 0 1px 0 rgba(255,255,255,0.18), 0 4px 12px rgba(0,0,0,0.30); }
.log-item { display: flex; align-items: center; justify-content: space-between; padding: 12px 14px; border-bottom: 1px solid rgba(0,0,0,0.22); }
.log-item:last-child { border-bottom: none; }
.log-remark { font-size: 14px; color: #fff; text-shadow: 0 1px 1px rgba(0,0,0,0.25); }
.log-time { font-size: 11px; color: rgba(255,255,255,0.70); margin-top: 2px; }
.log-points { font-size: 16px; font-weight: 700; color: #FFF3D6; }
.log-points.minus { color: #D6E8D5; }
.log-empty { padding: 24px; text-align: center; color: rgba(255,255,255,0.80); font-size: 13px; }
</style>
