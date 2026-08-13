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
      <button class="rb-clear" @click="clearRoute">✕ 取消</button>
    </div>

    <!-- 地图区域 -->
    <div class="map-area" ref="mapAreaRef"
      @wheel.prevent="onWheel"
      @pointerdown="onPointerDown"
    >
      <div v-if="!mapData" class="map-loading">平面图加载中…</div>

      <div v-else class="map-canvas" :style="canvasStyle">
        <div class="floor-wrap" :style="{ width: floorWrapWidth + 'px' }">
          <svg class="floor-svg" :viewBox="`0 0 1000 ${H}`" preserveAspectRatio="none" width="100%" height="auto">
            <!-- 整页 CAD 几何：商铺 / 走廊 / 墙体 / 结构 -->
            <g v-for="(r, i) in baseRects" :key="'r' + i">
              <polygon :points="polyStr(r.poly)" :fill="r.fill" stroke="#B7B0A2" stroke-width="1.1" />
            </g>

            <!-- 设施标注 -->
            <text v-for="(f, i) in facilities" :key="'f' + i"
              :x="f.x * 1000" :y="f.y * H"
              class="fac-text" text-anchor="middle" dominant-baseline="middle">{{ f.text }}</text>

            <!-- 商铺轮廓 + 店名（店名做碰撞去重） -->
            <g v-for="(s, i) in currentShops" :key="'s' + i">
              <polygon
                :points="polyStr(s.poly)"
                fill="none"
                :stroke="selected && selected.name === s.name ? '#C4923A' : s.color"
                :stroke-width="selected && selected.name === s.name ? 3.6 : 2.2"
                :class="['shop-poly', { sel: selected && selected.name === s.name }]"
                @click.stop="onShopClick(s)"
              />
              <text
                v-if="labelVisible(s)"
                :x="s.x * 1000" :y="s.y * H"
                class="shop-label"
                :class="{ sel: selected && selected.name === s.name }"
                @click.stop="onShopClick(s)"
              >{{ s.name }}</text>
            </g>

            <!-- 导航路线 -->
            <path v-if="routeD" :d="routeD" class="route-casing" />
            <path v-if="routeD" :d="routeD" class="route-line" />

            <!-- 目的地标记 -->
            <g v-if="selected">
              <circle :cx="selected.x*1000" :cy="selected.y*H" r="13" fill="#C4923A" stroke="#fff" stroke-width="3.5" />
              <circle :cx="selected.x*1000" :cy="selected.y*H" r="22" fill="none" stroke="#C4923A" stroke-width="2" opacity="0.45" />
            </g>

            <!-- 我的位置（起点） -->
            <g v-if="entrance">
              <circle :cx="entrance[0]*1000" :cy="entrance[1]*H" r="11" fill="#2E8BFF" stroke="#fff" stroke-width="3.5" />
              <circle :cx="entrance[0]*1000" :cy="entrance[1]*H" r="20" fill="none" stroke="#2E8BFF" stroke-width="2" opacity="0.45" />
              <text :x="entrance[0]*1000" :y="entrance[1]*H - 24" class="me-text">我的位置</text>
            </g>
          </svg>
        </div>
      </div>

      <!-- 右上角开关 -->
      <div class="nav-controls">
        <button class="nc-btn" :class="{ on: showLabels }" @click="showLabels = !showLabels" title="显示/隐藏店名">店名 Aa</button>
        <button class="nc-btn" :class="{ on: voiceOn }" @click="toggleVoice" :title="voiceOn ? '语音播报开' : '语音播报关'">{{ voiceOn ? '语音开' : '静音关' }}</button>
      </div>

      <!-- 左上角楼层标签 -->
      <div class="map-label">{{ activeZone }} · {{ activeFloorLabel }}</div>

      <!-- 左下角图例 -->
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

      <!-- 右下角缩放控件 -->
      <div class="zoom-controls">
        <button class="zc-btn" @click="zoomIn" title="放大">+</button>
        <button class="zc-btn" @click="zoomOut" title="缩小">−</button>
        <button class="zc-btn zc-reset" @click="resetView" title="重置视图">⟲</button>
        <span class="zc-level">{{ Math.round(zoom * 100) }}%</span>
      </div>

      <!-- 选中门店气泡 -->
      <div v-if="selected" class="poi-popup" @click.stop>
        <div class="pp-cat" :style="{ background: selected.color }">{{ selected.category }}</div>
        <div class="pp-info">
          <div class="pp-name">{{ selected.name }}</div>
          <div class="pp-sub">{{ activeZone }} · {{ activeFloorLabel }}</div>
        </div>
        <button class="pp-voice" @click="replayVoice" title="语音播报">播</button>
        <button class="pp-nav" @click="clearRoute">取消</button>
        <button class="pp-go" @click="goDetail(selected)">详情 ›</button>
      </div>

      <!-- 分步导航卡 -->
      <div v-if="selected" class="steps-sheet" :class="{ collapsed: !stepsOpen }" @pointerdown.stop>
        <div class="ss-head" @click="stepsOpen = !stepsOpen">
          <span class="ss-title">导航路线 · 共 {{ navSteps.length }} 步</span>
          <span class="ss-actions">
            <button class="ss-voice" @click.stop="replayVoice" title="重播语音">播</button>
            <span class="ss-chev">{{ stepsOpen ? '▾' : '▴' }}</span>
          </span>
        </div>
        <div v-if="stepsOpen" class="ss-body">
          <div v-for="(st, i) in navSteps" :key="i" class="ss-step" :class="'st-' + st.type">
            <span class="ss-ico">{{ st.type === 'arrive' ? '到' : st.type === 'start' ? '起' : (st.turn === '右转' ? '右' : st.turn === '左转' ? '左' : '直') }}</span>
            <span class="ss-text">{{ st.text }}</span>
          </div>
        </div>
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
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import shopsData from '@/data/shops.js'

const route = useRoute()
const router = useRouter()
const shops = shopsData

const searchQuery = ref('')
const searchResults = ref([])
const activeZone = ref('')
const activeFloorKey = ref('')
const zoom = ref(1)
const panX = ref(0)
const panY = ref(0)
const drawerOpen = ref(false)
const legendOpen = ref(false)
const stepsOpen = ref(true)
const showLabels = ref(true)
const voiceOn = ref(true)
const selected = ref(null)

const floorWrapWidth = ref(0)
const mapData = ref(null)
const mapFloors = ref({})

const dragging = ref(false)
const moved = ref(false)
const dragStart = ref({ x: 0, y: 0, px: 0, py: 0 })
const lastTouchDist = ref(0)
const lastTouchCenter = ref({ x: 0, y: 0 })
const mapAreaRef = ref(null)

const M_PER_UNIT = 0.06 // 估算：平面图 1000 视图单位 ≈ 60m

const zoneList = computed(() => [...new Set(shops.map(s => s.zone))])
function getFloorsForZone(zone) {
  const floors = shops.filter(s => s.zone === zone).map(s => Number(s.floor))
  const unique = [...new Set(floors)].sort((a, b) => a - b)
  return unique.map(f => ({ key: String(f), label: f >= 1 ? `${f}F` : `B${Math.abs(f)}`, value: f }))
}
const floorList = computed(() => getFloorsForZone(activeZone.value))
const activeFloorLabel = computed(() => floorList.value.find(f => f.key === activeFloorKey.value)?.label || '')

const currentFloor = computed(() => mapFloors.value[`${activeZone.value}-${activeFloorKey.value}`] || null)
const currentShops = computed(() => currentFloor.value?.shops || [])
const baseRects = computed(() => currentFloor.value?.rects || [])
const facilities = computed(() => currentFloor.value?.facilities || [])
const H = computed(() => currentFloor.value ? Math.round(1000 / currentFloor.value.aspect) : 562)
const entrance = computed(() => currentFloor.value?.entrance || null)

const canvasStyle = computed(() => ({
  transform: `translate(${panX.value}px, ${panY.value}px) scale(${zoom.value})`,
  transition: dragging.value ? 'none' : 'transform 0.18s ease-out',
}))

const floorShops = computed(() =>
  shops.filter(s => s.zone === activeZone.value && String(s.floor) === activeFloorKey.value)
)
const categoryList = computed(() => {
  const seen = {}
  const list = []
  floorShops.value.forEach(s => { if (!seen[s.category]) { seen[s.category] = 1; list.push({ name: s.category, color: s.color }) } })
  return list
})

const routeD = computed(() => {
  if (!selected.value || !currentFloor.value) return ''
  const [ex, ey] = currentFloor.value.entrance
  const px = selected.value.x, py = selected.value.y
  const X0 = ex * 1000, Y0 = ey * H.value, X1 = px * 1000, Y1 = py * H.value
  return `M ${X0} ${Y0} L ${X1} ${Y0} L ${X1} ${Y1}`
})

function polyStr(poly) {
  const h = H.value
  return poly.map(p => `${(p[0] * 1000).toFixed(1)},${(p[1] * h).toFixed(1)}`).join(' ')
}

/* ---- 店名碰撞去重（在 viewBox 坐标系，均匀变换下与屏幕一致） ---- */
function estLabelW(name) { return name.length * 30 + 24 }
const LBL_H = 42
function shopArea(s) {
  const xs = s.poly.map(p => p[0]), ys = s.poly.map(p => p[1])
  return (Math.max(...xs) - Math.min(...xs)) * (Math.max(...ys) - Math.min(...ys))
}
function intersect(a, b) {
  return !(a.x + a.w < b.x || b.x + b.w < a.x || a.y + a.h < b.y || b.y + b.h < a.y)
}
const visibleLabels = computed(() => {
  const set = new Set()
  if (!showLabels.value || !currentShops.value.length) return set
  const arr = [...currentShops.value]
  arr.sort((a, b) => {
    if (selected.value?.name === a.name) return -1
    if (selected.value?.name === b.name) return 1
    return shopArea(b) - shopArea(a)
  })
  const placed = []
  for (const s of arr) {
    const cx = s.x * 1000, cy = s.y * H.value
    const w = estLabelW(s.name), h = LBL_H
    const box = { x: cx - w / 2, y: cy - h / 2, w, h }
    let ok = true
    for (const p of placed) { if (intersect(box, p)) { ok = false; break } }
    if (ok) { set.add(s.name); placed.push(box) }
  }
  return set
})
function labelVisible(s) { return visibleLabels.value.has(s.name) }

/* ---- 分步导航 ---- */
function headingName(dx, dy) {
  if (Math.abs(dx) >= Math.abs(dy)) return dx > 0 ? '东' : '西'
  return dy > 0 ? '南' : '北'
}
const navSteps = computed(() => {
  if (!selected.value || !currentFloor.value) return []
  const fl = currentFloor.value
  const ex = fl.entrance[0], ey = fl.entrance[1]
  const px = selected.value.x, py = selected.value.y
  const P0 = [ex * 1000, ey * H.value]
  const Pc = [px * 1000, ey * H.value]
  const P1 = [px * 1000, py * H.value]
  const raw = [P0, Pc, P1]
  const pts = [raw[0]]
  for (let i = 1; i < raw.length; i++) {
    const a = pts[pts.length - 1], b = raw[i]
    if (Math.hypot(b[0] - a[0], b[1] - a[1]) > 2) pts.push(b)
  }
  const steps = []
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1], b = pts[i]
    const dx = b[0] - a[0], dy = b[1] - a[1]
    const len = Math.max(1, Math.round(Math.hypot(dx, dy) * M_PER_UNIT))
    if (i === 1) {
      steps.push({ type: 'start', text: `从「我的位置」向${headingName(dx, dy)}直行约 ${len} 米` })
    } else {
      const pa = pts[i - 2], pb = pts[i - 1]
      const ddx = pb[0] - pa[0], ddy = pb[1] - pa[1]
      const h1x = Math.sign(ddx), h1y = Math.sign(ddy), h2x = Math.sign(dx), h2y = Math.sign(dy)
      const cross = h1x * h2y - h1y * h2x
      const turn = cross > 0 ? '右转' : (cross < 0 ? '左转' : '直行')
      steps.push({ type: 'turn', turn, text: `${turn === '直行' ? '继续直行' : turn + '后'}向${headingName(dx, dy)}直行约 ${len} 米` })
    }
  }
  steps.push({ type: 'arrive', text: `到达目的地「${selected.value.name}」（${selected.value.category}）` })
  return steps
})

/* ---- 语音播报 ---- */
const synth = (typeof window !== 'undefined' && window.speechSynthesis) ? window.speechSynthesis : null
function speak(text) {
  if (!voiceOn.value || !synth) return
  try {
    synth.cancel()
    const u = new SpeechSynthesisUtterance(text)
    u.lang = 'zh-CN'; u.rate = 1.0; u.pitch = 1.0
    synth.speak(u)
  } catch (e) {}
}
function speakSteps() {
  if (!navSteps.value.length) return
  speak('开始导航。' + navSteps.value.map(s => s.text).join('，') + '。')
}
function replayVoice() { speakSteps() }
function toggleVoice() {
  voiceOn.value = !voiceOn.value
  if (!voiceOn.value && synth) synth.cancel()
}

onMounted(async () => {
  if (zoneList.value.length && !activeZone.value) activeZone.value = zoneList.value[0]
  updateFloor()
  try {
    const res = await fetch(`${import.meta.env.BASE_URL}map2d-data.json`)
    const data = await res.json()
    const map = {}
    data.floors.forEach(f => { map[f.key] = f })
    mapFloors.value = map
    mapData.value = data
  } catch (e) { console.error('map2d-data load failed', e) }
  const shopId = route.query.shop
  if (shopId) {
    const s = shops.find(s => s.id === shopId)
    if (s) { activeZone.value = s.zone; setTimeout(() => { activeFloorKey.value = String(s.floor); drawerOpen.value = true }, 160) }
  }
  window.addEventListener('resize', fitView)
  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', onPointerUp)
  window.addEventListener('pointercancel', onPointerUp)
  nextTick(fitView)
})
onUnmounted(() => {
  window.removeEventListener('resize', fitView)
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
  window.removeEventListener('pointercancel', onPointerUp)
  if (synth) synth.cancel()
})

function updateFloor() {
  const fl = floorList.value
  if (fl.length && (!activeFloorKey.value || !fl.find(f => f.key === activeFloorKey.value))) activeFloorKey.value = fl[0].key
}
function setZone(z) { activeZone.value = z; updateFloor(); selected.value = null; resetView() }
function setFloor(key) { activeFloorKey.value = key; selected.value = null; resetView() }

const MIN_ZOOM = 0.5
const MAX_ZOOM = 6
const ZOOM_STEP = 0.4
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

// 适配视图：默认铺满高度放大（不再留白显小），可拖动看全貌
function fitView() {
  const area = mapAreaRef.value
  if (!area) return
  const rect = area.getBoundingClientRect()
  const aw = rect.width, ah = rect.height
  floorWrapWidth.value = aw
  const planH = aw * H.value / 1000
  const z = clampZoom(ah / planH) // 让平面图竖向铺满
  zoom.value = z
  panX.value = (aw - aw * z) / 2
  panY.value = (ah - planH * z) / 2
}

function flyTo(x, y, z) {
  const area = mapAreaRef.value
  if (!area) return
  const rect = area.getBoundingClientRect()
  const aw = rect.width, ah = rect.height
  const fw = floorWrapWidth.value || aw
  const Z = clampZoom(z || Math.max(zoom.value, 3.0))
  zoom.value = Z
  panX.value = aw / 2 - x * fw * Z
  panY.value = ah / 2 - y * (H.value / 1000) * fw * Z
}

/* ---- 拖动：Pointer Events 统一鼠标/触摸，实时跟随 ---- */
function onPointerDown(e) {
  if (e.target.closest('.zoom-controls, .legend, .poi-popup, .steps-sheet, .nav-controls')) return
  dragging.value = true; moved.value = false
  dragStart.value = { x: e.clientX, y: e.clientY, px: panX.value, py: panY.value }
}
function onPointerMove(e) {
  if (!dragging.value) return
  const dx = e.clientX - dragStart.value.x, dy = e.clientY - dragStart.value.y
  if (Math.abs(dx) > 3 || Math.abs(dy) > 3) moved.value = true
  panX.value = dragStart.value.px + dx
  panY.value = dragStart.value.py + dy
}
function onPointerUp() { dragging.value = false }

function onShopClick(s) {
  if (moved.value) return // 拖动时不触发选中
  selectShop(s)
}
function selectShop(s) {
  selected.value = { name: s.name, x: s.x, y: s.y, color: s.color, category: s.category }
  stepsOpen.value = true
  flyTo(s.x, s.y, 3.0)
  nextTick(() => { if (voiceOn.value) speakSteps() })
}
function clearRoute() { selected.value = null; if (synth) synth.cancel() }
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
.nav-page { display: flex; flex-direction: column; height: 100vh; background: #000000; overflow: hidden; }

.nav-search { display: flex; align-items: center; gap: 8px; padding: 7px 14px; margin: 6px 12px 0; background: #222; border: 1px solid transparent; border-radius: 10px; transition: border-color .15s; }
.nav-search:focus-within { border-color: #C4923A; }
.nav-search input { flex: 1; border: none; background: none; outline: none; font-size: 14px; color: #F0F0F0; font-family: inherit; }
.nav-search input::placeholder { color: rgba(255,255,255,0.4); }
.sc-clear { border: none; background: none; font-size: 15px; color: rgba(255,255,255,0.6); cursor: pointer; padding: 0 2px; }

.search-drop { margin: 4px 12px 0; background: #222; border-radius: 10px; box-shadow: 0 4px 16px rgba(0,0,0,.4); max-height: 220px; overflow-y: auto; z-index: 30; position: relative; }
.sd-item { padding: 11px 14px; display: flex; justify-content: space-between; align-items: center; cursor: pointer; font-size: 14px; color: #F0F0F0; }
.sd-item:not(:last-child) { border-bottom: .5px solid rgba(255,255,255,0.08); }
.sd-item:active { background: #2A2A2A; }
.sd-meta { font-size: 11px; color: rgba(255,255,255,0.5); white-space: nowrap; margin-left: 8px; }

.tab-row { display: flex; gap: 6px; padding: 6px 12px 0; overflow-x: auto; scrollbar-width: none; }
.tab-row::-webkit-scrollbar { display: none; }
.tab-pill { flex-shrink: 0; border: 1px solid rgba(255,255,255,0.08); background: #222; color: rgba(255,255,255,0.6); font-size: 13px; font-weight: 600; padding: 5px 14px; border-radius: 20px; cursor: pointer; font-family: inherit; transition: all .2s; white-space: nowrap; }
.tab-pill.active { background: #C4923A; border-color: #C4923A; color: #fff; }

.route-banner { display: flex; align-items: center; gap: 8px; margin: 6px 12px 0; background: linear-gradient(90deg, #C4923A, #C4923A); color: #fff; border-radius: 10px; padding: 8px 12px; font-size: 13px; box-shadow: 0 4px 14px rgba(196,146,58,.3); }
.rb-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.rb-start { background: #2E8BFF; box-shadow: 0 0 0 3px rgba(46,139,255,.35); }
.rb-text { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.rb-text b { font-weight: 700; }
.rb-clear { border: none; background: rgba(255,255,255,.2); color: #fff; font-size: 12px; padding: 5px 10px; border-radius: 8px; cursor: pointer; font-family: inherit; flex-shrink: 0; }
.rb-clear:active { background: rgba(255,255,255,.35); }

.map-area { flex: 1; margin: 6px 12px 0; position: relative; overflow: hidden; border-radius: 12px; background: #EDEBE5; cursor: grab; user-select: none; touch-action: none; }
.map-area:active { cursor: grabbing; }
.map-loading { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; color: #888; font-size: 14px; }
.map-canvas { position: absolute; top: 0; left: 0; width: 100%; transform-origin: 0 0; }
.floor-wrap { position: relative; }
.floor-svg { display: block; -webkit-user-drag: none; }

.shop-poly { cursor: pointer; transition: stroke .15s; }
.shop-poly:hover { stroke: #C4923A !important; }
.shop-poly.sel { fill: rgba(196,146,58,.18) !important; }
.shop-label { font-size: 30px; fill: #2b2b2b; font-weight: 600; text-anchor: middle; dominant-baseline: middle; paint-order: stroke; stroke: #fff; stroke-width: 3.4px; stroke-linejoin: round; pointer-events: none; font-family: inherit; user-select: none; }
.shop-label.sel { fill: #C4923A; font-weight: 700; }
.fac-text { font-size: 20px; fill: #6b6459; font-weight: 600; paint-order: stroke; stroke: #fff; stroke-width: 3px; stroke-linejoin: round; pointer-events: none; font-family: inherit; user-select: none; }

.route-casing { fill: none; stroke: #fff; stroke-width: 16; stroke-linejoin: round; stroke-linecap: round; opacity: .9; }
.route-line { fill: none; stroke: #C4923A; stroke-width: 7; stroke-linejoin: round; stroke-linecap: round; }
.me-text { font-size: 24px; fill: #2E8BFF; font-weight: 700; text-anchor: middle; paint-order: stroke; stroke: #fff; stroke-width: 3.4px; stroke-linejoin: round; pointer-events: none; font-family: inherit; }

.map-label { position: absolute; top: 10px; left: 12px; font-size: 13px; font-weight: 700; color: #fff; background: rgba(0,0,0,.5); padding: 3px 10px; border-radius: 6px; z-index: 8; pointer-events: none; }

.nav-controls { position: absolute; top: 10px; right: 10px; display: flex; gap: 6px; z-index: 9; }
.nc-btn { border: 1px solid rgba(0,0,0,.12); background: rgba(255,255,255,.9); color: #888; font-size: 11px; font-weight: 600; padding: 5px 9px; border-radius: 16px; cursor: pointer; box-shadow: 0 2px 8px rgba(0,0,0,.15); font-family: inherit; -webkit-tap-highlight-color: transparent; }
.nc-btn.on { background: #C4923A; color: #fff; border-color: #C4923A; }

.zoom-controls { position: absolute; right: 10px; bottom: 10px; display: flex; flex-direction: column; gap: 4px; z-index: 9; align-items: flex-end; }
.zc-btn { width: 36px; height: 36px; border: none; border-radius: 50%; background: rgba(255,255,255,.92); color: #333; font-size: 19px; font-weight: 600; cursor: pointer; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 8px rgba(0,0,0,.18); -webkit-tap-highlight-color: transparent; }
.zc-btn:active { background: #C4923A; color: #fff; }
.zc-reset { font-size: 15px; }
.zc-level { font-size: 10px; color: #555; background: rgba(255,255,255,.85); padding: 2px 8px; border-radius: 8px; margin-top: 2px; box-shadow: 0 1px 4px rgba(0,0,0,.12); }

.legend { position: absolute; left: 10px; bottom: 10px; z-index: 9; }
.legend-toggle { display: flex; align-items: center; gap: 4px; border: none; background: rgba(255,255,255,.92); color: #333; font-size: 12px; padding: 6px 10px; border-radius: 18px; cursor: pointer; box-shadow: 0 2px 8px rgba(0,0,0,.18); font-weight: 600; }
.legend-ico { font-size: 13px; }
.legend-panel { margin-bottom: 6px; background: rgba(255,255,255,.95); border-radius: 10px; padding: 8px 10px; min-width: 96px; box-shadow: 0 4px 14px rgba(0,0,0,.2); }
.legend-row { display: flex; align-items: center; gap: 7px; font-size: 12px; color: #333; padding: 3px 0; }
.legend-dot { width: 12px; height: 12px; border-radius: 3px; flex-shrink: 0; }

.poi-popup { position: absolute; left: 50%; bottom: 16px; transform: translateX(-50%); display: flex; align-items: center; gap: 8px; z-index: 10; background: rgba(34,34,34,.96); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 8px 10px; box-shadow: 0 6px 20px rgba(0,0,0,.5); max-width: 94%; }
.pp-cat { font-size: 11px; color: #fff; padding: 3px 8px; border-radius: 6px; font-weight: 700; flex-shrink: 0; }
.pp-info { min-width: 0; }
.pp-name { font-size: 14px; font-weight: 700; color: #FFF; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pp-sub { font-size: 11px; color: #999; }
.pp-voice, .pp-nav, .pp-go { border: none; border-radius: 8px; font-size: 12px; padding: 6px 10px; cursor: pointer; font-family: inherit; flex-shrink: 0; }
.pp-voice { background: #2E8BFF; color: #fff; }
.pp-nav { background: #333; color: #CCC; }
.pp-go { background: #C4923A; color: #fff; font-weight: 600; }

.steps-sheet { position: absolute; left: 10px; right: 64px; bottom: 56px; z-index: 8; background: rgba(255,255,255,.96); border-radius: 12px; box-shadow: 0 6px 20px rgba(0,0,0,.25); overflow: hidden; max-height: 42%; display: flex; flex-direction: column; }
.steps-sheet.collapsed { max-height: 40px; }
.ss-head { display: flex; align-items: center; justify-content: space-between; padding: 9px 12px; cursor: pointer; background: linear-gradient(90deg, #C4923A, #C4923A); color: #fff; }
.ss-title { font-size: 13px; font-weight: 700; }
.ss-actions { display: flex; align-items: center; gap: 8px; }
.ss-voice { border: none; background: rgba(255,255,255,.22); color: #fff; font-size: 13px; width: 28px; height: 28px; border-radius: 50%; cursor: pointer; }
.ss-chev { font-size: 13px; }
.ss-body { padding: 6px 12px 10px; overflow-y: auto; }
.ss-step { display: flex; align-items: flex-start; gap: 9px; padding: 7px 0; border-bottom: .5px solid #eee; }
.ss-step:last-child { border-bottom: none; }
.ss-ico { font-size: 17px; flex-shrink: 0; width: 22px; text-align: center; line-height: 1.3; }
.ss-text { font-size: 13px; line-height: 1.45; color: #2b2b2b; }
.st-arrive .ss-text { font-weight: 700; color: #C4923A; }

.shop-drawer { background: #222; border-radius: 16px 16px 0 0; border-top: 1px solid rgba(255,255,255,0.08); box-shadow: 0 -2px 12px rgba(0,0,0,.35); transition: max-height .32s ease; max-height: 42px; overflow: hidden; flex-shrink: 0; }
.shop-drawer.open { max-height: 280px; }
.drawer-handle { padding: 8px 16px; cursor: pointer; display: flex; flex-direction: column; align-items: center; gap: 3px; -webkit-tap-highlight-color: transparent; }
.drawer-pill { width: 32px; height: 4px; background: rgba(255,255,255,0.2); border-radius: 2px; transition: background .2s; }
.shop-drawer.open .drawer-pill { background: #C4923A; }
.drawer-hint { font-size: 11px; color: rgba(255,255,255,0.55); }
.shop-drawer.open .drawer-hint { color: rgba(255,255,255,0.8); }
.drawer-body { padding: 0 14px 14px; overflow-y: auto; max-height: 230px; }
.shop-item { display: flex; align-items: center; gap: 10px; padding: 9px 0; cursor: pointer; border-bottom: .5px solid rgba(255,255,255,0.08); }
.shop-item:active { background: #222; }
.shop-item:last-child { border-bottom: none; }
.si-dot { width: 34px; height: 34px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; color: #fff; flex-shrink: 0; }
.si-info { flex: 1; min-width: 0; }
.si-name { font-size: 14px; font-weight: 600; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.si-tags { font-size: 11px; color: rgba(255,255,255,0.55); margin-top: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.shop-empty { text-align: center; color: rgba(255,255,255,0.4); font-size: 13px; padding: 20px 0; }
</style>
