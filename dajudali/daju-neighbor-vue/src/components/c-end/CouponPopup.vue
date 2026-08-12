<template>
  <!-- 遮罩 -->
  <van-overlay :show="visible" @click="$emit('close')" z-index="999" />

  <!-- 弹窗 -->
  <transition name="cpn-popup">
    <div v-if="visible" class="cpn-popup">
      <div class="cpn-sheet">
        <h3>领券中心</h3>

        <template v-for="grp in grouped" :key="grp.key">
          <div class="cpn-group-title">{{ grp.label }}</div>
          <div
            v-for="c in grp.items"
            :key="c.id"
            class="cpn-card"
            :class="{ 'cpn-card--used': c.claimed }"
          >
            <!-- 水印 -->
            <div class="cpn-watermark"><SvgIcon name="tag" :size="40" color="#8B8B8B" /></div>

            <!-- 顶部：金额 + 标题 -->
            <div class="cpn-top">
              <div class="cpn-amount">
                <small>¥</small>{{ c.amount }}
              </div>
              <div class="cpn-detail">
                <div class="cpn-name">{{ c.title }}</div>
                <div>{{ c.desc }}</div>
              </div>
            </div>

            <!-- 底部：条件 + 按钮 -->
            <div class="cpn-meta">
              满{{ c.min }}元可用 | 有效期至 {{ c.expire }} | 券码：{{ c.code }}
            </div>

            <button
              v-if="!c.claimed"
              class="cpn-btn"
              @click="claim(c)"
            >立即领取</button>
            <div v-else class="cpn-done">已领取 · 去收银台核销</div>
          </div>
        </template>

        <button class="cpn-close-btn" @click="$emit('close')">关闭</button>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import SvgIcon from './SvgIcon.vue'

const props = defineProps({
  visible: Boolean,
  showToast: { type: Function, default: () => {} }
})

const emit = defineEmits(['close', 'claim'])

const coupons = reactive([
  { id: 1, amount: 20, min: 100, title: '餐饮通用券', desc: '海江新天地所有餐饮商户可用', expire: '2026-08-31', code: 'DJ0820', category: '餐饮', claimed: false },
  { id: 2, amount: 50, min: 300, title: '零售满减券', desc: '服饰/美妆/数码品类可用', expire: '2026-09-15', code: 'DJ0850', category: '零售', claimed: false },
  { id: 3, amount: 10, min: 50, title: '小吃饮品券', desc: 'B1美食广场通用', expire: '2026-08-31', code: 'DJ0810', category: '餐饮', claimed: false },
  { id: 4, amount: 15, min: 0, title: '新人无门槛券', desc: '全场通用，仅限首单', expire: '2026-08-15', code: 'DJ0815', category: '通用', claimed: false },
  { id: 5, amount: 2, min: 0, title: '停车券', desc: '可抵扣2小时停车费', expire: '2026-12-31', code: 'PARK02', category: '停车', claimed: false },
])

// 按品类分组展示（顺序固定，避免每次渲染乱序）
const GROUP_ORDER = ['餐饮', '零售', '停车', '通用']
const GROUP_LABEL = {
  '餐饮': '餐饮券',
  '零售': '零售券',
  '停车': '停车券',
  '通用': '通用 · 新人专享',
}
const grouped = computed(() => {
  const map = {}
  for (const c of coupons) {
    ;(map[c.category] || (map[c.category] = [])).push(c)
  }
  return GROUP_ORDER.filter(k => map[k]).map(k => ({
    key: k,
    label: GROUP_LABEL[k] || k,
    items: map[k],
  }))
})

function claim(c) {
  c.claimed = true
  // 生成唯一券码
  const code = 'HJ' + Date.now().toString(36).toUpperCase().slice(-6) + Math.random().toString(36).slice(2, 5).toUpperCase()
  c.code = code
  emit('claim', c)
}
</script>

<style scoped>
/* 弹窗容器 */
.cpn-popup {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1000;
  display: flex;
  justify-content: center;
  align-items: center;
}

.cpn-sheet {
  background: #1A1A1A;
  border-radius: 20px;
  width: 340px;
  max-width: 90vw;
  max-height: 75vh;
  overflow-y: auto;
  padding: 20px;
  z-index: 1001;
  position: relative;
}

.cpn-sheet h3 {
  text-align: center;
  margin: 0 0 16px;
  font-size: 18px;
  color: #F0F0F0;
}

/* 分组标题 */
.cpn-group-title {
  font-size: 13px;
  font-weight: 700;
  color: #C4923A;
  letter-spacing: 0.4px;
  padding: 4px 2px 8px;
  margin-top: 8px;
}
.cpn-group-title:first-child { margin-top: 0; }

/* 优惠券卡片 */
.cpn-card {
  position: relative;
  margin-bottom: 12px;
  background: linear-gradient(135deg, #1A1A1A, #1A1A1A);
  color: #fff;
  border-radius: 14px;
  padding: 16px;
  margin-bottom: 12px;
  overflow: hidden;
  user-select: none;
}

.cpn-card--used {
  opacity: 0.5;
  pointer-events: none;
}

/* 水印 */
.cpn-watermark {
  position: absolute;
  right: -10px;
  bottom: -10px;
  font-size: 60px;
  opacity: 0.1;
}

/* 金额 + 标题行 */
.cpn-top {
  display: flex;
  align-items: flex-start;
  margin-bottom: 10px;
}

.cpn-amount {
  font-size: 36px;
  font-weight: 800;
  line-height: 1;
  margin-right: 10px;
  flex-shrink: 0;
}

.cpn-amount small {
  font-size: 18px;
}

.cpn-detail {
  font-size: 12px;
  opacity: 0.9;
  line-height: 1.5;
}

.cpn-name {
  font-weight: 700;
  font-size: 14px;
}

/* 条件和券码 */
.cpn-meta {
  font-size: 11px;
  opacity: 0.8;
  line-height: 1.6;
}

/* 领取按钮 */
.cpn-btn {
  display: inline-block;
  background: #1A1A1A;
  color: #999999;
  border: none;
  border-radius: 20px;
  padding: 6px 20px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  margin-top: 8px;
  font-family: inherit;
}

.cpn-btn:active {
  transform: scale(0.95);
}

/* 已领取提示 */
.cpn-done {
  font-size: 11px;
  opacity: 0.7;
  margin-top: 8px;
}

/* 关闭按钮 */
.cpn-close-btn {
  display: block;
  width: 100%;
  padding: 10px;
  background: #1A1A1A;
  border: none;
  border-radius: 10px;
  margin-top: 12px;
  color: #BBBBBB;
  font-size: 14px;
  cursor: pointer;
  font-family: inherit;
}

/* 弹窗动画 */
.cpn-popup-enter-active,
.cpn-popup-leave-active {
  transition: all 0.3s ease;
}

.cpn-popup-enter-from .cpn-sheet,
.cpn-popup-leave-to .cpn-sheet {
  transform: scale(0.9);
  opacity: 0;
}
</style>
