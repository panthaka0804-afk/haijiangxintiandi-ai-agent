<template>
  <div class="map3d-page">
    <iframe src="/vue/map3d.html" frameborder="0" class="map3d-frame"></iframe>
    <button class="back-btn" @click="$router.back()">‹ 返回</button>
  </div>
</template>

<script setup>
// 3D 室内地图：独立 Three.js 应用（public/map3d.html），以 iframe 嵌入
</script>

<style scoped>
.map3d-page { position: fixed; inset: 0; background: #0c0c0c; }
.map3d-frame { width: 100%; height: 100%; border: none; display: block; }
.back-btn {
  position: fixed; top: 10px; right: 12px; z-index: 20;
  border: 1px solid rgba(255,255,255,.15); background: rgba(30,30,30,.85);
  backdrop-filter: blur(6px); color: #eee; font-size: 13px; font-weight: 600;
  padding: 7px 14px; border-radius: 20px; cursor: pointer; font-family: inherit;
  -webkit-tap-highlight-color: transparent;
}
.back-btn:active { background: #FF7B2C; color: #fff; }
</style>
