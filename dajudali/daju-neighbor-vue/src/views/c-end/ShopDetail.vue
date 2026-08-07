<template>
  <div class="shop-detail">
    <div class="sd-header" :style="{background: shop.color + 'DD'}">
      <div class="sd-back" @click="$router.back()">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"><polyline points="15 18 9 12 15 6"/></svg>
      </div>
      <div class="sd-hero">
        <div class="sd-avatar">{{ shop.name[0] }}</div>
        <div class="sd-name">{{ shop.name }}</div>
        <div class="sd-tags">{{ shop.tags?.join(' · ') }} · {{ shop.floor }}F</div>
      </div>
      <div class="sd-shine"></div>
    </div>

    <div class="sd-body">
      <div class="sd-info-card">
        <div class="sd-row" v-if="shop.desc">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FF7B2C" stroke-width="1.5" stroke-linecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          <span class="sd-info-label">简介</span>
          <span class="sd-info-val">{{ shop.desc }}</span>
        </div>
        <div class="sd-row">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FF7B2C" stroke-width="1.5" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          <span class="sd-info-label">营业时间</span>
          <span class="sd-info-val">{{ shop.hours }}</span>
        </div>
        <div class="sd-row">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FF7B2C" stroke-width="1.5" stroke-linecap="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
          <span class="sd-info-label">楼层位置</span>
          <span class="sd-info-val">{{ shop.floor }}F {{ shop.zone }}</span>
        </div>
        <div class="sd-row">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FF7B2C" stroke-width="1.5" stroke-linecap="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.362 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.338 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
          <span class="sd-info-label">联系电话</span>
          <span class="sd-info-val">{{ shop.phone }}</span>
        </div>
      </div>

      <div class="sd-coupon-card" v-if="shop.has_coupon">
        <div class="sdc-left">
          <div class="sdc-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#FF7B2C" stroke-width="1.5" stroke-linecap="round"><path d="M20 12v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-8"/><path d="M22 7H2v5h20z"/></svg>
          </div>
          <div>
            <div class="sdc-title">满{{ shop.coupon_condition }}减{{ shop.coupon_amount }}</div>
            <div class="sdc-expire">有效期至 {{ shop.coupon_expire }}</div>
          </div>
        </div>
        <button class="sdc-btn">领取</button>
      </div>

      <div class="sd-features" v-if="shop.features && shop.features.length">
        <div class="sd-feature-title">特色服务</div>
        <div class="sd-feature-tags">
          <span v-for="f in shop.features" :key="f" class="sd-feature-tag">{{ f }}</span>
        </div>
      </div>

      <button class="sd-nav-btn" @click="goNav">导航到店</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import shops from '@/data/shops.js'

const router = useRouter()
const route = useRoute()

const shop = computed(() => {
  const s = shops.find(s => s.id === route.params.id)
  return s || { id: route.params.id, name: '商铺', floor: 1, color: '#999', tags: [], hours: '--', zone: '--', phone: '--', desc: '', features: [], has_coupon: false }
})

function goNav() {
  router.push(`/nav?shop=${shop.value.id}`)
}
</script>

<style scoped>
.shop-detail { min-height: 100vh; background: #1A1A1A; }

.sd-header {
  height: 180px; position: relative; overflow: hidden;
  display: flex; flex-direction: column; justify-content: flex-end;
}
.sd-shine {
  position: absolute; top: -60px; right: -30px;
  width: 140px; height: 140px;
  background: radial-gradient(circle, rgba(255,255,255,0.12) 0%, transparent 70%);
  border-radius: 50%;
}
.sd-back { position: absolute; top: 16px; left: 12px; padding: 6px; cursor: pointer; z-index: 2; }
.sd-hero { position: relative; z-index: 1; padding: 0 20px 24px; display: flex; flex-direction: column; gap: 8px; align-items: flex-start; }
.sd-avatar { width: 56px; height: 56px; border-radius: 12px; background: rgba(255,255,255,0.2); display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: 700; color: #fff; }
.sd-name { font-size: 22px; font-weight: 700; color: #fff; }
.sd-tags { font-size: 13px; color: rgba(255,255,255,0.7); }

.sd-body { padding: 16px 12px; display: flex; flex-direction: column; gap: 12px; }

.sd-info-card {
  background: #222222; border-radius: 12px; padding: 4px 0;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
.sd-row { display: flex; align-items: center; gap: 12px; padding: 14px 16px; }
.sd-row:not(:last-child) { border-bottom: 0.5px solid #2E2E2E; }
.sd-info-label { font-size: 14px; color: #999; width: 64px; flex-shrink: 0; }
.sd-info-val { font-size: 14px; color: #F0F0F0; font-weight: 500; }

.sd-coupon-card {
  background: #222222; border-radius: 12px; padding: 16px;
  display: flex; align-items: center; justify-content: space-between;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
.sdc-left { display: flex; align-items: center; gap: 12px; }
.sdc-icon { width: 44px; height: 44px; border-radius: 12px; background: rgba(255,123,44,0.12); display: flex; align-items: center; justify-content: center; }
.sdc-title { font-size: 15px; font-weight: 600; color: #F0F0F0; }
.sdc-expire { font-size: 12px; color: #999; margin-top: 2px; }
.sdc-btn {
  padding: 8px 18px; border: none; border-radius: 12px;
  background: #FF7B2C; color: #fff; font-size: 13px; font-weight: 600;
  cursor: pointer; font-family: inherit; transition: opacity 0.15s;
}
.sdc-btn:active { opacity: 0.8; }

.sd-nav-btn {
  padding: 14px; border: none; border-radius: 12px;
  background: #222222; color: #FF7B2C; font-size: 16px; font-weight: 700;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  cursor: pointer; font-family: inherit; transition: opacity 0.15s;
}
.sd-nav-btn:active { opacity: 0.8; }

.sd-features {
  background: #222222; border-radius: 12px; padding: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
.sd-feature-title { font-size: 14px; color: #999; margin-bottom: 10px; }
.sd-feature-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.sd-feature-tag {
  padding: 5px 12px; border-radius: 8px;
  background: rgba(255,123,44,0.1); border: 1px solid rgba(255,123,44,0.2);
  font-size: 13px; color: #FF8C00;
}
</style>
