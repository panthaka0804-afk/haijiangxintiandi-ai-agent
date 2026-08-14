<template>
  <div class="notify-page">
    <h3 class="page-h">触达中心</h3>
    <p class="page-sub">主动触达会员：扫描今日生日 / 周年庆 / 沉默会员，批量发送短信（微信订阅消息待域名备案完成后接入）。</p>

    <div class="scan-card">
      <button class="scan-btn" :disabled="scanning" @click="runScan">
        {{ scanning ? '扫描发送中…' : '立即触达扫描' }}
      </button>
      <div class="seg-row" v-if="result">
        <div class="seg" v-for="s in segs" :key="s.key">
          <div class="seg-num">{{ result[s.key] }}</div>
          <div class="seg-label">{{ s.label }}</div>
        </div>
        <div class="seg seg-sent">
          <div class="seg-num">{{ result.sent }}</div>
          <div class="seg-label">本次已发</div>
        </div>
      </div>
      <p class="mode-tip" v-if="result">当前为沙箱模式（未配置短信密钥），发送记录将落库并在下方日志可见；配置 SMS_PROVIDER/密钥后即真实发送。</p>
    </div>

    <div class="log-card">
      <div class="log-head">
        <span>发送日志（最近 50 条）</span>
        <button class="refresh-btn" @click="loadLog">刷新</button>
      </div>
      <div v-if="!logs.length" class="empty">暂无发送记录</div>
      <table v-else class="log-table">
        <thead>
          <tr><th>手机号</th><th>类型</th><th>内容</th><th>状态</th><th>时间</th></tr>
        </thead>
        <tbody>
          <tr v-for="(l, i) in logs" :key="i">
            <td>{{ l.phone }}</td>
            <td><span class="tag" :class="'tag-' + l.kind">{{ kindLabel(l.kind) }}</span></td>
            <td class="content">{{ l.content }}</td>
            <td><span class="st" :class="l.status === 'sent' ? 'st-ok' : 'st-sb'">{{ l.status }}</span></td>
            <td class="time">{{ l.created_at }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { notifyScan, getNotifyLog } from '@/api'

const scanning = ref(false)
const result = ref(null)
const logs = ref([])
const segs = [
  { key: 'birthday', label: '今日生日' },
  { key: 'anniversary', label: '周年庆' },
  { key: 'silent', label: '沉默会员' },
]

function kindLabel(k) {
  return { birthday: '生日', anniversary: '周年庆', recall: '沉默召回', direct: '直接' }[k] || k
}

async function runScan() {
  scanning.value = true
  const r = await notifyScan()
  scanning.value = false
  if (r.ok) {
    result.value = r
    loadLog()
  }
}

async function loadLog() {
  const r = await getNotifyLog()
  if (r.ok) logs.value = r.logs || []
}

onMounted(loadLog)
</script>

<style scoped>
.notify-page { padding: 4px; }
.page-h { font-size: 18px; color: #fff; margin: 0 0 6px; }
.page-sub { font-size: 13px; color: #999; margin: 0 0 18px; line-height: 1.6; }
.scan-card {
  background: #1A1A1A; border: 1px solid #262626; border-radius: 14px;
  padding: 20px; margin-bottom: 18px;
}
.scan-btn {
  background: linear-gradient(135deg, #FF7B2C, #E85D04); color: #fff; border: none;
  padding: 12px 28px; border-radius: 10px; font-size: 15px; font-weight: 600; cursor: pointer;
  transition: all 0.2s;
}
.scan-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.scan-btn:hover:not(:disabled) { box-shadow: 0 6px 16px rgba(232, 93, 4, 0.35); }
.seg-row { display: flex; gap: 14px; margin-top: 18px; flex-wrap: wrap; }
.seg {
  flex: 1; min-width: 110px; background: #0F0F0F; border: 1px solid #2A2A2A; border-radius: 10px;
  padding: 14px; text-align: center;
}
.seg-sent { border-color: rgba(255, 123, 44, 0.5); }
.seg-num { font-size: 24px; font-weight: 800; color: #FF7B2C; }
.seg-label { font-size: 12px; color: #aaa; margin-top: 4px; }
.mode-tip { font-size: 12px; color: #888; margin: 14px 0 0; line-height: 1.6; }
.log-card {
  background: #1A1A1A; border: 1px solid #262626; border-radius: 14px; padding: 18px;
}
.log-head {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 14px; color: #fff; margin-bottom: 12px;
}
.refresh-btn {
  background: #262626; color: #ccc; border: none; padding: 6px 14px; border-radius: 8px;
  font-size: 12px; cursor: pointer;
}
.refresh-btn:hover { background: #333; color: #fff; }
.empty { color: #777; font-size: 13px; padding: 20px 0; text-align: center; }
.log-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.log-table th, .log-table td { padding: 9px 8px; text-align: left; border-bottom: 1px solid #262626; }
.log-table th { color: #888; font-weight: 600; }
.log-table td { color: #ddd; }
.log-table .content { max-width: 320px; color: #bbb; }
.log-table .time { color: #888; white-space: nowrap; }
.tag { padding: 2px 8px; border-radius: 6px; font-size: 11px; }
.tag-birthday { background: rgba(232, 128, 158, 0.2); color: #E8809E; }
.tag-anniversary { background: rgba(196, 146, 58, 0.2); color: #C4923A; }
.tag-recall { background: rgba(232, 93, 4, 0.2); color: #FF7B2C; }
.tag-direct { background: rgba(139, 139, 144, 0.2); color: #8B8B90; }
.st { padding: 2px 8px; border-radius: 6px; font-size: 11px; }
.st-ok { background: rgba(62, 142, 65, 0.2); color: #3E8E41; }
.st-sb { background: rgba(139, 139, 144, 0.2); color: #8B8B90; }
</style>
