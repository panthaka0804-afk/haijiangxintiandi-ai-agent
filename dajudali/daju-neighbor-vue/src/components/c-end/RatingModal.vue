<template>
  <div v-if="visible" class="rm-overlay" @click.self="close">
    <div class="rm-modal">
      <div class="rm-close" @click="close">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#888" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </div>
      <div class="rm-title">{{ title }}</div>
      <div class="rm-sub">{{ subtitle }}</div>
      <div class="rm-stars">
        <button v-for="i in 5" :key="i" class="rm-star" :class="{ active: i <= rating }" @click="rating = i">
          <svg width="34" height="34" viewBox="0 0 24 24" :fill="i <= rating ? '#FFB400' : 'none'" stroke="#FFB400" stroke-width="1.5" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
        </button>
      </div>
      <div class="rm-stars-label">{{ starLabel }}</div>
      <textarea v-model="text" placeholder="说说您的体验，帮助我们改进（可选）" class="rm-textarea" rows="2"></textarea>
      <div class="rm-actions">
        <button class="rm-btn-cancel" @click="close">稍后再说</button>
        <button class="rm-btn-submit" :disabled="!rating || submitting" @click="submit">{{ submitting ? '提交中...' : '提交评价' }}</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  visible: Boolean,
  title: { type: String, default: '请评价本次服务' },
  subtitle: { type: String, default: '' },
  feedbackType: { type: String, default: 'chat_ai' }, // chat_ai / chat_human / business
  bizType: { type: String, default: '' },
  orderId: { type: String, default: '' },
  phone: { type: String, default: '' }
})

const emit = defineEmits(['close', 'submitted'])

const rating = ref(0)
const text = ref('')
const submitting = ref(false)

const starLabels = ['', '很不满意', '不太满意', '一般', '满意', '非常满意']
const starLabel = computed(() => rating.value ? starLabels[rating.value] : '点击星星评分')

function close() {
  emit('close')
}

async function submit() {
  if (!rating.value) return
  submitting.value = true
  try {
    await fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        feedback_type: props.feedbackType,
        biz_type: props.bizType,
        order_id: props.orderId,
        rating: rating.value,
        feedback_text: text.value,
        phone: props.phone
      })
    })
    emit('submitted')
    close()
  } catch (e) {
    submitting.value = false
  }
}
</script>

<style scoped>
.rm-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 9999; display: flex; align-items: center; justify-content: center; -webkit-backdrop-filter: blur(4px); backdrop-filter: blur(4px); }
.rm-modal { background: #1C1C1E; border-radius: 20px; padding: 24px 22px; width: 320px; position: relative; box-sizing: border-box; }
.rm-close { position: absolute; top: 14px; right: 14px; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; }
.rm-close:active { background: rgba(255,255,255,0.06); }
.rm-title { font-size: 17px; font-weight: 700; color: #F0F0F0; text-align: center; }
.rm-sub { font-size: 12px; color: #888; text-align: center; margin-top: 4px; }
.rm-stars { display: flex; justify-content: center; gap: 8px; margin: 18px 0 6px; }
.rm-star { background: none; border: none; padding: 0; cursor: pointer; transition: transform 0.1s; }
.rm-star:active { transform: scale(1.2); }
.rm-stars-label { text-align: center; font-size: 13px; color: #FFB400; min-height: 18px; margin-bottom: 12px; }
.rm-textarea { width: 100%; box-sizing: border-box; padding: 10px 12px; border-radius: 10px; border: 1px solid #333; background: #151515; color: #ddd; font-size: 13px; resize: none; font-family: 'PingFang SC', sans-serif; }
.rm-textarea::placeholder { color: #555; }
.rm-actions { display: flex; gap: 10px; margin-top: 14px; }
.rm-btn-cancel { flex: 1; padding: 11px 0; border-radius: 10px; border: 1px solid #333; background: #151515; color: #999; font-size: 14px; cursor: pointer; }
.rm-btn-submit { flex: 2; padding: 11px 0; border-radius: 10px; border: none; background: linear-gradient(135deg, #E8552A, #FF7B2C); color: #fff; font-size: 14px; font-weight: 600; cursor: pointer; }
.rm-btn-submit:disabled { opacity: 0.4; cursor: default; }
</style>
