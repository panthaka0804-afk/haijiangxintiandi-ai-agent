<template>
  <div class="tb-row">
    <button
      v-for="btn in toolbarButtons"
      :key="btn.label"
      class="tb-btn"
      @click="handleClick(btn)"
    >
      <SvgIcon :name="btn.icon" :size="18" color="#999999" />
      <span>{{ btn.label }}</span>
    </button>
  </div>
</template>

<script setup>
import SvgIcon from './SvgIcon.vue'

const emit = defineEmits(['quickSend', 'openForm'])

const toolbarButtons = [
  { icon: 'clock',   label: '营业时间', action: '营业时间', form: null },
  { icon: 'parking', label: '停车缴费', action: null, form: 'parking' },
  { icon: 'car',     label: '反向寻车', action: '反向寻车', form: null },
  { icon: 'calendar', label: '在线预约', action: null, form: 'booking' },
  { icon: 'edit',    label: '活动报名', action: null, form: 'register' },
  { icon: 'tool',    label: '报修',     action: null, form: 'repair' },
  { icon: 'shop',    label: '招商合作', action: null, form: 'biz_guide' },
]

function handleClick(btn) {
  if (btn.form) {
    emit('openForm', btn.form)
  } else if (btn.action) {
    emit('quickSend', btn.action)
  }
}
</script>

<style scoped>
.tb-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 16px;
  background: #1A1A1A;
  flex-shrink: 0;
}

.tb-btn {
  flex: 0 0 calc((100% - 16px) / 3);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 10px 4px;
  border: none;
  border-radius: 16px;
  background: #1A1A1A;
  box-shadow: 3px 3px 6px #d1d6dd, -3px -3px 6px #ffffff;
  color: #F0F0F0;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: box-shadow 0.15s;
  font-family: -apple-system, 'PingFang SC', sans-serif;
}

.tb-btn:active {
  box-shadow: inset 3px 3px 6px #d1d6dd, inset -3px -3px 6px #ffffff;
}
</style>
