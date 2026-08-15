<template>
  <div class="rd-page">
    <div class="rd-back" @click="$router.back()">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#AAA" stroke-width="2" stroke-linecap="round"><polyline points="15 18 9 12 15 6"/></svg>
    </div>

    <div class="rd-hero">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 12v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-8"/><path d="M22 7H2v5h20z"/></svg>
    </div>

    <div class="rd-body">
      <div class="rd-name">{{ goods.name }}</div>
      <div class="rd-pts">{{ goods.points }} 积分</div>
      <div class="rd-card">
        <div class="rd-row">
          <span>当前积分</span>
          <span class="rd-row-val">{{ currentPoints }}</span>
        </div>
        <div class="rd-row">
          <span>兑换消耗</span>
          <span class="rd-row-val rd-cost">{{ goods.points }}</span>
        </div>
        <div class="rd-row">
          <span>兑换后剩余</span>
          <span class="rd-row-val" :class="{ 'rd-lack': afterPoints < 0 }">{{ afterPoints < 0 ? '积分不足' : afterPoints }}</span>
        </div>
      </div>
      <div class="rd-desc-card">
        <div class="rd-desc-title">使用说明</div>
        <p>兑换后自动发放至"我的优惠券"，到店出示即可使用。有效期30天，过期不可退。如有疑问请联系客服。</p>
      </div>
    </div>

    <div class="rd-actions">
      <button class="rd-cancel" @click="$router.back()">取消</button>
      <button class="rd-confirm"
        :disabled="redeeming || redeemed || afterPoints < 0"
        @click="doRedeem">
        {{ redeemed ? '已兑换 ✓' : (afterPoints < 0 ? '积分不足' : (redeeming ? '兑换中…' : '确认兑换')) }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getRedeemCatalog, redeemPoints } from '@/api'
import { useMemberStore } from '@/stores/member'
import { ElMessage } from 'element-plus'

const route = useRoute()
const memberStore = useMemberStore()

const goods = ref({ name: '兑换商品', points: 0, id: null })
const redeeming = ref(false)
const redeemed = ref(false)

onMounted(async () => {
  memberStore.restore()
  const id = Number(route.params.id)
  try {
    const resp = await getRedeemCatalog()
    if (resp.ok && resp.data) {
      const item = resp.data.find(g => Number(g.id) === id)
      if (item) goods.value = { ...item, points: item.cost, id: Number(item.id) }
    }
  } catch (e) { /* 用兜底展示 */ }
})

// 真实当前积分（来自会员 store，未登录为 0）
const currentPoints = computed(() => (memberStore.member && memberStore.member.points) || 0)
const afterPoints = computed(() => currentPoints.value - (goods.value.points || 0))

async function doRedeem() {
  const phone = memberStore.member && memberStore.member.phone
  if (!phone) {
    ElMessage.warning('请先登录 / 绑定手机号后再兑换')
    return
  }
  if (redeeming.value || redeemed.value) return
  if (afterPoints.value < 0) {
    ElMessage.warning('积分不足，无法兑换')
    return
  }
  redeeming.value = true
  try {
    const d = await redeemPoints(phone, goods.value.id)
    if (d.ok) {
      redeemed.value = true
      const after = d.redemption && d.redemption.after_points
      if (after !== undefined && after !== null && memberStore.member) {
        memberStore.setMember({ ...memberStore.member, points: after })
      }
      ElMessage.success('兑换成功，券已发放至「我的优惠券」')
    } else {
      ElMessage.error(d.error || '兑换失败')
    }
  } catch (e) {
    ElMessage.error('网络错误，请稍后重试')
  } finally {
    redeeming.value = false
  }
}
</script>

<style scoped>
.rd-page { min-height: 100vh; background: #000000; }
.rd-back { padding: 12px; cursor: pointer; }

.rd-hero { height: 180px; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #C4923A, #A8761F); }

.rd-body { padding: 20px 12px 0; }
.rd-name { font-size: 22px; font-weight: 700; color: #FFFFFF; text-align: center; text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.25); }
.rd-pts { font-size: 28px; font-weight: 800; color: #FFFFFF; text-align: center; margin-top: 6px; text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.25); }

.rd-card {
  margin-top: 16px; background-color: #6B6E64; border: 3px solid #4E5049; border-radius: 14px; padding: 4px 0;
  box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20);
}
.rd-row { display: flex; justify-content: space-between; padding: 14px 16px; font-size: 14px; color: rgba(255,255,255,0.85); }
.rd-row:not(:last-child) { border-bottom: 0.5px solid rgba(255,255,255,0.18); }
.rd-row-val { color: #FFFFFF; font-weight: 500; text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.25); }
.rd-cost { color: #FFFFFF; font-weight: 700; text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.25); }
.rd-lack { color: #F56C6C !important; font-weight: 700; }

.rd-desc-card { margin-top: 12px; background-color: #8B8B90; border: 3px solid #6A6A6E; border-radius: 14px; padding: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20); }
.rd-desc-title { font-size: 14px; font-weight: 600; color: rgba(255,255,255,0.9); margin-bottom: 8px; text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.25); }
.rd-desc-card p { margin: 0; font-size: 14px; color: #FFFFFF; line-height: 1.7; text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.25); }

.rd-actions { position: fixed; bottom: 0; left: 0; right: 0; padding: 12px 16px calc(20px + env(safe-area-inset-bottom, 0px)); display: flex; gap: 12px; background: linear-gradient(transparent, #000000 40%); }
.rd-cancel, .rd-confirm { flex: 1; padding: 14px; border: 3px solid #4E5049; border-radius: 20px; font-size: 15px; font-weight: 600; cursor: pointer; font-family: inherit; color: #fff; }
.rd-cancel { background-color: #4E5049; box-shadow: inset 3px 3px 7px rgba(0,0,0,0.45), inset -2px -2px 5px rgba(107,110,100,0.45); filter: drop-shadow(0 0.6px 1px rgba(0,0,0,0.4)); }
.rd-confirm { background-color: #9A7425; border-color: #9A7425; box-shadow: inset 3px 3px 7px rgba(0,0,0,0.45), inset -2px -2px 5px rgba(196,146,58,0.45); filter: drop-shadow(0 0.6px 1px rgba(0,0,0,0.4)); }
.rd-cancel:active, .rd-confirm:active:not(:disabled) { opacity: 0.82; }
.rd-confirm:disabled { background-color: #4E5049; border-color: #4E5049; color: #BBB; box-shadow: inset 3px 3px 7px rgba(0,0,0,0.5); filter: none; cursor: not-allowed; }
</style>
