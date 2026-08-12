<template>
  <div class="admin-layout">
    <!-- 左侧黑色栏 -->
    <aside class="sidebar" :style="{ width: isMobile ? '0' : (collapsed ? '64px' : '200px') }">
      <div class="sidebar-header">
        <span class="logo" v-if="!collapsed">海江新天地</span>
        <span class="logo-short" v-else>海江</span>
      </div>
      <nav class="sidebar-nav">
        <a v-for="t in superTabs" :key="t.key" class="nav-item" :class="{ active: activeMenu === t.key }" :href="'/vue' + t.key" @click.prevent="router.push(t.key)">
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
  { key: '/admin/dashboard', label: '看板' },
  { key: '/admin/orders', label: '工单' },
  { key: '/admin/human-chat', label: '人工客服' },
  { key: '/admin/feedback', label: '评价' },
  { key: '/admin/insights', label: '运营洞察' },
  { key: '/admin/kb', label: '知识库' },
  { key: '/admin/members', label: '会员' },
  { key: '/admin/activities', label: '活动' },
  { key: '/admin/shops', label: '商户' },
  { key: '/admin/offers', label: '优惠券' },
  { key: '/admin/redeem', label: '积分商城' },
  { key: '/admin/users', label: '用户' },
  { key: '/admin/settings', label: '设置' },
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
.admin-layout { display: flex; min-height: 100vh; background: #1A1A1A; }

/* ====== 左侧黑色栏 ====== */
.sidebar {
  position: fixed; top: 0; left: 0; bottom: 0;
  background: #1A1A1A;
  display: flex; flex-direction: column;
  transition: width 0.25s;
  z-index: 50;
  overflow: hidden;
}
.sidebar-header { padding: 20px 16px 16px; text-align: center; white-space: nowrap; }
.sidebar-header .logo { color: #999999; font-size: 16px; font-weight: 800; }
.sidebar-header .logo-short { color: #999999; font-size: 16px; font-weight: 800; display: block; }

.sidebar-nav { flex: 1; padding: 8px; display: flex; flex-direction: column; gap: 2px; }
.nav-item {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 14px; border-radius: 10px;
  color: #A7A7A7; text-decoration: none; font-size: 14px;
  transition: all 0.2s; white-space: nowrap; cursor: pointer;
}
.nav-item:hover { background: #1A1A1A; color: #e0e0e0; }
.nav-item.active { background: #1A1A1A; color: #999999; font-weight: 600; }
.nav-icon { flex-shrink: 0; }
.nav-label { overflow: hidden; }

.sidebar-footer { padding: 12px; }
.collapse-btn { width: 36px; height: 36px; background: #1A1A1A; border: none; color: #A7A7A7; border-radius: 8px; cursor: pointer; display: flex; align-items: center; justify-content: center; margin: 0 auto; }

/* ====== 右侧内容区 ====== */
.main-area { flex: 1; display: flex; flex-direction: column; background: #1A1A1A; transition: margin-left 0.25s; min-height: 100vh; }
.top-bar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px; height: 56px;
  background: #1A1A1A; border-bottom: 1px solid #eee;
  flex-shrink: 0;
}
.top-title { font-size: 16px; font-weight: 700; color: #F0F0F0; }
.top-right { display: flex; align-items: center; gap: 12px; }
.user-name { font-size: 13px; color: #999; }
.logout-btn {
  padding: 6px 16px; border: 1px solid #e0e0e0; border-radius: 8px;
  background: #1A1A1A; color: #BBBBBB; font-size: 13px; cursor: pointer;
}
.logout-btn:hover { border-color: #767676; color: #BBBBBB; }

.main-body { flex: 1; padding: 20px; background: #1A1A1A; overflow-y: auto; }

@media (max-width: 767px) {
  .sidebar { width: 0 !important; }
  .main-area { margin-left: 0 !important; }
  .top-bar { padding: 0 16px; }
  .main-body { padding: 12px; }
}
</style>
