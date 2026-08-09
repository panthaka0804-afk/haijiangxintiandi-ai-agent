<template>
  <div class="home-tab">
    <div class="hero-banner">
      <img :src="p.mallBanner" alt="" class="hero-bg" />
      <div class="hero-gradient"></div>
      <div class="hero-slogan">
        <div class="slogan-pill">
          <img :src="p.logoHero" alt="海江新天地" class="slogan-logo" />
          <span class="slogan-text">五湖四海皆兄弟 吃喝玩乐到海江</span>
        </div>
      </div>
    </div>

    <div class="member-card" :class="{ 'mc-light': loggedIn }">
      <template v-if="!loggedIn">
        <div class="mc-top">
          <div class="mc-logo-circle">
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#E8E8E8" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
          </div>
          <div>
            <div class="mc-title">海江新天地</div>
            <div class="mc-subtitle">绑定手机号 · 即刻享受会员权益</div>
          </div>
        </div>
        <div class="mc-phone-row">
          <div class="mc-phone-input">
            <span class="mc-prefix">+86</span>
            <input v-model="phone" type="tel" maxlength="11" placeholder="请输入手机号" class="mc-input" />
          </div>
        </div>
        <button class="mc-btn" @click="handleLogin" :disabled="loading">{{ loading ? '绑定中...' : '绑定 / 登录' }}</button>
        <button v-if="isWechat" class="mc-btn mc-btn-wx" @click="wxQuickRegister">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="#fff"><path d="M8.691 2.188C3.891 2.188 0 5.476 0 9.53c0 2.212 1.17 4.203 3.002 5.55a.59.59 0 0 1 .213.665l-.39 1.48c-.019.07-.048.141-.048.213 0 .163.13.295.29.295a.33.33 0 0 0 .167-.054l1.903-1.114a.86.86 0 0 1 .717-.098 10.16 10.16 0 0 0 2.837.403c.276 0 .543-.027.811-.05-.857-2.578.157-4.972 1.932-6.446 1.703-1.415 3.882-1.98 5.853-1.838-.576-3.583-4.196-6.348-8.596-6.348zM5.785 5.991c.642 0 1.162.529 1.162 1.18a1.17 1.17 0 0 1-1.162 1.178A1.17 1.17 0 0 1 4.623 7.17c0-.651.52-1.18 1.162-1.18zm5.813 0c.642 0 1.162.529 1.162 1.18a1.17 1.17 0 0 1-1.162 1.178 1.17 1.17 0 0 1-1.162-1.178c0-.651.52-1.18 1.162-1.18zm5.34 2.867c-1.797-.052-3.746.512-5.28 1.786-1.72 1.428-2.687 3.72-1.78 6.22.942 2.453 3.666 4.229 6.884 4.229.826 0 1.622-.12 2.361-.336a.72.72 0 0 1 .598.082l1.584.926a.28.28 0 0 0 .14.047c.136 0 .245-.111.245-.247 0-.06-.023-.12-.038-.177l-.327-1.233a.58.58 0 0 1 .023-.156.49.49 0 0 1 .155-.397c1.526-1.12 2.5-2.745 2.5-4.56 0-3.132-2.765-5.681-6.065-5.681zm-4.172 3.077c.534 0 .967.44.967.982a.975.975 0 0 1-.967.983.975.975 0 0 1-.968-.983c0-.542.434-.982.968-.982zm4.3 0c.535 0 .967.44.967.982a.975.975 0 0 1-.967.983.975.975 0 0 1-.968-.983c0-.542.434-.982.968-.982z"/></svg>
          微信一键注册
        </button>
        <div class="mc-agree" @click="agreed = !agreed">
          <span class="mc-agree-box" :class="{ checked: agreed }">
            <svg v-if="agreed" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#E8E8E8" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
          </span>
          <span class="mc-agree-text">登录即表示同意<a class="mc-link" href="/vue/user-agreement.html" target="_blank" @click.stop>《用户协议》</a>和<a class="mc-link" href="/vue/privacy-policy.html" target="_blank" @click.stop>《隐私政策》</a></span>
        </div>
      </template>

      <div v-else class="member-logged">
        <div class="mcard">
          <!-- 上半区：左名 + 右上大圆按钮 & 胶囊 -->
          <div class="mc-upper">
            <div class="mc-left">
              <div class="mc-name">{{ displayName }}</div>
              <div class="mc-upgrade" v-if="needPoints > 0">距离升级到{{ nextLevelName }}还需 <b>{{ needPoints }}</b></div>
              <div class="mc-upgrade" v-else-if="memberInfo && memberRank === 'L5'">已是最高等级 · 至尊之选</div>
            </div>
            <div class="mc-right">
              <button class="mc-big-round" @click="triggerUpload" title="更换头像">
                <img v-if="avatarUrl" :src="avatarUrl" alt="" />
                <svg v-else width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M4 21v-1a8 8 0 0 1 16 0v1"/></svg>
                <input ref="avatarInput" type="file" accept="image/*" style="display:none" @change="onAvatarFile" />
              </button>
              <div class="mc-pill">{{ memberInfo && memberInfo.membership_level || '普卡' }}</div>
            </div>
          </div>

          <!-- 弧形进度条 -->
          <div class="mc-arc">
            <svg class="mc-arc-svg" viewBox="0 0 300 44" preserveAspectRatio="none">
              <!-- 凹槽内壁（暗） -->
              <path d="M10 38 Q150 -6 290 38" fill="none" stroke="rgba(0,0,0,0.42)" stroke-width="9" stroke-linecap="round"/>
              <!-- 槽底反光（下移，形成凹陷明暗差） -->
              <path d="M10 39.5 Q150 -4.5 290 39.5" fill="none" stroke="rgba(255,255,255,0.26)" stroke-width="9" stroke-linecap="round"/>
              <!-- 进度填充（嵌在槽内） -->
              <path d="M10 38 Q150 -6 290 38" fill="none" stroke="#E0E0E0" stroke-width="5" stroke-linecap="round" :stroke-dasharray="arcLen" :stroke-dashoffset="arcDash"/>
              <circle :cx="arcDotX" :cy="arcDotY" r="6.5" fill="#E0E0E0" stroke="#fff" stroke-width="2"/>
            </svg>
          </div>

          <!-- 底部：三列数据 + 右侧三个圆形按钮 -->
          <div class="mc-lower">
            <div class="mc-cols">
              <div class="mc-col" @click="emit('switchTab', 'offers')">
                <div class="mc-col-num">{{ memberInfo && memberInfo.coupon_count != null ? memberInfo.coupon_count : 0 }}</div>
                <div class="mc-col-label">优惠券</div>
              </div>
            </div>
            <div class="mc-rounds">
              <button class="mc-round" @click="router.push('/member')" title="会员中心">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M4 21v-1a8 8 0 0 1 16 0v1"/></svg>
              </button>
              <button class="mc-round" @click="emit('switchTab', 'offers')" title="优惠券">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 12v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-8"/><path d="M22 7H2v5h20z"/></svg>
              </button>
              <button class="mc-round" @click="openQrCode" title="会员码">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><path d="M21 14v3a1 1 0 01-1 1h-3M14 21h3a1 1 0 001-1v-3"/></svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <teleport to="body">
      <div v-if="showQr" class="qr-overlay" @click.self="showQr = false">
        <div class="qr-modal">
          <div class="qr-close" @click="showQr = false">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#999" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </div>
          <div class="qr-title">会员二维码</div>
          <div class="qr-body">
            <div class="qr-code-box">
              <img v-if="qrSrc" :src="qrSrc" width="160" height="160" style="background:#1C1C1E;border-radius:8px" />
              <svg v-else width="160" height="160" viewBox="0 0 160 160" fill="none"><rect x="60" y="60" width="40" height="40" rx="4" stroke="#555" stroke-width="2"/><line x1="80" y1="68" x2="80" y2="92" stroke="#555" stroke-width="2"/><line x1="68" y1="80" x2="92" y2="80" stroke="#555" stroke-width="2"/></svg>
            </div>
            <div class="qr-user">{{ displayName }}</div>
            <div class="qr-tip">展示此二维码给商户扫描</div>
          </div>
        </div>
      </div>
    </teleport>

    <div class="quick-links">
      <div class="qlink" v-for="e in entries" :key="e.label" @click="go(e.route)">
        <div class="qlink-icon" :class="{ active: e.active }" :style="{ background: e.bg, borderColor: e.bd }">
          <span class="qlink-glyph" v-html="iconSvg(e.icon)"></span>
        </div>
        <span class="qlink-label">{{ e.label }}</span>
      </div>
    </div>

    <div class="section-label">
      <span class="section-en">offers</span>
      <span class="section-cn">优惠</span>
    </div>

    <div class="daily-deal" @click="$router.push('/offers')">
      <svg class="dd-illus" viewBox="0 0 120 60" fill="none" preserveAspectRatio="xMinYMid slice"><path d="M78 10 l6 14 15 2 -11 10 3 15 -13 -8 -13 8 3 -15 -11 -10 15 -2 z"/><circle cx="40" cy="44" r="8"/><path d="M40 37 v14 M33 44 h14"/></svg>
      <div class="dd-icon-box">
        <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#E8E8E8" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/>
        </svg>
      </div>
      <div class="dd-left">
        <div class="dd-title">每日特惠</div>
        <div class="dd-desc">精选商户限时折扣，天天有好价</div>
      </div>
      <div class="dd-right">
        <span class="dd-btn">立即查看</span>
      </div>
    </div>

    <div class="section-label">
      <span class="section-en">service</span>
      <span class="section-cn">服务</span>
    </div>

    <div class="biz-modules">
      <div class="biz-hero" @click="go('/activities')">
        <div class="biz-hero-bg"></div>
        <svg class="biz-hero-illus" viewBox="0 0 120 100" fill="none" preserveAspectRatio="xMinYMid slice"><path d="M28 30 h44 a8 8 0 0 1 8 8 v14 a8 8 0 0 1 -8 8 H44 l-12 11 v-11 h-4 a8 8 0 0 1 -8 -8 V38 a8 8 0 0 1 8 -8 z"/><path d="M52 48 l6 6 12 -12"/></svg>
        <div class="biz-hero-content">
          <div class="biz-hero-icon">
            <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
            </svg>
          </div>
          <div class="biz-hero-title">社区聚乐部</div>
          <div class="biz-hero-desc">活动报名 · 邻里社群 · 精彩生活</div>
        </div>
        <span class="biz-hero-btn">立即查看</span>
      </div>
      <div class="biz-grid">
        <div class="biz-card" v-for="m in bizModules" :key="m.label" @click="go(m.route)">
          <div class="biz-card-bg" :style="{background: m.grad}"></div>
          <svg class="biz-card-illus" v-html="m.illus" viewBox="0 0 120 100" fill="none" preserveAspectRatio="xMinYMid slice"></svg>
          <div class="biz-card-content">
            <div class="biz-card-icon-sm">
              <svg v-html="m.icon" width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"></svg>
            </div>
            <div class="biz-card-title">{{ m.label }}</div>
            <div class="biz-card-desc">{{ m.desc }}</div>
          </div>
        </div>
      </div>
    </div>

    <div class="section-label">
      <span class="section-en">recommended shops</span>
      <span class="section-cn">推荐商铺</span>
    </div>
    <div class="shop-list">
      <div v-for="s in shops" :key="s.id" class="shop-card" @click="go('/shops/' + s.id)">
        <svg class="shop-illus" v-html="s.illus" viewBox="0 0 120 100" fill="none" preserveAspectRatio="xMinYMid slice"></svg>
        <div class="shop-logo" :style="{ background: s.color, color: logoTextColor(s.color) }">{{ s.name }}</div>
        <div class="shop-info">
          <div class="shop-name">{{ s.name }}</div>
          <div class="shop-meta">{{ s.floor }} · {{ s.category }}</div>
        </div>
        <svg class="shop-arrow" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#E8E8E8" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { placeholderImages as p } from '@/assets/placeholders'
import allShops from '@/data/shops'
import http from '@/api'
import { useMemberStore } from '@/stores/member'

const emit = defineEmits(['switchTab'])
const router = useRouter()
const memberStore = useMemberStore()

// 统一会员数据：所有页面（首页会员卡 / 会员中心 / 更多页）共用 memberStore，登录后自动同步
function buildMember(u) {
  return {
    phone: (u && u.phone) || '',
    display_name: (u && u.display_name) || '海江会员',
    membership_level: (u && u.membership_level) || '普卡',
    points: (u && u.points) || 0,
    discount: (u && u.discount) || '',
    headimgurl: (u && u.headimgurl) || '',
    coupon_count: (u && u.coupon_count) || 0,
  }
}

// 新拟态：把图标线条渲染成内嵌 SVG（stroke=currentColor），配合 engraved 阴影做"刻入卡面"效果
const iconSvg = (paths) =>
  `<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round">${paths}</svg>`

const isWechat = /micromessenger/i.test(navigator.userAgent || '')
const WX_APPID = 'wxbdd219b39de37798'

const phone = ref('')
const agreed = ref(true)
const loading = ref(false)
const showQr = ref(false)
const qrSrc = ref('')
const loggedIn = ref(false)
const displayName = ref('')
const avatarUrl = ref('')
const memberInfo = ref(null)
const avatarInput = ref(null)
const memberExpanded = ref(false)

const memberRank = computed(() => {
  if (!memberInfo.value) return 'L1'
  const pts = memberInfo.value.points || 0
  if (pts >= 20000) return 'L5'
  if (pts >= 10000) return 'L4'
  if (pts >= 5000) return 'L3'
  if (pts >= 2000) return 'L2'
  return 'L1'
})

const upgradeNextLevel = {
  'L1': { name: '伙伴', need: 2000 },
  'L2': { name: '金卡', need: 5000 },
  'L3': { name: '铂金卡', need: 10000 },
  'L4': { name: '钻石卡', need: 20000 },
}

// 图片样式：升级到 X 还需 N 分
const nextLevelName = computed(() => {
  const next = upgradeNextLevel[memberRank.value]
  return next ? next.name : ''
})
const needPoints = computed(() => {
  const next = upgradeNextLevel[memberRank.value]
  if (!next) return 0
  if (!memberInfo.value) return 200
  return Math.max(0, next.need - (memberInfo.value.points || 0))
})

const upgradeHint = computed(() => {
  if (!memberInfo.value) return ''
  const rank = memberRank.value
  if (rank === 'L5') return '最高等级 • 至尊之选'
  const next = upgradeNextLevel[rank]
  if (!next) return ''
  const need = next.need - (memberInfo.value.points || 0)
  if (need <= 0) return '积分已达标，即将自动升级'
  return '再积 ' + need + ' 分升级 ' + next.name
})

const upgradePercent = computed(() => {
  if (!memberInfo.value) return 0
  const rank = memberRank.value
  if (rank === 'L5') return 100
  const cur = memberInfo.value.points || 0
  const prevNeeds = { 'L2': 2000, 'L3': 5000, 'L4': 10000, 'L5': 20000 }
  const next = upgradeNextLevel[rank]
  if (!next) return 100
  const prevNeed = prevNeeds[rank] || 0
  const range = next.need - prevNeed
  const progress = cur - prevNeed
  return Math.min(100, Math.max(0, Math.round((progress / range) * 100)))
})

// 弧形进度条几何（沿二次贝塞尔 Q150,-10 在 viewBox 300x40 上）
const arcLen = computed(() => {
  const p0 = [10, 38], p1 = [150, -6], p2 = [290, 38]
  const ab = Math.hypot(p1[0] - p0[0], p1[1] - p0[1])
  const bc = Math.hypot(p2[0] - p1[0], p2[1] - p1[1])
  return ab + bc // 折线近似弧长
})
const arcDash = computed(() => {
  const len = arcLen.value
  const pct = upgradePercent.value / 100
  return len * (1 - pct)
})
const arcDot = computed(() => {
  const pct = Math.min(0.999, Math.max(0.001, upgradePercent.value / 100))
  // 二次贝塞尔点：B(t) = (1-t)^2 P0 + 2(1-t)t P1 + t^2 P2
  const P0 = [10, 38], P1 = [150, -6], P2 = [290, 38]
  const mt = 1 - pct
  const x = mt * mt * P0[0] + 2 * mt * pct * P1[0] + pct * pct * P2[0]
  const y = mt * mt * P0[1] + 2 * mt * pct * P1[1] + pct * pct * P2[1]
  return { x, y }
})
const arcDotX = computed(() => arcDot.value.x)
const arcDotY = computed(() => arcDot.value.y)

onMounted(async () => {
  const urlParams = new URLSearchParams(window.location.search)
  const wxCode = urlParams.get('code')
  if (wxCode) {
    try {
      const wxRes = await http.post('/api/wx-auth', { code: wxCode })
      if (wxRes.ok && wxRes.user) {
        loggedIn.value = true
        displayName.value = wxRes.user.display_name || '会员'
        memberInfo.value = wxRes.user
        avatarUrl.value = wxRes.user.headimgurl || ''
        memberStore.setMember(buildMember(wxRes.user))
        const cleanUrl = window.location.origin + window.location.pathname
        window.history.replaceState({}, document.title, cleanUrl)
        return
      }
    } catch {}
  }
  try {
    const res = await http.get('/api/session')
    if (res.ok && res.user) {
      loggedIn.value = true
      displayName.value = res.user.display_name || '会员'
      avatarUrl.value = res.user.headimgurl || ''
      if (res.user.phone) {
        try {
          const minfo = await http.post('/api/member/lookup', { phone: res.user.phone })
          if (minfo.ok && minfo.member) {
            memberInfo.value = minfo.member
            memberStore.setMember(buildMember({ ...res.user, ...minfo.member }))
          }
        } catch {}
      } else if (res.user.display_name || res.user.headimgurl) {
        // 仅有微信信息（无手机号）也写入，保证头像/昵称同步
        memberStore.setMember(buildMember(res.user))
      }
    }
  } catch {}
})

async function handleLogin() {
  if (!agreed.value) return alert('请先同意用户协议')
  if (!/^1\d{10}$/.test(phone.value)) return alert('请输入正确的手机号')
  loading.value = true
  const p = phone.value.trim()
  try {
    const lookup = await http.post('/api/member/lookup', { phone: p })
    if (lookup.ok && lookup.member) {
      const res = await http.post('/login', { username: 'm' + p, password: 'member' + p })
      if (res.ok && res.user) {
        loggedIn.value = true
        memberInfo.value = lookup.member
        displayName.value = res.user.display_name || '会员'
        memberStore.setMember(buildMember({ phone: p, display_name: res.user.display_name, headimgurl: res.user.headimgurl, ...lookup.member }))
      } else {
        alert(res.error || '登录失败')
      }
    } else {
      const reg = await http.post('/api/member/register', { phone: p, display_name: '会员' + p.slice(-4) })
      if (reg.ok && reg.user) {
        const res2 = await http.post('/login', { username: 'm' + p, password: 'member' + p })
        if (res2.ok && res2.user) {
          loggedIn.value = true
          memberInfo.value = reg.user
          displayName.value = '会员' + p.slice(-4)
          memberStore.setMember(buildMember(reg.user))
        }
      } else {
        alert(reg.error || '注册失败')
      }
    }
  } catch (e) {
    alert('网络错误')
  }
  loading.value = false
}

async function wxQuickRegister() {
  if (!agreed.value) return alert('请先同意用户协议')
  const redirectUri = encodeURIComponent(window.location.origin + '/vue/')
  const wxAuthUrl = 'https://open.weixin.qq.com/connect/oauth2/authorize?appid=' + WX_APPID + '&redirect_uri=' + redirectUri + '&response_type=code&scope=snsapi_userinfo&state=wxreg#wechat_redirect'
  window.location.href = wxAuthUrl
}

async function openQrCode() {
  showQr.value = true
  try {
    const res = await http.get('/api/member/qrcode')
    if (res.ok && res.qr) { qrSrc.value = res.qr }
  } catch {}
}

function editName() {
  const n = prompt('修改昵称', displayName.value)
  if (n && n.trim()) {
    displayName.value = n.trim()
    http.put('/api/member/profile', { display_name: n }).catch(() => {})
  }
}

function triggerUpload() { avatarInput.value && avatarInput.value.click() }

async function doLogout() {
  await http.post('/logout')
  memberStore.logout()
  loggedIn.value = false
  memberInfo.value = null
  displayName.value = ''
  avatarUrl.value = ''
  phone.value = ''
}
function onAvatarFile(e) {
  const file = e.target.files && e.target.files[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => { avatarUrl.value = reader.result }
  reader.readAsDataURL(file)
}

const bizModules = [
  {
    label: '美食天地',
    desc: 'B1美食广场',
    route: '/shops',
    grad: 'linear-gradient(135deg, #2E2E2E 0%, #4A4A4A 60%, #D8D8D8 100%)',
    icon: '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
    illus: '<path d="M22 58 a34 14 0 0 0 68 0 Z"/><path d="M28 40 L58 60"/><path d="M44 38 L70 58"/><path d="M40 26 q6 -8 0 -16"/><path d="M58 28 q6 -8 0 -16"/>'
  },
  {
    label: '亲子乐园',
    desc: '3F儿童游乐',
    route: '/shops?floor=3',
    grad: 'linear-gradient(135deg, #3A3A3A 0%, #4A4A4A 60%, #C8C8C8 100%)',
    icon: '<circle cx="12" cy="8" r="4"/><path d="M8 21v-1a6 6 0 0112 0v1"/>',
    illus: '<circle cx="46" cy="38" r="17"/><path d="M46 55 v22"/><path d="M44 53 l4 4 6 -8"/><circle cx="82" cy="30" r="12"/><path d="M82 42 v16"/>'
  },
  {
    label: '生活服务',
    desc: '洗衣美甲维修',
    route: '/shops?floor=2',
    grad: 'linear-gradient(135deg, #3A3A3A 0%, #4A4A4A 60%, #C8C8C8 100%)',
    icon: '<path d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/>',
    illus: '<path d="M30 56 L60 32 L90 56"/><path d="M38 56 V74 H82 V56"/><rect x="53" y="61" width="13" height="13"/>'
  },
  {
    label: '停车缴费',
    desc: '在线缴费出场',
    route: 'parking',
    grad: 'linear-gradient(135deg, #3A3A3A 0%, #4A4A4A 60%, #C8C8C8 100%)',
    icon: '<rect x="3" y="10" width="18" height="10" rx="2"/><circle cx="7" cy="20" r="1.5"/><circle cx="17" cy="20" r="1.5"/><path d="M6 10V6a2 2 0 012-2h8a2 2 0 012 2v4"/>',
    illus: '<path d="M22 60 h58 v-16 h-12 l-8 -12 h-22 l-8 12 h-8 z"/><circle cx="42" cy="62" r="6"/><circle cx="76" cy="62" r="6"/>'
  }
]

const entries = [
  { label: '导航地图', route: 'nav', icon: '<path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"/><circle cx="12" cy="9" r="2.5"/>', active: false, bg: '#8B8B90', bd: '#6A6A6E' },
  { label: '优惠促销', route: 'offers', icon: '<path d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/><line x1="12" y1="11" x2="12" y2="21"/><polyline points="4 7 12 11 20 7"/>', active: false, bg: '#C9956C', bd: '#A87C48' },
  { label: '活动报名', route: 'activities', icon: '<circle cx="12" cy="12" r="10"/><polygon points="10 8 16 12 10 16 10 8"/>', active: false, bg: '#6B6E64', bd: '#4E5049' },
  { label: '停车缴费', route: 'parking', icon: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M17 21v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2"/>', active: false, bg: '#D4A59A', bd: '#A67D72' },
]

const shops = computed(() => allShops.slice(0, 6))

// 品牌色亮暗判定：亮底用深字、暗底用白字，避免低对比
function logoTextColor(hex) {
  const c = (hex || '#888').replace('#', '')
  const r = parseInt(c.substr(0, 2), 16) || 0
  const g = parseInt(c.substr(2, 2), 16) || 0
  const b = parseInt(c.substr(4, 2), 16) || 0
  const lum = 0.299 * r + 0.587 * g + 0.114 * b
  return lum > 150 ? '#1A1A1A' : '#FFFFFF'
}

function go(route) {
  if (typeof route === 'string') {
    if (route === 'nav') router.push('/nav')
    else if (route === 'offers') router.push('/offers')
    else if (route === 'activities') router.push('/activities')
    else if (route === 'parking') router.push('/parking')
    else if (route.startsWith('/')) router.push(route)
  }
}
</script>


<style scoped>
@font-face { font-family: 'Gayathri'; src: url('@/assets/fonts/Gayathri-Bold.ttf') format('truetype'); font-weight: 700; font-style: normal; font-display: swap; }
.home-tab { padding-bottom: 80px; }
.hero-banner { width: 100%; aspect-ratio: 1/1; position: relative; overflow: hidden; }
.hero-bg { width: calc(100% + 200px); height: 100%; margin-left: -100px; object-fit: cover; display: block; transform: translateX(40px); }
.hero-gradient { position: absolute; inset: 0; background: linear-gradient(180deg, rgba(0,0,0,0.15) 0%, rgba(0,0,0,0.5) 70%, rgba(0,0,0,0.8) 100%); }
.hero-slogan { position: absolute; top: 14px; left: 8px; z-index: 2; }
.slogan-pill {
  display: inline-flex; align-items: center; gap: 0.5px;
  border: 1px solid rgba(255,255,255,0.85);
  border-radius: 999px;
  padding: 0.5px 9px;
}
.slogan-logo { height: 26px; width: auto; display: block; flex-shrink: 0; transform: translateY(1.5px); filter: drop-shadow(0 1px 2px rgba(0,0,0,0.45)); }
.slogan-text {
  font-family: 'PingFang SC', var(--font-primary);
  font-size: calc(var(--fs-deco) + 2px);
  font-weight: 600;
  color: #FFFFFF;
  letter-spacing: 0.5px;
  line-height: 1.4;
  text-shadow: 0 1px 2px rgba(0,0,0,0.4);
}

.member-card { margin: -60px 12px 0; border-radius: 18px; padding: 22px 18px 20px; position: relative; z-index: 3; box-shadow: 0 6px 20px rgba(0,0,0,0.35); }
/* 未登录：黑色玻璃登录卡（与整站黑底/玻璃语言统一） */
.member-card:not(.mc-light) {
  background: #161618;
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 24px;
  padding: 22px 20px 20px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.06);
}
.mc-top { display: flex; align-items: center; gap: 14px; margin-bottom: 18px; }
.mc-logo-circle { width: 44px; height: 44px; border-radius: 50%; background: rgba(255,255,255,0.06); display: flex; align-items: center; justify-content: center; flex-shrink: 0; box-shadow: inset 0 1px 1px rgba(255,255,255,0.08), inset 0 -1px 2px rgba(0,0,0,0.5); }
.mc-logo-circle svg { stroke: #fff !important; }
.mc-title { font-size: var(--fs-headline); font-weight: 800; color: #fff; display: flex; align-items: center; gap: 6px; letter-spacing: 0.5px; }
.mc-subtitle { font-size: var(--fs-aux); color: rgba(255,255,255,0.55); margin-top: 2px; }
.mc-phone-row { margin-bottom: 12px; }
.mc-phone-input { display: flex; align-items: center; background: #0E0E10; border: 1px solid rgba(255,255,255,0.10); border-radius: 10px; padding: 0 14px; height: 46px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.5); }
.mc-prefix { font-size: var(--fs-aux); font-weight: 600; color: rgba(255,255,255,0.5); margin-right: 10px; border-right: 1px solid rgba(255,255,255,0.12); padding-right: 10px; }
.mc-input { flex: 1; background: transparent; border: none; outline: none; font-size: 14px; color: #fff; font-family: inherit; }
.mc-input::placeholder { color: rgba(255,255,255,0.35); }
.mc-btn { width: 100%; height: 46px; border: 1px solid #A87C48; border-radius: 12px; background: #C9956C; color: #fff; font-size: 14px; font-weight: 700; cursor: pointer; letter-spacing: 0.5px; box-shadow: inset 0 1px 0 rgba(255,255,255,0.22), 0 4px 12px rgba(168,124,72,0.30); }
.mc-btn:active { opacity: 0.9; transform: translateY(1px); }
.mc-btn:disabled { opacity: 0.5; }
.mc-btn-wx { background: #6B6E64 !important; border: 1px solid #4E5049 !important; color: #fff !important; margin-top: 10px; display: flex; align-items: center; justify-content: center; gap: 8px; font-weight: 700; font-size: 14px !important; border-radius: 12px !important; height: 46px !important; box-shadow: inset 0 1px 0 rgba(255,255,255,0.18), 0 4px 12px rgba(78,80,73,0.30) !important; }
.mc-btn-outline { background: transparent !important; border: 1.5px solid rgba(255,255,255,0.8) !important; color: #fff !important; }
.mc-agree { display: flex; align-items: flex-start; gap: 8px; margin-top: 14px; cursor: pointer; }
.mc-agree-box { width: 16px; height: 16px; border-radius: 50%; border: 1.5px solid rgba(255,255,255,0.4); flex-shrink: 0; display: flex; align-items: center; justify-content: center; margin-top: 2px; transition: all 0.2s; background: rgba(255,255,255,0.05); }
.mc-agree-box.checked { border-color: #C9956C; background: rgba(201,149,108,0.18); }
.mc-agree-text { font-size: var(--fs-aux); color: rgba(255,255,255,0.55); line-height: 1.6; }
.mc-link { color: #C9956C; text-decoration: underline; font-weight: 600; }

/* 登录态：橙色渐变 + 清透感（浅亮、通透、有呼吸感） */
/* iOS 玻璃边框：双层背景，border-box 渐变边(顶部亮→侧透→底微光)，大圆角 */
.mc-light {
  background-color: transparent !important;
  background-image:
    linear-gradient(150deg, rgba(255, 255, 255, 0.03) 0%, rgba(255, 255, 255, 0) 100%),
    linear-gradient(160deg, rgba(106, 91, 140, 1) 0%, rgba(106, 91, 140, 1) 100%);
  background-origin: padding-box, border-box;
  background-clip: padding-box, border-box;
  border: 3px solid transparent;
  border-radius: 24px;
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  box-shadow:
    0 0 16px rgba(106, 91, 140, 0.35),
    0 8px 30px rgba(0, 0, 0, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.28);
}
.member-logged { padding: 0; position: relative; }

.mcard { position: relative; z-index: 1; padding: 22px 20px 20px; overflow: visible; }

/* 上半区：左名 + 右上大圆按钮 & 胶囊 */
.mc-upper { display: flex; align-items: flex-start; justify-content: space-between; }
.mc-left { flex: 1; min-width: 0; padding-top: 2px; }
.mc-name { font-size: var(--fs-headline); font-weight: 800; color: #FFFFFF; letter-spacing: 0.3px; text-shadow: 0 -1px 2px rgba(0, 0, 0, 0.85), 0 1px 1px rgba(255, 255, 255, 0.5); }
.mc-upgrade { font-size: 12px; color: #FFFFFF; margin-top: 12px; text-shadow: 0 -1px 1px rgba(0,0,0,0.45), 0 1px 1px rgba(255,255,255,0.28); }
.mc-upgrade b { color: #FFFFFF; font-weight: 800; font-size: var(--fs-body); text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.3); }

.mc-right { display: flex; flex-direction: column; align-items: flex-end; gap: 10px; }
.mc-big-round { width: 92px; height: 92px; border-radius: 50%; border: 4px solid rgba(255,255,255,0.25); background: linear-gradient(135deg, #4A4A4A, #2E2E2E); color: #fff; display: flex; align-items: center; justify-content: center; cursor: pointer; box-shadow: 0 8px 22px rgba(0,0,0,0.5); margin-top: -90px; position: relative; overflow: hidden; flex-shrink: 0; }
.mc-big-round img { width: 100%; height: 100%; object-fit: cover; }
.mc-big-round:active { opacity: 0.9; }
.mc-big-round svg, .mc-round svg { filter: drop-shadow(0 -1px 1px rgba(0,0,0,0.5)) drop-shadow(0 1px 1px rgba(255,255,255,0.3)); }
.mc-pill { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.16); color: #FFFFFF; font-size: var(--fs-aux); font-weight: 400; padding: 5px 18px; border-radius: 16px; letter-spacing: 1px; box-shadow: inset 0 2px 4px rgba(0,0,0,0.45), inset 0 -1px 3px rgba(255,255,255,0.22); text-shadow: 0 -1px 1px rgba(0,0,0,0.45), 0 1px 1px rgba(255,255,255,0.3); }

/* 弧形进度条 */
.mc-arc { margin: 20px 2px 6px; }
.mc-arc-svg { width: 100%; height: 46px; display: block; overflow: visible; }

/* 底部：两列数据 + 三个圆形按钮 */
.mc-lower { display: flex; align-items: center; justify-content: space-between; margin-top: 22px; }
.mc-cols { display: flex; gap: 44px; }
.mc-col { cursor: pointer; }
.mc-col-num { font-size: var(--fs-headline); font-weight: 800; color: #FFFFFF; line-height: 1.2; text-shadow: 0 -1px 1px rgba(0, 0, 0, 0.5), 0 1px 1px rgba(255, 255, 255, 0.35); }
.mc-col-label { font-size: 12px; color: #FFFFFF; margin-top: 6px; letter-spacing: 0.5px; text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.26); }
.mc-rounds { display: flex; gap: 12px; }
.mc-round { width: 42px; height: 42px; border-radius: 50%; border: 1px solid rgba(255,255,255,0.16); background: rgba(255,255,255,0.05); display: flex; align-items: center; justify-content: center; cursor: pointer; box-shadow: inset 0 2px 5px rgba(0,0,0,0.5), inset 0 -2px 4px rgba(255,255,255,0.22); }
.mc-round:active { background: rgba(255,255,255,0.1); }

.quick-links { display: flex; justify-content: space-around; margin: 22px 12px 22px; }
.qlink { display: flex; flex-direction: column; align-items: center; gap: 6px; cursor: pointer; -webkit-tap-highlight-color: transparent; }
.qlink:active { opacity: 0.7; }
/* 导航图标：圆形内凹（中性灰底 + 白色凸起细线条，严格按参考图） */
.qlink-icon { position: relative; width: 58px; height: 58px; box-sizing: border-box; border-radius: 50%; border: 3px solid transparent; background: #8B8B90; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.20); transition: box-shadow .2s ease, transform .15s ease; }
.qlink-icon:active { transform: scale(0.96); }
.qlink-glyph { width: 30px; height: 30px; color: #FFFFFF; filter: drop-shadow(0 0.6px 1px rgba(0, 0, 0, 0.4)); }
/* 选中态：银框轻微缩放反馈（无灰阴影） */
.qlink-icon.active { opacity: 0.85; }
.qlink-label { font-size: 12px; color: #FFFFFF; }

/* ── 卡片多彩复古配色（无纹理） ── */
.daily-deal, .biz-hero, .biz-card, .shop-card { position: relative; overflow: hidden; }
.dd-illus, .biz-hero-illus, .biz-card-illus, .shop-illus { position: absolute; right: 0; top: 0; width: 64%; height: 100%; pointer-events: none; z-index: 1; opacity: 0.28; stroke: #FFFFFF; stroke-width: 2.6; stroke-linecap: round; stroke-linejoin: round; }
.dd-icon-box, .dd-left, .dd-right, .biz-card-content, .shop-logo, .shop-info, .shop-arrow { position: relative; z-index: 2; }

/* 每日特惠 — 金黄 */
.daily-deal { display: flex; align-items: center; gap: 12px; margin: 0 16px 20px; padding: 14px 16px; background-color: #C4923A; border: 3px solid #9A7425; border-radius: 18px; box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20); cursor: pointer; -webkit-tap-highlight-color: transparent; }
.dd-btn { display: inline-block; padding: 8px 20px; background-color: #9A7425; border: 3px solid #9A7425; border-radius: 20px; box-shadow: inset 3px 3px 7px rgba(0, 0, 0, 0.45), inset -2px -2px 5px rgba(196,146,58,0.45); color: #FFFFFF; font-size: var(--fs-aux); font-weight: 600; white-space: nowrap; filter: drop-shadow(0 0.6px 1px rgba(0, 0, 0, 0.4)); }

/* 社区聚乐部 — 浅粉棕 */
.biz-hero { position: relative; border-radius: 18px; overflow: hidden; height: 170px; cursor: pointer; margin-bottom: 10px; box-sizing: border-box; background-color: #D4A59A; border: 3px solid #A67D72; box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20); }
.biz-hero-btn { position: absolute; right: 22px; bottom: 22px; z-index: 3; display: inline-block; padding: 5px 20px; background-color: #A67D72; border: 3px solid #A67D72; border-radius: 20px; box-shadow: inset 3px 3px 7px rgba(0, 0, 0, 0.45), inset -2px -2px 5px rgba(212,165,154,0.45); color: #FFFFFF; font-size: var(--fs-aux); font-weight: 600; white-space: nowrap; filter: drop-shadow(0 0.6px 1px rgba(0, 0, 0, 0.4)); }

/* 四格业务卡 — 各一色 */
.biz-card { position: relative; border-radius: 16px; overflow: hidden; height: 150px; cursor: pointer; transition: transform 0.15s; box-sizing: border-box; }
.biz-card:nth-child(1) { background-color: #9B4A3E; border: 3px solid #6E332A; box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20); } /* 美食 — 深红棕 */
.biz-card:nth-child(2) { background-color: #C9956C; border: 3px solid #A87C48; box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20); } /* 亲子 — 浅橙棕 */
.biz-card:nth-child(3) { background-color: #8B8B90; border: 3px solid #6A6A6E; box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20); } /* 生活 — 灰紫 */
.biz-card:nth-child(4) { background-color: #6B6E64; border: 3px solid #4E5049; box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20); } /* 停车 — 深灰绿 */

/* 推荐商铺 — 多彩卡片，颜色穿插开 */
.shop-card { flex: 0 0 100%; height: auto; border-radius: 18px; overflow: hidden; scroll-snap-align: start; box-sizing: border-box; padding: 18px; display: flex; flex-direction: row; align-items: center; gap: 14px; background-color: #C4923A; border: 3px solid #9A7425; box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20); cursor: pointer; -webkit-tap-highlight-color: transparent; }
.shop-card:nth-child(1) { background-color: #C4923A; border-color: #9A7425; }
.shop-card:nth-child(2) { background-color: #6B6E64; border-color: #4E5049; }
.shop-card:nth-child(3) { background-color: #C9956C; border-color: #A87C48; }
.shop-card:nth-child(4) { background-color: #8B8B90; border-color: #6A6A6E; }
.shop-card:nth-child(5) { background-color: #9B4A3E; border-color: #6E332A; }
.shop-card:nth-child(6) { background-color: #D4A59A; border-color: #A67D72; }
.daily-deal:active { opacity: 0.82; }
.biz-hero:active { transform: scale(0.985); }
.biz-card:active { transform: scale(0.97); }
.shop-card:active { transform: scale(0.985); }

.dd-icon-box { width: 50px; height: 50px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; position: relative; z-index: 2; }
.dd-icon-box svg { stroke: #FFFFFF; filter: drop-shadow(0 0.4px 0.5px rgba(0,0,0,0.45)); }
.dd-left { flex: 1; min-width: 0; position: relative; z-index: 2; }
.dd-title { font-size: var(--fs-body); font-weight: 700; color: #FFFFFF; margin-bottom: 2px; text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.25); }
.dd-desc { font-size: var(--fs-secondary); color: #FFFFFF; text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.25); }
.dd-right { flex-shrink: 0; position: relative; z-index: 2; }

.qr-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 9999; display: flex; align-items: center; justify-content: center; -webkit-backdrop-filter: blur(4px); backdrop-filter: blur(4px); animation: qrFadeIn 0.2s ease; }
@keyframes qrFadeIn { from { opacity: 0 } to { opacity: 1 } }
.qr-modal { background: #1C1C1E; border-radius: 20px; padding: 0 28px 28px; width: 300px; position: relative; animation: qrScaleIn 0.25s ease; }
@keyframes qrScaleIn { from { transform: scale(0.9); opacity: 0 } to { transform: scale(1); opacity: 1 } }
.qr-close { position: absolute; top: 16px; right: 16px; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; }
.qr-close:active { background: rgba(255,255,255,0.05); }
.qr-title { font-size: 18px; font-weight: 700; color: #F0F0F0; text-align: center; padding: 28px 0 16px; }
.qr-body { text-align: center; }
.qr-code-box { display: flex; align-items: center; justify-content: center; margin-bottom: 16px; }
.qr-user { font-size: var(--fs-body); font-weight: 600; color: #F0F0F0; margin-bottom: 6px; }
.qr-tip { font-size: var(--fs-aux); color: #888; }

.section-label { display: flex; flex-direction: column; margin: 42px 16px 18px; }
.section-en { font-family: 'Gayathri', var(--font-primary); font-size: 22px; font-weight: 900; letter-spacing: 1px; line-height: 1.2; color: rgba(255,255,255,0.92); text-transform: capitalize; -webkit-text-stroke: 0.5px rgba(255,255,255,0.92); }
.section-cn { font-size: 21px; font-weight: 400; color: #FFFFFF; margin-top: 10px; text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.18); }
.shop-list { margin: 0 0; padding: 4px 16px 10px; display: flex; flex-direction: row; gap: 12px; overflow-x: auto; scroll-snap-type: x mandatory; scroll-padding-inline: 16px; -webkit-overflow-scrolling: touch; }
.shop-list::-webkit-scrollbar { display: none; }
.shop-list { scrollbar-width: none; }
.shop-logo { width: 60px; height: 60px; border-radius: 16px; display: flex; align-items: center; justify-content: center; text-align: center; font-size: 15px; font-weight: 800; line-height: 1.12; padding: 4px 5px; letter-spacing: 0.5px; flex-shrink: 0; border: 1px solid rgba(255,255,255,0.20); box-shadow: 0 3px 9px rgba(0,0,0,0.38), inset 0 1px 1px rgba(255,255,255,0.28); text-shadow: 0 1px 1px rgba(0,0,0,0.22); position: relative; z-index: 2; }
.shop-info { flex: 1; min-width: 0; position: relative; z-index: 2; }
.shop-name { font-size: var(--fs-body); font-weight: 600; color: #FFFFFF; text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.25); }
.shop-meta { font-size: 12px; color: #FFFFFF; margin-top: 2px; }
.shop-arrow { flex-shrink: 0; stroke: #FFFFFF; position: relative; z-index: 2; }
.spacer { height: 20px; }

/* ── 业务版块 ── */
.biz-modules { padding: 0 16px; margin-top: 16px; }
.biz-hero-bg { position: absolute; inset: 0; background: rgba(0,0,0,0.03); }
.biz-hero-content { position: relative; z-index: 2; padding: 22px; display: flex; flex-direction: column; height: 100%; max-width: 62%; }
.biz-hero-title { font-size: var(--fs-headline); font-weight: 800; color: #FFFFFF; margin-bottom: 6px; letter-spacing: 0.5px; text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.25); }
.biz-hero-desc { font-size: var(--fs-secondary); color: #FFFFFF; margin-bottom: auto; }
.biz-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.biz-card:active { transform: scale(0.97); }
.biz-card-bg { position: absolute; inset: 0; background: transparent !important; }
.biz-card-content { position: relative; z-index: 2; padding: 14px; display: flex; flex-direction: column; height: 100%; }
.biz-card-icon-sm { width: 48px; height: 48px; display: flex; align-items: center; justify-content: center; margin-bottom: auto; color: #FFFFFF; }
.biz-card-icon-sm svg { filter: drop-shadow(0 0.4px 0.5px rgba(0,0,0,0.45)); }
.biz-hero-icon { width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; margin-bottom: 12px; color: #FFFFFF; }
.biz-hero-icon svg { filter: drop-shadow(0 0.4px 0.5px rgba(0,0,0,0.45)); }
.biz-card-title { font-size: var(--fs-body); font-weight: 700; color: #FFFFFF; margin-top: 8px; text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.25); }
.biz-card-desc { font-size: var(--fs-secondary); color: #FFFFFF; margin-top: 2px; }
</style>
