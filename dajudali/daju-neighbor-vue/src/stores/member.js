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

  return {
    member,
    isLoggedIn,
    setMember,
    clearMember,
    restore,
    loginByPhone,
    register,
    logout,
  }
})
