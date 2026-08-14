<template>
  <div class="member-exclusive">
    <div class="section-label" v-if="!hideHeader">
      <span class="section-en">Member Exclusive</span>
      <span class="section-cn">会员专属</span>
    </div>

    <div class="excl-list">
      <div v-for="it in items" :key="it.id" class="excl-card" :class="{ locked: !it.eligible }">
        <div class="excl-cover" :style="{ background: it.cover }">
          <span class="excl-type">{{ it.type }}</span>
          <span v-if="!it.eligible" class="excl-lock">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
            需{{ it.level_required }}
          </span>
        </div>
        <div class="excl-body">
          <div class="excl-title">{{ it.title }}</div>
          <div class="excl-shop">{{ it.shop }}</div>
          <div class="excl-summary">{{ it.summary }}</div>
          <div class="excl-meta">
            <span class="excl-loc">{{ it.location }}</span>
            <span class="excl-deadline">截止 {{ it.deadline }}</span>
          </div>
          <div v-if="expanded[it.id]" class="excl-detail">{{ it.detail }}</div>
          <div class="excl-detail-toggle" @click="toggleDetail(it.id)">
            {{ expanded[it.id] ? '收起' : '查看详情' }}
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" :style="{ transform: expanded[it.id] ? 'rotate(180deg)' : 'none' }"><polyline points="6 9 12 15 18 9"/></svg>
          </div>
          <div class="excl-quota">
            <div class="excl-quota-track"><div class="excl-quota-fill" :style="{ width: quotaPct(it) + '%' }"></div></div>
            <span class="excl-quota-text">剩 {{ it.quota_left }}/{{ it.quota_total }}</span>
          </div>
          <button class="excl-btn" :class="{ claimed: it.claimed, off: it.quota_left <= 0 }" :disabled="it.claimed || it.quota_left <= 0" @click="claim(it)">
            {{ it.claimed ? '已报名' : (it.quota_left > 0 ? '立即报名' : '已抢光') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onActivated } from 'vue'
import { useRouter } from 'vue-router'
import { useMemberStore } from '@/stores/member'
import { showSuccessToast, showFailToast } from 'vant'
import { getMemberExclusives, claimExclusive } from '@/api'

const props = defineProps({
  // 在独立页面内使用时隐藏版块标题（标题由页面顶部导航栏承担）
  hideHeader: { type: Boolean, default: false },
})

const router = useRouter()
const memberStore = useMemberStore()
const member = computed(() => memberStore.member)

const items = ref([])
const expanded = ref({})

async function load() {
  const phone = member.value && member.value.phone
  try {
    const res = await getMemberExclusives(phone)
    if (res.ok) items.value = res.items || []
  } catch (e) {
    items.value = []
  }
}
onMounted(load)
onActivated(load)

function quotaPct(it) {
  const total = it.quota_total || 1
  return Math.max(0, Math.min(100, Math.round((it.quota_left / total) * 100)))
}

function toggleDetail(id) {
  expanded.value[id] = !expanded.value[id]
}

async function claim(it) {
  const phone = member.value && member.value.phone
  if (!phone) {
    showFailToast('请先登录会员')
    router.push('/member')
    return
  }
  if (!it.eligible) {
    showFailToast(`需「${it.level_required}」及以上会员参与`)
    return
  }
  try {
    const res = await claimExclusive(phone, it.id)
    if (res.ok) {
      it.claimed = true
      if (it.quota_left > 0) it.quota_left -= 1
      showSuccessToast('报名成功！详情见会员消息')
    } else {
      showFailToast(res.error || '报名失败')
    }
  } catch (e) {
    showFailToast('网络错误')
  }
}
</script>

<style scoped>
.member-exclusive { margin: 0 0 18px; }

/* ── 版块标题（与首页/会员权益统一） ── */
.section-label { display: flex; flex-direction: column; margin: 22px 16px 14px; }
.section-en { font-family: 'Gayathri', var(--font-primary); font-size: 22px; font-weight: 900; letter-spacing: 1px; line-height: 1.2; color: rgba(255,255,255,0.92); text-transform: capitalize; -webkit-text-stroke: 0.5px rgba(255,255,255,0.3); }
.section-cn { font-size: var(--fs-headline); font-weight: 400; color: #FFFFFF; margin-top: 10px; text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.18); }

.excl-list { display: flex; flex-direction: column; gap: 14px; margin: 0 16px; }

.excl-card {
  border-radius: 18px; overflow: hidden;
  background-color: #2A2A2E;
  border: 3px solid #4A4A50;
  box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.08);
}
.excl-card.locked { opacity: 0.92; }

/* 封面：渐变实色 + 顶部高光 + 内描边压印 */
.excl-cover {
  position: relative; height: 86px;
  display: flex; align-items: flex-start; justify-content: space-between;
  padding: 12px 14px; box-sizing: border-box;
}
.excl-cover::before {
  content: ""; position: absolute; inset: 0; border-radius: inherit; pointer-events: none;
  box-shadow: inset 0 2px 3px rgba(255,255,255,0.28), inset 0 -3px 6px rgba(0,0,0,0.22);
}
.excl-type {
  font-size: 13px; font-weight: 700; color: #fff;
  background: rgba(0,0,0,0.28); border: 1px solid rgba(255,255,255,0.35);
  padding: 4px 12px; border-radius: 10px;
  text-shadow: 0 1px 1px rgba(0,0,0,0.30);
}
.excl-lock {
  display: flex; align-items: center; gap: 4px;
  font-size: 12px; font-weight: 700; color: #fff;
  background: rgba(0,0,0,0.40); border: 1px solid rgba(255,255,255,0.30);
  padding: 4px 10px; border-radius: 10px;
}

.excl-body { padding: 14px 16px 16px; }
.excl-title { font-size: 16px; font-weight: 700; color: #fff; line-height: 1.4; text-shadow: 0 1px 2px rgba(0,0,0,0.35); }
.excl-shop { font-size: 12px; color: #FFB877; margin-top: 4px; font-weight: 600; }
.excl-summary { font-size: 13px; color: rgba(255,255,255,0.82); margin-top: 8px; line-height: 1.5; }
.excl-meta { display: flex; flex-direction: column; gap: 2px; margin-top: 8px; font-size: 11px; color: rgba(255,255,255,0.65); }
.excl-detail { font-size: 12px; color: rgba(255,255,255,0.78); margin-top: 8px; line-height: 1.6; background: rgba(255,255,255,0.06); border-radius: 10px; padding: 10px 12px; }
.excl-detail-toggle {
  display: inline-flex; align-items: center; gap: 3px;
  margin-top: 8px; font-size: 12px; color: #FFB877; cursor: pointer; font-weight: 600;
}

.excl-quota { display: flex; align-items: center; gap: 10px; margin-top: 12px; }
.excl-quota-track { flex: 1; height: 6px; background: rgba(255,255,255,0.14); border-radius: 3px; overflow: hidden; }
.excl-quota-fill { height: 100%; background: linear-gradient(90deg, #C4923A, #FFB877); border-radius: 3px; transition: width 0.4s; }
.excl-quota-text { font-size: 11px; color: rgba(255,255,255,0.72); white-space: nowrap; }

.excl-btn {
  width: 100%; margin-top: 12px;
  padding: 11px 0; border-radius: 14px;
  border: 2px solid #A87C48; background-color: #C9956C; color: #fff;
  font-size: 15px; font-weight: 700; cursor: pointer;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.25);
  text-shadow: 0 1px 1px rgba(0,0,0,0.30);
}
.excl-btn:active { transform: scale(0.98); }
.excl-btn.claimed { background: rgba(255,255,255,0.10); border-color: rgba(255,255,255,0.25); color: rgba(255,255,255,0.85); cursor: default; }
.excl-btn.off { background: rgba(255,255,255,0.08); border-color: rgba(255,255,255,0.20); color: rgba(255,255,255,0.6); cursor: default; }
</style>
