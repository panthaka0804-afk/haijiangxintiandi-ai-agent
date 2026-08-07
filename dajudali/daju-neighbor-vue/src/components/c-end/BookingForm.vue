<template>
  <van-action-sheet :show="visible" @update:show="$emit('update:visible', $event)" title="在线预约" :close-on-click-overlay="false">
    <div style="padding:12px 16px;max-height:70vh;overflow-y:auto;">
      <div style="margin-bottom:12px;">
        <label style="font-size:13px;color:#8E8E93;">预约类型</label>
        <van-field v-model="form.type" readonly clickable placeholder="请选择" @click="showTypePicker = true" />
      </div>
      <div style="margin-bottom:12px;">
        <label style="font-size:13px;color:#8E8E93;">商户/场地</label>
        <van-field v-model="form.merchant" readonly clickable placeholder="请先选择类型" @click="showMerchantPicker = true" />
      </div>
      <div style="margin-bottom:12px;">
        <label style="font-size:13px;color:#8E8E93;">预约日期</label>
        <van-field v-model="form.date" readonly clickable placeholder="请选择" @click="showDatePicker = true" />
      </div>
      <div style="margin-bottom:12px;">
        <label style="font-size:13px;color:#8E8E93;">预约时间</label>
        <van-field v-model="form.time" readonly clickable placeholder="请选择" @click="showTimePicker = true" />
      </div>
      <div style="margin-bottom:12px;">
        <label style="font-size:13px;color:#8E8E93;">人数</label>
        <van-field v-model="form.count" readonly clickable placeholder="请选择" @click="showCountPicker = true" />
      </div>
      <van-field v-model="form.name" label="姓名" placeholder="请输入姓名" />
      <van-field v-model="form.phone" label="手机号" type="tel" placeholder="请输入11位手机号" maxlength="11" />
      <van-field v-model="form.note" label="备注" placeholder="特殊需求（选填）" />
      <div style="display:flex;gap:12px;margin-top:16px;padding-bottom:8px;">
        <van-button style="flex:1" @click="$emit('update:visible', false)">取消</van-button>
        <van-button style="flex:1" type="primary" @click="submit" :loading="submitting">提交预约</van-button>
      </div>
    </div>
  </van-action-sheet>

  <!-- Type Picker -->
  <van-action-sheet :show="showTypePicker" @update:show="showTypePicker = $event" title="选择预约类型">
    <div style="padding:8px;">
      <div v-for="item in typeColumns" :key="item" style="padding:14px 16px;font-size:16px;border-bottom:1px solid #f0f0f0;cursor:pointer;" @click="onSelectType(item)">{{ item }}</div>
    </div>
  </van-action-sheet>

  <!-- Merchant Picker -->
  <van-action-sheet :show="showMerchantPicker" @update:show="showMerchantPicker = $event" title="选择商户/场地">
    <div style="padding:8px;">
      <div v-for="item in currentMerchants" :key="item" style="padding:14px 16px;font-size:16px;border-bottom:1px solid #f0f0f0;cursor:pointer;" @click="onSelectMerchant(item)">{{ item }}</div>
    </div>
  </van-action-sheet>

  <!-- Date Picker -->
  <van-action-sheet :show="showDatePicker" @update:show="showDatePicker = $event" title="选择日期">
    <div style="padding:8px;max-height:50vh;overflow-y:auto;">
      <div v-for="item in dateColumns" :key="item.value" style="padding:14px 16px;font-size:16px;border-bottom:1px solid #f0f0f0;cursor:pointer;" @click="onSelectDate(item.value)">{{ item.label }}</div>
    </div>
  </van-action-sheet>

  <!-- Time Picker -->
  <van-action-sheet :show="showTimePicker" @update:show="showTimePicker = $event" title="选择时间">
    <div style="padding:8px;">
      <div v-for="item in timeColumns" :key="item" style="padding:14px 16px;font-size:16px;border-bottom:1px solid #f0f0f0;cursor:pointer;" @click="onSelectTime(item)">{{ item }}</div>
    </div>
  </van-action-sheet>

  <!-- Count Picker -->
  <van-action-sheet :show="showCountPicker" @update:show="showCountPicker = $event" title="选择人数">
    <div style="padding:8px;">
      <div v-for="item in countColumns" :key="item" style="padding:14px 16px;font-size:16px;border-bottom:1px solid #f0f0f0;cursor:pointer;" @click="onSelectCount(item)">{{ item }}</div>
    </div>
  </van-action-sheet>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { showToast } from 'vant'

defineProps({ visible: Boolean })
const emit = defineEmits(['update:visible', 'submitted'])

const form = reactive({ type: '', merchant: '', date: '', time: '', count: '', name: '', phone: '', note: '' })
const submitting = ref(false)

const showTypePicker = ref(false)
const showMerchantPicker = ref(false)
const showDatePicker = ref(false)
const showTimePicker = ref(false)
const showCountPicker = ref(false)

const maxDate = new Date(Date.now() + 30 * 86400000)
const dateValue = ref(new Date())
const dateColumns = computed(() => {
  const days = []
  const today = new Date()
  for (let i = 0; i < 30; i++) {
    const d = new Date(today.getTime() + i * 86400000)
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    const weekdays = ['周日','周一','周二','周三','周四','周五','周六']
    const wd = weekdays[d.getDay()]
    const val = `${y}-${m}-${day}`
    const label = i === 0 ? `今天 ${m}月${day}日 ${wd}` : ` ${val} ${wd}`
    days.push({ label, value: val })
  }
  return days
})
const typeColumns = ['预定商户包厢', '热门餐厅排队', '预约运动场地']
const timeColumns = Array.from({length: 12}, (_, i) => `${10 + i}:00-${11 + i}:00`)
const countColumns = ['1人','2人','3人','4人','5人','6人','7-10人','10人以上']

const merchantMap = {
  '预定商户包厢': ['蜀大侠火锅', '棒约翰披萨', '星巴克', '金饰珠宝VIP室'],
  '热门餐厅排队': ['蜀大侠火锅', '棒约翰披萨', 'B1美食广场-热门档口', '星巴克'],
  '预约运动场地': ['网球场', '室内篮球场', '瑜伽舞蹈室', '健身房私教区']
}

const currentMerchants = computed(() => merchantMap[form.type] || [])

function onSelectType(item) { form.type = item; form.merchant = ''; showTypePicker.value = false }
function onSelectMerchant(item) { form.merchant = item; showMerchantPicker.value = false }
function onSelectTime(item) { form.time = item; showTimePicker.value = false }
function onSelectCount(item) { form.count = item; showCountPicker.value = false }

function onSelectDate(val) {
  form.date = val
  showDatePicker.value = false
}

async function submit() {
  if (!form.type) { showToast('请选择预约类型'); return }
  if (!form.merchant) { showToast('请选择商户/场地'); return }
  if (!form.date) { showToast('请选择日期'); return }
  if (!form.time) { showToast('请选择时间'); return }
  if (!form.name.trim()) { showToast('请输入姓名'); return }
  if (!/^\d{11}$/.test(form.phone)) { showToast('请输入正确的11位手机号'); return }

  submitting.value = true
  try {
    const desc = `预约类型：${form.type}\n商户/场地：${form.merchant}\n时间：${form.date} ${form.time}\n人数：${form.count || '未指定'}\n备注：${form.note || '无'}`
    const res = await fetch('/api/orders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: '预约', title: `${form.type} - ${form.merchant}`, description: desc, reporter_contact: form.phone })
    })
    const json = await res.json()
    if (json.ok) {
      showToast('预约成功，商户将尽快确认')
      emit('update:visible', false)
      emit('submitted', form)
    } else {
      showToast(json.error || '提交失败')
    }
  } catch {
    showToast('网络错误')
  } finally {
    submitting.value = false
  }
}
</script>
