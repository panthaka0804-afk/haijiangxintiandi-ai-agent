<template>
  <div class="ps-root">
    <header class="ps-hdr">
      <h1>物业报修与投诉</h1>
      <span class="ps-sub">设施报修 · 投诉建议</span>
    </header>

    <!-- Tab切换 -->
    <div class="ps-tabs">
      <button v-for="t in tabs" :key="t.key" :class="{ active: activeTab === t.key }" @click="activeTab = t.key">{{ t.label }}</button>
    </div>

    <!-- ====== 设施报修 ====== -->
    <section v-if="activeTab === 'repair'" class="ps-section">
      <div class="ps-card">
        <div class="ps-card-hdr">设施报修</div>
        <div class="ps-hint">描述故障位置与问题，AI 自动分类并分派物业工程岗</div>
        <div class="ps-form">
          <input v-model="repair.location" placeholder="故障位置（如 3F 扶梯旁卫生间）" class="ps-input" />
          <textarea v-model="repair.description" placeholder="问题描述（如 水龙头漏水、灯泡不亮）" class="ps-input ps-textarea" rows="3"></textarea>
          <!-- 图片上传 -->
          <div class="ps-upload">
            <label class="ps-upload-btn">
              <input type="file" accept="image/*" @change="onImagePick" hidden />
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg>
              {{ repair.image ? '已选图片' : '上传图片（可选）' }}
            </label>
            <span v-if="repair.image" class="ps-upload-clear" @click="repair.image = ''">移除</span>
          </div>
          <input v-model="repair.name" placeholder="联系人姓名" class="ps-input" />
          <input v-model="repair.phone" placeholder="手机号" class="ps-input" />
          <button class="ps-btn ps-btn-primary" @click="submitRepair" :disabled="repairing">{{ repairing ? '提交中...' : '提交报修' }}</button>
        </div>
        <!-- 分类结果 -->
        <div v-if="repairResult" class="ps-result">
          <div class="ps-result-line">已分类：{{ repairResult.category }} · 分派：{{ repairResult.assignee }}</div>
          <div class="ps-result-line">{{ repairResult.message }}</div>
        </div>
      </div>
    </section>

    <!-- ====== 投诉建议 ====== -->
    <section v-if="activeTab === 'complaint'" class="ps-section">
      <div class="ps-card">
        <div class="ps-card-hdr">投诉建议</div>
        <div class="ps-hint">提交投诉或建议，AI 自动分类分级，处理完成后推送结果并邀请评价</div>
        <div class="ps-form">
          <select v-model="complaint.kind" class="ps-input">
            <option value="投诉">投诉</option>
            <option value="建议">建议</option>
          </select>
          <textarea v-model="complaint.content" placeholder="请描述您的投诉或建议内容" class="ps-input ps-textarea" rows="4"></textarea>
          <input v-model="complaint.name" placeholder="联系人姓名" class="ps-input" />
          <input v-model="complaint.phone" placeholder="手机号" class="ps-input" />
          <button class="ps-btn ps-btn-primary" @click="submitComplaint" :disabled="complaining">{{ complaining ? '提交中...' : '提交' }}</button>
        </div>
        <div v-if="complaintResult" class="ps-result" :class="'lv-' + complaintResult.level">
          <div class="ps-result-line ps-result-level">{{ complaintResult.level_name }} · 分类：{{ complaintResult.category }}</div>
          <div class="ps-result-line">处理时限：{{ complaintResult.deadline }}</div>
          <div class="ps-result-line">{{ complaintResult.requirement }}</div>
        </div>
      </div>
    </section>

    <!-- ====== 我的工单进度 ====== -->
    <section class="ps-section">
      <div class="ps-card">
        <div class="ps-card-hdr">我的工单进度</div>
        <div class="ps-form">
          <div class="ps-row2">
            <input v-model="queryPhone" placeholder="输入手机号查询进度" class="ps-input" />
            <button class="ps-btn ps-btn-primary ps-btn-sm" @click="loadMyOrders">查询</button>
          </div>
        </div>
        <div v-if="myOrders.length" class="ps-orders">
          <div v-for="o in myOrders" :key="o.id" class="ps-order">
            <div class="ps-order-main">
              <span class="ps-order-title">{{ o.title }}</span>
              <span class="ps-order-status" :class="'st-'+o.status">{{ statusMap[o.status] || o.status }}</span>
            </div>
            <div class="ps-order-meta">{{ o.type }} · 优先级 {{ o.priority === 'high' ? '紧急' : '普通' }} · {{ (o.created_at || '').slice(5, 16) }}</div>
          </div>
        </div>
        <div v-else-if="searched" class="ps-empty">暂无报修/投诉工单</div>
      </div>
    </section>

    <RatingModal
      :visible="ratingVisible"
      :title="ratingTitle"
      subtitle="您的评价将帮助我们精准定位服务卡点"
      feedback-type="business"
      :biz-type="ratingBizType"
      :order-id="ratingOrderId"
      :phone="repair.phone || complaint.phone"
      @close="ratingVisible = false"
    />
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import RatingModal from '@/components/c-end/RatingModal.vue'

const tabs = [
  { key: 'repair', label: '设施报修' },
  { key: 'complaint', label: '投诉建议' }
]
const activeTab = ref('repair')
const statusMap = { pending: '待处理', processing: '处理中', done: '已完成', closed: '已关闭' }

// 满意度评价
const ratingVisible = ref(false)
const ratingBizType = ref('报修')
const ratingOrderId = ref('')
const ratingTitle = ref('请评价本次服务')

const repair = reactive({ location: '', description: '', image: '', name: '', phone: '' })
const complaint = reactive({ kind: '投诉', content: '', name: '', phone: '' })
const repairing = ref(false)
const complaining = ref(false)
const repairResult = ref(null)
const complaintResult = ref(null)

const queryPhone = ref('')
const myOrders = ref([])
const searched = ref(false)

function validPhone(p) { return /^1\d{10}$/.test(p) }

function onImagePick(e) {
  const file = e.target.files[0]
  if (!file) return
  if (file.size > 1024 * 1024) return alert('图片不能超过 1MB')
  const reader = new FileReader()
  reader.onload = () => { repair.image = reader.result }
  reader.readAsDataURL(file)
}

async function submitRepair() {
  if (!repair.description || !repair.name || !validPhone(repair.phone)) return alert('请填写问题描述、联系人和手机号')
  repairing.value = true
  try {
    const resp = await fetch('/api/repair', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(repair) })
    const data = await resp.json()
    if (data.ok) {
      repairResult.value = data.data
      Object.assign(repair, { location: '', description: '', image: '', name: '', phone: '' })
      // 推送业务办理评价
      ratingBizType.value = '报修'
      ratingOrderId.value = String(data.data.work_order_id || '')
      ratingTitle.value = '请评价本次报修服务'
      ratingVisible.value = true
    } else {
      alert(data.error || '提交失败')
    }
  } catch (e) { alert('网络错误') }
  repairing.value = false
}

async function submitComplaint() {
  if (!complaint.content || !complaint.name || !validPhone(complaint.phone)) return alert('请填写内容、联系人和手机号')
  complaining.value = true
  try {
    const resp = await fetch('/api/complaint', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(complaint) })
    const data = await resp.json()
    if (data.ok) {
      complaintResult.value = data.data
      Object.assign(complaint, { content: '', name: '', phone: '' })
      // 推送业务办理评价
      ratingBizType.value = '投诉建议'
      ratingOrderId.value = String(data.data.work_order_id || '')
      ratingTitle.value = '请评价本次投诉/建议服务'
      ratingVisible.value = true
    } else {
      alert(data.error || '提交失败')
    }
  } catch (e) { alert('网络错误') }
  complaining.value = false
}

async function loadMyOrders() {
  if (!validPhone(queryPhone.value)) return alert('请输入正确的手机号')
  try {
    const resp = await fetch('/api/property/my-orders?phone=' + queryPhone.value)
    const data = await resp.json()
    if (data.ok) { myOrders.value = data.data; searched.value = true }
  } catch (e) { alert('网络错误') }
}
</script>

<style scoped>
.ps-root { min-height: 100vh; background: #000000; color: #fff; padding: 16px; font-family: 'PingFang SC', sans-serif; max-width: 480px; margin: 0 auto; }
.ps-hdr { text-align: center; padding: 24px 0 16px; }
.ps-hdr h1 { margin: 0 0 6px; font-size: 22px; color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,.35); }
.ps-sub { font-size: 13px; color: rgba(255,255,255,.6); }

.ps-tabs { display: flex; gap: 6px; margin-bottom: 20px; }
.ps-tabs button { flex: 1; padding: 8px 14px; border-radius: 20px; border: 3px solid #4E5049; background: #6B6E64; color: #fff; font-size: 13px; cursor: pointer; white-space: nowrap;
  box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(107,110,100,.45); }
.ps-tabs button.active { background: #8B8B90; border-color: #6A6A6E; color: #fff; }

.ps-card { background: #6B6E64; border: 3px solid #4E5049; border-radius: 12px; padding: 16px; margin-bottom: 14px; box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20); }
.ps-card-hdr { font-size: 15px; font-weight: 600; color: #fff; margin-bottom: 8px; text-shadow: 0 1px 2px rgba(0,0,0,.35); }
.ps-hint { font-size: 12px; color: rgba(255,255,255,.8); margin-bottom: 14px; line-height: 1.5; }
.ps-form { display: flex; flex-direction: column; gap: 10px; }
.ps-input { padding: 10px 12px; border-radius: 8px; border: 3px solid #4E5049; background: #000; color: #fff; font-size: 14px;
  box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(107,110,100,.25); }
.ps-input::placeholder { color: rgba(255,255,255,.4); }
.ps-textarea { resize: vertical; min-height: 60px; }
.ps-row2 { display: flex; gap: 10px; }
.ps-row2 .ps-input { flex: 1; }

.ps-upload { display: flex; align-items: center; gap: 10px; }
.ps-upload-btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 12px; border-radius: 8px; border: 1px dashed #6A6A6E; color: rgba(255,255,255,.85); font-size: 13px; cursor: pointer; }
.ps-upload-clear { font-size: 12px; color: #D4A59A; cursor: pointer; }

.ps-btn { padding: 10px; border-radius: 20px; border: 3px solid #9A7425; font-size: 15px; font-weight: 600; cursor: pointer; font-family: inherit;
  background: #9A7425; color: #fff;
  box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(196,146,58,.45);
  filter: drop-shadow(0 0.6px 1px rgba(0,0,0,0.4)); }
.ps-btn:active { box-shadow: inset 5px 5px 10px rgba(0,0,0,.55), inset -2px -2px 5px rgba(196,146,58,.35); }
.ps-btn:disabled { opacity: 0.5; cursor: default; }
.ps-btn-primary { background: #9A7425; border-color: #9A7425; color: #fff; }
.ps-btn-sm { flex-shrink: 0; padding: 10px 18px; font-size: 14px; }

.ps-result { margin-top: 14px; padding: 12px 14px; background: #8B8B90; border: 3px solid #6A6A6E; border-radius: 10px; box-shadow: inset 0 1px 0 rgba(255,255,255,.2); }
.ps-result.lv-urgent { border-color: #C4923A; }
.ps-result.lv-critical { border-color: #9B4A3E; background: #9B4A3E; }
.ps-result-line { font-size: 13px; color: #fff; line-height: 1.6; }
.ps-result-level { font-weight: 600; color: #C4923A; }
.ps-result.lv-critical .ps-result-level { color: #D4A59A; }

.ps-orders { margin-top: 12px; }
.ps-order { padding: 12px 0; border-bottom: 1px solid rgba(0,0,0,.25); }
.ps-order:last-child { border-bottom: none; }
.ps-order-main { display: flex; justify-content: space-between; align-items: center; }
.ps-order-title { font-size: 14px; color: #fff; }
.ps-order-status { font-size: 12px; padding: 2px 8px; border-radius: 4px; background: #4E5049; color: #fff; }
.ps-order-status.st-pending { background: #4E5049; color: #fff; }
.ps-order-status.st-processing { background: #6B6E64; color: #fff; }
.ps-order-status.st-done { background: #8B8B90; color: #fff; }
.ps-order-meta { font-size: 12px; color: rgba(255,255,255,.7); margin-top: 4px; }
.ps-empty { text-align: center; color: rgba(255,255,255,.5); padding: 20px 0; font-size: 13px; }
</style>
