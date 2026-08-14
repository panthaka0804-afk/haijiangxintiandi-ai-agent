<template>
  <div class="admin-layout">
    <!-- 左侧黑色栏 -->
    <aside class="sidebar" :style="{ width: isMobile ? '0' : (collapsed ? '64px' : '200px') }">
      <div class="sidebar-header">
        <span class="logo" v-if="!collapsed">海江新天地</span>
        <span class="logo-short" v-else>海江</span>
      </div>
      <nav class="sidebar-nav">
        <a v-for="t in superTabs" :key="t.key" class="nav-item" :class="{ active: activeMenu === t.key }" :style="{ '--c': t.color }" :href="'/vue' + t.key" @click.prevent="router.push(t.key)">
          <svg class="nav-icon" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <template v-if="t.key === '/admin/dashboard'">
              <rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/>
              <rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>
            </template>
            <template v-else-if="t.key === '/admin/orders'">
              <path d="M9 12h6M9 16h6M17 21H7a2 2 0 01-2-2V5a2 2 0 012-2h5.59a2 2 0 011.41.59l4.41 4.41a2 2 0 01.59 1.41V19a2 2 0 01-2 2z"/>
            </template>
            <template v-else-if="t.key === '/admin/human-chat'">
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
            </template>
            <template v-else-if="t.key === '/admin/feedback'">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
            </template>
            <template v-else-if="t.key === '/admin/insights'">
              <path d="M3 3v18h18"/><path d="M7 15l4-4 4 3 5-6"/>
            </template>
            <template v-else-if="t.key === '/admin/kb'">
              <path d="M6 2h11a2 2 0 012 2v16a2 2 0 01-2 2H6a2 2 0 01-2-2V4a2 2 0 012-2z"/><line x1="6" y1="6" x2="10" y2="6"/><line x1="6" y1="10" x2="12" y2="10"/><line x1="6" y1="14" x2="10" y2="14"/>
            </template>
            <template v-else-if="t.key === '/admin/members'">
              <circle cx="9" cy="7" r="3.5"/><path d="M4 21v-1a5.5 5.5 0 0110 0v1"/>
              <circle cx="17.5" cy="8" r="2.5"/><path d="M14.5 21v-1a4 4 0 013.5-3.87"/>
            </template>
            <template v-else-if="t.key === '/admin/activities'">
              <circle cx="12" cy="12" r="9.5"/><polygon points="10.5,8.5 10.5,15.5 16,12" stroke="currentColor" fill="currentColor" style="fill-opacity:0.15"/>
            </template>
            <template v-else-if="t.key === '/admin/users'">
              <circle cx="12" cy="8" r="3.5"/><path d="M5 21v-1a5.5 5.5 0 0114 0v1"/>
            </template>
            <template v-else-if="t.key === '/admin/settings'">
              <circle cx="12" cy="12" r="2.5"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/>
            </template>
            <template v-else-if="t.key === '/admin/shops'">
              <path d="M3 9l1.5-4.5A2 2 0 016.4 3h11.2a2 2 0 011.9 1.5L21 9"/>
              <path d="M3 9v10a1 1 0 001 1h16a1 1 0 001-1V9"/>
              <path d="M3 9h18"/><path d="M9 20v-6h6v6"/>
            </template>
            <template v-else-if="t.key === '/admin/offers'">
              <path d="M4 7h16a1 1 0 011 1v2a2 2 0 000 4v2a1 1 0 01-1 1H4a1 1 0 01-1-1v-2a2 2 0 000-4V8a1 1 0 011-1z"/>
              <line x1="13" y1="7" x2="13" y2="17" stroke-dasharray="2 2"/>
            </template>
            <template v-else-if="t.key === '/admin/redeem'">
              <rect x="3" y="8" width="18" height="13" rx="1.5"/>
              <path d="M3 12h18"/><path d="M12 8v13"/>
              <path d="M12 8C12 8 10 4 7.5 5.5 5 7 12 8 12 8z"/>
              <path d="M12 8C12 8 14 4 16.5 5.5 19 7 12 8 12 8z"/>
            </template>
            <template v-else-if="t.key === '/admin/intelligence'">
              <rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 3v2M15 3v2M9 19v2M15 19v2M3 9h2M3 15h2M19 9h2M19 15h2"/><rect x="9.5" y="9.5" width="5" height="5" rx="1"/>
            </template>
          </svg>
          <span class="nav-label" v-show="!collapsed">{{ t.label }}</span>
        </a>
      </nav>
      <div class="sidebar-footer">
        <button class="collapse-btn" @click="collapsed = !collapsed">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline :points="collapsed ? '9 18 15 12 9 6' : '15 18 9 12 15 6'"/></svg>
        </button>
      </div>
    </aside>

    <!-- 右侧内容区 -->
    <div class="main-area" :style="{ marginLeft: isMobile ? '0' : (collapsed ? '64px' : '200px') }">
      <div class="top-bar">
        <span class="top-title">{{ currentTabLabel }}</span>
        <div class="top-right">
          <span class="user-name">{{ userStore.user?.display_name || '管理员' }}</span>
          <button class="logout-btn" @click="handleLogout">退出</button>
        </div>
      </div>
      <div class="main-body">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { logout } from '@/api'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const collapsed = ref(false)
const isMobile = ref(false)

function checkMobile() { isMobile.value = window.innerWidth < 768 }
onMounted(() => { checkMobile(); window.addEventListener('resize', checkMobile) })
onUnmounted(() => window.removeEventListener('resize', checkMobile))

const activeMenu = computed(() => route.path)

const superTabs = [
  { key: '/admin/intelligence', label: '智能中心', color: '#FF7B2C' },
  { key: '/admin/dashboard', label: '看板', color: '#C4923A' },
  { key: '/admin/orders', label: '工单', color: '#D4A59A' },
  { key: '/admin/human-chat', label: '人工客服', color: '#9B4A3E' },
  { key: '/admin/feedback', label: '评价', color: '#C9956C' },
  { key: '/admin/insights', label: '运营洞察', color: '#8B8B90' },
  { key: '/admin/kb', label: '知识库', color: '#6B6E64' },
  { key: '/admin/members', label: '会员', color: '#C4923A' },
  { key: '/admin/activities', label: '活动', color: '#D4A59A' },
  { key: '/admin/shops', label: '商户', color: '#9B4A3E' },
  { key: '/admin/offers', label: '优惠券', color: '#C9956C' },
  { key: '/admin/redeem', label: '积分商城', color: '#8B8B90' },
  { key: '/admin/users', label: '用户', color: '#6B6E64' },
  { key: '/admin/settings', label: '设置', color: '#C4923A' },
]

const currentTabLabel = computed(() => {
  const t = superTabs.find(t => t.key === route.path)
  return t ? t.label : '管理后台'
})

function handleLogout() {
  logout()
  userStore.clearUser()
  router.push('/manage')
}
</script>

<style scoped>
.admin-layout { display: flex; min-height: 100vh; background: #000000; }

/* ====== 左侧栏 ====== */
.sidebar {
  position: fixed; top: 0; left: 0; bottom: 0;
  background: #0A0A0A;
  display: flex; flex-direction: column;
  transition: width 0.25s;
  z-index: 50;
  overflow: hidden;
  border-right: 1px solid #1A1A1A;
}
.sidebar-header { padding: 22px 16px 18px; text-align: center; white-space: nowrap; }
.sidebar-header .logo {
  font-size: 17px; font-weight: 800;
  background: linear-gradient(135deg, #FF7B2C, #E85D04);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent; color: transparent;
}
.sidebar-header .logo-short {
  font-size: 17px; font-weight: 800; display: block;
  background: linear-gradient(135deg, #FF7B2C, #E85D04);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent; color: transparent;
}

.sidebar-nav { flex: 1; padding: 8px; display: flex; flex-direction: column; gap: 4px; }
.nav-item {
  position: relative;
  display: flex; align-items: center; gap: 12px;
  padding: 12px 14px; border-radius: 10px;
  color: #8A8A8A; text-decoration: none; font-size: 14px;
  transition: all 0.2s; white-space: nowrap; cursor: pointer;
}
.nav-item .nav-icon { flex-shrink: 0; color: var(--c, #C4923A); transition: color 0.2s; }
.nav-item .nav-label { overflow: hidden; transition: color 0.2s; }
.nav-item:hover { background: rgba(255, 255, 255, 0.06); }
.nav-item:hover .nav-icon, .nav-item:hover .nav-label { color: var(--c, #C4923A); }
.nav-item.active {
  background: linear-gradient(135deg, rgba(255, 123, 44, 0.92), rgba(232, 93, 4, 0.92));
  color: #fff; font-weight: 600;
  box-shadow: 0 6px 16px rgba(232, 93, 4, 0.35);
}
.nav-item.active .nav-icon, .nav-item.active .nav-label { color: #fff; }
.nav-item.active::before {
  content: ''; position: absolute; left: 0; top: 10px; bottom: 10px;
  width: 3px; background: #fff; border-radius: 0 2px 2px 0;
}

.sidebar-footer { padding: 12px; }
.collapse-btn {
  width: 36px; height: 36px; background: #1A1A1A; border: none;
  color: #888; border-radius: 8px; cursor: pointer;
  display: flex; align-items: center; justify-content: center; margin: 0 auto;
  transition: all 0.2s;
}
.collapse-btn:hover { background: #242424; color: #FF7B2C; }

/* ====== 右侧内容区 ====== */
.main-area { flex: 1; display: flex; flex-direction: column; background: #000000; transition: margin-left 0.25s; min-height: 100vh; }
.top-bar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px; height: 56px;
  background: #0A0A0A; border-bottom: 1px solid #1A1A1A;
  flex-shrink: 0;
}
.top-title {
  font-size: 16px; font-weight: 700;
  background: linear-gradient(135deg, #FF7B2C, #E85D04);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent; color: transparent;
}
.top-right { display: flex; align-items: center; gap: 12px; }
.user-name { font-size: 13px; color: #999; }
.logout-btn {
  padding: 6px 16px; border: 1px solid rgba(255, 123, 44, 0.5); border-radius: 8px;
  background: transparent; color: #FF7B2C; font-size: 13px; cursor: pointer;
  transition: all 0.2s;
}
.logout-btn:hover { background: rgba(255, 123, 44, 0.14); border-color: #FF7B2C; color: #FF8F47; }

.main-body { flex: 1; padding: 20px; background: #000000; overflow-y: auto; }

@media (max-width: 767px) {
  .sidebar { width: 0 !important; }
  .main-area { margin-left: 0 !important; }
  .top-bar { padding: 0 16px; }
  .main-body { padding: 12px; }
}
</style>
