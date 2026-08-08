import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

// Element Plus
import 'element-plus/dist/index.css'
// Vant (按需导入在 vite.config.js 配了 auto-import)
import 'vant/lib/index.css'
// 全局样式（暗黑主题变量 + 字体规范 + UI库暗色覆盖），须在三方库之后以覆盖默认值
import './style.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
