<template>
  <div class="rp-page">
    <div class="rp-pts-card" :style="{ '--ac-bg': theme.bg, '--ac-bd': theme.bd, '--ac-accent': theme.accent }">
      <div class="rp-pts-shine"></div>
      <div class="rp-pts-ring"></div>
      <div class="rp-pts-level">{{ memberStore.member ? (memberStore.member.membership_level || '普卡') : '未登录' }} · {{ memberStore.member && memberStore.member.discount ? memberStore.member.discount + '折' : '' }}</div>
      <div class="rp-pts-num">{{ memberStore.member ? (memberStore.member.points || 0) : '--' }}</div>
      <div class="rp-pts-label">可用积分</div>
    </div>

    <div class="rp-tabs">
      <button class="rp-tab-btn" :class="{ active: viewTab === 'mall' }" @click="viewTab = 'mall'">积分商城</button>
      <button class="rp-tab-btn" :class="{ active: viewTab === 'records' }" @click="openRecords">兑换记录</button>
    </div>

    <!-- 积分商城 -->
    <template v-if="viewTab === 'mall'">
      <div class="rp-cats">
        <button v-for="c in cats" :key="c" class="rp-cat-btn" :class="{ active: activeCat === c }" @click="activeCat = c">{{ c }}</button>
      </div>

      <!-- 加载状态 -->
      <div v-if="loading" class="loading-state">加载中...</div>

      <div class="rp-grid" v-else>
        <div v-for="(g, i) in decorated" :key="g.id" class="rp-item" :style="{ '--ac-bg': g.bg, '--ac-bd': g.bd }" @click="$router.push(`/redeem/${g.id}`)">
          <div class="rp-item-img" :style="{ background: g.grad }">
            <span class="rp-item-cat">{{ g.category || '好礼' }}</span>
            <div class="rp-img-text">{{ g.name }}</div>
          </div>
          <div class="rp-item-info">
            <div class="rp-item-name">{{ g.name }}</div>
            <div class="rp-item-pts">{{ g.points }} 积分</div>
          </div>
          <button class="rp-item-btn">立即兑换</button>
        </div>
        <div v-if="!decorated.length" class="empty-state">暂无商品</div>
      </div>
    </template>

    <!-- 兑换记录 -->
    <div v-else class="rp-records">
      <div v-if="recordsLoading" class="loading-state">加载中...</div>
      <template v-else>
        <div v-for="(r, i) in records" :key="(r.code || 'r') + '-' + i" class="rp-rec-card" :style="{ '--ac-bg': PALETTE[i % PALETTE.length].bg, '--ac-bd': PALETTE[i % PALETTE.length].bd }">
          <div class="rp-rec-name">{{ r.item || '优惠券' }}</div>
          <div class="rp-rec-code">券码 {{ r.code || '—' }}</div>
          <div class="rp-rec-time" v-if="r.time">{{ r.time }}</div>
        </div>
        <div v-if="!records.length" class="empty-state">暂无兑换记录</div>
      </template>
    </div>
    <div class="spacer"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getRedeemCatalog, getMemberCoupons } from '@/api'
import { useMemberStore } from '@/stores/member'

const activeCat = ref('全部')
// 顶部切换：积分商城 / 兑换记录（“兑换记录”原是更多页坏链入口，现并入本页作为标签页）
const viewTab = ref('mall')
const records = ref([])
const recordsLoading = ref(false)
function loadRecords() {
  if (records.value.length || recordsLoading.value) return
  recordsLoading.value = true
  const phone = memberStore.member && memberStore.member.phone
  getMemberCoupons(phone)
    .then(res => { if (res && res.ok) records.value = res.coupons || [] })
    .catch(() => { records.value = [] })
    .finally(() => { recordsLoading.value = false })
}
function openRecords() {
  viewTab.value = 'records'
  loadRecords()
}
const cats = ['全部', '餐饮', '购物', '娱乐', '亲子', '生活服务', '停车']
const loading = ref(true)
const goods = ref([])

// 接入全局会员 store：积分/等级与首页、会员中心、我的页完全同步（不单独查 localStorage）
const memberStore = useMemberStore()
// 从 sessionStorage 恢复登录态，保证进入兑换页时与其它页一致
memberStore.restore()

// 积分卡主题色：按登录会员等级取统一主题色（各页共用 levelTheme）
const theme = computed(() => {
  const lv = memberStore.member && memberStore.member.membership_level
  return memberStore.levelTheme(lv || '普卡')
})

// 本地兜底（后台异常时也能展示）— 与 /api/redeem/catalog 同源的 9 项
const FALLBACK_GOODS = [
  { id: 1, name: '停车券', points: 500, category: '停车', gradient: 'linear-gradient(135deg, #6B6E64, #9AA39A)' },
  { id: 2, name: '海江食集满50减10券', points: 800, category: '餐饮', gradient: 'linear-gradient(135deg, #C4923A, #E0B288)' },
  { id: 3, name: '瑞幸咖啡饮品券', points: 1000, category: '餐饮', gradient: 'linear-gradient(135deg, #0051A8, #3E7FD0)' },
  { id: 4, name: 'SFC上影电影票', points: 2000, category: '娱乐', gradient: 'linear-gradient(135deg, #9B7BD4, #C9B6E8)' },
  { id: 5, name: '朱光玉火锅50元券', points: 3000, category: '餐饮', gradient: 'linear-gradient(135deg, #9B4A3E, #C97A6E)' },
  { id: 6, name: '泡泡米儿童体验课', points: 5000, category: '亲子', gradient: 'linear-gradient(135deg, #E8809E, #F0AAC0)' },
  { id: 7, name: '华为授权店30元券', points: 8000, category: '购物', gradient: 'linear-gradient(135deg, #4A90D9, #7DB8F0)' },
  { id: 8, name: '200元购物卡', points: 10000, category: '购物', gradient: 'linear-gradient(135deg, #8B8B90, #A9A9AE)' },
  { id: 9, name: '哇咔健身周卡', points: 15000, category: '娱乐', gradient: 'linear-gradient(135deg, #3E8E41, #6FBF73)' },
]

// 平台统一目录不含 category，按名称推导分类以保留前端分类筛选
function deriveCategory(name) {
  if (!name) return '好礼'
  if (name.includes('停车')) return '停车'
  if (name.includes('食集') || name.includes('朱光玉') || name.includes('瑞幸') || name.includes('火锅')) return '餐饮'
  if (name.includes('SFC') || name.includes('电影') || name.includes('健身')) return '娱乐'
  if (name.includes('泡泡米') || name.includes('儿童')) return '亲子'
  if (name.includes('华为') || name.includes('购物卡')) return '购物'
  return '生活服务'
}

onMounted(async () => {
  try {
    const resp = await getRedeemCatalog()
    if (resp.ok && resp.data && resp.data.length) {
      // 统一目录 {id,name,cost,desc} → 前端 {id,name,points,category}
      goods.value = resp.data.map(g => ({ ...g, points: g.cost, category: deriveCategory(g.name) }))
    } else {
      goods.value = FALLBACK_GOODS
    }
  } catch (e) {
    console.error('Failed to load redeem catalog:', e)
    goods.value = FALLBACK_GOODS
  } finally {
    loading.value = false
  }
})

// 多彩卡片调色板（与活动报名页同款：bg 实色底 + bd 深边框色；grad 同色系低饱和渐变图头）
const PALETTE = [
  { bg: '#C4923A', bd: '#9A7425', grad: 'linear-gradient(135deg, #DDB873, #9A7425)' },
  { bg: '#9B4A3E', bd: '#6E332A', grad: 'linear-gradient(135deg, #BE7468, #6E332A)' },
  { bg: '#8B8B90', bd: '#6A6A6E', grad: 'linear-gradient(135deg, #A9A9AE, #6A6A6E)' },
  { bg: '#C9956C', bd: '#A87C48', grad: 'linear-gradient(135deg, #E0B288, #A87C48)' },
  { bg: '#6B6E64', bd: '#4E5049', grad: 'linear-gradient(135deg, #8C8F82, #4E5049)' },
  { bg: '#D4A59A', bd: '#A67D72', grad: 'linear-gradient(135deg, #E5C2B9, #A67D72)' },
]

// 先按分类筛选，再为每条商品补齐同色系主题色（图头渐变不再用后台高饱和 gradient）
const filtered = computed(() => activeCat.value === '全部' ? goods.value : goods.value.filter(g => g.category === activeCat.value))

const decorated = computed(() => {
  return filtered.value.map((g, i) => {
    const p = PALETTE[i % PALETTE.length]
    return { ...g, grad: p.grad, bg: p.bg, bd: p.bd }
  })
})
</script>

<style scoped>
.rp-page { padding: 8px 12px; min-height: 100vh; background: #000000; }

.loading-state, .empty-state {
  text-align: center; padding: 40px 20px; color: #BBBBBB; font-size: 14px;
}

.rp-pts-card {
  background: linear-gradient(135deg, var(--ac-bg, #C4923A), var(--ac-bd, #9A7425));
  border: 3px solid var(--ac-bd, #4E5049); border-radius: 18px; padding: 24px; position: relative; overflow: hidden; margin-bottom: 16px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20);
  text-align: center;
}
.rp-pts-shine { position: absolute; top: -50px; right: -30px; width: 120px; height: 120px; background: radial-gradient(circle, var(--ac-accent, #C4923A) 0%, transparent 70%); border-radius: 50%; opacity: 0.35; }
.rp-pts-ring { position: absolute; right: -10px; bottom: -8px; width: 80px; height: 40px; border: 2px solid var(--ac-bd, rgba(255,255,255,0.1)); border-radius: 50%; transform: rotate(-10deg); }
.rp-pts-level { position: relative; z-index: 1; font-size: 14px; color: var(--ac-accent, rgba(255,255,255,0.7)); }
.rp-pts-num { position: relative; z-index: 1; font-size: 42px; font-weight: 800; color: #fff; margin-top: 6px; }
.rp-pts-label { position: relative; z-index: 1; font-size: 13px; color: rgba(255,255,255,0.65); margin-top: 4px; }

.rp-cats { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 8px; margin-bottom: 14px; -webkit-overflow-scrolling: touch; }
.rp-cats::-webkit-scrollbar { display: none; }
.rp-cat-btn {
  flex-shrink: 0; padding: 10px 16px; border: 3px solid #4E5049; border-radius: 12px;
  font-size: 14px; font-weight: 600; cursor: pointer; font-family: inherit;
  background: #6B6E64; color: #fff;
  transition: all 0.15s;
}
.rp-cat-btn.active { background: #8B8B90; border-color: #6A6A6E; box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20); }

/* 两列多彩卡片（视觉与活动报名页同款：实色底 + 深边框 + 同色系渐变图头 + 内凹按钮），排列保持原网格格式 */
.rp-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
.rp-item {
  background-color: var(--ac-bg, #C4923A);
  border: 3px solid var(--ac-bd, #9A7425);
  border-radius: 14px; overflow: hidden; box-sizing: border-box;
  box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20);
  cursor: pointer; transition: opacity 0.15s;
}
.rp-item:active { opacity: 0.85; }
.rp-item-img { height: 90px; display: flex; flex-direction: column; justify-content: flex-end; padding: 14px 12px; position: relative; }
.rp-item-cat {
  position: absolute; top: 10px; left: 10px;
  padding: 2px 8px; border-radius: 999px;
  font-size: 10px; font-weight: 700; color: #fff;
  background: var(--ac-bd, #9A7425);
  box-shadow: 0 2px 6px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.25);
}
.rp-img-text { font-size: 15px; font-weight: 700; color: #fff; text-shadow: 0 1px 4px rgba(0,0,0,0.4); }
.rp-item-info { padding: 10px 12px 8px; }
.rp-item-name { font-size: 14px; font-weight: 600; color: #fff; text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.25); }
.rp-item-pts { font-size: 12px; color: #fff; font-weight: 600; margin-top: 3px; text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.25); }
/* 立即兑换按钮：内凹（inset 阴影）风格，与活动页一致 */
.rp-item-btn {
  margin: 0 12px 12px; width: calc(100% - 24px); padding: 8px 0;
  border: 3px solid var(--ac-bd, #9A7425);
  border-radius: 14px;
  background-color: var(--ac-bd, #9A7425); color: #fff;
  font-size: 13px; font-weight: 600; cursor: pointer; font-family: inherit;
  box-shadow: inset 3px 3px 7px rgba(0, 0, 0, 0.45), inset -2px -2px 5px rgba(196, 146, 58, 0.45);
  transition: transform 0.15s;
}
.rp-item-btn:active { transform: scale(0.99); }
.spacer { height: 24px; }

/* 顶部主标签：积分商城 / 兑换记录 */
.rp-tabs { display: flex; gap: 8px; margin-bottom: 14px; }
.rp-tab-btn {
  flex: 1; padding: 11px 0; border: 3px solid #4E5049; border-radius: 12px;
  font-size: 14px; font-weight: 700; cursor: pointer; font-family: inherit;
  background: #6B6E64; color: #fff;
  transition: all 0.15s;
}
.rp-tab-btn.active {
  background: #8B8B90; border-color: #6A6A6E;
  box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20);
}

/* 兑换记录卡（复用五色板，实色底 + 深边框，与商城卡视觉统一） */
.rp-records { display: flex; flex-direction: column; gap: 10px; }
.rp-rec-card {
  background-color: var(--ac-bg, #8B8B90);
  border: 3px solid var(--ac-bd, #6A6A6E);
  border-radius: 14px; padding: 14px 16px; box-sizing: border-box;
  box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20);
}
.rp-rec-name { font-size: 15px; font-weight: 700; color: #fff; text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.25); }
.rp-rec-code { font-size: 12px; color: #fff; font-weight: 600; margin-top: 6px; opacity: 0.92; text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.25); }
.rp-rec-time { font-size: 12px; color: rgba(255,255,255,0.8); margin-top: 4px; }
</style>
