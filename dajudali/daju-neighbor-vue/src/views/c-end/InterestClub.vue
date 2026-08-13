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
      <div v-for="(c, i) in clubs" :key="c.id" class="ic-club-card" :class="'ic-c-' + (i % 5)">
        <div class="ic-club-avatar">{{ initial(c.name) }}</div>
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
          {{ c.name }}
        </button>
      </div>
      <div v-if="eventsLoading" class="ic-loading">加载中…</div>
      <div v-else-if="!events.length" class="ic-empty">该分类暂无进行中的活动群</div>
      <div v-for="(e, i) in events" :key="e.id" class="ic-ev-card" :class="'ic-c-' + (i % 5)" @click="openEvent(e, i)">
        <div class="ic-ev-avatar">{{ initial(e.club_name) }}</div>
        <div class="ic-ev-main">
          <div class="ic-ev-top">
            <span class="ic-ev-club">{{ e.club_name }}</span>
            <span class="ic-ev-tag">#{{ e.tag }}</span>
          </div>
          <div class="ic-ev-title">{{ e.title }}</div>
          <div class="ic-ev-info"><span class="ic-ev-k">时间</span> {{ e.meet_time }}　<span class="ic-ev-k">地点</span> {{ e.place }}</div>
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
      <div v-for="(c, i) in myClubs" :key="c.id" class="ic-my-club" :class="'ic-c-' + (i % 5)">
        <span class="ic-my-avatar">{{ initial(c.name) }}</span>
        <div class="ic-my-info">
          <div class="ic-my-name">{{ c.name }} <span class="ic-my-tag">#{{ c.tag }}</span></div>
          <div class="ic-my-intro">{{ c.intro }}</div>
        </div>
      </div>

      <div class="ic-sec-title">我的活动群</div>
      <div v-if="!myEvents.length" class="ic-empty">还没有参与任何活动群</div>
      <div v-for="e in myEvents" :key="e.id" class="ic-my-ev" @click="openEventById(e.id)">
        <div class="ic-my-ev-title">{{ e.title }}</div>
        <div class="ic-my-ev-meta"><span class="ic-ev-k">时间</span> {{ e.meet_time }}　<span class="ic-ev-k">地点</span> {{ e.place }}</div>
        <span class="ic-my-ev-status" :class="e.status">{{ e.status === 'open' ? '进行中' : '已结束' }}</span>
      </div>
    </section>

    <!-- 活动群详情弹层 -->
    <transition name="ic-slide">
      <div v-if="detail" class="ic-mask" @click.self="closeDetail">
        <div class="ic-sheet">
          <div class="ic-sheet-hd">
            <div class="ic-sheet-avatar">{{ initial(detail.club_name) }}</div>
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

            <div class="ic-sheet-sub">群成员（{{ detail.joined_count }}）</div>
            <div class="ic-members">
              <span v-for="(m, i) in detail.members" :key="i" class="ic-member">{{ m.name }}</span>
              <span v-if="!detail.members.length" class="ic-member ghost">虚位以待</span>
            </div>

            <div class="ic-sheet-sub">留言接龙（{{ detail.messages.length }}）</div>
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
          <div class="ic-sheet-ft" :class="'ic-c-' + (detail.colorIdx || 0)">
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

function initial(name) {
  if (!name) return '·'
  const ch = String(name).trim().charAt(0)
  return ch ? ch.toUpperCase() : '·'
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

async function openEvent(e, i = 0) {
  await openEventById(e.id, i)
}
async function openEventById(id, colorIdx = 0) {
  try {
    const res = await getClubEventDetail(id, phone.value)
    if (res.ok) { detail.value = res.data; detail.value.colorIdx = colorIdx }
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
.ic-tab.active { background: #9A7425; color: #fff; border-color: #8A5E12; box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(196,146,58,.45); }

/* 多彩卡片：实色渐变底 + 3px 深边框 + 内高光 + 白字（与首页一致：金黄/浅橙棕/深红棕/灰紫/深灰绿） */
.ic-c-0 { background: linear-gradient(135deg, #C4923A, #A8741C); border-color: #8A5E12; }
.ic-c-1 { background: linear-gradient(135deg, #C9956C, #B07E4E); border-color: #A87C48; }
.ic-c-2 { background: linear-gradient(135deg, #9B4A3E, #7E3328); border-color: #5C241D; }
.ic-c-3 { background: linear-gradient(135deg, #8B8B90, #6F6F76); border-color: #54545A; }
.ic-c-4 { background: linear-gradient(135deg, #6B6E64, #505247); border-color: #3C3E36; }

.ic-sec { padding: 0 16px; }
.ic-sec-title { font-size: 14px; font-weight: 700; color: #fff; margin: 16px 0 10px; letter-spacing: 0.5px; }

.ic-club-card, .ic-ev-card, .ic-my-club, .ic-my-ev {
  border: 3px solid transparent; border-radius: 16px; padding: 14px; margin-bottom: 12px;
  box-shadow: 0 6px 16px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.22);
}
.ic-my-ev { display: flex; align-items: center; justify-content: space-between; }
.ic-club-card, .ic-ev-card { display: flex; align-items: center; gap: 12px; }
.ic-club-avatar, .ic-ev-avatar, .ic-my-avatar, .ic-sheet-avatar {
  width: 46px; height: 46px; border-radius: 12px; display: flex; align-items: center; justify-content: center;
  font-size: 20px; font-weight: 800; color: #fff; flex-shrink: 0; background: rgba(0,0,0,0.28); text-shadow: 0 1px 1px rgba(0,0,0,.4);
}
.ic-club-main { flex: 1; min-width: 0; }
.ic-club-top { display: flex; align-items: center; gap: 8px; }
.ic-club-name { font-size: 15px; font-weight: 800; color: #fff; text-shadow: 0 1px 1px rgba(0,0,0,.35); }
.ic-club-tag { font-size: 11px; color: #fff; background: rgba(0,0,0,0.22); padding: 2px 8px; border-radius: 10px; }
.ic-club-intro { font-size: 12px; color: rgba(255,255,255,0.85); margin: 4px 0; line-height: 1.5; }
.ic-club-meta { font-size: 11px; color: rgba(255,255,255,0.75); }
.ic-club-btn { flex-shrink: 0; padding: 8px 20px; background-color: #9A7425; border: 3px solid #9A7425; border-radius: 20px; box-shadow: inset 3px 3px 7px rgba(0,0,0,0.45), inset -2px -2px 5px rgba(196,146,58,0.45); color: #FFFFFF; font-size: var(--fs-aux); font-weight: 600; white-space: nowrap; cursor: pointer; filter: drop-shadow(0 0.6px 1px rgba(0,0,0,0.4)); }
.ic-club-btn:active { box-shadow: inset 5px 5px 10px rgba(0,0,0,.55), inset -2px -2px 5px rgba(196,146,58,.35); }
.ic-club-btn.joined { background-color: rgba(0,0,0,0.35); border: 3px solid rgba(255,255,255,0.30); color: rgba(255,255,255,0.85); box-shadow: inset 3px 3px 7px rgba(0,0,0,.5), inset -2px -2px 5px rgba(255,255,255,.08); filter: none; }
/* 加入按钮跟随卡片五色（与拼团一致） */
.ic-c-0 .ic-club-btn { background-color: #8A5E12; border-color: #6E4A0E; box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(196,146,58,.45); }
.ic-c-1 .ic-club-btn { background-color: #A87C48; border-color: #87613A; box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(201,149,108,.45); }
.ic-c-2 .ic-club-btn { background-color: #5C241D; border-color: #451B16; box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(155,74,62,.45); }
.ic-c-3 .ic-club-btn { background-color: #54545A; border-color: #3F3F44; box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(139,139,144,.45); }
.ic-c-4 .ic-club-btn { background-color: #3C3E36; border-color: #2C2E28; box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(107,110,100,.45); }
.ic-c-0 .ic-club-btn.joined { background-color: #6E4A0E; }
.ic-c-1 .ic-club-btn.joined { background-color: #87613A; }
.ic-c-2 .ic-club-btn.joined { background-color: #451B16; }
.ic-c-3 .ic-club-btn.joined { background-color: #3F3F44; }
.ic-c-4 .ic-club-btn.joined { background-color: #2C2E28; }

.ic-filter { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 4px; margin-bottom: 10px; }
.ic-chip { flex-shrink: 0; height: 32px; padding: 0 14px; border: 1px solid rgba(255,255,255,0.12); background: #161618; color: rgba(255,255,255,0.6); font-size: 13px; border-radius: 16px; cursor: pointer; white-space: nowrap; }
.ic-chip.active { background: #9A7425; color: #fff; border-color: #8A5E12; box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(196,146,58,.45); }

.ic-ev-main { flex: 1; min-width: 0; }
.ic-ev-top { display: flex; align-items: center; gap: 8px; }
.ic-ev-club { font-size: 12px; color: #fff; font-weight: 700; text-shadow: 0 1px 1px rgba(0,0,0,.35); }
.ic-ev-tag { font-size: 11px; color: rgba(255,255,255,0.75); }
.ic-ev-title { font-size: 15px; font-weight: 700; margin: 3px 0; color: #fff; text-shadow: 0 1px 1px rgba(0,0,0,.35); }
.ic-ev-info { font-size: 12px; color: rgba(255,255,255,0.8); margin-bottom: 6px; }
.ic-ev-k { color: rgba(255,255,255,0.6); margin-right: 2px; }
.ic-ev-progress { display: flex; align-items: center; gap: 8px; }
.ic-ev-bar { flex: 1; height: 6px; background: rgba(0,0,0,0.30); border-radius: 3px; overflow: hidden; }
.ic-ev-fill { height: 100%; background: linear-gradient(90deg, rgba(0,0,0,0.35), rgba(255,255,255,0.55)); border-radius: 3px; }
.ic-ev-txt { font-size: 11px; color: rgba(255,255,255,0.85); white-space: nowrap; text-shadow: 0 1px 1px rgba(0,0,0,.3); }
.ic-ev-badge { position: absolute; top: 10px; right: 10px; font-size: 11px; font-weight: 700; color: #fff; background: rgba(0,0,0,0.30); padding: 2px 8px; border-radius: 10px; }

.ic-my-info { flex: 1; min-width: 0; }
.ic-my-name { font-size: 14px; font-weight: 700; color: #fff; text-shadow: 0 1px 1px rgba(0,0,0,.35); }
.ic-my-tag { font-size: 11px; color: rgba(255,255,255,0.85); }
.ic-my-intro { font-size: 12px; color: rgba(255,255,255,0.75); margin-top: 2px; }
.ic-my-ev-title { font-size: 14px; font-weight: 700; color: #fff; text-shadow: 0 1px 1px rgba(0,0,0,.35); }
.ic-my-ev-meta { font-size: 12px; color: rgba(255,255,255,0.8); margin-top: 3px; }
.ic-my-ev-status { font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 10px; }
.ic-my-ev-status.open { background: rgba(255,255,255,0.25); color: #fff; }
.ic-my-ev-status.closed { background: rgba(0,0,0,0.30); color: rgba(255,255,255,0.7); }

.ic-tip { font-size: 12px; color: rgba(255,255,255,0.5); margin: 16px; line-height: 1.6; text-align: center; }
.ic-loading, .ic-empty { text-align: center; color: rgba(255,255,255,0.5); padding: 30px 0; font-size: 14px; }

/* 弹层 */
.ic-mask { position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 50; display: flex; align-items: flex-end; }
.ic-sheet { width: 100%; max-height: 86vh; background: #161618; border-radius: 20px 20px 0 0; display: flex; flex-direction: column; overflow: hidden; }
.ic-sheet-hd { display: flex; align-items: center; gap: 12px; padding: 16px; border-bottom: 1px solid rgba(255,255,255,0.08); }
.ic-sheet-hd-main { flex: 1; min-width: 0; }
.ic-sheet-club { font-size: 12px; color: #C4923A; font-weight: 700; }
.ic-sheet-title { font-size: 16px; font-weight: 800; margin-top: 2px; color: #fff; }
.ic-sheet-close { width: 30px; height: 30px; border: none; background: rgba(255,255,255,0.08); color: #fff; font-size: 20px; border-radius: 50%; cursor: pointer; flex-shrink: 0; }
.ic-sheet-body { flex: 1; overflow-y: auto; padding: 16px; }
.ic-sheet-row { display: flex; gap: 12px; font-size: 13px; padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.05); }
.ic-sheet-row span { color: rgba(255,255,255,0.5); width: 40px; flex-shrink: 0; }
.ic-sheet-row b { color: #fff; font-weight: 600; }
.ic-sheet-sub { font-size: 13px; font-weight: 700; color: #fff; margin: 16px 0 8px; }
.ic-members { display: flex; flex-wrap: wrap; gap: 8px; }
.ic-member { font-size: 12px; color: #fff; background: #9A7425; padding: 4px 12px; border-radius: 14px; border: 1px solid #8A5E12; }
.ic-member.ghost { background: rgba(255,255,255,0.10); color: rgba(255,255,255,0.5); border-color: transparent; }
.ic-msgs { display: flex; flex-direction: column; gap: 8px; }
.ic-msg { background: #0F0F11; border-radius: 10px; padding: 8px 12px; font-size: 13px; }
.ic-msg.ghost { color: rgba(255,255,255,0.4); text-align: center; }
.ic-msg-name { color: #C4923A; font-weight: 700; margin-right: 8px; }
.ic-msg-content { color: #fff; }
.ic-msg-time { color: rgba(255,255,255,0.4); font-size: 11px; margin-left: 8px; }
.ic-sheet-ft { padding: 12px 16px; padding-bottom: calc(12px + env(safe-area-inset-bottom, 0px)); border-top: 1px solid rgba(255,255,255,0.08); display: flex; gap: 10px; background: #161618; }
.ic-join-btn { flex: 1; padding: 8px 20px; background-color: #9A7425; border: 3px solid #9A7425; border-radius: 20px; box-shadow: inset 3px 3px 7px rgba(0,0,0,0.45), inset -2px -2px 5px rgba(196,146,58,0.45); color: #FFFFFF; font-size: var(--fs-aux); font-weight: 600; white-space: nowrap; cursor: pointer; filter: drop-shadow(0 0.6px 1px rgba(0,0,0,0.4)); }
.ic-join-btn:active { box-shadow: inset 5px 5px 10px rgba(0,0,0,.55), inset -2px -2px 5px rgba(196,146,58,.35); }
.ic-msg-input { flex: 1; height: 44px; border: 1px solid rgba(255,255,255,0.15); background: #0F0F11; color: #fff; border-radius: 12px; padding: 0 14px; font-size: 14px; }
.ic-send-btn { padding: 8px 20px; background-color: #9A7425; border: 3px solid #9A7425; border-radius: 20px; box-shadow: inset 3px 3px 7px rgba(0,0,0,0.45), inset -2px -2px 5px rgba(196,146,58,0.45); color: #FFFFFF; font-size: var(--fs-aux); font-weight: 600; white-space: nowrap; cursor: pointer; filter: drop-shadow(0 0.6px 1px rgba(0,0,0,0.4)); }
/* 弹层操作按钮跟随活动群卡片五色（与首页一致，零高饱和橙） */
.ic-c-0 .ic-join-btn, .ic-c-0 .ic-send-btn { background-color: #8A5E12; border-color: #6E4A0E; box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(196,146,58,.45); }
.ic-c-1 .ic-join-btn, .ic-c-1 .ic-send-btn { background-color: #A87C48; border-color: #87613A; box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(201,149,108,.45); }
.ic-c-2 .ic-join-btn, .ic-c-2 .ic-send-btn { background-color: #5C241D; border-color: #451B16; box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(155,74,62,.45); }
.ic-c-3 .ic-join-btn, .ic-c-3 .ic-send-btn { background-color: #54545A; border-color: #3F3F44; box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(139,139,144,.45); }
.ic-c-4 .ic-join-btn, .ic-c-4 .ic-send-btn { background-color: #3C3E36; border-color: #2C2E28; box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(107,110,100,.45); }

.ic-slide-enter-active, .ic-slide-leave-active { transition: opacity 0.25s; }
.ic-slide-enter-from, .ic-slide-leave-to { opacity: 0; }
</style>
