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
