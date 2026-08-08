<template>
  <div class="figma-page">
    <el-card shadow="never" class="figma-header-card">
      <div class="figma-header">
        <div>
          <h2>Figma 设计协作</h2>
          <p class="figma-sub">实时预览设计稿，直接在后台提修改意见</p>
        </div>
        <div class="figma-header-actions">
          <el-input
            v-model="figmaUrl"
            placeholder="粘贴 Figma 链接 https://www.figma.com/file/..."
            size="default"
            style="width: 420px"
            clearable
            @keyup.enter="loadFigma"
          >
            <template #append>
              <el-button type="primary" @click="loadFigma" :loading="loading">加载</el-button>
            </template>
          </el-input>
          <el-button-group>
            <el-button
              :type="viewMode === 'design' ? 'primary' : 'default'"
              @click="viewMode = 'design'"
            >
              <el-icon><View /></el-icon> 设计稿
            </el-button>
            <el-button
              :type="viewMode === 'comments' ? 'primary' : 'default'"
              @click="viewMode = 'comments'"
            >
              <el-icon><ChatDotRound /></el-icon> 批注列表
            </el-button>
          </el-button-group>
        </div>
      </div>
    </el-card>

    <div class="figma-body">
      <!-- 设计稿预览区 -->
      <div class="figma-preview" v-show="viewMode === 'design'">
        <div v-if="!currentFileKey" class="figma-empty">
          <el-icon :size="64" color="#A8A7A4"><Picture /></el-icon>
          <p>输入 Figma 文件链接开始协作</p>
          <p class="figma-empty-tip">支持 Figma 文件链接和 Frame 链接</p>
          <el-divider>快捷入口</el-divider>
          <div class="figma-quick-links">
            <el-card
              v-for="project in savedProjects"
              :key="project.key"
              shadow="hover"
              class="figma-project-card"
              @click="loadProject(project)"
            >
              <div class="project-preview">
                <el-icon :size="32" color="#999999"><Folder /></el-icon>
              </div>
              <div class="project-info">
                <div class="project-name">{{ project.name }}</div>
                <div class="project-date">{{ project.updatedAt }}</div>
              </div>
            </el-card>
            <el-card shadow="hover" class="figma-project-card figma-add-card" @click="showAddDialog = true">
              <el-icon :size="32" color="#A8A7A4"><Plus /></el-icon>
              <span>添加项目</span>
            </el-card>
          </div>
        </div>
        <div v-else class="figma-embed-wrap">
          <!-- Figma 嵌入 iframe -->
          <div class="figma-toolbar">
            <el-breadcrumb separator="/">
              <el-breadcrumb-item @click="backToProjects">
                <el-icon><ArrowLeft /></el-icon> 项目列表
              </el-breadcrumb-item>
              <el-breadcrumb-item>{{ currentProject?.name || '设计稿' }}</el-breadcrumb-item>
            </el-breadcrumb>
            <div class="figma-toolbar-actions">
              <el-tag v-if="currentProject?.status" :type="statusType(currentProject.status)" size="small">
                {{ currentProject.status }}
              </el-tag>
              <el-button-group size="small">
                <el-button @click="zoomOut">
                  <el-icon><Minus /></el-icon>
                </el-button>
                <el-button @click="zoomIn">
                  <el-icon><Plus /></el-icon>
                </el-button>
                <el-button @click="fitScreen">
                  <el-icon><FullScreen /></el-icon>
                </el-button>
              </el-button-group>
              <el-button size="small" @click="openInFigma" type="primary" plain>
                <el-icon><TopRight /></el-icon> Figma 打开
              </el-button>
            </div>
          </div>
          <iframe
            v-if="embedUrl"
            :src="embedUrl"
            class="figma-iframe"
            allowfullscreen
          ></iframe>
        </div>
      </div>

      <!-- 批注列表 -->
      <div class="figma-comments" v-show="viewMode === 'comments'">
        <div class="comments-toolbar">
          <el-input
            v-model="newComment"
            placeholder="添加批注或修改意见..."
            type="textarea"
            :rows="3"
            resize="none"
          />
          <div class="comments-toolbar-actions">
            <el-select v-model="commentStatus" placeholder="状态筛选" clearable size="small" style="width:120px">
              <el-option label="待处理" value="pending" />
              <el-option label="处理中" value="in_progress" />
              <el-option label="已解决" value="resolved" />
            </el-select>
            <el-button type="primary" @click="addComment" :disabled="!newComment.trim()">
              发布批注
            </el-button>
          </div>
        </div>
        <div class="comments-list">
          <div v-if="comments.length === 0" class="comments-empty">
            <el-icon :size="48" color="#A8A7A4"><ChatLineSquare /></el-icon>
            <p>暂无批注，加载设计稿后可以在这里提修改意见</p>
          </div>
          <el-timeline v-else>
            <el-timeline-item
              v-for="item in filteredComments"
              :key="item.id"
              :timestamp="item.createdAt"
              :type="item.status === 'resolved' ? 'success' : item.status === 'in_progress' ? 'warning' : 'primary'"
              placement="top"
            >
              <el-card shadow="hover" class="comment-card">
                <div class="comment-header">
                  <div class="comment-author">
                    <el-avatar :size="32" style="background:#1A1A1A">{{ item.author?.[0] || 'A' }}</el-avatar>
                    <div>
                      <strong>{{ item.author || '匿名' }}</strong>
                      <span class="comment-page-ref" v-if="item.pageRef"> · {{ item.pageRef }}</span>
                    </div>
                  </div>
                  <div class="comment-actions">
                    <el-tag :type="statusType(item.status)" size="small">
                      {{ statusLabel(item.status) }}
                    </el-tag>
                    <el-dropdown trigger="click" v-if="item.status !== 'resolved'">
                      <el-button size="small" text>
                        <el-icon><MoreFilled /></el-icon>
                      </el-button>
                      <template #dropdown>
                        <el-dropdown-menu>
                          <el-dropdown-item @click="updateCommentStatus(item, 'in_progress')">标记处理中</el-dropdown-item>
                          <el-dropdown-item @click="updateCommentStatus(item, 'resolved')">标记已解决</el-dropdown-item>
                        </el-dropdown-menu>
                      </template>
                    </el-dropdown>
                  </div>
                </div>
                <div class="comment-body">{{ item.content }}</div>
                <div class="comment-reply" v-if="item.replies?.length">
                  <div v-for="reply in item.replies" :key="reply.id" class="reply-item">
                    <strong>{{ reply.author }}:</strong> {{ reply.content }}
                    <span class="reply-time">{{ reply.createdAt }}</span>
                  </div>
                </div>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </div>
      </div>
    </div>

    <!-- 添加项目弹窗 -->
    <el-dialog v-model="showAddDialog" title="添加设计项目" width="500px">
      <el-form :model="newProject" label-width="80px">
        <el-form-item label="项目名称">
          <el-input v-model="newProject.name" placeholder="例: 海江新天地首页改版" />
        </el-form-item>
        <el-form-item label="Figma链接">
          <el-input v-model="newProject.url" placeholder="https://www.figma.com/file/..." />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="saveProject" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  View, ChatDotRound, Picture, Folder, Plus, ArrowLeft,
  Minus, FullScreen, TopRight, ChatLineSquare, MoreFilled
} from '@element-plus/icons-vue'

// ===== 状态 =====
const figmaUrl = ref('')
const currentFileKey = ref('')
const embedUrl = ref('')
const loading = ref(false)
const viewMode = ref('design')
const showAddDialog = ref(false)
const saving = ref(false)
const newComment = ref('')
const commentStatus = ref('')
const zoomLevel = ref(1)

const newProject = ref({ name: '', url: '' })

// 保存的项目（实际应该存数据库，这里先 localStorage）
const savedProjects = ref(JSON.parse(localStorage.getItem('figma-projects') || '[]'))

// 模拟批注数据
const comments = ref(JSON.parse(localStorage.getItem('figma-comments') || '[]'))

const currentProject = computed(() => {
  return savedProjects.value.find(p => p.key === currentFileKey.value)
})

const filteredComments = computed(() => {
  if (!commentStatus.value) return comments.value
  return comments.value.filter(c => c.status === commentStatus.value)
})

// ===== 方法 =====

// 从 Figma URL 提取 file key
function extractFigmaKey(url) {
  // https://www.figma.com/file/XXXXX/filename
  // https://www.figma.com/design/XXXXX/filename
  const match = url.match(/figma\.com\/(file|design)\/([a-zA-Z0-9]+)/)
  return match ? match[2] : null
}

function loadFigma() {
  const key = extractFigmaKey(figmaUrl.value)
  if (!key) {
    ElMessage.warning('请输入有效的 Figma 链接')
    return
  }
  loading.value = true
  currentFileKey.value = key
  embedUrl.value = `https://www.figma.com/embed?embed_host=dajusheji&url=https://www.figma.com/file/${key}/Design?node-id=0%3A1`
  setTimeout(() => { loading.value = false }, 500)
}

function loadProject(project) {
  currentFileKey.value = project.key
  embedUrl.value = `https://www.figma.com/embed?embed_host=dajusheji&url=https://www.figma.com/file/${project.key}/Design?node-id=0%3A1`
}

function backToProjects() {
  currentFileKey.value = ''
  embedUrl.value = ''
}

function saveProject() {
  if (!newProject.value.name || !newProject.value.url) {
    ElMessage.warning('请填写完整信息')
    return
  }
  const key = extractFigmaKey(newProject.value.url)
  if (!key) {
    ElMessage.warning('Figma 链接无效')
    return
  }
  saving.value = true
  savedProjects.value.push({
    key,
    name: newProject.value.name,
    url: newProject.value.url,
    status: 'in_review',
    updatedAt: new Date().toLocaleDateString('zh-CN')
  })
  localStorage.setItem('figma-projects', JSON.stringify(savedProjects.value))
  newProject.value = { name: '', url: '' }
  showAddDialog.value = false
  saving.value = false
  ElMessage.success('项目已添加')
}

function addComment() {
  if (!newComment.value.trim()) return
  const comment = {
    id: Date.now(),
    content: newComment.value.trim(),
    author: '管理员',
    status: 'pending',
    pageRef: currentProject.value?.name || '设计稿',
    createdAt: new Date().toLocaleString('zh-CN'),
    replies: []
  }
  comments.value.unshift(comment)
  localStorage.setItem('figma-comments', JSON.stringify(comments.value))
  newComment.value = ''
  ElMessage.success('批注已发布')
}

function updateCommentStatus(comment, status) {
  comment.status = status
  localStorage.setItem('figma-comments', JSON.stringify(comments.value))
  ElMessage.success('状态已更新')
}

function statusType(status) {
  const map = { pending: 'danger', in_progress: 'warning', resolved: 'success', in_review: 'info' }
  return map[status] || 'info'
}

function statusLabel(status) {
  const map = { pending: '待处理', in_progress: '处理中', resolved: '已解决', in_review: '审核中' }
  return map[status] || status
}

function zoomIn() {
  zoomLevel.value = Math.min(2, zoomLevel.value + 0.1)
}

function zoomOut() {
  zoomLevel.value = Math.max(0.5, zoomLevel.value - 0.1)
}

function fitScreen() {
  zoomLevel.value = 1
}

function openInFigma() {
  if (currentProject.value) {
    window.open(currentProject.value.url, '_blank')
  }
}
</script>

<style scoped>
.figma-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 140px);
  gap: 16px;
}

.figma-header-card {
  flex-shrink: 0;
}

.figma-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.figma-header h2 {
  margin: 0 0 4px;
  font-size: 20px;
  font-weight: 700;
}

.figma-sub {
  margin: 0;
  color: #BBBBBB;
  font-size: 14px;
}

.figma-header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.figma-body {
  flex: 1;
  min-height: 0;
}

.figma-preview {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.figma-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #BBBBBB;
}

.figma-empty p {
  margin: 8px 0 0;
  font-size: 15px;
}

.figma-empty-tip {
  font-size: 13px !important;
  color: #A8A7A4 !important;
}

.figma-quick-links {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  justify-content: center;
  margin-top: 16px;
}

.figma-project-card {
  width: 180px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.figma-project-card:hover {
  transform: translateY(-2px);
}

.figma-add-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #A8A7A4;
  font-size: 13px;
  border: 1px dashed #D6D5D3;
  min-height: 100px;
}

.project-preview {
  display: flex;
  justify-content: center;
  margin-bottom: 8px;
}

.project-name {
  font-size: 14px;
  font-weight: 600;
  color: #F0F0F0;
}

.project-date {
  font-size: 12px;
  color: #A8A7A4;
  margin-top: 4px;
}

.figma-embed-wrap {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.figma-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: #1A1A1A;
  border-radius: 8px;
  margin-bottom: 8px;
  border: 1px solid #E8E8E6;
}

.figma-toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.figma-iframe {
  flex: 1;
  border: 1px solid #E8E8E6;
  border-radius: 8px;
  width: 100%;
  min-height: 400px;
}

/* 批注区 */
.figma-comments {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.comments-toolbar {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.comments-toolbar-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.comments-list {
  flex: 1;
  overflow-y: auto;
}

.comments-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  color: #A8A7A4;
}

.comment-card {
  margin-bottom: 8px;
}

.comment-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.comment-author {
  display: flex;
  align-items: center;
  gap: 8px;
}

.comment-page-ref {
  color: #A8A7A4;
  font-size: 12px;
}

.comment-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.comment-body {
  font-size: 14px;
  line-height: 1.6;
  color: #F0F0F0;
}

.comment-reply {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #F5F5F4;
}

.reply-item {
  font-size: 13px;
  line-height: 1.5;
  color: #BBBBBB;
  margin-bottom: 4px;
}

.reply-time {
  color: #A8A7A4;
  font-size: 11px;
  margin-left: 8px;
}
</style>
