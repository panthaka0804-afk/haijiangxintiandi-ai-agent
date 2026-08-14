// API 基础配置（build 时用 VITE_API_BASE 注入公网后端地址；为空则同源）
const BASE_URL = import.meta.env.VITE_API_BASE || ''

async function request(url, options = {}) {
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers
    },
    ...options
  }

  try {
    const resp = await fetch(BASE_URL + url, config)
    const data = await resp.json()
    return data
  } catch (e) {
    return { ok: false, error: '网络错误，请稍后重试' }
  }
}

// ========== 会话/认证 ==========
export function getSession() {
  return request('/api/session')
}

export function login(username, password, admin = false) {
  return request('/login', {
    method: 'POST',
    body: JSON.stringify({ username, password, admin })
  })
}

export function logout() {
  return request('/logout', { method: 'POST' })
}

// ========== 后台智能化模块 ==========
export function getAdminRfm() {
  return request('/api/admin/rfm')
}
export function getFeedbackSentiment() {
  return request('/api/admin/feedback/sentiment')
}
export function getDailyReport() {
  return request('/api/admin/daily-report')
}

// ========== 后台智能运营中心 · 衍生功能（17 项） ==========
export function getRecallCandidates() {
  return request('/api/admin/recall-candidates')
}
export function getRepurchase() {
  return request('/api/admin/repurchase')
}
export function getHighValue() {
  return request('/api/admin/high-value')
}
export function getTierSprint() {
  return request('/api/admin/tier-sprint')
}
export function getFeedbackAlerts() {
  return request('/api/admin/feedback/alerts')
}
export function followFeedbackAlert(feedbackId, note = '') {
  return request('/api/admin/feedback/alerts/follow', {
    method: 'POST',
    body: JSON.stringify({ feedback_id: feedbackId, note })
  })
}
export function getFeedbackPainpoints() {
  return request('/api/admin/feedback/painpoints')
}
export function getMerchantSentiment() {
  return request('/api/admin/feedback/merchant-sentiment')
}
export function getFeedbackTrend() {
  return request('/api/admin/feedback/trend')
}
export function getReportPeriod(period = 'weekly') {
  return request('/api/admin/report-period?period=' + period)
}
export function getAnomaly() {
  return request('/api/admin/anomaly')
}
export function getKpi() {
  return request('/api/admin/kpi')
}
export function updateKpi(metric, target) {
  return request('/api/admin/kpi', {
    method: 'POST',
    body: JSON.stringify({ metric, target })
  })
}
export function getActivityRoi() {
  return request('/api/admin/activity-roi')
}
export function getPushCopy(payload) {
  return request('/api/admin/push-copy', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}
export function getAdvisor(question) {
  return request('/api/admin/advisor', {
    method: 'POST',
    body: JSON.stringify({ question })
  })
}
export function getLeasing() {
  return request('/api/admin/leasing')
}
export function getMarketingCalendar() {
  return request('/api/admin/marketing-calendar')
}
export function getTimeslotHeat() {
  return request('/api/admin/timeslot-heat')
}

// ========== 聊天 ==========
export function sendChat(message, largeFont = false) {
  return request('/api/public/chat', {
    method: 'POST',
    body: JSON.stringify({ message, large_font: largeFont })
  })
}

export function clearChat() {
  return request('/api/chat/clear', { method: 'POST' })
}

// ========== 会员 ==========
export function registerMember(displayName, phone) {
  return request('/api/member/register', {
    method: 'POST',
    body: JSON.stringify({ display_name: displayName, phone })
  })
}

export function lookupMember(phone) {
  return request('/api/member/lookup', {
    method: 'POST',
    body: JSON.stringify({ phone })
  })
}

export function getMemberPortal(phone) {
  return request('/api/member/portal', {
    method: 'POST',
    body: JSON.stringify({ phone })
  })
}

export function redeemPoints(phone, redeemId) {
  return request('/api/member/redeem', {
    method: 'POST',
    body: JSON.stringify({ phone, redeem_id: redeemId })
  })
}

export function getMemberCoupons(phone) {
  return request('/api/member/coupons', {
    method: 'POST',
    body: JSON.stringify({ phone })
  })
}

// ========== 知识库 ==========
export function getKnowledgeBase(params = {}) {
  const query = new URLSearchParams(params).toString()
  return request('/api/kb' + (query ? '?' + query : ''))
}

export function createKnowledge(data) {
  return request('/api/kb', {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

export function updateKnowledge(id, data) {
  return request('/api/kb/' + id, {
    method: 'PUT',
    body: JSON.stringify(data)
  })
}

export function deleteKnowledge(id) {
  return request('/api/kb/' + id, { method: 'DELETE' })
}

// ========== 工单 ==========
export function getOrders(params = {}) {
  const query = new URLSearchParams(params).toString()
  return request('/api/admin/orders' + (query ? '?' + query : ''))
}

export function createOrder(data) {
  return request('/api/orders', {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

export function updateOrder(id, data) {
  return request('/api/admin/orders/' + id, {
    method: 'PUT',
    body: JSON.stringify(data)
  })
}

// ========== 导航 ==========
export function searchNav(keyword) {
  return request('/api/nav/search?q=' + encodeURIComponent(keyword))
}

export function getFloors() {
  return request('/api/nav/floors')
}

// ========== 场地报价 ==========
export function getVenueQuotation(data) {
  return request('/api/venue/quotation', {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

// ========== 后台管理 ==========
export function getDashboardStats() {
  return request('/api/dashboard')
}

export function getAdminMembers(params = {}) {
  const query = new URLSearchParams(params).toString()
  return request('/api/admin/members' + (query ? '?' + query : ''))
}

export function updateAdminMember(id, data) {
  return request('/api/admin/member/' + id, {
    method: 'PUT',
    body: JSON.stringify(data)
  })
}

export function deleteAdminMember(id) {
  return request('/api/admin/member/' + id, { method: 'DELETE' })
}

export function getUsers(params = {}) {
  const query = new URLSearchParams(params).toString()
  return request('/api/users' + (query ? '?' + query : ''))
}

export function createUser(data) {
  return request('/api/users', {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

export function getTenants() {
  return request('/api/tenants')
}

export function updateTenant(id, data) {
  return request('/api/tenants/' + id, {
    method: 'PUT',
    body: JSON.stringify(data)
  })
}

export function getBarcode(text) {
  return request('/api/barcode', {
    method: 'POST',
    body: JSON.stringify({ text })
  })
}

// ========== 商户 ==========
export function getShops() {
  return request('/api/shops')
}

export function getShopDetail(id) {
  return request('/api/shops/' + id)
}

// ========== 优惠券 ==========
export function getOffers() {
  return request('/api/offers')
}
// 优惠券管理（上架/编辑/下架/删除）
export function getAdminOffers() {
  return request('/api/admin/offers')
}
export function createOffer(payload) {
  return request('/api/admin/offers', { method: 'POST', body: JSON.stringify(payload) })
}
export function updateOffer(id, payload) {
  return request('/api/admin/offers/' + id, { method: 'PUT', body: JSON.stringify(payload) })
}
export function toggleOffer(id) {
  return request('/api/admin/offers/' + id + '/toggle', { method: 'POST' })
}
export function deleteOffer(id) {
  return request('/api/admin/offers/' + id, { method: 'DELETE' })
}

// ========== 积分商城 ==========
export function getRedeemGoods() {
  return request('/api/redeem')
}

// ========== 停车 ==========
export function queryParking(data) {
  return request('/api/parking/query', {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

export function payParking(data) {
  return request('/api/parking/pay', {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

// ========== 无感积分停车 ==========
export function bindPlate(data) {
  return request('/api/parking/bind', { method: 'POST', body: JSON.stringify(data) })
}
export function myPlates() {
  return request('/api/parking/my-plates')
}
export function unbindPlate(data) {
  return request('/api/parking/unbind', { method: 'POST', body: JSON.stringify(data) })
}
export function redeemParkingCoupon() {
  return request('/api/parking/redeem-coupon', { method: 'POST', body: '{}' })
}
export function parkingEntry(data) {
  return request('/api/parking/entry', { method: 'POST', body: JSON.stringify(data) })
}
export function parkingExit(data) {
  return request('/api/parking/exit', { method: 'POST', body: JSON.stringify(data) })
}

// ========== 兴趣社（活动驱动轻组织） ==========
export function getInterestClubs(phone) {
  return request('/api/interest-clubs' + (phone ? '?phone=' + encodeURIComponent(phone) : ''))
}
export function joinInterestClub(clubId, phone, name, joined) {
  return request('/api/interest-club/join', {
    method: 'POST',
    body: JSON.stringify({ club_id: clubId, phone, name, joined })
  })
}
export function getClubEvents(params = {}) {
  const query = new URLSearchParams(params).toString()
  return request('/api/club-events' + (query ? '?' + query : ''))
}
export function getClubEventDetail(eventId, phone) {
  return request('/api/club-event/detail?event_id=' + eventId + (phone ? '&phone=' + encodeURIComponent(phone) : ''))
}
export function joinClubEvent(eventId, phone, name) {
  return request('/api/club-event/join', {
    method: 'POST',
    body: JSON.stringify({ event_id: eventId, phone, name })
  })
}
export function sendClubEventMessage(eventId, phone, name, content) {
  return request('/api/club-event/message', {
    method: 'POST',
    body: JSON.stringify({ event_id: eventId, phone, name, content })
  })
}
export function getMyClubs(phone) {
  return request('/api/club-event/my?phone=' + encodeURIComponent(phone))
}

// ========== 会员互赠 / 人脉引荐（邻里特权） ==========
export function getGiftQuota(phone) {
  return request('/api/gift/quota', { method: 'POST', body: JSON.stringify({ phone }) })
}
export function sendGift(phone, friendPhone, friendName) {
  return request('/api/gift/send', {
    method: 'POST',
    body: JSON.stringify({ phone, friend_phone: friendPhone, friend_name: friendName })
  })
}
export function redeemGift(phone, code) {
  return request('/api/gift/redeem', {
    method: 'POST',
    body: JSON.stringify({ phone, code })
  })
}
export function bindReferrer(phone, name, code) {
  return request('/api/referral/bind', {
    method: 'POST',
    body: JSON.stringify({ phone, name, code })
  })
}
export function recordConsumption(phone, amount, source = '邻里消费') {
  return request('/api/consumption/record', {
    method: 'POST',
    body: JSON.stringify({ phone, amount, source })
  })
}

// ========== 邻里帮悬赏墙 ==========
export function listNeighborHelp(scope = 'wall', phone = '') {
  return request('/api/neighbor-help/list?scope=' + encodeURIComponent(scope) + (phone ? '&phone=' + encodeURIComponent(phone) : ''))
}
export function publishNeighborHelp(payload) {
  return request('/api/neighbor-help/publish', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}
export function acceptNeighborHelp(phone, helpNo) {
  return request('/api/neighbor-help/accept', {
    method: 'POST',
    body: JSON.stringify({ phone, help_no: helpNo })
  })
}
export function completeNeighborHelp(phone, helpNo) {
  return request('/api/neighbor-help/complete', {
    method: 'POST',
    body: JSON.stringify({ phone, help_no: helpNo })
  })
}
export function confirmNeighborHelp(phone, helpNo) {
  return request('/api/neighbor-help/confirm', {
    method: 'POST',
    body: JSON.stringify({ phone, help_no: helpNo })
  })
}
export function cancelNeighborHelp(phone, helpNo) {
  return request('/api/neighbor-help/cancel', {
    method: 'POST',
    body: JSON.stringify({ phone, help_no: helpNo })
  })
}

// ========== 便民生活：车主权益 / 预约 / 签到 / 会员日 ==========
export function getLifeCards(phone) {
  return request('/api/life/cards', { method: 'POST', body: JSON.stringify({ phone }) })
}
export function subscribeLifeCard(phone, planType) {
  return request('/api/life/cards/subscribe', { method: 'POST', body: JSON.stringify({ phone, plan_type: planType }) })
}
// 母婴室
export function getNurserySlots() {
  return request('/api/life/nursery/slots', { method: 'GET' })
}
export function bookNursery(phone, payload) {
  return request('/api/life/nursery/book', { method: 'POST', body: JSON.stringify({ phone, ...payload }) })
}
export function cancelNursery(phone, id) {
  return request('/api/life/nursery/cancel', { method: 'POST', body: JSON.stringify({ phone, id }) })
}
export function getMyNursery(phone) {
  return request('/api/life/nursery/mine', { method: 'POST', body: JSON.stringify({ phone }) })
}
// 宠物托管
export function getPetSlots() {
  return request('/api/life/pet/slots', { method: 'GET' })
}
export function bookPet(phone, payload) {
  return request('/api/life/pet/book', { method: 'POST', body: JSON.stringify({ phone, ...payload }) })
}
export function cancelPet(phone, id) {
  return request('/api/life/pet/cancel', { method: 'POST', body: JSON.stringify({ phone, id }) })
}
export function getMyPet(phone) {
  return request('/api/life/pet/mine', { method: 'POST', body: JSON.stringify({ phone }) })
}
// 签到抽奖
export function getCheckinStatus(phone) {
  return request('/api/life/checkin/status', { method: 'POST', body: JSON.stringify({ phone }) })
}
export function doCheckin(phone) {
  return request('/api/life/checkin', { method: 'POST', body: JSON.stringify({ phone }) })
}
// 周三会员日
export function getMemberDayStatus(phone) {
  return request('/api/life/member-day/status', { method: 'POST', body: JSON.stringify({ phone }) })
}
export function claimMemberDay(phone) {
  return request('/api/life/member-day/claim', { method: 'POST', body: JSON.stringify({ phone }) })
}

// ========== 会员专属内容（新品试吃 / 内测名额 / 专属体验） ==========
export function getMemberExclusives(phone) {
  return request('/api/member/exclusives', {
    method: 'POST',
    body: JSON.stringify({ phone: phone || '' })
  })
}
export function claimExclusive(phone, id) {
  return request('/api/member/exclusive/claim', {
    method: 'POST',
    body: JSON.stringify({ phone, id })
  })
}

// ========== 会员自动化（沉默召回 / 生日·周年庆专属权益日） ==========
export function getAutoCoupons(phone) {
  return request('/api/member/auto-coupons', {
    method: 'POST',
    body: JSON.stringify({ phone: phone || '' })
  })
}
export function claimAutoCoupon(phone, id) {
  return request('/api/member/auto-coupon/claim', {
    method: 'POST',
    body: JSON.stringify({ phone, id })
  })
}

// 通用 HTTP 客户端（ActivityDetail 等使用）
const http = {
  get: (url, opts) => {
    let u = url
    if (opts && opts.params) {
      const qs = new URLSearchParams(opts.params).toString()
      u += (url.includes('?') ? '&' : '?') + qs
    }
    return request(u, { method: 'GET', headers: opts?.headers })
  },
  post: (url, data, opts) => request(url, { method: 'POST', body: JSON.stringify(data), ...opts }),
  put: (url, data, opts) => request(url, { method: 'PUT', body: JSON.stringify(data), ...opts }),
  delete: (url, opts) => request(url, { method: 'DELETE', ...opts }),
}
export default http
