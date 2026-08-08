<template>
  <div class="offers-tab">
    <!-- 版块标题（与「我的」页统一） -->
    <div class="section-label">
      <span class="section-en">Coupons</span>
      <span class="section-cn">优惠券</span>
    </div>

    <!-- 分类标签（首页按钮风格） -->
    <div class="cat-scroll">
      <button v-for="c in cats" :key="c.key" class="cat-btn"
        :class="{ active: activeCat === c.key }" @click="activeCat = c.key">
        {{ c.label }}
      </button>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">加载中...</div>

    <!-- 优惠券列表 -->
    <div class="coupon-list" v-else>
      <div v-for="(c, i) in filteredCoupons" :key="c.id" class="coupon-card"
        :class="['sw-' + (i % 6), { claimed: c.claimed }]">
        <div class="c-left">
          <div class="c-icon-box">
            <svg class="c-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" v-html="catIcon(c.cat)"></svg>
          </div>
          <div class="c-info">
            <div class="c-name">{{ c.shop_name || c.name }}</div>
            <div class="c-desc">{{ c.label }}</div>
            <div class="c-expire">有效期至 {{ c.expire }}</div>
          </div>
        </div>
        <div class="c-divider"></div>
        <div class="c-right">
          <div class="c-amount"><span class="c-sign">¥</span>{{ c.amount }}</div>
          <button class="c-btn" :class="{ claimed: c.claimed }"
            @click="claim(c.id)">{{ c.claimed ? '已领取' : '立即领取' }}</button>
        </div>
      </div>
      <div v-if="!filteredCoupons.length" class="empty-state">暂无优惠券</div>
    </div>

    <div class="spacer"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getOffers } from '@/api'

const activeCat = ref('all')
const loading = ref(true)
const cats = [
  { key: 'all', label: '全部' },
  { key: 'food', label: '餐饮券' },
  { key: 'retail', label: '零售券' },
  { key: 'parking', label: '停车券' },
  { key: 'fun', label: '娱乐券' },
]

// 本地兜底（后台异常时也能展示）
const FALLBACK_OFFERS = [
  { id: 1, name: '蜀大侠火锅', label: '满200减50', expire: '2026-12-31', amount: 50, category: 'food' },
  { id: 2, name: '星巴克', label: '买一赠一券', expire: '2026-10-31', amount: 35, category: 'food' },
  { id: 4, name: 'UNIQLO', label: '满299减30', expire: '2026-11-30', amount: 30, category: 'retail' },
  { id: 9, name: '海江新天地', label: '停车券 减10', expire: '2026-12-31', amount: 10, category: 'parking' },
  { id: 6, name: '万达影城', label: '观影立减20', expire: '2026-11-30', amount: 20, category: 'fun' },
]

const coupons = ref([])

onMounted(async () => {
  try {
    const resp = await getOffers()
    if (resp.ok && resp.data && resp.data.length) {
      coupons.value = resp.data.map(c => ({
        id: c.id,
        name: c.shop_name,
        label: c.label,
        expire: c.expire,
        amount: c.amount,
        cat: c.category,
        claimed: false,
      }))
    } else {
      coupons.value = FALLBACK_OFFERS.map(c => ({ ...c, claimed: false }))
    }
  } catch (e) {
    console.error('Failed to load offers:', e)
    coupons.value = FALLBACK_OFFERS.map(c => ({ ...c, claimed: false }))
  } finally {
    loading.value = false
  }
})

const filteredCoupons = computed(() =>
  activeCat.value === 'all' ? coupons.value : coupons.value.filter(c => c.cat === activeCat.value)
)

const CAT_ICON = {
  food: '<path d="M3 11h18a9 9 0 0 1-18 0z"/><path d="M12 3v3M9 4v2M15 4v2"/>',
  retail: '<path d="M6 8h12l-1 12H7L6 8z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/>',
  parking: '<path d="M5 13l1.5-4.5A2 2 0 0 1 8.4 7h7.2a2 2 0 0 1 1.9 1.5L19 13"/><path d="M4 13h16v5H4z"/><circle cx="7.5" cy="18" r="1.5"/><circle cx="16.5" cy="18" r="1.5"/>',
  fun: '<path d="M12 3l2.5 5.5L20 9.3l-4 4 1 6-5-3-5 3 1-6-4-4 5.5-.8z"/>',
}
function catIcon(cat) {
  return CAT_ICON[cat] || '<path d="M3 8a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v2a2 2 0 0 0 0 4v2a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-2a2 2 0 0 0 0-4V8z"/>'
}

function claim(id) {
  const c = coupons.value.find(x => x.id === id)
  if (c && !c.claimed) c.claimed = true
}
</script>

<style scoped>
.offers-tab { padding-bottom: 8px; }

/* ── 版块标题（与「我的」页统一） ── */
.section-label { display: flex; flex-direction: column; margin: 18px 16px 14px; }
.section-en { font-family: 'Gayathri', var(--font-primary); font-size: 22px; font-weight: 900; letter-spacing: 1px; line-height: 1.2; color: rgba(255,255,255,0.92); text-transform: capitalize; -webkit-text-stroke: 0.5px rgba(255,255,255,0.3); }
.section-cn { font-size: var(--fs-headline); font-weight: 400; color: #FFFFFF; margin-top: 8px; text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.18); }

.loading-state, .empty-state {
  text-align: center; padding: 40px 20px; color: rgba(255,255,255,0.5); font-size: 14px;
}

/* ── 分类标签：首页按钮风格 ── */
.cat-scroll { display: flex; gap: 10px; overflow-x: auto; padding: 0 16px 16px; -webkit-overflow-scrolling: touch; }
.cat-scroll::-webkit-scrollbar { display: none; }
.cat-btn {
  flex-shrink: 0; padding: 8px 18px; border: 3px solid #6A6A6E; border-radius: 20px;
  font-size: var(--fs-secondary); font-weight: 600; font-family: inherit; cursor: pointer;
  background: #2A2A2A; color: #BBBBBB;
  box-shadow: 0 2px 6px rgba(0,0,0,0.3);
  transition: all 0.15s;
  white-space: nowrap;
}
.cat-btn.active {
  background: #C4923A; border-color: #9A7425; color: #FFFFFF;
  box-shadow: inset 3px 3px 7px rgba(0,0,0,0.45), inset -2px -2px 5px rgba(196,146,58,0.45);
  filter: drop-shadow(0 0.6px 1px rgba(0,0,0,0.4));
}
.cat-btn:not(.active):active { background: #333; }

/* ── 优惠券卡片：实色多彩（与首页同一套配色） ── */
.coupon-list { display: flex; flex-direction: column; gap: 12px; margin: 0 16px; }
.coupon-card {
  border-radius: 18px;
  border: 3px solid #9A7425;
  background-color: #C4923A;
  padding: 16px;
  display: flex; align-items: center; gap: 12px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20);
  box-sizing: border-box;
  transition: opacity 0.2s, transform 0.15s;
}
.coupon-card:active { transform: scale(0.985); }
.coupon-card.claimed { opacity: 0.6; }
/* 颜色按卡片位置轮询穿插（首页6色），避免同色堆叠 */
.coupon-card.sw-0 { background-color: #C4923A; border-color: #9A7425; }
.coupon-card.sw-1 { background-color: #D4A59A; border-color: #A67D72; }
.coupon-card.sw-2 { background-color: #9B4A3E; border-color: #6E332A; }
.coupon-card.sw-3 { background-color: #C9956C; border-color: #A87C48; }
.coupon-card.sw-4 { background-color: #8B8B90; border-color: #6A6A6E; }
.coupon-card.sw-5 { background-color: #6B6E64; border-color: #4E5049; }

/* 左侧：图标 + 信息 */
.c-left { display: flex; align-items: center; gap: 12px; flex: 1; min-width: 0; }
.c-icon-box {
  width: 48px; height: 48px; border-radius: 14px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  color: #FFFFFF;
  background: rgba(0,0,0,0.18);
  box-shadow: inset 2px 2px 5px rgba(0,0,0,0.30), inset -1px -1px 3px rgba(255,255,255,0.18);
}
.c-icon { width: 26px; height: 26px; filter: drop-shadow(0 0.4px 0.5px rgba(0,0,0,0.45)); }
.c-info { flex: 1; min-width: 0; }
.c-name { font-size: var(--fs-body); font-weight: 700; color: #FFFFFF; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-shadow: 0 -1px 1px rgba(0,0,0,0.3), 0 1px 1px rgba(255,255,255,0.2); }
.c-desc { font-size: var(--fs-secondary); color: #FFFFFF; opacity: 0.9; margin-top: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.c-expire { font-size: var(--fs-aux); color: #FFFFFF; opacity: 0.7; margin-top: 4px; }

/* 票券虚线分隔 */
.c-divider { width: 0; align-self: stretch; margin: 4px 0; border-left: 2px dashed rgba(255,255,255,0.45); }

/* 右侧：金额 + 领取按钮 */
.c-right { display: flex; flex-direction: column; gap: 8px; align-items: center; flex-shrink: 0; }
.c-amount { font-size: 28px; font-weight: 800; color: #FFFFFF; line-height: 1; text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.25); }
.c-sign { font-size: 16px; font-weight: 700; margin-right: 1px; }
.c-btn {
  padding: 7px 16px; border: 3px solid #9A7425; border-radius: 20px;
  font-size: var(--fs-secondary); font-weight: 600; cursor: pointer; font-family: inherit;
  background: #9A7425; color: #FFFFFF;
  box-shadow: inset 3px 3px 7px rgba(0,0,0,0.45), inset -2px -2px 5px rgba(196,146,58,0.45);
  filter: drop-shadow(0 0.6px 1px rgba(0,0,0,0.4));
  transition: opacity 0.15s;
}
.c-btn:active:not(.claimed) { opacity: 0.82; }
.c-btn.claimed { background: #555555; border-color: #444444; box-shadow: inset 3px 3px 7px rgba(0,0,0,0.5); color: #DDDDDD; filter: none; }

/* 按钮配色跟随穿插色（深一档 + 内凹高光） */
.coupon-card.sw-0 .c-btn { background:#9A7425; border-color:#9A7425; box-shadow: inset 3px 3px 7px rgba(0,0,0,0.45), inset -2px -2px 5px rgba(196,146,58,0.45); }
.coupon-card.sw-1 .c-btn { background:#A67D72; border-color:#A67D72; box-shadow: inset 3px 3px 7px rgba(0,0,0,0.45), inset -2px -2px 5px rgba(212,165,154,0.45); }
.coupon-card.sw-2 .c-btn { background:#6E332A; border-color:#6E332A; box-shadow: inset 3px 3px 7px rgba(0,0,0,0.45), inset -2px -2px 5px rgba(155,74,62,0.45); }
.coupon-card.sw-3 .c-btn { background:#A87C48; border-color:#A87C48; box-shadow: inset 3px 3px 7px rgba(0,0,0,0.45), inset -2px -2px 5px rgba(201,149,108,0.45); }
.coupon-card.sw-4 .c-btn { background:#6A6A6E; border-color:#6A6A6E; box-shadow: inset 3px 3px 7px rgba(0,0,0,0.45), inset -2px -2px 5px rgba(139,139,144,0.45); }
.coupon-card.sw-5 .c-btn { background:#4E5049; border-color:#4E5049; box-shadow: inset 3px 3px 7px rgba(0,0,0,0.45), inset -2px -2px 5px rgba(107,110,100,0.45); }

.spacer { height: 24px; }
</style>
