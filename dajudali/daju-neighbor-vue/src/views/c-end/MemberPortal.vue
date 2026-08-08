<template>
  <div class="member-page">
    <van-nav-bar title="会员中心" left-text="返回" left-arrow @click-left="$router.back()" fixed placeholder>
      <template #right>
        <van-button size="small" round plain @click="userStore.largeFont = !userStore.largeFont" :style="{ color: userStore.largeFont ? '#9E9E9E' : '#777', borderColor: userStore.largeFont ? '#9E9E9E' : '#444', fontWeight: '700' }">{{ userStore.largeFont ? '老年关怀' : '老年关怀' }}</van-button>
      </template>
    </van-nav-bar>

    <!-- 未查询：输入手机号 -->
    <template v-if="!memberData">
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
      </van-form>
    </template>

    <!-- 会员信息展示 -->
    <template v-else>
      <div class="member-card">
        <div class="card-header">
          <span class="level-badge" :class="memberData.level">{{ memberData.level }}</span>
          <span class="card-name">{{ memberData.name }}</span>
        </div>
        <div class="card-body">
          <div class="info-row">
            <span class="label">手机号</span>
            <span>{{ memberData.phone }}</span>
          </div>
          <div class="info-row">
            <span class="label">当前积分</span>
            <span class="value highlight">{{ memberData.points }}</span>
          </div>
          <div class="info-row">
            <span class="label">会员折扣</span>
            <span class="value highlight">{{ memberData.discount || '98折' }}</span>
          </div>
          <div class="info-row">
            <span class="label">距升级还需</span>
            <span>{{ memberData.needUpgrade || '-' }}分</span>
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
          v-for="c in coupons"
          :key="c.code"
          :title="c.name"
          :label="'有效期至 ' + c.expire_date"
          :value="c.code"
        />
      </van-cell-group>
    </template>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useUserStore } from '@/stores/user'
import { showToast, showConfirmDialog } from 'vant'

const userStore = useUserStore()
import { getMemberPortal, getMemberCoupons, redeemPoints } from '@/api'

const phone = ref('')
const loading = ref(false)
const memberData = ref(null)
const coupons = ref([])

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
    const res = await getMemberPortal(phone.value)
    if (res.ok) {
      memberData.value = res.member
      const couponRes = await getMemberCoupons(phone.value)
      if (couponRes.ok) {
        coupons.value = couponRes.coupons || []
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

async function showRedeemConfirm(item) {
  try {
    await showConfirmDialog({
      title: '确认兑换',
      message: `确定用 ${item.points} 积分兑换"${item.name}"？\n兑换后剩余 ${memberData.value.points - item.points} 分`,
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
  background: #1A1A1A;
}

.member-card {
  margin: 16px;
  background: linear-gradient(135deg, #1A1A1A, #2A2A2A);
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 2px 12px #999999;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.level-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  color: #fff;
  background: #999;
}

.level-badge.普卡 { background: #999; }
.level-badge.银卡 { background: #1A1A1A; }
.level-badge.金卡 { background: #1A1A1A; }
.level-badge.钻石卡 { background: #1A1A1A; }

.card-name {
  font-size: 18px;
  font-weight: 600;
  color: #F0F0F0;
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
  color: #999999;
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
