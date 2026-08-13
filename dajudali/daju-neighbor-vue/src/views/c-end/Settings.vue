<template>
  <div class="st-page">
    <div class="st-back" @click="$router.back()">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#AAA" stroke-width="2" stroke-linecap="round"><polyline points="15 18 9 12 15 6"/></svg>
    </div>

    <!-- 头部 -->
    <div class="st-head">
      <div class="st-head-title">设置</div>
      <div class="st-head-sub">Settings</div>
    </div>

    <!-- 账户信息卡片 -->
    <div class="st-account" @click="$router.push('/member')">
      <div class="st-acc-avatar">
        <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
      </div>
      <div class="st-acc-info">
        <div class="st-acc-name">海江会员</div>
        <div class="st-acc-phone">195****1648</div>
      </div>
      <div class="st-acc-level">普卡 Lv.1</div>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.6)" stroke-width="2" stroke-linecap="round"><polyline points="9 18 15 12 9 6"/></svg>
    </div>

    <!-- 账户 -->
    <div class="st-section">
      <div class="st-tag st-tag-gold">账户</div>

      <div class="st-card st-card-gold" @click="go('/member')">
        <div class="st-row-left">
          <span class="st-ic st-ic-gold"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg></span>
          <span>账户与安全</span>
        </div>
        <div class="st-row-right"><span class="st-val">已实名</span><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.5)" stroke-width="2" stroke-linecap="round"><polyline points="9 18 15 12 9 6"/></svg></div>
      </div>

      <div class="st-card st-card-pink">
        <div class="st-row-left">
          <span class="st-ic st-ic-pink"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg></span>
          <span>消息通知</span>
        </div>
        <div class="st-row-right">
          <span class="st-val st-val-muted" v-if="!notifyOn">已关闭</span>
          <span class="st-val st-val-on" v-else>已开启</span>
          <div class="st-switch" :class="{ on: notifyOn }" @click.stop="notifyOn = !notifyOn"><span class="st-knob"></span></div>
        </div>
      </div>

      <div class="st-card st-card-orangebrown">
        <div class="st-row-left">
          <span class="st-ic st-ic-orangebrown"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7V4h16v3"/><path d="M9 20h6"/><path d="M12 4v16"/></svg></span>
          <span>大字模式</span>
        </div>
        <div class="st-row-right">
          <span class="st-val st-val-muted" v-if="!user.largeFont">标准</span>
          <span class="st-val st-val-on" v-else>大字体</span>
          <div class="st-switch" :class="{ on: user.largeFont }" @click.stop="user.largeFont = !user.largeFont"><span class="st-knob"></span></div>
        </div>
      </div>

      <div class="st-card st-card-grayviolet">
        <div class="st-row-left">
          <span class="st-ic st-ic-grayviolet"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg></span>
          <span>深色模式</span>
        </div>
        <div class="st-row-right">
          <span class="st-val st-val-on">已开启</span>
          <div class="st-switch on" @click.stop="toast('当前为深色主题，无需切换')"><span class="st-knob"></span></div>
        </div>
      </div>
    </div>

    <!-- 通用 -->
    <div class="st-section">
      <div class="st-tag st-tag-greengray">通用</div>
      <div class="st-card st-card-greengray" @click="clearCache">
        <div class="st-row-left">
          <span class="st-ic st-ic-greengray"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg></span>
          <span>清除缓存</span>
        </div>
        <div class="st-row-right"><span class="st-val st-val-muted">{{ cacheSize }}</span><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.5)" stroke-width="2" stroke-linecap="round"><polyline points="9 18 15 12 9 6"/></svg></div>
      </div>
    </div>

    <!-- 隐私与法律 -->
    <div class="st-section">
      <div class="st-tag st-tag-grayviolet">隐私与法律</div>
      <div class="st-card st-card-gold" @click="go('/user-agreement')">
        <div class="st-row-left">
          <span class="st-ic st-ic-gold"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></span>
          <span>用户协议</span>
        </div>
        <div class="st-row-right"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.5)" stroke-width="2" stroke-linecap="round"><polyline points="9 18 15 12 9 6"/></svg></div>
      </div>
      <div class="st-card st-card-pink" @click="go('/privacy-policy')">
        <div class="st-row-left">
          <span class="st-ic st-ic-pink"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg></span>
          <span>隐私政策</span>
        </div>
        <div class="st-row-right"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.5)" stroke-width="2" stroke-linecap="round"><polyline points="9 18 15 12 9 6"/></svg></div>
      </div>
      <div class="st-card st-card-orangebrown" @click="go('/about')">
        <div class="st-row-left">
          <span class="st-ic st-ic-orangebrown"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg></span>
          <span>关于我们</span>
        </div>
        <div class="st-row-right"><span class="st-val st-val-muted">v1.0.0</span><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.5)" stroke-width="2" stroke-linecap="round"><polyline points="9 18 15 12 9 6"/></svg></div>
      </div>
    </div>

    <!-- 帮助 -->
    <div class="st-section">
      <div class="st-tag st-tag-orangebrown">帮助</div>
      <div class="st-card st-card-grayviolet" @click="go('/')">
        <div class="st-row-left">
          <span class="st-ic st-ic-grayviolet"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg></span>
          <span>帮助与反馈</span>
        </div>
        <div class="st-row-right"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.5)" stroke-width="2" stroke-linecap="round"><polyline points="9 18 15 12 9 6"/></svg></div>
      </div>
    </div>

    <!-- 账号操作（危险区） -->
    <div class="st-section">
      <div class="st-tag st-tag-brownred">账号操作</div>
      <div class="st-card st-card-greengray st-logout" @click="logout">
        <div class="st-row-left">
          <span class="st-ic st-ic-greengray"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg></span>
          <span>退出登录</span>
        </div>
      </div>
      <div class="st-card st-card-brownred st-unregister" @click="showUnreg = true">
        <div class="st-row-left">
          <span class="st-ic st-ic-brownred"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg></span>
          <span>注销账号</span>
        </div>
      </div>
    </div>

    <div class="st-footer">海江新天地 · 上海宝山</div>

    <!-- 注销确认弹窗 -->
    <transition name="st-fade">
      <div class="st-modal-mask" v-if="showUnreg" @click.self="showUnreg = false">
        <div class="st-modal">
          <div class="st-modal-ic"><svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#FF5252" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg></div>
          <div class="st-modal-title">注销账号</div>
          <div class="st-modal-text">注销后，您的会员信息、积分、优惠券、停车绑定等数据将被永久删除且无法恢复。请谨慎操作。</div>
          <label class="st-check" @click="agreeUnreg = !agreeUnreg">
            <span class="st-check-box" :class="{ on: agreeUnreg }">
              <svg v-if="agreeUnreg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
            </span>
            <span>我已了解注销后无法恢复</span>
          </label>
          <div class="st-modal-btns">
            <button class="st-btn st-btn-cancel" @click="showUnreg = false">取消</button>
            <button class="st-btn st-btn-danger" :disabled="!agreeUnreg" @click="confirmUnregister">确认注销</button>
          </div>
        </div>
      </div>
    </transition>

    <!-- Toast -->
    <transition name="st-fade">
      <div class="st-toast" v-if="toastMsg">{{ toastMsg }}</div>
    </transition>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
const router = useRouter()
const user = useUserStore()

const notifyOn = ref(localStorage.getItem('hj_notify') === '1')
const cacheSize = ref('2.4 MB')
const showUnreg = ref(false)
const agreeUnreg = ref(false)
const toastMsg = ref('')
let toastTimer = null

function toast(m) {
  toastMsg.value = m
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => (toastMsg.value = ''), 1800)
}

function go(path) { router.push(path) }

// 消息通知持久化
import { watch } from 'vue'
watch(notifyOn, (v) => localStorage.setItem('hj_notify', v ? '1' : '0'))

function clearCache() {
  try {
    // 保留账号登录态与大字模式偏好，清理其它业务缓存
    const keep = ['largeFont', 'hj_notify']
    const backup = {}
    keep.forEach((k) => { backup[k] = localStorage.getItem(k) })
    localStorage.clear()
    Object.keys(backup).forEach((k) => backup[k] != null && localStorage.setItem(k, backup[k]))
    sessionStorage.removeItem('__dj_member')
  } catch (e) {}
  cacheSize.value = '0 KB'
  toast('缓存已清除')
}

async function logout() {
  try { await fetch('/logout', { method: 'POST' }) } catch (e) {}
  user.clearUser()
  sessionStorage.removeItem('__dj_member')
  try { localStorage.removeItem('member_phone') } catch (e) {}
  toast('已退出登录')
  setTimeout(() => router.replace('/'), 700)
}

async function confirmUnregister() {
  if (!agreeUnreg.value) return
  try { await fetch('/logout', { method: 'POST' }) } catch (e) {}
  // 清空本地全部账号相关数据
  try {
    localStorage.clear()
    sessionStorage.clear()
  } catch (e) {}
  user.clearUser()
  showUnreg.value = false
  toast('账号已注销')
  setTimeout(() => { router.replace('/'); setTimeout(() => location.reload(), 300) }, 800)
}
</script>

<style scoped>
.st-page { padding: 0 14px; min-height: 100vh; background: #000000; }
.st-back { padding: 12px 0; cursor: pointer; display: inline-block; margin-bottom: 2px; }

/* 头部 */
.st-head { display: flex; flex-direction: column; margin-bottom: 16px; }
.st-head-title { font-size: 26px; font-weight: 800; color: #FFFFFF; letter-spacing: 1px; }
.st-head-sub { font-size: 12px; color: #8A8A8A; letter-spacing: 2px; margin-top: 2px; }

/* 账户卡片 */
.st-account {
  display: flex; align-items: center; gap: 12px;
  background: linear-gradient(135deg, #C4923A, #9A7425);
  border: 1px solid #9A7425;
  border-radius: 16px; padding: 16px; margin-bottom: 18px; cursor: pointer;
  box-shadow: 0 4px 12px rgba(0,0,0,.35), inset 0 1px 0 rgba(255,255,255,.20);
}
.st-acc-avatar {
  width: 48px; height: 48px; border-radius: 50%; flex-shrink: 0;
  background: linear-gradient(135deg, #C4923A, #C4923A);
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 3px 10px rgba(196,146,58,0.3);
}
.st-acc-info { flex: 1; min-width: 0; }
.st-acc-name { font-size: 17px; font-weight: 700; color: #F0F0F0; }
.st-acc-phone { font-size: 13px; color: #9A9A9A; margin-top: 3px; }
.st-acc-level {
  font-size: 12px; font-weight: 700;   color: #FFE8B0;
  background: rgba(196,146,58,0.15); border: 1px solid rgba(196,146,58,0.35);
  border-radius: 8px; padding: 4px 10px; flex-shrink: 0;
}

/* 分组 / 多彩卡片 */
.st-section { margin-bottom: 18px; }
.st-tag {
  display: inline-block; font-size: 12px; font-weight: 700; letter-spacing: 1px;
  padding: 4px 12px; border-radius: 20px; margin: 0 0 10px 2px;
}
.st-tag-gold       { color: #F2D9A8; background: rgba(196,146,58,.20);  border: 1px solid rgba(196,146,58,.50); }
.st-tag-pink       { color: #F0D8D0; background: rgba(212,165,154,.20); border: 1px solid rgba(212,165,154,.50); }
.st-tag-orangebrown{ color: #ECCFB6; background: rgba(201,149,108,.20); border: 1px solid rgba(201,149,108,.50); }
.st-tag-grayviolet { color: #DADADF; background: rgba(139,139,144,.20); border: 1px solid rgba(139,139,144,.50); }
.st-tag-greengray  { color: #CACDBF; background: rgba(107,110,100,.20); border: 1px solid rgba(107,110,100,.50); }
.st-tag-brownred   { color: #ECCDC7; background: rgba(155,74,62,.20);  border: 1px solid rgba(155,74,62,.50); }

/* 多彩卡片 */
.st-card {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 16px; margin-bottom: 10px; cursor: pointer;
  border-radius: 14px; border: 1px solid transparent;
  box-shadow: 0 4px 12px rgba(0,0,0,.35), inset 0 1px 0 rgba(255,255,255,.12);
  transition: transform .12s ease, box-shadow .12s ease;
}
.st-card:active { transform: scale(.985); }
.st-row-left { display: flex; align-items: center; gap: 12px; font-size: 15px; font-weight: 600; color: #FFFFFF; text-shadow: 0 1px 2px rgba(0,0,0,0.30); }
.st-row-right { display: flex; align-items: center; gap: 8px; }
.st-val { font-size: 13px; text-shadow: 0 1px 2px rgba(0,0,0,0.30); }
.st-val-muted { color: rgba(255,255,255,0.72); }
.st-val-on { color: #FFFFFF; font-weight: 700; }

/* 卡片配色 —— 与首页「多彩卡片」统一色板：金黄/浅粉棕/深红棕/浅橙棕/灰紫/深灰绿 */
.st-card-gold       { background: #C4923A; border-color: #9A7425; }
.st-card-pink       { background: #D4A59A; border-color: #A67D72; }
.st-card-orangebrown{ background: #C9956C; border-color: #A87C48; }
.st-card-grayviolet { background: #8B8B90; border-color: #6A6A6E; }
.st-card-greengray  { background: #6B6E64; border-color: #4E5049; }
.st-card-brownred   { background: #9B4A3E; border-color: #6E332A; }

/* 图标底色块 */
.st-ic {
  width: 32px; height: 32px; border-radius: 9px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
}
.st-ic-gold        { background: linear-gradient(135deg, #D9A85A, #C4923A); }
.st-ic-pink        { background: linear-gradient(135deg, #E4C0B6, #D4A59A); }
.st-ic-orangebrown { background: linear-gradient(135deg, #DAAE8E, #C9956C); }
.st-ic-grayviolet  { background: linear-gradient(135deg, #A4A4A8, #8B8B90); }
.st-ic-greengray   { background: linear-gradient(135deg, #82857A, #6B6E64); }
.st-ic-brownred    { background: linear-gradient(135deg, #B5635A, #9B4A3E); }

/* 开关 */
.st-switch {
  width: 44px; height: 26px; border-radius: 13px; flex-shrink: 0;
  background: #3A3A3A; position: relative; cursor: pointer; transition: background 0.2s;
}
.st-switch.on { background: linear-gradient(135deg, #C4923A, #C4923A); }
.st-knob {
  position: absolute; top: 3px; left: 3px; width: 20px; height: 20px;
  border-radius: 50%; background: #fff; transition: left 0.2s; box-shadow: 0 1px 3px rgba(0,0,0,0.4);
}
.st-switch.on .st-knob { left: 21px; }

/* 危险行文字（实色卡片上保持白字清晰） */
.st-logout .st-row-left span:last-child,
.st-unregister .st-row-left span:last-child { color: #FFFFFF; font-weight: 700; }

/* 底部 */
.st-footer { text-align: center; color: rgba(255,255,255,0.45); font-size: 12px; padding: 16px 0 40px; }

/* 弹窗 */
.st-modal-mask {
  position: fixed; inset: 0; background: rgba(0,0,0,0.7);
  display: flex; align-items: center; justify-content: center; z-index: 100; padding: 30px;
}
.st-modal {
  width: 100%; max-width: 320px; background: #1E1E1E; border-radius: 18px; padding: 24px 20px 18px;
  border: 1px solid rgba(255,255,255,0.1); text-align: center;
}
.st-modal-ic {
  width: 56px; height: 56px; border-radius: 50%; margin: 0 auto 14px;
  background: rgba(255,82,82,0.12); display: flex; align-items: center; justify-content: center;
}
.st-modal-title { font-size: 19px; font-weight: 800; color: #FFFFFF; }
.st-modal-text { font-size: 13px; line-height: 1.7; color: #B5B5B5; margin: 12px 0 16px; text-align: left; }
.st-check { display: flex; align-items: center; gap: 8px; text-align: left; font-size: 13px; color: #D0D0D0; cursor: pointer; margin-bottom: 18px; }
.st-check-box {
  width: 20px; height: 20px; border-radius: 6px; flex-shrink: 0;
  border: 1.5px solid rgba(255,255,255,0.3); display: flex; align-items: center; justify-content: center;
}
.st-check-box.on { background: #C4923A; border-color: #C4923A; }
.st-modal-btns { display: flex; gap: 12px; }
.st-btn {
  flex: 1; padding: 12px 0; border: none; border-radius: 12px; font-size: 15px; font-weight: 700; cursor: pointer;
}
.st-btn-cancel { background: #333; color: #E0E0E0; }
.st-btn-danger { background: linear-gradient(135deg, #E0554F, #B1302B); color: #fff; }
.st-btn-danger:disabled { opacity: 0.4; cursor: not-allowed; }

/* Toast */
.st-toast {
  position: fixed; left: 50%; bottom: 80px; transform: translateX(-50%);
  background: rgba(20,20,20,0.95); color: #fff; padding: 12px 22px; border-radius: 24px;
  font-size: 14px; z-index: 200; border: 1px solid rgba(255,255,255,0.12);
  box-shadow: 0 4px 16px rgba(0,0,0,0.5);
}

.st-fade-enter-active, .st-fade-leave-active { transition: opacity 0.2s; }
.st-fade-enter-from, .st-fade-leave-to { opacity: 0; }
</style>
