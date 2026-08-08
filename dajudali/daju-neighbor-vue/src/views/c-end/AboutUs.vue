<template>
  <div class="au-page">
    <div class="au-back" @click="$router.back()">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#AAA" stroke-width="2" stroke-linecap="round"><polyline points="15 18 9 12 15 6"/></svg>
    </div>

    <!-- 头部 -->
    <div class="au-hero">
      <div class="au-logo">海</div>
      <div class="au-name">旭惠·海江新天地</div>
      <div class="au-en">XUHUI · HAIJIANG SHOPPING MALL</div>
      <div class="au-slogan">一街两面 · 昼夜共生</div>
      <div class="au-meta">总建筑面积约 81,000㎡　|　B1 – 4F</div>
    </div>

    <!-- 项目简介 -->
    <section class="au-card">
      <h2 class="au-h">项目简介</h2>
      <p class="au-p">旭惠·海江新天地坐落于上海市宝山区牡丹江路中心位置，北起海江路、南至永乐路，紧邻白玉兰绿化广场、宝山体育中心等市政设施，是宝山区主干道、长展面、商办融合、多元发展的综合商业街区。</p>
      <p class="au-p">项目融合宝山在地文化与青年社交场景，是集世界美食、艺术人文、休闲娱乐于一体的特色商业街区，为北上海居住与办公人群提供美好生活方式新选择。</p>
    </section>

    <!-- 区位交通 -->
    <section class="au-card">
      <h2 class="au-h">区位交通</h2>
      <div class="au-grid">
        <div class="au-cell">
          <div class="au-cell-ic">🚇</div>
          <div class="au-cell-t">地铁 3 号线宝杨路站</div>
          <div class="au-cell-s">步行约 0.9 KM</div>
        </div>
        <div class="au-cell">
          <div class="au-cell-ic">🚇</div>
          <div class="au-cell-t">地铁 3 号线友谊路站</div>
          <div class="au-cell-s">约 1.4 KM</div>
        </div>
        <div class="au-cell">
          <div class="au-cell-ic">🚌</div>
          <div class="au-cell-t">21 个公交站点</div>
          <div class="au-cell-s">1KM 内通达全市</div>
        </div>
        <div class="au-cell">
          <div class="au-cell-ic">🛣️</div>
          <div class="au-cell-t">G1503 上海绕城高速</div>
          <div class="au-cell-s">驾车 5 分钟上高速</div>
        </div>
      </div>
    </section>

    <!-- 15 分钟生活圈 -->
    <section class="au-card">
      <h2 class="au-h">15 分钟生活圈</h2>
      <p class="au-p">响应上海市"15 分钟社区生活圈"行动方案，原安信商业广场焕新为旭惠·海江新天地。3KM 范围内覆盖超 25 万常住人口、120 所院校、近 300 个住宅社区，为商业繁荣提供稳定市场基础。</p>
      <div class="au-stats">
        <div class="au-stat"><div class="au-stat-num">25<span>万+</span></div><div class="au-stat-lbl">覆盖人口</div></div>
        <div class="au-stat"><div class="au-stat-num">120<span>所</span></div><div class="au-stat-lbl">周边院校</div></div>
        <div class="au-stat"><div class="au-stat-num">296<span>个</span></div><div class="au-stat-lbl">住宅社区</div></div>
      </div>
    </section>

    <!-- 业态占比 -->
    <section class="au-card">
      <h2 class="au-h">业态占比</h2>
      <div class="au-bar-row" v-for="b in formats" :key="b.label">
        <div class="au-bar-lbl">{{ b.label }}</div>
        <div class="au-bar-track"><div class="au-bar-fill" :style="{ width: b.pct + '%', background: b.color }"></div></div>
        <div class="au-bar-pct">{{ b.pct }}%</div>
      </div>
    </section>

    <!-- 七大板块 -->
    <section class="au-card">
      <h2 class="au-h">项目七大板块</h2>
      <div class="au-block" v-for="(b, i) in blocks" :key="i">
        <div class="au-block-no">{{ b.no }}</div>
        <div class="au-block-body">
          <div class="au-block-name">{{ b.name }}</div>
          <div class="au-block-desc">{{ b.desc }}</div>
        </div>
      </div>
    </section>

    <!-- 周边利好 -->
    <section class="au-card">
      <h2 class="au-h">区域利好</h2>
      <div class="au-tags">
        <span class="au-tag">吴淞创新城（北上海城市副中心）</span>
        <span class="au-tag">上海吴淞口国际邮轮港（亚洲最大邮轮母港）</span>
        <span class="au-tag">牡丹江路商业街焕新（宝山"南京路"）</span>
        <span class="au-tag">上海宝山站（2027 年通车，北上海交通枢纽）</span>
        <span class="au-tag">宝武钢铁集团总部职能回归</span>
      </div>
    </section>

    <!-- 活动 IP -->
    <section class="au-card">
      <h2 class="au-h">全年活动 IP</h2>
      <p class="au-p">以"街区即舞台，生活即内容"为理念，打造「艺萃 · 潮燃 · 心悦」三大内容矩阵，全年无休精彩活动。</p>
      <div class="au-ip" v-for="ip in ips" :key="ip.title">
        <div class="au-ip-head">
          <span class="au-ip-title">{{ ip.title }}</span>
          <span class="au-ip-sub">{{ ip.sub }}</span>
        </div>
        <div class="au-ip-list">
          <span class="au-ip-item" v-for="(e, i) in ip.events" :key="i">{{ e }}</span>
        </div>
      </div>
    </section>

    <!-- 地址 -->
    <section class="au-card au-addr">
      <h2 class="au-h">项目地址</h2>
      <div class="au-addr-row">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FF7B2C" stroke-width="1.6" stroke-linecap="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
        <span>上海市宝山区牡丹江路 1228 – 1258 号</span>
      </div>
    </section>

    <div class="spacer"></div>
  </div>
</template>

<script setup>
const formats = [
  { label: '特色餐饮', pct: 40, color: '#C4923A' },
  { label: '休闲娱乐', pct: 28, color: '#9B4A3E' },
  { label: '生活服务', pct: 15, color: '#8B8B90' },
  { label: '亲子教育', pct: 10, color: '#C9956C' },
  { label: '生鲜零售', pct: 7, color: '#6B6E64' },
]

const blocks = [
  { no: 'B1', name: '海江·星动聚场', desc: '潮玩风尚引力场 · 密室逃脱 / 剧本杀 / 游艺厅 / KTV / 足浴' },
  { no: 'B2', name: '海江·财富中心', desc: '22 层甲级写字楼' },
  { no: 'B3/4/6', name: '海江夜巷', desc: '潮乐夜生活聚落 · "夜经济"与"潮经济"核心引擎' },
  { no: 'B5', name: '海江·商务中心', desc: '18 层甲级写字楼' },
  { no: 'B7', name: '海江·悦活天地', desc: '全能生活服务枢纽 · 金融 / 教育 / 健康 / 宠物 / 影音' },
]

const ips = [
  { title: '海江·艺萃', sub: '人文艺术盛宴', events: ['海江城市艺术季', '幻境光影节', '海江火把节'] },
  { title: '海江·潮燃', sub: '青年引力磁场', events: ['次元觉醒嘉年华', '夏日造浪节', '星空电音狂欢节'] },
  { title: '海江·心悦', sub: '品味精致生活', events: ['爪爪萌友派对', '微风生活节', '海江精酿啤酒节'] },
]
</script>

<style scoped>
.au-page { padding: 0 12px; min-height: 100vh; background: #000000; }
.au-back { padding: 12px 0; cursor: pointer; display: inline-block; margin-bottom: 2px; }

/* 头部 */
.au-hero { text-align: center; padding: 18px 0 22px; }
.au-logo {
  width: 64px; height: 64px; margin: 0 auto 14px; border-radius: 18px;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #FF7B2C, #E85D04);
  color: #fff; font-size: 34px; font-weight: 800;
  box-shadow: 0 4px 14px rgba(255, 123, 44, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.35);
}
.au-name { font-size: 24px; font-weight: 700; color: #F0F0F0; }
.au-en { font-size: 12px; color: #8A8A8A; letter-spacing: 1px; margin-top: 4px; }
.au-slogan { font-size: 15px; color: #FF7B2C; font-weight: 600; margin-top: 12px; }
.au-meta { font-size: 13px; color: #999; margin-top: 6px; }

/* 卡片 */
.au-card {
  margin-bottom: 10px; padding: 16px;
  background: #1A1A1A; border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.06);
}
.au-h {
  font-size: 16px; font-weight: 700; color: #FFFFFF;
  margin: 0 0 12px; padding-left: 10px;
  border-left: 3px solid #FF7B2C;
}
.au-p { font-size: 14px; line-height: 1.85; color: #BDBDBD; margin: 0 0 10px; }
.au-p:last-child { margin-bottom: 0; }

/* 交通网格 */
.au-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.au-cell {
  background: #232323; border-radius: 12px; padding: 12px;
  display: flex; flex-direction: column; gap: 4px;
}
.au-cell-ic { font-size: 20px; }
.au-cell-t { font-size: 13px; color: #E8E8E8; font-weight: 600; }
.au-cell-s { font-size: 12px; color: #8A8A8A; }

/* 统计 */
.au-stats { display: flex; gap: 10px; margin-top: 14px; }
.au-stat { flex: 1; text-align: center; background: #232323; border-radius: 12px; padding: 14px 6px; }
.au-stat-num { font-size: 22px; font-weight: 800; color: #FF7B2C; }
.au-stat-num span { font-size: 12px; font-weight: 600; color: #FF7B2C; margin-left: 2px; }
.au-stat-lbl { font-size: 12px; color: #9A9A9A; margin-top: 4px; }

/* 业态条 */
.au-bar-row { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.au-bar-row:last-child { margin-bottom: 0; }
.au-bar-lbl { width: 56px; font-size: 13px; color: #D0D0D0; flex-shrink: 0; }
.au-bar-track { flex: 1; height: 10px; background: #2A2A2A; border-radius: 6px; overflow: hidden; }
.au-bar-fill { height: 100%; border-radius: 6px; }
.au-bar-pct { width: 38px; text-align: right; font-size: 13px; color: #FF7B2C; font-weight: 700; flex-shrink: 0; }

/* 板块 */
.au-block { display: flex; gap: 12px; margin-bottom: 12px; align-items: flex-start; }
.au-block:last-child { margin-bottom: 0; }
.au-block-no {
  flex-shrink: 0; width: 52px; height: 40px; border-radius: 10px;
  background: #232323; color: #FF7B2C; font-size: 13px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}
.au-block-name { font-size: 14px; color: #F0F0F0; font-weight: 600; }
.au-block-desc { font-size: 12px; color: #9A9A9A; margin-top: 3px; line-height: 1.6; }

/* 标签 */
.au-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.au-tag {
  padding: 6px 12px; border-radius: 18px; background: #232323;
  color: #C0C0C0; font-size: 12px; line-height: 1.4;
}

/* 活动 IP */
.au-ip { margin-bottom: 14px; }
.au-ip:last-child { margin-bottom: 0; }
.au-ip-head { display: flex; align-items: baseline; gap: 8px; margin-bottom: 8px; }
.au-ip-title { font-size: 14px; font-weight: 700; color: #FF7B2C; }
.au-ip-sub { font-size: 12px; color: #8A8A8A; }
.au-ip-list { display: flex; flex-wrap: wrap; gap: 8px; }
.au-ip-item {
  padding: 5px 12px; border-radius: 16px;
  background: #232323; color: #D0D0D0; font-size: 12px;
}

/* 地址 */
.au-addr-row { display: flex; align-items: center; gap: 10px; font-size: 14px; color: #E0E0E0; }

.spacer { height: 40px; }
</style>
