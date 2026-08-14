<template>
  <div class="mc-page">
    <van-nav-bar title="我的优惠券" left-text="返回" left-arrow @click-left="$router.back()" fixed placeholder />

    <!-- 未登录 -->
    <div v-if="!phone" class="login-tip">
      <p>请先在会员中心绑定手机号后查看</p>
      <van-button round type="primary" @click="$router.push('/member')">去会员中心</van-button>
    </div>

    <template v-else>
      <div v-if="loading" class="loading-state">加载中...</div>

      <!-- 已领取优惠券（可核销） -->
      <div class="sec" v-else>
        <div class="sec-head">
          <span class="sec-en">claimed coupons</span>
          <span class="sec-cn">已领取优惠券</span>
          <span class="sec-badge" v-if="claimedCoupons.length">{{ claimedCoupons.length }}</span>
        </div>

        <div v-if="!claimedCoupons.length" class="empty">还没有领取的优惠券，去「优惠券」领一张吧</div>

        <div v-for="(c, i) in claimedCoupons" :key="c.claim_id" class="cp-card" :class="['sw-' + (i % 6), { redeemed: c.redeemed }]">
          <div class="cp-left">
            <div class="cp-icon-box">
              <svg class="cp-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" v-html="catIcon(c.cat)"></svg>
            </div>
            <div class="cp-info">
              <div class="cp-name">{{ c.shop_name || '海江新天地' }}</div>
              <div class="cp-desc">{{ c.label }}</div>
              <div class="cp-expire">领取于 {{ c.time }}</div>
            </div>
          </div>
          <div class="cp-right">
            <div class="cp-amount"><span class="cp-sign">¥</span>{{ c.amount }}</div>
            <button v-if="!c.redeemed" class="cp-btn" @click="doRedeem(c)">去核销</button>
            <div v-else class="cp-done">已核销 ¥{{ c.redeem_amount || c.amount }}</div>
          </div>
        </div>
      </div>

      <!-- 积分兑换券（已兑换） -->
      <div class="sec" v-if="!loading && redeemRecords.length">
        <div class="sec-head">
          <span class="sec-en">points redeemed</span>
          <span class="sec-cn">积分兑换券</span>
        </div>
        <div v-for="(c, i) in redeemRecords" :key="'r' + i" class="cp-card cp-redeem" :class="'sw-' + (i % 6)">
          <div class="cp-left">
            <div class="cp-icon-box">
              <svg class="cp-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>
            </div>
            <div class="cp-info">
              <div class="cp-name">{{ c.item || '优惠券' }}</div>
              <div class="cp-desc">券码 {{ c.code }}</div>
              <div class="cp-expire">兑换于 {{ c.time }}</div>
            </div>
          </div>
          <div class="cp-right">
            <div class="cp-done">已兑换</div>
          </div>
        </div>
      </div>

      <div class="spacer"></div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useMemberStore } from '@/stores/member'
import { showConfirmDialog, showToast, showDialog } from 'vant'
import { getMyCoupons, redeemMyCoupon } from '@/api'

const memberStore = useMemberStore()
const phone = ref('')
const loading = ref(true)
const coupons = ref([])

const CAT_ICON = {
  food: '<path d="M3 11h18a9 9 0 0 1-18 0z"/><path d="M12 3v3M9 4v2M15 4v2"/>',
  retail: '<path d="M6 8h12l-1 12H7L6 8z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/>',
  parking: '<path d="M5 13l1.5-4.5A2 2 0 0 1 8.4 7h7.2a2 2 0 0 1 1.9 1.5L19 13"/><path d="M4 13h16v5H4z"/><circle cx="7.5" cy="18" r="1.5"/><circle cx="16.5" cy="18" r="1.5"/>',
  fun: '<path d="M12 3l2.5 5.5L20 9.3l-4 4 1 6-5-3-5 3 1-6-4-4 5.5-.8z"/>',
  kids: '<path d="M9 11a3 3 0 1 0 6 0 3 3 0 0 0-6 0z"/><path d="M12 2a3 3 0 0 1 3 3v1a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z"/><path d="M5 21v-2a4 4 0 0 1 4-4h6a4 4 0 0 1 4 4v2"/>',
  service: '<path d="M12 21s-7-4.5-7-10a4 4 0 0 1 7-2.5A4 4 0 0 1 19 11c0 5.5-7 10-7 10z"/>',
}
function catIcon(cat) {
  return CAT_ICON[cat] || '<path d="M3 8a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v2a2 2 0 0 0 0 4v2a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-2a2 2 0 0 0 0-4z"/>'
}

const claimedCoupons = computed(() => coupons.value.filter(c => c.type === 'claim'))
const redeemRecords = computed(() => coupons.value.filter(c => c.type === 'redeem'))

onMounted(async () => {
  memberStore.restore()
  phone.value = memberStore.member?.phone || ''
  if (!phone.value) { loading.value = false; return }
  await load()
})

async function load() {
  loading.value = true
  try {
    const res = await getMyCoupons(phone.value)
    if (res.ok) coupons.value = res.coupons || []
  } catch {}
  loading.value = false
}

async function doRedeem(c) {
  try {
    await showConfirmDialog({
      title: '确认核销',
      message: `确认到店核销「${c.shop_name} - ${c.label}」？核销后该券即作废。`,
      confirmButtonText: '确认核销',
      cancelButtonText: '取消'
    })
  } catch { return }
  try {
    const res = await redeemMyCoupon(phone.value, c.claim_id, c.amount || 0)
    if (res.ok) {
      showToast('核销成功')
      await load()
    } else {
      showDialog({ title: '核销失败', message: res.error || '请稍后重试' })
    }
  } catch { showToast('网络错误') }
}
</script>

<style scoped>
.mc-page { min-height: 100vh; background: #000; padding-bottom: 20px; }
.login-tip { text-align: center; padding: 80px 24px; color: rgba(255,255,255,0.6); }
.login-tip p { margin-bottom: 16px; font-size: 14px; }
.loading-state, .empty { text-align: center; padding: 36px 20px; color: rgba(255,255,255,0.5); font-size: 14px; }

.sec { margin-top: 8px; }
.sec-head { display: flex; flex-direction: column; margin: 20px 16px 12px; position: relative; }
.sec-en { font-family: 'Gayathri', var(--font-primary); font-size: 20px; font-weight: 900; letter-spacing: 1px; color: rgba(255,255,255,0.92); text-transform: capitalize; -webkit-text-stroke: 0.5px rgba(255,255,255,0.3); }
.sec-cn { font-size: var(--fs-headline); font-weight: 400; color: #fff; margin-top: 6px; text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.18); }
.sec-badge { position: absolute; right: 0; top: 6px; background: #FF7B2C; color: #fff; font-size: 12px; font-weight: 700; padding: 2px 10px; border-radius: 12px; }

.cp-card {
  border-radius: 18px; border: 3px solid #9A7425; background-color: #C4923A; padding: 16px;
  display: flex; align-items: center; gap: 12px; margin: 0 16px 12px; box-sizing: border-box;
  box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20);
  transition: transform 0.15s, opacity 0.2s;
}
.cp-card:active { transform: scale(0.985); }
.cp-card.redeemed { opacity: 0.62; }
.cp-card.sw-0 { background-color: #C4923A; border-color: #9A7425; }
.cp-card.sw-1 { background-color: #D4A59A; border-color: #A67D72; }
.cp-card.sw-2 { background-color: #9B4A3E; border-color: #6E332A; }
.cp-card.sw-3 { background-color: #C9956C; border-color: #A87C48; }
.cp-card.sw-4 { background-color: #8B8B90; border-color: #6A6A6E; }
.cp-card.sw-5 { background-color: #6B6E64; border-color: #4E5049; }

.cp-left { display: flex; align-items: center; gap: 12px; flex: 1; min-width: 0; }
.cp-icon-box { width: 46px; height: 46px; border-radius: 14px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; color: #fff; background: rgba(0,0,0,0.18); box-shadow: inset 2px 2px 5px rgba(0,0,0,0.30), inset -1px -1px 3px rgba(255,255,255,0.18); }
.cp-icon { width: 24px; height: 24px; filter: drop-shadow(0 0.4px 0.5px rgba(0,0,0,0.45)); }
.cp-info { flex: 1; min-width: 0; }
.cp-name { font-size: var(--fs-body); font-weight: 700; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-shadow: 0 -1px 1px rgba(0,0,0,0.3), 0 1px 1px rgba(255,255,255,0.2); }
.cp-desc { font-size: var(--fs-secondary); color: #fff; opacity: 0.92; margin-top: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cp-expire { font-size: var(--fs-aux); color: #fff; opacity: 0.72; margin-top: 4px; }

.cp-right { display: flex; flex-direction: column; gap: 8px; align-items: center; flex-shrink: 0; }
.cp-amount { font-size: 26px; font-weight: 800; color: #fff; line-height: 1; text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.25); }
.cp-sign { font-size: 15px; font-weight: 700; margin-right: 1px; }
.cp-btn {
  padding: 7px 18px; border: 3px solid #9A7425; border-radius: 20px; font-size: var(--fs-secondary);
  font-weight: 700; cursor: pointer; font-family: inherit; color: #fff; background: #9A7425;
  box-shadow: inset 3px 3px 7px rgba(0,0,0,0.45), inset -2px -2px 5px rgba(196,146,58,0.45);
  filter: drop-shadow(0 0.6px 1px rgba(0,0,0,0.4)); transition: opacity 0.15s;
}
.cp-btn:active { opacity: 0.82; }
.cp-done { font-size: 13px; font-weight: 700; color: #fff; background: rgba(0,0,0,0.25); padding: 6px 12px; border-radius: 16px; }

.spacer { height: 20px; }
</style>
