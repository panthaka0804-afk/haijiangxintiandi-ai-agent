<template>
  <div class="mp-page">
    <div class="mp-back" @click="$router.back()">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#AAA" stroke-width="2" stroke-linecap="round"><polyline points="15 18 9 12 15 6"/></svg>
    </div>

    <div class="mp-hero">
      <div class="mp-hero-icon">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#999999" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
      </div>
      <div class="mp-hero-title">招商合作</div>
      <div class="mp-hero-sub">海江新天地诚邀优质品牌入驻</div>
    </div>

    <div class="mp-card">
      <div class="mp-card-title">项目优势</div>
      <div class="mp-advantage">
        <div class="mp-ad-item">
          <div class="mp-ad-icon">📍</div>
          <div class="mp-ad-text">核心商圈 · 日均客流 3 万+</div>
        </div>
        <div class="mp-ad-item">
          <div class="mp-ad-icon">🏢</div>
          <div class="mp-ad-text">5 层商业体 · 200+ 商铺</div>
        </div>
        <div class="mp-ad-item">
          <div class="mp-ad-icon">🅿️</div>
          <div class="mp-ad-text">地下停车场 · 500 车位</div>
        </div>
        <div class="mp-ad-item">
          <div class="mp-ad-icon">📊</div>
          <div class="mp-ad-text">统一运营 · 品牌推广支持</div>
        </div>
      </div>
    </div>

    <div class="mp-card">
      <div class="mp-card-title">招商类目</div>
      <div class="mp-tags">
        <span class="mp-tag">餐饮美食</span>
        <span class="mp-tag">时尚零售</span>
        <span class="mp-tag">亲子娱乐</span>
        <span class="mp-tag">生活服务</span>
        <span class="mp-tag">教育培训</span>
        <span class="mp-tag">科技数码</span>
      </div>
    </div>

    <div class="mp-card">
      <div class="mp-card-title">联系方式</div>
      <div class="mp-contact">
        <div class="mp-contact-item" @click="call">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#999999" stroke-width="1.5" stroke-linecap="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
          <span>致电咨询：400-888-8888</span>
        </div>
        <div class="mp-contact-item">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#999999" stroke-width="1.5" stroke-linecap="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
          <span>招商邮箱：merchant@haijiang.com</span>
        </div>
        <div class="mp-contact-item">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#999999" stroke-width="1.5" stroke-linecap="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
          <span>周一至周五 9:00-18:00</span>
        </div>
      </div>
    </div>

    <a href="tel:4008888888" class="mp-call-btn">立即拨打</a>
    <div class="spacer"></div>
  </div>
</template>

<script setup>
function call() { window.location.href = 'tel:4008888888' }
</script>

<style scoped>
.mp-page { padding: 0 12px; min-height: 100vh; background: #1A1A1A; }
.mp-back { padding: 10px 0; cursor: pointer; display: inline-block; margin-bottom: 4px; }

.mp-hero { text-align: center; padding: 24px 0 20px; }
.mp-hero-icon { margin-bottom: 12px; }
.mp-hero-title { font-size: 24px; font-weight: 700; color: #F0F0F0; }
.mp-hero-sub { font-size: 14px; color: #777; margin-top: 6px; }

.mp-card { margin-bottom: 10px; padding: 16px; background: #2A2A2A; border-radius: 14px; }
.mp-card-title { font-size: 15px; font-weight: 600; color: #F0F0F0; margin-bottom: 12px; }

.mp-advantage { display: flex; flex-direction: column; gap: 10px; }
.mp-ad-item { display: flex; align-items: center; gap: 10px; }
.mp-ad-icon { font-size: 18px; }
.mp-ad-text { font-size: 14px; color: #AAA; }

.mp-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.mp-tag {
  padding: 5px 14px; border-radius: 20px; background: #1A1A1A; color: #999999;
  font-size: 13px; font-weight: 500;
}

.mp-contact { display: flex; flex-direction: column; gap: 12px; }
.mp-contact-item { display: flex; align-items: center; gap: 10px; font-size: 14px; color: #AAA; cursor: pointer; }

.mp-call-btn {
  display: block; width: 100%; padding: 14px; border: none; border-radius: 14px;
  background: #1A1A1A; color: #fff; font-size: 16px; font-weight: 700;
  text-align: center; text-decoration: none; cursor: pointer; margin-top: 8px;
}
.spacer { height: 40px; }
</style>
