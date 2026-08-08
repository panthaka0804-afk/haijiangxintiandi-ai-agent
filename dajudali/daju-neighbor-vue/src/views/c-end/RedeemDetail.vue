<template>
  <div class="rd-page">
    <div class="rd-back" @click="$router.back()">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#AAA" stroke-width="2" stroke-linecap="round"><polyline points="15 18 9 12 15 6"/></svg>
    </div>

    <div class="rd-hero" :style="{background: goods.gradient}">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 12v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-8"/><path d="M22 7H2v5h20z"/></svg>
    </div>

    <div class="rd-body">
      <div class="rd-name">{{ goods.name }}</div>
      <div class="rd-pts">{{ goods.points }} 积分</div>
      <div class="rd-card">
        <div class="rd-row">
          <span>当前积分</span>
          <span class="rd-row-val">22,000</span>
        </div>
        <div class="rd-row">
          <span>兑换消耗</span>
          <span class="rd-row-val rd-cost">{{ goods.points }}</span>
        </div>
        <div class="rd-row">
          <span>兑换后剩余</span>
          <span class="rd-row-val">17,000</span>
        </div>
      </div>
      <div class="rd-desc-card">
        <div class="rd-desc-title">使用说明</div>
        <p>兑换后自动发放至"我的优惠券"，到店出示即可使用。有效期30天，过期不可退。如有疑问请联系客服。</p>
      </div>
    </div>

    <div class="rd-actions">
      <button class="rd-cancel" @click="$router.back()">取消</button>
      <button class="rd-confirm">确认兑换</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const goodsMap = {
  'g1': { name: 'SFC上影影城 电影票', points: 2000, gradient: 'linear-gradient(135deg, #9B7BD4, #C9B6E8)' },
  'g2': { name: '朱光玉火锅 50元代金券', points: 3000, gradient: 'linear-gradient(135deg, #9B4A3E, #C97A6E)' },
  'g3': { name: '华为授权店 30元券', points: 2500, gradient: 'linear-gradient(135deg, #4A90D9, #7DB8F0)' },
  'g4': { name: '海江新天地 停车券10元', points: 500, gradient: 'linear-gradient(135deg, #6B6E64, #9AA39A)' },
  'g5': { name: '康友四季 足浴券', points: 2500, gradient: 'linear-gradient(135deg, #3E8E41, #6FBF73)' },
  'g6': { name: '泡泡米儿童 体验课', points: 2000, gradient: 'linear-gradient(135deg, #E8809E, #F0AAC0)' },
  'g7': { name: '瑞幸咖啡 中杯券', points: 1000, gradient: 'linear-gradient(135deg, #0051A8, #3E7FD0)' },
  'g8': { name: '哇咔健身 体验周卡', points: 4000, gradient: 'linear-gradient(135deg, #3E8E41, #6FBF73)' },
}
const goods = ref(goodsMap[route.params.id] || { name: '兑换商品', points: 0, gradient: '#999' })
</script>

<style scoped>
.rd-page { min-height: 100vh; background: #1A1A1A; }
.rd-back { padding: 12px; cursor: pointer; }

.rd-hero { height: 180px; display: flex; align-items: center; justify-content: center; }

.rd-body { padding: 20px 12px 0; }
.rd-name { font-size: 22px; font-weight: 700; color: #F0F0F0; text-align: center; }
.rd-pts { font-size: 28px; font-weight: 800; color: #999999; text-align: center; margin-top: 6px; }

.rd-card {
  margin-top: 16px; background: #222222; border-radius: 12px; padding: 4px 0;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
.rd-row { display: flex; justify-content: space-between; padding: 14px 16px; font-size: 14px; color: #999; }
.rd-row:not(:last-child) { border-bottom: 0.5px solid #2E2E2E; }
.rd-row-val { color: #F0F0F0; font-weight: 500; }
.rd-cost { color: #999999; font-weight: 700; }

.rd-desc-card { margin-top: 12px; background: #222222; border-radius: 12px; padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }
.rd-desc-title { font-size: 14px; font-weight: 600; color: #999; margin-bottom: 8px; }
.rd-desc-card p { margin: 0; font-size: 14px; color: #AAA; line-height: 1.7; }

.rd-actions { position: fixed; bottom: 0; left: 0; right: 0; padding: 12px 16px 20px; display: flex; gap: 12px; background: linear-gradient(transparent, #1A1A1A 40%); }
.rd-cancel, .rd-confirm { flex: 1; padding: 14px; border: none; border-radius: 12px; font-size: 15px; font-weight: 600; cursor: pointer; font-family: inherit; }
.rd-cancel { background: #2A2A2A; color: #999; }
.rd-confirm { background: #1A1A1A; color: #fff; }
.rd-cancel:active, .rd-confirm:active { opacity: 0.8; }
</style>
