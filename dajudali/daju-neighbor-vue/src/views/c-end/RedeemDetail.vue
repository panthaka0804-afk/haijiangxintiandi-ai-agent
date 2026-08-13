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

.rd-desc-card { margin-top: 12px; background-color: #8B8B90; border: 3px solid #6A6A6E; border-radius: 14px; padding: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20); }
.rd-desc-title { font-size: 14px; font-weight: 600; color: rgba(255,255,255,0.9); margin-bottom: 8px; text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.25); }
.rd-desc-card p { margin: 0; font-size: 14px; color: #FFFFFF; line-height: 1.7; text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.25); }

.rd-actions { position: fixed; bottom: 0; left: 0; right: 0; padding: 12px 16px calc(20px + env(safe-area-inset-bottom, 0px)); display: flex; gap: 12px; background: linear-gradient(transparent, #000000 40%); }
.rd-cancel, .rd-confirm { flex: 1; padding: 14px; border: 3px solid #4E5049; border-radius: 20px; font-size: 15px; font-weight: 600; cursor: pointer; font-family: inherit; color: #fff; }
.rd-cancel { background-color: #4E5049; box-shadow: inset 3px 3px 7px rgba(0,0,0,0.45), inset -2px -2px 5px rgba(107,110,100,0.45); filter: drop-shadow(0 0.6px 1px rgba(0,0,0,0.4)); }
.rd-confirm { background-color: #9A7425; border-color: #9A7425; box-shadow: inset 3px 3px 7px rgba(0,0,0,0.45), inset -2px -2px 5px rgba(196,146,58,0.45); filter: drop-shadow(0 0.6px 1px rgba(0,0,0,0.4)); }
.rd-cancel:active, .rd-confirm:active { opacity: 0.82; }
</style>
