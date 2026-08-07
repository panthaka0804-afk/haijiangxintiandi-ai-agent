import re

with open('daju-neighbor-vue/src/views/c-end/NavView.vue', 'r', encoding='utf-8') as f:
    content = f.read()

old_svg_start = '// SVG \u6e32\u67d3 - 3D\u7b49\u8ddd\u98ce\u683c'
# Find next </script> after svgContent
idx_start = content.find(old_svg_start)
if idx_start < 0:
    print("ERROR: old SVG start not found")
    exit(1)

# Find the end of the old svgContent block - it ends with a closing })

# Actually just find the 'const svgContent' and replace until end of its function

# ======= NEW SVG ======= 
new_svg = '''// SVG \u6e32\u67d3 - \u9ad8\u5fb7\u5730\u56fe\u98ce\u683c
const svgContent = computed(() => {
  const rooms = navData[currentFloor.value] || []
  const tgt = selectedTarget.value?.f === currentFloor.value ? selectedTarget.value : null

  const cc = (type) => {
    const m = {
      cafe:       { fill:'#E8F5E9', stroke:'#66BB6A', text:'#2E7D32' },
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
  const types = [...new Set(floorRooms.map(r => r.type))]

  let s = '<svg viewBox="0 0 1840 1060" width="100%" height="100%" style="display:block">'
  s += '<defs>'
  s += '<filter id="s1"><feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#000" flood-opacity=".08"/></filter>'
  s += '<filter id="s2"><feDropShadow dx="0" dy="4" stdDeviation="8" flood-color="#FF8C00" flood-opacity=".35"/></filter>'

  for (const t of types) {
    const l = cc(t)
    s += '<linearGradient id="g-' + t + '" x1="0%" y1="0%" x2="100%" y2="100%">'
    s += '<stop offset="0%" stop-color="#fff" stop-opacity=".55"/>'
    s += '<stop offset="40%" stop-color="' + l.fill + '" stop-opacity=".95"/>'
    s += '<stop offset="100%" stop-color="' + l.fill + '" stop-opacity=".6"/>'
    s += '</linearGradient>'
  }

  s += '<pattern id="hatch" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
  s += '<line x1="0" y1="0" x2="0" y2="10" stroke="#000" stroke-width=".8" stroke-opacity=".025"/>'
  s += '</pattern>'
  s += '</defs>'

  s += '<rect width="1840" height="1060" fill="#F2F0EA" rx="0"/>'

  for (let gx = 0; gx <= 1840; gx += 60)
    s += '<line x1="' + gx + '" y1="0" x2="' + gx + '" y2="1060" stroke="#D8D4CC" stroke-width=".5" opacity=".35"/>'
  for (let gy = 0; gy <= 1060; gy += 60)
    s += '<line x1="0" y1="' + gy + '" x2="1840" y2="' + gy + '" stroke="#D8D4CC" stroke-width=".5" opacity=".35"/>'

  const cs = 'stroke="#C0BAAE" stroke-width="3" stroke-dasharray="14 10" opacity=".55"'
  s += '<line x1="0" y1="144" x2="1840" y2="144" ' + cs + '/>'
  s += '<line x1="0" y1="900" x2="1840" y2="900" ' + cs + '/>'
  s += '<line x1="398" y1="144" x2="398" y2="900" ' + cs + '/>'
  s += '<line x1="814" y1="144" x2="814" y2="900" ' + cs + '/>'

  for (const r of floorRooms) {
    const isT = tgt && r.name === tgt.name && r.x === tgt.x
    if (r.type === 'elevator') continue
    const cl = cc(r.type)
    const fs = r.name.length > 6 ? 12 : 14
    const rad = 10

    if (isT) {
      s += '<g filter="url(#s2)"><rect x="' + (r.x-4) + '" y="' + (r.y-4) + '" width="' + (r.w+8) + '" height="' + (r.h+8) + '" rx="14" fill="none" stroke="#FF8C00" stroke-width="3.5" stroke-dasharray="10 6"/></g>'
      s += '<rect x="' + r.x + '" y="' + r.y + '" width="' + r.w + '" height="' + r.h + '" rx="' + rad + '" fill="url(#g-' + r.type + ')" stroke="#FF8C00" stroke-width="3"/>'
      s += '<rect x="' + r.x + '" y="' + r.y + '" width="' + r.w + '" height="' + r.h + '" rx="' + rad + '" fill="url(#hatch)"/>'
      s += '<rect x="' + (r.x+r.w/2-45) + '" y="' + (r.y+r.h/2-13) + '" width="90" height="26" rx="7" fill="#FF8C00" opacity=".92"/>'
      s += '<text x="' + (r.x+r.w/2) + '" y="' + (r.y+r.h/2+4) + '" text-anchor="middle" font-size="' + fs + '" font-weight="700" fill="#fff" font-family="-apple-system,PingFang SC,sans-serif">' + r.name + '</text>'
      s += '<circle cx="' + (r.x+r.w/2) + '" cy="' + (r.y+r.h+16) + '" r="8" fill="#FF8C00"/><circle cx="' + (r.x+r.w/2) + '" cy="' + (r.y+r.h+16) + '" r="3" fill="#fff"/>'
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
    s += '<text x="' + (r.x+r.w/2) + '" y="' + (r.y+r.h/2+5) + '" text-anchor="middle" font-size="18" fill="' + cl.text + '">\u2b0d</text>'
  }

  s += '</svg>'
  return s
})'''

# Replace from idx_start to first occurrence of '})' after the old block that ends the computed
# Find the computed's closing
# Old block ends with something like:
#   s += '</svg>'
#   return s
# })
# But there might be old extra functions. Find '</script>' after idx_start
script_end = content.find('</script>', idx_start)
# But we need to keep everything from before svgContent
# The old svgContent is from idx_start to some closing }) before other functions

# Find where the svgContent computed ends. Look for pattern:
#   s += '</svg>'
#   return s
# })
idx_svg_end = content.find("s += '</svg>'\n  return s\n})", idx_start)
if idx_svg_end < 0:
    # try without spaces
    idx_svg_end = content.find("s += `</svg>`\n  return s\n})", idx_start)
if idx_svg_end < 0:
    idx_svg_end = content.find("  return s\n})\n\n", idx_start)
if idx_svg_end < 0:
    # broader search
    m = re.search(r"return s\s*\n\s*\}\)", content[idx_start:])
    if m:
        idx_svg_end = idx_start + m.end()
        
if idx_svg_end < 0:
    print("ERROR: could not find end of svgContent")
    exit(1)

# Remove ALL old code from idx_start to script_end (including orphan functions)
content = content[:idx_start] + new_svg + content[script_end:]

with open('daju-neighbor-vue/src/views/c-end/NavView.vue', 'w', encoding='utf-8') as f:
    f.write(content)

print("SVG block replaced OK")
