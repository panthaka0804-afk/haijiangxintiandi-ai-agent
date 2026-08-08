<template>
  <div class="settings-page">
    <h3>系统设置</h3>

    <el-card shadow="never" style="margin-bottom: 16px;">
      <template #header>
        <span>租户设置</span>
      </template>
      <el-form :model="tenantForm" label-width="100px">
        <el-form-item label="租户名称">
          <el-input v-model="tenantForm.name" placeholder="如：海江新天地社区商业" />
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input v-model="tenantForm.phone" placeholder="客服电话" />
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="tenantForm.address" placeholder="商场地址" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="savingTenant" @click="saveTenant">保存设置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" style="margin-bottom: 16px;">
      <template #header>
        <span>AI 配置</span>
      </template>
      <el-form :model="aiConfig" label-width="100px">
        <el-form-item label="系统提示词">
          <el-input v-model="aiConfig.system_prompt" type="textarea" :rows="6" placeholder="AI客服的系统提示词" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="savingAI" @click="saveAIConfig">保存配置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <span>API 密钥</span>
      </template>
      <el-form :model="apiKeys" label-width="120px">
        <el-form-item label="DeepSeek API Key">
          <el-input v-model="apiKeys.ds_api_key" type="password" show-password placeholder="sk-..." />
        </el-form-item>
        <el-form-item label="Secret Key">
          <el-input v-model="apiKeys.secret_key" type="password" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="saveApiKeys">保存密钥</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getTenants, updateTenant } from '@/api'

const savingTenant = ref(false)
const savingAI = ref(false)
const tenantForm = ref({ name: '', phone: '', address: '' })
const aiConfig = ref({ system_prompt: '' })
const apiKeys = ref({ ds_api_key: '', secret_key: '' })

onMounted(async () => {
  try {
    const res = await getTenants()
    const arr = Array.isArray(res) ? res : (res.tenants || [])
    if (arr.length) {
      const t = arr[0]
      tenantForm.value = { name: t.name || '', phone: t.phone || '', address: t.address || '' }
    }
  } catch {}
})

async function saveTenant() {
  savingTenant.value = true
  try {
    await updateTenant(1, tenantForm.value)
    ElMessage.success('设置已保存')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    savingTenant.value = false
  }
}

function saveAIConfig() {
  ElMessage.success('AI配置已保存（此功能需后端配合）')
}

function saveApiKeys() {
  ElMessage.success('密钥已保存（此功能需后端配合）')
}
</script>

<style scoped>
h3 {
  margin: 0 0 16px;
  color: #303133;
  font-size: 18px;
}
</style>
