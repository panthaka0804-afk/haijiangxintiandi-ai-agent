import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  // C端 — 主入口（三 Tab）
  {
    path: '/',
    name: 'chat',
    component: () => import('@/views/c-end/ChatView.vue'),
    meta: { title: '海江新天地' }
  },
  // C端 — 独立页面
  { path: '/offers', name: 'offers', component: () => import('@/views/c-end/OffersTab.vue'), meta: { title: '优惠券 - 海江新天地' } },
  { path: '/nav', name: 'nav', component: () => import('@/views/c-end/NavTab.vue'), meta: { title: '室内导航 - 海江新天地' } },
  { path: '/shops', name: 'shops', component: () => import('@/views/c-end/ShopsList.vue'), meta: { title: '商户列表 - 海江新天地' } },
  { path: '/shops/:id', name: 'shop-detail', component: () => import('@/views/c-end/ShopDetail.vue'), meta: { title: '商户详情 - 海江新天地' } },
  { path: '/parking', name: 'parking', component: () => import('@/views/c-end/ParkingPage.vue'), meta: { title: '停车缴费 - 海江新天地' } },
  { path: '/parking/bind', name: 'parking-bind', component: () => import('@/views/c-end/ParkingBind.vue'), meta: { title: '管理车辆 - 海江新天地' } },
  { path: '/activities', name: 'activities', component: () => import('@/views/c-end/ActivitiesPage.vue'), meta: { title: '活动报名 - 海江新天地' } },
  { path: '/activities/:id', name: 'activity-detail', component: () => import('@/views/c-end/ActivityDetail.vue'), meta: { title: '活动详情 - 海江新天地' } },
  { path: '/redeem', name: 'redeem', component: () => import('@/views/c-end/RedeemPage.vue'), meta: { title: '积分商城 - 海江新天地' } },
  { path: '/redeem/:id', name: 'redeem-detail', component: () => import('@/views/c-end/RedeemDetail.vue'), meta: { title: '兑换详情 - 海江新天地' } },
  { path: '/merchant', name: 'merchant', component: () => import('@/views/c-end/MerchantPage.vue'), meta: { title: '招商合作 - 海江新天地' } },
  // 活动管理 - 独立页面，自带登录
  { path: '/act-admin', name: 'act-admin', component: () => import('@/views/admin/ActivitiesAdmin.vue'), meta: { title: '活动管理 - 海江新天地' } },

  // 后台管理路由
  { path: '/manage', name: 'admin-login', component: () => import('@/views/admin/AdminLogin.vue'), meta: { title: '后台登录 - 海江新天地' } },
  {
    path: '/admin', name: 'admin', component: () => import('@/views/admin/Dashboard.vue'),
    meta: { title: '管理后台 - 海江新天地', requiresAdmin: true },
    children: [
      { path: '', redirect: { name: 'admin-dashboard' } },
      { path: 'dashboard', name: 'admin-dashboard', component: () => import('@/views/admin/AdminDashboard.vue'), meta: { title: '数据看板' } },
      { path: 'kb', name: 'admin-kb', component: () => import('@/views/admin/KnowledgeBase.vue'), meta: { title: '知识库管理' } },
      { path: 'orders', name: 'admin-orders', component: () => import('@/views/admin/WorkOrders.vue'), meta: { title: '工单管理' } },
      { path: 'members', name: 'admin-members', component: () => import('@/views/admin/Members.vue'), meta: { title: '会员管理' } },
      { path: 'users', name: 'admin-users', component: () => import('@/views/admin/Users.vue'), meta: { title: '用户管理' } },
      { path: 'settings', name: 'admin-settings', component: () => import('@/views/admin/Settings.vue'), meta: { title: '系统设置' } },
      { path: 'figma', name: 'admin-figma', component: () => import('@/views/admin/FigmaDesign.vue'), meta: { title: 'Figma协作' } },
      { path: 'activities', name: 'admin-activities', component: () => import('@/views/admin/ActivitiesAdmin.vue'), meta: { title: '活动管理' } },
    ],
  },
  { path: '/platform', name: 'platform', component: () => import('@/views/admin/Platform.vue'), meta: { title: '平台管理 - 海江新天地', requiresSuperAdmin: true } },
]

const router = createRouter({
  history: createWebHistory('/vue/'),
  routes,
})

router.beforeEach(async (to, from, next) => {
  document.title = to.meta.title || '海江新天地'
  if (to.meta.requiresAdmin || to.meta.requiresSuperAdmin || to.path.startsWith('/admin')) {
    try {
      const resp = await fetch('/api/session')
      const data = await resp.json()
      if (!data.ok) return next('/manage')
      if (to.meta.requiresSuperAdmin && data.user.role !== 'super_admin') return next('/admin')
      if (!data.user.role || !['tenant_admin', 'super_admin'].includes(data.user.role)) return next('/manage')
    } catch { return next('/manage') }
  }
  next()
})

export default router
