// 商城占位图索引 — 均用 CSS 渐变 SVG 代替真实图片
// 后续替换：将对应路径的 SVG 换成 PNG/WebP 即可

export const placeholderImages = {
  // 首页顶部 Banner（商场外观/内部全景）
  mallBanner: new URL('@/assets/placeholders/mall-banner.jpg', import.meta.url).href,

  // Banner 中间 Logo
  logoHero: new URL('@/assets/placeholders/logo-hero.png', import.meta.url).href,

  // 默认会员头像
  defaultAvatar: new URL('@/assets/placeholders/default-avatar.svg', import.meta.url).href,

  // 首页 Banner 下方促销横幅
  promoBanner: new URL('@/assets/placeholders/promo-banner.svg', import.meta.url).href,

  // 室内导航地图占位
  floorPlan: new URL('@/assets/placeholders/floor-plan.svg', import.meta.url).href,

  // 分类图标 — 美食
  categoryFood: new URL('@/assets/placeholders/category-food.svg', import.meta.url).href,

  // 分类图标 — 时尚零售
  categoryFashion: new URL('@/assets/placeholders/category-fashion.svg', import.meta.url).href,

  // 分类图标 — 停车
  categoryParking: new URL('@/assets/placeholders/category-parking.svg', import.meta.url).href,

  // 分类图标 — 亲子娱乐
  categoryKids: new URL('@/assets/placeholders/category-kids.svg', import.meta.url).href,
}

// 商户模拟数据 — 后续从数据库或 API 获取
export const shopList = [
  { id: 's1', name: '星巴克', floor: '1F', category: '餐饮', tags: ['咖啡', '轻食'], placeholder: null },
  { id: 's2', name: '蜀大侠火锅', floor: '4F', category: '餐饮', tags: ['火锅', '川菜'], placeholder: null },
  { id: 's3', name: '棒约翰', floor: 'B1', category: '餐饮', tags: ['披萨', '亲子'], placeholder: null },
  { id: 's4', name: 'UNIQLO', floor: '1F', category: '零售', tags: ['服饰', '日系'], placeholder: null },
  { id: 's5', name: '名创优品', floor: '2F', category: '零售', tags: ['百货', '生活'], placeholder: null },
  { id: 's6', name: '万达影城', floor: '5F', category: '娱乐', tags: ['电影', 'IMAX'], placeholder: null },
  { id: 's7', name: '玩具反斗城', floor: '3F', category: '亲子', tags: ['玩具', '儿童'], placeholder: null },
  { id: 's8', name: '海底捞', floor: '4F', category: '餐饮', tags: ['火锅', '服务'], placeholder: null },
]
