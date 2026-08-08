<template>
  <div class="welcome-cards">
    <div class="wc-row">
      <div v-for="card in topRow" :key="card.label" class="wc-card" @click="$emit('quickSend', card.action)">
        <div class="wc-icon"><SvgIcon :name="card.icon" :size="28" :color="card.color" /></div>
        <div class="wc-text">{{ card.label }}</div>
        <div class="wc-sub">{{ card.sub }}</div>
      </div>
    </div>
    <div class="wc-row">
      <div v-for="card in bottomRow" :key="card.label" class="wc-card" @click="$emit('quickSend', card.action)">
        <div class="wc-icon"><SvgIcon :name="card.icon" :size="28" :color="card.color" /></div>
        <div class="wc-text">{{ card.label }}</div>
        <div class="wc-sub">{{ card.sub }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import SvgIcon from './SvgIcon.vue'

defineEmits(['quickSend'])

const topRow = [
  { icon: 'calendar', label: '找活动', sub: '亲子/夜市/夜校', action: '最近有什么活动', color: '#979797' },
  { icon: 'tag', label: '找优惠', sub: '折扣/满减/积分', action: '有什么优惠', color: '#9E9E9E' },
]

const bottomRow = [
  { icon: 'shop', label: '找店铺', sub: '餐厅/商店/品牌', action: '附近有什么好吃的', color: '#A6A6A6' },
  { icon: 'parking', label: '停车缴费', sub: '收费/优惠/位置', action: '停车场怎么收费', color: '#989898' },
]
</script>

<style scoped>
.welcome-cards {
  padding: 4px 0 12px;
}

.wc-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.wc-card {
  flex: 1;
  background: #1A1A1A;
  border-radius: 14px;
  padding: 14px 10px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  cursor: pointer;
  text-align: center;
  transition: transform 0.15s;
  user-select: none;
}

.wc-card:active {
  transform: scale(0.96);
  background: #1A1A1A;
}

.wc-icon {
  margin-bottom: 4px;
  display: flex;
  justify-content: center;
}

.wc-text {
  font-size: 14px;
  font-weight: 700;
  color: #F0F0F0;
}

.wc-sub {
  font-size: 11px;
  color: #999;
  margin-top: 2px;
}
</style>
