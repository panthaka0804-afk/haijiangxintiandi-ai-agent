// 无依赖导出工具：CSV（可被 Excel / WPS 直接打开）与打印 PDF 报表
// 不引入任何第三方库，纯浏览器 API 实现。

function downloadBlob(content, filename, mime) {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  // 延迟回收，避免某些浏览器还没开始下载就被回收
  setTimeout(() => URL.revokeObjectURL(url), 1500)
}

function csvEscape(v) {
  const s = v == null ? '' : String(v)
  if (/[",\n\r]/.test(s)) return '"' + s.replace(/"/g, '""') + '"'
  return s
}

/**
 * 导出 CSV。
 * @param {Array<Object>} rows 数据行
 * @param {string} filename 文件名（含 .csv）
 * @param {Array<{key:string, title:string}>} [columns] 列定义；缺省取首行 key
 * @returns {boolean} 是否成功（有数据）
 */
export function exportCsv(rows, filename, columns) {
  if (!rows || !rows.length) return false
  const cols = columns || Object.keys(rows[0]).map((k) => ({ key: k, title: k }))
  const head = cols.map((c) => csvEscape(c.title)).join(',')
  const body = rows
    .map((r) => cols.map((c) => csvEscape(r[c.key])).join(','))
    .join('\r\n')
  // 前置 BOM，确保 Excel 正确识别 UTF-8 中文
  downloadBlob('﻿' + head + '\r\n' + body, filename, 'text/csv;charset=utf-8')
  return true
}

/**
 * 打印 / 导出 PDF 报表。
 * @param {string} title 报表标题
 * @param {Array<{title?:string, columns:Array<{key:string,title:string}>, rows:Array<Object>}>} tables 多个表格
 */
export function printReport(title, tables) {
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]))
  const tpl = (t) => {
    const cols = t.columns
    const thead = '<tr>' + cols.map((c) => `<th>${esc(c.title)}</th>`).join('') + '</tr>'
    const tbody = t.rows
      .map((r) => '<tr>' + cols.map((c) => `<td>${esc(r[c.key])}</td>`).join('') + '</tr>')
      .join('')
    return `<h3>${esc(t.title || '')}</h3><table><thead>${thead}</thead><tbody>${tbody}</tbody></table>`
  }
  const html = `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>${esc(title)}</title>
<style>
  body{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;color:#222;padding:24px;}
  h2{margin:0 0 4px;font-size:20px;} .meta{color:#888;font-size:12px;margin-bottom:18px;}
  h3{font-size:15px;margin:18px 0 8px;border-left:4px solid #E85D04;padding-left:8px;}
  table{border-collapse:collapse;width:100%;font-size:12px;}
  th,td{border:1px solid #ddd;padding:6px 8px;text-align:left;}
  th{background:#f5f5f5;font-weight:600;}
  tr:nth-child(even) td{background:#fafafa;}
  @media print{.noprint{display:none;}}
</style></head><body>
<h2>${esc(title)}</h2>
<div class="meta">生成时间：${new Date().toLocaleString('zh-CN')}</div>
${tables.map(tpl).join('')}
<script>window.onload=function(){setTimeout(function(){window.print();},200);};<\/script>
</body></html>`
  const w = window.open('', '_blank')
  if (!w) return false
  w.document.open()
  w.document.write(html)
  w.document.close()
  return true
}
