<template>
  <div class="nav-page" style="background:#1A1A1A">
    <!-- 苹果风顶部栏 - 毛玻璃 -->
    <div class="nav-top">
      <div class="nav-top-inner">
        <button class="nav-back" @click="$router.back()">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#1A1A1A" stroke-width="2.5" stroke-linecap="round"><polyline points="15 18 9 12 15 6"/></svg>
        </button>
        <h2>室内导航</h2>
        <button class="nav-aa" @click="userStore.largeFont = !userStore.largeFont" :style="{ color: userStore.largeFont ? '#999999' : '#999', fontWeight: '700', fontSize: '14px' }">{{ userStore.largeFont ? '老年关怀' : '老年关怀' }}</button>
      </div>
    </div>

    <!-- iOS 分段控制器 - 楼层切换 -->
    <div class="nav-segmented">
      <div class="seg-track">
        <div class="seg-bg" :style="segStyle"></div>
        <button
          v-for="f in floorList"
          :key="f"
          :class="['seg-btn', { active: currentFloor === f }]"
          @click="switchFloor(f)"
        >{{ f }}</button>
      </div>
    </div>

    <!-- 搜索框 -->
    <div class="nav-search-wrap">
      <div class="nav-search-inner">
        <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#999" stroke-width="2.5" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索店铺或设施"
          @input="onSearchInput"
          @keyup.enter="onSearchEnter"
        />
        <button v-if="searchQuery" class="search-clear" @click="searchQuery='';searchResults=[]">✕</button>
      </div>
      <!-- 搜索结果下拉 -->
      <div v-if="searchResults.length" class="search-drop">
        <div
          v-for="it in searchResults"
          :key="it.f+it.n"
          class="search-item"
          @click="highlightTarget(it)"
        >{{ it.n }} <span class="search-floor">{{ it.f }}</span></div>
      </div>
    </div>

    <!-- 路线卡片 -->
    <div v-if="routeSteps.length" class="route-card">
      <div class="route-card-top">
        <span class="route-title">{{ routeTitle }}</span>
        <button class="route-play" @click="startStepNav">
          <svg width="14" height="14" viewBox="0 0 24 24" :fill="isNavigating ? '#666' : '#FFFFFF'"><polygon points="5,3 19,12 5,21"/></svg>
          <span>{{ isNavigating ? '停止' : '导航' }}</span>
        </button>
      </div>
      <div class="route-steps">
        <div
          v-for="(step, i) in routeSteps"
          :key="i"
          class="route-step"
          :class="{ 'route-step--active': activeStep === i, 'route-step--done': activeStep > i }"
        >
          <div class="step-dot">{{ activeStep > i ? '✓' : i + 1 }}</div>
          <span>{{ step }}</span>
        </div>
      </div>
    </div>

    <!-- SVG 地图 -->
    <div class="nav-map-wrap" ref="mapWrap"
      @mousedown="onDragStart"
      @mousemove="onDragMove"
      @mouseup="onDragEnd"
      @mouseleave="onDragEnd"
      @touchstart="onDragStart"
      @touchmove="onDragMove"
      @touchend="onDragEnd"
      @wheel.prevent="onWheel"
    >
      <div class="nav-map" v-html="svgContent" @click="onMapClick" :style="{ transform: 'scale(' + mapScale + ')', transformOrigin: '0 0' }"></div>
    </div>
    <!-- 缩放控件（固定定位，不随地图动） -->
    <div class="zoom-controls">
      <button class="zoom-btn" @click.stop="mapScale = Math.min(3, mapScale + 0.2)">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#F0F0F0" stroke-width="2.5" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><line x1="11" y1="7" x2="11" y2="15"/><line x1="7" y1="11" x2="15" y2="11"/><line x1="20" y1="20" x2="16" y2="16"/></svg>
      </button>
      <div class="zoom-level">{{ Math.round(mapScale * 100) }}%</div>
      <button class="zoom-btn" @click.stop="mapScale = Math.max(0.5, mapScale - 0.2)">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#F0F0F0" stroke-width="2.5" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><line x1="7" y1="11" x2="15" y2="11"/><line x1="20" y1="20" x2="16" y2="16"/></svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const route = useRoute()

// ====== 地图数据 ======
const navData = {
  '1F': [
    { x: 120, y: 245, w: 200, h: 140, name: '星巴克', type: 'cafe' },
    { x: 120, y: 400, w: 200, h: 140, name: '金饰珠宝', type: 'retail' },
    { x: 120, y: 555, w: 200, h: 140, name: '轻奢服饰', type: 'retail' },
    { x: 120, y: 720, w: 200, h: 70, name: '卫生间', type: 'wc' },
    { x: 350, y: 520, w: 200, h: 220, name: 'B1美食广场', type: 'food' },
    { x: 580, y: 350, w: 220, h: 390, name: '中央大厅服务台', type: 'service' },
    { x: 840, y: 245, w: 200, h: 140, name: '朱光玉火锅', type: 'food' },
    { x: 1070, y: 245, w: 200, h: 140, name: '瑞幸咖啡', type: 'food' },
    { x: 1300, y: 245, w: 220, h: 140, name: '亲子儿童乐园', type: 'kids' },
    { x: 840, y: 400, w: 200, h: 140, name: '零售精品', type: 'retail' },
    { x: 1070, y: 400, w: 200, h: 140, name: '数码电子', type: 'retail' },
    { x: 1300, y: 400, w: 220, h: 140, name: '书吧文创', type: 'service' },
    { x: 1550, y: 245, w: 200, h: 140, name: '健身房', type: 'sport' },
    { x: 1550, y: 400, w: 200, h: 140, name: '瑜伽舞蹈', type: 'sport' },
    { x: 580, y: 760, w: 200, h: 100, name: '母婴室', type: 'wc' },
    { x: 840, y: 555, w: 430, h: 305, name: '中央庭院', type: 'open' },
    { x: 840, y: 880, w: 200, h: 100, name: '充电桩', type: 'parking' },
    { x: 1070, y: 880, w: 200, h: 100, name: '无障碍通道', type: 'service' },
    { x: 1300, y: 560, w: 470, h: 420, name: '停车场入口', type: 'parking' },
    { x: 365, y: 280, w: 30, h: 30, name: '电梯', type: 'elevator' },
    { x: 830, y: 775, w: 30, h: 30, name: '电梯', type: 'elevator' },
    { x: 1520, y: 280, w: 30, h: 30, name: '电梯', type: 'elevator' },
  ],
  '2F': [
    { x: 120, y: 240, w: 280, h: 180, name: '夜校教室(大)', type: 'classroom' },
    { x: 120, y: 435, w: 280, h: 140, name: '夜校教室(小)', type: 'classroom' },
    { x: 120, y: 590, w: 280, h: 140, name: '共享会客厅', type: 'meeting' },
    { x: 120, y: 745, w: 280, h: 70, name: '卫生间', type: 'wc' },
    { x: 440, y: 240, w: 350, h: 280, name: '亲子街区', type: 'kids' },
    { x: 440, y: 535, w: 350, h: 220, name: '时尚服饰', type: 'retail' },
    { x: 830, y: 240, w: 300, h: 200, name: '电影院售票', type: 'cinema' },
    { x: 830, y: 455, w: 300, h: 160, name: '观影厅入口', type: 'cinema' },
    { x: 1160, y: 240, w: 250, h: 200, name: '儿童培训', type: 'kids' },
    { x: 1160, y: 455, w: 250, h: 160, name: '艺术教室', type: 'classroom' },
    { x: 830, y: 630, w: 250, h: 100, name: '母婴室', type: 'wc' },
    { x: 1100, y: 630, w: 310, h: 100, name: 'VIP会客室', type: 'meeting' },
    { x: 830, y: 745, w: 580, h: 135, name: '教育培训展区', type: 'classroom' },
    { x: 430, y: 260, w: 30, h: 30, name: '电梯', type: 'elevator' },
    { x: 820, y: 260, w: 30, h: 30, name: '电梯', type: 'elevator' },
    { x: 1150, y: 260, w: 30, h: 30, name: '电梯', type: 'elevator' },
  ],
  '3F': [
    { x: 120, y: 240, w: 350, h: 350, name: '电影院', type: 'cinema' },
    { x: 120, y: 605, w: 350, h: 150, name: '影院休息厅', type: 'cinema' },
    { x: 120, y: 770, w: 350, h: 70, name: '卫生间', type: 'wc' },
    { x: 510, y: 240, w: 400, h: 300, name: '健身房', type: 'sport' },
    { x: 510, y: 555, w: 400, h: 200, name: '瑜伽工作室', type: 'sport' },
    { x: 950, y: 240, w: 350, h: 280, name: '少儿培训中心', type: 'classroom' },
    { x: 950, y: 535, w: 350, h: 140, name: '舞蹈教室', type: 'classroom' },
    { x: 1340, y: 240, w: 280, h: 280, name: '网球场', type: 'sport' },
    { x: 1340, y: 535, w: 280, h: 140, name: '室内篮球', type: 'sport' },
    { x: 950, y: 690, w: 350, h: 100, name: '大会议室', type: 'meeting' },
    { x: 1340, y: 690, w: 280, h: 100, name: '商务中心', type: 'meeting' },
    { x: 500, y: 260, w: 30, h: 30, name: '电梯', type: 'elevator' },
    { x: 940, y: 260, w: 30, h: 30, name: '电梯', type: 'elevator' },
    { x: 1330, y: 260, w: 30, h: 30, name: '电梯', type: 'elevator' },
  ],
}

// 停车场车位数据（位于 1F 停车场区域）
const parkingSpots = [
  // A区（靠近充电桩）
  { id: 'A101', x: 850, y: 590, row: 'A', col: 1 },
  { id: 'A102', x: 890, y: 590, row: 'A', col: 2 },
  { id: 'A103', x: 930, y: 590, row: 'A', col: 3 },
  { id: 'A104', x: 970, y: 590, row: 'A', col: 4 },
  { id: 'A105', x: 1010, y: 590, row: 'A', col: 5 },
  { id: 'A106', x: 1050, y: 590, row: 'A', col: 6 },
  { id: 'A107', x: 1090, y: 590, row: 'A', col: 7 },
  { id: 'A108', x: 1130, y: 590, row: 'A', col: 8 },
  // B区（中间排）
  { id: 'B201', x: 1340, y: 590, row: 'B', col: 1 },
  { id: 'B202', x: 1380, y: 590, row: 'B', col: 2 },
  { id: 'B203', x: 1420, y: 590, row: 'B', col: 3 },
  { id: 'B204', x: 1460, y: 590, row: 'B', col: 4 },
  { id: 'B205', x: 1500, y: 590, row: 'B', col: 5 },
  { id: 'B206', x: 1540, y: 590, row: 'B', col: 6 },
  { id: 'B207', x: 1580, y: 590, row: 'B', col: 7 },
  { id: 'B208', x: 1620, y: 590, row: 'B', col: 8 },
  { id: 'B209', x: 1660, y: 590, row: 'B', col: 9 },
  { id: 'B210', x: 1700, y: 590, row: 'B', col: 10 },
  { id: 'B211', x: 1340, y: 620, row: 'B', col: 11 },
  { id: 'B212', x: 1380, y: 620, row: 'B', col: 12 },
  { id: 'B213', x: 1420, y: 620, row: 'B', col: 13 },
  { id: 'B214', x: 1460, y: 620, row: 'B', col: 14 },
  { id: 'B215', x: 1500, y: 620, row: 'B', col: 15 },
  { id: 'B216', x: 1540, y: 620, row: 'B', col: 16 },
  { id: 'B217', x: 1580, y: 620, row: 'B', col: 17 },
  { id: 'B218', x: 1620, y: 620, row: 'B', col: 18 },
  { id: 'B219', x: 1660, y: 620, row: 'B', col: 19 },
  { id: 'B220', x: 1700, y: 620, row: 'B', col: 20 },
  // C区（最下层）
  { id: 'C301', x: 1340, y: 650, row: 'C', col: 1 },
  { id: 'C302', x: 1380, y: 650, row: 'C', col: 2 },
  { id: 'C303', x: 1420, y: 650, row: 'C', col: 3 },
  { id: 'C304', x: 1460, y: 650, row: 'C', col: 4 },
  { id: 'C305', x: 1500, y: 650, row: 'C', col: 5 },
  { id: 'C306', x: 1540, y: 650, row: 'C', col: 6 },
  { id: 'C307', x: 1580, y: 650, row: 'C', col: 7 },
  { id: 'C308', x: 1620, y: 650, row: 'C', col: 8 },
  { id: 'C309', x: 1660, y: 650, row: 'C', col: 9 },
  { id: 'C310', x: 1700, y: 650, row: 'C', col: 10 },
  { id: 'C311', x: 1340, y: 680, row: 'C', col: 11 },
  { id: 'C312', x: 1380, y: 680, row: 'C', col: 12 },
  { id: 'C313', x: 1420, y: 680, row: 'C', col: 13 },
  { id: 'C314', x: 1460, y: 680, row: 'C', col: 14 },
  { id: 'C315', x: 1500, y: 680, row: 'C', col: 15 },
  { id: 'C316', x: 1540, y: 680, row: 'C', col: 16 },
  { id: 'C317', x: 1580, y: 680, row: 'C', col: 17 },
  { id: 'C318', x: 1620, y: 680, row: 'C', col: 18 },
  { id: 'C319', x: 1660, y: 680, row: 'C', col: 19 },
  { id: 'C320', x: 1700, y: 680, row: 'C', col: 20 },
  { id: 'C321', x: 1340, y: 710, row: 'C', col: 21 },
  { id: 'C322', x: 1380, y: 710, row: 'C', col: 22 },
  { id: 'C323', x: 1420, y: 710, row: 'C', col: 23 },
  { id: 'C324', x: 1460, y: 710, row: 'C', col: 24 },
  { id: 'C325', x: 1500, y: 710, row: 'C', col: 25 },
  { id: 'C326', x: 1540, y: 710, row: 'C', col: 26 },
  { id: 'C327', x: 1580, y: 710, row: 'C', col: 27 },
  { id: 'C328', x: 1620, y: 710, row: 'C', col: 28 },
  { id: 'C329', x: 1660, y: 710, row: 'C', col: 29 },
  { id: 'C330', x: 1700, y: 710, row: 'C', col: 30 },
]

// 颜色由 cType() 函数统一提供（3D版本）

const floorList = Object.keys(navData)
const currentFloor = ref('1F')
const searchQuery = ref('')
const searchResults = ref([])
const selectedTarget = ref(null)
const routeTitle = ref('')
const routeSteps = ref([])
const activeStep = ref(-1)
const isNavigating = ref(false)
let navTimer = null
const mapScale = ref(1)

// 分段控制器滑块位置
const segStyle = computed(() => {
  const idx = floorList.indexOf(currentFloor.value)
  return {
    width: `${100 / floorList.length}%`,
    transform: `translateX(${idx * 100}%)`,
  }
})

onMounted(() => {
  document.body.style.overflow = 'hidden'
  // 从停车寻车跳转过来
  const qTarget = route.query.target
  const qSpot = route.query.spot
  const qPlate = route.query.plate
  if (qTarget) {
    setRouteTitle(qPlate, qSpot)
    // 找具体车位坐标
    const spotNum = parseSpotNumber(qSpot)
    const spotData = spotNum ? parkingSpots.find(s => s.id === spotNum) : null
    if (spotData) {
      // 用具体车位坐标
      currentFloor.value = '1F'
      setTimeout(() => {
        generateParkingRoute(spotData, '1F', qSpot)
      }, 100)
    } else {
      // fallback: 用停车场入口
      let found = null
      for (const f in navData) {
        const r = navData[f].find(r => r.name === qTarget || r.type === 'parking')
        if (r) { found = { ...r, f }; break }
      }
      if (found) {
        currentFloor.value = found.f
        selectedTarget.value = found
        setTimeout(() => {
          generateParkingRoute(found, found.f, qSpot)
        }, 100)
      }
    }
  }
})

// 从字符串中提取车位编号，如 "B区 B205", "B205", "A区A101"
function parseSpotNumber(str) {
  if (!str) return null
  const m = str.match(/([A-C])\d{3}/i)
  return m ? m[0].toUpperCase() : null
}

function setRouteTitle(plate, spot) {
  routeTitle.value = plate ? `🅿️ ${plate} → ${spot || '车位'}` : `当前位置 → ${spot || '车位'}`
}

// SVG 拖拽平移
let dragState = { active: false, startX: 0, startY: 0, scrollLeft: 0, scrollTop: 0 }
const mapWrap = ref(null)

function onDragStart(e) {
  const el = mapWrap.value
  if (!el) return
  if (e.touches && e.touches.length === 2) { dragState.pinchDist = Math.hypot(e.touches[0].clientX-e.touches[1].clientX, e.touches[0].clientY-e.touches[1].clientY); dragState.pinchBase = mapScale.value; return }
  dragState.active = true
  dragState.startX = (e.touches ? e.touches[0].clientX : e.clientX)
  dragState.startY = (e.touches ? e.touches[0].clientY : e.clientY)
  dragState.scrollLeft = el.scrollLeft
  dragState.scrollTop = el.scrollTop
  el.style.cursor = 'grabbing'
}

function onDragMove(e) {
  if (e.touches && e.touches.length === 2 && dragState.pinchDist) { e.preventDefault(); const d=Math.hypot(e.touches[0].clientX-e.touches[1].clientX, e.touches[0].clientY-e.touches[1].clientY); mapScale.value=Math.max(.5, Math.min(3, dragState.pinchBase*(d/dragState.pinchDist))); return }
  if (!dragState.active) return
  const el = mapWrap.value
  if (!el) return
  e.preventDefault()
  const x = (e.touches ? e.touches[0].clientX : e.clientX)
  const y = (e.touches ? e.touches[0].clientY : e.clientY)
  const dx = dragState.startX - x
  const dy = dragState.startY - y
  el.scrollLeft = dragState.scrollLeft + dx
  el.scrollTop = dragState.scrollTop + dy
}

function onWheel(e) { mapScale.value = Math.max(0.5, Math.min(3, mapScale.value + (e.deltaY > 0 ? -0.1 : 0.1))) }
function onDragEnd() {
  dragState.active = false
  dragState.pinchDist = undefined
  if (mapWrap.value) mapWrap.value.style.cursor = 'grab'
}
onBeforeUnmount(() => { document.body.style.overflow = ''; stopNav() })

// 搜索
function onSearchInput() {
  const q = searchQuery.value
  if (!q) { searchResults.value = []; return }
  const items = []
  for (const f in navData)
    for (const r of navData[f])
      if (r.name.includes(q) || r.type.includes(q))
        items.push({ f, n: r.name })
  searchResults.value = items.slice(0, 10)
}

function onSearchEnter() {
  if (searchResults.value.length > 0) highlightTarget(searchResults.value[0])
}

function highlightTarget(it) {
  const rooms = navData[it.f] || []
  const room = rooms.find(r => r.name === it.n)
  if (room) {
    selectedTarget.value = { ...room, f: it.f }
    currentFloor.value = it.f
    searchResults.value = []
    generateRoute(room, it.f)
  }
}

function switchFloor(f) {
  currentFloor.value = f
  if (selectedTarget.value && selectedTarget.value.f !== f) {
    selectedTarget.value = null; routeSteps.value = []; stopNav()
  }
}

function onMapClick(e) {
  const svgEl = e.currentTarget.querySelector('svg')
  if (!svgEl) return
  const rect = svgEl.getBoundingClientRect()
  const vb = svgEl.viewBox.baseVal
  const x = (e.clientX - rect.left) * vb.width / rect.width
  const y = (e.clientY - rect.top) * vb.height / rect.height
  const rooms = navData[currentFloor.value] || []
  for (const r of rooms)
    if (x >= r.x && x <= r.x + r.w && y >= r.y && y <= r.y + r.h)
      { highlightTarget({ f: currentFloor.value, n: r.name }); return }
}

// 路线生成
function generateRoute(room, floor) {
  stopNav()
  const desk = navData[floor]?.find(r => r.name === '中央大厅服务台')
  const start = desk || { x: 580, y: 545, w: 220, h: 390, name: '服务台' }
  const sx = start.x + start.w / 2, sy = start.y + start.h / 2
  const ex = room.x + room.w / 2, ey = room.y + room.h / 2
  routeTitle.value = `${start.name} → ${room.name}`

  const steps = [`从${start.name}出发`]
  const dx = ex - sx, dy = ey - sy
  const dirX = dx > 60 ? '东' : dx < -60 ? '西' : ''
  const dirY = dy > 60 ? '南' : dy < -60 ? '北' : ''

  // 障碍检测：线段是否穿过任何店铺/设施
  const layout = navData[floor] || []
  const hasObstacle = (x1, y1, x2, y2) => {
    for (const r of layout) {
      if (r.type === 'elevator' || r.type === 'parking' || r.type === 'open' || r.type === 'wc') continue
      if (Math.abs(y1 - y2) < 10) {
        const minX = Math.min(x1, x2), maxX = Math.max(x1, x2)
        if (y1 > r.y - 5 && y1 < r.y + r.h + 5 && maxX > r.x && minX < r.x + r.w) return true
      } else if (Math.abs(x1 - x2) < 10) {
        const minY = Math.min(y1, y2), maxY = Math.max(y1, y2)
        if (x1 > r.x - 5 && x1 < r.x + r.w + 5 && maxY > r.y && minY < r.y + r.h) return true
      }
    }
    return false
  }

  // 最短折线路径：先直走再拐弯，有障碍才绕主通道
  const canWalkVH = !hasObstacle(sx, sy, sx, ey) && !hasObstacle(sx, ey, ex, ey)
  const canWalkHV = !hasObstacle(sx, sy, ex, sy) && !hasObstacle(ex, sy, ex, ey)
  
  if (canWalkVH || canWalkHV) {
    if (canWalkVH && (!canWalkHV || Math.abs(dy) >= Math.abs(dx))) {
      if (Math.abs(dy) > 20) steps.push(`向${dirY}直行约${Math.round(Math.abs(dy) / 5)}米`)
      if (Math.abs(dx) > 20) steps.push(`向${dirX}直行约${Math.round(Math.abs(dx) / 5)}米`)
      parkingPath.value = [{ x: sx, y: sy }, { x: sx, y: ey }, { x: ex, y: ey }]
    } else {
      if (Math.abs(dx) > 20) steps.push(`向${dirX}直行约${Math.round(Math.abs(dx) / 5)}米`)
      if (Math.abs(dy) > 20) steps.push(`向${dirY}直行约${Math.round(Math.abs(dy) / 5)}米`)
      parkingPath.value = [{ x: sx, y: sy }, { x: ex, y: sy }, { x: ex, y: ey }]
    }
  } else {
    const tC = 144, bC = 900
    const sCY = Math.abs(sy - tC) < Math.abs(sy - bC) ? tC : bC
    const eCY = Math.abs(ey - tC) < Math.abs(ey - bC) ? tC : bC
    if (sy > tC + 20 && sy < bC - 20) steps.push(`向北走到主通道约${Math.round(Math.abs(sy - tC) / 5)}米`)
    if (sCY !== eCY) steps.push(`沿主通道向${dirX}直行约${Math.round(Math.abs(ex - sx) / 5)}米`)
    else { const d = ex - sx; if (Math.abs(d) > 60) steps.push(`沿主通道向${d > 0 ? '东' : '西'}直行约${Math.round(Math.abs(d) / 5)}米`) }
    if (ey > tC + 20 && ey < bC - 20) steps.push(`从主通道向${ey - eCY > 0 ? '南' : '北'}走约${Math.round(Math.abs(ey - eCY) / 5)}米`)
    parkingPath.value = [{ x: sx, y: sy }]
    if (Math.abs(sy - sCY) > 20) parkingPath.value.push({ x: sx, y: sCY })
    const midX = Math.round((sx + ex) / 2)
    if (sCY !== eCY) {
      parkingPath.value.push({ x: midX, y: sCY })
      parkingPath.value.push({ x: midX, y: eCY })
      parkingPath.value.push({ x: ex, y: eCY })
    } else {
      parkingPath.value.push({ x: ex, y: sCY })
    }
    if (Math.abs(ey - eCY) > 20) parkingPath.value.push({ x: ex, y: ey })
  }
  steps.push(`到达${room.name}`)
  routeSteps.value = steps
  activeStep.value = -1
}


// 停车导航路径线数据
const parkingPath = ref([])
// 高德风格导航动画：当前位置（沿路径移动的光标）
const navigatorPos = ref({ x: 0, y: 0 })
const navAnimProgress = ref(0) // 0-1 动画进度
let navAnimTimer = null

// 逐步导航
function startStepNav() {
  if (isNavigating.value) { stopNav(); return }
  if (!routeSteps.value.length) return
  isNavigating.value = true; activeStep.value = -1; stepByStep(0)
}

function stepByStep(i) {
  if (i >= routeSteps.value.length) {
    activeStep.value = i - 1
    const arr = ['到啦到啦，就是这儿！', '嘿，咱们到了！', '目的地到了哦～', '到了到了～']
    speakText(arr[Math.floor(Math.random() * arr.length)])
    setTimeout(() => { isNavigating.value = false }, 2500)
    return
  }
  activeStep.value = i
  let raw = routeSteps.value[i]
  let text = raw
    .replace(/向东/g, '往右手边').replace(/向西/g, '往左手边')
    .replace(/向南/g, '往前面').replace(/向北/g, '往后走')
    .replace(/直行约/g, '走大概').replace(/米/g, '米的样子')
    .replace(/从/g, '咱们从').replace(/出发/g, '出发哈')
    .replace(/到达/g, '就到了').replace(/主通道/g, '主走廊')
  const pf = ['好的，', '来，', '接下来，', '嗯，', '']
  text = (i === 0 ? '行，' : pf[Math.floor(Math.random() * pf.length)]) + text
  speakText(text)
  // 等语音播完再下一句——最大容错 30 秒
  navTimer = setTimeout(() => { stepByStep(i + 1) }, Math.max(3000, text.length * 250))
}

function speakText(text) {
  fetch('/api/tts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, voice: 'nova' })
  }).then(res => res.ok ? res.blob() : Promise.reject())
    .then(blob => {
      const a = new Audio(URL.createObjectURL(blob))
      a.play(); a.onended = () => URL.revokeObjectURL(a.src)
    })
    .catch(() => {
      if (!window.speechSynthesis) return
      window.speechSynthesis.cancel()
      const u = new SpeechSynthesisUtterance(text)
      u.lang = 'zh-CN'; u.rate = 0.95; u.pitch = 1.1
      window.speechSynthesis.speak(u)
    })
}

function stopNav() {
  isNavigating.value = false
  if (navTimer) { clearTimeout(navTimer); navTimer = null }
  if (navAnimTimer) { clearInterval(navAnimTimer); navAnimTimer = null }
  if (window.speechSynthesis) window.speechSynthesis.cancel()
}

// 高德风格导航动画：沿路径从0走到1，灰色变蓝色
function startNavAnim() {
  if (navAnimTimer) { clearInterval(navAnimTimer); navAnimTimer = null }
  if (!parkingPath.value.length) return
  
  const duration = 6000 // 6秒走完全程
  const fps = 30
  const frames = Math.ceil(duration * fps / 1000)
  let frame = 0
  
  navAnimProgress.value = 0
  
  navAnimTimer = setInterval(() => {
    frame++
    const progress = Math.min(1, frame / frames)
    navAnimProgress.value = progress
    if (progress >= 1) {
      clearInterval(navAnimTimer)
      navAnimTimer = null
    }
  }, 1000 / fps)
}

// SVG 渲染 - 高德地图风格
const svgContent = computed(() => {
  const rooms = navData[currentFloor.value] || []
  const tgt = selectedTarget.value?.f === currentFloor.value ? selectedTarget.value : null

  const cc = (type) => {
    const m = {
      cafe:       { fill:'#F0F0F0', stroke:'#BBBBBB', text:'#BBBBBB' },
      retail:     { fill:'#F0F0F0', stroke:'#BBBBBB', text:'#B0B0B0' },
      food:       { fill:'#F0F0F0', stroke:'#BBBBBB', text:'#C0C0C0' },
      service:    { fill:'#F0F0F0', stroke:'#BBBBBB', text:'#A8A8A8' },
      kids:       { fill:'#F0F0F0', stroke:'#BBBBBB', text:'#B8B8B8' },
      sport:      { fill:'#F0F0F0', stroke:'#BBBBBB', text:'#A0A0A0' },
      wc:         { fill:'#F0F0F0', stroke:'#BBBBBB', text:'#C8C8C8' },
      parking:    { fill:'#F0F0F0', stroke:'#BBBBBB', text:'#AEAEAE' },
      elevator:   { fill:'#F0F0F0', stroke:'#BBBBBB', text:'#B4B4B4' },
      classroom:  { fill:'#F0F0F0', stroke:'#BBBBBB', text:'#A8A8A8' },
      meeting:    { fill:'#F0F0F0', stroke:'#BBBBBB', text:'#B0B0B0' },
      cinema:     { fill:'#F0F0F0', stroke:'#BBBBBB', text:'#C0C0C0' },
      open:       { fill:'#F0F0F0', stroke:'#BBBBBB', text:'#A8A8A8' },
    }
    return m[type] || m.retail
  }

  const floorRooms = navData[currentFloor.value] || []
  const types = [...new Set(floorRooms.map(r => r.type))]

  let s = '<svg viewBox="0 0 1840 1060" width="100%" height="100%" style="display:block">'
  s += '<defs>'
  s += '<filter id="s1"><feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#000" flood-opacity=".08"/></filter>'
  s += '<filter id="s2"><feDropShadow dx="0" dy="4" stdDeviation="8" flood-color="#9E9E9E" flood-opacity=".35"/></filter>'

  for (const t of types) {
    const l = cc(t)
    s += '<linearGradient id="g-' + t + '" x1="0%" y1="0%" x2="100%" y2="100%">'
    s += '<stop offset="0%" stop-color="#222" stop-opacity=".55"/>'
    s += '<stop offset="40%" stop-color="' + l.fill + '" stop-opacity=".15"/>'
    s += '<stop offset="100%" stop-color="' + l.fill + '" stop-opacity=".08"/>'
    s += '</linearGradient>'
  }

  s += '<pattern id="hatch" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
  s += '<line x1="0" y1="0" x2="0" y2="10" stroke="#fff" stroke-width=".8" stroke-opacity=".025"/>'
  s += '</pattern>'
  s += '</defs>'

  s += '<rect width="1840" height="1060" fill="#1A1A1A" rx="0"/>'

  for (let gx = 0; gx <= 1840; gx += 60)
    s += '<line x1="' + gx + '" y1="0" x2="' + gx + '" y2="1060" stroke="#2E2E2E" stroke-width=".5" opacity=".35"/>'
  for (let gy = 0; gy <= 1060; gy += 60)
    s += '<line x1="0" y1="' + gy + '" x2="1840" y2="' + gy + '" stroke="#2E2E2E" stroke-width=".5" opacity=".35"/>'

  const cs = 'stroke="#444" stroke-width="3" stroke-dasharray="14 10" opacity=".55"'
  s += '<line x1="0" y1="144" x2="1840" y2="144" ' + cs + '/>'
  s += '<line x1="0" y1="900" x2="1840" y2="900" ' + cs + '/>'
  s += '<line x1="398" y1="144" x2="398" y2="900" ' + cs + '/>'
  s += '<line x1="814" y1="144" x2="814" y2="900" ' + cs + '/>'

  for (const r of floorRooms) {
    const isT = tgt && r.name === tgt.name && r.x === tgt.x
    if (r.type === 'elevator') continue
    const cl = cc(r.type)
    const base = userStore.largeFont ? 1.7 : 1
    const fs = (r.name.length > 6 ? 12 : 14) * base
    const rad = 10

    if (isT) {
      s += '<g filter="url(#s2)"><rect x="' + (r.x-4) + '" y="' + (r.y-4) + '" width="' + (r.w+8) + '" height="' + (r.h+8) + '" rx="14" fill="none" stroke="#9E9E9E" stroke-width="3.5" stroke-dasharray="10 6"/></g>'
      s += '<rect x="' + r.x + '" y="' + r.y + '" width="' + r.w + '" height="' + r.h + '" rx="' + rad + '" fill="url(#g-' + r.type + ')" stroke="#9E9E9E" stroke-width="3"/>'
      s += '<rect x="' + r.x + '" y="' + r.y + '" width="' + r.w + '" height="' + r.h + '" rx="' + rad + '" fill="url(#hatch)"/>'
      s += '<rect x="' + (r.x+r.w/2-45) + '" y="' + (r.y+r.h/2-13) + '" width="90" height="26" rx="7" fill="#9E9E9E" opacity=".92"/>'
      s += '<text x="' + (r.x+r.w/2) + '" y="' + (r.y+r.h/2+4) + '" text-anchor="middle" font-size="' + fs + '" font-weight="700" fill="#fff" font-family="-apple-system,PingFang SC,sans-serif">' + r.name + '</text>'
      s += '<circle cx="' + (r.x+r.w/2) + '" cy="' + (r.y+r.h+16) + '" r="8" fill="#9E9E9E"/><circle cx="' + (r.x+r.w/2) + '" cy="' + (r.y+r.h+16) + '" r="3" fill="#fff"/>'
    } else {
      s += '<rect x="' + r.x + '" y="' + r.y + '" width="' + r.w + '" height="' + r.h + '" rx="' + rad + '" fill="url(#g-' + r.type + ')" stroke="' + cl.stroke + '" stroke-width="1.2" filter="url(#s1)"/>'
      s += '<rect x="' + r.x + '" y="' + r.y + '" width="' + r.w + '" height="' + r.h + '" rx="' + rad + '" fill="url(#hatch)"/>'
      s += '<text x="' + (r.x+r.w/2) + '" y="' + (r.y+r.h/2+3) + '" text-anchor="middle" font-size="' + fs + '" font-weight="600" fill="' + cl.text + '" font-family="-apple-system,PingFang SC,sans-serif">' + r.name + '</text>'
    }
  }

  for (const r of floorRooms) {
    if (r.type !== 'elevator') continue
    const cl = cc('elevator')
    s += '<rect x="' + r.x + '" y="' + r.y + '" width="' + r.w + '" height="' + r.h + '" rx="7" fill="url(#g-elevator)" stroke="' + cl.stroke + '" stroke-width="1.5" filter="url(#s1)"/>'
    s += '<text x="' + (r.x+r.w/2) + '" y="' + (r.y+r.h/2+5) + '" text-anchor="middle" font-size="' + (18 * (userStore.largeFont ? 1.7 : 1)) + '" fill="' + cl.text + '">⬍</text>'
  }

  // 车位网格渲染（仅在1F且停车场区域可见时）
  s += `<g transform="translate(0,0)">`
  for (const spot of parkingSpots) {
    const spotW = 35, spotH = 22
    s += `<rect x="${spot.x}" y="${spot.y}" width="${spotW}" height="${spotH}" rx="3" fill="rgba(255,255,255,0.06)" stroke="#444" stroke-width="1"/>`
    // 车位编号
    s += `<text x="${spot.x + spotW/2}" y="${spot.y + spotH/2 + 3}" text-anchor="middle" font-size="7" font-weight="500" fill="#666" font-family="monospace">${spot.id}</text>`
  }
  s += `</g>`

  // 停车导航路径线（高德风格：已走蓝线，未走灰线，光标在动态切割点）
  if (parkingPath.value.length >= 2) {
    const pts = parkingPath.value
    const segs = []
    let totalLen = 0
    for (let i = 1; i < pts.length; i++) {
      const d = Math.hypot(pts[i].x - pts[i-1].x, pts[i].y - pts[i-1].y)
      segs.push({ a: pts[i-1], b: pts[i], len: d, acc: totalLen })
      totalLen += d
    }
    const cutoff = navAnimProgress.value * totalLen
    let walkedD = ''
    let remainD = ''
    let cutoffPt = null
    for (const seg of segs) {
      if (cutoff >= seg.acc + seg.len) {
        if (!walkedD) walkedD += `M${seg.a.x},${seg.a.y}`
        walkedD += ` L${seg.b.x},${seg.b.y}`
      } else if (cutoff <= seg.acc) {
        if (!remainD) remainD += `M${seg.a.x},${seg.a.y}`
        remainD += ` L${seg.b.x},${seg.b.y}`
      } else {
        const t = seg.len > 0 ? (cutoff - seg.acc) / seg.len : 0
        const cx = seg.a.x + (seg.b.x - seg.a.x) * t
        const cy = seg.a.y + (seg.b.y - seg.a.y) * t
        cutoffPt = { x: cx, y: cy }
        if (!walkedD) walkedD += `M${seg.a.x},${seg.a.y}`
        walkedD += ` L${cx},${cy}`
        remainD += `M${cx},${cy} L${seg.b.x},${seg.b.y}`
      }
    }
    if (remainD) {
      s += '<path d="' + remainD + '" fill="none" stroke="#D1D5DB" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" opacity="0.6"/>'
    }
    if (walkedD) {
      s += '<path d="' + walkedD + '" fill="none" stroke="#BBBBBB" stroke-width="9" stroke-linecap="round" stroke-linejoin="round" opacity="0.1"/>'
      s += '<path d="' + walkedD + '" fill="none" stroke="#BBBBBB" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" opacity="0.9"/>'
    }
    const sp = pts[0]
    s += `<circle cx="${sp.x}" cy="${sp.y}" r="11" fill="#BBBBBB" stroke="#fff" stroke-width="2.5"/>`
    s += `<circle cx="${sp.x}" cy="${sp.y}" r="4" fill="#fff"/>`
    s += `<text x="${sp.x}" y="${sp.y - 18}" text-anchor="middle" font-size="11" font-weight="700" fill="#BBBBBB">起点</text>`
    const ep = pts[pts.length - 1]
    const nearestSpot = parkingSpots.reduce((best, s) => {
      const d = Math.hypot(s.x + 17.5 - ep.x, s.y + 11 - ep.y)
      return d < best.d ? { spot: s, d } : best
    }, { spot: null, d: Infinity })
    s += `<path d="M${ep.x},${ep.y - 14} Q${ep.x},${ep.y + 6} ${ep.x - 10},${ep.y + 4} Q${ep.x},${ep.y + 14} ${ep.x},${ep.y + 14} Q${ep.x},${ep.y + 14} ${ep.x + 10},${ep.y + 4} Q${ep.x},${ep.y + 6} ${ep.x},${ep.y - 14} Z" fill="#4A4A4A" stroke="#fff" stroke-width="2"><animate attributeName="opacity" values="0.85;1;0.85" dur="0.8s" repeatCount="indefinite"/></path>`
    s += `<circle cx="${ep.x}" cy="${ep.y - 2}" r="4" fill="#fff"/>`
    const spotLabel = nearestSpot.spot ? nearestSpot.spot.id : '车位'
    s += `<text x="${ep.x}" y="${ep.y + 28}" text-anchor="middle" font-size="11" font-weight="700" fill="#F0F0F0">${spotLabel}</text>`
    if (cutoffPt && cutoffPt.x > 0) {
      const np = cutoffPt
      s += `<circle cx="${np.x}" cy="${np.y}" r="16" fill="#BBBBBB" opacity="0.08"><animate attributeName="r" values="14;22;14" dur="2s" repeatCount="indefinite"/></circle>`
      s += `<circle cx="${np.x}" cy="${np.y}" r="12" fill="#BBBBBB" opacity="0.15"><animate attributeName="r" values="10;16;10" dur="1.5s" repeatCount="indefinite"/></circle>`
      s += `<circle cx="${np.x}" cy="${np.y}" r="8" fill="#BBBBBB" stroke="#fff" stroke-width="2"/>`
      s += `<polygon points="${np.x},${np.y - 9} ${np.x - 5},${np.y - 1} ${np.x + 5},${np.y - 1}" fill="#fff"/>`
      s += `<circle cx="${np.x}" cy="${np.y}" r="6" fill="none" stroke="#BBBBBB" stroke-width="2" opacity="0.6"><animate attributeName="r" values="6;18" dur="1s" repeatCount="indefinite"/><animate attributeName="opacity" values="0.6;0" dur="1s" repeatCount="indefinite"/></circle>`
    }
  }

  s += '</svg>'
  return s
})</script>

<style scoped>
.nav-page {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  z-index: 9999;
  background: #1A1A1A !important;
  display: flex;
  flex-direction: column;
  font-family: -apple-system, 'PingFang SC', 'SF Pro Display', sans-serif;
}

/* 确保地图区域有背景 */
.nav-map-wrap {
  background: #1A1A1A;
}

/* 顶部栏 */
.nav-top {
  background: rgba(26,26,26,0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 0.5px solid #333;
  flex-shrink: 0;
}
.nav-top-inner {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 12px 10px;
}
.nav-top h2 {
  font-size: 17px; font-weight: 700; color: #F0F0F0; margin: 0;
  letter-spacing: -0.2px;
}

/* iOS 分段控制器 */
.nav-segmented {
  padding: 0 16px 8px; flex-shrink: 0;
  background: rgba(26,26,26,0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}
.seg-track {
  display: flex; position: relative;
  background: #1A1A1A; border-radius: 10px; padding: 2px;
  box-shadow: inset 0 2px 5px rgba(0,0,0,0.5), inset 0 -1px 2px rgba(255,255,255,0.06);
}
.seg-bg {
  position: absolute; top: 2px; bottom: 2px;
  background: #333; border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,.3), 0 0 0 0.5px rgba(0,0,0,.2);
  transition: transform .25s cubic-bezier(.4,0,.2,1);
}
.seg-btn {
  flex: 1; position: relative; z-index: 1;
  padding: 8px 0; border: none; background: none;
  font-size: 14px; font-weight: 600; cursor: pointer;
  color: #BBBBBB; transition: color .15s;
  font-family: inherit;
}
.seg-btn.active { color: #F0F0F0; }

/* 搜索框 */
.nav-search-wrap {
  padding: 0 16px 12px; flex-shrink: 0;
  background: rgba(26,26,26,0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  position: relative; z-index: 10;
}
.nav-search-inner {
  display: flex; align-items: center; gap: 8px;
  background: #1A1A1A; border-radius: 10px;
  padding: 0 8px; height: 36px;
  transition: background .2s;
  box-shadow: inset 0 2px 5px rgba(0,0,0,0.5), inset 0 -1px 2px rgba(255,255,255,0.06);
}
.nav-search-inner:focus-within {
  background: #1A1A1A;
}
.search-icon { flex-shrink: 0; }
.nav-search-inner input {
  flex: 1; border: none; background: none;
  font-size: 15px; outline: none; color: #F0F0F0;
  font-family: inherit;
}
.nav-search-inner input::placeholder { color: #BBBBBB; }
.search-clear {
  width: 20px; height: 20px; border: none; border-radius: 50%;
  background: #1A1A1A; color: #fff; font-size: 10px;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.search-drop {
  position: absolute; left: 16px; right: 16px; top: 54px;
  background: #222222; border-radius: 14px;
  box-shadow: 0 8px 32px rgba(0,0,0,.4);
  max-height: 200px; overflow-y: auto; z-index: 20;
}
.search-item {
  padding: 12px 16px; font-size: 15px; cursor: pointer;
  border-bottom: 0.5px solid #2E2E2E; color: #F0F0F0;
}
.search-item:active { background: #1A1A1A; }
.search-floor { color: #BBBBBB; font-size: 13px; }

/* 路线卡片 */
.route-card {
  margin: 8px 16px; background: #222222; border-radius: 10px;
  overflow: hidden; flex-shrink: 0;
}
.route-card-top {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; background: #222222; border-bottom: 0.5px solid #333;
}
.route-title { font-size: 16px; font-weight: 500; color: #F0F0F0; }
.route-play {
  display: flex; align-items: center; gap: 4px; border: none;
  background: #1A1A1A; color: #FFFFFF; font-size: 13px; font-weight: 500;
  padding: 6px 14px; border-radius: 999px; cursor: pointer; font-family: inherit;
}
.route-steps { padding: 4px 0; }
.route-step {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 14px; font-size: 14px; color: rgba(255,255,255,0.3); transition: all .3s;
}
.route-step--active { color: #999999; font-weight: 500; background: #1A1A1A; }
.route-step--done { color: #BBBBBB; }
.step-dot {
  width: 22px; height: 22px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 600; flex-shrink: 0;
  background: #2A2A2A; color: rgba(255,255,255,0.3); transition: all .3s;
}
.route-step--active .step-dot { background: #1A1A1A; color: #FFFFFF; }
.route-step--done .step-dot { background: #8A8A8A; color: #FFFFFF; }

/* 地图 */
.nav-map-wrap {
  flex: 1; overflow: auto; -webkit-overflow-scrolling: touch;
  padding: 8px 0 20px;
  cursor: grab;
  user-select: none;
  -webkit-user-select: none;
  position: relative;
  background: #1A1A1A;
}
.nav-map-wrap::-webkit-scrollbar { display: none; }
.nav-map-wrap { -ms-overflow-style: none; scrollbar-width: none; }
.nav-map {
  min-width: 920px;
}
.nav-map :deep(svg) {
  min-width: 920px;
  width: 100%;
  height: auto;
}

/* 缩放控件（固定右下角） */
.zoom-controls {
  position: fixed;
  bottom: 28px;
  right: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  z-index: 10;
}
.zoom-btn {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  border: 1px solid #444;
  background: rgba(34,34,34,.92);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0,0,0,.3);
  transition: all .2s;
}
.zoom-btn:active {
  background: #2A2A2A;
  transform: scale(.92);
}
.zoom-level {
  font-size: 11px;
  font-weight: 600;
  color: #999;
  padding: 2px 6px;
  border-radius: 6px;
  background: rgba(34,34,34,.85);
  backdrop-filter: blur(10px);
}
</style>
