<template>
  <div class="cb-wrapper">
    <div class="cb-card" @click="$emit('click')">
      <div class="card-grad">
        <div class="card-grad-left">
          <span class="card-grad-title">领券中心</span>
          <span class="card-grad-sub">餐饮券 · 零售券 · 停车券</span>
        </div>
        <div class="card-grad-right">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20 12v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-8"/><path d="M22 7H2v5h20z"/><path d="M12 22V7"/><path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z"/><path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z"/>
          </svg>
        </div>
        <div class="card-dots"></div>
        <div class="card-ring"></div>
      </div>
      <div class="card-white">
        <div class="card-tags">
          <span class="tag">最高减50元</span>
          <span class="tag">限时领取</span>
          <span class="tag">餐饮券</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineEmits(['click'])
</script>

<style scoped>
.cb-wrapper { padding: 0 12px 8px; }

.cb-card {
  border-radius: 20px; overflow: hidden;
  box-shadow: 6px 6px 12px #d1d6dd, -6px -6px 12px #ffffff;
  cursor: pointer; transition: transform 0.15s, box-shadow 0.15s;
}
.cb-card:active { transform: scale(0.98); box-shadow: inset 3px 3px 6px #d1d6dd, inset -3px -3px 6px #ffffff; }

/* 渐变顶 */
.card-grad {
  background: linear-gradient(135deg, #1A1A1A 0%, #1A1A1A 100%);
  padding: 22px 18px 18px; position: relative; overflow: hidden;
  display: flex; justify-content: space-between; align-items: flex-start;
}
.card-grad-left { display: flex; flex-direction: column; gap: 6px; z-index: 1; }
.card-grad-title { font-size: 20px; font-weight: 700; color: #fff; }
.card-grad-sub { font-size: 12px; color: rgba(255,255,255,0.7); }
.card-grad-right { z-index: 1; }
.card-dots {
  position: absolute; top: 12px; right: 60px;
  width: 28px; height: 28px;
  background: radial-gradient(circle, #1A1A1A 1px, transparent 1px);
  background-size: 7px 7px;
}
.card-ring {
  position: absolute; right: -12px; bottom: -8px;
  width: 60px; height: 30px;
  border: 1.5px solid rgba(255,255,255,0.1);
  border-radius: 50%; transform: rotate(-8deg);
}

/* 白底 */
.card-white { background: #1A1A1A; padding: 10px 18px 12px; }
.card-tags { display: flex; gap: 6px; }
.tag { background: #1A1A1A; color: #999999; font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 6px; }
</style>
