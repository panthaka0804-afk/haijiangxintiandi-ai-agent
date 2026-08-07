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
        <span class="sd-floor">{{ r.floor }}F · {{ r.category }}</span>
      </div>
    </div>

    <!-- 分段控制器 -->
    <div class="seg-bar">
      <div class="seg-bg" :style="segStyle"></div>
      <button v-for="f in floors" :key="f" class="seg-btn" :class="{ active: activeFloor === f }" @click="activeFloor = f">{{ f }}F</button>
    </div>

    <!-- 地图区域 -->
    <div class="map-section" ref="mapRef">
      <div class="floor-label">{{ activeFloor }}F</div>
      <!-- 每个楼层的地图占位 + 标记点 -->
      <div class="floor-map">
        <svg width="100%" height="100%" viewBox="0 0 400 500" class="floor-svg">
          <!-- 建筑轮廓 -->
          <rect x="10" y="10" width="380" height="480" rx="14" fill="#2A2A2A" stroke="#333" stroke-width="1" />
          <!-- 中庭 -->
          <rect :x="150" :y="90" :width="100" :height="floorLayout.length > 4 ? 320 : 200" rx="8" fill="none" stroke="#444" stroke-dasharray="6 3" />
          <!-- 商铺标记 -->
          <g v-for="(s, i) in floorLayout" :key="s.id" @click="toggleShop(s.id)">
            <rect :x="s.x" :y="s.y" :width="s.w" :height="s.h" rx="6" :fill="highlightId === s.id ? s.color : '#333'" :stroke="highlightId === s.id ? s.color : '#444'" stroke-width="1.5" style="transition: all 0.3s; cursor: pointer;" />
            <text :x="s.x + s.w/2" :y="s.y + s.h/2 + 4" text-anchor="middle" :fill="highlightId === s.id ? '#fff' : '#AAA'" font-size="11" font-weight="600" font-family="inherit" style="transition: all 0.3s; pointer-events: none;">{{ s.name.slice(0,3) }}</text>
          </g>
          <!-- 出入口 -->
          <g v-for="ex in exits" :key="ex.label">
            <rect :x="ex.x - 12" :y="ex.y" :width="24" :height="16" rx="4" fill="#FF7B2C" />
            <text :x="ex.x" :y="ex.y + 12" text-anchor="middle" fill="#fff" font-size="10" font-weight="600" font-family="inherit">{{ ex.label }}</text>
          </g>
          <!-- 扶梯 -->
          <rect x="40" y="200" width="16" height="80" rx="8" fill="#2A2A2A" stroke="#444" stroke-width="1" />
          <text x="48" y="245" text-anchor="middle" fill="#666" font-size="9" font-family="inherit">梯</text>
          <rect x="344" y="200" width="16" height="80" rx="8" fill="#2A2A2A" stroke="#444" stroke-width="1" />
          <text x="352" y="245" text-anchor="middle" fill="#666" font-size="9" font-family="inherit">梯</text>
          <!-- 卫生间 -->
          <rect x="30" y="420" width="50" height="28" rx="6" fill="#333" stroke="#444" stroke-width="1" />
          <text x="55" y="438" text-anchor="middle" fill="#666" font-size="11" font-family="inherit">🚻</text>
          <rect x="320" y="420" width="50" height="28" rx="6" fill="#333" stroke="#444" stroke-width="1" />
          <text x="345" y="438" text-anchor="middle" fill="#666" font-size="11" font-family="inherit">🚻</text>
          <!-- 导航路线 -->
          <polyline v-if="routePath.length >= 2"
            :points="routePath.map(p => `${p.x},${p.y}`).join(' ')"
            fill="none" stroke="#FF7B2C" stroke-width="2.5" stroke-dasharray="8,4"
            stroke-linecap="round" stroke-linejoin="round"
          >
            <animate attributeName="stroke-dashoffset" from="24" to="0" dur="1s" repeatCount="indefinite" />
          </polyline>
          <!-- 路线起点标记 -->
          <circle v-if="routePath.length" :cx="routePath[0].x" :cy="routePath[0].y" r="6" fill="#4CAF50" stroke="#fff" stroke-width="2" />
          <!-- 路线终点标记 -->
          <circle v-if="routePath.length" :cx="routePath[routePath.length-1].x" :cy="routePath[routePath.length-1].y" r="6" fill="#FF7B2C" stroke="#fff" stroke-width="2" />
          <!-- 电梯标记 -->
          <g v-for="(ep, ei) in elevatorPositions[String(activeFloor)] || []" :key="'e'+ei">
            <rect :x="ep.x - 6" :y="ep.y - 6" width="12" height="12" rx="3" fill="#607D8B" stroke="#fff" stroke-width="1" />
            <text :x="ep.x" :y="ep.y + 4" text-anchor="middle" fill="#fff" font-size="8" font-family="inherit">梯</text>
          </g>
          <!-- 入口 -->
          <rect :x="entrancePos.x - 8" :y="entrancePos.y - 8" width="16" height="16" rx="4" fill="#4CAF50" stroke="#fff" stroke-width="1" />
          <text :x="entrancePos.x" :y="entrancePos.y + 4" text-anchor="middle" fill="#fff" font-size="8" font-family="inherit">入</text>
        </svg>
      </div>
      <!-- 地图上的浮层提示 -->
      <div v-if="highlightShop" class="map-tooltip" @click="$router.push(`/shops/${highlightShop.id}`)">
        <div class="mt-icon" :style="{background: highlightShop.color}">{{ highlightShop.name[0] }}</div>
        <div class="mt-info">
          <div class="mt-name">{{ highlightShop.name }}</div>
          <div class="mt-meta">{{ highlightShop.floor }}F · {{ highlightShop.category }}</div>
        </div>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FF7B2C" stroke-width="2" stroke-linecap="round"><polyline points="9 18 15 12 9 6"/></svg>
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
        <span class="sheet-title">{{ activeFloor }}F 商铺</span>
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
            <span class="si-area">{{ (s.zone || s.area || '') + (s.floor ? ' · ' + s.floor + 'F' : '') }}</span>
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
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'

const searchQuery = ref('')
const searchResults = ref([])
const activeFloor = ref(1)
const sheetOpen = ref(true)
const largeFont = ref(false)
const highlightId = ref(null)
const showRoute = ref(false)  // 是否显示路径指引面板
const routePath = ref([])  // 路线坐标点
const routeSteps = ref([])  // 文字步骤
const routeTarget = ref(null)  // 导航目标
const floors = [5, 4, 3, 2, 1, 'B1']

import shopsData from '@/data/shops.js'

const route = useRoute()
const shops = shopsData

const exits = computed(() => {
  if (activeFloor.value === 1) return [{ label: '入口', x: 200, y: 490 }, { label: '西门', x: 50, y: 470 }, { label: '东门', x: 350, y: 470 }]
  if (activeFloor.value === 5) return [{ label: '天台', x: 200, y: 490 }]
  return []
})

const floorLayout = computed(() => {
  const f = activeFloor.value
  const base = shops.filter(s => String(s.floor) === String(f))
  const positions = {
    1: [{x:20,y:30,w:100,h:55},{x:140,y:30,w:120,h:55},{x:280,y:30,w:100,h:55}],
    2: [{x:20,y:50,w:100,h:50},{x:140,y:50,w:120,h:50},{x:280,y:50,w:100,h:50}],
    3: [{x:20,y:40,w:100,h:55},{x:140,y:40,w:120,h:55},{x:280,y:40,w:100,h:55}],
    4: [{x:20,y:60,w:100,h:50},{x:140,y:60,w:120,h:50},{x:280,y:60,w:100,h:50}],
    5: [{x:20,y:30,w:160,h:70},{x:200,y:30,w:180,h:70}],
  }
  return base.map((s, i) => ({ ...s, ...positions[f]?.[i] || {x:20+i*130,y:40,w:110,h:60} }))
})

const floorShops = computed(() => shops.filter(s => String(s.floor) === String(activeFloor.value)))
const highlightShop = computed(() => {
  if (!highlightId.value) return null
  return shops.find(s => s.id === highlightId.value)
})

const segStyle = computed(() => {
  const i = floors.indexOf(activeFloor.value)
  return { left: `${i * 100 / floors.length}%`, width: `${100 / floors.length}%` }
})

function onSearch() {
  if (!searchQuery.value) { searchResults.value = []; return }
  const q = searchQuery.value.toLowerCase()
  searchResults.value = shops.filter(s =>
    s.name.toLowerCase().includes(q) || s.category.includes(q) || s.tags?.some(t => t.includes(q)) || String(s.floor).includes(q)
  )
}

function onSearchItem(shop) {
  activeFloor.value = shop.floor
  highlightId.value = shop.id
  searchResults.value = []
  searchQuery.value = ''
  setTimeout(() => { highlightId.value = null }, 3000)
}

function locateMe() {
  activeFloor.value = 1
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
  // 生成路径
  generateRoute(id)
}

// 3部电梯的坐标（每个楼层都有，简化为固定行列位置）
const elevatorPositions = {
  1: [{x:195,y:405},{x:435,y:775},{x:845,y:405}],
  2: [{x:245,y:405},{x:435,y:775},{x:645,y:405}],
  3: [{x:135,y:405},{x:435,y:775},{x:535,y:405}],
  4: [{x:135,y:405},{x:285,y:775},{x:535,y:405}],
  5: [{x:135,y:405},{x:285,y:775},{x:535,y:405}],
  'B1': [{x:195,y:405},{x:435,y:775},{x:845,y:405}],
}

// 入口大厅（服务台）坐标
const entrancePos = { x: 40, y: 490 }

function generateRoute(shopId) {
  const shop = shops.find(s => s.id === shopId)
  if (!shop) return
  routeTarget.value = shop

  const f = activeFloor.value
  const layout = floorLayout.value
  const target = layout.find(s => s.id === shopId)
  if (!target) return

  // 目标店铺中心坐标
  const tx = target.x + target.w / 2
  const ty = target.y + target.h / 2

  // 入口坐标
  const sx = entrancePos.x
  const sy = entrancePos.y

  // 找最近的电梯
  const elevators = elevatorPositions[String(f)] || elevatorPositions[1]
  let bestElev = elevators[0]
  let bestDist = Infinity
  for (const e of elevators) {
    const d = Math.abs(e.x - tx) + Math.abs(e.y - ty)
    if (d < bestDist) { bestDist = d; bestElev = e }
  }

  const steps = []
  const path = []

  // 起点
  path.push({ x: sx, y: sy })

  // 生成路径
  const midX = (sx + bestElev.x) / 2
  const midY = (bestElev.y + ty) / 2

  // 先走到大厅中央 → 扶梯区域
  path.push({ x: 200, y: 490 })
  steps.push('从大厅入口直行约30米')

  // 扶梯/电梯
  path.push({ x: bestElev.x, y: bestElev.y })
  if (String(f) !== '1') {
    steps.push(`乘坐电梯/扶梯到 ${f}F`)
  }

  // 电梯到目标
  path.push({ x: bestElev.x + (tx > bestElev.x ? 60 : -60), y: bestElev.y })
  steps.push(`出电梯后${tx > bestElev.x ? '向右' : '向左'}转`)

  // 经过店铺
  path.push({ x: tx, y: bestElev.y })
  steps.push('沿通道直行')

  // 到达
  path.push({ x: tx, y: ty })
  steps.push(`到达【${shop.name}】`)

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
      activeFloor.value = typeof s.floor === 'string' ? parseInt(s.floor) || 1 : s.floor
      sheetOpen.value = true
      // 延迟等布局渲染完再生成路线
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
  color: #777; cursor: pointer; position: relative; z-index: 1; transition: color 0.25s; font-family: inherit;
}
.seg-btn.active { color: #FF7B2C; }

/* 地图 */
.map-section { flex: 1; margin: 0 12px; position: relative; }
.floor-label { position: absolute; top: 12px; right: 12px; font-size: 24px; font-weight: 800; color: #444; z-index: 1; }
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
.na-btn.on { background: #3A2A1A; color: #FF7B2C; }
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
.rps-dot.start { background: #4CAF50; color: #fff; }
.rps-dot.end { background: #FF7B2C; color: #fff; }
.rps-text { font-size: 14px; color: #CCC; line-height: 1.6; padding-top: 3px; }

</style>
