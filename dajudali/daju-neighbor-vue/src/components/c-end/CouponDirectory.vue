<template>
  <div class="coupon-dir">
    <div class="cd-card" :class="{ expanded }" @click="expanded = !expanded">
      <div class="card-grad">
        <div class="card-grad-left">
          <span class="card-grad-title">优惠套餐目录</span>
          <span class="card-grad-sub">火锅 · 亲子 · 夜生活 · 会员价</span>
        </div>
        <div class="card-grad-right">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20 12v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-8"/><path d="M22 7H2v5h20z"/><path d="M12 22V7"/><path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z"/><path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z"/>
          </svg>
        </div>
        <div class="card-dots"></div>
        <div class="card-ring"></div>
      </div>
      <div class="card-white">
        <div class="card-tags">
          <span class="tag">美食优惠</span>
          <span class="tag">亲子套餐</span>
          <span class="tag">银行叠加</span>
        </div>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ccc" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" :style="{ transform: expanded ? 'rotate(180deg)' : '', transition: 'transform 0.25s' }"><polyline points="6 9 12 15 18 9"/></svg>
      </div>
    </div>

    <div v-show="expanded" class="cd-menu">
      <div class="cd-section-title">美食优惠</div>
      <div class="cd-grid">
        <button v-for="b in food" :key="b.label" class="cd-btn" @click.stop="$emit('quickSend', b.action)">{{ b.label }}</button>
      </div>
      <div class="cd-section-title">场景化套餐</div>
      <div class="cd-grid">
        <button v-for="b in scene" :key="b.label" class="cd-btn" @click.stop="$emit('quickSend', b.action)">{{ b.label }}</button>
      </div>
      <div class="cd-section-title">银行叠加</div>
      <div class="cd-grid">
        <button v-for="b in bank" :key="b.label" class="cd-btn" @click.stop="$emit('quickSend', b.action)">{{ b.label }}</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
defineEmits(['quickSend'])
const expanded = ref(false)

const food = [
  { label: '火锅套餐', action: '美食优惠有哪些' },
  { label: '披萨亲子', action: '棒约翰披萨优惠' },
  { label: '美食广场', action: 'B1美食广场优惠' },
  { label: '星巴克', action: '星巴克会员优惠' },
]
const scene = [
  { label: '亲子欢聚', action: '亲子欢聚套餐怎么算' },
  { label: '夜生活', action: '夜生活套餐怎么算' },
  { label: '祖孙同行', action: '祖孙同行套餐怎么算' },
  { label: '会员专属价', action: '会员等级和折扣' },
]
const bank = [
  { label: '招行满减', action: '招商银行信用卡优惠' },
  { label: '浦发刷卡', action: '浦发银行信用卡优惠' },
  { label: '团购券', action: '抖音美团团购券怎么用' },
  { label: '积分兑换', action: '积分怎么兑换' },
]
</script>

<style scoped>
.coupon-dir { padding: 0 12px 6px; }

.cd-card {
  margin: 6px 0; border-radius: 20px; overflow: hidden;
  box-shadow: 6px 6px 12px #d1d6dd, -6px -6px 12px #ffffff;
  cursor: pointer; transition: transform 0.15s, box-shadow 0.15s;
}
.cd-card:active { transform: scale(0.98); box-shadow: inset 3px 3px 6px #d1d6dd, inset -3px -3px 6px #ffffff; }

/* 渐变顶 */
.card-grad {
  background: linear-gradient(135deg, #FF7B2C 0%, #E85D04 100%);
  padding: 22px 18px 18px; position: relative; overflow: hidden;
  display: flex; justify-content: space-between; align-items: flex-start;
}
.card-grad-left { display: flex; flex-direction: column; gap: 6px; z-index: 1; }
.card-grad-title { font-size: 20px; font-weight: 700; color: #fff; }
.card-grad-sub { font-size: 12px; color: rgba(255,255,255,0.7); }
.card-grad-right { z-index: 1; }
.card-dots {
  position: absolute; top: 12px; right: 60px;
  width: 28px; height: 28px;
  background: radial-gradient(circle, rgba(255,255,255,0.2) 1px, transparent 1px);
  background-size: 7px 7px;
}
.card-ring {
  position: absolute; right: -12px; bottom: -8px;
  width: 60px; height: 30px;
  border: 1.5px solid rgba(255,255,255,0.1);
  border-radius: 50%; transform: rotate(-8deg);
}

/* 白底 */
.card-white {
  background: #F0F2F5; padding: 10px 18px 12px;
  display: flex; align-items: center; justify-content: space-between;
}
.card-tags { display: flex; gap: 6px; }
.tag { background: #FFF3E0; color: #FF7B2C; font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 6px; }

/* 展开菜单 — 凸起新拟态 */
.cd-menu { background: #F0F2F5; border-radius: 16px; padding: 12px 12px 6px; margin-bottom: 2px; margin-top: 4px; box-shadow: 3px 3px 6px #d1d6dd, -3px -3px 6px #ffffff; }
.cd-section-title { font-size: 12px; font-weight: 600; color: #888; letter-spacing: 0.4px; padding: 6px 4px 8px; }
.cd-section-title:first-child { padding-top: 0; }
.cd-grid { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 4px; }
.cd-btn {
  padding: 8px 16px; border: none; border-radius: 8px;
  background: #E8ECF1; color: #FF7B2C;
  box-shadow: 2px 2px 4px #d1d6dd, -2px -2px 4px #ffffff;
  font-size: 13px; font-weight: 500; cursor: pointer;
  white-space: nowrap; transition: box-shadow 0.15s; font-family: inherit;
}
.cd-btn:active { box-shadow: inset 2px 2px 4px #d1d6dd, inset -2px -2px 4px #ffffff; }
</style>
