<template>
  <div class="gb-root">
    <!-- 头部 -->
    <header class="gb-hdr">
      <button class="gb-back" @click="$router.back()">‹</button>
      <h1>拼团组队</h1>
      <span class="gb-hdr-sub">邻里拼团 · 满员即发券</span>
    </header>

    <!-- 我的拼团 -->
    <section v-if="myGroups.length" class="gb-my">
      <div class="gb-sec-title">我的拼团</div>
      <div v-for="g in myGroups" :key="g.id" class="gb-my-card">
        <div class="gb-my-left">
          <div class="gb-my-shop">{{ g.shop_name }}</div>
          <div class="gb-my-title">{{ g.title }}</div>
        </div>
        <span class="gb-my-status" :class="g.status">{{ g.status === 'full' ? '已成团' : '拼团中' }}</span>
      </div>
    </section>

    <!-- 活动列表 -->
    <section class="gb-list">
      <div class="gb-sec-title">进行中的拼团</div>
      <div v-if="loading" class="gb-loading">加载中…</div>
      <div v-else-if="!groups.length" class="gb-empty">暂无进行中的拼团，敬请期待~</div>
      <div v-for="g in groups" :key="g.id" class="gb-card">
        <div class="gb-card-top">
          <span class="gb-shop">{{ g.shop_name }}</span>
          <span class="gb-need">需 {{ g.need_count }} 人成团</span>
        </div>
        <div class="gb-title">{{ g.title }}</div>
        <div class="gb-coupon">
          <span class="gb-coupon-amt">¥{{ g.coupon_amount }}</span>
          <span class="gb-coupon-label">{{ g.coupon_label }}</span>
        </div>
        <!-- 进度 -->
        <div class="gb-progress">
          <div class="gb-progress-bar">
            <div class="gb-progress-fill" :style="{ width: progressPct(g) + '%' }"></div>
          </div>
          <span class="gb-progress-txt">已拼 {{ g.joined_count }}/{{ g.need_count }} 人</span>
        </div>
        <button class="gb-btn" :class="{ joined: g.joined_by_me }" :disabled="g.joined_by_me" @click="join(g)">
          {{ g.joined_by_me ? '已参团' : (g.remain > 0 ? '立即参团（还差 ' + g.remain + ' 人）' : '已成团') }}
        </button>
        <div v-if="g.expire_at" class="gb-expire">有效期至 {{ g.expire_at }}</div>
      </div>
    </section>

    <div class="gb-tip">拼团满员后，专属优惠券将自动发放到「我的优惠券」，到店出示核销即可。</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useMemberStore } from '@/stores/member'
import { showToast } from 'vant'

const memberStore = useMemberStore()
const phone = ref('')
const groups = ref([])
const myGroups = ref([])
const loading = ref(true)

onMounted(async () => {
  const m = memberStore.member
  if (m && m.phone) phone.value = m.phone
  await loadList()
  if (phone.value) await loadMy()
})

function progressPct(g) {
  if (!g.need_count) return 0
  return Math.min(100, Math.round((g.joined_count / g.need_count) * 100))
}

async function loadList() {
  try {
    const res = await fetch('/api/group-buy/list').then(r => r.json())
    if (res.ok) groups.value = res.data || []
  } catch (e) {}
  loading.value = false
}

async function loadMy() {
  try {
    const res = await fetch('/api/group-buy/my?phone=' + phone.value).then(r => r.json())
    if (res.ok) myGroups.value = res.data || []
  } catch (e) {}
}

async function join(g) {
  if (!phone.value) {
    showToast('请先在会员中心绑定手机号')
    return
  }
  if (g.joined_by_me) return
  try {
    const res = await fetch('/api/group-buy/join', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ group_id: g.id, phone: phone.value, name: '' })
    }).then(r => r.json())
    if (res.ok) {
      if (res.data.full) {
        showToast('拼团成功！专属券已发放到「我的优惠券」')
      } else {
        showToast(res.data.message || '参团成功')
      }
      await loadList()
      await loadMy()
    } else {
      showToast(res.error || '参团失败')
    }
  } catch (e) {
    showToast('网络异常')
  }
}
</script>

<style scoped>
.gb-root { min-height: 100vh; background: #000; color: #fff; padding-bottom: 30px; font-family: 'PingFang SC', var(--font-primary); }
.gb-hdr { display: flex; align-items: center; gap: 12px; padding: 14px 16px; background: #0A0A0C; border-bottom: 1px solid rgba(255,255,255,0.08); position: sticky; top: 0; z-index: 10; }
.gb-back { width: 32px; height: 32px; border: none; background: rgba(255,255,255,0.08); color: #fff; font-size: 22px; border-radius: 50%; cursor: pointer; line-height: 1; }
.gb-hdr h1 { font-size: 18px; font-weight: 800; margin: 0; flex: 1; }
.gb-hdr-sub { font-size: 12px; color: rgba(255,255,255,0.5); }

.gb-sec-title { font-size: 14px; font-weight: 700; color: #fff; margin: 18px 16px 10px; letter-spacing: 0.5px; }
.gb-my { margin: 0 16px; }
.gb-my-card { display: flex; align-items: center; justify-content: space-between; background: #161618; border: 1px solid rgba(255,255,255,0.10); border-radius: 12px; padding: 12px 14px; margin-bottom: 8px; }
.gb-my-shop { font-size: 13px; font-weight: 700; color: #FF7B2C; }
.gb-my-title { font-size: 12px; color: rgba(255,255,255,0.6); margin-top: 2px; }
.gb-my-status { font-size: 12px; font-weight: 700; padding: 3px 10px; border-radius: 20px; }
.gb-my-status.full { background: rgba(255,123,44,0.18); color: #FF7B2C; }
.gb-my-status.open { background: rgba(255,255,255,0.10); color: rgba(255,255,255,0.7); }

.gb-card { margin: 0 16px 14px; background: #161618; border: 1px solid rgba(255,255,255,0.10); border-radius: 16px; padding: 16px; box-shadow: 0 4px 14px rgba(0,0,0,0.4); }
.gb-card-top { display: flex; align-items: center; justify-content: space-between; }
.gb-shop { font-size: 13px; font-weight: 700; color: #FF7B2C; }
.gb-need { font-size: 11px; color: rgba(255,255,255,0.5); background: rgba(255,255,255,0.06); padding: 2px 8px; border-radius: 10px; }
.gb-title { font-size: 15px; font-weight: 700; margin: 8px 0 12px; }
.gb-coupon { display: flex; align-items: baseline; gap: 8px; background: linear-gradient(135deg, rgba(232,93,4,0.20), rgba(255,123,44,0.10)); border: 1px dashed rgba(255,123,44,0.45); border-radius: 10px; padding: 10px 12px; margin-bottom: 14px; }
.gb-coupon-amt { font-size: 22px; font-weight: 800; color: #FF7B2C; }
.gb-coupon-label { font-size: 13px; color: rgba(255,255,255,0.8); }
.gb-progress { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.gb-progress-bar { flex: 1; height: 8px; background: rgba(255,255,255,0.10); border-radius: 4px; overflow: hidden; }
.gb-progress-fill { height: 100%; background: linear-gradient(90deg, #E85D04, #FF7B2C); border-radius: 4px; transition: width 0.4s; }
.gb-progress-txt { font-size: 12px; color: rgba(255,255,255,0.6); white-space: nowrap; }
.gb-btn { width: 100%; height: 44px; border: none; border-radius: 12px; background: linear-gradient(135deg, #E85D04, #FF7B2C); color: #fff; font-size: 14px; font-weight: 700; cursor: pointer; box-shadow: 0 4px 12px rgba(232,93,4,0.35); }
.gb-btn:active { transform: translateY(1px); }
.gb-btn.joined { background: rgba(255,255,255,0.12); color: rgba(255,255,255,0.6); box-shadow: none; }
.gb-expire { font-size: 11px; color: rgba(255,255,255,0.4); margin-top: 8px; text-align: center; }
.gb-tip { font-size: 12px; color: rgba(255,255,255,0.45); margin: 16px; line-height: 1.6; text-align: center; }
.gb-loading, .gb-empty { text-align: center; color: rgba(255,255,255,0.5); padding: 30px 0; font-size: 14px; }
</style>
