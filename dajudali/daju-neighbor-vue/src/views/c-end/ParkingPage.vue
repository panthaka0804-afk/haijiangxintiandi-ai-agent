<template>
  <div class="parking-page">
    <div class="pp-back" @click="$router.back()">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#AAA" stroke-width="2" stroke-linecap="round"><polyline points="15 18 9 12 15 6"/></svg>
    </div>

    <div class="pp-hero">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#FF7B2C" stroke-width="1.5" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><path d="M14 7h-4v10h4a3 3 0 0 0 0-6h-3"/></svg>
      <div class="pp-title">停车缴费</div>
    </div>

    <!-- 车牌输入 -->
    <div class="pp-plate-section">
      <div class="pp-plate-label">输入车牌号</div>
      <div class="pp-plate-input-wrap">
        <input v-model="plate" placeholder="沪A·12345" maxlength="10" class="pp-plate-input" />
      </div>
      <div class="pp-plate-presets">
        <button v-for="p in presets" :key="p" class="pp-preset-btn" @click="plate = p">{{ p }}</button>
        <button class="pp-preset-btn add" @click="$router.push('/parking/bind')">+ 管理</button>
      </div>
    </div>

    <button class="pp-query-btn" :disabled="!plate">查询停车费</button>

    <!-- 停车状态卡片 -->
    <div class="pp-status-card" v-if="queried">
      <div class="pps-row">
        <span class="pps-label">车牌号</span>
        <span class="pps-val">{{ plate }}</span>
      </div>
      <div class="pps-row">
        <span class="pps-label">入场时间</span>
        <span class="pps-val">2026-08-06 18:30</span>
      </div>
      <div class="pps-row">
        <span class="pps-label">已停时长</span>
        <span class="pps-val">3 小时 5 分钟</span>
      </div>
      <div class="pps-divider"></div>
      <div class="pps-fee">
        <span class="pps-fee-label">应付金额</span>
        <span class="pps-fee-val">¥15.00</span>
      </div>
    </div>

    <button class="pp-pay-btn" v-if="queried">立即支付 ¥15.00</button>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const plate = ref('沪A·12345')
const presets = ['沪A·12345', '沪B·67890', '沪C·11111']
const queried = ref(true)
</script>

<style scoped>
.parking-page { padding: 0 12px; min-height: 100vh; background: #1A1A1A; }
.pp-back { padding: 10px 0; cursor: pointer; display: inline-block; }

.pp-hero { display: flex; align-items: center; gap: 14px; margin-bottom: 24px; padding: 4px 0; }
.pp-title { font-size: 24px; font-weight: 700; color: #F0F0F0; }

.pp-plate-section { margin-bottom: 16px; }
.pp-plate-label { font-size: 13px; font-weight: 600; color: #999; margin-bottom: 8px; }
.pp-plate-input-wrap {
  background: #2A2A2A; border: 1px solid #444; border-radius: 12px;
  margin-bottom: 10px; transition: border-color 0.15s;
}
.pp-plate-input-wrap:focus-within { border-color: #FF7B2C; }
.pp-plate-input {
  width: 100%; padding: 16px; border: none; background: none; outline: none;
  font-size: 28px; font-weight: 700; color: #F0F0F0; text-align: center;
  letter-spacing: 2px; font-family: inherit;
}
.pp-plate-presets { display: flex; gap: 8px; flex-wrap: wrap; }
.pp-preset-btn {
  padding: 8px 16px; border: 1px solid #333; border-radius: 12px;
  background: #222222; color: #999; font-size: 13px; font-weight: 500;
  cursor: pointer; font-family: inherit; transition: all 0.15s;
}
.pp-preset-btn:active { background: #2A2A2A; }
.pp-preset-btn.add { color: #FF7B2C; border-color: #FF7B2C; }

.pp-query-btn {
  width: 100%; padding: 14px; border: none; border-radius: 12px;
  background: #2A2A2A; color: #666; font-size: 16px; font-weight: 600;
  cursor: pointer; font-family: inherit; transition: all 0.15s; margin-bottom: 20px;
}
.pp-query-btn:not(:disabled) { background: #FF7B2C; color: #fff; }
.pp-query-btn:not(:disabled):active { opacity: 0.8; }

.pp-status-card {
  background: #222222; border-radius: 12px; padding: 4px 0; margin-bottom: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
.pps-row { display: flex; justify-content: space-between; padding: 14px 16px; }
.pps-label { font-size: 14px; color: #999; }
.pps-val { font-size: 14px; color: #F0F0F0; font-weight: 500; }
.pps-divider { height: 1px; background: #2E2E2E; margin: 0 16px; }
.pps-fee { display: flex; justify-content: space-between; padding: 18px 16px; align-items: center; }
.pps-fee-label { font-size: 16px; font-weight: 600; color: #F0F0F0; }
.pps-fee-val { font-size: 28px; font-weight: 800; color: #FF7B2C; }

.pp-pay-btn {
  width: 100%; padding: 16px; border: none; border-radius: 12px;
  background: #FF7B2C; color: #fff; font-size: 17px; font-weight: 700;
  cursor: pointer; font-family: inherit; transition: opacity 0.15s;
}
.pp-pay-btn:active { opacity: 0.8; }
</style>
