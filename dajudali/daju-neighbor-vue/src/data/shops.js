// 海江新天地 — 商户数据（来源：旭惠·海江新天地 招商落位2026.5 实际落位）
// 由 gen_shops.py 从招商落位清单生成，字段驱动 室内导航 / 商户列表 / 商户详情

const raw = [
  { id:'s001', name:'瑞幸咖啡', floor:1, zone:'1区', category:'餐饮', tags:['咖啡', '快取'], color:'#0051A8' },
  { id:'s002', name:'多乐之日', floor:1, zone:'1区', category:'餐饮', tags:['烘焙', '面包'], color:'#8B5A2B' },
  { id:'s003', name:'麦当劳', floor:1, zone:'1区', category:'餐饮', tags:['快餐', '汉堡'], color:'#D52B1E' },
  { id:'s004', name:'秀目眼镜', floor:1, zone:'1区', category:'零售', tags:['眼镜', '验光'], color:'#4A90D9' },
  { id:'s005', name:'霸王茶姬', floor:1, zone:'1区', category:'餐饮', tags:['茶饮', '新茶饮'], color:'#6E4B3A' },
  { id:'s006', name:'小杨生煎', floor:1, zone:'1区', category:'餐饮', tags:['生煎', '小吃'], color:'#C0392B' },
  { id:'s007', name:'新贝乐', floor:1, zone:'1区', category:'餐饮', tags:['本帮菜', '家常菜'], color:'#C4923A' },
  { id:'s008', name:'手心兔小吐司', floor:1, zone:'1区', category:'餐饮', tags:['吐司', '烘焙'], color:'#C9975A' },
  { id:'s009', name:'贵华嫂', floor:1, zone:'1区', category:'餐饮', tags:['小吃', '面点'], color:'#C4923A' },
  { id:'s010', name:'成都你六姐', floor:1, zone:'1区', category:'餐饮', tags:['川菜', '江湖菜'], color:'#C2185B' },
  { id:'s011', name:'晨光文具', floor:1, zone:'1区', category:'零售', tags:['文具', '办公'], color:'#4A90D9' },
  { id:'s012', name:'老盛兴汤包馆', floor:1, zone:'1区', category:'餐饮', tags:['汤包', '小吃'], color:'#C0392B' },
  { id:'s013', name:'烧饼文化', floor:1, zone:'1区', category:'餐饮', tags:['烧饼', '小吃'], color:'#C4923A' },
  { id:'s014', name:'潮纪', floor:1, zone:'1区', category:'餐饮', tags:['潮汕', '牛肉'], color:'#C2185B' },
  { id:'s015', name:'喜姐炸串', floor:1, zone:'1区', category:'餐饮', tags:['炸串', '小吃'], color:'#C4923A' },
  { id:'s016', name:'临榆炸鸡腿', floor:1, zone:'1区', category:'餐饮', tags:['炸鸡', '小吃'], color:'#D52B1E' },
  { id:'s017', name:'银流咖啡', floor:1, zone:'1区', category:'餐饮', tags:['咖啡', '轻食'], color:'#6F4E37' },
  { id:'s018', name:'海江食集', floor:1, zone:'1区', category:'餐饮', tags:['美食广场', '小吃集合'], color:'#C4923A' },
  { id:'s019', name:'万酒堂', floor:1, zone:'1区', category:'零售', tags:['酒水', '零售'], color:'#4A90D9' },
  { id:'s020', name:'诺家智慧大药房', floor:1, zone:'1区', category:'生活服务', tags:['药房', '健康'], color:'#3E8E41' },
  { id:'s021', name:'古康元', floor:1, zone:'1区', category:'生活服务', tags:['理疗', '养生'], color:'#3E8E41' },
  { id:'s022', name:'美甲美睫', floor:1, zone:'1区', category:'生活服务', tags:['美甲', '美睫'], color:'#3E8E41' },
  { id:'s023', name:'美肤盾', floor:1, zone:'1区', category:'生活服务', tags:['护肤', '美容'], color:'#3E8E41' },
  { id:'s024', name:'通信钟表', floor:1, zone:'1区', category:'生活服务', tags:['通讯', '钟表'], color:'#3E8E41' },
  { id:'s025', name:'体彩', floor:1, zone:'1区', category:'生活服务', tags:['彩票', '便民'], color:'#3E8E41' },
  { id:'s026', name:'福彩', floor:1, zone:'1区', category:'生活服务', tags:['彩票', '便民'], color:'#3E8E41' },
  { id:'s027', name:'泡泡米儿童', floor:2, zone:'1区', category:'亲子', tags:['儿童娱乐', '亲子'], color:'#E8809E' },
  { id:'s028', name:'小荧星艺校', floor:2, zone:'1区', category:'亲子', tags:['艺术培训', '舞蹈'], color:'#E8809E' },
  { id:'s029', name:'海江活动艺术中心', floor:2, zone:'1区', category:'娱乐', tags:['艺术中心', '演出'], color:'#9B7BD4' },
  { id:'s030', name:'雀王棋牌', floor:3, zone:'1区', category:'娱乐', tags:['棋牌', '休闲'], color:'#9B7BD4' },
  { id:'s031', name:'哇咔健身', floor:3, zone:'1区', category:'娱乐', tags:['健身', '团课'], color:'#9B7BD4' },
  { id:'s032', name:'锦光星耀桌球俱乐部', floor:3, zone:'1区', category:'娱乐', tags:['桌球', '台球'], color:'#9B7BD4' },
  { id:'s033', name:'尊柜KTV/棋牌室', floor:4, zone:'1区', category:'娱乐', tags:['KTV', '棋牌'], color:'#9B7BD4' },
  { id:'s034', name:'徐妈串串', floor:1, zone:'3区', category:'餐饮', tags:['串串', '川味'], color:'#C4923A' },
  { id:'s035', name:'泰士多', floor:1, zone:'3区', category:'餐饮', tags:['东南亚', '料理'], color:'#C4923A' },
  { id:'s036', name:'刘栋梁大排档', floor:1, zone:'3区', category:'餐饮', tags:['大排档', '夜宵'], color:'#C4923A' },
  { id:'s037', name:'星巴克', floor:1, zone:'3区', category:'餐饮', tags:['咖啡', '第三空间'], color:'#00704A' },
  { id:'s038', name:'味千拉面', floor:1, zone:'3区', category:'餐饮', tags:['拉面', '日式'], color:'#E60012' },
  { id:'s039', name:'小灶湘', floor:1, zone:'3区', category:'餐饮', tags:['湘菜', '剁椒'], color:'#C2185B' },
  { id:'s040', name:'朱光玉火锅', floor:1, zone:'3区', category:'餐饮', tags:['火锅', '重庆'], color:'#C2185B' },
  { id:'s041', name:'扬春茶社', floor:1, zone:'3区', category:'餐饮', tags:['茶馆', '茶饮'], color:'#6E4B3A' },
  { id:'s042', name:'肖记公安牛杂', floor:1, zone:'3区', category:'餐饮', tags:['牛杂', '湖北'], color:'#C4923A' },
  { id:'s043', name:'大城小野', floor:2, zone:'3区', category:'餐饮', tags:['料理', '创意菜'], color:'#C2185B' },
  { id:'s044', name:'伴月楼', floor:2, zone:'3区', category:'餐饮', tags:['杭帮菜', '本帮'], color:'#C0392B' },
  { id:'s045', name:'星巴克', floor:2, zone:'3区', category:'餐饮', tags:['咖啡', '第三空间'], color:'#00704A' },
  { id:'s046', name:'汇通棋牌', floor:3, zone:'3区', category:'娱乐', tags:['棋牌', '休闲'], color:'#9B7BD4' },
  { id:'s047', name:'苏宁易购', floor:1, zone:'4区', category:'零售', tags:['电器', '数码'], color:'#E60012' },
  { id:'s048', name:'华为/迪信通', floor:1, zone:'4区', category:'零售', tags:['手机', '数码'], color:'#4A90D9' },
  { id:'s049', name:'足浴养生', floor:3, zone:'4区', category:'生活服务', tags:['足浴', '养生'], color:'#3E8E41' },
  { id:'s050', name:'民谣星烧烤酒馆', floor:1, zone:'6区', category:'餐饮', tags:['烧烤', '音乐'], color:'#C4923A' },
  { id:'s051', name:'戴海川·美蛙', floor:1, zone:'6区', category:'餐饮', tags:['美蛙', '川味'], color:'#C2185B' },
  { id:'s052', name:'暴走牛牛·碳火烧肉', floor:1, zone:'6区', category:'餐饮', tags:['烧肉', '日式'], color:'#C0392B' },
  { id:'s053', name:'鱼石尚云南蒸石锅鱼', floor:1, zone:'6区', category:'餐饮', tags:['蒸汽石锅鱼', '云南菜'], color:'#3E8E41' },
  { id:'s054', name:'福海面馆', floor:1, zone:'6区', category:'餐饮', tags:['面', '快餐'], color:'#E60012' },
  { id:'s055', name:'Jenga精酿啤酒馆', floor:1, zone:'6区', category:'餐饮', tags:['精酿', '啤酒'], color:'#C9975A' },
  { id:'s056', name:'潮汕·草根活鱼火锅', floor:1, zone:'6区', category:'餐饮', tags:['火锅', '潮汕'], color:'#C2185B' },
  { id:'s057', name:'阿国烤局', floor:1, zone:'6区', category:'餐饮', tags:['烤串', '夜宵'], color:'#C4923A' },
  { id:'s058', name:'深夜食堂', floor:1, zone:'6区', category:'餐饮', tags:['夜宵', '小炒'], color:'#C4923A' },
  { id:'s059', name:'汽石锅鱼', floor:1, zone:'6区', category:'餐饮', tags:['石锅鱼', '川味'], color:'#3E8E41' },
  { id:'s060', name:'牛肉档', floor:1, zone:'6区', category:'餐饮', tags:['牛肉', '火锅'], color:'#C0392B' },
  { id:'s061', name:'合一瑜伽健身', floor:2, zone:'6区', category:'娱乐', tags:['瑜伽', '健身'], color:'#9B7BD4' },
  { id:'s062', name:'合一瑜伽普拉提', floor:2, zone:'6区', category:'娱乐', tags:['普拉提', '健身'], color:'#9B7BD4' },
  { id:'s063', name:'L服饰', floor:2, zone:'6区', category:'零售', tags:['服饰', '服装'], color:'#4A90D9' },
  { id:'s064', name:'网鱼电竞酒店', floor:2, zone:'6区', category:'娱乐', tags:['电竞', '酒店'], color:'#9B7BD4' },
  { id:'s065', name:'屿汀美容spa', floor:2, zone:'6区', category:'生活服务', tags:['美容', 'SPA'], color:'#3E8E41' },
  { id:'s066', name:'弘文书馆', floor:2, zone:'6区', category:'生活服务', tags:['书店', '文创'], color:'#3E8E41' },
  { id:'s067', name:'康友四季', floor:2, zone:'6区', category:'生活服务', tags:['洗浴', '汗蒸'], color:'#3E8E41' },
  { id:'s068', name:'新鸳鸯', floor:3, zone:'6区', category:'餐饮', tags:['火锅', '川味'], color:'#C2185B' },
  { id:'s069', name:'功夫汪宠物乐园', floor:1, zone:'7区', category:'亲子', tags:['宠物', '亲子'], color:'#E8809E' },
  { id:'s070', name:'东煜画室', floor:1, zone:'7区', category:'亲子', tags:['绘画', '美术'], color:'#E8809E' },
  { id:'s071', name:'卡卡海洋', floor:1, zone:'7区', category:'亲子', tags:['亲子乐园', '探索'], color:'#E8809E' },
  { id:'s072', name:'招商银行', floor:1, zone:'7区', category:'生活服务', tags:['银行', '金融'], color:'#4A90D9' },
  { id:'s073', name:'壹品培优', floor:1, zone:'7区', category:'亲子', tags:['培优', '托管'], color:'#E8809E' },
  { id:'s074', name:'舞林园', floor:1, zone:'7区', category:'亲子', tags:['舞蹈', '培训'], color:'#E8809E' },
  { id:'s075', name:'OX牛排', floor:1, zone:'7区', category:'餐饮', tags:['牛排', '西餐'], color:'#C0392B' },
  { id:'s076', name:'MANNER', floor:1, zone:'7区', category:'餐饮', tags:['咖啡', '精品咖啡'], color:'#B8915C' },
  { id:'s077', name:'赛百味', floor:1, zone:'7区', category:'餐饮', tags:['三明治', '轻食'], color:'#2E8B57' },
  { id:'s078', name:'海鲜餐厅', floor:1, zone:'7区', category:'餐饮', tags:['海鲜', '粤菜'], color:'#3E8E41' },
  { id:'s079', name:'大墨蒲公英', floor:2, zone:'7区', category:'亲子', tags:['儿童绘画', '美术'], color:'#E8809E' },
  { id:'s080', name:'菁英之伽', floor:2, zone:'7区', category:'娱乐', tags:['瑜伽', '健身'], color:'#9B7BD4' },
  { id:'s081', name:'招商银行', floor:2, zone:'7区', category:'生活服务', tags:['银行', '金融'], color:'#4A90D9' },
  { id:'s082', name:'健身房', floor:2, zone:'7区', category:'娱乐', tags:['健身', '器械'], color:'#9B7BD4' },
  { id:'s083', name:'东方好艺考', floor:2, zone:'7区', category:'亲子', tags:['艺考', '培训'], color:'#E8809E' },
  { id:'s084', name:'POP兔', floor:2, zone:'7区', category:'亲子', tags:['早教', '托育'], color:'#E8809E' },
  { id:'s085', name:'音乐教室', floor:2, zone:'7区', category:'亲子', tags:['音乐', '培训'], color:'#E8809E' },
  { id:'s086', name:'南京银行', floor:2, zone:'7区', category:'生活服务', tags:['银行', '金融'], color:'#4A90D9' },
  { id:'s087', name:'诚之书院', floor:2, zone:'7区', category:'亲子', tags:['书院', '国学'], color:'#E8809E' },
  { id:'s088', name:'嘻戏英语', floor:2, zone:'7区', category:'亲子', tags:['英语', '培训'], color:'#E8809E' },
  { id:'s089', name:'沪小胖', floor:3, zone:'7区', category:'餐饮', tags:['小龙虾', '夜宵'], color:'#E60012' },
  { id:'s090', name:'SFC上影影城', floor:3, zone:'7区', category:'娱乐', tags:['影院', '电影'], color:'#C4923A' },
]

const CAT_INTRO = {"餐饮": "汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。", "零售": "精选好物与品牌，打造舒适惬意的购物体验。", "生活服务": "贴心周到的生活服务，便捷周边日常所需。", "亲子": "亲子同乐的成长空间，陪伴孩子快乐探索世界。", "娱乐": "潮流娱乐聚场，释放精彩的昼夜生活。"}
const HOURS = {"餐饮": "10:00 - 22:00", "零售": "10:00 - 22:00", "生活服务": "10:00 - 21:00", "亲子": "10:00 - 21:00", "娱乐": "10:00 - 22:00"}
const HOURS_SPECIAL = {"生活服务,银行": "09:00 - 17:00", "娱乐,KTV": "18:00 - 02:00", "娱乐,棋牌": "10:00 - 24:00"}
const FEATURES = {"餐饮": ["可堂食", "外卖配送", "支持扫码点单"], "零售": ["线上线下同价", "支持退换", "会员积分"], "生活服务": ["专业服务", "可预约"], "亲子": ["亲子友好", "可免费体验"], "娱乐": ["可预约", "适合聚会"]}
const COUPON = {"餐饮": [50, 10], "零售": [200, 30], "生活服务": [0, 5], "亲子": [100, 20], "娱乐": [0, 30]}
const CAT_COLOR = {"餐饮": "#C4923A", "零售": "#4A90D9", "生活服务": "#3E8E41", "亲子": "#E8809E", "娱乐": "#9B7BD4"}
const PHONE = '021-5656 8888'
const EXPIRE = '2026-12-31'

function build(s) {
  const c = s.color || CAT_COLOR[s.category]
  const hours = HOURS_SPECIAL[s.category + ',' + s.tags[0]] || HOURS[s.category]
  const [cond, amt] = COUPON[s.category]
  const desc = `${s.name}位于海江新天地${s.zone} ${s.floor}F，主营${s.tags[0]}、${s.tags.length>1?s.tags[s.tags.length-1]:s.tags[0]}。${CAT_INTRO[s.category]}`
  return {
    ...s, color: c, hours, phone: PHONE, desc, description: desc,
    has_coupon: 1, coupon_condition: cond, coupon_amount: amt, coupon_expire: EXPIRE,
    features: FEATURES[s.category],
  }
}

const shops = raw.map(build)
export default shops
