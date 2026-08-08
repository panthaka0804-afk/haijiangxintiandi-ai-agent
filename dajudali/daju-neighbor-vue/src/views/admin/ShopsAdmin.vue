<template>
  <div class="shops-admin">
    <div class="aa-header">
      <h2>商户管理</h2>
      <span class="aa-count">共 {{ shops.length }} 家</span>
    </div>

    <div class="aa-search">
      <input v-model="kw" placeholder="搜索商户名称 / 品类" />
    </div>

    <div class="aa-table-wrap">
      <table class="aa-table">
        <thead>
          <tr>
            <th>名称</th><th>楼层</th><th>品类</th><th>电话</th><th>营业时间</th><th>标签</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in filtered" :key="s.id">
            <td>
              <span class="sa-dot" :style="{background: s.color}"></span>
              {{ s.name }}
            </td>
            <td>{{ s.floor }}F</td>
            <td>{{ s.category }}</td>
            <td>{{ s.phone || '-' }}</td>
            <td>{{ s.hours || '-' }}</td>
            <td class="sa-tags">{{ Array.isArray(s.tags) ? s.tags.join('、') : (s.tags || '-') }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="!filtered.length" class="aa-empty">暂无商户数据</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const shops = ref([])
const kw = ref('')

onMounted(async () => {
  try {
    const res = await fetch('/api/shops')
    const d = await res.json()
    if (d && d.data) shops.value = d.data
  } catch (e) { console.error(e) }
})

const filtered = computed(() => {
  const q = kw.value.trim().toLowerCase()
  if (!q) return shops.value
  return shops.value.filter(s =>
    (s.name || '').toLowerCase().includes(q) ||
    (s.category || '').includes(q)
  )
})
</script>

<style scoped>
.shops-admin { padding: 0; }
.aa-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.aa-header h2 { margin: 0; color: #F0F0F0; font-size: 18px; }
.aa-count { color: #999; font-size: 13px; }

.aa-search { margin-bottom: 12px; }
.aa-search input {
  width: 100%; padding: 10px 14px; border: 1px solid #e0e0e0; border-radius: 8px;
  font-size: 14px; color: #F0F0F0; background: #1A1A1A; box-sizing: border-box;
}
.aa-search input:focus { outline: none; border-color: #999999; }

.aa-table-wrap { background: #1A1A1A; border-radius: 14px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.aa-table { width: 100%; border-collapse: collapse; }
.aa-table th { text-align: left; padding: 12px 16px; background: #1A1A1A; color: #BBBBBB; font-size: 13px; font-weight: 600; border-bottom: 1px solid #2E2E2E; }
.aa-table td { padding: 11px 16px; border-bottom: 1px solid #2E2E2E; font-size: 13px; color: #F0F0F0; vertical-align: top; }
.aa-table tr:last-child td { border-bottom: none; }
.sa-dot { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 6px; vertical-align: middle; }
.sa-tags { color: #BBBBBB; }
.aa-empty { padding: 40px; text-align: center; color: #999; font-size: 14px; }
</style>
