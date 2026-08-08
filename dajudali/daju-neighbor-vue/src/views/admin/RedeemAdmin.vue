<template>
  <div class="redeem-admin">
    <div class="aa-header">
      <h2>积分商城管理</h2>
      <span class="aa-count">共 {{ goods.length }} 项</span>
    </div>

    <div class="aa-search">
      <input v-model="kw" placeholder="搜索商品名称 / 分类" />
    </div>

    <div class="aa-table-wrap">
      <table class="aa-table">
        <thead>
          <tr><th>ID</th><th>名称</th><th>分类</th><th>所需积分</th><th>库存</th><th>状态</th></tr>
        </thead>
        <tbody>
          <tr v-for="g in filtered" :key="g.id">
            <td>{{ g.id }}</td>
            <td>
              <span class="ra-dot" :style="{background: g.gradient || '#6A6A6E'}"></span>
              {{ g.name }}
            </td>
            <td>{{ g.category }}</td>
            <td><b>{{ g.points }}</b> 分</td>
            <td>{{ g.stock < 0 ? '不限' : g.stock }}</td>
            <td><span class="aa-tag" :class="g.status">{{ statusLabel(g.status) }}</span></td>
          </tr>
        </tbody>
      </table>
      <div v-if="!filtered.length" class="aa-empty">暂无积分商品</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const goods = ref([])
const kw = ref('')

onMounted(async () => {
  try {
    const res = await fetch('/api/redeem')
    const d = await res.json()
    if (d && d.data) goods.value = d.data
  } catch (e) { console.error(e) }
})

const filtered = computed(() => {
  const q = kw.value.trim().toLowerCase()
  if (!q) return goods.value
  return goods.value.filter(g =>
    (g.name || '').toLowerCase().includes(q) ||
    (g.category || '').includes(q)
  )
})

function statusLabel(s) {
  return { active: '上架中', inactive: '已下架' }[s] || s || '-'
}
</script>

<style scoped>
.redeem-admin { padding: 0; }
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
.aa-table td { padding: 11px 16px; border-bottom: 1px solid #2E2E2E; font-size: 13px; color: #F0F0F0; }
.aa-table tr:last-child td { border-bottom: none; }
.ra-dot { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 6px; vertical-align: middle; }
.aa-tag { padding: 2px 10px; border-radius: 10px; font-size: 12px; }
.aa-tag.active { background: #1A1A1A; color: #9E9E9E; }
.aa-tag.inactive { background: #1A1A1A; color: #777; }
.aa-empty { padding: 40px; text-align: center; color: #999; font-size: 14px; }
</style>
