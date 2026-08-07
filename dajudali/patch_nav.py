# Script to patch NavView.vue: replace 3D SVG rendering with Gaode-style 2D + pinch zoom
import re

with open('daju-neighbor-vue/src/views/c-end/NavView.vue', 'r', encoding='utf-8') as f:
    content = f.read()

# === Part 1: Replace svgContent computed ===
old_svg_start = '// SVG 渲染 - 3D等距风格'
old_svg_end = "// 3D房间绘制"

new_svg = '''// SVG 渲染 - 高德地图风格（2D俯视 + 渐变纹理 + 阴影）
const svgContent = computed(() => {
  const rooms = navData[currentFloor.value] || []
  const tgt = selectedTarget.value?.f === currentFloor.value ? selectedTarget.value : null

  const cc = (type) => {
    const m = {
      cafe:       { fill:'#E8F5E9', stroke:'#66BB6A', text:'#2E7D32', icon:'\\u2615' },
      retail:     { fill:'#FFF8E1', stroke:'#FFB300', text:'#F57F17' },
      food:       { fill:'#FFF3E0', stroke:'#FF8A65', text:'#E65100' },
      service:    { fill:'#F3E5F5', stroke:'#BA68C8', text:'#6A1B9A' },
      kids:       { fill:'#FCE4EC', stroke:'#F06292', text:'#AD1457' },
      sport:      { fill:'#E0F7FA', stroke:'#4DD0E1', text:'#00838F' },
      wc:         { fill:'#ECEFF1', stroke:'#90A4AE', text:'#546E7A' },
      parking:    { fill:'#E8EAF6', stroke:'#7986CB', text:'#283593' },
      elevator:   { fill:'#EFEBE9', stroke:'#A1887F', text:'#4E342E' },
      classroom:  { fill:'#E3F2FD', stroke:'#64B5F6', text:'#1565C0' },
      meeting:    { fill:'#E0F2F1', stroke:'#80CBC4', text:'#00695C' },
      cinema:     { fill:'#FBE9E7', stroke:'#FF8A65', text:'#BF360C' },
      open:       { fill:'#F1F8E9', stroke:'#AED581', text:'#33691E' },
    }
    return m[type] || m.retail
  }

  const floorRooms = navData[currentFloor.value] || []
  // Find all types in current floor
  const types = [...new Set(floorRooms.map(r => r.type))]

  let s = `<svg viewBox="0 0 1840 1060" width="100%" height="100%" style="display:block">`
  s += `<defs>`
  s += `<filter id="s1"><feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#000" flood-opacity=".08"/></filter>`
  s += `<filter id="s2"><feDropShadow dx="0" dy="4" stdDeviation="8" flood-color="#FF8C00" flood-opacity=".35"/></filter>`

  // LinearGradient per type
  for (const t of types) {
    const l = cc(t)
    s += `<linearGradient id="g-${t}" x1="0%" y1="0%" x2="100%" y2="100%">`
    s += `<stop offset="0%" stop-color="#fff" stop-opacity=".55"/>`
    s += `<stop offset="40%" stop-color="${l.fill}" stop-opacity=".95"/>`
    s += `<stop offset="100%" stop-color="${l.fill}" stop-opacity=".6"/>`
    s += `</linearGradient>`
  }

  // Hatch texture
  s += `<pattern id="hatch" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">`
  s += `<line x1="0" y1="0" x2="0" y2="10" stroke="#000" stroke-width=".8" stroke-opacity=".025"/>`
  s += `</pattern>`
  s += `</defs>`

  // Ground
  s += `<rect width="1840" height="1060" fill="#F2F0EA" rx="0"/>`

  // Grid (light)
  for (let gx = 0; gx <= 1840; gx += 60)
    s += `<line x1="${gx}" y1="0" x2="${gx}" y2="1060" stroke="#D8D4CC" stroke-width=".5" opacity=".35"/>`
  for (let gy = 0; gy <= 1060; gy += 60)
    s += `<line x1="0" y1="${gy}" x2="1840" y2="${gy}" stroke="#D8D4CC" stroke-width=".5" opacity=".35"/>`

  // Corridors
  const cs = `stroke="#C0BAAE" stroke-width="3" stroke-dasharray="14 10" opacity=".55"`
  s += `<line x1="0" y1="144" x2="1840" y2="144" ${cs}/>`
  s += `<line x1="0" y1="900" x2="1840" y2="900" ${cs}/>`
  s += `<line x1="398" y1="144" x2="398" y2="900" ${cs}/>`
  s += `<line x1="814" y1="144" x2="814" y2="900" ${cs}/>`

  // Rooms
  for (const r of floorRooms) {
    const isT = tgt && r.name === tgt.name && r.x === tgt.x
    if (r.type === 'elevator') continue
    const c = cc(r.type)
    const fs = r.name.length > 6 ? 12 : 14
    const rad = 10

    if (isT) {
      s += `<g filter="url(#s2)"><rect x="${r.x-4}" y="${r.y-4}" width="${r.w+8}" height="${r.h+8}" rx="14" fill="none" stroke="#FF8C00" stroke-width="3.5" stroke-dasharray="10 6"/></g>`
      s += `<rect x="${r.x}" y="${r.y}" width="${r.w}" height="${r.h}" rx="${rad}" fill="url(#g-${r.type})" stroke="#FF8C00" stroke-width="3"/>`
      s += `<rect x="${r.x}" y="${r.y}" width="${r.w}" height="${r.h}" rx="${rad}" fill="url(#hatch)"/>`
      // Label badge
      s += `<rect x="${r.x+r.w/2-45}" y="${r.y+r.h/2-13}" width="90" height="26" rx="7" fill="#FF8C00" opacity=".92"/>`
      s += `<text x="${r.x+r.w/2}" y="${r.y+r.h/2+4}" text-anchor="middle" font-size="${fs}" font-weight="700" fill="#fff" font-family="-apple-system,PingFang SC,sans-serif">${r.name}</text>`
      // Pin
      s += `<circle cx="${r.x+r.w/2}" cy="${r.y+r.h+16}" r="8" fill="#FF8C00"/><circle cx="${r.x+r.w/2}" cy="${r.y+r.h+16}" r="3" fill="#fff"/>`
    } else {
      s += `<rect x="${r.x}" y="${r.y}" width="${r.w}" height="${r.h}" rx="${rad}" fill="url(#g-${r.type})" stroke="${c.stroke}" stroke-width="1.2" filter="url(#s1)"/>`
      s += `<rect x="${r.x}" y="${r.y}" width="${r.w}" height="${r.h}" rx="${rad}" fill="url(#hatch)"/>`
      s += `<text x="${r.x+r.w/2}" y="${r.y+r.h/2+3}" text-anchor="middle" font-size="${fs}" font-weight="600" fill="${c.text}" font-family="-apple-system,PingFang SC,sans-serif">${r.name}</text>`
    }
  }

  // Elevators
  for (const r of floorRooms) {
    if (r.type !== 'elevator') continue
    const c = cc('elevator')
    s += `<rect x="${r.x}" y="${r.y}" width="${r.w}" height="${r.h}" rx="7" fill="url(#g-elevator)" stroke="${c.stroke}" stroke-width="1.5" filter="url(#s1)"/>`
    s += `<text x="${r.x+r.w/2}" y="${r.y+r.h/2+5}" text-anchor="middle" font-size="18" fill="${c.text}">\\u2b0d</text>`
  }

  s += `</svg>`
  return s
})
'''

idx_start = content.find(old_svg_start)
idx_end = content.find(old_svg_end, idx_start)
if idx_start < 0 or idx_end < 0:
    print("ERROR: could not find old SVG block")
    exit(1)
# Extend to remove everything up to '</script>' (including old functions)
content = content[:idx_start] + new_svg

# Find the next '</script>' after our insert and trim old code
script_end = content.find('</script>', idx_start + len(new_svg))
content = content[:script_end] + '\n</script>' + content[content.find('<style scoped>', script_end):]

# === Part 2: Add scale ref and pinch zoom to drag handlers ===
# Add scale ref after dragState
old_drag = 'let navTimer = null'
new_zoom = '''let navTimer = null
const mapScale = ref(1)

// Pinch zoom
function onWheel(e) {
  e.preventDefault()
  const delta = e.deltaY > 0 ? -0.1 : 0.1
  mapScale.value = Math.max(0.5, Math.min(3, mapScale.value + delta))
}'''

content = content.replace(old_drag, new_zoom)

# Update onDragStart to store pinch info
old_start = 'function onDragStart(e) {\n  const el = mapWrap.value\n  if (!el) return\n  dragState.active = true\n  dragState.startX = (e.touches ? e.touches[0].clientX : e.clientX)\n  dragState.startY = (e.touches ? e.touches[0].clientY : e.clientY)'
new_start = '''function onDragStart(e) {
  const el = mapWrap.value
  if (!el) return
  if (e.touches && e.touches.length === 2) {
    // Pinch start - record distance
    dragState.pinchStart = Math.hypot(
      e.touches[0].clientX - e.touches[1].clientX,
      e.touches[0].clientY - e.touches[1].clientY
    )
    dragState.pinchScale = mapScale.value
    return
  }
  dragState.active = true
  dragState.startX = (e.touches ? e.touches[0].clientX : e.clientX)
  dragState.startY = (e.touches ? e.touches[0].clientY : e.clientY)'''

content = content.replace(old_start, new_start)

# Add pinch move
old_move = 'function onDragMove(e) {\n  if (!dragState.active) return'
new_move = '''function onDragMove(e) {
  // Pinch zoom
  if (e.touches && e.touches.length === 2 && dragState.pinchStart !== undefined) {
    e.preventDefault()
    const dist = Math.hypot(
      e.touches[0].clientX - e.touches[1].clientX,
      e.touches[0].clientY - e.touches[1].clientY
    )
    const newScale = dragState.pinchScale * (dist / dragState.pinchStart)
    mapScale.value = Math.max(0.5, Math.min(3, newScale))
    return
  }
  if (!dragState.active) return'''

content = content.replace(old_move, new_move)

# Update onDragEnd to clear pinch state
old_end = 'function onDragEnd() {\n  dragState.active = false\n  if (mapWrap.value) mapWrap.value.style.cursor = \'grab\'\n}'
new_end = '''function onDragEnd() {
  dragState.active = false
  dragState.pinchStart = undefined
  if (mapWrap.value) mapWrap.value.style.cursor = 'grab'
}'''
content = content.replace(old_end, new_end)

# === Part 3: Update map template to use scale ===
old_map_div = '<div class="nav-map" v-html="svgContent" @click="onMapClick"></div>'
new_map_div = '''<div class="nav-map" v-html="svgContent" @click="onMapClick" :style="{ transform: `scale(${mapScale})`, transformOrigin: '0 0', transition: mapScale === 1 ? 'none' : 'transform .1s' }"></div>'''
content = content.replace(old_map_div, new_map_div)

# === Part 4: Update CSS - hide scrollbar, adjust map ===
# Replace nav-map-wrap and nav-map styles
old_css = '''/* 地图 */
.nav-map-wrap {
  flex: 1; overflow: auto; -webkit-overflow-scrolling: touch;
  padding: 8px 0 20px;
  cursor: grab;
  user-select: none;
  -webkit-user-select: none;
}
.nav-map :deep(svg) {
  min-width: 920px;
  width: 100%;
  height: auto;
}'''

new_css = '''/* 地图 */
.nav-map-wrap {
  flex: 1; overflow: auto; -webkit-overflow-scrolling: touch;
  padding: 8px 0 20px;
  cursor: grab;
  user-select: none;
  -webkit-user-select: none;
}
.nav-map-wrap::-webkit-scrollbar { display: none; }
.nav-map-wrap { -ms-overflow-style: none; scrollbar-width: none; }
.nav-map {
  min-width: 920px;
  min-height: 540px;
}
.nav-map :deep(svg) {
  min-width: 920px;
  width: 100%;
  height: auto;
}'''

content = content.replace(old_css, new_css)

# Add wheel event to mapWrap in template (in the div attrs)
old_wheel = '@touchend="onDragEnd"'
new_wheel = '@touchend="onDragEnd"\n      @wheel.prevent="onWheel"'
content = content.replace(old_wheel, new_wheel)

with open('daju-neighbor-vue/src/views/c-end/NavView.vue', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patched successfully")
