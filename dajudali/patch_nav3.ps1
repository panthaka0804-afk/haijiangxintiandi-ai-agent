$f = "C:\Users\admin\AppData\Roaming\OpenClawBrowser\openclaw-gateway\.openclaw\workspace\dajudali\daju-neighbor-vue\src\views\c-end\NavView.vue"
$c = [System.IO.File]::ReadAllText($f, [System.Text.Encoding]::UTF8)

# 1. Add mapScale ref
$c = $c.Replace('let navTimer = null', "let navTimer = null`r`nconst mapScale = ref(1)")

# 2. Add wheel handler in template
$c = $c.Replace('@touchend="onDragEnd"', '@touchend="onDragEnd"`r`n      @wheel.prevent="onWheel"')

# 3. Add scale style to map div  
$oldDiv = '<div class="nav-map" v-html="svgContent" @click="onMapClick"></div>'
$newDiv = '<div class="nav-map" v-html="svgContent" @click="onMapClick" :style="{ transform: `scale(${mapScale})`, transformOrigin: ''0 0'' }"></div>'
$c = $c.Replace($oldDiv, $newDiv)

# 4. Add onWheel function
$c = $c.Replace('function onDragEnd() {', "function onWheel(e) { mapScale.value = Math.max(0.5, Math.min(3, mapScale.value + (e.deltaY > 0 ? -0.1 : 0.1))) }`r`nfunction onDragEnd() {")

# 5. Add pinch zoom
if ($c -notmatch 'pinchDist') {
    $oldStart = "dragState.active = true`r`n  dragState.startX = (e.touches ? e.touches[0].clientX : e.clientX)"
    $newStart = "if (e.touches && e.touches.length === 2) { dragState.pinchDist = Math.hypot(e.touches[0].clientX-e.touches[1].clientX, e.touches[0].clientY-e.touches[1].clientY); dragState.pinchBase = mapScale.value; return }`r`n  dragState.active = true`r`n  dragState.startX = (e.touches ? e.touches[0].clientX : e.clientX)"
    $c = $c.Replace($oldStart, $newStart)
    
    $oldMove = "if (!dragState.active) return"
    $newMove = "if (e.touches && e.touches.length === 2 && dragState.pinchDist) { e.preventDefault(); const d=Math.hypot(e.touches[0].clientX-e.touches[1].clientX, e.touches[0].clientY-e.touches[1].clientY); mapScale.value=Math.max(.5, Math.min(3, dragState.pinchBase*(d/dragState.pinchDist))); return }`r`n  if (!dragState.active) return"
    $c = $c.Replace($oldMove, $newMove)
    
    $oldEnd = "dragState.active = false"
    $newEnd = "dragState.active = false`r`n  dragState.pinchDist = undefined"
    $c = $c.Replace($oldEnd, $newEnd)
}

# 6. Hide scrollbars
$oldCss = ".nav-map-wrap {`r`n  flex: 1; overflow: auto; -webkit-overflow-scrolling: touch;`r`n  padding: 8px 0 20px;`r`n  cursor: grab;`r`n  user-select: none;`r`n  -webkit-user-select: none;`r`n}"
$newCss = ".nav-map-wrap {`r`n  flex: 1; overflow: auto; -webkit-overflow-scrolling: touch;`r`n  padding: 8px 0 20px;`r`n  cursor: grab;`r`n  user-select: none;`r`n  -webkit-user-select: none;`r`n}`r`n.nav-map-wrap::-webkit-scrollbar { display: none; }`r`n.nav-map-wrap { -ms-overflow-style: none; scrollbar-width: none; }"
$c = $c.Replace($oldCss, $newCss)

[System.IO.File]::WriteAllText($f, $c, [System.Text.Encoding]::UTF8)
Write-Host "patched OK $($c.Length)"