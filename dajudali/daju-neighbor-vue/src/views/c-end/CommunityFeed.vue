<template>
  <div class="community-page">
    <van-nav-bar title="邻里圈" left-text="返回" left-arrow @click-left="$router.back()" fixed placeholder>
      <template #right>
        <span class="nav-link" @click="$router.push('/points')">激励中心</span>
      </template>
    </van-nav-bar>

    <!-- 未登录提示 -->
    <div v-if="!phone" class="login-tip">
      <div class="tip-title">登录后加入邻里圈</div>
      <div class="tip-hint">发帖晒单、点赞评论、攒成长值</div>
      <van-button round block type="primary" style="margin-top:16px" @click="$router.push('/member')">去登录</van-button>
    </div>

    <template v-else>
      <!-- 话题横滑 -->
      <div class="topic-scroll">
        <span class="topic-chip" :class="{ active: !activeTopic }" @click="switchTopic('')">全部</span>
        <span v-for="t in topics" :key="t.id" class="topic-chip" :class="{ active: activeTopic === t.title }" @click="switchTopic(t.title)"># {{ t.title }}</span>
      </div>

      <!-- 信息流 -->
      <div class="feed-list">
        <div v-for="(p, i) in posts" :key="p.id" class="post-card" :class="'cmm-c-' + (i % 5)">
          <div class="post-head">
            <div class="post-avatar">{{ (p.user_name || '邻').slice(0, 1) }}</div>
            <div class="post-meta">
              <div class="post-name">{{ p.user_name }}</div>
              <div class="post-time">{{ fmtTime(p.created_at) }}</div>
            </div>
          </div>
          <div class="post-content">{{ p.content }}</div>
          <div v-if="p.images && p.images.length" class="post-images">
            <img v-for="(img, i) in p.images" :key="i" :src="img" alt="" loading="lazy" />
          </div>
          <div class="post-tags">
            <span v-if="p.topic" class="post-topic"># {{ p.topic }}</span>
            <span v-if="p.category" class="post-category">{{ p.category }}</span>
          </div>
          <div class="post-actions">
            <button class="act-btn" :class="{ liked: p.liked_by_me }" @click="doLike(p)">
              <svg width="16" height="16" viewBox="0 0 24 24" :fill="p.liked_by_me ? '#C4923A' : 'none'" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
              {{ p.like_count || 0 }}
            </button>
            <button class="act-btn" @click="openComments(p)">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
              {{ p.comment_count || 0 }}
            </button>
          </div>
        </div>
        <div v-if="!posts.length" class="feed-empty">还没有内容，来发第一篇吧~</div>
      </div>

      <!-- 发帖悬浮按钮 -->
      <button class="fab" @click="openPost">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
      </button>
    </template>

    <!-- 发帖弹窗 -->
    <van-popup v-model:show="showPost" position="bottom" round>
      <div class="post-pop">
        <div class="pop-title">发布内容</div>
        <textarea v-model="postContent" class="post-input" placeholder="分享你的探店、遛娃、好物体验…" maxlength="2000" />
        <div class="topic-pick">
          <span class="topic-chip" :class="{ active: !postTopic }" @click="postTopic = ''">无话题</span>
          <span v-for="t in topics" :key="t.id" class="topic-chip" :class="{ active: postTopic === t.title }" @click="postTopic = t.title"># {{ t.title }}</span>
        </div>
        <van-uploader v-model="fileList" :max-count="3" :after-read="afterRead" :preview-full-image="false" />
        <van-button round block type="primary" :loading="posting" style="margin-top:16px" @click="submitPost">发布（+10 成长值）</van-button>
      </div>
    </van-popup>

    <!-- 评论弹窗 -->
    <van-popup v-model:show="showComments" position="bottom" round>
      <div class="comment-pop">
        <div class="pop-title">评论</div>
        <div class="comment-list">
          <div v-for="c in comments" :key="c.id" class="comment-item">
            <div class="comment-name">{{ c.user_name }}</div>
            <div class="comment-content">{{ c.content }}</div>
          </div>
          <div v-if="!comments.length" class="comment-empty">还没有评论，抢个沙发~</div>
        </div>
        <div class="comment-input-row">
          <input v-model="commentContent" class="comment-input" placeholder="说点什么…" maxlength="500" @keyup.enter="submitComment" />
          <button class="comment-send" @click="submitComment">发送</button>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useMemberStore } from '@/stores/member'
import { showToast } from 'vant'

const memberStore = useMemberStore()

const phone = ref('')
const name = ref('')
const topics = ref([])
const posts = ref([])
const activeTopic = ref('')

const showPost = ref(false)
const postContent = ref('')
const postTopic = ref('')
const fileList = ref([])
const postImages = ref([])
const posting = ref(false)

const showComments = ref(false)
const currentPost = ref(null)
const comments = ref([])
const commentContent = ref('')

function fmtTime(ts) {
  if (!ts) return ''
  const d = new Date(ts.replace(' ', 'T'))
  const now = new Date()
  const diff = (now - d) / 1000
  if (diff < 60) return '刚刚'
  if (diff < 3600) return Math.floor(diff / 60) + ' 分钟前'
  if (diff < 86400) return Math.floor(diff / 3600) + ' 小时前'
  return (d.getMonth() + 1) + '月' + d.getDate() + '日'
}

async function loadTopics() {
  try {
    const res = await fetch('/api/community/topics').then(r => r.json())
    if (res.ok) topics.value = res.data
  } catch (e) {}
}

async function loadFeed() {
  if (!phone.value) return
  try {
    const url = '/api/community/feed?phone=' + phone.value + (activeTopic.value ? '&topic=' + encodeURIComponent(activeTopic.value) : '')
    const res = await fetch(url).then(r => r.json())
    if (res.ok) posts.value = res.data
  } catch (e) {}
}

function switchTopic(t) {
  activeTopic.value = t
  loadFeed()
}

function openPost() {
  postContent.value = ''
  postTopic.value = ''
  fileList.value = []
  postImages.value = []
  showPost.value = true
}

function afterRead(items) {
  items.forEach(item => {
    const file = item.file
    if (file.size > 3 * 1024 * 1024) {
      showToast('图片过大，请压缩后上传')
      return
    }
    const reader = new FileReader()
    reader.onload = () => {
      compressImage(reader.result, 800, 0.7, base64 => {
        postImages.value.push(base64)
      })
    }
    reader.readAsDataURL(file)
  })
}

function compressImage(dataUrl, maxW, quality, cb) {
  const img = new Image()
  img.onload = () => {
    const scale = Math.min(1, maxW / img.width)
    const canvas = document.createElement('canvas')
    canvas.width = img.width * scale
    canvas.height = img.height * scale
    const ctx = canvas.getContext('2d')
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
    cb(canvas.toDataURL('image/jpeg', quality))
  }
  img.src = dataUrl
}

async function submitPost() {
  if (!postContent.value.trim()) {
    showToast('请填写内容')
    return
  }
  posting.value = true
  try {
    const res = await fetch('/api/community/post', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone: phone.value, name: name.value, content: postContent.value.trim(), topic: postTopic.value, images: postImages.value }),
    }).then(r => r.json())
    if (res.ok) {
      showToast('发布成功 +10 成长值')
      if (res.data.new_badges && res.data.new_badges.length) showToast('获得新徽章！')
      showPost.value = false
      loadFeed()
      loadTopics()
    } else {
      showToast(res.error || '发布失败')
    }
  } catch (e) {
    showToast('网络错误')
  } finally {
    posting.value = false
  }
}

async function doLike(p) {
  try {
    const res = await fetch('/api/community/like', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ post_id: p.id, phone: phone.value }),
    }).then(r => r.json())
    if (res.ok) {
      p.liked_by_me = res.data.liked
      p.like_count = res.data.like_count
    }
  } catch (e) {}
}

async function openComments(p) {
  currentPost.value = p
  showComments.value = true
  try {
    const res = await fetch('/api/community/post/' + p.id + '?phone=' + phone.value).then(r => r.json())
    if (res.ok) comments.value = res.data.comments
  } catch (e) {}
}

async function submitComment() {
  if (!commentContent.value.trim() || !currentPost.value) return
  try {
    const res = await fetch('/api/community/comment', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ post_id: currentPost.value.id, phone: phone.value, name: name.value, content: commentContent.value.trim() }),
    }).then(r => r.json())
    if (res.ok) {
      showToast('评论成功 +2 成长值')
      commentContent.value = ''
      currentPost.value.comment_count = (currentPost.value.comment_count || 0) + 1
      openComments(currentPost.value)
    } else {
      showToast(res.error || '评论失败')
    }
  } catch (e) {}
}

onMounted(() => {
  const m = memberStore.member
  if (m && m.phone) {
    phone.value = m.phone
    name.value = m.name || m.display_name || ''
    loadTopics()
    loadFeed()
  }
})
</script>

<style scoped>
.community-page { min-height: 100vh; background: #000; padding-bottom: 90px; }
.nav-link { font-size: 14px; color: #C4923A; }
.login-tip { padding: 60px 32px; text-align: center; color: rgba(255,255,255,.6); }
.tip-title { font-size: 18px; color: #eee; margin-bottom: 8px; }
.tip-hint { font-size: 14px; }

.topic-scroll { display: flex; gap: 8px; padding: 12px 16px; overflow-x: auto; white-space: nowrap; -webkit-overflow-scrolling: touch; }
.topic-scroll::-webkit-scrollbar { display: none; }
.topic-chip { flex-shrink: 0; padding: 6px 14px; border-radius: 16px; background: #1a1a1a; border: 1px solid #2e2e2e; color: #999; font-size: 13px; cursor: pointer; }
.topic-chip.active { background: #9A7425; border-color: #8A5E12; color: #fff; box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(196,146,58,.45); }

.feed-list { padding: 0 16px; }
/* 帖子卡片：首页五色多彩卡（金黄/浅橙棕/深红棕/灰紫/深灰绿 循环） */
.post-card { border: 3px solid #8A5E12; border-radius: 16px; padding: 14px; margin-bottom: 12px; color: #fff; box-shadow: inset 0 1px 0 rgba(255,255,255,.22), 0 6px 16px rgba(0,0,0,.45); }
.cmm-c-0 { background: linear-gradient(135deg, #C4923A, #A8741C); border-color: #8A5E12; }
.cmm-c-1 { background: linear-gradient(135deg, #C9956C, #B07E4E); border-color: #A87C48; }
.cmm-c-2 { background: linear-gradient(135deg, #9B4A3E, #7E3328); border-color: #5C241D; }
.cmm-c-3 { background: linear-gradient(135deg, #8B8B90, #6F6F76); border-color: #54545A; }
.cmm-c-4 { background: linear-gradient(135deg, #6B6E64, #505247); border-color: #3C3E36; }
.post-head { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.post-avatar { width: 38px; height: 38px; border-radius: 50%; background: rgba(0,0,0,0.28); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 16px; font-weight: 600; flex-shrink: 0; }
.post-name { font-size: 14px; color: #fff; text-shadow: 0 1px 1px rgba(0,0,0,.35); }
.post-time { font-size: 11px; color: rgba(255,255,255,0.7); margin-top: 2px; }
.post-content { font-size: 15px; color: #fff; line-height: 1.6; word-break: break-word; text-shadow: 0 1px 1px rgba(0,0,0,.25); }
.post-images { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-top: 10px; }
.post-images img { width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 8px; }
.post-tags { margin-top: 10px; display: flex; gap: 8px; }
.post-topic { color: #fff; font-size: 12px; background: rgba(0,0,0,0.22); padding: 2px 8px; border-radius: 10px; }
.post-category { color: #fff; font-size: 12px; background: rgba(255,255,255,0.18); padding: 2px 8px; border-radius: 10px; }
.post-actions { display: flex; gap: 20px; margin-top: 12px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.25); }
.act-btn { display: flex; align-items: center; gap: 5px; background: none; border: none; color: rgba(255,255,255,0.85); font-size: 13px; cursor: pointer; padding: 0; }
.act-btn.liked { color: #fff; }
.feed-empty { text-align: center; color: rgba(255,255,255,0.6); padding: 40px 0; font-size: 14px; }

.fab { position: fixed; right: 20px; bottom: 80px; width: 52px; height: 52px; border-radius: 50%; border: 3px solid #8A5E12; background: #9A7425; display: flex; align-items: center; justify-content: center; cursor: pointer; box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(196,146,58,.45); z-index: 10; }

.post-pop { padding: 20px 16px 30px; }
.pop-title { font-size: 16px; font-weight: 600; color: #fff; margin-bottom: 14px; }
.post-input { width: 100%; min-height: 100px; background: #161618; border: 1px solid rgba(255,255,255,0.15); border-radius: 10px; color: #eee; padding: 12px; font-size: 15px; resize: none; }
.topic-pick { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0; }

.comment-pop { padding: 20px 16px 30px; max-height: 70vh; display: flex; flex-direction: column; }
.comment-list { flex: 1; overflow-y: auto; margin-bottom: 12px; }
.comment-item { padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.08); }
.comment-name { font-size: 13px; color: #C4923A; margin-bottom: 4px; }
.comment-content { font-size: 14px; color: #eee; line-height: 1.5; }
.comment-empty { text-align: center; color: rgba(255,255,255,0.5); padding: 20px 0; }
.comment-input-row { display: flex; gap: 10px; }
.comment-input { flex: 1; background: #161618; border: 1px solid rgba(255,255,255,0.15); border-radius: 20px; color: #eee; padding: 10px 14px; font-size: 14px; }
.comment-send { padding: 10px 18px; border-radius: 20px; font-size: 14px; cursor: pointer; background-color: #9A7425; border: 3px solid #9A7425; color: #fff; font-weight: 600; white-space: nowrap; box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(196,146,58,.45); filter: drop-shadow(0 0.6px 1px rgba(0,0,0,0.4)); }
/* 弹窗/登录的 van primary 按钮也统一金棕凹陷 */
.community-page :deep(.van-button--primary) { background-color: #9A7425; border-color: #8A5E12; color: #fff; font-weight: 600; box-shadow: inset 3px 3px 7px rgba(0,0,0,.45), inset -2px -2px 5px rgba(196,146,58,.45); }
.community-page :deep(.van-button--primary:active) { box-shadow: inset 5px 5px 10px rgba(0,0,0,.55), inset -2px -2px 5px rgba(196,146,58,.35); }
</style>
