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
      <van-cell-group inset style="margin-top: 16px;">
        <van-cell
          title="激励中心"
          label="每日签到 · 成长值 · 成就徽章"
          value="去签到"
          icon="gift-o"
          is-link
          @click="$router.push('/points')"
        />
      </van-cell-group>

      <!-- 邻里特权：会员互赠 + 人脉引荐 -->
      <van-cell-group inset title="邻里特权" style="margin-top: 16px;">
        <!-- 我的引荐码 -->
        <div class="nb-refer">
          <div class="nb-refer-left">
            <div class="nb-refer-code">{{ gift.referral_code || '—' }}</div>
            <div class="nb-refer-tip">把码发给邻居，TA 注册时填写，双方各得 {{ referBase }} 分</div>
            <div class="nb-refer-actions">
              <van-button size="mini" round plain @click="copyCode">复制引荐码</van-button>
              <van-button size="mini" round plain @click="openQr">看二维码</van-button>
            </div>
          </div>
          <img v-if="refQr" :src="refQr" class="nb-refer-qr" alt="引荐二维码" />
        </div>

        <!-- 高阶会员：赠折扣权 -->
        <template v-if="gift.is_high_tier">
          <van-cell title="赠折扣权给朋友" :label="`本月还可赠 ${gift.gift_quota} 次 · 朋友核销后首单享你的卡级`"
            icon="diamond-o" is-link @click="showSend = true" />
        </template>
        <template v-else>
          <van-cell title="升级金卡/钻石卡可赠折扣权" label="高阶会员每月可赠朋友一次折扣权" icon="diamond-o" is-link @click="showUpgradeTip" />
        </template>

        <!-- 我收到的折扣权券（待核销） -->
        <van-cell v-if="gift.received_cards && gift.received_cards.length"
          title="我收到的折扣权" :label="`${gift.received_cards.length} 张待核销`"
          icon="coupon-o" is-link @click="showRedeem = true" />

        <!-- 我赠出的券 -->
        <van-cell v-if="gift.sent_cards && gift.sent_cards.length"
          :title="`我赠出的折扣权 (${gift.sent_cards.length})`" icon="send-gift-o" is-link @click="showSent = true" />
      </van-cell-group>

      <!-- 兑换列表 -->
      <van-cell-group inset title="积分兑换" style="margin-top: 16px;">
        <van-cell
          v-for="item in redeemList"
          :key="item.id"
          :title="item.name"
          :label="`所需积分: ${item.points}`"
          :value="item.value"
          @click="showRedeemConfirm(item)"
          is-link
        />
      </van-cell-group>

      <!-- 我的券 -->
      <van-cell-group inset title="我的券" style="margin-top: 16px" v-if="coupons && coupons.length">
        <van-cell
          v-for="(c, i) in coupons"
          :key="(c.code || 'c') + '-' + i"
          :title="c.item || '优惠券'"
          :label="'有效期至 ' + (c.time || '—')"
          :value="c.code || '—'"
        />
      </van-cell-group>

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
          <p style="font-size:13px;color:#FFB877;margin-top:8px;">引荐码：{{ gift.referral_code }}</p>
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

.nb-refer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 4px;
}
.nb-refer-left { min-width: 0; flex: 1; }
.nb-refer-code {
  font-size: 22px;
  font-weight: 700;
  color: #FFB877;
  letter-spacing: 2px;
  font-family: 'SF Mono', 'Roboto Mono', monospace;
}
.nb-refer-tip {
  font-size: 12px;
  color: #999;
  margin: 6px 0 10px;
  line-height: 1.5;
}
.nb-refer-actions { display: flex; gap: 8px; }
.nb-refer-actions :deep(.van-button) {
  border-color: #FFB877;
  color: #FFB877;
}
.nb-refer-qr {
  width: 84px;
  height: 84px;
  border-radius: 8px;
  flex-shrink: 0;
  background: #1C1C1E;
}
</style>
