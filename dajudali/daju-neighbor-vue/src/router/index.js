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
  { path: '/map3d', name: 'map3d', component: () => import('@/views/c-end/Map3D.vue'), meta: { title: '3D地图 - 海江新天地' } },
  { path: '/shops', name: 'shops', component: () => import('@/views/c-end/ShopsList.vue'), meta: { title: '商户列表 - 海江新天地' } },
  { path: '/shops/:id', name: 'shop-detail', component: () => import('@/views/c-end/ShopDetail.vue'), meta: { title: '商户详情 - 海江新天地' } },
  { path: '/parking', name: 'parking', component: () => import('@/views/c-end/ParkingPage.vue'), meta: { title: '停车缴费 - 海江新天地' } },
  { path: '/parking/bind', name: 'parking-bind', component: () => import('@/views/c-end/ParkingBind.vue'), meta: { title: '管理车辆 - 海江新天地' } },
  { path: '/activities', name: 'activities', component: () => import('@/views/c-end/ActivitiesPage.vue'), meta: { title: '活动报名 - 海江新天地' } },
  { path: '/activities/:id', name: 'activity-detail', component: () => import('@/views/c-end/ActivityDetail.vue'), meta: { title: '活动详情 - 海江新天地' } },
  { path: '/redeem', name: 'redeem', component: () => import('@/views/c-end/RedeemPage.vue'), meta: { title: '积分商城 - 海江新天地' } },
  { path: '/redeem/:id', name: 'redeem-detail', component: () => import('@/views/c-end/RedeemDetail.vue'), meta: { title: '兑换详情 - 海江新天地' } },
  { path: '/member', name: 'member', component: () => import('@/views/c-end/MemberPortal.vue'), meta: { title: '会员中心 - 海江新天地' } },
  { path: '/my-coupons', name: 'my-coupons', component: () => import('@/views/c-end/MyCoupons.vue'), meta: { title: '我的优惠券 - 海江新天地' } },
  { path: '/messages', name: 'messages', component: () => import('@/views/c-end/MessageCenter.vue'), meta: { title: '消息中心 - 海江新天地' } },
  { path: '/exclusive', name: 'exclusive', component: () => import('@/views/c-end/ExclusivePage.vue'), meta: { title: '会员专属 - 海江新天地' } },
  { path: '/community', name: 'community', component: () => import('@/views/c-end/CommunityFeed.vue'), meta: { title: '邻里圈 - 海江新天地' } },
  { path: '/group-buy', name: 'group-buy', component: () => import('@/views/c-end/GroupBuy.vue'), meta: { title: '邻里拼团 - 海江新天地' } },
  { path: '/interest-club', name: 'interest-club', component: () => import('@/views/c-end/InterestClub.vue'), meta: { title: '兴趣社 - 海江新天地' } },
  { path: '/neighbor-help', name: 'neighbor-help', component: () => import('@/views/c-end/NeighborHelp.vue'), meta: { title: '邻里帮 - 海江新天地' } },
  { path: '/life', name: 'life-service', component: () => import('@/views/c-end/LifeService.vue'), meta: { title: '便民生活 - 海江新天地' } },
  { path: '/merchant', name: 'merchant', component: () => import('@/views/c-end/MerchantPage.vue'), meta: { title: '招商合作 - 海江新天地' } },
  { path: '/md', name: 'merchant-dashboard', component: () => import('@/views/c-end/MerchantDashboard.vue'), meta: { title: '商户看板 - 海江新天地' } },
  { path: '/call-display', name: 'call-display', component: () => import('@/views/c-end/CallDisplay.vue'), meta: { title: '叫号大屏 - 海江新天地' } },
  { path: '/organizer', name: 'organizer', component: () => import('@/views/c-end/OrganizerPortal.vue'), meta: { title: '主理人中心 - 海江新天地' } },
  { path: '/biz', name: 'biz', component: () => import('@/views/c-end/BusinessCoop.vue'), meta: { title: '商务合作 - 海江新天地' } },
  { path: '/property', name: 'property', component: () => import('@/views/c-end/PropertyService.vue'), meta: { title: '物业报修与投诉 - 海江新天地' } },
  // 旧独立登录页已并入首页，重定向避免黑屏
  { path: '/login', redirect: '/' },
  // 法律协议
  { path: '/user-agreement', name: 'user-agreement', component: () => import('@/views/c-end/UserAgreement.vue'), meta: { title: '用户协议 - 海江新天地' } },
  { path: '/privacy-policy', name: 'privacy-policy', component: () => import('@/views/c-end/PrivacyPolicy.vue'), meta: { title: '隐私政策 - 海江新天地' } },
  { path: '/about', name: 'about', component: () => import('@/views/c-end/AboutUs.vue'), meta: { title: '关于我们 - 海江新天地' } },
  { path: '/settings', name: 'settings', component: () => import('@/views/c-end/Settings.vue'), meta: { title: '设置 - 海江新天地' } },
  // 活动管理 - 独立页面，自带登录
  { path: '/act-admin', name: 'act-admin', component: () => import('@/views/admin/ActivitiesAdmin.vue'), meta: { title: '活动管理 - 海江新天地' } },

  // 后台管理路由
  { path: '/manage', name: 'admin-login', component: () => import('@/views/admin/AdminLogin.vue'), meta: { title: '后台登录 - 海江新天地' } },
  {
    path: '/admin', name: 'admin', component: () => import('@/views/admin/Dashboard.vue'),
    meta: { title: '管理后台 - 海江新天地', requiresAdmin: true },
    children: [
      { path: '', redirect: { name: 'admin-intelligence' } },
      { path: 'dashboard', name: 'admin-dashboard', component: () => import('@/views/admin/AdminDashboard.vue'), meta: { title: '数据看板' } },
      { path: 'kb', name: 'admin-kb', component: () => import('@/views/admin/KnowledgeBase.vue'), meta: { title: '知识库管理' } },
      { path: 'orders', name: 'admin-orders', component: () => import('@/views/admin/WorkOrders.vue'), meta: { title: '工单管理' } },
      { path: 'members', name: 'admin-members', component: () => import('@/views/admin/Members.vue'), meta: { title: '会员管理' } },
      { path: 'users', name: 'admin-users', component: () => import('@/views/admin/Users.vue'), meta: { title: '用户管理' } },
      { path: 'settings', name: 'admin-settings', component: () => import('@/views/admin/Settings.vue'), meta: { title: '系统设置' } },
      { path: 'activities', name: 'admin-activities', component: () => import('@/views/admin/ActivitiesAdmin.vue'), meta: { title: '活动管理' } },
      { path: 'shops', name: 'admin-shops', component: () => import('@/views/admin/ShopsAdmin.vue'), meta: { title: '商户管理' } },
      { path: 'offers', name: 'admin-offers', component: () => import('@/views/admin/OffersAdmin.vue'), meta: { title: '优惠券管理' } },
      { path: 'redeem', name: 'admin-redeem', component: () => import('@/views/admin/RedeemAdmin.vue'), meta: { title: '积分商城管理' } },
      { path: 'human-chat', name: 'admin-human-chat', component: () => import('@/views/admin/HumanChatAdmin.vue'), meta: { title: '人工客服' } },
      { path: 'feedback', name: 'admin-feedback', component: () => import('@/views/admin/FeedbackAdmin.vue'), meta: { title: '满意度评价' } },
      { path: 'insights', name: 'admin-insights', component: () => import('@/views/admin/InsightsAdmin.vue'), meta: { title: '运营洞察' } },
      { path: 'intelligence', name: 'admin-intelligence', component: () => import('@/views/admin/AdminIntelligence.vue'), meta: { title: '智能运营中心' } },
      { path: 'subsidy', name: 'admin-subsidy', component: () => import('@/views/admin/AdminSubsidy.vue'), meta: { title: '商户扶持' } },
      { path: 'notify', name: 'admin-notify', component: () => import('@/views/admin/NotifyAdmin.vue'), meta: { title: '触达中心' } },
      // 后台未知子路径兜底：避免「点进去白屏」，统一暗色 404
      { path: ':pathMatch(.*)*', name: 'admin-not-found', component: () => import('@/views/admin/AdminNotFound.vue'), meta: { title: '页面不存在' } },
    ],
  },
  { path: '/platform', name: 'platform', component: () => import('@/views/admin/Platform.vue'), meta: { title: '平台管理 - 海江新天地', requiresSuperAdmin: true } },
  // 全局兜底：任何未知顶层路径统一回 C 端首页，杜绝白屏
  { path: '/:pathMatch(.*)*', redirect: { name: 'chat' } },
]

const router = createRouter({
  history: createWebHistory('/vue/'),
  routes,
})

function isAdminContext(to) {
  return to.meta.requiresAdmin || to.meta.requiresSuperAdmin ||
    to.path.startsWith('/admin') || to.path.startsWith('/platform')
}

router.beforeEach(async (to, from, next) => {
  // 后台页面标题统一收敛为「… · 海江新天地管理后台」，杜绝 C 端「小江AI」串台
  if (isAdminContext(to)) {
    const t = to.meta.title
    document.title = (t ? t + ' · ' : '') + '海江新天地管理后台'
  } else {
    document.title = to.meta.title || '海江新天地'
  }
  if (to.meta.requiresAdmin || to.meta.requiresSuperAdmin || to.path.startsWith('/admin')) {
    try {
      const resp = await fetch('/api/session')
      const data = await resp.json()
      if (!data.ok) return next('/manage')
      const role = data.user.role
      const STAFF = ['tenant_admin', 'super_admin', 'admin', 'operator', 'cs']
      if (!STAFF.includes(role)) return next('/manage')
      if (to.meta.requiresSuperAdmin && role !== 'super_admin') return next('/admin')
      const perms = data.user.perms || []
      // 账号管理 / 系统设置 仅 user.manage 权限（超管/管理员）
      if ((to.path === '/admin/users' || to.path === '/admin/settings') && !perms.includes('user.manage')) return next('/admin')
    } catch { return next('/manage') }
  }
  next()
})

export default router
