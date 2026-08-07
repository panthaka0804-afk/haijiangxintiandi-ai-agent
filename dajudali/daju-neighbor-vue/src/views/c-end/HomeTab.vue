<template>
  <div class="home-tab">
    <div class="hero-banner">
      <img :src="p.mallBanner" alt="" class="hero-bg" />
      <div class="hero-gradient"></div>
      <div class="hero-slogan">
        <svg class="slogan-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#999" stroke-width="2" stroke-linecap="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
        <span>五湖四海皆兄弟 吃喝玩乐到海江</span>
      </div>
      <div class="hero-logo">
        <img :src="p.logoHero" alt="海江新天地" class="hero-logo-img" />
      </div>
    </div>

    <div class="member-card">
      <template v-if="!loggedIn">
        <div class="mc-top">
          <div class="mc-logo-circle">
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#FF7B2C" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
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
            <svg v-if="agreed" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#FF7B2C" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
          </span>
          <span class="mc-agree-text">登录即表示同意<span class="mc-link">《用户协议》</span>和<span class="mc-link">《隐私政策》</span></span>
        </div>
      </template>

      <div v-else class="member-logged">
        <div class="mc-arc-header">
          <button class="mc-qr-btn" @click="openQrCode">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FF7B2C" stroke-width="2" stroke-linecap="round"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><path d="M21 14v3a1 1 0 01-1 1h-3M14 21h3a1 1 0 001-1v-3"/></svg>
          </button>
          <div class="mc-arc-info">
            <div class="mc-avatar-sm" @click="triggerUpload">
              <img v-if="avatarUrl" :src="avatarUrl" alt="" />
              <span v-else class="mc-avatar-initial">{{ (displayName || '?')[0] }}</span>
              <input ref="avatarInput" type="file" accept="image/*" style="display:none" @change="onAvatarFile" />
            </div>
            <div class="mc-arc-detail">
              <div class="mc-title">{{ displayName }} <svg class="mc-edit-pen" @click.stop="editName" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#FF7B2C" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></div>
              <div class="mc-subtitle">{{ memberInfo && memberInfo.membership_level || '普卡' }} 会员 · 积分 {{ memberInfo && memberInfo.points || 0 }}</div>
            </div>
          </div>
          <div class="mc-arc-level">{{ memberInfo && memberInfo.membership_level || '普卡' }}</div>
        </div>
        <div class="mc-arc-progress-bar" v-if="upgradeHint">
          <div class="mc-progress-bar"><div class="mc-progress-fill" :style="{ width: upgradePercent + '%' }"></div></div>
          <span class="mc-progress-text">{{ upgradeHint }}</span>
        </div>
        <div class="mc-actions">
          <button class="mc-btn mc-btn-outline" @click="openQrCode">会员码</button>
          <button class="mc-btn mc-btn-outline" @click="emit('switchTab', 'offers')">我的优惠券</button>
          <button class="mc-btn" @click="emit('switchTab', 'profile')">会员中心</button>
        </div>
        <div class="mc-logout" @click="doLogout">退出登录</div>
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
        <div class="qlink-icon" :class="{ active: e.active }">
          <svg v-html="e.icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"></svg>
        </div>
        <span class="qlink-label">{{ e.label }}</span>
      </div>
    </div>

    <div class="daily-deal" @click="$router.push('/offers')">
      <div class="dd-icon-box">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FF7B2C" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
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

    <div class="biz-modules">
      <div class="biz-hero" @click="go('/activities')">
        <div class="biz-hero-bg"></div>
        <div class="biz-hero-content">
          <div class="biz-hero-title">社区聚乐部</div>
          <div class="biz-hero-desc">活动报名 · 邻里社群 · 精彩生活</div>
          <span class="biz-hero-btn">立即查看</span>
        </div>
      </div>
      <div class="biz-grid">
        <div class="biz-card" v-for="m in bizModules" :key="m.label" @click="go(m.route)">
          <div class="biz-card-icon" :style="{background: m.grad}">
            <svg v-html="m.icon" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"></svg>
          </div>
          <div class="biz-card-title">{{ m.label }}</div>
          <div class="biz-card-desc">{{ m.desc }}</div>
        </div>
      </div>
    </div>

    <div class="section-label">推荐商铺</div>
    <div class="shop-list">
      <div v-for="s in shops" :key="s.id" class="shop-card" @click="go('/shop/' + s.id)">
        <div class="shop-avatar" :style="{background: s.color}">{{ s.name[0] }}</div>
        <div class="shop-info">
          <div class="shop-name">{{ s.name }}</div>
          <div class="shop-meta">{{ s.floor }} · {{ s.category }}</div>
        </div>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#555" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
      </div>
    </div>
    <div class="spacer"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { placeholderImages as p } from '@/assets/placeholders'
import allShops from '@/data/shops'
import http from '@/api'

const emit = defineEmits(['switchTab'])
const router = useRouter()
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
  'L1': { name: '银卡', need: 2000 },
  'L2': { name: '金卡', need: 5000 },
  'L3': { name: '铂金卡', need: 10000 },
  'L4': { name: '钻石卡', need: 20000 },
}

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
      if (res.user.phone) {
        try {
          const minfo = await http.post('/api/member/lookup', { phone: res.user.phone })
          if (minfo.ok && minfo.member) { memberInfo.value = minfo.member }
        } catch {}
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
    grad: 'linear-gradient(135deg, #E85D04, #FF7B2C)',
    icon: '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>'
  },
  {
    label: '亲子乐园',
    desc: '3F儿童游乐',
    route: '/shops?floor=3',
    grad: 'linear-gradient(135deg, #7C3AED, #A78BFA)',
    icon: '<circle cx="12" cy="10" r="3"/><path d="M8 17l1.5-4h5L16 17"/><circle cx="12" cy="8" r="4"/><path d="M8 21v-1a6 6 0 0112 0v1"/>'
  },
  {
    label: '生活服务',
    desc: '洗衣美甲维修',
    route: '/shops?floor=2',
    grad: 'linear-gradient(135deg, #059669, #34D399)',
    icon: '<path d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/>'
  },
  {
    label: '停车缴费',
    desc: '在线缴费出场',
    route: '#',
    grad: 'linear-gradient(135deg, #2563EB, #60A5FA)',
    icon: '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M6 7V5a2 2 0 012-2h8a2 2 0 012 2v2"/><circle cx="16" cy="15" r="1.5"/><circle cx="8" cy="15" r="1.5"/>'
  }
]

const entries = [
  { label: '导航地图', route: 'nav', icon: '<path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"/><circle cx="12" cy="9" r="2.5"/>', active: false },
  { label: '优惠促销', route: 'offers', icon: '<path d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/><line x1="12" y1="11" x2="12" y2="21"/><polyline points="4 7 12 11 20 7"/>', active: false },
  { label: '活动报名', route: 'activities', icon: '<circle cx="12" cy="12" r="10"/><polygon points="10 8 16 12 10 16 10 8"/>', active: false },
  { label: '停车缴费', route: 'parking', icon: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M17 21v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2"/>', active: false },
]

const shops = computed(() => allShops.slice(0, 6))

function go(route) {
  if (typeof route === 'string') {
    if (route === 'nav') emit('switchTab', 'nav')
    else if (route === 'offers') emit('switchTab', 'offers')
    else if (route === 'activities') emit('switchTab', 'activities')
    else if (route === 'parking') router.push('/parking')
    else if (route.startsWith('/')) router.push(route)
  }
}
</script>


<style scoped>
.home-tab { padding-bottom: 80px; }
.hero-banner { width: 100%; aspect-ratio: 1/1; position: relative; overflow: hidden; }
.hero-bg { width: 100%; height: 100%; object-fit: cover; display: block; }
.hero-gradient { position: absolute; inset: 0; background: linear-gradient(180deg, rgba(0,0,0,0.15) 0%, rgba(0,0,0,0.5) 70%, rgba(0,0,0,0.8) 100%); }
.hero-slogan { position: absolute; top: 12px; left: 14px; display: flex; align-items: center; gap: 6px; z-index: 2; }
.hero-slogan span { font-size: 11px; color: rgba(255,255,255,0.7); letter-spacing: 0.5px; }
.slogan-icon { flex-shrink: 0; opacity: 0.6; }
.hero-logo { position: absolute; left: 50%; top: 45%; transform: translate(-50%, -50%); width: 55%; max-width: 220px; z-index: 1; }
.hero-logo-img { width: 100%; display: block; filter: drop-shadow(0 2px 8px rgba(0,0,0,0.4)); }

.member-card { margin: -60px 12px 0; background: #1C1C1E; border-radius: 20px; padding: 24px 20px 22px; position: relative; z-index: 3; box-shadow: 0 -4px 20px rgba(0,0,0,0.5); }
.mc-top { display: flex; align-items: center; gap: 14px; margin-bottom: 20px; }
.mc-logo-circle { width: 48px; height: 48px; border-radius: 50%; background: rgba(255,123,44,0.12); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.mc-title { font-size: 18px; font-weight: 700; color: #F0F0F0; display: flex; align-items: center; gap: 6px; }
.mc-subtitle { font-size: 13px; color: #999; margin-top: 2px; }
.mc-phone-row { margin-bottom: 14px; }
.mc-phone-input { display: flex; align-items: center; background: #2A2A2E; border-radius: 12px; padding: 0 14px; height: 48px; }
.mc-prefix { font-size: 15px; font-weight: 600; color: #AAA; margin-right: 10px; border-right: 1px solid #3A3A3E; padding-right: 10px; }
.mc-input { flex: 1; background: transparent; border: none; outline: none; font-size: 16px; color: #F0F0F0; font-family: inherit; }
.mc-input::placeholder { color: #555; }
.mc-btn { width: 100%; height: 48px; border: none; border-radius: 24px; background: linear-gradient(135deg, #FF7B2C, #E85D04); color: #fff; font-size: 16px; font-weight: 600; cursor: pointer; letter-spacing: 1px; }
.mc-btn:active { opacity: 0.85; }
.mc-btn:disabled { opacity: 0.5; }
.mc-btn-wx { background: #07C160 !important; margin-top: 10px; display: flex; align-items: center; justify-content: center; gap: 8px; }
.mc-btn-outline { background: transparent !important; border: 1px solid #FF7B2C !important; color: #FF7B2C !important; }
.mc-agree { display: flex; align-items: flex-start; gap: 8px; margin-top: 14px; cursor: pointer; }
.mc-agree-box { width: 16px; height: 16px; border-radius: 50%; border: 1px solid #555; flex-shrink: 0; display: flex; align-items: center; justify-content: center; margin-top: 2px; transition: all 0.2s; }
.mc-agree-box.checked { border-color: #FF7B2C; background: rgba(255,123,44,0.1); }
.mc-agree-text { font-size: 13px; color: #777; line-height: 1.6; }
.mc-link { color: #FF7B2C; }

.member-logged { padding: 0; }
.mc-arc-header { position: relative; margin: -24px -20px 0; padding: 20px 20px 50px; overflow: visible; min-height: 120px; border-radius: 20px 20px 0 0; }
.mc-arc-bg { position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 0; opacity: 0.3; }
.mc-qr-btn { position: relative; margin-left: auto; z-index: 5; min-width: 32px; height: 32px; border-radius: 8px; background: rgba(255,123,44,0.2); border: 1px solid rgba(255,123,44,0.4); display: flex; align-items: center; justify-content: center; cursor: pointer; }
.mc-qr-btn:active { opacity: 0.7; }
.mc-arc-info { display: flex; align-items: center; gap: 12px; position: relative; z-index: 3; }
.mc-avatar-sm { width: 48px; height: 48px; border-radius: 50%; background: #2A2A2E; display: flex; align-items: center; justify-content: center; overflow: hidden; flex-shrink: 0; cursor: pointer; border: 2px solid rgba(255,123,44,0.3); }
.mc-avatar-sm img { width: 100%; height: 100%; object-fit: cover; }
.mc-avatar-initial { font-size: 20px; font-weight: 700; color: #FF7B2C; }
.mc-logout { text-align: center; padding: 12px; margin-top: 12px; font-size: 13px; color: #666; cursor: pointer; border-top: 1px solid rgba(255,255,255,0.06); }
.mc-logout:active { color: #FF7B2C; }
.mc-edit-pen { flex-shrink: 0; cursor: pointer; opacity: 0.5; transition: opacity 0.2s; }
.mc-edit-pen:active { opacity: 1; }
.mc-arc-detail { flex: 1; }
.mc-arc-level { position: absolute; bottom: 12px; right: 20px; background: linear-gradient(135deg, #FF7B2C, #E85D04); color: #fff; font-size: 11px; font-weight: 700; padding: 3px 14px; border-radius: 10px; z-index: 4; letter-spacing: 1px; }
.mc-arc-progress-bar { margin-top: -24px; margin-bottom: 14px; position: relative; z-index: 1; }
.mc-progress-bar { height: 6px; background: #2A2A2E; border-radius: 3px; overflow: hidden; margin-bottom: 6px; }
.mc-progress-fill { height: 100%; background: linear-gradient(90deg, #FF7B2C, #FF9500); border-radius: 3px; transition: width 0.4s ease; }
.mc-progress-text { font-size: 12px; color: #888; }
.mc-actions { display: flex; gap: 10px; margin-top: 4px; }

.quick-links { display: flex; justify-content: space-around; margin: 20px 16px 20px; }
.qlink { display: flex; flex-direction: column; align-items: center; gap: 6px; cursor: pointer; -webkit-tap-highlight-color: transparent; }
.qlink:active { opacity: 0.7; }
.qlink-icon { width: 48px; height: 48px; border-radius: 14px; background: #2A2A2E; display: flex; align-items: center; justify-content: center; color: #999; transition: all 0.2s; }
.qlink-icon.active { color: #FF7B2C; background: rgba(255,123,44,0.12); }
.qlink-label { font-size: 12px; color: #AAA; }

.daily-deal { display: flex; align-items: center; gap: 12px; margin: 0 16px 20px; padding: 14px 16px; background: linear-gradient(135deg, #2A1A0A, #1E1A1A); border: 0.5px solid rgba(255,123,44,0.2); border-radius: 14px; cursor: pointer; -webkit-tap-highlight-color: transparent; }
.daily-deal:active { opacity: 0.85; }
.dd-icon-box { width: 44px; height: 44px; border-radius: 12px; background: rgba(255,123,44,0.12); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.dd-left { flex: 1; min-width: 0; }
.dd-title { font-size: 15px; font-weight: 700; color: #FF7B2C; margin-bottom: 2px; }
.dd-desc { font-size: 12px; color: #888; }
.dd-right { flex-shrink: 0; }
.dd-btn { display: inline-block; padding: 8px 18px; background: linear-gradient(135deg, #FF7B2C, #E85D04); color: #fff; font-size: 14px; font-weight: 600; border-radius: 20px; white-space: nowrap; }

.qr-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 9999; display: flex; align-items: center; justify-content: center; -webkit-backdrop-filter: blur(4px); backdrop-filter: blur(4px); animation: qrFadeIn 0.2s ease; }
@keyframes qrFadeIn { from { opacity: 0 } to { opacity: 1 } }
.qr-modal { background: #1C1C1E; border-radius: 20px; padding: 0 28px 28px; width: 300px; position: relative; animation: qrScaleIn 0.25s ease; }
@keyframes qrScaleIn { from { transform: scale(0.9); opacity: 0 } to { transform: scale(1); opacity: 1 } }
.qr-close { position: absolute; top: 16px; right: 16px; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; }
.qr-close:active { background: rgba(255,255,255,0.05); }
.qr-title { font-size: 18px; font-weight: 700; color: #F0F0F0; text-align: center; padding: 28px 0 16px; }
.qr-body { text-align: center; }
.qr-code-box { display: flex; align-items: center; justify-content: center; margin-bottom: 16px; }
.qr-user { font-size: 16px; font-weight: 600; color: #F0F0F0; margin-bottom: 6px; }
.qr-tip { font-size: 13px; color: #888; }

.section-label { font-size: 16px; font-weight: 700; color: #F0F0F0; margin: 0 16px 12px; }
.shop-list { margin: 0 16px; display: flex; flex-direction: column; gap: 8px; }
.shop-card { display: flex; align-items: center; gap: 12px; padding: 14px; background: #2A2A2E; border-radius: 14px; cursor: pointer; -webkit-tap-highlight-color: transparent; }
.shop-card:active { opacity: 0.8; }
.shop-avatar { width: 44px; height: 44px; border-radius: 12px; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 18px; font-weight: 700; flex-shrink: 0; }
.shop-info { flex: 1; }
.shop-name { font-size: 15px; font-weight: 600; color: #F0F0F0; }
.shop-meta { font-size: 12px; color: #888; margin-top: 2px; }
.spacer { height: 20px; }

/* ── 业务版块 ── */
.biz-modules { padding: 0 16px; margin-top: 16px; }
.biz-hero { position: relative; border-radius: 16px; overflow: hidden; height: 180px; cursor: pointer; margin-bottom: 10px; }
.biz-hero:active { opacity: 0.9; }
.biz-hero-bg { position: absolute; inset: 0; background: linear-gradient(135deg, #FF7B2C 0%, #E85D04 40%, #FFB347 100%); }
.biz-hero-bg::after { content: ''; position: absolute; top: -40px; right: -30px; width: 160px; height: 160px; border-radius: 50%; background: rgba(255,255,255,0.08); }
.biz-hero-bg::before { content: ''; position: absolute; bottom: -50px; left: -20px; width: 120px; height: 120px; border-radius: 50%; background: rgba(255,255,255,0.05); }
.biz-hero-content { position: relative; z-index: 1; padding: 24px; display: flex; flex-direction: column; height: 100%; }
.biz-hero-title { font-size: 24px; font-weight: 800; color: #fff; margin-bottom: 6px; letter-spacing: 1px; }
.biz-hero-desc { font-size: 13px; color: rgba(255,255,255,0.85); margin-bottom: auto; }
.biz-hero-btn { display: inline-block; margin-top: 12px; padding: 6px 20px; background: rgba(255,255,255,0.25); border: 1px solid rgba(255,255,255,0.4); border-radius: 20px; font-size: 13px; font-weight: 600; color: #fff; align-self: flex-start; }
.biz-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.biz-card { background: #252525; border-radius: 14px; padding: 18px 16px; cursor: pointer; transition: transform 0.15s; }
.biz-card:active { transform: scale(0.97); }
.biz-card-icon { width: 44px; height: 44px; border-radius: 12px; display: flex; align-items: center; justify-content: center; margin-bottom: 12px; }
.biz-card-title { font-size: 16px; font-weight: 700; color: #F0F0F0; margin-bottom: 4px; }
.biz-card-desc { font-size: 12px; color: #888; }
</style>
