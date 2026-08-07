<template>
  <div class="act-page">
    <div class="act-cats">
      <button v-for="c in cats" :key="c.key" class="act-btn" :class="{ active: activeCat === c.key }" @click="activeCat = c.key">{{ c.label }}</button>
    </div>
    <div class="act-list">
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
    </div>
    <div class="spacer"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api'

const activeCat = ref('ongoing')
const cats = [
  { key: 'ongoing', label: '进行中' },
  { key: 'upcoming', label: '即将开始' },
  { key: 'past', label: '往期回顾' },
]

const acts = ref([])
const loading = ref(true)

async function loadActs() {
  loading.value = true
  try {
    const res = await api.get('/api/activities', { params: { cat: activeCat.value } })
    acts.value = res.data || []
  } catch(e) {
    console.error(e)
  }
  loading.value = false
}

onMounted(loadActs)

const filtered = computed(() => acts.value)

// 切换分类时重新加载
import { watch } from 'vue'
watch(activeCat, () => { loadActs() })
</script>

<style scoped>
.act-page { padding: 8px 12px; min-height: 100vh; background: #1A1A1A; }

.act-cats { display: flex; gap: 8px; margin-bottom: 14px; }
.act-btn {
  flex: 1; padding: 10px; border: 1px solid #333; border-radius: 12px;
  font-size: 14px; font-weight: 600; cursor: pointer; font-family: inherit;
  background: #222222; color: #999;
  transition: all 0.15s;
}
.act-btn.active { background: #FF7B2C; color: #fff; border-color: #FF7B2C; }

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
  background: radial-gradient(circle, rgba(255,255,255,0.2) 1px, transparent 1px);
  background-size: 10px 10px;
}
.act-img-text { font-size: 18px; font-weight: 700; color: #fff; }
.act-img-date { font-size: 13px; color: rgba(255,255,255,0.75); margin-top: 4px; }
.act-info { padding: 14px 18px; }
.act-info-title { font-size: 16px; font-weight: 600; color: #F0F0F0; }
.act-info-meta { display: flex; gap: 16px; margin-top: 6px; font-size: 13px; color: #999; }
.act-reg-btn {
  margin: 0 18px 16px; padding: 10px 0; width: calc(100% - 36px);
  border: none; border-radius: 12px; background: #FF7B2C; color: #fff;
  font-size: 14px; font-weight: 600; cursor: pointer; font-family: inherit;
  transition: opacity 0.15s;
}
.act-reg-btn:active { opacity: 0.8; }
.spacer { height: 24px; }
</style>
