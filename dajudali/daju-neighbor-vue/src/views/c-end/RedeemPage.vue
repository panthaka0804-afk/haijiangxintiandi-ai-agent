<template>
  <div class="rp-page">
    <div class="rp-pts-card">
      <div class="rp-pts-shine"></div>
      <div class="rp-pts-ring"></div>
      <div class="rp-pts-level">{{ memberInfo.level || '会员' }} · {{ memberInfo.discount || '' }}</div>
      <div class="rp-pts-num">{{ memberInfo.points || '--' }}</div>
      <div class="rp-pts-label">可用积分</div>
    </div>

    <div class="rp-cats">
      <button v-for="c in cats" :key="c" class="rp-cat-btn" :class="{ active: activeCat === c }" @click="activeCat = c">{{ c }}</button>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">加载中...</div>

    <div class="rp-grid" v-else>
      <div v-for="g in filtered" :key="g.id" class="rp-item" @click="$router.push(`/redeem/${g.id}`)">
        <div class="rp-item-img" :style="{background: g.gradient}">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 12v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-8"/><path d="M22 7H2v5h20z"/></svg>
        </div>
        <div class="rp-item-info">
          <div class="rp-item-name">{{ g.name }}</div>
          <div class="rp-item-pts">{{ g.points }} 积分</div>
        </div>
        <button class="rp-item-btn">兑换</button>
      </div>
      <div v-if="!filtered.length" class="empty-state">暂无商品</div>
    </div>
    <div class="spacer"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getRedeemGoods, lookupMember } from '@/api'

const activeCat = ref('全部')
const cats = ['全部', '餐饮', '购物', '娱乐', '停车']
const loading = ref(true)
const goods = ref([])
const memberInfo = ref({ points: null, level: '', discount: '' })

onMounted(async () => {
  try {
    const resp = await getRedeemGoods()
    if (resp.ok && resp.data) {
      goods.value = resp.data
    }
  } catch (e) {
    console.error('Failed to load redeem goods:', e)
  } finally {
    loading.value = false
  }
  // 尝试获取会员积分（如果 localStorage 有手机号）
  const phone = localStorage.getItem('member_phone')
  if (phone) {
    try {
      const mResp = await lookupMember(phone)
      if (mResp.ok && mResp.member) {
        memberInfo.value = {
          points: mResp.member.points?.toLocaleString(),
          level: mResp.member.membership_level,
          discount: mResp.member.discount,
        }
      }
    } catch {}
  }
})

const filtered = computed(() => activeCat.value === '全部' ? goods.value : goods.value.filter(g => g.category === activeCat.value))
</script>

<style scoped>
.rp-page { padding: 8px 12px; min-height: 100vh; background: #1A1A1A; }

.loading-state, .empty-state {
  text-align: center; padding: 40px 20px; color: #666; font-size: 14px;
}

.rp-pts-card {
  background: linear-gradient(135deg, #FF7B2C, #E85D04);
  border-radius: 16px; padding: 24px; position: relative; overflow: hidden; margin-bottom: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  text-align: center;
}
.rp-pts-shine { position: absolute; top: -50px; right: -30px; width: 120px; height: 120px; background: radial-gradient(circle, rgba(255,255,255,0.12) 0%, transparent 70%); border-radius: 50%; }
.rp-pts-ring { position: absolute; right: -10px; bottom: -8px; width: 80px; height: 40px; border: 2px solid rgba(255,255,255,0.1); border-radius: 50%; transform: rotate(-10deg); }
.rp-pts-level { position: relative; z-index: 1; font-size: 14px; color: rgba(255,255,255,0.7); }
.rp-pts-num { position: relative; z-index: 1; font-size: 42px; font-weight: 800; color: #fff; margin-top: 6px; }
.rp-pts-label { position: relative; z-index: 1; font-size: 13px; color: rgba(255,255,255,0.65); margin-top: 4px; }

.rp-cats { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 8px; margin-bottom: 12px; -webkit-overflow-scrolling: touch; }
.rp-cats::-webkit-scrollbar { display: none; }
.rp-cat-btn {
  flex-shrink: 0; padding: 7px 18px; border: 1px solid #333; border-radius: 12px;
  font-size: 13px; font-weight: 600; cursor: pointer; font-family: inherit;
  background: #222222; color: #999;
  transition: all 0.15s;
}
.rp-cat-btn.active { background: #FF7B2C; color: #fff; border-color: #FF7B2C; }

.rp-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
.rp-item {
  background: #222222; border-radius: 12px; overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  cursor: pointer; transition: opacity 0.15s;
}
.rp-item:active { opacity: 0.8; }
.rp-item-img { height: 90px; display: flex; align-items: center; justify-content: center; }
.rp-item-info { padding: 10px 12px 8px; }
.rp-item-name { font-size: 14px; font-weight: 600; color: #F0F0F0; }
.rp-item-pts { font-size: 12px; color: #FF7B2C; font-weight: 600; margin-top: 3px; }
.rp-item-btn {
  margin: 0 12px 12px; width: calc(100% - 24px); padding: 8px 0;
  border: none; border-radius: 12px; background: #FF7B2C; color: #fff;
  font-size: 13px; font-weight: 600; cursor: pointer; font-family: inherit;
  transition: opacity 0.15s;
}
.rp-item-btn:active { opacity: 0.8; }
.spacer { height: 24px; }
</style>
