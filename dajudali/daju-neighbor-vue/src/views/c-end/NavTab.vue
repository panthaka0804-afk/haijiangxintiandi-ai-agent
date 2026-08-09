<template>
  <div class="nav-page">
    <!-- 搜索栏 -->
    <div class="nav-search">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#999" stroke-width="2.5" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input v-model="searchQuery" placeholder="搜索商户、分类、楼层…" @input="onSearch" />
      <button v-if="searchQuery" class="sc-clear" @click="searchQuery='';searchResults=[]">✕</button>
    </div>
    <div v-if="searchResults.length" class="search-drop">
      <div v-for="r in searchResults" :key="r.id" class="sd-item" @click="onSearchItem(r)">
        <span>{{ r.name }}</span>
        <span class="sd-meta">{{ r.zone }} · {{ r.floorLabel }} · {{ r.category }}</span>
      </div>
    </div>

    <!-- 区块 / 楼层切换 -->
    <div class="tab-row">
      <button v-for="z in zoneList" :key="z" class="tab-pill" :class="{ active: activeZone === z }" @click="setZone(z)">{{ z }}</button>
    </div>
    <div class="tab-row">
      <button v-for="f in floorList" :key="f.key" class="tab-pill" :class="{ active: activeFloorKey === f.key }" @click="setFloor(f.key)">{{ f.label }}</button>
    </div>

    <!-- 路线提示条 -->
    <div v-if="selected" class="route-banner">
      <span class="rb-dot rb-start"></span>
      <span class="rb-text">我的位置 → <b>{{ selected.name }}</b></span>
      <button class="rb-clear" @click="clearRoute">✕ 取消导航</button>
    </div>

    <!-- 地图区域：真实商铺轮廓平铺的 2D 平面图 -->
    <div class="map-area" ref="mapAreaRef"
      @wheel.prevent="onWheel"
      @mousedown="onDragStart"
      @touchstart.passive="onTouchStart"
      @touchmove.prevent="onTouchMove"
      @touchend="onDragEnd"
      @mouseup="onDragEnd"
      @mouseleave="onDragEnd"
    >
      <!-- 加载中 -->
      <div v-if="!mapData" class="map-loading">平面图加载中…</div>

      <div v-else class="map-canvas" :style="canvasStyle">
        <div class="floor-wrap" :style="{ width: floorWrapWidth + 'px' }">
          <svg class="floor-svg" :viewBox="`0 0 1000 ${H}`" preserveAspectRatio="none" width="100%" height="auto">
            <!-- 走廊 / 公共区域底色 -->
            <rect x="0" y="0" :width="1000" :height="H" fill="#ECEAE4" />
            <!-- 建筑外框 -->
            <rect x="3" y="3" :width="994" :height="H-6" fill="none" stroke="#C9C5BC" stroke-width="3" rx="6" />

            <!-- 商铺多边形 -->
            <g v-for="(s, i) in currentShops" :key="s.name + i">
              <polygon
                :points="polyStr(s)"
                :fill="fillOf(s)"
                :stroke="selected && selected.name === s.name ? '#FF7B2C' : s.color"
                :stroke-width="selected && selected.name === s.name ? 3.4 : 1.3"
                :class="['shop-poly', { sel: selected && selected.name === s.name }]"
                @click.stop="selectShop(s)"
              />
              <text
                :x="s.x * 1000" :y="s.y * H"
                class="shop-label"
                :class="{ sel: selected && selected.name === s.name }"
                @click.stop="selectShop(s)"
              >{{ s.name }}</text>
            </g>

            <!-- 导航路线 -->
            <path v-if="routeD" :d="routeD" class="route-casing" />
            <path v-if="routeD" :d="routeD" class="route-line" />

            <!-- 我的位置（起点） -->
            <g v-if="entrance">
              <circle :cx="entrance[0]*1000" :cy="entrance[1]*H" r="11" fill="#2E8BFF" stroke="#fff" stroke-width="3.5" />
              <circle :cx="entrance[0]*1000" :cy="entrance[1]*H" r="20" fill="none" stroke="#2E8BFF" stroke-width="2" opacity="0.45" />
              <text :x="entrance[0]*1000" :y="entrance[1]*H - 22" class="me-text">我的位置</text>
            </g>
          </svg>
        </div>
      </div>

      <!-- 右下角缩放控件 -->
      <div class="zoom-controls">
        <button class="zc-btn" @click="zoomIn" title="放大">+</button>
        <button class="zc-btn" @click="zoomOut" title="缩小">−</button>
        <button class="zc-btn zc-reset" @click="resetView" title="重置视图">⟲</button>
        <span class="zc-level">{{ Math.round(zoom * 100) }}%</span>
      </div>

      <!-- 左上角楼层标签 -->
      <div class="map-label">{{ activeZone }} · {{ activeFloorLabel }}</div>

      <!-- 左下角分类图例（可折叠） -->
      <div class="legend" :class="{ open: legendOpen }">
        <button class="legend-toggle" @click="legendOpen = !legendOpen">
          <span class="legend-ico">▦</span> 图例
        </button>
        <div v-if="legendOpen" class="legend-panel">
          <div v-for="c in categoryList" :key="c.name" class="legend-row">
            <span class="legend-dot" :style="{ background: c.color }"></span>{{ c.name }}
          </div>
        </div>
      </div>

      <!-- 选中门店气泡 -->
      <div v-if="selected" class="poi-popup" @click.stop>
        <div class="pp-cat" :style="{ background: selected.color }">{{ selected.category }}</div>
        <div class="pp-info">
          <div class="pp-name">{{ selected.name }}</div>
          <div class="pp-sub">{{ activeZone }} · {{ activeFloorLabel }}</div>
        </div>
        <button class="pp-nav" @click="clearRoute">取消</button>
        <button class="pp-go" @click="goDetail(selected)">详情 ›</button>
      </div>
    </div>

    <!-- 商户列表折叠抽屉 -->
    <div class="shop-drawer" :class="{ open: drawerOpen }">
      <div class="drawer-handle" @click="drawerOpen = !drawerOpen">
        <div class="drawer-pill"></div>
        <span class="drawer-hint">{{ drawerOpen ? '收起列表' : `商铺列表 (${floorShops.length})` }}</span>
      </div>
      <div v-if="drawerOpen" class="drawer-body">
        <div v-for="s in floorShops" :key="s.id" class="shop-item" @click="locateShop(s)">
          <div class="si-dot" :style="{ background: s.color }">{{ s.name[0] }}</div>
          <div class="si-info">
            <div class="si-name">{{ s.name }}</div>
            <div class="si-tags">{{ s.tags?.join(' · ') || s.category }}</div>
          </div>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#777" stroke-width="2.5" stroke-linecap="round"><polyline points="9 18 15 12 9 6"/></svg>
        </div>
        <div v-if="!floorShops.length" class="shop-empty">该楼层暂无入驻商户</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import shopsData from '@/data/shops.js'

const route = useRoute()
const router = useRouter()
const shops = shopsData

// ---- 状态 ----
const searchQuery = ref('')
const searchResults = ref([])
const activeZone = ref('')
const activeFloorKey = ref('')
const zoom = ref(1)
const panX = ref(0)
const panY = ref(0)
const drawerOpen = ref(false)
const legendOpen = ref(false)
const selected = ref(null)

const floorWrapWidth = ref(0)
const mapData = ref(null)          // 真实商铺几何（来自 map3d-data.json）
const mapFloors = ref({})          // key: "1区-1" -> floor 对象

// 拖拽/手势
const dragging = ref(false)
const dragStart = ref({ x: 0, y: 0, px: 0, py: 0 })
const lastTouchDist = ref(0)
const lastTouchCenter = ref({ x: 0, y: 0 })
const moved = ref(false)
const mapAreaRef = ref(null)

// ---- 区块 / 楼层 ----
const zoneList = computed(() => [...new Set(shops.map(s => s.zone))])
function getFloorsForZone(zone) {
  const floors = shops.filter(s => s.zone === zone).map(s => Number(s.floor))
  const unique = [...new Set(floors)].sort((a, b) => a - b)
  return unique.map(f => ({ key: String(f), label: f >= 1 ? `${f}F` : `B${Math.abs(f)}`, value: f }))
}
const floorList = computed(() => getFloorsForZone(activeZone.value))
const activeFloorLabel = computed(() => floorList.value.find(f => f.key === activeFloorKey.value)?.label || '')

// 当前楼层真实几何
const currentFloor = computed(() => mapFloors.value[`${activeZone.value}-${activeFloorKey.value}`] || null)
const currentShops = computed(() => currentFloor.value?.shops || [])
const H = computed(() => currentFloor.value ? Math.round(1000 / currentFloor.value.aspect) : 562)
const entrance = computed(() => currentFloor.value?.entrance || null)

const canvasStyle = computed(() => ({
  transform: `translate(${panX.value}px, ${panY.value}px) scale(${zoom.value})`,
  transition: dragging.value ? 'none' : 'transform 0.25s ease-out',
}))

const floorShops = computed(() =>
  shops.filter(s => s.zone === activeZone.value && String(s.floor) === activeFloorKey.value)
)

// 分类图例
const categoryList = computed(() => {
  const seen = {}
  const list = []
  floorShops.value.forEach(s => { if (!seen[s.category]) { seen[s.category] = 1; list.push({ name: s.category, color: s.color }) } })
  return list
})

// 导航路线（我的位置 → 选中店，先横后纵，正交折线）
const routeD = computed(() => {
  if (!selected.value || !currentFloor.value) return ''
  const [ex, ey] = currentFloor.value.entrance
  const px = selected.value.x, py = selected.value.y
  const X0 = ex * 1000, Y0 = ey * H.value, X1 = px * 1000, Y1 = py * H.value
  // 先走到目标列、再走到目标行（走廊折线感）
  return `M ${X0} ${Y0} L ${X1} ${Y0} L ${X1} ${Y1}`
})

// 多边形点串
function polyStr(s) {
  const h = H.value
  return s.poly.map(p => `${(p[0] * 1000).toFixed(1)},${(p[1] * h).toFixed(1)}`).join(' ')
}
// 浅色填充（保留业态色相）
function fillOf(s) {
  const hex = s.color
  if (!hex || hex[0] !== '#' || hex.length < 7) return '#F3F1EC'
  let r = parseInt(hex.slice(1, 3), 16), g = parseInt(hex.slice(3, 5), 16), b = parseInt(hex.slice(5, 7), 16)
  const a = 0.16
  return `rgba(${r},${g},${b},${a})`
}

// ---- 初始化 ----
onMounted(async () => {
  if (zoneList.value.length && !activeZone.value) activeZone.value = zoneList.value[0]
  updateFloor()
  // 拉取真实商铺几何
  try {
    const res = await fetch(`${import.meta.env.BASE_URL}map3d-data.json`)
    const data = await res.json()
    const map = {}
    data.floors.forEach(f => { map[f.key] = f })
    mapFloors.value = map
    mapData.value = data
  } catch (e) {
    console.error('map3d-data load failed', e)
  }
  const shopId = route.query.shop
  if (shopId) {
    const s = shops.find(s => s.id === shopId)
    if (s) { activeZone.value = s.zone; setTimeout(() => { activeFloorKey.value = String(s.floor); drawerOpen.value = true }, 160) }
  }
  window.addEventListener('resize', fitView)
  nextTick(fitView)
})
function updateFloor() {
  const fl = floorList.value
  if (fl.length && (!activeFloorKey.value || !fl.find(f => f.key === activeFloorKey.value))) activeFloorKey.value = fl[0].key
}

// ---- 切换 ----
function setZone(z) { activeZone.value = z; updateFloor(); selected.value = null; resetView() }
function setFloor(key) { activeFloorKey.value = key; selected.value = null; resetView() }

// ---- 缩放 ----
const MIN_ZOOM = 0.5
const MAX_ZOOM = 5
const ZOOM_STEP = 0.35
const clampZoom = z => Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, z))
function zoomIn() { zoom.value = clampZoom(zoom.value + ZOOM_STEP) }
function zoomOut() { zoom.value = clampZoom(zoom.value - ZOOM_STEP) }
function resetView() { zoom.value = 1; panX.value = 0; panY.value = 0; nextTick(fitView) }

function zoomAt(clientX, clientY, delta) {
  const rect = mapAreaRef.value?.getBoundingClientRect()
  if (!rect) { zoom.value = clampZoom(zoom.value + delta); return }
  const xInArea = clientX - rect.left
  const yIn = clientY - rect.top
  const oldZoom = zoom.value
  const newZoom = clampZoom(oldZoom + delta)
  const scale = newZoom / oldZoom
  panX.value = xInArea - (xInArea - panX.value) * scale
  panY.value = yIn - (yIn - panY.value) * scale
  zoom.value = newZoom
}
function onWheel(e) {
  const delta = e.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP
  zoomAt(e.clientX, e.clientY, delta)
}

// ---- 适配视图（平面图按宽度铺满，垂直可拖动）----
function fitView() {
  const area = mapAreaRef.value
  if (!area) return
  const rect = area.getBoundingClientRect()
  const aw = rect.width, ah = rect.height
  const fw = aw
  floorWrapWidth.value = fw
  const planH = fw * H.value / 1000
  zoom.value = 1
  panX.value = 0
  panY.value = (ah - planH) / 2 > 0 ? (ah - planH) / 2 : 0
}

// 飞到某点（0..1 归一化）
function flyTo(x, y, z) {
  const area = mapAreaRef.value
  if (!area) return
  const rect = area.getBoundingClientRect()
  const aw = rect.width, ah = rect.height
  const fw = floorWrapWidth.value || aw
  const Z = clampZoom(z || Math.max(zoom.value, 2.4))
  zoom.value = Z
  panX.value = aw / 2 - x * fw * Z
  panY.value = ah / 2 - y * (H.value / 1000) * fw * Z
}

// ---- 拖拽平移 ----
function onDragStart(e) {
  if (e.target.closest('.zoom-controls, .legend, .poi-popup')) return
  dragging.value = true; moved.value = false
  const pt = e.touches ? e.touches[0] : e
  dragStart.value = { x: pt.clientX, y: pt.clientY, px: panX.value, py: panY.value }
}
function onDragMove(e) {
  if (!dragging.value) return
  const pt = e.touches ? e.touches[0] : e
  const dx = pt.clientX - dragStart.value.x, dy = pt.clientY - dragStart.value.y
  if (Math.abs(dx) > 4 || Math.abs(dy) > 4) moved.value = true
  panX.value = dragStart.value.px + dx
  panY.value = dragStart.value.py + dy
}
function onTouchStart(e) {
  if (e.touches.length === 2) {
    const t1 = e.touches[0], t2 = e.touches[1]
    lastTouchDist.value = Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY)
    lastTouchCenter.value = { x: (t1.clientX + t2.clientX) / 2, y: (t1.clientY + t2.clientY) / 2 }
  } else if (e.touches.length === 1) onDragStart(e)
}
function onTouchMove(e) {
  if (e.touches.length === 2) {
    const t1 = e.touches[0], t2 = e.touches[1]
    const dist = Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY)
    if (lastTouchDist.value > 0) {
      const scale = dist / lastTouchDist.value
      zoomAt(lastTouchCenter.value.x, lastTouchCenter.value.y, (scale - 1) * zoom.value * 0.5)
    }
    lastTouchDist.value = dist
    lastTouchCenter.value = { x: (t1.clientX + t2.clientX) / 2, y: (t1.clientY + t2.clientY) / 2 }
  } else if (e.touches.length === 1) onDragMove(e)
}
function onDragEnd() { dragging.value = false; lastTouchDist.value = 0 }

// ---- 选店 / 路线 ----
function selectShop(s) {
  selected.value = { name: s.name, x: s.x, y: s.y, color: s.color, category: s.category }
  flyTo(s.x, s.y, 2.6)
}
function clearRoute() { selected.value = null }
function goDetail(s) {
  const shop = shops.find(x => x.name === s.name && x.zone === activeZone.value && String(x.floor) === activeFloorKey.value)
  if (shop) router.push(`/shops/${shop.id}`)
}
function locateShop(s) {
  if (s.zone !== activeZone.value || String(s.floor) !== activeFloorKey.value) {
    activeZone.value = s.zone
    activeFloorKey.value = String(s.floor)
    selected.value = null
  }
  nextTick(() => {
    const arr = currentFloor.value?.shops || []
    const sh = arr.find(x => x.name === s.name)
    if (sh) selectShop(sh)
  })
}

// ---- 搜索 ----
function onSearch() {
  const q = searchQuery.value.toLowerCase().trim()
  if (!q) { searchResults.value = []; return }
  searchResults.value = shops.filter(s =>
    s.name.toLowerCase().includes(q) ||
    s.category.includes(q) ||
    s.tags?.some(t => t.toLowerCase().includes(q)) ||
    s.zone.includes(q)
  ).slice(0, 20).map(s => ({ ...s, floorLabel: (s.floor >= 1 ? `${s.floor}F` : `B${Math.abs(s.floor)}`) }))
}
function onSearchItem(shop) {
  searchQuery.value = ''; searchResults.value = []
  activeZone.value = shop.zone
  activeFloorKey.value = String(shop.floor)
  selected.value = null
  nextTick(() => {
    const arr = currentFloor.value?.shops || []
    const sh = arr.find(x => x.name === shop.name)
    if (sh) selectShop(sh)
    else drawerOpen.value = true
  })
}
</script>

<style scoped>
.nav-page {
  display: flex; flex-direction: column;
  height: 100vh; background: #0c0c0c; overflow: hidden;
}

/* 搜索栏 */
.nav-search {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 14px; margin: 6px 12px 0;
  background: #1E1E1E; border: 1px solid transparent; border-radius: 10px;
  transition: border-color .15s;
}
.nav-search:focus-within { border-color: #FF7B2C; }
.nav-search input { flex: 1; border: none; background: none; outline: none; font-size: 14px; color: #F0F0F0; font-family: inherit; }
.nav-search input::placeholder { color: #666; }
.sc-clear { border: none; background: none; font-size: 15px; color: #888; cursor: pointer; padding: 0 2px; }

.search-drop {
  margin: 4px 12px 0; background: #1E1E1E; border-radius: 10px;
  box-shadow: 0 4px 16px rgba(0,0,0,.4); max-height: 220px; overflow-y: auto; z-index: 30; position: relative;
}
.sd-item { padding: 11px 14px; display: flex; justify-content: space-between; align-items: center; cursor: pointer; font-size: 14px; color: #F0F0F0; }
.sd-item:not(:last-child) { border-bottom: .5px solid #2A2A2A; }
.sd-item:active { background: #2A2A2A; }
.sd-meta { font-size: 11px; color: #888; white-space: nowrap; margin-left: 8px; }

/* 切换器 */
.tab-row { display: flex; gap: 6px; padding: 6px 12px 0; overflow-x: auto; scrollbar-width: none; }
.tab-row::-webkit-scrollbar { display: none; }
.tab-pill {
  flex-shrink: 0; border: 1px solid #333; background: #161616; color: #999;
  font-size: 13px; font-weight: 600; padding: 5px 14px; border-radius: 20px;
  cursor: pointer; font-family: inherit; transition: all .2s; white-space: nowrap;
}
.tab-pill.active { background: #FF7B2C; border-color: #FF7B2C; color: #fff; }

/* 路线提示条 */
.route-banner {
  display: flex; align-items: center; gap: 8px; margin: 6px 12px 0;
  background: linear-gradient(90deg, #FF7B2C, #E85D04); color: #fff;
  border-radius: 10px; padding: 8px 12px; font-size: 13px;
  box-shadow: 0 4px 14px rgba(255,123,44,.3);
}
.rb-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.rb-start { background: #2E8BFF; box-shadow: 0 0 0 3px rgba(46,139,255,.35); }
.rb-text { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.rb-text b { font-weight: 700; }
.rb-clear { border: none; background: rgba(255,255,255,.2); color: #fff; font-size: 12px; padding: 5px 10px; border-radius: 8px; cursor: pointer; font-family: inherit; flex-shrink: 0; }
.rb-clear:active { background: rgba(255,255,255,.35); }

/* 地图区域 */
.map-area {
  flex: 1; margin: 6px 12px 0; position: relative; overflow: hidden;
  border-radius: 12px; background: #ECEAE4; cursor: grab; user-select: none; touch-action: none;
}
.map-area:active { cursor: grabbing; }
.map-loading { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; color: #888; font-size: 14px; }
.map-canvas { position: absolute; top: 0; left: 0; width: 100%; transform-origin: 0 0; }
.floor-wrap { position: relative; }
.floor-svg { display: block; -webkit-user-drag: none; }

/* 商铺多边形 */
.shop-poly { cursor: pointer; transition: fill .15s, stroke .15s; }
.shop-poly:hover { fill: rgba(255,123,44,.22) !important; }
.shop-poly.sel { fill: rgba(255,123,44,.30) !important; }
.shop-label {
  font-size: 30px; fill: #2b2b2b; font-weight: 600; text-anchor: middle; dominant-baseline: middle;
  paint-order: stroke; stroke: #fff; stroke-width: 3.2px; stroke-linejoin: round;
  pointer-events: none; font-family: inherit; user-select: none;
}
.shop-label.sel { fill: #E85D04; font-weight: 700; }

/* 路线 */
.route-casing { fill: none; stroke: #fff; stroke-width: 16; stroke-linejoin: round; stroke-linecap: round; opacity: .9; }
.route-line { fill: none; stroke: #FF7B2C; stroke-width: 7; stroke-linejoin: round; stroke-linecap: round; stroke-dasharray: 1 0; }

/* 我的位置文字 */
.me-text { font-size: 26px; fill: #2E8BFF; font-weight: 700; text-anchor: middle; paint-order: stroke; stroke: #fff; stroke-width: 3.4px; stroke-linejoin: round; pointer-events: none; font-family: inherit; }

/* 地图内标签 */
.map-label { position: absolute; top: 10px; left: 12px; font-size: 13px; font-weight: 700; color: #fff; background: rgba(0,0,0,.5); padding: 3px 10px; border-radius: 6px; z-index: 8; pointer-events: none; }

/* 缩放控件 */
.zoom-controls { position: absolute; right: 10px; bottom: 10px; display: flex; flex-direction: column; gap: 4px; z-index: 9; align-items: flex-end; }
.zc-btn {
  width: 36px; height: 36px; border: none; border-radius: 50%; background: rgba(255,255,255,.9);
  color: #333; font-size: 19px; font-weight: 600; cursor: pointer;
  display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 8px rgba(0,0,0,.18);
  -webkit-tap-highlight-color: transparent;
}
.zc-btn:active { background: #FF7B2C; color: #fff; }
.zc-reset { font-size: 15px; }
.zc-level { font-size: 10px; color: #555; background: rgba(255,255,255,.85); padding: 2px 8px; border-radius: 8px; margin-top: 2px; box-shadow: 0 1px 4px rgba(0,0,0,.12); }

/* 图例 */
.legend { position: absolute; left: 10px; bottom: 10px; z-index: 9; }
.legend-toggle { display: flex; align-items: center; gap: 4px; border: none; background: rgba(255,255,255,.9); color: #333; font-size: 12px; padding: 6px 10px; border-radius: 18px; cursor: pointer; box-shadow: 0 2px 8px rgba(0,0,0,.18); font-weight: 600; }
.legend-ico { font-size: 13px; }
.legend-panel { margin-bottom: 6px; background: rgba(255,255,255,.95); border-radius: 10px; padding: 8px 10px; min-width: 96px; box-shadow: 0 4px 14px rgba(0,0,0,.2); }
.legend-row { display: flex; align-items: center; gap: 7px; font-size: 12px; color: #333; padding: 3px 0; }
.legend-dot { width: 12px; height: 12px; border-radius: 3px; flex-shrink: 0; }

/* 选中气泡 */
.poi-popup {
  position: absolute; left: 50%; bottom: 16px; transform: translateX(-50%);
  display: flex; align-items: center; gap: 8px; z-index: 10;
  background: rgba(24,24,24,.96); border: 1px solid #333; border-radius: 12px;
  padding: 8px 10px; box-shadow: 0 6px 20px rgba(0,0,0,.5); max-width: 92%;
}
.pp-cat { font-size: 11px; color: #fff; padding: 3px 8px; border-radius: 6px; font-weight: 700; flex-shrink: 0; }
.pp-info { min-width: 0; }
.pp-name { font-size: 14px; font-weight: 700; color: #FFF; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pp-sub { font-size: 11px; color: #999; }
.pp-nav, .pp-go { border: none; border-radius: 8px; font-size: 12px; padding: 6px 10px; cursor: pointer; font-family: inherit; flex-shrink: 0; }
.pp-nav { background: #333; color: #CCC; }
.pp-go { background: #FF7B2C; color: #fff; font-weight: 600; }

/* 商户列表抽屉 */
.shop-drawer {
  background: #161616; border-radius: 16px 16px 0 0; box-shadow: 0 -2px 12px rgba(0,0,0,.35);
  transition: max-height .32s ease; max-height: 42px; overflow: hidden; flex-shrink: 0;
}
.shop-drawer.open { max-height: 280px; }
.drawer-handle { padding: 8px 16px; cursor: pointer; display: flex; flex-direction: column; align-items: center; gap: 3px; -webkit-tap-highlight-color: transparent; }
.drawer-pill { width: 32px; height: 4px; background: #444; border-radius: 2px; transition: background .2s; }
.shop-drawer.open .drawer-pill { background: #FF7B2C; }
.drawer-hint { font-size: 11px; color: #777; }
.shop-drawer.open .drawer-hint { color: #AAA; }
.drawer-body { padding: 0 14px 14px; overflow-y: auto; max-height: 230px; }
.shop-item { display: flex; align-items: center; gap: 10px; padding: 9px 0; cursor: pointer; border-bottom: .5px solid #222; }
.shop-item:active { background: #222; }
.shop-item:last-child { border-bottom: none; }
.si-dot { width: 34px; height: 34px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; color: #fff; flex-shrink: 0; }
.si-info { flex: 1; min-width: 0; }
.si-name { font-size: 14px; font-weight: 600; color: #EEE; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.si-tags { font-size: 11px; color: #888; margin-top: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.shop-empty { text-align: center; color: #666; font-size: 13px; padding: 20px 0; }
</style>
