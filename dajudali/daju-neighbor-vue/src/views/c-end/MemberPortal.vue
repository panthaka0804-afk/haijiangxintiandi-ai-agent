<template>
  <div class="member-page">
    <van-nav-bar title="会员中心" left-text="返回" left-arrow @click-left="$router.back()" fixed placeholder>
      <template #right>
        <van-button size="small" round plain @click="userStore.largeFont = !userStore.largeFont" :style="{ color: userStore.largeFont ? '#FFB877' : '#777', borderColor: userStore.largeFont ? '#FFB877' : '#444', fontWeight: '700' }">关怀模式</van-button>
      </template>
    </van-nav-bar>

    <!-- 未登录（无会员信息）：输入手机号查询 / 登录 -->
    <template v-if="!memberStore.member">
      <van-form @submit="queryMember" style="margin-top: 20px;">
        <van-cell-group inset>
          <van-field
            v-model="phone"
            name="phone"
            label="手机号"
            type="tel"
            maxlength="11"
            placeholder="请输入注册手机号"
            :rules="[
              { required: true, message: '请输入手机号' },
              { pattern: /^1\d{10}$/, message: '手机号格式不正确' }
            ]"
          />
        </van-cell-group>
        <div style="margin: 16px">
          <van-button round block type="primary" native-type="submit" :loading="loading">
            查询会员信息
          </van-button>
        </div>
        <div class="member-hint">登录后，首页会员卡、会员中心与各页面的积分与会员信息将自动同步。</div>
      </van-form>
    </template>

    <!-- 会员信息展示（与首页会员卡、更多页共享同一份登录态） -->
    <template v-else>
      <div class="member-card">
        <div class="card-header">
          <div class="m-avatar">
            <img v-if="member.avatar" :src="member.avatar" class="m-avatar-img" alt="" />
            <svg v-else width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
          </div>
          <div class="m-head-text">
            <span class="level-badge" :style="{ background: member.theme.bg, borderColor: member.theme.bd }">{{ member.level }}</span>
            <span class="card-name">{{ member.name }}</span>
          </div>
        </div>
        <div class="card-body">
          <div class="info-row">
            <span class="label">手机号</span>
            <span>{{ member.phone || '未绑定' }}</span>
          </div>
          <div class="info-row">
            <span class="label">当前积分</span>
            <span class="value highlight">{{ member.points }}</span>
          </div>
          <div class="info-row">
            <span class="label">会员折扣</span>
            <span class="value highlight">{{ member.discount }}</span>
          </div>
          <div class="info-row">
            <span class="label">距升级还需</span>
            <span>{{ member.needUpgrade }}分</span>
          </div>
        </div>
      </div>

      <!-- 激励中心入口 -->
      <div class="mp-card mp-gift-send" @click="$router.push('/points')">
        <div class="mp-icon-box">
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M20 12v10H4V12"/><path d="M2 7h20v5H2z"/><path d="M12 22V7"/><path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z"/><path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z"/></svg>
        </div>
        <div class="mp-left">
          <div class="mp-title">激励中心</div>
          <div class="mp-desc">每日签到 · 成长值 · 成就徽章</div>
        </div>
        <span class="mp-arrow">›</span>
      </div>

      <!-- 邻里特权：会员互赠 + 人脉引荐 -->
      <div class="mp-section">
        <span class="mp-section-en">neighbor privilege</span>
        <span class="mp-section-cn">邻里特权</span>
      </div>

      <!-- 人脉引荐 hero -->
      <div class="mp-card mp-refer">
        <div class="mp-refer-head">
          <div class="mp-icon-box">
            <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          </div>
          <div class="mp-refer-title">邻里引荐</div>
        </div>
        <div class="mp-refer-code">{{ gift.referral_code || '—' }}</div>
        <div class="mp-refer-tip">把码发给邻居，TA 注册时填写，双方各得 {{ referBase }} 分</div>
        <div class="mp-refer-foot">
          <button class="mp-pill" @click="copyCode">复制引荐码</button>
          <button class="mp-pill" @click="openQr">看二维码</button>
          <img v-if="refQr" :src="refQr" class="mp-refer-qr" alt="引荐二维码" />
        </div>
      </div>

      <!-- 会员互赠：高阶赠折扣权 / 低阶升级 -->
      <div class="mp-card" :class="gift.is_high_tier ? 'mp-gift-send' : 'mp-gift-up'">
        <div class="mp-icon-box">
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>
        </div>
        <div class="mp-left">
          <div class="mp-title">{{ gift.is_high_tier ? '赠折扣权给朋友' : '升级可赠折扣权' }}</div>
          <div class="mp-desc">{{ gift.is_high_tier ? `本月还可赠 ${gift.gift_quota} 次 · 朋友核销后首单享你的卡级` : '金卡/钻石卡每月可赠朋友一次折扣权' }}</div>
        </div>
        <button class="mp-pill" v-if="gift.is_high_tier" @click="showSend = true">去赠送</button>
        <button class="mp-pill" v-else @click="showUpgradeTip">去升级</button>
      </div>

      <!-- 我收到的折扣权 -->
      <div class="mp-card mp-gift-recv" v-if="gift.received_cards && gift.received_cards.length"
        @click="showRedeem = true">
        <div class="mp-icon-box">
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M3 8a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v2a2 2 0 0 0 0 4v2a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-2a2 2 0 0 0 0-4z"/></svg>
        </div>
        <div class="mp-left">
          <div class="mp-title">我收到的折扣权</div>
          <div class="mp-desc">{{ gift.received_cards.length }} 张待核销</div>
        </div>
        <span class="mp-arrow">›</span>
      </div>

      <!-- 我赠出的折扣权 -->
      <div class="mp-card mp-gift-sent" v-if="gift.sent_cards && gift.sent_cards.length"
        @click="showSent = true">
        <div class="mp-icon-box">
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4 20-7z"/></svg>
        </div>
        <div class="mp-left">
          <div class="mp-title">我赠出的折扣权 ({{ gift.sent_cards.length }})</div>
          <div class="mp-desc">点击查看核销状态</div>
        </div>
        <span class="mp-arrow">›</span>
      </div>

      <!-- 积分兑换 -->
      <div class="mp-section">
        <span class="mp-section-en">redeem</span>
        <span class="mp-section-cn">积分兑换</span>
      </div>
      <div class="mp-grid">
        <div v-for="(item, i) in redeemList" :key="item.id" class="mp-card mp-redeem" :class="'mp-redeem-' + (i % 5)"
          @click="showRedeemConfirm(item)">
          <div class="mp-value">{{ item.value }}</div>
          <div class="mp-title">{{ item.name }}</div>
          <div class="mp-desc">{{ item.points }} 积分</div>
        </div>
      </div>

      <!-- 我的券 -->
      <div class="mp-section" v-if="coupons && coupons.length">
        <span class="mp-section-en">my coupons</span>
        <span class="mp-section-cn">我的券</span>
      </div>
      <div class="mp-grid" v-if="coupons && coupons.length">
        <div v-for="(c, i) in coupons" :key="(c.code || 'c') + '-' + i" class="mp-card mp-coupon" :class="'mp-coupon-' + (i % 5)">
          <div class="mp-title">{{ c.item || '优惠券' }}</div>
          <div class="mp-desc">有效期至 {{ c.time || '—' }}</div>
          <div class="mp-coupon-code">{{ c.code || '—' }}</div>
        </div>
      </div>

      <!-- 赠折扣权弹窗 -->
      <van-dialog v-model:show="showSend" title="赠折扣权给朋友" show-cancel-button @confirm="doSend">
        <div style="padding: 16px;">
          <van-field v-model="sendForm.friend_phone" label="朋友手机" type="tel" maxlength="11" placeholder="请输入朋友手机号" />
          <van-field v-model="sendForm.friend_name" label="朋友称呼" placeholder="如：王姐 / 邻居" />
          <p style="font-size:12px;color:#999;margin:8px 0 0;">朋友核销后首次消费享你的「{{ gift.level }}」折扣，首单后恢复本人卡级。</p>
        </div>
      </van-dialog>

      <!-- 核销折扣权弹窗 -->
      <van-dialog v-model:show="showRedeem" title="核销折扣权" show-cancel-button @confirm="doRedeem">
        <div style="padding: 16px;">
          <van-field v-model="redeemForm.code" label="券码" placeholder="输入朋友赠你的券码" />
          <p style="font-size:12px;color:#999;margin:8px 0 0;">核销后临时升级为赠卡人卡级，首单消费享对应折扣。</p>
        </div>
      </van-dialog>

      <!-- 我赠出的券 -->
      <van-dialog v-model:show="showSent" title="我赠出的折扣权">
        <div style="padding: 12px 16px;max-height:50vh;overflow:auto;">
          <div v-for="c in (gift.sent_cards || [])" :key="c.code" style="padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.08);font-size:13px;">
            <div>券码 <b>{{ c.code }}</b> · {{ c.from_level }}</div>
            <div style="color:#999;">{{ c.status === 'used' ? '已核销' : (c.status === 'expired' ? '已过期' : '待核销') }} · 有效期至 {{ c.expire_at }}</div>
          </div>
        </div>
      </van-dialog>

      <!-- 引荐二维码 -->
      <van-dialog v-model:show="showQr" title="我的引荐二维码">
        <div style="padding: 16px;text-align:center;">
          <img v-if="refQr" :src="refQr" style="width:200px;height:200px;border-radius:8px;" alt="二维码" />
          <p style="font-size:13px;color:#FFB877;margin-top:8px;text-shadow:0 -1px 1px rgba(0,0,0,0.4),0 1px 1px rgba(255,255,255,0.25);">引荐码：{{ gift.referral_code }}</p>
          <p style="font-size:12px;color:#999;">朋友扫码后手动填写引荐码即可建立邻里关系</p>
        </div>
      </van-dialog>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { useMemberStore } from '@/stores/member'
import { showToast, showConfirmDialog, showDialog } from 'vant'
import { getMemberCoupons, getGiftQuota, sendGift, redeemGift, bindReferrer } from '@/api'

const userStore = useUserStore()
const memberStore = useMemberStore()

const phone = ref('')
const loading = ref(false)
const coupons = ref([])

// 邻里特权状态
const gift = ref({ is_high_tier: false, gift_quota: 0, referral_code: '', sent_cards: [], received_cards: [] })
const referBase = 50
const refQr = ref('')
const showQr = ref(false)
const showSend = ref(false)
const showRedeem = ref(false)
const showSent = ref(false)
const sendForm = ref({ friend_phone: '', friend_name: '' })
const redeemForm = ref({ code: '' })

// 与首页会员卡、更多页共用同一份 memberStore（登录后自动同步）
const member = computed(() => {
  const m = memberStore.member
  if (!m) return null
  const level = m.membership_level || '普卡'
  return {
    name: m.display_name || '海江会员',
    phone: m.phone || '',
    points: m.points || 0,
    level,
    theme: memberStore.levelTheme(level),
    discount: m.discount || '98折',
    avatar: m.headimgurl || '',
    needUpgrade: '-',
  }
})

// 进入页面时先从 sessionStorage 恢复（保持各页面同步）
memberStore.restore()
if (memberStore.member && memberStore.member.phone) {
  loadCoupons(memberStore.member.phone)
  loadGift(memberStore.member.phone)
}

async function loadGift(p) {
  if (!p) return
  try {
    const res = await getGiftQuota(p)
    if (res.ok) gift.value = res.data || gift.value
  } catch {}
}

async function copyCode() {
  const code = gift.value.referral_code
  if (!code) return
  try {
    await navigator.clipboard.writeText(code)
    showToast('引荐码已复制：' + code)
  } catch {
    showToast('引荐码：' + code)
  }
}

async function openQr() {
  if (!gift.value.referral_code) return
  try {
    const r = await fetch('/api/referral/qrcode?code=' + encodeURIComponent(gift.value.referral_code))
    const d = await r.json()
    if (d.ok) { refQr.value = d.qr; showQr.value = true }
  } catch { showToast('二维码生成失败') }
}

async function doSend() {
  const fp = sendForm.value.friend_phone.trim()
  if (!/^1\d{10}$/.test(fp)) { showToast('请输入朋友正确的手机号'); return }
  if (gift.value.gift_quota <= 0) { showToast('本月赠出次数已用完'); return }
  try {
    const res = await sendGift(phone.value, fp, sendForm.value.friend_name.trim() || '邻居')
    if (res.ok) {
      showToast(`已赠出${res.data.from_level}折扣权，券码 ${res.data.code}`)
      showSend.value = false
      sendForm.value = { friend_phone: '', friend_name: '' }
      loadGift(phone.value)
    } else showToast(res.error || '赠送失败')
  } catch { showToast('网络错误') }
}

async function doRedeem() {
  const code = redeemForm.value.code.trim().toUpperCase()
  if (!code) { showToast('请输入折扣权券码'); return }
  try {
    const res = await redeemGift(phone.value, code)
    if (res.ok) {
      showDialog({ title: '已升级', message: `临时升级为${res.data.temp_level}，有效期内首单享${res.data.discount}折，首单后恢复本人卡级` })
      showRedeem.value = false
      redeemForm.value.code = ''
      loadGift(phone.value)
    } else showToast(res.error || '核销失败')
  } catch { showToast('网络错误') }
}

function showUpgradeTip() {
  showDialog({ title: '成为高阶会员', message: '金卡 / 钻石卡会员每月可赠朋友一次折扣权，朋友核销后首单即享你的卡级折扣。多消费攒积分即可升级～' })
}

const redeemList = [
  { id: 'g4', name: '停车券', points: 500, value: '¥10' },
  { id: 'g7', name: '瑞幸咖啡券', points: 1000, value: '¥35' },
  { id: 'g1', name: 'SFC电影票', points: 2000, value: '¥45' },
  { id: 'g6', name: '泡泡米体验课', points: 2000, value: '¥49' },
  { id: 'g3', name: '华为30元券', points: 2500, value: '¥30' },
  { id: 'g5', name: '康友四季足浴', points: 2500, value: '¥30' },
  { id: 'g2', name: '朱光玉火锅券', points: 3000, value: '¥50' },
  { id: 'g8', name: '哇咔健身周卡', points: 4000, value: '¥39' },
  { id: 9, name: '火锅双人餐', points: 15000, value: '¥368' },
]

async function queryMember() {
  loading.value = true
  try {
    // loginByPhone 内部走 /api/member/lookup 并写入 memberStore（各页面共享）
    const res = await memberStore.loginByPhone(phone.value)
    if (res.ok) {
      if (memberStore.member && memberStore.member.phone) {
        await loadCoupons(memberStore.member.phone)
        await loadGift(memberStore.member.phone)
      }
    } else {
      showToast(res.error || '查询失败')
    }
  } catch {
    showToast('网络错误')
  } finally {
    loading.value = false
  }
}

async function loadCoupons(p) {
  try {
    const res = await getMemberCoupons(p)
    if (res.ok) coupons.value = res.coupons || []
  } catch {}
}

async function showRedeemConfirm(item) {
  try {
    await showConfirmDialog({
      title: '确认兑换',
      message: `确定用 ${item.points} 积分兑换"${item.name}"？\n兑换后剩余 ${member.value.points - item.points} 分`,
      confirmButtonText: '确认兑换',
      cancelButtonText: '取消'
    })
    showToast('请通过小程序积分商城完成兑换')
  } catch {
    // 取消
  }
}
</script>

<style scoped>
.member-page {
  min-height: 100vh;
  background: #000;
}
.member-hint {
  margin: 4px 24px;
  font-size: 12px;
  color: #888;
  line-height: 1.6;
}

.member-card {
  margin: 16px;
  background: linear-gradient(135deg, #1A1A1A, #2A2A2A);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.5);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 16px;
}

.m-avatar {
  width: 54px;
  height: 54px;
  border-radius: 50%;
  background: rgba(255,255,255,0.06);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  flex-shrink: 0;
  border: 1px solid rgba(255,255,255,0.16);
}
.m-avatar-img { width: 100%; height: 100%; object-fit: cover; }

.m-head-text {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.level-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  color: #fff;
  border: 1px solid rgba(0,0,0,0.2);
  flex-shrink: 0;
}

.card-name {
  font-size: 18px;
  font-weight: 600;
  color: #F0F0F0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: #AAA;
}

.info-row .label {
  color: #777;
}

.info-row .value {
  font-weight: 600;
  color: #F0F0F0;
}

.info-row .value.highlight {
  color: #FFB877;
  font-size: 18px;
}

:deep(.van-nav-bar) {
  background: linear-gradient(135deg, #1A1A1A, #1A1A1A);
}

:deep(.van-nav-bar__title),
:deep(.van-nav-bar__text),
:deep(.van-nav-bar .van-icon) {
  color: #fff;
}

/* ============ 多彩卡片（对齐首页风格） ============ */
/* 统一：实色底 + 同色系深边框(3px) + 内高光 + 白字 text-shadow */
.mp-section {
  display: flex;
  flex-direction: column;
  margin: 26px 16px 12px;
}
.mp-section-en {
  font-family: 'Gayathri', var(--font-primary);
  font-size: 20px;
  font-weight: 900;
  letter-spacing: 1px;
  line-height: 1.2;
  color: rgba(255,255,255,0.92);
  text-transform: capitalize;
  -webkit-text-stroke: 0.5px rgba(255,255,255,0.92);
}
.mp-section-cn {
  font-size: 20px;
  font-weight: 400;
  color: #FFFFFF;
  margin-top: 8px;
  text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.18);
}

.mp-card {
  position: relative;
  box-sizing: border-box;
  border-radius: 18px;
  overflow: hidden;
  margin: 0 16px 12px;
  padding: 16px 18px;
  display: flex;
  align-items: center;
  gap: 14px;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  border: 3px solid #9A7425;
  background-color: #C4923A;
  box-shadow: 0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.20);
}
.mp-card:active { transform: scale(0.985); }

/* 配色循环（与首页一致：金黄/浅橙棕/深红棕/灰紫/深灰绿） */
.mp-gift-send  { background-color: #C9956C; border-color: #A87C48; } /* 浅橙棕 */
.mp-gift-up    { background-color: #8B8B90; border-color: #6A6A6E; } /* 灰紫 */
.mp-gift-recv  { background-color: #6B6E64; border-color: #4E5049; } /* 深灰绿 */
.mp-gift-sent  { background-color: #9B4A3E; border-color: #6E332A; } /* 深红棕 */
.mp-refer      { background-color: #D4A59A; border-color: #A67D72; } /* 浅粉棕 */

.mp-icon-box {
  width: 50px;
  height: 50px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: rgba(255,255,255,0.16);
  box-shadow: inset 1px 1px 2px rgba(255,255,255,0.30), inset -1px -1px 3px rgba(0,0,0,0.20);
}
.mp-icon-box svg { stroke: #FFFFFF; filter: drop-shadow(0 0.4px 0.5px rgba(0,0,0,0.45)); }

.mp-left { flex: 1; min-width: 0; }
.mp-title {
  font-size: 16px;
  font-weight: 700;
  color: #FFFFFF;
  margin-bottom: 2px;
  text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.25);
}
.mp-desc {
  font-size: 12px;
  color: #FFFFFF;
  text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.25);
}
.mp-arrow {
  flex-shrink: 0;
  font-size: 26px;
  color: #FFFFFF;
  line-height: 1;
  text-shadow: 0 -1px 1px rgba(0,0,0,0.4);
}

.mp-pill {
  flex-shrink: 0;
  padding: 8px 18px;
  border: 3px solid rgba(255,255,255,0.0);
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  color: #FFFFFF;
  cursor: pointer;
  background-color: rgba(0,0,0,0.22);
  box-shadow: inset 2px 2px 5px rgba(0,0,0,0.35), inset -2px -2px 4px rgba(255,255,255,0.18);
}
.mp-pill:active { opacity: 0.86; }

/* 邻里引荐 hero（竖向大卡） */
.mp-refer { flex-direction: column; align-items: stretch; gap: 10px; }
.mp-refer-head { display: flex; align-items: center; gap: 12px; }
.mp-refer-title {
  font-size: 18px;
  font-weight: 800;
  color: #FFFFFF;
  letter-spacing: 0.5px;
  text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.25);
}
.mp-refer-code {
  font-size: 26px;
  font-weight: 800;
  color: #FFFFFF;
  letter-spacing: 3px;
  font-family: 'SF Mono', 'Roboto Mono', monospace;
  text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.25);
}
.mp-refer-tip {
  font-size: 12px;
  color: #FFFFFF;
  line-height: 1.5;
  text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.2);
}
.mp-refer-foot { display: flex; align-items: center; gap: 10px; }
.mp-refer-qr {
  width: 64px;
  height: 64px;
  border-radius: 8px;
  flex-shrink: 0;
  background: #FFFFFF;
  box-shadow: inset 0 1px 2px rgba(0,0,0,0.25);
}

/* 网格卡（积分兑换 / 我的券） */
.mp-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin: 0 16px 4px;
}
.mp-grid .mp-card {
  margin: 0;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 4px;
  min-height: 92px;
  padding: 14px 16px;
}
.mp-value {
  font-size: 22px;
  font-weight: 800;
  color: #FFFFFF;
  text-shadow: 0 -1px 1px rgba(0,0,0,0.4), 0 1px 1px rgba(255,255,255,0.25);
}
.mp-coupon-code {
  margin-top: 2px;
  font-size: 11px;
  color: #FFFFFF;
  opacity: 0.85;
  font-family: 'SF Mono', 'Roboto Mono', monospace;
  letter-spacing: 0.5px;
}

/* 兑换/券 5 色循环 */
.mp-redeem-0, .mp-coupon-0 { background-color: #C4923A; border-color: #9A7425; } /* 金黄 */
.mp-redeem-1, .mp-coupon-1 { background-color: #C9956C; border-color: #A87C48; } /* 浅橙棕 */
.mp-redeem-2, .mp-coupon-2 { background-color: #9B4A3E; border-color: #6E332A; } /* 深红棕 */
.mp-redeem-3, .mp-coupon-3 { background-color: #8B8B90; border-color: #6A6A6E; } /* 灰紫 */
.mp-redeem-4, .mp-coupon-4 { background-color: #6B6E64; border-color: #4E5049; } /* 深灰绿 */
</style>
