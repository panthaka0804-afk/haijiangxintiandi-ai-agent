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
      <div v-for="(g, i) in myGroups" :key="g.id" class="gb-my-card" :class="'gb-c-' + (i % 5)">
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
      <div v-for="(g, i) in groups" :key="g.id" class="gb-card" :class="'gb-c-' + (i % 5)">
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
/* 多彩卡片：实色渐变底 + 3px 深边框 + 内高光 + 白字 */
.gb-my-card, .gb-card {
  border: 3px solid transparent; border-radius: 16px; padding: 14px; margin-bottom: 12px;
  box-shadow: 0 6px 16px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.22);
}
.gb-my-card { display: flex; align-items: center; justify-content: space-between; }
.gb-card { margin-left: 16px; margin-right: 16px; }
/* 5 色循环（与首页多彩卡一致：金黄/浅橙棕/深红棕/灰紫/深灰绿） */
.gb-c-0 { background: linear-gradient(135deg, #C4923A, #A8741C); border-color: #8A5E12; }
.gb-c-1 { background: linear-gradient(135deg, #C9956C, #B07E4E); border-color: #A87C48; }
.gb-c-2 { background: linear-gradient(135deg, #9B4A3E, #7E3328); border-color: #5C241D; }
.gb-c-3 { background: linear-gradient(135deg, #8B8B90, #6F6F76); border-color: #54545A; }
.gb-c-4 { background: linear-gradient(135deg, #6B6E64, #505247); border-color: #3C3E36; }

.gb-my-shop { font-size: 13px; font-weight: 700; color: #fff; text-shadow: 0 1px 1px rgba(0,0,0,.35); }
.gb-my-title { font-size: 12px; color: rgba(255,255,255,0.82); margin-top: 2px; }
.gb-my-status { font-size: 12px; font-weight: 700; padding: 3px 10px; border-radius: 20px; background: rgba(0,0,0,0.25); color: #fff; text-shadow: 0 1px 1px rgba(0,0,0,.3); }
.gb-my-status.open { background: rgba(255,255,255,0.18); color: #fff; }

.gb-card-top { display: flex; align-items: center; justify-content: space-between; }
.gb-shop { font-size: 13px; font-weight: 700; color: #fff; text-shadow: 0 1px 1px rgba(0,0,0,.35); }
.gb-need { font-size: 11px; color: #fff; background: rgba(0,0,0,0.22); padding: 2px 8px; border-radius: 10px; }
.gb-title { font-size: 15px; font-weight: 700; margin: 8px 0 12px; color: #fff; text-shadow: 0 1px 1px rgba(0,0,0,.35); }
.gb-coupon { display: flex; align-items: baseline; gap: 8px; background: rgba(0,0,0,0.22); border: 1px solid rgba(255,255,255,0.30); border-radius: 10px; padding: 10px 12px; margin-bottom: 14px; }
.gb-coupon-amt { font-size: 22px; font-weight: 800; color: #fff; text-shadow: 0 1px 1px rgba(0,0,0,.4); }
.gb-coupon-label { font-size: 13px; color: rgba(255,255,255,0.9); }
.gb-progress { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.gb-progress-bar { flex: 1; height: 8px; background: rgba(0,0,0,0.30); border-radius: 4px; overflow: hidden; }
.gb-progress-fill { height: 100%; background: linear-gradient(90deg, rgba(0,0,0,0.35), rgba(255,255,255,0.55)); border-radius: 4px; transition: width 0.4s; }
.gb-progress-txt { font-size: 12px; color: rgba(255,255,255,0.85); white-space: nowrap; text-shadow: 0 1px 1px rgba(0,0,0,.3); }
.gb-btn { width: 100%; height: 44px; border: 1px solid #8A5E12; border-radius: 12px; background: #9A7425; color: #fff; font-size: 14px; font-weight: 700; cursor: pointer; box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(196,146,58,.45); }
.gb-btn:active { box-shadow: inset 5px 5px 10px rgba(0,0,0,.55), inset -2px -2px 5px rgba(196,146,58,.35); }
.gb-btn.joined { background: rgba(0,0,0,0.30); border-color: rgba(255,255,255,0.30); color: rgba(255,255,255,0.8); box-shadow: inset 3px 3px 7px rgba(0,0,0,.5), inset -2px -2px 5px rgba(255,255,255,.08); }
/* 按钮跟随卡片色系（可点态） */
.gb-c-0 .gb-btn { background: #8A5E12; border-color: #6E4A0E; box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(196,146,58,.45); }
.gb-c-1 .gb-btn { background: #A87C48; border-color: #87613A; box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(201,149,108,.45); }
.gb-c-2 .gb-btn { background: #5C241D; border-color: #451B16; box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(155,74,62,.45); }
.gb-c-3 .gb-btn { background: #54545A; border-color: #3F3F44; box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(139,139,144,.45); }
.gb-c-4 .gb-btn { background: #3C3E36; border-color: #2C2E28; box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(107,110,100,.45); }
/* 按钮跟随卡片色系（已参团态 · 同色系压暗） */
.gb-c-0 .gb-btn.joined { background: #6E4A0E; border-color: rgba(255,255,255,.30); }
.gb-c-1 .gb-btn.joined { background: #87613A; border-color: rgba(255,255,255,.30); }
.gb-c-2 .gb-btn.joined { background: #451B16; border-color: rgba(255,255,255,.30); }
.gb-c-3 .gb-btn.joined { background: #3F3F44; border-color: rgba(255,255,255,.30); }
.gb-c-4 .gb-btn.joined { background: #2C2E28; border-color: rgba(255,255,255,.30); }
.gb-expire { font-size: 11px; color: rgba(255,255,255,0.4); margin-top: 8px; text-align: center; }
.gb-tip { font-size: 12px; color: rgba(255,255,255,0.45); margin: 16px; line-height: 1.6; text-align: center; }
.gb-loading, .gb-empty { text-align: center; color: rgba(255,255,255,0.5); padding: 30px 0; font-size: 14px; }
</style>
