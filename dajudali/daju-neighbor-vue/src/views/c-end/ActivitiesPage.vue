<template>
  <div class="act-page">
    <div class="act-cats">
      <button v-for="c in cats" :key="c.key" class="act-btn" :class="{ active: activeCat === c.key }" @click="activeCat = c.key">{{ c.label }}</button>
    </div>
    <div v-if="loading" class="loading-state">加载中...</div>
    <div class="act-list" v-else>
      <div v-for="(a, i) in decorated" :key="a.id" class="act-card" :style="{ '--ac-bg': a.bg, '--ac-bd': a.bd }" @click="$router.push(`/activities/${a.id}`)">
        <div class="act-img" :style="{background: a.grad}">
          <span class="act-badge">{{ statusOf(a).t }}</span>
          <div class="act-img-text">{{ a.title }}</div>
          <div class="act-img-date">{{ a.start_date }}<template v-if="a.end_date && a.end_date !== a.start_date"> ~ {{ a.end_date }}</template></div>
        </div>
        <div class="act-info">
          <div class="act-info-title">{{ a.title }}</div>
          <div class="act-info-meta">
            <span>📅 {{ a.start_date }}</span>
            <span>📍 {{ a.venue }}</span>
          </div>
        </div>
        <button class="act-reg-btn">立即报名</button>
      </div>
      <div v-if="!decorated.length" class="empty-state">暂无活动</div>
    </div>
    <div class="spacer"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import api from '@/api'

const activeCat = ref('ongoing')
const cats = [
  { key: 'ongoing', label: '进行中' },
  { key: 'upcoming', label: '即将开始' },
  { key: 'past', label: '往期回顾' },
]

// 本地兜底数据（后台异常时也能展示，满足演示需要）
const FALLBACK = [
  { id: 1, title: '夏日亲子嘉年华', desc: '带上宝贝来海江新天地玩！趣味游戏、DIY手工、亲子运动会，赢取精美礼品。商家联合提供专属折扣，当日消费满额抽奖。', venue: '中庭广场', start_date: '2026-08-07', end_date: '2026-08-16', gradient: 'linear-gradient(135deg, #00704A, #00A85A)', status: 'open' },
  { id: 2, title: '美食节·川味专场', desc: '麻辣鲜香，一口入魂。朱光玉火锅、成都你六姐等川味品牌联合推出限定套餐，到店即送招牌小食。', venue: 'B1美食广场', start_date: '2026-08-18', end_date: '2026-08-22', gradient: 'linear-gradient(135deg, #C41E3A, #EF5350)', status: 'open' },
  { id: 7, title: '周末瑜伽体验', desc: '专业导师带你放松身心，零基础也可参与。名额有限，先到先得。', venue: '5F 活动空间', start_date: '2026-08-23', end_date: '2026-08-23', gradient: 'linear-gradient(135deg, #6A5B8C, #9B8BC0)', status: 'open' },
  { id: 3, title: '开学季文具特卖', desc: '开学焕新，文具图书低至5折，满199减50。', venue: '1F 中庭', start_date: '2026-09-01', end_date: '2026-09-03', gradient: 'linear-gradient(135deg, #E85D04, #FFB347)', status: 'upcoming' },
]

// 多彩卡片调色板（与首页同款风格：bg 实色底 + bd 深边框色；grad 为顶部图头，取同色系低饱和渐变，hi 为同色高光）
const PALETTE = [
  { bg: '#C4923A', bd: '#9A7425', hi: '#DDB873', grad: 'linear-gradient(135deg, #DDB873, #9A7425)' }, // 金 - 亲子
  { bg: '#9B4A3E', bd: '#6E332A', hi: '#BE7468', grad: 'linear-gradient(135deg, #BE7468, #6E332A)' }, // 深红棕 - 美食
  { bg: '#8B8B90', bd: '#6A6A6E', hi: '#A9A9AE', grad: 'linear-gradient(135deg, #A9A9AE, #6A6A6E)' }, // 灰紫 - 体验
  { bg: '#C9956C', bd: '#A87C48', hi: '#E0B288', grad: 'linear-gradient(135deg, #E0B288, #A87C48)' }, // 浅橙棕 - 特卖
  { bg: '#6B6E64', bd: '#4E5049', hi: '#8C8F82', grad: 'linear-gradient(135deg, #8C8F82, #4E5049)' }, // 深灰绿 - 公益
  { bg: '#D4A59A', bd: '#A67D72', hi: '#E5C2B9', grad: 'linear-gradient(135deg, #E5C2B9, #A67D72)' }, // 浅粉棕 - 节日
]

const acts = ref([])
const loading = ref(true)

async function loadActs() {
  loading.value = true
  try {
    const res = await api.get('/api/activities', { params: { cat: activeCat.value } })
    if (res && res.data && res.data.length) {
      acts.value = res.data
    } else {
      acts.value = FALLBACK
    }
  } catch(e) {
    console.error(e)
    acts.value = FALLBACK
  }
  loading.value = false
}

onMounted(loadActs)

watch(activeCat, () => { loadActs() })

// 为每条活动补齐主题色：图头渐变统一用调色板的同色系低饱和渐变（与卡片底色协调，不再用后台高饱和 gradient）
const decorated = computed(() => {
  return acts.value.map((a, i) => {
    const p = PALETTE[i % PALETTE.length]
    return {
      ...a,
      grad: p.grad,
      bg: a.bg || p.bg,
      bd: a.bd || p.bd,
      hi: p.hi,
    }
  })
})

function statusOf(a) {
  if (a.status === 'upcoming') return { t: '即将开始', c: '#FFB347' }
  if (a.status === 'closed' || a.status === 'past') return { t: '已结束', c: '#888' }
  return { t: '报名中', c: a.accent || '#00A85A' }
}
</script>

<style scoped>
.act-page { padding: 8px 12px; min-height: 100vh; background: #1A1A1A; }
.loading-state, .empty-state { text-align: center; padding: 40px 20px; color: #BBBBBB; font-size: 14px; }

.act-cats { display: flex; gap: 8px; margin-bottom: 14px; }
.act-btn {
  flex: 1; padding: 10px; border: 3px solid #4E5049; border-radius: 12px;
  font-size: 14px; font-weight: 600; cursor: pointer; font-family: inherit;
  background: #6B6E64; color: #fff;
  transition: all 0.15s;
}
.act-btn.active { background: #8B8B90; border-color: #6A6A6E; box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20); }

.act-list { display: flex; flex-direction: column; gap: 14px; }
.act-card {
  background-color: var(--ac-bg, #C4923A);
  border: 3px solid var(--ac-bd, #9A7425);
  border-radius: 18px; overflow: hidden; box-sizing: border-box;
  box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20);
  cursor: pointer; transition: transform 0.15s, opacity 0.15s;
}
.act-card:active { opacity: 0.85; transform: scale(0.985); }
.act-img { height: 120px; display: flex; flex-direction: column; justify-content: flex-end; padding: 20px 18px; position: relative; }
.act-img:after {
  content: ''; position: absolute; top: 10px; right: 16px;
  width: 40px; height: 40px;
  background: radial-gradient(circle, rgba(0,0,0,0.25) 1px, transparent 1px);
  background-size: 10px 10px;
}
.act-badge {
  position: absolute; top: 12px; left: 14px;
  padding: 3px 10px; border-radius: 999px;
  font-size: 11px; font-weight: 700; color: #fff;
  background: var(--ac-bd, #9A7425);
  box-shadow: 0 2px 6px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.25);
}
.act-img-text { font-size: 18px; font-weight: 700; color: #fff; text-shadow: 0 1px 4px rgba(0,0,0,0.4); }
.act-img-date { font-size: 13px; color: rgba(255,255,255,0.85); margin-top: 4px; text-shadow: 0 1px 4px rgba(0,0,0,0.4); }
.act-info { padding: 14px 18px; }
.act-info-title { font-size: 16px; font-weight: 600; color: #fff; text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.25); }
.act-info-meta { display: flex; gap: 16px; margin-top: 6px; font-size: 13px; color: #fff; text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.25); }
/* 立即报名按钮：内凹（inset 阴影）风格，与首页 dd-btn / biz-hero-btn 一致 */
.act-reg-btn {
  margin: 0 18px 16px; padding: 10px 0; width: calc(100% - 36px);
  border: 3px solid var(--ac-bd, #9A7425);
  border-radius: 20px;
  background-color: var(--ac-bd, #9A7425); color: #fff;
  font-size: 14px; font-weight: 600; cursor: pointer; font-family: inherit;
  box-shadow: inset 3px 3px 7px rgba(0, 0, 0, 0.45), inset -2px -2px 5px rgba(196, 146, 58, 0.45);
  transition: transform 0.15s;
}
.act-reg-btn:active { transform: scale(0.99); }
.spacer { height: 24px; }
</style>
