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
  { id: 's2', name: '朱光玉火锅', floor: '1F', category: '餐饮', tags: ['火锅', '川菜'], placeholder: null },
  { id: 's3', name: '瑞幸咖啡', floor: '1F', category: '餐饮', tags: ['咖啡', '快取'], placeholder: null },
  { id: 's4', name: '华为授权店', floor: '1F', category: '零售', tags: ['手机', '数码'], placeholder: null },
  { id: 's5', name: '晨光文具', floor: '1F', category: '零售', tags: ['文具', '办公'], placeholder: null },
  { id: 's6', name: 'SFC上影影城', floor: '1F', category: '娱乐', tags: ['电影', '影城'], placeholder: null },
  { id: 's7', name: '泡泡米儿童', floor: '1F', category: '亲子', tags: ['儿童', '教培'], placeholder: null },
  { id: 's8', name: '康友四季', floor: '1F', category: '生活服务', tags: ['足浴', '养生'], placeholder: null },
]
