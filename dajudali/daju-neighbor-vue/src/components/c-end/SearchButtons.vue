<template>
  <div class="sb-row">
    <button
      v-for="btn in buttons"
      :key="btn.label"
      class="sb-btn"
      @click="$emit('quickSend', btn.action)"
    >
      <SvgIcon :name="btn.icon" :size="16" color="#fff" />
      <span>{{ btn.label }}</span>
    </button>
  </div>
</template>

<script setup>
import SvgIcon from './SvgIcon.vue'

defineEmits(['quickSend'])

const buttons = [
  { icon: 'tag',     label: '找优惠', action: '找优惠' },
  { icon: 'shop',    label: '找店铺', action: '找店铺' },
  { icon: 'gift',    label: '找商品', action: '找商品' },
]
</script>

<style scoped>
.sb-row {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  padding: 4px 12px;
  flex-shrink: 0;
}

.sb-btn {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 10px 18px;
  border: none;
  border-radius: 22px;
  background: linear-gradient(135deg, #1A1A1A, #1A1A1A);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  box-shadow: 0 2px 8px #747474;
  transition: transform 0.1s;
  font-family: inherit;
}

.sb-btn:active {
  transform: scale(0.96);
}
</style>
