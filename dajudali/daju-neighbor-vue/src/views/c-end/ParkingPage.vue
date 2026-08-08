<template>
  <div class="parking-page">
    <div class="pp-back" @click="$router.back()">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#AAA" stroke-width="2" stroke-linecap="round"><polyline points="15 18 9 12 15 6"/></svg>
    </div>

    <div class="pp-hero">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#999999" stroke-width="1.5" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><path d="M14 7h-4v10h4a3 3 0 0 0 0-6h-3"/></svg>
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

    <button class="pp-query-btn" :disabled="!plate || querying" @click="doQuery">
      {{ querying ? '查询中...' : '查询停车费' }}
    </button>

    <!-- 错误提示 -->
    <div v-if="errorMsg" class="pp-error">{{ errorMsg }}</div>

    <!-- 停车状态卡片 -->
    <div class="pp-status-card" v-if="queried && parkingData">
      <div class="pps-row">
        <span class="pps-label">车牌号</span>
        <span class="pps-val">{{ parkingData.plate }}</span>
      </div>
      <div class="pps-row">
        <span class="pps-label">入场时间</span>
        <span class="pps-val">{{ parkingData.entry_time }}</span>
      </div>
      <div class="pps-row">
        <span class="pps-label">已停时长</span>
        <span class="pps-val">{{ parkingData.duration }}</span>
      </div>
      <div class="pps-divider"></div>
      <div class="pps-fee">
        <span class="pps-fee-label">应付金额</span>
        <span class="pps-fee-val">¥{{ parkingData.fee?.toFixed(2) }}</span>
      </div>
    </div>

    <button class="pp-pay-btn" v-if="queried && parkingData && !paid" :disabled="paying" @click="doPay">
      {{ paying ? '支付中...' : `立即支付 ¥${parkingData.fee?.toFixed(2)}` }}
    </button>

    <!-- 支付成功 -->
    <div v-if="paid" class="pp-paid-card">
      <div class="pp-paid-icon">✓</div>
      <div class="pp-paid-text">缴费成功</div>
      <div class="pp-paid-detail">{{ payResult?.message }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { queryParking, payParking } from '@/api'

const plate = ref('')
const presets = ref(['沪A·12345', '沪B·67890', '沪C·11111'])
const queried = ref(false)
const querying = ref(false)
const paying = ref(false)
const paid = ref(false)
const errorMsg = ref('')
const parkingData = ref(null)
const payResult = ref(null)

async function doQuery() {
  if (!plate.value.trim()) return
  querying.value = true
  errorMsg.value = ''
  paid.value = false
  try {
    const resp = await queryParking({ plate: plate.value.trim() })
    if (resp.ok && resp.data) {
      parkingData.value = resp.data
      queried.value = true
    } else {
      errorMsg.value = resp.error || '查询失败，请稍后重试'
      queried.value = false
      parkingData.value = null
    }
  } catch (e) {
    errorMsg.value = '网络错误，请稍后重试'
    queried.value = false
    parkingData.value = null
  } finally {
    querying.value = false
  }
}

async function doPay() {
  if (!plate.value.trim()) return
  paying.value = true
  try {
    const resp = await payParking({ plate: plate.value.trim() })
    if (resp.ok) {
      paid.value = true
      payResult.value = resp.data
    } else {
      errorMsg.value = resp.error || '支付失败，请稍后重试'
    }
  } catch (e) {
    errorMsg.value = '网络错误，请稍后重试'
  } finally {
    paying.value = false
  }
}
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
.pp-plate-input-wrap:focus-within { border-color: #999999; }
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
.pp-preset-btn.add { color: #999999; border-color: #999999; }

.pp-query-btn {
  width: 100%; padding: 14px; border: none; border-radius: 12px;
  background: #2A2A2A; color: #666; font-size: 16px; font-weight: 600;
  cursor: pointer; font-family: inherit; transition: all 0.15s; margin-bottom: 20px;
}
.pp-query-btn:not(:disabled) { background: #1A1A1A; color: #fff; }
.pp-query-btn:not(:disabled):active { opacity: 0.8; }
.pp-query-btn:disabled { opacity: 0.5; }

.pp-error {
  background: #1A1A1A; border: 1px solid #767676;
  color: #818181; font-size: 13px; padding: 10px 14px; border-radius: 10px;
  margin-bottom: 16px; text-align: center;
}

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
.pps-fee-val { font-size: 28px; font-weight: 800; color: #999999; }

.pp-pay-btn {
  width: 100%; padding: 16px; border: none; border-radius: 12px;
  background: #1A1A1A; color: #fff; font-size: 17px; font-weight: 700;
  cursor: pointer; font-family: inherit; transition: opacity 0.15s;
}
.pp-pay-btn:active { opacity: 0.8; }
.pp-pay-btn:disabled { opacity: 0.5; }

.pp-paid-card {
  background: #222222; border-radius: 12px; padding: 32px 20px;
  text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
.pp-paid-icon {
  width: 48px; height: 48px; border-radius: 50%; background: #1A1A1A;
  color: #fff; font-size: 24px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  margin: 0 auto 12px;
}
.pp-paid-text { font-size: 18px; font-weight: 700; color: #878787; margin-bottom: 8px; }
.pp-paid-detail { font-size: 13px; color: #999; }
</style>
