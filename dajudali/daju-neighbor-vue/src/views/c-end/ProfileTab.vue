<template>
  <div class="profile-tab">
    <!-- 会员卡 — 保留橙色渐变 -->
    <div class="member-card">
      <div class="mc-top">
        <div class="mc-level">钻石会员</div>
        <div class="mc-number">NO. 8888 6688 1234 5678</div>
      </div>
      <div class="mc-points">
        <div class="mc-pts-num">22,000</div>
        <div class="mc-pts-label">可用积分</div>
      </div>
      <div class="mc-bottom">
        <span>享 88 折优惠</span>
        <span>专属客服通道</span>
        <span>生日双倍积分</span>
      </div>
      <div class="mc-shine"></div>
      <div class="mc-ring"></div>
    </div>

    <!-- 功能 9 宫格 -->
    <div class="fn-grid">
      <div v-for="fn in functions" :key="fn.label" class="fn-item" @click="go(fn.route)">
        <div class="fn-icon">
          <svg v-html="fn.icon" width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"></svg>
        </div>
        <span class="fn-label">{{ fn.label }}</span>
      </div>
    </div>

    <!-- 更多设置 -->
    <div class="settings-list">
      <div class="s-item" @click="$router.push('/parking/bind')">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FF7B2C" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M14 7h-4v10h4a3 3 0 0 0 0-6h-3"/></svg>
        <span>我的车辆</span>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#555" stroke-width="2" stroke-linecap="round"><polyline points="9 18 15 12 9 6"/></svg>
      </div>
      <div class="s-item" @click="emit('switchTab', 'chat')">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FF7B2C" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        <span>联系客服</span>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#555" stroke-width="2" stroke-linecap="round"><polyline points="9 18 15 12 9 6"/></svg>
      </div>
      <div class="s-item">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FF7B2C" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
        <span>设置</span>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#555" stroke-width="2" stroke-linecap="round"><polyline points="9 18 15 12 9 6"/></svg>
      </div>
    </div>

    <div class="spacer"></div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
const emit = defineEmits(['switchTab'])
const router = useRouter()

const functions = [
  { label: '积分兑换', route: '/redeem', icon: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>' },
  { label: '我的优惠券', route: '/offers', icon: '<path d="M20 12v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-8"/><path d="M22 7H2v5h20z"/>' },
  { label: '停车管理', route: '/parking', icon: '<circle cx="12" cy="12" r="10"/><path d="M14 7h-4v10h4a3 3 0 0 0 0-6h-3"/>' },
  { label: '活动报名', route: '/activities', icon: '<rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>' },
  { label: '商户收藏', route: '/shops', icon: '<path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>' },
  { label: '室内导航', route: '/nav', icon: '<polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/>' },
  { label: '兑换记录', route: '/redeem', icon: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>' },
  { label: '会员中心', route: '/profile', icon: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>' },
  { label: '关于我们', route: '/home', icon: '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>' },
]

function go(route) { if (route) router.push(route) }
</script>

<style scoped>
.profile-tab { padding: 8px 12px; }

/* 会员卡 — 橙色渐变（品牌特色，保留） */
.member-card {
  background: linear-gradient(135deg, #FF7B2C, #E85D04);
  border-radius: 16px; padding: 24px 22px; position: relative; overflow: hidden; margin-bottom: 18px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
.mc-shine {
  position: absolute; top: -60px; right: -40px;
  width: 150px; height: 150px;
  background: radial-gradient(circle, rgba(255,255,255,0.12) 0%, transparent 70%);
  border-radius: 50%;
}
.mc-ring {
  position: absolute; right: -10px; bottom: -10px;
  width: 80px; height: 40px;
  border: 2px solid rgba(255,255,255,0.1);
  border-radius: 50%; transform: rotate(-10deg);
}
.mc-top { position: relative; z-index: 1; margin-bottom: 16px; }
.mc-level { font-size: 14px; color: rgba(255,255,255,0.7); font-weight: 500; }
.mc-number { font-size: 13px; color: rgba(255,255,255,0.5); margin-top: 2px; letter-spacing: 1px; }
.mc-points { position: relative; z-index: 1; margin-bottom: 16px; }
.mc-pts-num { font-size: 40px; font-weight: 800; color: #fff; }
.mc-pts-label { font-size: 13px; color: rgba(255,255,255,0.65); margin-top: 2px; }
.mc-bottom { position: relative; z-index: 1; display: flex; gap: 12px; }
.mc-bottom span {
  background: rgba(255,255,255,0.15); color: rgba(255,255,255,0.8);
  padding: 4px 12px; border-radius: 10px; font-size: 12px;
}

/* 功能 9 宫格 */
.fn-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 16px; }
.fn-item {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 12px 4px; cursor: pointer; transition: all 0.15s;
}
.fn-icon {
  width: 60px; height: 60px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  background: #222222; color: #999;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  transition: all 0.15s;
}
.fn-icon:active { color: #FF7B2C; opacity: 0.8; }
.fn-label { font-size: 12px; color: #AAA; font-weight: 500; }

/* 设置列表 */
.settings-list {
  background: #222222; border-radius: 12px; overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
.s-item {
  display: flex; align-items: center; gap: 14px; padding: 14px 16px;
  cursor: pointer; transition: background 0.15s; font-size: 15px; color: #F0F0F0;
}
.s-item:not(:last-child) { border-bottom: 0.5px solid #2E2E2E; }
.s-item:active { background: #2A2A2A; }
.s-item :last-child { margin-left: auto; }

.spacer { height: 24px; }
</style>
