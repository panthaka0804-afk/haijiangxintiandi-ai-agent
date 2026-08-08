<template>
  <div class="nav-page">
    <!-- 搜索栏 -->
    <div class="nav-search">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#777" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input v-model="searchQuery" placeholder="搜索商铺、设施、楼层" @input="onSearch" />
      <button v-if="searchQuery" class="search-clear" @click="searchQuery=''; searchResults=[]">✕</button>
    </div>
    <!-- 搜索结果 -->
    <div v-if="searchResults.length" class="search-drop">
      <div v-for="r in searchResults" :key="r.id" class="sd-item" @click="onSearchItem(r)">
        <span>{{ r.name }}</span>
        <span class="sd-floor">{{ r.zone }} · {{ r.floor }}F · {{ r.category }}</span>
      </div>
    </div>

    <!-- 区块分段控制器 -->
    <div class="seg-bar">
      <div class="seg-bg" :style="blockSegStyle"></div>
      <button v-for="b in blocks" :key="b" class="seg-btn" :class="{ active: activeBlock === b }" @click="onBlockChange(b)">{{ b }}</button>
    </div>
    <!-- 楼层分段控制器 -->
    <div class="seg-bar">
      <div class="seg-bg" :style="floorSegStyle"></div>
      <button v-for="f in floorsForBlock" :key="f" class="seg-btn" :class="{ active: activeFloor === f }" @click="activeFloor = f">{{ f }}F</button>
    </div>

    <!-- 地图区域 -->
    <div class="map-section" ref="mapRef">
      <div class="floor-label">{{ activeBlock }} · {{ activeFloor }}F</div>
      <div class="floor-map">
        <svg width="100%" height="100%" :viewBox="`0 0 ${layout.W} ${layout.H}`" class="floor-svg" preserveAspectRatio="xMidYMid meet">
          <!-- 建筑轮廓 -->
          <rect x="4" y="4" :width="layout.W - 8" :height="layout.H - 8" rx="14" fill="#232323" stroke="#3A3A3A" stroke-width="1.5" />
          <!-- 中庭通道（仅层数较多时显示） -->
          <rect v-if="layout.rows >= 5" :x="layout.W/2 - 6" y="14" width="12" :height="layout.H - 28" rx="6" fill="#1B1B1B" stroke="#333" stroke-width="1" />
          <!-- 商铺标记 -->
          <g v-for="s in layout.items" :key="s.id" @click="toggleShop(s.id)">
            <rect :x="s.x" :y="s.y" :width="s.w" :height="s.h" rx="7" :fill="highlightId === s.id ? s.color : '#2E2E2E'" :stroke="highlightId === s.id ? s.color : '#3D3D3D'" stroke-width="1.5" style="transition: all 0.25s; cursor: pointer;" />
            <text :x="s.x + s.w/2" :y="s.y + s.h/2 + 4" text-anchor="middle" :fill="highlightId === s.id ? '#fff' : '#BBB'" font-size="11" font-weight="600" font-family="inherit" style="transition: all 0.25s; pointer-events: none;">{{ s.name.slice(0,3) }}</text>
          </g>
          <!-- 入口标记 -->
          <g>
            <rect :x="18" :y="10" width="34" height="16" rx="4" fill="#555" />
            <text :x="35" :y="22" text-anchor="middle" fill="#fff" font-size="10" font-weight="600" font-family="inherit">入口</text>
          </g>
          <!-- 导航路线 -->
          <polyline v-if="routePath.length >= 2"
            :points="routePath.map(p => `${p.x},${p.y}`).join(' ')"
            fill="none" stroke="#FF7B2C" stroke-width="2.5" stroke-dasharray="8,4"
            stroke-linecap="round" stroke-linejoin="round"
          >
            <animate attributeName="stroke-dashoffset" from="24" to="0" dur="1s" repeatCount="indefinite" />
          </polyline>
          <circle v-if="routePath.length" :cx="routePath[0].x" :cy="routePath[0].y" r="6" fill="#FF7B2C" stroke="#fff" stroke-width="2" />
          <circle v-if="routePath.length" :cx="routePath[routePath.length-1].x" :cy="routePath[routePath.length-1].y" r="6" fill="#FF7B2C" stroke="#fff" stroke-width="2" />
        </svg>
      </div>
      <!-- 地图上的浮层提示 -->
      <div v-if="highlightShop" class="map-tooltip" @click="$router.push(`/shops/${highlightShop.id}`)">
        <div class="mt-icon" :style="{background: highlightShop.color}">{{ highlightShop.name[0] }}</div>
        <div class="mt-info">
          <div class="mt-name">{{ highlightShop.name }}</div>
          <div class="mt-meta">{{ highlightShop.zone }} · {{ highlightShop.floor }}F · {{ highlightShop.category }}</div>
        </div>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#999" stroke-width="2" stroke-linecap="round"><polyline points="9 18 15 12 9 6"/></svg>
      </div>

      <!-- 步行指引面板 -->
      <div v-if="showRoute && routeSteps.length" class="route-panel">
        <div class="rp-header">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FF7B2C" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          <span class="rp-title">{{ routeTarget ? '前往 ' + routeTarget.name : '步行指引' }}</span>
          <button class="rp-close" @click="showRoute=false;highlightId=null;routePath=[]">✕</button>
        </div>
        <div class="rp-steps">
          <div v-for="(step, si) in routeSteps" :key="si" class="rp-step">
            <div class="rps-dot" :class="{ start: si === 0, end: si === routeSteps.length - 1 }">{{ si === 0 ? '起' : si === routeSteps.length - 1 ? '终' : si }}</div>
            <div class="rps-text">{{ step }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部抽屉：楼层商铺列表 -->
    <div class="sheet" :class="{ open: sheetOpen }">
      <div class="sheet-handle" @click="sheetOpen = !sheetOpen">
        <div class="sheet-pill"></div>
      </div>
      <div class="sheet-header">
        <span class="sheet-title">{{ activeBlock }} · {{ activeFloor }}F 商铺</span>
        <span class="sheet-count">{{ floorShops.length }} 家</span>
      </div>
      <div class="sheet-list">
        <div v-for="s in floorShops" :key="s.id" class="sheet-item" @click="$router.push(`/shops/${s.id}`)">
          <div class="si-avatar" :style="{background: s.color}">{{ s.name[0] }}</div>
          <div class="si-body">
            <div class="si-name">{{ s.name }}</div>
            <div class="si-tags">{{ s.tags?.join(' · ') }} · {{ s.category }}</div>
          </div>
          <div class="si-extra">
            <span class="si-area">{{ s.zone + ' · ' + s.floor + 'F' }}</span>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#555" stroke-width="2" stroke-linecap="round"><polyline points="9 18 15 12 9 6"/></svg>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部工具栏 -->
    <div class="nav-actions">
      <button class="na-btn" :class="{ on: largeFont }" @click="largeFont = !largeFont">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="4 7 4 4 20 4 20 7"/><line x1="9" y1="20" x2="15" y2="20"/><line x1="12" y1="4" x2="12" y2="20"/></svg>
        <span>大字</span>
      </button>
      <button class="na-btn" @click="$router.push('/shops')">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
        <span>列表</span>
      </button>
      <button class="na-btn" @click="locateMe">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/></svg>
        <span>定位</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'

const searchQuery = ref('')
const searchResults = ref([])
const activeBlock = ref('')
const activeFloor = ref(1)
const sheetOpen = ref(true)
const largeFont = ref(false)
const highlightId = ref(null)
const showRoute = ref(false)
const routePath = ref([])
const routeSteps = ref([])
const routeTarget = ref(null)

import shopsData from '@/data/shops.js'
const route = useRoute()
const shops = shopsData

// 区块列表（按数据出现的顺序）
const blocks = computed(() => [...new Set(shops.map(s => s.zone))])
if (!activeBlock.value && blocks.value.length) activeBlock.value = blocks.value[0]

// 当前区块下的楼层列表（数值排序，跳过不存在的楼层）
const floorsForBlock = computed(() => {
  const fs = shops.filter(s => s.zone === activeBlock.value).map(s => Number(s.floor))
  return [...new Set(fs)].sort((a, b) => a - b)
})

// 切换区块时，重置到该区块首层
function onBlockChange(b) {
  activeBlock.value = b
  const fs = floorsForBlock.value
  if (fs.length && !fs.includes(Number(activeFloor.value))) activeFloor.value = fs[0]
}

// 当前区块+楼层的网格布局
const layout = computed(() => {
  const list = shops.filter(s => s.zone === activeBlock.value && String(s.floor) === String(activeFloor.value))
  const n = list.length
  const cols = n <= 4 ? 2 : n <= 12 ? 3 : 4
  const rows = Math.max(1, Math.ceil(n / cols))
  const W = 400
  const pad = 14
  const cellW = (W - pad * 2) / cols
  const cellH = 64
  const gap = 6
  const items = list.map((s, i) => {
    const c = i % cols
    const r = Math.floor(i / cols)
    const x = pad + c * cellW + gap / 2
    const y = pad + r * cellH + gap / 2
    const w = cellW - gap
    const h = cellH - gap
    return { ...s, x, y, w, h, cx: x + w / 2, cy: y + h / 2 }
  })
  const H = pad * 2 + rows * cellH
  return { items, W, H, cols, rows, n }
})

// 底部抽屉列表
const floorShops = computed(() => shops.filter(s => s.zone === activeBlock.value && String(s.floor) === String(activeFloor.value)))
const highlightShop = computed(() => {
  if (!highlightId.value) return null
  return shops.find(s => s.id === highlightId.value)
})

// 分段滑块样式
function segStyleFor(list, active) {
  const i = list.indexOf(active)
  const w = 100 / list.length
  return { left: `${i * w}%`, width: `${w}%` }
}
const blockSegStyle = computed(() => segStyleFor(blocks.value, activeBlock.value))
const floorSegStyle = computed(() => segStyleFor(floorsForBlock.value, Number(activeFloor.value)))

function onSearch() {
  if (!searchQuery.value) { searchResults.value = []; return }
  const q = searchQuery.value.toLowerCase()
  searchResults.value = shops.filter(s =>
    s.name.toLowerCase().includes(q) || s.category.includes(q) || s.tags?.some(t => t.toLowerCase().includes(q)) || String(s.floor).includes(q) || (s.zone || '').includes(q)
  )
}

function onSearchItem(shop) {
  activeBlock.value = shop.zone
  const fs = floorsForBlock.value
  if (!fs.includes(Number(shop.floor))) activeFloor.value = fs[0]
  else activeFloor.value = Number(shop.floor)
  highlightId.value = shop.id
  searchResults.value = []
  searchQuery.value = ''
  setTimeout(() => { if (highlightId.value === shop.id) highlightId.value = null }, 3000)
}

function locateMe() {
  if (blocks.value.length) activeBlock.value = blocks.value[0]
  if (floorsForBlock.value.length) activeFloor.value = floorsForBlock.value[0]
  sheetOpen.value = true
}

function toggleShop(id) {
  if (highlightId.value === id) {
    highlightId.value = null
    showRoute.value = false
    routePath.value = []
    routeSteps.value = []
    routeTarget.value = null
    return
  }
  highlightId.value = id
  generateRoute(id)
}

// 入口坐标（SVG 内）
const entrancePos = { x: 35, y: 18 }

function generateRoute(shopId) {
  const shop = shops.find(s => s.id === shopId)
  if (!shop) return
  routeTarget.value = shop
  const target = layout.value.items.find(s => s.id === shopId)
  if (!target) return

  const tx = target.cx
  const ty = target.cy
  const sx = entrancePos.x
  const sy = entrancePos.y

  const steps = []
  const path = []
  path.push({ x: sx, y: sy })
  steps.push(`${activeBlock} ${activeFloor}F 入口处，进入楼层`)

  // 先横向走到目标列，再纵向到目标
  path.push({ x: tx, y: sy })
  steps.push('沿主通道直行至目标商铺所在区域')
  path.push({ x: tx, y: ty })
  steps.push(`到达【${shop.name}】（${shop.zone} · ${shop.floor}F）`)

  routePath.value = path
  routeSteps.value = steps
  showRoute.value = true
}

// 从店铺详情页跳转过来的导航
onMounted(() => {
  const shopId = route.query.shop
  if (shopId) {
    const s = shops.find(s => s.id === shopId)
    if (s) {
      activeBlock.value = s.zone
      const fs = floorsForBlock.value
      activeFloor.value = fs.includes(Number(s.floor)) ? Number(s.floor) : fs[0]
      sheetOpen.value = true
      setTimeout(() => {
        highlightId.value = shopId
        generateRoute(shopId)
      }, 300)
    }
  }
})
</script>

<style scoped>
.nav-page { display: flex; flex-direction: column; height: 100vh; background: #1A1A1A; overflow: hidden; }

/* 搜索 */
.nav-search {
  display: flex; align-items: center; gap: 10px; padding: 6px 14px; margin: 8px 12px;
  background: #2A2A2A; border: 1px solid transparent; border-radius: 12px; transition: border-color 0.15s;
}
.nav-search:focus-within { border-color: #FF7B2C; background: #2A2A2A; }
.nav-search input { flex: 1; border: none; background: none; outline: none; font-size: 15px; color: #F0F0F0; font-family: inherit; }
.nav-search input::placeholder { color: #666; }
.search-clear { border: none; background: none; font-size: 16px; color: #666; cursor: pointer; padding: 0 4px; }

.search-drop {
  margin: 0 12px; background: #222222; border-radius: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.3);
  max-height: 200px; overflow-y: auto; position: relative; z-index: 10;
}
.sd-item { padding: 12px 16px; display: flex; justify-content: space-between; align-items: center; cursor: pointer; font-size: 14px; color: #F0F0F0; }
.sd-item:not(:last-child) { border-bottom: 0.5px solid #2E2E2E; }
.sd-floor { font-size: 12px; color: #777; }

/* 分段控制器 */
.seg-bar {
  display: flex; position: relative; margin: 4px 40px 6px;
  background: #2A2A2A; border-radius: 12px; padding: 3px;
}
.seg-bg {
  position: absolute; top: 3px; height: calc(100% - 6px); background: #333;
  border-radius: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.3); transition: all 0.25s;
}
.seg-btn {
  flex: 1; border: none; background: none; padding: 8px 0; font-size: 15px; font-weight: 600;
  color: #777; cursor: pointer; position: relative; z-index: 1; transition: color 0.25s; font-family: inherit; white-space: nowrap;
}
.seg-btn.active { color: #FF7B2C; }

/* 地图 */
.map-section { flex: 1; margin: 0 12px; position: relative; overflow: hidden; }
.floor-label { position: absolute; top: 12px; right: 12px; font-size: 20px; font-weight: 800; color: #444; z-index: 1; }
.floor-map { width: 100%; height: 100%; }
.floor-svg { width: 100%; height: 100%; }

.map-tooltip {
  position: absolute; bottom: 12px; left: 12px; right: 12px;
  background: #222222; border-radius: 14px; padding: 14px; display: flex; align-items: center; gap: 12px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.3); cursor: pointer; z-index: 2; animation: slideUp 0.2s ease-out;
}
@keyframes slideUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
.mt-icon { width: 40px; height: 40px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 16px; font-weight: 700; color: #fff; flex-shrink: 0; }
.mt-info { flex: 1; }
.mt-name { font-size: 15px; font-weight: 600; color: #F0F0F0; }
.mt-meta { font-size: 12px; color: #999; margin-top: 2px; }

/* 底部抽屉 */
.sheet {
  background: #222222; border-radius: 16px 16px 0 0; box-shadow: 0 -2px 12px rgba(0,0,0,0.3);
  transition: all 0.3s ease; display: flex; flex-direction: column;
  max-height: 80px; overflow: hidden;
}
.sheet.open { max-height: 320px; overflow-y: auto; }
.sheet-handle { padding: 8px 0; cursor: pointer; display: flex; justify-content: center; }
.sheet-pill { width: 36px; height: 4px; background: #444; border-radius: 2px; }
.sheet-header { display: flex; justify-content: space-between; padding: 0 16px 8px; }
.sheet-title { font-size: 16px; font-weight: 700; color: #F0F0F0; }
.sheet-count { font-size: 13px; color: #777; }
.sheet-list { padding: 0 16px 16px; display: flex; flex-direction: column; }
.sheet-item { display: flex; align-items: center; gap: 12px; padding: 12px 0; cursor: pointer; }
.sheet-item:not(:last-child) { border-bottom: 0.5px solid #2A2A2A; }
.si-avatar { width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 15px; font-weight: 700; color: #fff; flex-shrink: 0; }
.si-body { flex: 1; }
.si-name { font-size: 14px; font-weight: 600; color: #F0F0F0; }
.si-tags { font-size: 12px; color: #999; margin-top: 2px; }
.si-extra { display: flex; align-items: center; gap: 6px; }
.si-area { font-size: 12px; color: #555; }

/* 底部工具栏 */
.nav-actions {
  display: flex; gap: 10px; padding: 8px 16px 12px;
  border-top: 0.5px solid #2E2E2E; background: #222222;
}
.na-btn {
  flex: 1; display: flex; align-items: center; justify-content: center; gap: 4px;
  padding: 8px; border: none; border-radius: 12px; background: #2A2A2A; color: #999;
  font-size: 13px; font-weight: 500; cursor: pointer; font-family: inherit; transition: all 0.15s;
}
.na-btn.on { background: #1A1A1A; color: #FF7B2C; }
.na-btn:active { opacity: 0.7; }

/* 路线指引面板 */
.route-panel {
  position: absolute; bottom: 130px; left: 12px; right: 12px;
  background: #222222; border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.4);
  overflow: hidden; z-index: 20;
  max-height: 220px; overflow-y: auto;
}
.rp-header {
  display: flex; align-items: center; gap: 8px;
  padding: 12px 14px; border-bottom: 0.5px solid #333;
}
.rp-title { font-size: 14px; font-weight: 600; color: #F0F0F0; flex: 1; }
.rp-close {
  border: none; background: none; font-size: 18px; color: #666;
  cursor: pointer; padding: 4px;
}
.rp-steps { padding: 8px 14px 12px; }
.rp-step {
  display: flex; align-items: flex-start; gap: 12px;
  padding: 8px 0;
}
.rp-step:not(:last-child) { border-bottom: 1px dashed #333; }
.rps-dot {
  width: 26px; height: 26px; border-radius: 50%;
  background: #333; color: #999; font-size: 12px; font-weight: 700;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.rps-dot.start { background: #FF7B2C; color: #fff; }
.rps-dot.end { background: #FF7B2C; color: #fff; }
.rps-text { font-size: 14px; color: #CCC; line-height: 1.6; padding-top: 3px; }
</style>
