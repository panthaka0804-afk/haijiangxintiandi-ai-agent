<template>
  <div class="nav-page">
    <!-- 搜索栏（精简） -->
    <div class="nav-search">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#777" stroke-width="2.5" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input v-model="searchQuery" placeholder="搜索商铺、楼层…" @input="onSearch" />
      <button v-if="searchQuery" class="sc-clear" @click="searchQuery='';searchResults=[]">✕</button>
    </div>
    <!-- 搜索结果下拉 -->
    <div v-if="searchResults.length" class="search-drop">
      <div v-for="r in searchResults" :key="r.id" class="sd-item" @click="onSearchItem(r)">
        <span>{{ r.name }}</span>
        <span class="sd-meta">{{ r.zone }} · {{ r.floorLabel }} · {{ r.category }}</span>
      </div>
    </div>

    <!-- 区块切换 -->
    <div class="tab-row">
      <button v-for="z in zoneList" :key="z" class="tab-pill" :class="{ active: activeZone === z }" @click="setZone(z)">{{ z }}</button>
    </div>
    <!-- 楼层切换 -->
    <div class="tab-row">
      <button v-for="f in floorList" :key="f.key" class="tab-pill" :class="{ active: activeFloorKey === f.key }" @click="setFloor(f.key)">{{ f.label }}</button>
    </div>

    <!-- 地图区域（占满剩余空间） -->
    <div class="map-area" ref="mapAreaRef"
      @wheel.prevent="onWheel"
      @mousedown="onDragStart"
      @touchstart.passive="onTouchStart"
      @touchmove.prevent="onTouchMove"
      @touchend="onDragEnd"
      @mouseup="onDragEnd"
      @mouseleave="onDragEnd"
    >
      <!-- 楼层平面图底图 -->
      <div class="map-viewport" :style="viewportStyle">
        <img v-if="currentImageUrl" :src="currentImageUrl" :alt="`${activeZone} ${activeFloorLabel}`" class="floor-img" draggable="false" />
        <!-- 无底图时的提示 -->
        <div v-else class="no-map-hint">
          <p>暂无 {{ activeZone }} {{ activeFloorLabel }} 平面图</p>
          <p class="hint-sub">该楼层可能正在规划中</p>
        </div>
      </div>

      <!-- 右下角：放大镜控件（固定在地图区域内） -->
      <div class="zoom-controls">
        <button class="zc-btn" @click="zoomIn" title="放大">+</button>
        <button class="zc-btn" @click="zoomOut" title="缩小">−</button>
        <button class="zc-btn zc-reset" @click="resetView" title="重置视图">⟲</button>
        <span class="zc-level">{{ Math.round(zoom * 100) }}%</span>
      </div>

      <!-- 当前楼层标签 -->
      <div class="map-label">{{ activeZone }} · {{ activeFloorLabel }}</div>
    </div>

    <!-- 商户列表（可折叠抽屉，默认收起） -->
    <div class="shop-drawer" :class="{ open: drawerOpen }">
      <div class="drawer-handle" @click="drawerOpen = !drawerOpen">
        <div class="drawer-pill"></div>
        <span class="drawer-hint">{{ drawerOpen ? '收起列表' : `商铺列表 (${floorShops.length})` }}</span>
      </div>
      <div v-if="drawerOpen" class="drawer-body">
        <div v-for="s in floorShops" :key="s.id" class="shop-item" @click="$router.push(`/shops/${s.id}`)">
          <div class="si-dot" :style="{ background: s.color }">{{ s.name[0] }}</div>
          <div class="si-info">
            <div class="si-name">{{ s.name }}</div>
            <div class="si-tags">{{ s.tags?.join(' · ') || s.category }}</div>
          </div>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#555" stroke-width="2.5" stroke-linecap="round"><polyline points="9 18 15 12 9 6"/></svg>
        </div>
        <div v-if="!floorShops.length" class="shop-empty">该楼层暂无入驻商户</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import shopsData from '@/data/shops.js'

const route = useRoute()
const shops = shopsData

// ---- 状态 ----
const searchQuery = ref('')
const searchResults = ref([])
const activeZone = ref('')
const activeFloorKey = ref('')
const zoom = ref(1)
const panX = ref(0)
const panY = ref(0)
const drawerOpen = ref(false) // 默认收起！

// 拖拽状态
const dragging = ref(false)
const dragStart = ref({ x: 0, y: 0, px: 0, py: 0 })
const lastTouchDist = ref(0)
const lastTouchCenter = ref({ x: 0, y: 0 })

// refs
const mapAreaRef = ref(null)

// ---- 区块 & 楼层数据 ----
// 所有区块
const zoneList = computed(() => [...new Set(shops.map(s => s.zone))])

// 区块 → 可用楼层列表（带显示名和 key）
function getFloorsForZone(zone) {
  const floors = shops.filter(s => s.zone === zone).map(s => Number(s.floor))
  const unique = [...new Set(floors)].sort((a, b) => a - b)
  return unique.map(f => ({
    key: String(f),
    label: f >= 1 ? `${f}F` : `B${Math.abs(f)}`, // 正数=xF，负数=Bx
    value: f
  }))
}

const floorList = computed(() => getFloorsForZone(activeZone.value))

// 当前选中楼层的显示名
const activeFloorLabel = computed(() => {
  const f = floorList.value.find(f => f.key === activeFloorKey.value)
  return f?.label || ''
})

// 区块 → ASCII slug（避免中文文件名在 URL 编码链路里 404）
const ZONE_SLUG = { '1区': 'z1', '3区': 'z3', '4区': 'z4', '5区': 'z5', '6区': 'z6' }
// 当前平面图 URL（public 目录，Vite 原样复制到 dist 根；用 BASE_URL 自动适配 /vue/ 前缀）
const currentImageUrl = computed(() => {
  if (!activeZone.value || !activeFloorKey.value) return ''
  const slug = ZONE_SLUG[activeZone.value]
  if (!slug) return '' // 7区等暂无平面图 → 显示提示
  return `${import.meta.env.BASE_URL}floor-plans/${slug}-${activeFloorKey.value}.png`
})

// 视口 transform 样式
const viewportStyle = computed(() => ({
  transform: `translate(${panX.value}px, ${panY.value}px) scale(${zoom.value})`,
  transition: dragging.value ? 'none' : 'transform 0.25s ease-out',
}))

// 当前楼层的商铺
const floorShops = computed(() =>
  shops.filter(s => s.zone === activeZone.value && String(s.floor) === activeFloorKey.value)
)

// ---- 初始化 ----
onMounted(() => {
  if (zoneList.value.length && !activeZone.value) {
    activeZone.value = zoneList.value[0]
  }
  updateFloor()
  // 从店铺详情页跳转过来时定位
  const shopId = route.query.shop
  if (shopId) {
    const s = shops.find(s => s.id === shopId)
    if (s) {
      activeZone.value = s.zone
      setTimeout(() => {
        activeFloorKey.value = String(s.floor)
        drawerOpen.value = true
      }, 100)
    }
  }
})

function updateFloor() {
  const fl = floorList.value
  if (fl.length && (!activeFloorKey.value || !fl.find(f => f.key === activeFloorKey.value))) {
    activeFloorKey.value = fl[0].key
  }
}

// ---- 切换 ----
function setZone(z) {
  activeZone.value = z
  updateFloor()
  resetView()
}
function setFloor(key) {
  activeFloorKey.value = key
  resetView()
}

// ---- 缩放 ----
const MIN_ZOOM = 0.5
const MAX_ZOOM = 3.5
const ZOOM_STEP = 0.25

function clampZoom(z) {
  return Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, z))
}

function zoomIn() { zoom.value = clampZoom(zoom.value + ZOOM_STEP) }
function zoomOut() { zoom.value = clampZoom(zoom.value - ZOOM_STEP) }

function resetView() {
  zoom.value = 1
  panX.value = 0
  panY.value = 0
}

function zoomAt(clientX, clientY, delta) {
  const rect = mapAreaRef.value?.getBoundingClientRect()
  if (!rect) { zoom.value = clampZoom(zoom.value + delta); return }

  const xInArea = clientX - rect.left
  const yInArea = clientY - rect.top

  const oldZoom = zoom.value
  const newZoom = clampZoom(oldZoom + delta)

  // 以指针位置为中心缩放
  const scale = newZoom / oldZoom
  panX.value = xInArea - (xInArea - panX.value) * scale
  panY.value = yInArea - (yInArea - panY.value) * scale
  zoom.value = newZoom
}

function onWheel(e) {
  const delta = e.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP
  zoomAt(e.clientX, e.clientY, delta)
}

// ---- 拖拽平移 ----
function onDragStart(e) {
  if (e.target.tagName === 'BUTTON' || e.target.closest('.zoom-controls')) return
  dragging.value = true
  const pt = e.touches ? e.touches[0] : e
  dragStart.value = { x: pt.clientX, y: pt.clientY, px: panX.value, py: panY.value }
}

function onDragMove(e) {
  if (!dragging.value) return
  const pt = e.touches ? e.touches[0] : e
  const dx = pt.clientX - dragStart.value.x
  const dy = pt.clientY - dragStart.value.y
  panX.value = dragStart.value.px + dx
  panY.value = dragStart.value.py + dy
}

function onTouchStart(e) {
  if (e.touches.length === 2) {
    // 双指捏合准备
    const t1 = e.touches[0], t2 = e.touches[1]
    lastTouchDist.value = Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY)
    lastTouchCenter.value = {
      x: (t1.clientX + t2.clientX) / 2,
      y: (t1.clientY + t2.clientY) / 2,
    }
  } else if (e.touches.length === 1) {
    onDragStart(e)
  }
}

function onTouchMove(e) {
  if (e.touches.length === 2) {
    // 双指缩放
    const t1 = e.touches[0], t2 = e.touches[1]
    const dist = Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY)
    if (lastTouchDist.value > 0) {
      const scale = dist / lastTouchDist.value
      const delta = (scale - 1) * zoom.value * 0.5
      zoomAt(lastTouchCenter.value.x, lastTouchCenter.value.y, delta)
    }
    lastTouchDist.value = dist
    const cx = (t1.clientX + t2.clientX) / 2
    const cy = (t1.clientY + t2.clientY) / 2
    lastTouchCenter.value = { x: cx, y: cy }
  } else if (e.touches.length === 1) {
    onDragMove(e)
  }
}

function onDragEnd() {
  dragging.value = false
  lastTouchDist.value = 0
}

// ---- 搜索 ----
function onSearch() {
  if (!searchQuery.value) { searchResults.value = []; return }
  const q = searchQuery.value.toLowerCase().trim()
  if (!q) { searchResults.value = []; return }
  searchResults.value = shops.filter(s =>
    s.name.toLowerCase().includes(q) ||
    s.category.includes(q) ||
    s.tags?.some(t => t.toLowerCase().includes(q)) ||
    s.zone.includes(q)
  ).slice(0, 20)
}

function onSearchItem(shop) {
  activeZone.value = shop.zone
  activeFloorKey.value = String(shop.floor)
  drawerOpen.value = true
  searchResults.value = []
  searchQuery.value = ''
  resetView()
}
</script>

<style scoped>
.nav-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #000;
  overflow: hidden;
}

/* ===== 搜索栏 ===== */
.nav-search {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 14px; margin: 6px 12px 0;
  background: #1E1E1E; border: 1px solid transparent;
  border-radius: 10px; transition: border-color .15s;
}
.nav-search:focus-within { border-color: #FF7B2C; }
.nav-search input {
  flex: 1; border: none; background: none; outline: none;
  font-size: 14px; color: #F0F0F0; font-family: inherit;
}
.nav-search input::placeholder { color: #555; }
.sc-clear { border:none; background:none; font-size:15px; color:#666; cursor:pointer; padding:0 2px; }

.search-drop {
  margin: 4px 12px 0; background: #1E1E1E; border-radius: 10px;
  box-shadow: 0 4px 16px rgba(0,0,0,.35);
  max-height: 200px; overflow-y: auto; position: relative; z-index: 10;
}
.sd-item {
  padding: 11px 14px; display: flex; justify-content: space-between; align-items: center;
  cursor: pointer; font-size: 14px; color: #F0F0F0;
}
.sd-item:not(:last-child) { border-bottom: .5px solid #2A2A2A; }
.sd-meta { font-size: 11px; color: #777; white-space: nowrap; margin-left: 8px; }

/* ===== 区块/楼层切换器 ===== */
.tab-row {
  display: flex; gap: 6px; padding: 6px 12px 0;
  overflow-x: auto; scrollbar-width: none;
  -ms-overflow-style: none;
}
.tab-row::-webkit-scrollbar { display: none; }
.tab-pill {
  flex-shrink: 0; border: 1px solid #333; background: #161616;
  color: #888; font-size: 13px; font-weight: 600;
  padding: 5px 14px; border-radius: 20px; cursor: pointer;
  font-family: inherit; transition: all .2s; white-space: nowrap;
}
.tab-pill.active { background: #FF7B2C; border-color: #FF7B2C; color: #fff; }
.tab-pill:active { opacity: .75; }

/* ===== 地图区域 ===== */
.map-area {
  flex: 1; margin: 6px 12px 0; position: relative;
  overflow: hidden; border-radius: 12px;
  background: #111; cursor: grab; user-select: none;
  touch-action: none; /* 阻止浏览器默认触摸行为 */
}
.map-area:active { cursor: grabbing; }

.map-viewport {
  width: 100%; height: 100%;
  display: flex; align-items: center; justify-content: center;
  transform-origin: center center;
}

.floor-img {
  max-width: 100%; max-height: 100%;
  object-fit: contain; pointer-events: none;
  /* 防止图片被拖选 */
  -webkit-user-drag: none;
}

.no-map-hint {
  text-align: center; color: #555; padding: 40px 20px;
}
.no-map-hint p { font-size: 15px; margin-bottom: 6px; }
.hint-sub { font-size: 12px; color: #333; }

/* 地图内标签 */
.map-label {
  position: absolute; top: 10px; left: 12px;
  font-size: 13px; font-weight: 700; color: #444;
  background: rgba(0,0,0,.45); padding: 3px 10px; border-radius: 6px;
  z-index: 2; pointer-events: none;
}

/* ===== 放大镜控件（右下角固定） ===== */
.zoom-controls {
  position: absolute; right: 10px; bottom: 10px;
  display: flex; flex-direction: column; gap: 4px;
  z-index: 5; align-items: flex-end;
}
.zc-btn {
  width: 36px; height: 36px; border: none; border-radius: 50%;
  background: rgba(30,30,30,.85); backdrop-filter: blur(6px);
  color: #DDD; font-size: 19px; font-weight: 600;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: background .15s; border: 1px solid rgba(255,255,255,.1);
  -webkit-tap-highlight-color: transparent;
}
.zc-btn:active { background: rgba(255,123,44,.7); color: #fff; }
.zc-reset { font-size: 15px; }
.zc-level {
  font-size: 10px; color: #666; background: rgba(0,0,0,.5);
  padding: 2px 8px; border-radius: 8px; margin-top: 2px;
}

/* ===== 商户列表折叠抽屉 ===== */
.shop-drawer {
  background: #161616; border-radius: 16px 16px 0 0;
  box-shadow: 0 -2px 12px rgba(0,0,0,.35);
  transition: max-height .32s ease;
  max-height: 42px; /* 折叠态：只露 handle */
  overflow: hidden;
  flex-shrink: 0;
}
.shop-drawer.open { max-height: 280px; }

.drawer-handle {
  padding: 8px 16px; cursor: pointer;
  display: flex; flex-direction: column; align-items: center; gap: 3px;
  -webkit-tap-highlight-color: transparent;
}
.drawer-pill {
  width: 32px; height: 4px; background: #444; border-radius: 2px;
  transition: background .2s;
}
.shop-drawer.open .drawer-pill { background: #FF7B2C; }
.drawer-hint { font-size: 11px; color: #777; }
.shop-drawer.open .drawer-hint { color: #AAA; }

.drawer-body {
  padding: 0 14px 14px; overflow-y: auto; max-height: 230px;
}

.shop-item {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 0; cursor: pointer;
  border-bottom: .5px solid #222; transition: background .12s;
}
.shop-item:active { background: #222; }
.shop-item:last-child { border-bottom: none; }

.si-dot {
  width: 34px; height: 34px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 700; color: #fff; flex-shrink: 0;
}
.si-info { flex: 1; min-width: 0; }
.si-name { font-size: 14px; font-weight: 600; color: #EEE; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.si-tags { font-size: 11px; color: #777; margin-top: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.shop-empty {
  text-align: center; color: #555; font-size: 13px; padding: 20px 0;
}
</style>
