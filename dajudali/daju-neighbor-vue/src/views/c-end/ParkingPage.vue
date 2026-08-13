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
      <div class="pp-paid-icon">已</div>
      <div class="pp-paid-text">缴费成功</div>
      <div class="pp-paid-detail">{{ payResult?.message }}</div>
    </div>

    <!-- 无感积分停车演示 -->
    <div class="pp-seamless">
      <div class="pps-title">无感积分停车（会员自动抵扣）</div>
      <div class="pps-sub">绑定车牌后，车辆进出自动识别；出场自动用会员权益 / 停车券 / 积分抵扣，无需当场缴费</div>
      <div class="pps-plates" v-if="myPlateList.length">
        <span>我的车辆：</span><b>{{ myPlateList.join('、') }}</b>
        <span class="pps-link" @click="$router.push('/parking/bind')">管理</span>
      </div>
      <div class="pps-actions">
        <button class="pps-btn entry" :disabled="!plate || entrying" @click="doEntry">{{ entrying ? '入场中...' : '模拟入场' }}</button>
        <button class="pps-btn exit" :disabled="!plate || exiting" @click="doExit">{{ exiting ? '结算中...' : '模拟出场结算' }}</button>
      </div>
      <div class="pps-msg" v-if="entryMsg">{{ entryMsg }}</div>
      <div class="pps-result" v-if="settleResult">
        <div class="pps-r-row"><span>车牌</span><b>{{ settleResult.plate }}</b></div>
        <div class="pps-r-row"><span>会员等级</span><b>{{ settleResult.member_level }}</b></div>
        <div class="pps-r-row"><span>停车时长</span><b>{{ settleResult.duration }}</b></div>
        <div class="pps-r-row"><span>原始费用</span><b>¥{{ settleResult.original_fee?.toFixed(2) }}</b></div>
        <div class="pps-r-row"><span>会员免费时长</span><b>{{ settleResult.member_benefit_min }} 分钟</b></div>
        <div class="pps-r-row"><span>停车券抵扣</span><b>{{ settleResult.coupon_hours_used }} 小时</b></div>
        <div class="pps-r-row"><span>积分抵扣</span><b>{{ settleResult.points_used }} 分</b></div>
        <div class="pps-r-row total"><span>已自动抵扣</span><b>-¥{{ settleResult.discount_total?.toFixed(2) }}</b></div>
        <div class="pps-r-row total"><span>实付</span><b>¥{{ settleResult.payable?.toFixed(2) }}</b></div>
        <div class="pps-barrier" :class="settleResult.barrier === 'OPEN' ? 'open' : 'pay'">
          道闸：{{ settleResult.barrier === 'OPEN' ? '已自动放行' : '需支付后放行' }}
        </div>
        <div class="pps-msg2">{{ settleResult.message }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { queryParking, payParking, parkingEntry, parkingExit, myPlates } from '@/api'

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

// ---- 无感积分停车演示 ----
const myPlateList = ref([])
const entrying = ref(false)
const exiting = ref(false)
const settleResult = ref(null)
const entryMsg = ref('')

async function loadMyPlates() {
  try { const r = await myPlates(); if (r.ok) myPlateList.value = r.plates || [] } catch (e) {}
}
loadMyPlates()

async function doEntry() {
  if (!plate.value.trim()) return
  entrying.value = true; entryMsg.value = ''; settleResult.value = null
  try {
    const r = await parkingEntry({ plate: plate.value.trim() })
    entryMsg.value = r.ok ? (r.data?.message || '入场成功') : (r.error || '入场失败')
  } catch (e) { entryMsg.value = '网络错误' } finally { entrying.value = false }
}

async function doExit() {
  if (!plate.value.trim()) return
  exiting.value = true; entryMsg.value = ''; settleResult.value = null
  try {
    const r = await parkingExit({ plate: plate.value.trim() })
    if (r.ok) settleResult.value = r.data
    else entryMsg.value = r.error || '结算失败'
  } catch (e) { entryMsg.value = '网络错误' } finally { exiting.value = false }
}
</script>

<style scoped>
.parking-page { padding: 0 12px; min-height: 100vh; background: #000000; }
.pp-back { padding: 10px 0; cursor: pointer; display: inline-block; }

.pp-hero { display: flex; align-items: center; gap: 14px; margin-bottom: 24px; padding: 4px 0; }
.pp-title { font-size: 24px; font-weight: 700; color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,.35); }

.pp-plate-section { margin-bottom: 16px; }
.pp-plate-label { font-size: 13px; font-weight: 600; color: rgba(255,255,255,.7); margin-bottom: 8px; }
.pp-plate-input-wrap {
  background: #000; border: 3px solid #4E5049; border-radius: 12px;
  margin-bottom: 10px; transition: border-color 0.15s;
  box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(107,110,100,.25);
}
.pp-plate-input-wrap:focus-within { border-color: #6B6E64; }
.pp-plate-input {
  width: 100%; padding: 16px; border: none; background: none; outline: none;
  font-size: 28px; font-weight: 700; color: #fff; text-align: center;
  letter-spacing: 2px; font-family: inherit;
}
.pp-plate-presets { display: flex; gap: 8px; flex-wrap: wrap; }
.pp-preset-btn {
  padding: 8px 16px; border: 3px solid #4E5049; border-radius: 20px;
  background: #6B6E64; color: #fff; font-size: 13px; font-weight: 500;
  cursor: pointer; font-family: inherit; transition: all 0.15s;
  box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(107,110,100,.45);
}
.pp-preset-btn:active { box-shadow: inset 5px 5px 10px rgba(0,0,0,.55), inset -2px -2px 5px rgba(107,110,100,.35); }
.pp-preset-btn.add { background: #C4923A; border-color: #9A7425; color: #fff; }

.pp-query-btn {
  width: 100%; padding: 14px; border: 3px solid #9A7425; border-radius: 20px;
  background: #9A7425; color: #fff; font-size: 16px; font-weight: 600;
  cursor: pointer; font-family: inherit; transition: all 0.15s; margin-bottom: 20px;
  box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(196,146,58,.45);
  filter: drop-shadow(0 0.6px 1px rgba(0,0,0,0.4));
}
.pp-query-btn:not(:disabled):active { box-shadow: inset 5px 5px 10px rgba(0,0,0,.55), inset -2px -2px 5px rgba(196,146,58,.35); }
.pp-query-btn:disabled { opacity: 0.5; }

.pp-error {
  background: #8B8B90; border: 3px solid #6A6A6E;
  color: #fff; font-size: 13px; padding: 10px 14px; border-radius: 10px;
  margin-bottom: 16px; text-align: center;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.2);
}

.pp-status-card {
  background: #6B6E64; border: 3px solid #4E5049; border-radius: 12px; padding: 4px 0; margin-bottom: 16px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20);
}
.pps-row { display: flex; justify-content: space-between; padding: 14px 16px; }
.pps-label { font-size: 14px; color: rgba(255,255,255,.85); }
.pps-val { font-size: 14px; color: #fff; font-weight: 500; }
.pps-divider { height: 1px; background: rgba(0,0,0,.25); margin: 0 16px; }
.pps-fee { display: flex; justify-content: space-between; padding: 18px 16px; align-items: center; }
.pps-fee-label { font-size: 16px; font-weight: 600; color: #fff; }
.pps-fee-val { font-size: 28px; font-weight: 800; color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,.35); }

.pp-pay-btn {
  width: 100%; padding: 16px; border: 3px solid #9A7425; border-radius: 20px;
  background: #9A7425; color: #fff; font-size: 17px; font-weight: 700;
  cursor: pointer; font-family: inherit; transition: opacity 0.15s;
  box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(196,146,58,.45);
  filter: drop-shadow(0 0.6px 1px rgba(0,0,0,0.4));
}
.pp-pay-btn:active { box-shadow: inset 5px 5px 10px rgba(0,0,0,.55), inset -2px -2px 5px rgba(196,146,58,.35); }
.pp-pay-btn:disabled { opacity: 0.5; }

.pp-paid-card {
  background: #C4923A; border: 3px solid #9A7425; border-radius: 12px; padding: 32px 20px;
  text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20);
}
.pp-paid-icon {
  width: 48px; height: 48px; border-radius: 50%; background: #9A7425;
  color: #fff; font-size: 20px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  margin: 0 auto 12px;
  box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(196,146,58,.45);
}
.pp-paid-text { font-size: 18px; font-weight: 700; color: #fff; margin-bottom: 8px; text-shadow: 0 1px 2px rgba(0,0,0,.35); }
.pp-paid-detail { font-size: 13px; color: rgba(255,255,255,.85); }

.pp-seamless {
  margin-top: 24px; padding: 16px; background: #8B8B90; border: 3px solid #6A6A6E; border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20);
}
.pps-title { font-size: 17px; font-weight: 700; color: #fff; margin-bottom: 6px; text-shadow: 0 1px 2px rgba(0,0,0,.35); }
.pps-sub { font-size: 12px; color: rgba(255,255,255,.85); line-height: 1.6; margin-bottom: 14px; }
.pps-plates { font-size: 13px; color: rgba(255,255,255,.85); margin-bottom: 14px; }
.pps-plates b { color: #fff; }
.pps-link { color: #fff; margin-left: 8px; text-decoration: underline; cursor: pointer; }
.pps-actions { display: flex; gap: 10px; margin-bottom: 12px; }
.pps-btn {
  flex: 1; padding: 13px; border: 3px solid #4E5049; border-radius: 20px;
  font-size: 15px; font-weight: 600; cursor: pointer; font-family: inherit;
  background: #6B6E64; color: #fff;
  box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(107,110,100,.45);
  filter: drop-shadow(0 0.6px 1px rgba(0,0,0,0.4));
}
.pps-btn.entry { background: #6B6E64; border-color: #4E5049; color: #fff; }
.pps-btn.exit { background: #9B4A3E; border-color: #6E332A; color: #fff;
  box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(155,74,62,.45);
}
.pps-btn:disabled { opacity: 0.5; }
.pps-msg { font-size: 13px; color: #fff; margin-bottom: 10px; }
.pps-result { background: #6B6E64; border: 3px solid #4E5049; border-radius: 10px; padding: 12px 14px; margin-top: 4px;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.2);
}
.pps-r-row { display: flex; justify-content: space-between; padding: 7px 0; font-size: 14px; color: rgba(255,255,255,.85); }
.pps-r-row b { color: #fff; font-weight: 600; }
.pps-r-row.total { border-top: 1px solid rgba(0,0,0,.25); margin-top: 4px; padding-top: 10px; }
.pps-r-row.total b { color: #fff; }
.pps-barrier { margin-top: 10px; padding: 10px; border-radius: 10px; text-align: center; font-size: 14px; font-weight: 600; }
.pps-barrier.open { background: #6B6E64; border: 3px solid #4E5049; color: #fff; }
.pps-barrier.pay { background: #9B4A3E; border: 3px solid #6E332A; color: #fff; }
.pps-msg2 { font-size: 12px; color: rgba(255,255,255,.85); margin-top: 8px; text-align: center; }
</style>
