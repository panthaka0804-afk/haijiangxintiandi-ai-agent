<template>
  <div class="offers-tab">
    <!-- 分类标签 -->
    <div class="cat-scroll">
      <button v-for="c in cats" :key="c.key" class="cat-btn"
        :class="{ active: activeCat === c.key }" @click="activeCat = c.key">
        {{ c.label }}
      </button>
    </div>

    <!-- 优惠券列表 -->
    <div class="coupon-list">
      <div v-for="c in filteredCoupons" :key="c.id" class="coupon-card"
        :class="{ claimed: c.claimed }">
        <div class="c-left">
          <div class="c-icon" :style="{background: c.color}">{{ c.name[0] }}</div>
          <div class="c-info">
            <div class="c-name">{{ c.name }}</div>
            <div class="c-desc">{{ c.label }}</div>
            <div class="c-expire">有效期至 {{ c.expire }}</div>
          </div>
        </div>
        <div class="c-right">
          <div class="c-amount"><span class="c-sign">¥</span>{{ c.amount }}</div>
          <button class="c-btn" :class="{ claimed: c.claimed }"
            @click="claim(c.id)">{{ c.claimed ? '已领取' : '立即领取' }}</button>
        </div>
      </div>
    </div>

    <div class="spacer"></div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const activeCat = ref('all')
const cats = [
  { key: 'all', label: '全部' },
  { key: 'food', label: '餐饮券' },
  { key: 'retail', label: '零售券' },
  { key: 'parking', label: '停车券' },
  { key: 'fun', label: '娱乐券' },
]

const coupons = ref([
  { id: 1, name: '蜀大侠', label: '满200减50', expire: '2026-12-31', amount: 50, cat: 'food', color: '#C41E3A', claimed: false },
  { id: 2, name: '星巴克', label: '买一赠一券', expire: '2026-10-31', amount: 35, cat: 'food', color: '#00704A', claimed: false },
  { id: 3, name: '海底捞', label: '满300减80', expire: '2026-09-30', amount: 80, cat: 'food', color: '#D32F2F', claimed: false },
  { id: 4, name: 'UNIQLO', label: '满299减30', expire: '2026-11-30', amount: 30, cat: 'retail', color: '#E60012', claimed: false },
  { id: 5, name: '万达影城', label: '双人票立减20', expire: '2026-10-15', amount: 20, cat: 'fun', color: '#E85D04', claimed: false },
  { id: 6, name: '棒约翰', label: '亲子套餐88折', expire: '2026-12-01', amount: 25, cat: 'food', color: '#FFB347', claimed: false },
  { id: 7, name: '停车场', label: '免费停车2小时', expire: '2026-09-15', amount: 10, cat: 'parking', color: '#4A90D9', claimed: true },
  { id: 8, name: '名创优品', label: '全场9折', expire: '2026-11-20', amount: 15, cat: 'retail', color: '#E8809E', claimed: false },
])

const filteredCoupons = computed(() =>
  activeCat.value === 'all' ? coupons.value : coupons.value.filter(c => c.cat === activeCat.value)
)

function claim(id) {
  const c = coupons.value.find(x => x.id === id)
  if (c && !c.claimed) c.claimed = true
}
</script>

<style scoped>
.offers-tab { padding: 8px 12px; }

/* 分类标签 */
.cat-scroll { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 8px; margin-bottom: 12px; -webkit-overflow-scrolling: touch; }
.cat-scroll::-webkit-scrollbar { display: none; }
.cat-btn {
  flex-shrink: 0; padding: 8px 20px; border: 1px solid #333; border-radius: 12px;
  font-size: 14px; font-weight: 600; font-family: inherit; cursor: pointer;
  background: #222222; color: #999;
  transition: all 0.15s;
}
.cat-btn.active {
  background: #FF7B2C; color: #fff; border-color: #FF7B2C;
}
.cat-btn:not(.active):active { background: #2A2A2A; }

/* 优惠券卡片 */
.coupon-list { display: flex; flex-direction: column; gap: 10px; }
.coupon-card {
  background: #222222; border-radius: 12px; padding: 16px;
  display: flex; justify-content: space-between; align-items: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  transition: all 0.2s;
}
.coupon-card.claimed { opacity: 0.55; }
.c-left { display: flex; align-items: center; gap: 14px; flex: 1; }
.c-icon {
  width: 48px; height: 48px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; font-weight: 700; color: #fff; flex-shrink: 0;
}
.c-info { flex: 1; }
.c-name { font-size: 16px; font-weight: 600; color: #F0F0F0; }
.c-desc { font-size: 13px; color: #999; margin-top: 3px; }
.c-expire { font-size: 11px; color: #666; margin-top: 4px; }
.c-right { text-align: center; display: flex; flex-direction: column; gap: 8px; align-items: center; }
.c-amount { font-size: 28px; font-weight: 700; color: #FF7B2C; }
.c-sign { font-size: 16px; }
.c-btn {
  padding: 7px 18px; border: none; border-radius: 12px;
  font-size: 13px; font-weight: 600; cursor: pointer; font-family: inherit;
  background: #FF7B2C; color: #fff;
  transition: opacity 0.15s;
}
.c-btn:active:not(.claimed) { opacity: 0.8; }
.c-btn.claimed { background: #444; color: #777; }
.spacer { height: 24px; }
</style>
