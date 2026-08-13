<template>
  <div class="nh-page">
    <van-nav-bar title="邻里帮" left-text="返回" left-arrow @click-left="$router.back()" fixed placeholder />

    <!-- 顶部发单 hero -->
    <div class="nh-hero" @click="openPublish">
      <div class="nh-hero-bg"></div>
      <div class="nh-hero-icon">
        <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><circle cx="12" cy="14" r="3"/><path d="M12 11v3l2 1"/>
        </svg>
      </div>
      <div class="nh-hero-text">
        <div class="nh-hero-title">谁家有个小忙？</div>
        <div class="nh-hero-desc">搬箱子 · 代取快递 · 临时照看 · 问个路，发个悬赏，邻居帮你搞定</div>
      </div>
      <span class="nh-hero-btn">发悬赏</span>
    </div>

    <!-- 规则条 -->
    <div class="nh-rule">
      <span>赏金预付冻结 · 完成确认到账</span>
      <span class="nh-rule-dot">·</span>
      <span>接单再得平台补贴 {{ systemBonus }} 分</span>
    </div>

    <!-- Tab：悬赏墙 / 我发的 / 我接的 -->
    <van-tabs v-model:active="tab" sticky offset-top="46" line-width="20px" @change="loadList">
      <van-tab title="悬赏墙" name="wall" />
      <van-tab title="我发的" name="published" />
      <van-tab title="我接的" name="accepted" />
    </van-tabs>

    <div class="nh-list">
      <div v-if="!list.length" class="nh-empty">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#555" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>
        <p>{{ tab === 'wall' ? '悬赏墙还空着，发个第一个小忙试试？' : '暂无记录' }}</p>
      </div>

      <div v-for="h in list" :key="h.id" class="nh-card" :class="statusClass(h.status)">
        <div class="nh-card-top">
          <span class="nh-tag">{{ h.category }}</span>
          <span class="nh-status" :class="'st-' + h.status">{{ statusText(h.status) }}</span>
        </div>
        <div class="nh-title">{{ h.title }}</div>
        <div class="nh-detail" v-if="h.detail">{{ h.detail }}</div>
        <div class="nh-meta">
          <span v-if="h.location">地点 · {{ h.location }}</span>
          <span v-if="h.expire_at">截止 · {{ h.expire_at }}</span>
        </div>
        <div class="nh-card-foot">
          <div class="nh-reward">
            <span class="nh-reward-num">{{ h.reward }}</span>
            <span class="nh-reward-unit">积分</span>
            <span class="nh-bonus">+{{ systemBonus }} 平台补贴</span>
          </div>
          <div class="nh-who">
            <span v-if="tab !== 'published'">发单 {{ h.publisher_mask }}</span>
            <span v-if="h.acceptor_phone"> · 接单 {{ h.acceptor_mask }}</span>
          </div>
        </div>

        <!-- 操作按钮：随身份 & 状态变化 -->
        <div class="nh-actions">
          <button v-if="tab === 'wall' && h.status === 'open' && h.publisher_phone !== myPhone"
            class="nh-btn nh-btn-primary" @click="doAccept(h)">抢单</button>
          <button v-if="tab === 'published' && h.status === 'open'"
            class="nh-btn nh-btn-ghost" @click="doCancel(h)">取消退回</button>
          <button v-if="tab === 'accepted' && h.status === 'accepted' && h.acceptor_phone === myPhone"
            class="nh-btn nh-btn-primary" @click="doComplete(h)">标记完成</button>
          <button v-if="tab === 'published' && h.status === 'completed'"
            class="nh-btn nh-btn-primary" @click="doConfirm(h)">确认完成</button>
          <span v-if="h.status === 'confirmed'" class="nh-done">✓ 已完成结算</span>
          <span v-if="h.status === 'cancelled'" class="nh-done">已取消</span>
        </div>
      </div>
    </div>

    <!-- 发布弹窗 -->
    <van-dialog v-model:show="showPublish" title="发个邻里小忙" :show-confirm-button="false" close-on-click-overlay>
      <div class="nh-form">
        <div class="nh-field-label">小忙类型</div>
        <div class="nh-cats">
          <button v-for="c in categories" :key="c" class="nh-cat" :class="{ on: pub.category === c }"
            @click="pub.category = c">{{ c }}</button>
        </div>
        <van-field v-model="pub.title" label="求助标题" maxlength="30" placeholder="如：3 楼搬两个箱子下楼" />
        <van-field v-model="pub.detail" label="详细说明" type="textarea" maxlength="80" placeholder="时间、物品、具体要求…" />
        <van-field v-model="pub.location" label="位置" maxlength="20" placeholder="如：A 区 12 栋 / 3 楼中庭" />
        <van-field v-model="pub.expire_at" label="期望完成" maxlength="20" placeholder="如：今晚 8 点前" />
        <div class="nh-field-label">悬赏积分（预付冻结，{{ minReward }}~{{ maxReward }}）</div>
        <van-stepper v-model="pub.reward" :min="minReward" :max="maxReward" :step="10" integer style="margin:6px 16px 4px;" />
        <div class="nh-balance">当前积分：<b>{{ myPoints }}</b>（接单人完成后再得平台补贴 {{ systemBonus }} 分）</div>
        <div class="nh-form-btns">
          <button class="nh-btn nh-btn-ghost" @click="showPublish = false">取消</button>
          <button class="nh-btn nh-btn-primary" @click="doPublish" :disabled="publishing">{{ publishing ? '发布中…' : '发布悬赏' }}</button>
        </div>
      </div>
    </van-dialog>

    <van-dialog v-model:show="showResult" :title="resultTitle" :show-confirm-button="false" close-on-click-overlay>
      <div class="nh-result">
        <div class="nh-result-icon" :class="{ err: !resultOk }">{{ resultOk ? '✓' : '!' }}</div>
        <p class="nh-result-msg">{{ resultMsg }}</p>
        <button class="nh-btn nh-btn-primary" @click="showResult = false; loadList()">好的</button>
      </div>
    </van-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { showToast } from 'vant'
import { useMemberStore } from '@/stores/member'
import {
  listNeighborHelp, publishNeighborHelp, acceptNeighborHelp,
  completeNeighborHelp, confirmNeighborHelp, cancelNeighborHelp
} from '@/api'

const memberStore = useMemberStore()
const myPhone = computed(() => memberStore.member?.phone || '')
const myPoints = computed(() => memberStore.member?.points || 0)

const tab = ref('wall')
const list = ref([])
const loading = ref(false)

const categories = ['搬家', '代取快递', '临时照看', '问路带路', '其他']
const systemBonus = ref(20)
const minReward = ref(10)
const maxReward = ref(500)

const showPublish = ref(false)
const publishing = ref(false)
const pub = reactive({ category: '代取快递', title: '', detail: '', location: '', expire_at: '', reward: 20 })

const showResult = ref(false)
const resultOk = ref(true)
const resultTitle = ref('提示')
const resultMsg = ref('')

function result(ok, title, msg) {
  resultOk.value = ok
  resultTitle.value = title
  resultMsg.value = msg
  showResult.value = true
}

function statusText(s) {
  return { open: '待抢单', accepted: '进行中', completed: '待确认', confirmed: '已完成', cancelled: '已取消' }[s] || s
}
function statusClass(s) {
  return { open: 'nh-open', accepted: 'nh-accepted', completed: 'nh-completed', confirmed: 'nh-confirmed', cancelled: 'nh-cancelled' }[s] || 'nh-open'
}

async function loadList() {
  loading.value = true
  try {
    const r = await listNeighborHelp(tab.value, myPhone.value)
    if (r.ok) {
      list.value = r.data || []
      const cfg = (r.data && r.data[0]) || {}
      // 后端可在列表里带配置，这里用默认值兜底
    } else {
      list.value = []
    }
  } catch {
    list.value = []
  } finally {
    loading.value = false
  }
}

function openPublish() {
  if (!myPhone.value) { showToast('请先在会员中心登录'); return }
  pub.category = '代取快递'; pub.title = ''; pub.detail = ''; pub.location = ''; pub.expire_at = ''; pub.reward = 20
  showPublish.value = true
}

async function doPublish() {
  if (!pub.title.trim()) { showToast('请填求助标题'); return }
  publishing.value = true
  try {
    const r = await publishNeighborHelp({
      phone: myPhone.value, title: pub.title.trim(), category: pub.category,
      reward: pub.reward, detail: pub.detail.trim(), location: pub.location.trim(), expire_at: pub.expire_at.trim()
    })
    if (r.ok) {
      result(true, '发布成功', `已发布，预付 ${pub.reward} 积分已冻结`)
      showPublish.value = false
      tab.value = 'wall'
      await loadList()
      // 同步刷新本地积分展示
      if (memberStore.member) memberStore.member.points = (memberStore.member.points || 0) - pub.reward
    } else {
      result(false, '发布失败', r.error || '请稍后重试')
    }
  } finally {
    publishing.value = false
  }
}

async function doAccept(h) {
  const r = await acceptNeighborHelp(myPhone.value, h.help_no)
  if (r.ok) { result(true, '接单成功', '请尽快联系邻居完成小忙'); await loadList() }
  else result(false, '操作失败', r.error || '')
}
async function doComplete(h) {
  const r = await completeNeighborHelp(myPhone.value, h.help_no)
  if (r.ok) { result(true, '已标记完成', '等待发单人确认'); await loadList() }
  else result(false, '操作失败', r.error || '')
}
async function doConfirm(h) {
  const r = await confirmNeighborHelp(myPhone.value, h.help_no)
  if (r.ok) { result(true, '已确认', r.message || '已完成结算'); await loadList() }
  else result(false, '操作失败', r.error || '')
}
async function doCancel(h) {
  const r = await cancelNeighborHelp(myPhone.value, h.help_no)
  if (r.ok) { result(true, '已取消', r.message || '已退回预付积分'); await loadList() }
  else result(false, '操作失败', r.error || '')
}

onMounted(async () => {
  await memberStore.restore()
  await loadList()
})
</script>

<style scoped>
.nh-page { padding-bottom: 40px; background: #000; min-height: 100vh; }
.nh-hero {
  position: relative; overflow: hidden; margin: 12px 12px 0; border-radius: 16px;
  padding: 20px 18px; cursor: pointer;
  background: linear-gradient(135deg, #C4923A, #A8741C);
  border: 3px solid #8A5E12;
  box-shadow: 0 6px 18px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.22);
}
.nh-hero-bg { position: absolute; inset: 0; background: radial-gradient(120% 80% at 90% 10%, rgba(255,255,255,.18), rgba(255,255,255,0) 60%); }
.nh-hero-icon {
  width: 54px; height: 54px; border-radius: 14px; display: flex; align-items: center; justify-content: center;
  background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.3);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.3);
}
.nh-hero-text { margin-top: 12px; }
.nh-hero-title { font-size: 19px; font-weight: 700; color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,.35); }
.nh-hero-desc { margin-top: 4px; font-size: 12.5px; color: rgba(255,255,255,.92); text-shadow: 0 1px 1px rgba(0,0,0,.3); line-height: 1.5; }
.nh-hero-btn {
  position: absolute; right: 16px; top: 16px; padding: 6px 14px; border-radius: 999px;
  background: #9A7425; color: #fff; font-weight: 700; font-size: 13px;
  border: 1px solid #8A5E12;
  box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(196,146,58,.45);
}
.nh-rule {
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
  margin: 10px 16px 4px; font-size: 11.5px; color: #9a9a9a;
}
.nh-rule-dot { color: #666; }
.nh-list { padding: 8px 12px 0; }
.nh-empty { text-align: center; color: #666; padding: 60px 0; }
.nh-empty p { margin-top: 10px; font-size: 13px; }

.nh-card {
  border-radius: 14px; padding: 14px; margin-bottom: 12px;
  border: 3px solid transparent;
  box-shadow: 0 4px 14px rgba(0,0,0,.4), inset 0 1px 0 rgba(255,255,255,.18);
}
.nh-open { background: linear-gradient(135deg, #C4923A, #B07E22); border-color: #8A5E12; }
.nh-accepted { background: linear-gradient(135deg, #C9956C, #B07E4E); border-color: #A87C48; }
.nh-completed { background: linear-gradient(135deg, #8B8B90, #6F6F76); border-color: #54545A; }
.nh-confirmed { background: linear-gradient(135deg, #6B6E64, #505247); border-color: #3C3E36; }
.nh-cancelled { background: linear-gradient(135deg, #3A3A3E, #2A2A2E); border-color: #1E1E22; opacity: .8; }

.nh-card-top { display: flex; justify-content: space-between; align-items: center; }
.nh-tag {
  font-size: 12px; font-weight: 700; color: #fff; background: rgba(0,0,0,.22);
  padding: 2px 10px; border-radius: 999px; text-shadow: 0 1px 1px rgba(0,0,0,.3);
}
.nh-status { font-size: 12px; color: #fff; font-weight: 600; text-shadow: 0 1px 1px rgba(0,0,0,.3); opacity: .95; }
.nh-title { margin-top: 10px; font-size: 16px; font-weight: 700; color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,.35); line-height: 1.4; }
.nh-detail { margin-top: 6px; font-size: 13px; color: rgba(255,255,255,.9); line-height: 1.5; }
.nh-meta { margin-top: 8px; display: flex; gap: 14px; flex-wrap: wrap; font-size: 12px; color: rgba(255,255,255,.82); }
.nh-card-foot { margin-top: 12px; display: flex; align-items: flex-end; justify-content: space-between; }
.nh-reward { display: flex; align-items: baseline; gap: 5px; }
.nh-reward-num { font-size: 22px; font-weight: 800; color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,.4); }
.nh-reward-unit { font-size: 12px; color: rgba(255,255,255,.9); }
.nh-bonus { margin-left: 8px; font-size: 11px; font-weight: 700; color: #FFF3D6; background: rgba(0,0,0,.25); padding: 2px 8px; border-radius: 999px; }
.nh-who { font-size: 11.5px; color: rgba(255,255,255,.8); }

.nh-actions { margin-top: 12px; display: flex; gap: 10px; align-items: center; }
.nh-btn {
  border: none; border-radius: 999px; padding: 8px 18px; font-size: 13.5px; font-weight: 700; cursor: pointer;
  box-shadow: 0 2px 6px rgba(0,0,0,.3);
}
.nh-btn-primary { background: #9A7425; color: #fff; border: 1px solid #8A5E12; box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(196,146,58,.45); }
.nh-btn-ghost { background: rgba(0,0,0,.30); color: #fff; border: 1px solid rgba(255,255,255,.4); box-shadow: inset 3px 3px 7px rgba(0,0,0,.5), inset -2px -2px 5px rgba(255,255,255,.08); }
.nh-btn:disabled { opacity: .6; }
.nh-done { font-size: 12.5px; color: rgba(255,255,255,.85); font-weight: 600; }

/* van-tabs 顶栏：去除白条，融进黑底 */
.nh-page :deep(.van-tabs__wrap) { background: #000; }
.nh-page :deep(.van-tabs__nav) { background: #000; }
.nh-page :deep(.van-tab) { color: #999; background: #000; }
.nh-page :deep(.van-tab--active) { color: #C4923A; font-weight: 700; }
.nh-page :deep(.van-tabs__line) { background: #C4923A; }
.nh-page :deep(.van-hairline--top-bottom::after) { border-color: #333; }

.nh-form { padding: 8px 0 16px; }
.nh-field-label { font-size: 12.5px; color: #bbb; margin: 10px 16px 4px; }
.nh-cats { display: flex; flex-wrap: wrap; gap: 8px; padding: 4px 16px; }
.nh-cat {
  border: 1px solid #444; background: #1A1A1A; color: #ccc; border-radius: 999px;
  padding: 5px 14px; font-size: 13px; cursor: pointer;
}
.nh-cat.on { background: #C4923A; color: #fff; border-color: #8A5E12; font-weight: 700; }
.nh-balance { font-size: 12px; color: #999; margin: 8px 16px; }
.nh-balance b { color: #FFB877; }
.nh-form-btns { display: flex; gap: 12px; padding: 8px 16px 0; }
.nh-form-btns .nh-btn { flex: 1; }

.nh-result { padding: 20px 18px 22px; text-align: center; }
.nh-result-icon {
  width: 48px; height: 48px; border-radius: 50%; margin: 0 auto 12px; display: flex; align-items: center; justify-content: center;
  font-size: 26px; font-weight: 800; color: #fff; background: #6B6E64;
}
.nh-result-icon.err { background: #C0392B; }
.nh-result-msg { font-size: 14px; color: #ddd; line-height: 1.6; margin-bottom: 16px; }
</style>
