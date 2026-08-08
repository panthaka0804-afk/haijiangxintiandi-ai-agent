<template>
  <div class="app-shell">
    <!-- 内容区 KeepAlive（已移除全局顶栏 .app-bar，由各页标题块代替） -->
    <div class="tab-content">
      <KeepAlive>
        <HomeTab v-if="activeTab === 'home'" key="home" @quickSend="onQuickSend" @switchTab="activeTab = $event" />
        <OffersTab v-else-if="activeTab === 'offers'" key="offers" />
        <ChatTab v-else-if="activeTab === 'chat'" key="chat" @switchTab="onSwitchTab" />
        <ProfileTab v-else-if="activeTab === 'profile'" key="profile" @switchTab="activeTab = $event" />
      </KeepAlive>
    </div>

    <!-- TabBar -->
    <div class="tab-bar">
      <div v-for="t in tabs" :key="t.key" class="tb-item" :class="{ active: activeTab === t.key }" @click="activeTab = t.key">
        <div class="tb-icon">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <template v-if="t.icon === 'home'">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
              <polyline points="9 22 9 12 15 12 15 22"/>
            </template>
            <template v-else-if="t.icon === 'ticket'">
              <path d="M20 12v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-8"/>
              <path d="M22 7H2v5h20z"/>
              <path d="M12 22V7"/>
            </template>
            <template v-else-if="t.icon === 'chat'">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </template>
            <template v-else>
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
              <circle cx="12" cy="7" r="4"/>
            </template>
          </svg>
        </div>
        <span class="tb-label">{{ t.label }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import HomeTab from './HomeTab.vue'
import OffersTab from './OffersTab.vue'
import ChatTab from './ChatTab.vue'
import ProfileTab from './ProfileTab.vue'

const activeTab = ref('home')
const tabs = [
  { key: 'home', label: '首页', icon: 'home' },
  { key: 'offers', label: '优惠', icon: 'ticket' },
  { key: 'chat', label: '客服', icon: 'chat' },
  { key: 'profile', label: '更多', icon: 'person' },
]

function onQuickSend(msg) {
  if (typeof msg === 'string' && msg.startsWith('?')) {
    activeTab.value = 'chat'
  } else if (msg) {
    activeTab.value = 'chat'
    // 消息会通过 chatStore 发送
  }
}

function onSwitchTab(tab) {
  activeTab.value = tab
}
</script>

<style scoped>
.app-shell { display: flex; flex-direction: column; height: 100vh; background: #1A1A1A; }

/* 内容 */
.tab-content { flex: 1; overflow-y: auto; -webkit-overflow-scrolling: touch; }

/* TabBar — 暗黑底 + 顶部分割线 */
.tab-bar {
  height: 56px; display: flex; flex-shrink: 0;
  background: #1A1A1A;
  border-top: 0.5px solid #333;
}
.tb-item {
  flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 2px; cursor: pointer; color: #777; transition: all 0.15s;
}
.tb-item.active { color: #999999; }
.tb-icon {
  width: 36px; height: 36px; display: flex; align-items: center; justify-content: center;
  border-radius: 10px; transition: all 0.15s;
}
.tb-label { font-size: 11px; font-weight: 600; }
</style>
