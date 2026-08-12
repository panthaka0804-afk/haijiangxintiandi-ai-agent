import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { lookupMember, registerMember } from '@/api'

export const useMemberStore = defineStore('member', () => {
  const member = ref(null)

  const isLoggedIn = computed(() => !!member.value)

  function setMember(m) {
    member.value = m
    // 持久化到 sessionStorage
    if (m) {
      sessionStorage.setItem('__dj_member', JSON.stringify(m))
    } else {
      sessionStorage.removeItem('__dj_member')
    }
  }

  function clearMember() {
    member.value = null
    sessionStorage.removeItem('__dj_member')
  }

  // 从 sessionStorage 恢复
  function restore() {
    try {
      const stored = sessionStorage.getItem('__dj_member')
      if (stored) {
        member.value = JSON.parse(stored)
      }
    } catch {}
  }

  async function loginByPhone(phone) {
    const res = await lookupMember(phone)
    if (res.ok) {
      setMember(res.member)
      return { ok: true }
    }
    return { ok: false, error: res.error || '查询失败' }
  }

  async function register(name, phone) {
    const res = await registerMember(name, phone)
    if (res.ok) {
      setMember({
        display_name: name,
        phone,
        membership_level: '普卡',
        discount: 98,
        points: 500,
      })
      return { ok: true }
    }
    return { ok: false, error: res.error || '注册失败' }
  }

  function logout() {
    clearMember()
  }

  // 会员等级 → 统一主题色（全站各页会员卡/积分卡共用，避免各页配色不一致）
  // bg: 实色底；bd: 深边框色；accent: 高光/强调色
  function levelTheme(level) {
    const map = {
      '普卡':   { bg: '#8B8B90', bd: '#6A6A6E', accent: '#A9A9AE' },
      '银卡':   { bg: '#9CA1A8', bd: '#7A7E84', accent: '#C2C6CC' },
      '金卡':   { bg: '#C4923A', bd: '#9A7425', accent: '#DDB873' },
      '铂金卡': { bg: '#9DA7B5', bd: '#7C8593', accent: '#C3CBD6' },
      '钻石卡': { bg: '#4F9CC9', bd: '#3A7BA0', accent: '#8FC8E8' },
      '黑钻卡': { bg: '#2E2E33', bd: '#555555', accent: '#6E6E76' },
    }
    return map[level] || map['普卡']
  }

  return {
    member,
    isLoggedIn,
    setMember,
    clearMember,
    restore,
    loginByPhone,
    register,
    logout,
    levelTheme,
  }
})
