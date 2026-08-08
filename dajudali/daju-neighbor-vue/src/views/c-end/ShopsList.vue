<template>
  <div class="shops-list">
    <div class="sl-search">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#777" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input type="text" placeholder="搜索商铺、品牌" v-model="searchText" />
    </div>

    <div class="sl-cats">
      <button v-for="c in cats" :key="c" class="sl-cat-btn" :class="{ active: activeCat === c }" @click="activeCat = c">{{ c }}</button>
    </div>

    <div v-if="loading" class="loading-state">加载中...</div>

    <div class="sl-list" v-else>
      <div v-for="s in filteredShops" :key="s.id" class="sl-card" @click="$router.push(`/shops/${s.id}`)">
        <div class="slc-avatar" :style="{background: s.color}">{{ s.name[0] }}</div>
        <div class="slc-info">
          <div class="slc-name">{{ s.name }}</div>
          <div class="slc-meta">{{ s.floor }}F · {{ s.category }} {{ s.tags ? '· ' + (Array.isArray(s.tags) ? s.tags.join(' · ') : s.tags) : '' }}</div>
        </div>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#555" stroke-width="2" stroke-linecap="round"><polyline points="9 18 15 12 9 6"/></svg>
      </div>
      <div v-if="!filteredShops.length" class="empty-state">暂无商铺</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getShops } from '@/api'
import localShops from '@/data/shops.js'

const searchText = ref('')
const activeCat = ref('全部')
const cats = ['全部', '餐饮', '零售', '亲子', '娱乐', '生活服务']
const loading = ref(true)
const shops = ref([])

onMounted(async () => {
  try {
    const resp = await getShops()
    if (resp.ok && resp.data && resp.data.length) {
      shops.value = resp.data.map(s => ({
        ...s,
        tags: Array.isArray(s.tags) ? s.tags : (s.tags || '').split(',').filter(Boolean),
        features: Array.isArray(s.features) ? s.features : (s.features || '').split(',').filter(Boolean),
      }))
    } else {
      shops.value = localShops
    }
  } catch {
    shops.value = localShops
  } finally {
    loading.value = false
  }
})

const filteredShops = computed(() => {
  let list = shops.value
  if (activeCat.value !== '全部') list = list.filter(s => s.category === activeCat.value)
  if (searchText.value) list = list.filter(s => s.name.includes(searchText.value))
  return list
})
</script>

<style scoped>
.shops-list { padding: 8px 12px; min-height: 100vh; background: #1A1A1A; }

.loading-state, .empty-state {
  text-align: center; padding: 40px 20px; color: #666; font-size: 14px;
}

.sl-search {
  display: flex; align-items: center; gap: 10px; padding: 10px 16px;
  background: #2A2A2A; border: 1px solid #444; border-radius: 12px;
  margin-bottom: 12px; transition: border-color 0.15s;
}
.sl-search:focus-within { border-color: #999999; }
.sl-search input { flex: 1; border: none; background: none; outline: none; font-size: 15px; color: #F0F0F0; font-family: inherit; }
.sl-search input::placeholder { color: #666; }

.sl-cats { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 8px; -webkit-overflow-scrolling: touch; }
.sl-cats::-webkit-scrollbar { display: none; }
.sl-cat-btn {
  flex-shrink: 0; padding: 7px 18px; border: 1px solid #333; border-radius: 12px;
  font-size: 13px; font-weight: 600; cursor: pointer; font-family: inherit;
  background: #222222; color: #999;
  transition: all 0.15s;
}
.sl-cat-btn.active { background: #1A1A1A; color: #fff; border-color: #999999; }

.sl-list { display: flex; flex-direction: column; gap: 0; }
.sl-card {
  background: #222222; padding: 14px 16px;
  display: flex; align-items: center; gap: 14px;
  cursor: pointer; transition: background 0.15s;
  border-bottom: 0.5px solid #2E2E2E;
}
.sl-card:first-child { border-radius: 12px 12px 0 0; }
.sl-card:last-child { border-radius: 0 0 12px 12px; border-bottom: none; }
.sl-card:active { background: #2A2A2A; }
.slc-avatar { width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 20px; font-weight: 700; color: #fff; flex-shrink: 0; }
.slc-info { flex: 1; }
.slc-name { font-size: 16px; font-weight: 600; color: #F0F0F0; }
.slc-meta { font-size: 12px; color: #999; margin-top: 4px; }
</style>
