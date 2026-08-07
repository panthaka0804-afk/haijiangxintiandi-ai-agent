<template>
  <!-- 会员栏（已登录时显示） -->
  <transition name="mb-slide">
    <div v-if="member" class="mb-bar">
      <!-- 头像 -->
      <div class="mb-avatar">{{ avatarText }}</div>

      <!-- 信息 -->
      <div class="mb-info">
        <div class="mb-name">{{ member.display_name || '会员' }}</div>
        <div class="mb-meta">
          {{ member.membership_level || '普卡' }}
          · {{ (member.discount || 98) }}折
          · {{ member.points || 0 }}积分
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="mb-actions">
        <button @click="$emit('showCoupons')">我的券</button>
        <button @click="$emit('showPoints')">积分兑</button>
        <button @click="$emit('logout')">退出</button>
      </div>
    </div>
  </transition>

  <!-- 未登录提示 -->
  <div v-if="!member" class="mb-bar mb-bar--guest" @click="$emit('login')">
    <div class="mb-avatar mb-avatar--guest">👤</div>
    <div class="mb-info">
      <div class="mb-name">点击登录会员</div>
      <div class="mb-meta">登录查看积分和优惠权益 →</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  member: { type: Object, default: null }
})

defineEmits(['login', 'showCoupons', 'showPoints', 'logout'])

const avatarText = computed(() => {
  if (!props.member) return 'M'
  const name = props.member.display_name || '会员'
  return name.charAt(0)
})
</script>

<style scoped>
/* 会员栏 */
.mb-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  background: linear-gradient(135deg, #FFF8F0, #FFF3E0);
  padding: 14px 16px;
  border-radius: 16px;
  margin: 4px 4px 10px;
  box-shadow: 0 2px 12px rgba(255, 107, 0, 0.12);
  flex-shrink: 0;
}

/* 未登录版 */
.mb-bar--guest {
  cursor: pointer;
  background: linear-gradient(135deg, #f5f5f5, #eee);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.mb-bar--guest .mb-name {
  color: #FF7B2C;
}

.mb-bar--guest .mb-meta {
  color: #999;
}

/* 头像 */
.mb-avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: linear-gradient(135deg, #FF6B00, #E65100);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 700;
  flex-shrink: 0;
}

.mb-avatar--guest {
  background: linear-gradient(135deg, #ccc, #aaa);
}

/* 信息区 */
.mb-info {
  flex: 1;
  min-width: 0;
}

.mb-name {
  font-size: 15px;
  font-weight: 700;
  color: #333;
  line-height: 1.3;
}

.mb-meta {
  font-size: 11px;
  color: #888;
  margin-top: 2px;
}

/* 操作按钮 */
.mb-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.mb-actions button {
  padding: 6px 10px;
  border: none;
  border-radius: 16px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  background: #fff;
  color: #E65100;
  border: 1px solid #FFE0B2;
  font-family: inherit;
  white-space: nowrap;
}

.mb-actions button:active {
  background: #FFF3E0;
}

/* 展开动画 */
.mb-slide-enter-active,
.mb-slide-leave-active {
  transition: all 0.3s ease;
}

.mb-slide-enter-from,
.mb-slide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
