<template>
  <div class="offers-admin">
    <div class="aa-header">
      <h2>优惠券管理</h2>
      <span class="aa-count">共 {{ offers.length }} 张</span>
    </div>

    <div class="aa-search">
      <input v-model="kw" placeholder="搜索商户 / 券说明" />
    </div>

    <div class="aa-table-wrap">
      <table class="aa-table">
        <thead>
          <tr><th>ID</th><th>商户</th><th>券说明</th><th>面额</th><th>分类</th><th>有效期</th><th>状态</th></tr>
        </thead>
        <tbody>
          <tr v-for="o in filtered" :key="o.id">
            <td>{{ o.id }}</td>
            <td>{{ o.shop_name }}</td>
            <td>{{ o.label }}</td>
            <td><b>¥{{ o.amount }}</b></td>
            <td>{{ catLabel(o.category) }}</td>
            <td>{{ o.expire }}</td>
            <td><span class="aa-tag" :class="o.status">{{ statusLabel(o.status) }}</span></td>
          </tr>
        </tbody>
      </table>
      <div v-if="!filtered.length" class="aa-empty">暂无优惠券数据</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const offers = ref([])
const kw = ref('')

onMounted(async () => {
  try {
    const res = await fetch('/api/offers')
    const d = await res.json()
    if (d && d.data) offers.value = d.data
  } catch (e) { console.error(e) }
})

const filtered = computed(() => {
  const q = kw.value.trim().toLowerCase()
  if (!q) return offers.value
  return offers.value.filter(o =>
    (o.shop_name || '').toLowerCase().includes(q) ||
    (o.label || '').toLowerCase().includes(q)
  )
})

function catLabel(c) {
  return { food: '餐饮券', retail: '零售券', parking: '停车券', fun: '娱乐券' }[c] || c || '-'
}
function statusLabel(s) {
  return { active: '生效中', inactive: '已停用' }[s] || s || '-'
}
</script>

<style scoped>
.offers-admin { padding: 0; }
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
.aa-tag { padding: 2px 10px; border-radius: 10px; font-size: 12px; }
.aa-tag.active { background: #1A1A1A; color: #9E9E9E; }
.aa-tag.inactive { background: #1A1A1A; color: #777; }
.aa-empty { padding: 40px; text-align: center; color: #999; font-size: 14px; }
</style>
