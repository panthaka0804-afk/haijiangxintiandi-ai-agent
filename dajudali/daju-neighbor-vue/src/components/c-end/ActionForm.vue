<template>
  <van-overlay :show="visible" @click="$emit('close')" z-index="1000" />

  <transition name="af-popup">
    <div v-if="visible" class="af-container">
      <div class="af-sheet" @click.stop>
        <div class="af-handle"></div>
        <div class="af-header">
          <button class="af-cancel-btn" @click="$emit('close')">取消</button>
          <h3 class="af-title">{{ title }}</h3>
          <div class="af-header-spacer"></div>
        </div>

        <div class="af-form">

          <!-- ===== 活动报名 ===== -->
          <template v-if="type === 'register'">
            <div class="af-field" @click="showEventPicker = true">
              <span class="af-label">活动</span>
              <span class="af-value" :class="{ placeholder: !form.activity }">
                {{ form.activity || '请选择活动' }}
              </span>
              <span class="af-chevron">›</span>
            </div>
            <div class="af-divider"></div>
            <div class="af-field">
              <span class="af-label">姓名</span>
              <input class="af-input" v-model="form.name" placeholder="请输入姓名" />
            </div>
            <div class="af-divider"></div>
            <div class="af-field">
              <span class="af-label">手机号</span>
              <input class="af-input" v-model="form.phone" type="tel" maxlength="11" placeholder="请输入手机号" />
            </div>
            <div class="af-divider"></div>
            <div class="af-field" @click="showCountPicker = true">
              <span class="af-label">人数</span>
              <span class="af-value" :class="{ placeholder: !form.count }">
                {{ form.count || '请选择人数' }}
              </span>
              <span class="af-chevron">›</span>
            </div>
            <div class="af-divider"></div>
            <div class="af-field af-field--textarea">
              <span class="af-label">备注</span>
              <textarea class="af-textarea" v-model="form.remark" rows="2" placeholder="有什么需求可以写这里"></textarea>
            </div>
          </template>

          <!-- ===== 报修 ===== -->
          <template v-else-if="type === 'repair'">
            <div class="af-field" @click="showRepairPicker = true">
              <span class="af-label">报修类型</span>
              <span class="af-value" :class="{ placeholder: !form.repairType }">
                {{ form.repairType || '请选择' }}
              </span>
              <span class="af-chevron">›</span>
            </div>
            <div class="af-divider"></div>
            <div class="af-field">
              <span class="af-label">联系人</span>
              <input class="af-input" v-model="form.name" placeholder="请输入姓名" />
            </div>
            <div class="af-divider"></div>
            <div class="af-field">
              <span class="af-label">手机号</span>
              <input class="af-input" v-model="form.phone" type="tel" maxlength="11" placeholder="请输入手机号" />
            </div>
            <div class="af-divider"></div>
            <div class="af-field">
              <span class="af-label">位置</span>
              <input class="af-input" v-model="form.location" placeholder="如3层扶梯旁" />
            </div>
            <div class="af-divider"></div>
            <div class="af-field af-field--textarea">
              <span class="af-label">问题描述</span>
              <textarea class="af-textarea" v-model="form.remark" rows="3" placeholder="请描述需要维修的问题"></textarea>
            </div>
          </template>

          <!-- ===== 招商合作（合并商家入驻） ===== -->
          <template v-else-if="type === 'biz_guide'">
            <div class="af-field" @click="showGuidePicker = true">
              <span class="af-label">咨询类型</span>
              <span class="af-value" :class="{ placeholder: !form.guideType }">
                {{ form.guideType || '请选择' }}
              </span>
              <span class="af-chevron">›</span>
            </div>
            <div class="af-divider"></div>
            <div class="af-field">
              <span class="af-label">联系人</span>
              <input class="af-input" v-model="form.name" placeholder="请输入姓名" />
            </div>
            <div class="af-divider"></div>
            <div class="af-field">
              <span class="af-label">手机号</span>
              <input class="af-input" v-model="form.phone" type="tel" maxlength="11" placeholder="请输入手机号" />
            </div>
            <div class="af-divider"></div>
            <div class="af-field">
              <span class="af-label">品牌/公司</span>
              <input class="af-input" v-model="form.brand" placeholder="请输入品牌或公司名称" />
            </div>
            <div class="af-divider"></div>
            <div class="af-field" @click="showBizPicker = true">
              <span class="af-label">经营品类</span>
              <span class="af-value" :class="{ placeholder: !form.bizType }">
                {{ form.bizType || '请选择' }}
              </span>
              <span class="af-chevron">›</span>
            </div>
            <div class="af-divider"></div>
            <div class="af-field">
              <span class="af-label">需求面积</span>
              <input class="af-input" v-model="form.area" placeholder="如：50-100㎡" />
            </div>
            <div class="af-divider"></div>
            <div class="af-field af-field--textarea">
              <span class="af-label">需求描述</span>
              <textarea class="af-textarea" v-model="form.remark" rows="3" placeholder="如：意向面积、预算、期望楼层等"></textarea>
            </div>
          </template>
        </div>

        <button class="af-submit-btn" @click="submit">{{ submitText }}</button>
      </div>
    </div>
  </transition>

  <!-- van-picker 选择器弹窗 -->
  <van-popup v-model:show="showEventPicker" position="bottom" round>
    <van-picker :columns="eventOptions" @confirm="onConfirmEvent" @cancel="showEventPicker = false" />
  </van-popup>
  <van-popup v-model:show="showCountPicker" position="bottom" round>
    <van-picker :columns="countOptions" @confirm="onConfirmCount" @cancel="showCountPicker = false" />
  </van-popup>
  <van-popup v-model:show="showRepairPicker" position="bottom" round>
    <van-picker :columns="repairOptions" @confirm="onConfirmRepair" @cancel="showRepairPicker = false" />
  </van-popup>
  <van-popup v-model:show="showBizPicker" position="bottom" round>
    <van-picker :columns="bizOptions" @confirm="onConfirmBiz" @cancel="showBizPicker = false" />
  </van-popup>
  <van-popup v-model:show="showGuidePicker" position="bottom" round>
    <van-picker :columns="guideOptions" @confirm="onConfirmGuide" @cancel="showGuidePicker = false" />
  </van-popup>
</template>

<script setup>
import { reactive, ref, watch, computed } from 'vue'
import { showToast } from 'vant'

const props = defineProps({
  visible: Boolean,
  type: { type: String, default: 'register' }
})

const emit = defineEmits(['close', 'submit'])

const form = reactive({
  activity: '', name: '', phone: '', count: '', remark: '',
  repairType: '', location: '', brand: '', bizType: '', area: '', guideType: ''
})

const showEventPicker = ref(false)
const showCountPicker = ref(false)
const showRepairPicker = ref(false)
const showBizPicker = ref(false)
const showGuidePicker = ref(false)

const titles = { register: '活动报名', repair: '物业报修', biz_guide: '招商合作' }
const submitTexts = { register: '提交报名', repair: '提交报修', biz_guide: '提交咨询' }

const title = computed(() => titles[props.type] || '')
const submitText = computed(() => submitTexts[props.type] || '提交')

const eventOptions = [
  { text: '亲子手作课堂（周六 14:00）', value: '亲子手作课堂（周六 14:00）' },
  { text: '海江夜巷民谣之夜（周日 19:00）', value: '海江夜巷民谣之夜（周日 19:00）' },
  { text: '夜校课程（每晚 19:00）', value: '夜校课程（每晚 19:00）' },
  { text: '宠物社交派对（每月15日）', value: '宠物社交派对（每月15日）' },
  { text: '亲子烘焙体验（周三 15:00）', value: '亲子烘焙体验（周三 15:00）' },
  { text: '其他活动', value: '其他活动' },
]
const countOptions = [
  { text: '1人', value: '1人' }, { text: '2人', value: '2人' },
  { text: '3人', value: '3人' }, { text: '4人', value: '4人' },
  { text: '5人及以上', value: '5人及以上' },
]
const repairOptions = [
  { text: '水电故障', value: '水电故障' }, { text: '空调不制冷', value: '空调不制冷' },
  { text: '漏水', value: '漏水' }, { text: '门锁/门窗损坏', value: '门锁/门窗损坏' },
  { text: '电梯故障', value: '电梯故障' }, { text: '卫生/清洁问题', value: '卫生/清洁问题' },
  { text: '其他', value: '其他' },
]
const bizOptions = [
  { text: '餐饮', value: '餐饮' }, { text: '零售', value: '零售' },
  { text: '教培', value: '教培' }, { text: '亲子', value: '亲子' },
  { text: '休闲娱乐', value: '休闲娱乐' }, { text: '美容美发', value: '美容美发' },
  { text: '其他', value: '其他' },
]
const guideOptions = [
  { text: '空铺招商', value: '空铺招商' },
  { text: '租赁报价咨询', value: '租赁报价咨询' },
  { text: '多经场地（市集/快闪）', value: '多经场地（市集/快闪）' },
  { text: '共享教室租赁', value: '共享教室租赁' },
  { text: '会客厅/沙龙场地', value: '会客厅/沙龙场地' },
  { text: '广告位投放', value: '广告位投放' },
  { text: '合作/分成模式咨询', value: '合作/分成模式咨询' },
  { text: '快闪入驻', value: '快闪入驻' },
  { text: '品牌入驻开店', value: '品牌入驻开店' },
  { text: '其他商务合作', value: '其他商务合作' },
]

watch(() => props.visible, (v) => {
  if (v) Object.keys(form).forEach(k => form[k] = '')
})

function onConfirmEvent({ selectedOptions }) { form.activity = selectedOptions[0]?.value || ''; showEventPicker.value = false }
function onConfirmCount({ selectedOptions }) { form.count = selectedOptions[0]?.value || ''; showCountPicker.value = false }
function onConfirmRepair({ selectedOptions }) { form.repairType = selectedOptions[0]?.value || ''; showRepairPicker.value = false }
function onConfirmBiz({ selectedOptions }) { form.bizType = selectedOptions[0]?.value || ''; showBizPicker.value = false }
function onConfirmGuide({ selectedOptions }) { form.guideType = selectedOptions[0]?.value || ''; showGuidePicker.value = false }

function validate() {
  if (!form.name.trim()) { showToast('请填写联系人'); return false }
  if (!form.phone.trim() || !/^1\d{10}$/.test(form.phone)) { showToast('请填写正确的手机号'); return false }
  return true
}

function submit() {
  if (!validate()) return
  showToast('提交成功，我们会尽快联系您！')
  emit('submit', { type: props.type, ...form })
  emit('close')
}
</script>

<style scoped>
.af-container {
  position: fixed;
  bottom: 0;
  left: 0;
  width: 100%;
  z-index: 1001;
}

.af-sheet {
  background: #1A1A1A;
  border-radius: 20px 20px 0 0;
  padding-bottom: env(safe-area-inset-bottom, 24px);
  max-height: 85vh;
  overflow-y: auto;
}

.af-handle {
  width: 36px;
  height: 5px;
  background: #1A1A1A;
  border-radius: 3px;
  margin: 8px auto 0;
}

.af-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px 8px;
}

.af-cancel-btn {
  font-size: 16px;
  color: #9E9E9E;
  background: none;
  border: none;
  padding: 4px;
  font-family: -apple-system, 'PingFang SC', sans-serif;
  cursor: pointer;
}

.af-header-spacer { width: 52px; }

.af-title {
  font-size: 17px;
  font-weight: 600;
  color: #F0F0F0;
  margin: 0;
  letter-spacing: -0.2px;
  font-family: -apple-system, 'PingFang SC', sans-serif;
}

.af-form {
  margin: 0 16px;
  background: #1A1A1A;
  border-radius: 12px;
  overflow: hidden;
}

.af-field {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  min-height: 44px;
  background: #1A1A1A;
  cursor: default;
  gap: 12px;
}

.af-field--textarea {
  align-items: flex-start;
  padding-bottom: 8px;
}

.af-label {
  font-size: 15px;
  color: #F0F0F0;
  white-space: nowrap;
  min-width: 64px;
  font-family: -apple-system, 'PingFang SC', sans-serif;
}

.af-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 15px;
  color: #F0F0F0;
  text-align: right;
  font-family: -apple-system, 'PingFang SC', sans-serif;
  background: transparent;
}

.af-input::placeholder,
.af-textarea::placeholder {
  color: #C7C7CC;
}

.af-textarea {
  flex: 1;
  border: none;
  outline: none;
  font-size: 15px;
  color: #F0F0F0;
  text-align: right;
  font-family: -apple-system, 'PingFang SC', sans-serif;
  background: transparent;
  resize: none;
  padding: 0;
  line-height: 1.5;
}

.af-value {
  flex: 1;
  text-align: right;
  font-size: 15px;
  color: #F0F0F0;
  font-family: -apple-system, 'PingFang SC', sans-serif;
}

.af-value.placeholder {
  color: #C7C7CC;
}

.af-chevron {
  font-size: 20px;
  color: #C7C7CC;
  font-weight: 300;
  line-height: 1;
}

.af-divider {
  height: 0.5px;
  background: #1A1A1A;
  margin: 0 16px;
}

.af-submit-btn {
  display: block;
  width: calc(100% - 32px);
  margin: 20px 16px;
  padding: 15px 0;
  background: linear-gradient(135deg, #1A1A1A, #1A1A1A);
  color: #fff;
  border: none;
  border-radius: 14px;
  font-size: 17px;
  font-weight: 700;
  cursor: pointer;
  font-family: -apple-system, 'PingFang SC', sans-serif;
  letter-spacing: -0.2px;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 4px 16px #999999;
}

.af-submit-btn:active {
  opacity: 0.85;
  transform: scale(0.98);
}

/* 动画 */
.af-popup-enter-active,
.af-popup-leave-active {
  transition: all 0.35s cubic-bezier(0.32, 0.72, 0, 1);
}

.af-popup-enter-from .af-sheet,
.af-popup-leave-to .af-sheet {
  transform: translateY(100%);
}
</style>
