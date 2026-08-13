<template>
  <div class="pb-page">
    <div class="pb-back" @click="$router.back()">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#AAA" stroke-width="2" stroke-linecap="round"><polyline points="15 18 9 12 15 6"/></svg>
    </div>
    <div class="pb-title">我的车辆</div>
    <div v-if="tip" class="pb-tip">{{ tip }}</div>

    <div class="pb-list">
      <div v-for="(p, i) in plates" :key="i" class="pb-card" :class="'pb-c' + (i % 5)">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="1.5" stroke-linecap="round"><rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg>
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
.pb-page { padding: 0 12px; min-height: 100vh; background: #000000; }
.pb-back { padding: 10px 0; cursor: pointer; display: inline-block; margin-bottom: 8px; }
.pb-title { font-size: 24px; font-weight: 700; color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,.35); margin-bottom: 20px; }
.pb-tip { font-size: 13px; color: #fff; background: #8B8B90; border: 3px solid #6A6A6E; padding: 8px 12px; border-radius: 10px; margin-bottom: 14px; box-shadow: inset 0 1px 0 rgba(255,255,255,.2); }

.pb-list { display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px; }
.pb-card {
  background: #6B6E64; border: 3px solid #4E5049; border-radius: 12px; padding: 16px;
  display: flex; align-items: center; gap: 14px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20);
}
.pb-c0 { background: #C4923A; border-color: #9A7425; }
.pb-c1 { background: #C9956C; border-color: #A87C48; }
.pb-c2 { background: #9B4A3E; border-color: #6E332A; }
.pb-c3 { background: #8B8B90; border-color: #6A6A6E; }
.pb-c4 { background: #6B6E64; border-color: #4E5049; }
.pb-plate { flex: 1; font-size: 18px; font-weight: 700; color: #fff; letter-spacing: 1px; text-shadow: 0 1px 2px rgba(0,0,0,.35); }
.pb-del { padding: 6px 14px; border: 3px solid #6E332A; border-radius: 10px; background: #9B4A3E; color: #fff; font-size: 13px; cursor: pointer; font-family: inherit;
  box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(155,74,62,.45); }
.pb-del:active { box-shadow: inset 5px 5px 10px rgba(0,0,0,.55), inset -2px -2px 5px rgba(155,74,62,.35); }

.pb-add-section { margin-bottom: 16px; }
.pb-input-wrap {
  background: #000; border: 3px solid #4E5049; border-radius: 12px;
  margin-bottom: 12px; transition: border-color 0.15s;
  box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(107,110,100,.25);
}
.pb-input-wrap:focus-within { border-color: #6B6E64; }
.pb-input { width: 100%; padding: 16px; border: none; background: none; outline: none; font-size: 22px; font-weight: 700; color: #fff; text-align: center; font-family: inherit; }
.pb-add-actions { display: flex; gap: 10px; }
.pb-cancel, .pb-confirm {
  flex: 1; padding: 12px; border: 3px solid #4E5049; border-radius: 20px;
  font-size: 15px; font-weight: 600; cursor: pointer; font-family: inherit;
  background: #6B6E64; color: #fff;
  box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(107,110,100,.45);
  filter: drop-shadow(0 0.6px 1px rgba(0,0,0,0.4));
}
.pb-cancel:active, .pb-confirm:active { box-shadow: inset 5px 5px 10px rgba(0,0,0,.55), inset -2px -2px 5px rgba(107,110,100,.35); }
.pb-confirm { background: #9A7425; border-color: #9A7425;
  box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(196,146,58,.45); }
.pb-confirm:active { box-shadow: inset 5px 5px 10px rgba(0,0,0,.55), inset -2px -2px 5px rgba(196,146,58,.35); }
.pb-confirm:disabled { background: #4E5049; border-color: #4E5049; color: rgba(255,255,255,.5); cursor: not-allowed; box-shadow: none; }

.pb-add-btn {
  width: 100%; padding: 14px; border: 3px solid #9A7425; border-radius: 20px;
  background: #9A7425; color: #fff; font-size: 15px; font-weight: 600;
  cursor: pointer; font-family: inherit;
  box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(196,146,58,.45);
  filter: drop-shadow(0 0.6px 1px rgba(0,0,0,0.4));
}
.pb-add-btn:active { box-shadow: inset 5px 5px 10px rgba(0,0,0,.55), inset -2px -2px 5px rgba(196,146,58,.35); }
</style>
