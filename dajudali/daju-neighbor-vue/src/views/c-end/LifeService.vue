<template>
  <div class="life-page">
    <van-nav-bar title="便民生活" left-text="返回" left-arrow @click-left="$router.back()" />

    <!-- 顶部 hero -->
    <div class="life-hero">
      <div class="lh-title">邻里便民生活</div>
      <div class="lh-sub">停车月卡 · 充电权益 · 母婴室 · 宠物托管，刚需一键办</div>
    </div>

    <!-- 车主权益 -->
    <div class="section-label"><span class="section-en">drive</span><span class="section-cn">车主权益</span></div>
    <div class="life-grid">
      <div
        v-for="(p, idx) in plans"
        :key="p.plan_type"
        class="life-card"
        :class="'life-c-' + idx"
        :style="cardStyle(idx)"
      >
        <div class="lc-top">
          <span class="lc-icon">{{ p.plan_type === 'monthly' ? 'P' : 'C' }}</span>
          <span class="lc-name">{{ p.plan_name }}</span>
        </div>
        <div class="lc-desc">
          {{ p.auto_granted ? ('您的' + p.grantedLevelText + '已自动包含，免费生效') : ('每月 ' + p.price + ' 积分订阅') }}
        </div>
        <div v-if="p.owned" class="lc-owned">已生效 · 至 {{ p.owned.end_date }}</div>
        <van-button
          size="small"
          round
          class="lc-btn"
          :disabled="!!p.owned"
          @click="subscribe(p.plan_type)"
        >{{ p.owned ? '已拥有' : (p.auto_granted ? '免费激活' : '立即订阅') }}</van-button>
      </div>
    </div>

    <!-- 母婴室预约 -->
    <div class="section-label"><span class="section-en">baby</span><span class="section-cn">母婴室预约</span></div>
    <div class="life-card ns-card life-c-2" :style="cardStyle(2)">
      <div class="lc-row">
        <span class="lc-tag">日期</span>
        <van-button size="mini" round plain class="date-chip" :class="{on: nursery.date === today}" @click="nursery.date = today">今天</van-button>
        <van-button size="mini" round plain class="date-chip" :class="{on: nursery.date === tomorrow}" @click="nursery.date = tomorrow">明天</van-button>
        <van-field v-model="nursery.date" placeholder="或手动输入 YYYY-MM-DD" class="date-input" />
      </div>
      <div class="lc-row">
        <span class="lc-tag">时段</span>
        <div class="chip-wrap">
          <span
            v-for="s in nurserySlots"
            :key="s"
            class="slot-chip"
            :class="{on: nursery.slot === s}"
            @click="nursery.slot = s"
          >{{ s }}</span>
        </div>
      </div>
      <div class="lc-row">
        <span class="lc-tag">备注</span>
        <van-field v-model="nursery.note" placeholder="如几月龄、几个宝宝（选填）" class="note-input" />
      </div>
      <van-button block round class="lc-submit" @click="bookNursery">预约母婴室</van-button>

      <div v-if="myNursery.length" class="rec-list">
        <div class="rec-title">我的预约</div>
        <div v-for="r in myNursery" :key="r.id" class="rec-item" :class="{cancel: r.status==='cancelled'}">
          <span>{{ r.date }} {{ r.slot }}</span>
          <span class="rec-mask">尾号{{ r.mask }}</span>
          <van-button v-if="r.status==='booked'" size="mini" plain class="rec-cancel" @click="cancelN(r.id)">取消</van-button>
          <span v-else class="rec-st">{{ r.status==='cancelled' ? '已取消' : '已使用' }}</span>
        </div>
      </div>
    </div>

    <!-- 宠物托管预约 -->
    <div class="section-label"><span class="section-en">pet</span><span class="section-cn">宠物托管</span></div>
    <div class="life-card pet-card life-c-3" :style="cardStyle(3)">
      <div class="lc-row">
        <span class="lc-tag">宠物</span>
        <div class="chip-wrap">
          <span v-for="t in ['狗','猫','其他']" :key="t" class="slot-chip" :class="{on: pet.pet_type === t}" @click="pet.pet_type = t">{{ t }}</span>
        </div>
      </div>
      <div class="lc-row">
        <span class="lc-tag">昵称</span>
        <van-field v-model="pet.pet_name" placeholder="宠物名字（选填）" class="note-input" />
      </div>
      <div class="lc-row">
        <span class="lc-tag">日期</span>
        <van-button size="mini" round plain class="date-chip" :class="{on: pet.date === today}" @click="pet.date = today">今天</van-button>
        <van-button size="mini" round plain class="date-chip" :class="{on: pet.date === tomorrow}" @click="pet.date = tomorrow">明天</van-button>
        <van-field v-model="pet.date" placeholder="或手动输入 YYYY-MM-DD" class="date-input" />
      </div>
      <div class="lc-row">
        <span class="lc-tag">时段</span>
        <div class="chip-wrap">
          <span
            v-for="s in petSlots"
            :key="s"
            class="slot-chip"
            :class="{on: pet.slot === s}"
            @click="pet.slot = s"
          >{{ s }}</span>
        </div>
      </div>
      <div class="lc-row">
        <span class="lc-tag">备注</span>
        <van-field v-model="pet.note" placeholder="如饮食/用药须知（选填）" class="note-input" />
      </div>
      <van-button block round class="lc-submit" @click="bookPet">预约宠物托管</van-button>

      <div v-if="myPet.length" class="rec-list">
        <div class="rec-title">我的托管</div>
        <div v-for="r in myPet" :key="r.id" class="rec-item" :class="{cancel: r.status==='cancelled'}">
          <span>{{ r.pet_type }}·{{ r.pet_name || '无名' }} {{ r.date }} {{ r.slot }}</span>
          <van-button v-if="r.status==='booked'" size="mini" plain class="rec-cancel" @click="cancelP(r.id)">取消</van-button>
          <span v-else class="rec-st">{{ r.status==='cancelled' ? '已取消' : '已完成' }}</span>
        </div>
      </div>
    </div>

    <div class="life-foot">预约自助生效，凭手机尾号到场使用 / 送达宠物</div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { showToast, showSuccessToast, showFailToast } from 'vant'
import { useMemberStore } from '@/stores/member'
import {
  getLifeCards, subscribeLifeCard,
  getNurserySlots, bookNursery as apiBookNursery, cancelNursery as apiCancelNursery, getMyNursery,
  getPetSlots, bookPet as apiBookPet, cancelPet as apiCancelPet, getMyPet
} from '@/api'

const store = useMemberStore()
const phone = computed(() => store.member?.phone || '')

const today = new Date().toISOString().slice(0, 10)
const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 10)

// 多彩卡片配色（对齐首页五色：金黄/浅橙棕/深红棕/灰紫/深灰绿）
const PALETTE = [
  { bg: 'linear-gradient(135deg,#C4923A,#A8741C)', bd: '#8A5E12' },
  { bg: 'linear-gradient(135deg,#C9956C,#B07E4E)', bd: '#A87C48' },
  { bg: 'linear-gradient(135deg,#9B4A3E,#7E3328)', bd: '#5C241D' },
  { bg: 'linear-gradient(135deg,#8B8B90,#6F6F76)', bd: '#54545A' },
  { bg: 'linear-gradient(135deg,#6B6E64,#505247)', bd: '#3C3E36' },
]
const cardStyle = (i) => ({ background: PALETTE[i % PALETTE.length].bg, borderColor: PALETTE[i % PALETTE.length].bd })

const plans = ref([])
const autoMonthlyLevel = ref('金卡')
const autoChargingLevel = ref('钻石卡')

const nurserySlots = ref([])
const petSlots = ref([])
const myNursery = ref([])
const myPet = ref([])

const nursery = reactive({ date: today, slot: '', note: '' })
const pet = reactive({ pet_type: '狗', pet_name: '', date: today, slot: '', note: '' })

function grantedLevelText(p) {
  return p.plan_type === 'monthly' ? autoMonthlyLevel.value : autoChargingLevel.value
}

async function loadCards() {
  if (!phone.value) return
  const res = await getLifeCards(phone.value)
  if (res.ok) {
    plans.value = (res.data.plans || []).map(p => ({ ...p, grantedLevelText: grantedLevelText(p) }))
    autoMonthlyLevel.value = res.data.auto_monthly_level
    autoChargingLevel.value = res.data.auto_charging_level
  }
}

async function subscribe(type) {
  if (!phone.value) { showToast('请先登录会员'); return }
  const res = await subscribeLifeCard(phone.value, type)
  if (res.ok) showSuccessToast(res.data.message || '成功')
  else showFailToast(res.error || '操作失败')
  loadCards()
}

async function loadNursery() {
  const r = await getNurserySlots()
  if (r.ok) nurserySlots.value = r.data.slots || []
  if (phone.value) { const m = await getMyNursery(phone.value); if (m.ok) myNursery.value = m.data || [] }
}
async function bookNursery() {
  if (!phone.value) { showToast('请先登录会员'); return }
  if (!nursery.slot) { showToast('请选择时段'); return }
  const res = await apiBookNursery(phone.value, { name: '', date: nursery.date, slot: nursery.slot, note: nursery.note })
  if (res.ok) { showSuccessToast(res.data.message); nursery.slot = ''; nursery.note = ''; loadNursery() }
  else showFailToast(res.error || '预约失败')
}
async function cancelN(id) {
  const res = await apiCancelNursery(phone.value, id)
  showToast(res.data?.message || (res.ok ? '已取消' : '失败'))
  loadNursery()
}

async function loadPet() {
  const r = await getPetSlots()
  if (r.ok) petSlots.value = r.data.slots || []
  if (phone.value) { const m = await getMyPet(phone.value); if (m.ok) myPet.value = m.data || [] }
}
async function bookPet() {
  if (!phone.value) { showToast('请先登录会员'); return }
  if (!pet.slot) { showToast('请选择时段'); return }
  const res = await apiBookPet(phone.value, { pet_type: pet.pet_type, pet_name: pet.pet_name, date: pet.date, slot: pet.slot, note: pet.note })
  if (res.ok) { showSuccessToast(res.data.message); pet.slot = ''; pet.note = ''; loadPet() }
  else showFailToast(res.error || '预约失败')
}
async function cancelP(id) {
  const res = await apiCancelPet(phone.value, id)
  showToast(res.data?.message || (res.ok ? '已取消' : '失败'))
  loadPet()
}

onMounted(() => {
  store.restore()
  loadCards()
  loadNursery()
  loadPet()
})
</script>

<style scoped>
.life-page { background: #000; min-height: 100vh; padding-bottom: 40px; }
.life-hero {
  margin: 12px 16px 4px;
  background: linear-gradient(135deg, #C4923A, #A8741C);
  border: 3px solid #8A5E12;
  border-radius: 18px;
  padding: 22px 18px;
  text-align: center;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.22), 0 6px 16px rgba(0,0,0,.45);
}
.lh-title { font-size: 20px; font-weight: 700; color: #fff; margin-top: 6px; text-shadow: 0 1px 2px rgba(0,0,0,.35); }
.lh-sub { font-size: 12px; color: rgba(255,255,255,.9); margin-top: 6px; }

.section-label { display: flex; align-items: baseline; gap: 8px; margin: 18px 18px 10px; }
.section-en { font-size: 11px; color: #C4923A; letter-spacing: 1px; font-weight: 600; }
.section-cn { font-size: 16px; color: #fff; font-weight: 600; }

.life-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding: 0 16px; }
.life-card {
  border-radius: 16px;
  border: 3px solid #8A5E12;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.22), 0 6px 16px rgba(0,0,0,.45);
  padding: 16px;
  color: #fff;
}
.life-grid .life-card { padding: 14px; }
.lc-top { display: flex; align-items: center; gap: 8px; }
.lc-icon { font-size: 16px; font-weight: 800; width: 26px; height: 26px; border-radius: 8px; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.28); }
.lc-name { font-size: 16px; font-weight: 700; text-shadow: 0 1px 2px rgba(0,0,0,.35); }
.lc-desc { font-size: 12px; margin: 10px 0 12px; line-height: 1.5; color: rgba(255,255,255,.92); }
.lc-owned { font-size: 12px; margin-bottom: 8px; color: #FFF3D6; }

/* 按钮：首页 dd-btn 凹陷质感 + 跟随卡片五色 */
.lc-btn, .lc-submit, .rec-cancel {
  display: inline-block; padding: 8px 20px; background-color: #9A7425; border: 3px solid #9A7425; border-radius: 20px;
  box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(196,146,58,.45);
  color: #FFFFFF; font-size: var(--fs-aux); font-weight: 600; white-space: nowrap; cursor: pointer;
  filter: drop-shadow(0 0.6px 1px rgba(0,0,0,0.4));
}
.lc-submit { display: block; width: 100%; text-align: center; margin-top: 4px; }
.lc-btn:active, .lc-submit:active, .rec-cancel:active { box-shadow: inset 5px 5px 10px rgba(0,0,0,.55), inset -2px -2px 5px rgba(196,146,58,.35); }
.lc-btn:disabled, .rec-cancel:disabled { opacity: .6; cursor: default; }
.life-c-0 .lc-btn, .life-c-0 .lc-submit, .life-c-0 .rec-cancel { background-color: #8A5E12; border-color: #6E4A0E; box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(196,146,58,.45); }
.life-c-1 .lc-btn, .life-c-1 .lc-submit, .life-c-1 .rec-cancel { background-color: #A87C48; border-color: #87613A; box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(201,149,108,.45); }
.life-c-2 .lc-btn, .life-c-2 .lc-submit, .life-c-2 .rec-cancel { background-color: #5C241D; border-color: #451B16; box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(155,74,62,.45); }
.life-c-3 .lc-btn, .life-c-3 .lc-submit, .life-c-3 .rec-cancel { background-color: #54545A; border-color: #3F3F44; box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(139,139,144,.45); }
.life-c-0 .lc-btn:active, .life-c-0 .lc-submit:active, .life-c-0 .rec-cancel:active { box-shadow: inset 5px 5px 10px rgba(0,0,0,.55), inset -2px -2px 5px rgba(196,146,58,.35); }
.life-c-1 .lc-btn:active, .life-c-1 .lc-submit:active, .life-c-1 .rec-cancel:active { box-shadow: inset 5px 5px 10px rgba(0,0,0,.55), inset -2px -2px 5px rgba(201,149,108,.35); }
.life-c-2 .lc-btn:active, .life-c-2 .lc-submit:active, .life-c-2 .rec-cancel:active { box-shadow: inset 5px 5px 10px rgba(0,0,0,.55), inset -2px -2px 5px rgba(155,74,62,.35); }
.life-c-3 .lc-btn:active, .life-c-3 .lc-submit:active, .life-c-3 .rec-cancel:active { box-shadow: inset 5px 5px 10px rgba(0,0,0,.55), inset -2px -2px 5px rgba(139,139,144,.35); }

.ns-card, .pet-card { margin: 0 16px; }

.lc-row { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.lc-tag { font-size: 13px; color: #fff; width: 36px; flex-shrink: 0; font-weight: 600; }
.chip-wrap { display: flex; flex-wrap: wrap; gap: 8px; }
.slot-chip {
  font-size: 12px; padding: 5px 12px; border-radius: 14px;
  background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.4);
  color: #fff; cursor: pointer;
}
.slot-chip.on { background: #fff; color: #333; border-color: #fff; font-weight: 700; }
.date-chip { background: rgba(255,255,255,.16); border-color: rgba(255,255,255,.5); color: #fff; }
.date-chip.on { background: #fff; color: #333; }
.date-input, .note-input { flex: 1; min-width: 120px; background: rgba(255,255,255,.12); border-radius: 8px; }
.date-input :deep(.van-field__control), .note-input :deep(.van-field__control) { color: #fff; }

.rec-list { margin-top: 14px; border-top: 1px solid rgba(255,255,255,.25); padding-top: 10px; }
.rec-title { font-size: 13px; font-weight: 700; color: #fff; margin-bottom: 8px; }
.rec-item { display: flex; align-items: center; gap: 8px; font-size: 12px; color: rgba(255,255,255,.92); padding: 5px 0; }
.rec-item.cancel { opacity: .55; }
.rec-mask { color: #FFF3D6; }
.rec-st { color: #FFF3D6; }

.life-foot { text-align: center; font-size: 11px; color: rgba(255,255,255,.55); margin: 22px 16px 0; }
</style>
