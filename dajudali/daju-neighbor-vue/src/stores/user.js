import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { getSession } from '@/api'

// 从 localStorage 恢复大字模式
const savedLarge = localStorage.getItem('largeFont') === '1'
if (savedLarge) document.documentElement.setAttribute('data-large', '')

export const useUserStore = defineStore('user', () => {
  const user = ref(null)
  const isLoggedIn = ref(false)
  const loading = ref(true)

  async function checkSession() {
    try {
      loading.value = true
      const res = await getSession()
      if (res.ok) {
        user.value = res.user
        isLoggedIn.value = true
      } else {
        user.value = null
        isLoggedIn.value = false
      }
    } catch {
      user.value = null
      isLoggedIn.value = false
    } finally {
      loading.value = false
    }
  }

  function setUser(u) {
    user.value = u
    isLoggedIn.value = !!u
  }

  function clearUser() {
    user.value = null
    isLoggedIn.value = false
  }

  const isAdmin = () => {
    return user.value && ['tenant_admin', 'super_admin'].includes(user.value.role)
  }

  const isSuperAdmin = () => {
    return user.value && user.value.role === 'super_admin'
  }

  // 大字模式
  const largeFont = ref(savedLarge)
  watch(largeFont, (v) => {
    localStorage.setItem('largeFont', v ? '1' : '0')
    if (v) document.documentElement.setAttribute('data-large', '')
    else document.documentElement.removeAttribute('data-large')
  })

  return { user, isLoggedIn, loading, checkSession, setUser, clearUser, isAdmin, isSuperAdmin, largeFont }
})
