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
    </template>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useUserStore } from '@/stores/user'
import { useMemberStore } from '@/stores/member'
import { showToast, showConfirmDialog } from 'vant'
import { getMemberCoupons } from '@/api'

const userStore = useUserStore()
const memberStore = useMemberStore()

const phone = ref('')
const loading = ref(false)
const coupons = ref([])

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
</style>
