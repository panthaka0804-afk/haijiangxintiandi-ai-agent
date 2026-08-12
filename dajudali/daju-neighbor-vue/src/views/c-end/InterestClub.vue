<template>
  <div class="ic-root">
    <!-- 头部 -->
    <header class="ic-hdr">
      <button class="ic-back" @click="$router.back()">‹</button>
      <h1>兴趣社</h1>
      <span class="ic-hdr-sub">活动驱动 · 散是满天星</span>
    </header>

    <!-- Tab -->
    <nav class="ic-tabs">
      <button :class="['ic-tab', { active: tab === 'clubs' }]" @click="switchTab('clubs')">兴趣社</button>
      <button :class="['ic-tab', { active: tab === 'events' }]" @click="switchTab('events')">活动群</button>
      <button :class="['ic-tab', { active: tab === 'mine' }]" @click="switchTab('mine')">我的</button>
    </nav>

    <!-- 兴趣社 -->
    <section v-if="tab === 'clubs'" class="ic-sec">
      <div class="ic-sec-title">选标签 · 自动入社</div>
      <div v-if="clubsLoading" class="ic-loading">加载中…</div>
      <div v-else-if="!clubs.length" class="ic-empty">暂无兴趣社</div>
      <div v-for="c in clubs" :key="c.id" class="ic-club-card" :style="{ background: c.gradient }">
        <div class="ic-club-emoji">{{ c.cover_emoji }}</div>
        <div class="ic-club-main">
          <div class="ic-club-top">
            <span class="ic-club-name">{{ c.name }}</span>
            <span class="ic-club-tag">#{{ c.tag }}</span>
          </div>
          <div class="ic-club-intro">{{ c.intro }}</div>
          <div class="ic-club-meta">{{ c.member_count }} 位邻居在社 · 点击查看活动群</div>
        </div>
        <button class="ic-club-btn" :class="{ joined: c.joined }" @click="toggleClub(c)">
          {{ c.joined ? '已加入' : '加入' }}
        </button>
      </div>
      <div class="ic-tip">加入兴趣社后，社内发起的活动会优先推给你。活动群按场开、活动结束自动散，不打扰。</div>
    </section>

    <!-- 活动群 -->
    <section v-if="tab === 'events'" class="ic-sec">
      <div class="ic-sec-title">活动驱动的临时群</div>
      <!-- 社筛选 -->
      <div class="ic-filter">
        <button :class="['ic-chip', { active: filterClub === 0 }]" @click="filterByClub(0)">全部</button>
        <button v-for="c in clubs" :key="c.id" :class="['ic-chip', { active: filterClub === c.id }]" @click="filterByClub(c.id)">
          {{ c.cover_emoji }} {{ c.name }}
        </button>
      </div>
      <div v-if="eventsLoading" class="ic-loading">加载中…</div>
      <div v-else-if="!events.length" class="ic-empty">该分类暂无进行中的活动群</div>
      <div v-for="e in events" :key="e.id" class="ic-ev-card" @click="openEvent(e)">
        <div class="ic-ev-emoji" :style="{ background: e.gradient }">{{ e.cover_emoji }}</div>
        <div class="ic-ev-main">
          <div class="ic-ev-top">
            <span class="ic-ev-club">{{ e.club_name }}</span>
            <span class="ic-ev-tag">#{{ e.tag }}</span>
          </div>
          <div class="ic-ev-title">{{ e.title }}</div>
          <div class="ic-ev-info">🕒 {{ e.meet_time }}　📍 {{ e.place }}</div>
          <div class="ic-ev-progress">
            <div class="ic-ev-bar"><div class="ic-ev-fill" :style="{ width: evPct(e) + '%' }"></div></div>
            <span class="ic-ev-txt">已报名 {{ e.joined_count }}/{{ e.need_count }} 人</span>
          </div>
        </div>
        <span v-if="e.joined" class="ic-ev-badge">已入群</span>
      </div>
    </section>

    <!-- 我的 -->
    <section v-if="tab === 'mine'" class="ic-sec">
      <div class="ic-sec-title">我的兴趣社</div>
      <div v-if="!myClubs.length" class="ic-empty">还没加入任何兴趣社，去「兴趣社」选标签加入吧~</div>
      <div v-for="c in myClubs" :key="c.id" class="ic-my-club">
        <span class="ic-my-emoji">{{ c.cover_emoji }}</span>
        <div class="ic-my-info">
          <div class="ic-my-name">{{ c.name }} <span class="ic-my-tag">#{{ c.tag }}</span></div>
          <div class="ic-my-intro">{{ c.intro }}</div>
        </div>
      </div>

      <div class="ic-sec-title">我的活动群</div>
      <div v-if="!myEvents.length" class="ic-empty">还没有参与任何活动群</div>
      <div v-for="e in myEvents" :key="e.id" class="ic-my-ev" @click="openEventById(e.id)">
        <div class="ic-my-ev-title">{{ e.title }}</div>
        <div class="ic-my-ev-meta">🕒 {{ e.meet_time }}　📍 {{ e.place }}</div>
        <span class="ic-my-ev-status" :class="e.status">{{ e.status === 'open' ? '进行中' : '已结束' }}</span>
      </div>
    </section>

    <!-- 活动群详情弹层 -->
    <transition name="ic-slide">
      <div v-if="detail" class="ic-mask" @click.self="closeDetail">
        <div class="ic-sheet">
          <div class="ic-sheet-hd">
            <div class="ic-sheet-emoji" :style="{ background: detail.gradient }">{{ detail.cover_emoji }}</div>
            <div class="ic-sheet-hd-main">
              <div class="ic-sheet-club">{{ detail.club_name }} · #{{ detail.tag }}</div>
              <div class="ic-sheet-title">{{ detail.title }}</div>
            </div>
            <button class="ic-sheet-close" @click="closeDetail">×</button>
          </div>
          <div class="ic-sheet-body">
            <div class="ic-sheet-row"><span>时间</span><b>{{ detail.meet_time }} 集合</b></div>
            <div class="ic-sheet-row"><span>地点</span><b>{{ detail.place }}</b></div>
            <div class="ic-sheet-row"><span>详情</span><b>{{ detail.detail || '—' }}</b></div>
            <div class="ic-sheet-row"><span>进度</span><b>已报名 {{ detail.joined_count }}/{{ detail.need_count }} 人（还差 {{ detail.remain }}）</b></div>

            <div class="ic-sheet-sub">👥 群成员（{{ detail.joined_count }}）</div>
            <div class="ic-members">
              <span v-for="(m, i) in detail.members" :key="i" class="ic-member">{{ m.name }}</span>
              <span v-if="!detail.members.length" class="ic-member ghost">虚位以待</span>
            </div>

            <div class="ic-sheet-sub">💬 留言接龙（{{ detail.messages.length }}）</div>
            <div class="ic-msgs">
              <div v-for="(x, i) in detail.messages" :key="i" class="ic-msg">
                <span class="ic-msg-name">{{ x.name }}</span>
                <span class="ic-msg-content">{{ x.content }}</span>
                <span class="ic-msg-time">{{ x.time }}</span>
              </div>
              <div v-if="!detail.messages.length" class="ic-msg ghost">还没有留言，来占个楼~</div>
            </div>
          </div>

          <!-- 底部操作 -->
          <div class="ic-sheet-ft">
            <template v-if="!detail.joined_by_me">
              <button class="ic-join-btn" @click="joinEvent(detail)">加入活动群（{{ detail.remain }} 个名额）</button>
            </template>
            <template v-else>
              <input v-model="msgText" class="ic-msg-input" placeholder="留言接龙，约起~" maxlength="120" @keyup.enter="sendMsg(detail)" />
              <button class="ic-send-btn" @click="sendMsg(detail)">发送</button>
            </template>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useMemberStore } from '@/stores/member'
import { showToast } from 'vant'
import {
  getInterestClubs, joinInterestClub, getClubEvents, getClubEventDetail,
  joinClubEvent, sendClubEventMessage, getMyClubs
} from '@/api'

const memberStore = useMemberStore()
const phone = ref('')
const tab = ref('clubs')
const clubs = ref([])
const clubsLoading = ref(true)
const events = ref([])
const eventsLoading = ref(false)
const filterClub = ref(0)
const myClubs = ref([])
const myEvents = ref([])
const detail = ref(null)
const msgText = ref('')

// 从持久化登录态恢复手机号；并监听会员登录态变化（登录/绑定后自动刷新）
memberStore.restore()
function syncPhone() {
  const m = memberStore.member
  if (m && m.phone) phone.value = m.phone
}
syncPhone()
watch(() => memberStore.member, syncPhone)

onMounted(async () => {
  await loadClubs()
  if (phone.value) await loadMine()
})

function switchTab(t) {
  tab.value = t
  if (t === 'clubs') loadClubs()
  else if (t === 'events') { filterClub.value = 0; loadEvents() }
  else if (t === 'mine' && phone.value) loadMine()
}

async function loadClubs() {
  clubsLoading.value = true
  try {
    const res = await getInterestClubs(phone.value)
    if (res.ok) clubs.value = res.data || []
  } catch (e) {}
  clubsLoading.value = false
}

async function loadEvents() {
  eventsLoading.value = true
  const params = {}
  if (filterClub.value) params.club_id = filterClub.value
  if (phone.value) params.phone = phone.value
  try {
    const res = await getClubEvents(params)
    if (res.ok) events.value = res.data || []
  } catch (e) {}
  eventsLoading.value = false
}

async function loadMine() {
  try {
    const res = await getMyClubs(phone.value)
    if (res.ok) {
      myClubs.value = res.data.clubs || []
      myEvents.value = res.data.events || []
    }
  } catch (e) {}
}

function filterByClub(id) {
  filterClub.value = id
  loadEvents()
}

function evPct(e) {
  if (!e.need_count) return 0
  return Math.min(100, Math.round((e.joined_count / e.need_count) * 100))
}

async function toggleClub(c) {
  if (!phone.value) { showToast('请先在会员中心绑定手机号'); return }
  try {
    const res = await joinInterestClub(c.id, phone.value, memberStore.member?.display_name || '', !c.joined)
    if (res.ok) {
      c.joined = res.data.joined
      c.member_count += res.data.joined ? 1 : -1
      showToast(res.data.joined ? '已加入 ' + c.name : '已退出')
    } else {
      showToast(res.error || '操作失败')
    }
  } catch (e) { showToast('网络异常') }
}

async function openEvent(e) {
  await openEventById(e.id)
}
async function openEventById(id) {
  try {
    const res = await getClubEventDetail(id, phone.value)
    if (res.ok) detail.value = res.data
    else showToast(res.error || '活动群不存在')
  } catch (e) { showToast('网络异常') }
}
function closeDetail() { detail.value = null }

async function joinEvent(d) {
  if (!phone.value) { showToast('请先在会员中心绑定手机号'); return }
  try {
    const res = await joinClubEvent(d.id, phone.value, memberStore.member?.display_name || '')
    if (res.ok) {
      showToast('入群成功！活动当天来集合点签到')
      await openEventById(d.id)
      await loadEvents()
      if (tab.value === 'mine') await loadMine()
    } else {
      showToast(res.error || '入群失败')
    }
  } catch (e) { showToast('网络异常') }
}

async function sendMsg(d) {
  const text = msgText.value.trim()
  if (!text) return
  if (!phone.value) { showToast('请先绑定手机号'); return }
  try {
    const res = await sendClubEventMessage(d.id, phone.value, memberStore.member?.display_name || '', text)
    if (res.ok) {
      msgText.value = ''
      await openEventById(d.id)
    } else {
      showToast(res.error || '发送失败')
    }
  } catch (e) { showToast('网络异常') }
}
</script>

<style scoped>
.ic-root { min-height: 100vh; background: #000; color: #fff; padding-bottom: 30px; font-family: 'PingFang SC', var(--font-primary); }
.ic-hdr { display: flex; align-items: center; gap: 12px; padding: 14px 16px; background: #0A0A0C; border-bottom: 1px solid rgba(255,255,255,0.08); position: sticky; top: 0; z-index: 10; }
.ic-back { width: 32px; height: 32px; border: none; background: rgba(255,255,255,0.08); color: #fff; font-size: 22px; border-radius: 50%; cursor: pointer; line-height: 1; }
.ic-hdr h1 { font-size: 18px; font-weight: 800; margin: 0; flex: 1; }
.ic-hdr-sub { font-size: 12px; color: rgba(255,255,255,0.5); }

.ic-tabs { display: flex; gap: 8px; padding: 12px 16px; position: sticky; top: 61px; background: #000; z-index: 9; }
.ic-tab { flex: 1; height: 38px; border: 1px solid rgba(255,255,255,0.12); background: #161618; color: rgba(255,255,255,0.6); font-size: 14px; font-weight: 700; border-radius: 10px; cursor: pointer; }
.ic-tab.active { background: linear-gradient(135deg,#E85D04,#FF7B2C); color: #fff; border-color: transparent; }

.ic-sec { padding: 0 16px; }
.ic-sec-title { font-size: 14px; font-weight: 700; color: #fff; margin: 16px 0 10px; letter-spacing: 0.5px; }

.ic-club-card { display: flex; align-items: center; gap: 12px; border-radius: 16px; padding: 14px; margin-bottom: 12px; box-shadow: 0 4px 14px rgba(0,0,0,0.35); }
.ic-club-emoji { width: 46px; height: 46px; border-radius: 12px; background: rgba(255,255,255,0.22); display: flex; align-items: center; justify-content: center; font-size: 26px; flex-shrink: 0; }
.ic-club-main { flex: 1; min-width: 0; }
.ic-club-top { display: flex; align-items: center; gap: 8px; }
.ic-club-name { font-size: 15px; font-weight: 800; color: #fff; }
.ic-club-tag { font-size: 11px; color: rgba(255,255,255,0.85); background: rgba(0,0,0,0.22); padding: 2px 8px; border-radius: 10px; }
.ic-club-intro { font-size: 12px; color: rgba(255,255,255,0.82); margin: 4px 0; line-height: 1.5; }
.ic-club-meta { font-size: 11px; color: rgba(255,255,255,0.7); }
.ic-club-btn { flex-shrink: 0; height: 34px; padding: 0 16px; border: 1px solid rgba(255,255,255,0.7); background: rgba(255,255,255,0.16); color: #fff; font-size: 13px; font-weight: 700; border-radius: 18px; cursor: pointer; }
.ic-club-btn.joined { background: rgba(0,0,0,0.25); border-color: rgba(255,255,255,0.4); }

.ic-filter { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 4px; margin-bottom: 10px; }
.ic-chip { flex-shrink: 0; height: 32px; padding: 0 14px; border: 1px solid rgba(255,255,255,0.12); background: #161618; color: rgba(255,255,255,0.6); font-size: 13px; border-radius: 16px; cursor: pointer; white-space: nowrap; }
.ic-chip.active { background: rgba(255,123,44,0.18); color: #FF7B2C; border-color: rgba(255,123,44,0.5); }

.ic-ev-card { display: flex; align-items: center; gap: 12px; background: #161618; border: 1px solid rgba(255,255,255,0.10); border-radius: 14px; padding: 12px; margin-bottom: 12px; cursor: pointer; position: relative; }
.ic-ev-emoji { width: 44px; height: 44px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 24px; flex-shrink: 0; }
.ic-ev-main { flex: 1; min-width: 0; }
.ic-ev-top { display: flex; align-items: center; gap: 8px; }
.ic-ev-club { font-size: 12px; color: #FF7B2C; font-weight: 700; }
.ic-ev-tag { font-size: 11px; color: rgba(255,255,255,0.5); }
.ic-ev-title { font-size: 15px; font-weight: 700; margin: 3px 0; }
.ic-ev-info { font-size: 12px; color: rgba(255,255,255,0.6); margin-bottom: 6px; }
.ic-ev-progress { display: flex; align-items: center; gap: 8px; }
.ic-ev-bar { flex: 1; height: 6px; background: rgba(255,255,255,0.10); border-radius: 3px; overflow: hidden; }
.ic-ev-fill { height: 100%; background: linear-gradient(90deg,#E85D04,#FF7B2C); border-radius: 3px; }
.ic-ev-txt { font-size: 11px; color: rgba(255,255,255,0.6); white-space: nowrap; }
.ic-ev-badge { position: absolute; top: 10px; right: 10px; font-size: 11px; font-weight: 700; color: #FF7B2C; background: rgba(255,123,44,0.16); padding: 2px 8px; border-radius: 10px; }

.ic-my-club { display: flex; align-items: center; gap: 12px; background: #161618; border: 1px solid rgba(255,255,255,0.10); border-radius: 12px; padding: 12px; margin-bottom: 10px; }
.ic-my-emoji { font-size: 28px; flex-shrink: 0; }
.ic-my-name { font-size: 14px; font-weight: 700; }
.ic-my-tag { font-size: 11px; color: #FF7B2C; }
.ic-my-intro { font-size: 12px; color: rgba(255,255,255,0.6); margin-top: 2px; }
.ic-my-ev { display: flex; align-items: center; justify-content: space-between; background: #161618; border: 1px solid rgba(255,255,255,0.10); border-radius: 12px; padding: 12px; margin-bottom: 10px; cursor: pointer; }
.ic-my-ev-title { font-size: 14px; font-weight: 700; }
.ic-my-ev-meta { font-size: 12px; color: rgba(255,255,255,0.6); margin-top: 3px; }
.ic-my-ev-status { font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 10px; }
.ic-my-ev-status.open { background: rgba(255,123,44,0.16); color: #FF7B2C; }
.ic-my-ev-status.closed { background: rgba(255,255,255,0.10); color: rgba(255,255,255,0.5); }

.ic-tip { font-size: 12px; color: rgba(255,255,255,0.45); margin: 16px; line-height: 1.6; text-align: center; }
.ic-loading, .ic-empty { text-align: center; color: rgba(255,255,255,0.5); padding: 30px 0; font-size: 14px; }

/* 弹层 */
.ic-mask { position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 50; display: flex; align-items: flex-end; }
.ic-sheet { width: 100%; max-height: 86vh; background: #161618; border-radius: 20px 20px 0 0; display: flex; flex-direction: column; overflow: hidden; }
.ic-sheet-hd { display: flex; align-items: center; gap: 12px; padding: 16px; border-bottom: 1px solid rgba(255,255,255,0.08); }
.ic-sheet-emoji { width: 46px; height: 46px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 26px; flex-shrink: 0; }
.ic-sheet-hd-main { flex: 1; min-width: 0; }
.ic-sheet-club { font-size: 12px; color: #FF7B2C; font-weight: 700; }
.ic-sheet-title { font-size: 16px; font-weight: 800; margin-top: 2px; }
.ic-sheet-close { width: 30px; height: 30px; border: none; background: rgba(255,255,255,0.08); color: #fff; font-size: 20px; border-radius: 50%; cursor: pointer; flex-shrink: 0; }
.ic-sheet-body { flex: 1; overflow-y: auto; padding: 16px; }
.ic-sheet-row { display: flex; gap: 12px; font-size: 13px; padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.05); }
.ic-sheet-row span { color: rgba(255,255,255,0.5); width: 40px; flex-shrink: 0; }
.ic-sheet-row b { color: #fff; font-weight: 600; }
.ic-sheet-sub { font-size: 13px; font-weight: 700; color: #fff; margin: 16px 0 8px; }
.ic-members { display: flex; flex-wrap: wrap; gap: 8px; }
.ic-member { font-size: 12px; color: #fff; background: linear-gradient(135deg,#E85D04,#FF7B2C); padding: 4px 12px; border-radius: 14px; }
.ic-member.ghost { background: rgba(255,255,255,0.10); color: rgba(255,255,255,0.5); }
.ic-msgs { display: flex; flex-direction: column; gap: 8px; }
.ic-msg { background: #0F0F11; border-radius: 10px; padding: 8px 12px; font-size: 13px; }
.ic-msg.ghost { color: rgba(255,255,255,0.4); text-align: center; }
.ic-msg-name { color: #FF7B2C; font-weight: 700; margin-right: 8px; }
.ic-msg-content { color: #fff; }
.ic-msg-time { color: rgba(255,255,255,0.4); font-size: 11px; margin-left: 8px; }
.ic-sheet-ft { padding: 12px 16px; border-top: 1px solid rgba(255,255,255,0.08); display: flex; gap: 10px; background: #161618; }
.ic-join-btn { flex: 1; height: 46px; border: none; border-radius: 12px; background: linear-gradient(135deg,#E85D04,#FF7B2C); color: #fff; font-size: 14px; font-weight: 700; cursor: pointer; box-shadow: 0 4px 12px rgba(232,93,4,0.35); }
.ic-msg-input { flex: 1; height: 44px; border: 1px solid rgba(255,255,255,0.15); background: #0F0F11; color: #fff; border-radius: 12px; padding: 0 14px; font-size: 14px; }
.ic-send-btn { height: 44px; padding: 0 18px; border: none; border-radius: 12px; background: linear-gradient(135deg,#E85D04,#FF7B2C); color: #fff; font-size: 14px; font-weight: 700; cursor: pointer; }

.ic-slide-enter-active, .ic-slide-leave-active { transition: opacity 0.25s; }
.ic-slide-enter-from, .ic-slide-leave-to { opacity: 0; }
</style>
