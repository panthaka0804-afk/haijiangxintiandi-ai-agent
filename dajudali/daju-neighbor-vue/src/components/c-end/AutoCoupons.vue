<template>
  <div class="auto-coupons">
    <div class="section-label" v-if="!hideHeader">
      <span class="section-en">Auto Benefits</span>
      <span class="section-cn">专属权益日 · 自动化</span>
    </div>

    <!-- 未登录提示 -->
    <div v-if="!member" class="auto-empty">登录会员后，为您自动推送专属权益</div>

    <!-- 自动券列表：沉默召回 / 生日 / 周年庆 -->
    <div v-else-if="coupons.length" class="auto-list">
      <div v-for="c in coupons" :key="c.id" class="auto-card" :class="'k-' + c.kind">
        <div class="auto-cover" :style="{ background: c.cover }">
          <span class="auto-kind">{{ c.kind_label }}</span>
          <span class="auto-title-cover">{{ c.title }}</span>
        </div>
        <div class="auto-body">
          <div class="auto-reason">{{ c.reason }}</div>
          <div class="auto-desc">{{ c.desc }}</div>
          <div class="auto-meta">
            <span class="auto-pref">偏好 · {{ c.pref }}</span>
            <span class="auto-validity">
              {{ c.kind === 'recall' ? '有效期至 ' + c.validity : '仅限 ' + c.validity }}
            </span>
          </div>
          <button class="auto-btn" :disabled="busy" @click="claim(c)">
            {{ busy ? '领取中…' : '立即领取' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 空态 -->
    <div v-else class="auto-empty">暂无专属自动化权益，常来逛逛会有惊喜~</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onActivated } from 'vue'
import { useRouter } from 'vue-router'
import { useMemberStore } from '@/stores/member'
import { showSuccessToast, showFailToast } from 'vant'
import { getAutoCoupons, claimAutoCoupon } from '@/api'

const props = defineProps({
  hideHeader: { type: Boolean, default: false },
})

const router = useRouter()
const memberStore = useMemberStore()
const member = computed(() => memberStore.member)

const coupons = ref([])
const busy = ref(false)

async function load() {
  const phone = member.value && member.value.phone
  if (!phone) {
    coupons.value = []
    return
  }
  try {
    const res = await getAutoCoupons(phone)
    if (res.ok) coupons.value = res.coupons || []
  } catch (e) {
    coupons.value = []
  }
}
onMounted(load)
onActivated(load)

async function claim(c) {
  const phone = member.value && member.value.phone
  if (!phone) {
    showFailToast('请先登录会员')
    router.push('/member')
    return
  }
  busy.value = true
  try {
    const res = await claimAutoCoupon(phone, c.id)
    if (res.ok) {
      // 领取后从自动列表移除（已落入券包）
      coupons.value = coupons.value.filter((x) => x.id !== c.id)
      showSuccessToast(res.message || '已存入您的券包')
    } else {
      showFailToast(res.error || '领取失败')
    }
  } catch (e) {
    showFailToast('网络错误')
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.auto-coupons { margin: 0 0 18px; }

.section-label { display: flex; flex-direction: column; margin: 22px 16px 14px; }
.section-en { font-family: 'Gayathri', var(--font-primary); font-size: 22px; font-weight: 900; letter-spacing: 1px; line-height: 1.2; color: rgba(255,255,255,0.92); text-transform: capitalize; -webkit-text-stroke: 0.5px rgba(255,255,255,0.3); }
.section-cn { font-size: var(--fs-headline); font-weight: 400; color: #FFFFFF; margin-top: 10px; text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.18); }

.auto-empty { margin: 0 16px; padding: 18px; text-align: center; font-size: 13px; color: rgba(255,255,255,0.55); background: rgba(255,255,255,0.05); border-radius: 14px; }

.auto-list { display: flex; flex-direction: column; gap: 14px; margin: 0 16px; }

.auto-card {
  border-radius: 18px; overflow: hidden;
  background-color: #2A2A2E;
  border: 3px solid #4A4A50;
  box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.08);
}

.auto-cover {
  position: relative; min-height: 64px;
  display: flex; flex-direction: column; justify-content: center; gap: 4px;
  padding: 12px 14px; box-sizing: border-box;
}
.auto-cover::before {
  content: ""; position: absolute; inset: 0; border-radius: inherit; pointer-events: none;
  box-shadow: inset 0 2px 3px rgba(255,255,255,0.28), inset 0 -3px 6px rgba(0,0,0,0.22);
}
.auto-kind {
  align-self: flex-start;
  font-size: 12px; font-weight: 700; color: #fff;
  background: rgba(0,0,0,0.30); border: 1px solid rgba(255,255,255,0.35);
  padding: 3px 10px; border-radius: 9px;
}
.auto-title-cover { font-size: 16px; font-weight: 800; color: #fff; line-height: 1.3; text-shadow: 0 1px 2px rgba(0,0,0,0.30); }

.auto-body { padding: 14px 16px 16px; }
.auto-reason { font-size: 13px; font-weight: 700; color: #FFB877; line-height: 1.5; }
.auto-desc { font-size: 13px; color: rgba(255,255,255,0.82); margin-top: 8px; line-height: 1.55; }
.auto-meta { display: flex; justify-content: space-between; gap: 8px; margin-top: 10px; font-size: 11px; color: rgba(255,255,255,0.6); }
.auto-pref { color: #FFC89B; }

.auto-btn {
  width: 100%; margin-top: 12px;
  padding: 11px 0; border-radius: 14px;
  border: 2px solid #A87C48; background-color: #C9956C; color: #fff;
  font-size: 15px; font-weight: 700; cursor: pointer;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.25);
  text-shadow: 0 1px 1px rgba(0,0,0,0.30);
}
.auto-btn:active { transform: scale(0.98); }
.auto-btn:disabled { opacity: 0.7; }
</style>
