<template>
  <div class="act-page">
    <div class="act-cats">
      <button v-for="c in cats" :key="c.key" class="act-btn" :class="{ active: activeCat === c.key }" @click="activeCat = c.key">{{ c.label }}</button>
    </div>
    <div v-if="loading" class="loading-state">加载中...</div>
    <div class="act-list" v-else>
      <div v-for="a in filtered" :key="a.id" class="act-card" @click="$router.push(`/activities/${a.id}`)">
        <div class="act-img" :style="{background: a.gradient || '#333'}">
          <div class="act-img-text">{{ a.title }}</div>
          <div class="act-img-date">{{ a.start_date }}</div>
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
      <div v-if="!filtered.length" class="empty-state">暂无活动</div>
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
  { id: 2, title: '美食节·川味专场', desc: '麻辣鲜香，一口入魂。蜀大侠、海底捞等川味品牌联合推出限定套餐，到店即送招牌小食。', venue: 'B1美食广场', start_date: '2026-08-18', end_date: '2026-08-22', gradient: 'linear-gradient(135deg, #C41E3A, #EF5350)', status: 'open' },
  { id: 7, title: '周末瑜伽体验', desc: '专业导师带你放松身心，零基础也可参与。名额有限，先到先得。', venue: '5F 活动空间', start_date: '2026-08-23', end_date: '2026-08-23', gradient: 'linear-gradient(135deg, #6A5B8C, #9B8BC0)', status: 'open' },
  { id: 3, title: '开学季文具特卖', desc: '开学焕新，文具图书低至5折，满199减50。', venue: '1F 中庭', start_date: '2026-09-01', end_date: '2026-09-03', gradient: 'linear-gradient(135deg, #E85D04, #FFB347)', status: 'upcoming' },
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

const filtered = computed(() => acts.value)

watch(activeCat, () => { loadActs() })
</script>

<style scoped>
.act-page { padding: 8px 12px; min-height: 100vh; background: #1A1A1A; }
.loading-state, .empty-state { text-align: center; padding: 40px 20px; color: #BBBBBB; font-size: 14px; }

.act-cats { display: flex; gap: 8px; margin-bottom: 14px; }
.act-btn {
  flex: 1; padding: 10px; border: 1px solid #333; border-radius: 12px;
  font-size: 14px; font-weight: 600; cursor: pointer; font-family: inherit;
  background: #222222; color: #999;
  transition: all 0.15s;
}
.act-btn.active { background: #1A1A1A; color: #fff; border-color: #999999; }

.act-list { display: flex; flex-direction: column; gap: 14px; }
.act-card {
  background: #222222; border-radius: 12px; overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  cursor: pointer; transition: opacity 0.15s;
}
.act-card:active { opacity: 0.8; }
.act-img { height: 120px; display: flex; flex-direction: column; justify-content: flex-end; padding: 20px 18px; position: relative; }
.act-img:after {
  content: ''; position: absolute; top: 10px; right: 16px;
  width: 40px; height: 40px;
  background: radial-gradient(circle, #1A1A1A 1px, transparent 1px);
  background-size: 10px 10px;
}
.act-img-text { font-size: 18px; font-weight: 700; color: #fff; }
.act-img-date { font-size: 13px; color: rgba(255,255,255,0.75); margin-top: 4px; }
.act-info { padding: 14px 18px; }
.act-info-title { font-size: 16px; font-weight: 600; color: #F0F0F0; }
.act-info-meta { display: flex; gap: 16px; margin-top: 6px; font-size: 13px; color: #999; }
.act-reg-btn {
  margin: 0 18px 16px; padding: 10px 0; width: calc(100% - 36px);
  border: none; border-radius: 12px; background: #1A1A1A; color: #fff;
  font-size: 14px; font-weight: 600; cursor: pointer; font-family: inherit;
  transition: opacity 0.15s;
}
.act-reg-btn:active { opacity: 0.8; }
.spacer { height: 24px; }
</style>
