<template>
  <!-- 遮罩 -->
  <van-overlay :show="visible" @click="$emit('close')" z-index="999" />

  <!-- 弹窗 -->
  <transition name="re-popup">
    <div v-if="visible" class="re-container">
      <div class="re-sheet" @click.stop>
        <h3>积分兑换</h3>

        <!-- 当前积分 -->
        <div class="re-summary" v-if="member">
          <div class="re-points">
            我的积分：<b>{{ member.points || 0 }}</b>
          </div>
          <div class="re-progress">
            <div class="re-progress-bar" :style="{ width: pointsPercent + '%' }"></div>
          </div>
          <div class="re-progress-label">
            距下一等级还差 {{ nextLevelNeeded }} 分
          </div>
        </div>

        <div class="re-summary re-summary--guest" v-else>
          <p>请先登录会员查看积分</p>
        </div>

        <!-- 兑换列表 -->
        <div class="re-list-title">可兑换项目</div>
        <div class="re-list">
          <div
            v-for="item in sortedItems"
            :key="item.id"
            class="re-item"
            :class="{
              're-item--affordable': member && member.points >= item.points,
              're-item--locked': member && member.points < item.points
            }"
            @click="selectItem(item)"
          >
            <div class="re-item-icon"><SvgIcon :name="item.icon" :size="24" color="#9E9E9E" /></div>
            <div class="re-item-info">
              <div class="re-item-name">{{ item.name }}</div>
              <div class="re-item-meta">{{ item.desc }}</div>
            </div>
            <div class="re-item-right">
              <div class="re-item-points">{{ item.points }}分</div>
              <div class="re-item-value">≈{{ item.value }}</div>
              <div class="re-item-ratio">{{ item.ratio }}分/元</div>
            </div>
          </div>
        </div>

        <!-- 确认按钮 -->
        <button
          v-if="selectedItem"
          class="re-confirm"
          :class="{ 're-confirm--disabled': !member || member.points < selectedItem.points }"
          :disabled="!member || member.points < selectedItem.points"
          @click="confirmRedeem"
        >
          兑换 {{ selectedItem.name }} · 扣 {{ selectedItem.points }} 分
        </button>

        <button class="re-close" @click="$emit('close')">关闭</button>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, computed } from 'vue'
import SvgIcon from './SvgIcon.vue'

const props = defineProps({
  visible: Boolean,
  member: { type: Object, default: null }
})

const emit = defineEmits(['close', 'redeem'])

const selectedItem = ref(null)

const items = [
  { id: 1, icon: 'parking', name: '停车券', desc: '海江新天地1小时停车券', points: 500, value: '¥10', ratio: 50 },
  { id: 2, icon: 'shop', name: 'B1美食券', desc: '海江食集通用10元', points: 800, value: '¥10', ratio: 80 },
  { id: 3, icon: 'star', name: '瑞幸咖啡券', desc: '瑞幸中杯代金券', points: 1000, value: '¥35', ratio: 28.6 },
  { id: 4, icon: 'gift', name: 'SFC电影票', desc: 'SFC上影影城通兑票', points: 2000, value: '¥45', ratio: 44.5 },
  { id: 5, icon: 'star', name: '华为30元券', desc: '华为授权店30元代金券', points: 2500, value: '¥30', ratio: 12 },
  { id: 6, icon: 'calendar', name: '泡泡米体验课', desc: '泡泡米儿童体验课', points: 2000, value: '¥49', ratio: 40.8 },
  { id: 7, icon: 'gift', name: '康友四季足浴', desc: '康友四季足浴券', points: 2500, value: '¥30', ratio: 12 },
  { id: 8, icon: 'tag', name: '朱光玉火锅券', desc: '朱光玉火锅50元代金券', points: 3000, value: '¥50', ratio: 60 },
  { id: 9, icon: 'star', name: '哇咔健身周卡', desc: '哇咔健身体验周卡', points: 4000, value: '¥39', ratio: 9.75 },
]

// 性价比排序：价值/积分越高越划算
const sortedItems = computed(() => {
  return [...items].sort((a, b) => {
    const ra = a.points / parseFloat(a.value.replace('¥', ''))
    const rb = b.points / parseFloat(b.value.replace('¥', ''))
    return ra - rb
  })
})

const pointsPercent = computed(() => {
  if (!props.member) return 0
  const p = props.member.points || 0
  return Math.min(100, (p / 10000) * 100)
})

const nextLevelNeeded = computed(() => {
  if (!props.member) return '--'
  const p = props.member.points || 0
  const levels = { 普卡: 0, 银卡: 3000, 金卡: 6000, 钻石卡: 20000 }
  const current = levels[props.member.membership_level] || 0
  const next = Object.entries(levels).find(([_, v]) => v > current)?.[1] || 10000
  return Math.max(0, next - p)
})

function selectItem(item) {
  if (!props.member) return
  if (props.member.points < item.points) return
  selectedItem.value = selectedItem.value?.id === item.id ? null : item
}

function confirmRedeem() {
  if (!selectedItem.value || !props.member) return
  if (props.member.points < selectedItem.value.points) return
  emit('redeem', selectedItem.value)
  emit('close')
}
</script>

<style scoped>
.re-container {
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

.re-sheet {
  background: #1A1A1A;
  border-radius: 20px;
  width: 340px;
  max-width: 90vw;
  max-height: 80vh;
  overflow-y: auto;
  padding: 20px;
  z-index: 1001;
}

.re-sheet h3 {
  text-align: center;
  margin: 0 0 16px;
  font-size: 18px;
  color: #F0F0F0;
}

/* 积分概览 */
.re-summary {
  background: linear-gradient(135deg, #1A1A1A, #1A1A1A);
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 16px;
  text-align: center;
}

.re-summary--guest {
  background: #1A1A1A;
}

.re-summary--guest p {
  color: #999;
  font-size: 13px;
  margin: 0;
}

.re-points {
  font-size: 14px;
  color: #BBBBBB;
  margin-bottom: 6px;
}

.re-points b {
  color: #BBBBBB;
  font-size: 22px;
}

.re-progress {
  height: 6px;
  background: #1A1A1A;
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 4px;
}

.re-progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #1A1A1A, #1A1A1A);
  border-radius: 3px;
  transition: width 0.3s;
}

.re-progress-label {
  font-size: 11px;
  color: #999;
}

/* 列表标题 */
.re-list-title {
  font-size: 14px;
  font-weight: 700;
  color: #F0F0F0;
  margin-bottom: 8px;
  padding-bottom: 4px;
  border-bottom: 1px solid #eee;
}

/* 兑换项 */
.re-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.re-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-radius: 12px;
  background: #1A1A1A;
  cursor: pointer;
  transition: all 0.15s;
  border: 2px solid transparent;
}

.re-item--affordable {
  background: #1A1A1A;
  border-color: #E4E4E4;
}

.re-item--affordable:hover {
  border-color: #A5A5A5;
}

.re-item--locked {
  opacity: 0.45;
  cursor: not-allowed;
}

.re-item:active:not(.re-item--locked) {
  transform: scale(0.98);
}

.re-item-icon {
  font-size: 28px;
  flex-shrink: 0;
}

.re-item-info {
  flex: 1;
  min-width: 0;
}

.re-item-name {
  font-size: 14px;
  font-weight: 600;
  color: #F0F0F0;
}

.re-item-meta {
  font-size: 11px;
  color: #999;
  margin-top: 2px;
}

.re-item-right {
  text-align: right;
  flex-shrink: 0;
}

.re-item-points {
  font-size: 14px;
  font-weight: 700;
  color: #BBBBBB;
}

.re-item-value {
  font-size: 11px;
  color: #999;
}

.re-item-ratio {
  font-size: 10px;
  color: #bbb;
  margin-top: 2px;
}

/* 确认按钮 */
.re-confirm {
  display: block;
  width: 100%;
  padding: 12px;
  margin-top: 14px;
  background: linear-gradient(135deg, #1A1A1A, #1A1A1A);
  color: #fff;
  border: none;
  border-radius: 25px;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  font-family: inherit;
}

.re-confirm--disabled {
  background: #1A1A1A;
  color: #999;
  cursor: not-allowed;
}

.re-confirm:active:not(.re-confirm--disabled) {
  transform: scale(0.96);
}

.re-close {
  display: block;
  width: 100%;
  padding: 10px;
  background: #1A1A1A;
  border: none;
  border-radius: 10px;
  margin-top: 8px;
  color: #BBBBBB;
  font-size: 14px;
  cursor: pointer;
  font-family: inherit;
}

/* 动画 */
.re-popup-enter-active,
.re-popup-leave-active {
  transition: all 0.3s ease;
}

.re-popup-enter-from .re-sheet,
.re-popup-leave-to .re-sheet {
  transform: scale(0.9);
  opacity: 0;
}
</style>
