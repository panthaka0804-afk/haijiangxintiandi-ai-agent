<template>
  <div class="pb-page">
    <div class="pb-back" @click="$router.back()">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#AAA" stroke-width="2" stroke-linecap="round"><polyline points="15 18 9 12 15 6"/></svg>
    </div>
    <div class="pb-title">我的车辆</div>
    <div v-if="tip" class="pb-tip">{{ tip }}</div>

    <div class="pb-list">
      <div v-for="(p, i) in plates" :key="i" class="pb-card">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#999999" stroke-width="1.5" stroke-linecap="round"><rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg>
        <span class="pb-plate">{{ p }}</span>
        <button class="pb-del" @click="delPlate(p)">删除</button>
      </div>
    </div>

    <div class="pb-add-section" v-if="adding">
      <div class="pb-input-wrap">
        <input v-model="newPlate" placeholder="沪A·12345" maxlength="10" class="pb-input" />
      </div>
      <div class="pb-add-actions">
        <button class="pb-cancel" @click="adding = false; newPlate = ''">取消</button>
        <button class="pb-confirm" @click="addPlate" :disabled="!newPlate">确认添加</button>
      </div>
    </div>

    <button class="pb-add-btn" v-if="!adding" @click="adding = true">+ 添加新车牌</button>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { myPlates, bindPlate, unbindPlate } from '@/api'

const plates = ref([])
const adding = ref(false)
const newPlate = ref('')
const loading = ref(false)
const tip = ref('')

async function loadPlates() {
  try {
    const resp = await myPlates()
    if (resp.ok) plates.value = resp.plates || []
  } catch (e) {}
}

onMounted(loadPlates)

function norm(p) { return (p || '').replace(/[·\s-]/g, '').toUpperCase() }

async function addPlate() {
  const p = norm(newPlate.value)
  if (!p) return
  loading.value = true; tip.value = ''
  try {
    const resp = await bindPlate({ plate: p })
    if (resp.ok) {
      plates.value = resp.plates || []
      newPlate.value = ''; adding.value = false
      tip.value = resp.message || '绑定成功'
    } else {
      tip.value = resp.error || '绑定失败'
    }
  } catch (e) { tip.value = '网络错误' } finally { loading.value = false }
}

async function delPlate(p) {
  try {
    const resp = await unbindPlate({ plate: p })
    if (resp.ok) plates.value = resp.plates || []
  } catch (e) {}
}
</script>

<style scoped>
.pb-page { padding: 0 12px; min-height: 100vh; background: #1A1A1A; }
.pb-back { padding: 10px 0; cursor: pointer; display: inline-block; margin-bottom: 8px; }
.pb-title { font-size: 24px; font-weight: 700; color: #F0F0F0; margin-bottom: 20px; }
.pb-tip { font-size: 13px; color: #8FB98F; background: #1E2A1E; border: 1px solid #3A5A3A; padding: 8px 12px; border-radius: 10px; margin-bottom: 14px; }

.pb-list { display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px; }
.pb-card {
  background: #222222; border-radius: 12px; padding: 16px;
  display: flex; align-items: center; gap: 14px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
.pb-plate { flex: 1; font-size: 18px; font-weight: 700; color: #F0F0F0; letter-spacing: 1px; }
.pb-del { padding: 6px 14px; border: none; border-radius: 10px; background: #1A1A1A; color: #808080; font-size: 13px; cursor: pointer; font-family: inherit; }

.pb-add-section { margin-bottom: 16px; }
.pb-input-wrap {
  background: #2A2A2A; border: 1px solid #444; border-radius: 12px;
  margin-bottom: 12px; transition: border-color 0.15s;
}
.pb-input-wrap:focus-within { border-color: #999999; }
.pb-input { width: 100%; padding: 16px; border: none; background: none; outline: none; font-size: 22px; font-weight: 700; color: #F0F0F0; text-align: center; font-family: inherit; }
.pb-add-actions { display: flex; gap: 10px; }
.pb-cancel, .pb-confirm {
  flex: 1; padding: 12px; border: none; border-radius: 12px;
  font-size: 15px; font-weight: 600; cursor: pointer; font-family: inherit;
}
.pb-cancel { background: #2A2A2A; color: #999; }
.pb-confirm { background: #1A1A1A; color: #fff; }
.pb-confirm:active { opacity: 0.8; }
.pb-confirm:disabled { background: #444; color: #777; cursor: not-allowed; }

.pb-add-btn {
  width: 100%; padding: 14px; border: dashed 2px #333; border-radius: 12px;
  background: none; color: #999; font-size: 15px; font-weight: 600;
  cursor: pointer; font-family: inherit;
}
</style>
