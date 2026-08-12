# -*- coding: utf-8 -*-
"""
海江新天地 · 全商户信息汇总 → 后台知识库(knowledge_base) 落库脚本
来源：运营提供的《旭惠·海江新天地（原安信商业广场）全商户信息汇总》
规则：
  - 每个商户一条记录，category='merchant'，question=商户全称
  - answer 保留：类别/位置/营业时间/人均/榜单特色/各平台优惠(逐条)
  - keywords 含：简称、品类、平台(美团/抖音/大众点评/携程)、位置关键词
  - 商场通用全域优惠单独 category='mall'
幂等：按 (tenant_id,category,question) 去重，存在则更新
"""
import sqlite3
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, 'dajudali.db')

# ---------------------------------------------------------------- 商户数据
# 字段: name, cat, area, hours, percap, tags, note, coupons[(平台, 内容)]
M = []

# 一、住宿类
M.append(dict(name='网鱼电竞酒店(上海宝山宝杨路地铁站店)', cat='住宿',
    area='商场E区2楼E2-12室（商场内门店）', hours='24小时', percap='80-150元',
    tags='电竞酒店,住宿,钟点房', note='',
    coupons=[('携程','39.9元（3小时钟点房）、118元起（过夜电竞房），新客立减15元（该钟点房套餐仅携程售卖，美团/大众点评无此特价）'),
             ('抖音','138元双人通宵电竞套餐（含饮品），过期可退')]))

# 二、茶饮咖啡类
M.append(dict(name='瑞幸咖啡(海江新天地店)', cat='茶饮咖啡',
    area='海江新天地', hours='07:00-22:30', percap='14元',
    tags='咖啡,茶饮,快取', note='',
    coupons=[('美团','9.9元美式/生椰'),('抖音','9.9元通用券'),('大众点评','每日9.9元特价饮品')]))
M.append(dict(name='星巴克(上海海江新天地店)', cat='茶饮咖啡',
    area='牡丹江路1238号-B区-106室', hours='06:30-22:00', percap='40元',
    tags='咖啡,茶饮', note='',
    coupons=[('大众点评','90代100星享囤券'),('抖音','68元双人下午茶'),('美团','外卖满30减8')]))
M.append(dict(name='霸王茶姬(海江新天地店)', cat='茶饮咖啡',
    area='牡丹江路1258号1层A1-06室', hours='07:30-23:00', percap='17元',
    tags='茶饮,奶茶', note='',
    coupons=[('抖音','9.9元伯牙绝弦单品'),('美团','15元双人饮品券'),('大众点评','开业囤券第二杯半价')]))
M.append(dict(name='Manner Coffee(海江新天地店)', cat='茶饮咖啡',
    area='牡丹江路1255号F区1层03-1号商铺', hours='08:00-17:00', percap='16元',
    tags='咖啡,茶饮', note='',
    coupons=[('美团','9.9元美式'),('抖音','12元拿铁+迷你蛋糕组合套餐')]))
M.append(dict(name='miiix coffee(安信财富中心店)', cat='茶饮咖啡',
    area='宝山区牡丹江路105-2', hours='05:30-17:30', percap='18元',
    tags='咖啡,茶饮', note='',
    coupons=[('美团','16元购20元代金券；9.9元超大杯美式；9.9元超大杯冰茶5选1；12.9元开心果维也纳咖啡'),
             ('抖音','同款饮品9.9元引流单品，无大额代金券套餐')]))
M.append(dict(name='SilverFlow 银流咖啡(海江路店)', cat='茶饮咖啡',
    area='牡丹江路1258号旭惠海江新天地', hours='06:30-18:30', percap='17元',
    tags='咖啡,茶饮', note='',
    coupons=[('美团','12.9元招牌咖啡6选1；12.9元Kiri联名轻酪拿铁3选1；20元两款馅料贝果'),
             ('抖音','13.9元咖啡贝果单人套餐')]))

# 三、快餐简餐
M.append(dict(name='小杨生煎(海江新天地店)', cat='快餐简餐',
    area='牡丹江路1258号', hours='06:30-22:00', percap='27元',
    tags='生煎,快餐,小吃', note='',
    coupons=[('抖音','19.9元单人餐（生煎+鸭血粉丝）'),('美团','25代30代金券')]))
M.append(dict(name='麦当劳(牡丹江路店)', cat='快餐简餐',
    area='牡丹江路1258号', hours='06:30-23:00', percap='26元',
    tags='快餐,汉堡', note='',
    coupons=[('美团','12.9元1+1随心配'),('抖音','39.9元双人正餐套餐'),('大众点评','6.9元起早餐单品')]))
M.append(dict(name='SUBWAY赛百味(海江新天地店)', cat='快餐简餐',
    area='牡丹江路1255号F-102', hours='07:30-21:00', percap='26元',
    tags='三明治,快餐', note='',
    coupons=[('抖音','19.9元单人三明治套餐'),('美团','22代30代金券')]))
M.append(dict(name='福海面馆(牡丹江路海江新天地店)', cat='快餐简餐',
    area='牡丹江路1233号E区E-15', hours='07:30-20:30', percap='34元',
    tags='面馆,本帮面,快餐', note='宝山面馆热门榜第1',
    coupons=[('抖音','18.8元单人招牌面'),('美团','68元双人吃面套餐')]))
M.append(dict(name='小扬春（海江新天地店）蟹黄小汤包&小渔市', cat='快餐简餐',
    area='海江新天地', hours='08:00-21:00', percap='35元',
    tags='汤包,小渔市,快餐', note='',
    coupons=[('大众点评','29.9元单人汤包套餐'),('抖音','98元4人聚餐套餐')]))
M.append(dict(name='Popeyes炸鸡·汉堡·奶昔(海江新天地店)', cat='快餐简餐',
    area='牡丹江路1255号', hours='10:00-23:00', percap='31元',
    tags='炸鸡,汉堡,快餐', note='',
    coupons=[('美团','19元【买一送一】大嘴鸡排堡；满20减5、满80减9神券'),
             ('抖音','直播单人升级套餐14.9元，同款买一送一堡21元')]))
M.append(dict(name='猪角·中国猪脚饭(上海旭惠海江新天地店)', cat='快餐简餐',
    area='牡丹江路1258号A1—032', hours='10:30-20:00', percap='28元',
    tags='猪脚饭,快餐', note='',
    coupons=[('美团','22.8元购25元代金券；19.9元双倍隆江猪脚饭套餐；15.9元五香鸡腿饭拼鸡排'),
             ('抖音','单人猪脚饭16.9元')]))
M.append(dict(name='阿跷锅贴·本帮面(海江新天地店)', cat='快餐简餐',
    area='牡丹江路1233号A1-12室', hours='06:00-22:00', percap='19元',
    tags='锅贴,本帮面,快餐', note='',
    coupons=[('美团','35.8元购45元代金券；7.59元招牌锅贴单品'),
             ('抖音','双人锅贴套餐26.9元')]))
M.append(dict(name='老盛兴·上海小笼汤包馆(海江新天地店)', cat='快餐简餐',
    area='牡丹江路1258号', hours='06:00-21:00', percap='30元',
    tags='小笼,汤包,快餐', note='',
    coupons=[('美团','26.5元购30元代金券；20.9元汤包小馄饨套餐；33.9元现炒拌面单人餐'),
             ('抖音','小笼单人套餐17.9元')]))

# 四、正餐特色餐饮
# （一）火锅/串串
M.append(dict(name='開縣徐妈串串火锅馆(海江新天地店)', cat='火锅串串',
    area='海江新天地', hours='10:00-凌晨2:00', percap='75元',
    tags='串串,火锅,夜宵', note='',
    coupons=[('抖音','9.9代100代金券（酒水、锅底不可用）'),('美团','128元双人串串套餐'),('大众点评','198元4人全餐')]))
M.append(dict(name='鱼石尚云南蒸汽石锅鱼(海江新天地店)', cat='火锅串串',
    area='海江新天地', hours='10:30-22:00', percap='90元',
    tags='石锅鱼,火锅,云南菜', note='',
    coupons=[('抖音','138元双人鱼锅套餐'),('美团','28代50代金券')]))
M.append(dict(name='潮汕草根·鲜牛肉·海鲜火锅排档(海江新天地店)', cat='火锅串串',
    area='海江新天地', hours='11:00-凌晨1:00', percap='110元',
    tags='牛肉火锅,海鲜火锅,排档', note='',
    coupons=[('抖音','168元3人鲜切牛肉套餐'),('大众点评','午市到店78折（无线上团购券，线下核销优惠）')]))
M.append(dict(name='朱光玉火锅馆(海江新天地店)', cat='火锅串串',
    area='牡丹江路1238号1层B1-15室', hours='11:00-22:00', percap='100元',
    tags='火锅,正餐', note='',
    coupons=[('美团','141元工作日200元代金券；148.8元毕业季200元代金券；买单满100减13'),
             ('抖音','双人火锅套餐168元，200元代金券145元')]))
# （二）湘菜/江湖菜
M.append(dict(name='筱灶湘·鲜炒乡里土菜(海江新天地店)', cat='湘菜江湖菜',
    area='海江新天地', hours='10:00-21:30', percap='65元',
    tags='湘菜,土菜,正餐', note='',
    coupons=[('抖音','88元双人湘菜套餐'),('美团','35代50代金券'),('线下','新店打卡送酸梅汤（线下活动，无线上券）')]))
M.append(dict(name='戴海川美蛙鲜鱼馆(宝山店)', cat='湘菜江湖菜',
    area='宝山', hours='10:30-23:00', percap='85元',
    tags='美蛙,鱼,江湖菜,正餐', note='',
    coupons=[('抖音','99元双人美蛙锅'),('美团','168元4人全餐套餐')]))
M.append(dict(name='肖记公安牛肉&鱼杂(海江新天地店)', cat='湘菜江湖菜',
    area='海江新天地', hours='10:00-22:30', percap='78元',
    tags='牛肉,鱼杂,湖北菜,正餐', note='',
    coupons=[('抖音','108元双人牛肉锅套餐'),('大众点评','满150减30平台通用餐饮券')]))
# （三）江浙/本帮/徽菜
M.append(dict(name='故事徽(海江新天地店)', cat='江浙本帮徽菜',
    area='海江新天地', hours='10:00-21:00', percap='82元',
    tags='徽菜,正餐', note='',
    coupons=[('抖音','128元3人徽菜套餐'),('美团','50代100代金券')]))
M.append(dict(name='伴月楼·新海派菜·江浙菜(海江新天地店)', cat='江浙本帮徽菜',
    area='海江新天地', hours='10:30-21:30', percap='105元',
    tags='本帮菜,江浙菜,海派菜,正餐', note='',
    coupons=[('抖音','168元4人家宴套餐'),('大众点评','午市78折（线下到店优惠）')]))
M.append(dict(name='新鸳鸯精菜馆', cat='江浙本帮徽菜',
    area='牡丹江路1233号E区三层301室', hours='无固定营业时间', percap='114元',
    tags='本帮菜,精菜馆,正餐', note='',
    coupons=[('抖音','368元6人松叶蟹全席（含包间使用权）'),('美团','200代300大额代金券')]))
# （四）烧烤/夜宵/酒馆/日料
M.append(dict(name='阿国烤局·东北烧烤•小龙虾(海江新天地店)', cat='烧烤夜宵酒馆日料',
    area='海江新天地', hours='16:30-凌晨3:00', percap='88元',
    tags='烧烤,小龙虾,夜宵', note='',
    coupons=[('抖音','98元双人烧烤套餐；99元3斤小龙虾单品')]))
M.append(dict(name='民谣星烧烤酒馆(宝山店)', cat='烧烤夜宵酒馆日料',
    area='牡丹江路1233号E-01室', hours='17:30-次日03:00', percap='91元',
    tags='烧烤,酒馆,夜宵', note='宝山酒吧销量榜第1',
    coupons=[('抖音','128元3-4人酸菜鱼烧烤套餐'),('美团','酒水买一送一券')]))
M.append(dict(name='沪小胖·小龙虾(宝山特许经营店)', cat='烧烤夜宵酒馆日料',
    area='牡丹江路1255号F座3楼', hours='11:00-次日02:00', percap='155元',
    tags='小龙虾,夜宵,海鲜', note='宝山小龙虾热门榜第1',
    coupons=[('抖音','138元3斤小龙虾套餐'),('大众点评','夜宵满200减50平台券')]))
M.append(dict(name='哥哥の深夜食堂(海江新天地店)', cat='烧烤夜宵酒馆日料',
    area='牡丹江路1233号E1-04', hours='17:00-次日02:00', percap='98元',
    tags='日料,深夜食堂,夜宵', note='宝山日料口味榜第3',
    coupons=[('抖音','108元双人日料夜宵套餐'),('美团','39.9元单人寿喜烧套餐')]))
M.append(dict(name='成都你六姐·牛肉冒菜·麻辣香锅', cat='烧烤夜宵酒馆日料',
    area='海江新天地', hours='10:30-21:30', percap='41元',
    tags='冒菜,麻辣香锅,川菜', note='',
    coupons=[('抖音','19.9元单人冒菜'),('美团','25代30代金券')]))
M.append(dict(name='暴走牛牛碳火烤肉(海江新天地店)', cat='烧烤夜宵酒馆日料',
    area='牡丹江路1233号', hours='11:00-23:00', percap='81元',
    tags='烤肉,碳火烤肉,正餐', note='',
    coupons=[('美团','79元购100元代金券；109元双人和牛套餐；259元四人牛肉套餐'),
             ('抖音','双人烤肉套餐115元，100元代金券82元')]))
M.append(dict(name='刘栋梁大排档·小龙虾·江湖菜(海江新天地店)', cat='烧烤夜宵酒馆日料',
    area='牡丹江路1238号', hours='16:00-02:00', percap='106元',
    tags='大排档,小龙虾,江湖菜,夜宵', note='',
    coupons=[('美团','83.7元午市双人餐；192元小龙虾双人餐；买单满100减5'),
             ('抖音','直播138元小龙虾双人套餐，100元代金券76元')]))
M.append(dict(name='新贝乐意大利餐厅·窑炉披萨(海江新天地店)', cat='烧烤夜宵酒馆日料',
    area='牡丹江路1258号A1-09', hours='10:00-21:00', percap='80元',
    tags='意大利菜,披萨,西餐', note='',
    coupons=[('美团','59.9元购100元代金券；69.9元工作日午市单人餐'),
             ('抖音','双人意式套餐128元，100元代金券62元')]))
# （五）水产特产
M.append(dict(name='蟹玉阳澄湖(牡丹江路店)', cat='水产特产',
    area='牡丹江路', hours='10:00-22:00', percap='320元',
    tags='螃蟹,水产,特产,自提', note='仅自提外带',
    coupons=[('抖音','螃蟹礼盒8折优惠'),('美团','满200减40生鲜通用券')]))

# 五、甜品烘焙
M.append(dict(name='多乐之日(海江新天地店)', cat='甜品烘焙',
    area='牡丹江路1258号A1-03', hours='07:30-22:00', percap='37元',
    tags='烘焙,面包,蛋糕,甜品', note='仅自提',
    coupons=[('抖音','19.9元蛋糕面包组合'),('美团','30代50烘焙代金券，团购过期自动全额退款')]))

# 六、休闲娱乐
M.append(dict(name='SFC上影国际影城(海江新天地店)', cat='休闲娱乐',
    area='海江新天地', hours='09:00-凌晨1:00', percap='',
    tags='电影院,影城,娱乐', note='',
    coupons=[('抖音','45元双人电影票'),('美团','19.9元单人票（周一至周四专享）'),('大众点评','12.9元爆米花小吃套餐')]))
M.append(dict(name='魅影梦空间KTV', cat='休闲娱乐',
    area='海江新天地（8月15日新开量贩KTV）', hours='全天营业', percap='',
    tags='KTV,量贩KTV,娱乐,免费停车', note='免费停车',
    coupons=[('抖音','29.9元白天场3小时欢唱'),('美团','88元黄金档小包3小时（含酒水）')]))
M.append(dict(name='雀王棋牌俱乐部(海江路店)', cat='休闲娱乐',
    area='海江路', hours='24小时营业', percap='60元',
    tags='棋牌,娱乐', note='',
    coupons=[('抖音','39.9元4小时棋牌房'),('美团','58元棋牌+茶水套餐')]))
M.append(dict(name='匯通·棋牌室(海江新天地店)', cat='休闲娱乐',
    area='牡丹江路与栀子花路交叉口西约40米', hours='24小时', percap='64元',
    tags='棋牌,娱乐', note='宝山棋牌室销量榜第1',
    coupons=[('抖音','59.9元全天6小时棋牌'),('大众点评','夜场时段折扣（线下核销）')]))
M.append(dict(name='享隆餐饮棋牌', cat='休闲娱乐',
    area='牡丹江路1258号A区4楼401室', hours='24小时', percap='55元',
    tags='棋牌,餐饮,娱乐', note='',
    coupons=[('美团','78元棋牌+简餐全套套餐')]))
M.append(dict(name='锦光星耀桌球俱乐部', cat='休闲娱乐',
    area='海江新天地', hours='10:00-凌晨2:00', percap='35元',
    tags='桌球,台球,娱乐', note='',
    coupons=[('抖音','19.9元2小时桌球畅打'),('美团','68元通宵桌球套餐')]))
M.append(dict(name='POP兔音乐教室·架子鼓·吉他·声乐', cat='休闲娱乐',
    area='海江新天地', hours='10:00-20:00', percap='',
    tags='音乐教室,乐器培训,娱乐', note='',
    coupons=[('抖音','9.9元4节乐器体验课'),('美团','88元月度不限次练琴卡')]))
M.append(dict(name='哇咔美式铁馆(海江新天地店)', cat='休闲娱乐',
    area='牡丹江路1258号3层A3-01~05室', hours='全天24小时自助', percap='',
    tags='健身房,铁馆,运动', note='年卡均价1605元（宝山健身房销量榜第1）',
    coupons=[('抖音','19.9元7天周卡'),('美团','399元不限次季度健身卡')]))
M.append(dict(name='合一瑜伽馆·蹦极·普拉提', cat='休闲娱乐',
    area='E区二楼201-202号', hours='08:00-21:00', percap='',
    tags='瑜伽,普拉提,蹦极,运动', note='',
    coupons=[('抖音','9.9元单次小班瑜伽课'),('美团','199元月卡')]))
M.append(dict(name='菁英之伽', cat='休闲娱乐',
    area='F区二楼招行楼上', hours='10:30-21:00', percap='',
    tags='瑜伽,运动', note='宝山瑜伽好评第2',
    coupons=[('抖音','29.9元双人瑜伽体验'),('大众点评','私教课立减100元（线上预约券）')]))

# 七、教育培训
M.append(dict(name='壹品培优(安信校区)', cat='教育培训',
    area='安信校区', hours='14:00-21:00', percap='',
    tags='文化课辅导,学科培训,教育', note='暂无线上团购',
    coupons=[('线下','99元3节学科体验课')]))
M.append(dict(name='嘻戏教育(海江新天地店)', cat='教育培训',
    area='海江新天地', hours='10:00-20:30', percap='',
    tags='素质教育,少儿培训,教育', note='',
    coupons=[('抖音','9.9元少儿综合素养体验课')]))
M.append(dict(name='菁华教育·小初高辅导', cat='教育培训',
    area='牡丹江路1211号安信商业广场', hours='10:00-22:00', percap='',
    tags='小初高辅导,学科培训,教育', note='',
    coupons=[('美团','199元全科测评+2次辅导课套餐')]))
M.append(dict(name='弘文书馆(安信馆)', cat='教育培训',
    area='E区二楼208室', hours='14:30-19:30', percap='159元',
    tags='书法,书画,培训,教育', note='',
    coupons=[('抖音','9.9元4次书法体验课')]))
M.append(dict(name='誠之書院·书法写字篆刻', cat='教育培训',
    area='F区2楼211-212室', hours='08:00-22:00', percap='',
    tags='书法,写字,篆刻,培训,教育', note='宝山书法好评第2',
    coupons=[('抖音','6.9元硬笔/软笔单次试听课')]))
M.append(dict(name='舞林园舞蹈', cat='教育培训',
    area='1层F1-F12', hours='', percap='',
    tags='舞蹈,成人古典舞,培训,教育', note='',
    coupons=[('抖音','19.9元3节舞蹈体验课'),('美团','128元月度舞蹈卡')]))

# 八、康养美容生活服务
M.append(dict(name='康友四季(海江新天地店)', cat='康养美容',
    area='海江新天地', hours='全天', percap='120元',
    tags='足疗,推拿,养生', note='',
    coupons=[('抖音','69元60分钟足疗套餐'),('美团','99元全身推拿套餐')]))
M.append(dict(name='头道汤头疗养生馆·壹美兰心', cat='康养美容',
    area='牡丹江路1248号安信财富中心A区1701号', hours='09:30-19:30', percap='182元',
    tags='头疗,养生,美容', note='',
    coupons=[('抖音','59元头疗养护套餐'),('大众点评','88元肩颈疏通线上券')]))
M.append(dict(name='屿汀美容', cat='康养美容',
    area='E区2楼06-07', hours='10:00-20:30', percap='',
    tags='皮肤管理,美容', note='',
    coupons=[('抖音','39.9元清洁补水单次套餐')]))
M.append(dict(name='何和堂·儿童体质养护（小儿推拿）', cat='康养美容',
    area='F区1层13号', hours='', percap='',
    tags='小儿推拿,儿童体质养护,养生', note='',
    coupons=[('抖音','29.9元单次小儿推拿体验')]))
M.append(dict(name='功夫宠·狗狗寄养·宠物训练', cat='宠物',
    area='牡丹江路1255号F区1层', hours='09:00-21:00', percap='136元',
    tags='宠物,狗狗寄养,宠物训练', note='宝山宠物店好评榜第1',
    coupons=[('抖音','39.9元宠物洗护套餐'),('美团','寄养3天立减50元券')]))
M.append(dict(name='扑扑碗PuPuBowl宠物膳食餐厅', cat='宠物',
    area='1层F1-18-5', hours='10:00-21:00', percap='',
    tags='宠物,宠物鲜食,宠物蛋糕', note='',
    coupons=[('抖音','29.9元宠物鲜食套餐')]))

# 九、零售、便利、数码、银行配套（全部暂无线上团购）
M.append(dict(name='迪信通（数码手机）', cat='零售便利数码银行',
    area='C区一层106室', hours='09:00-22:00', percap='',
    tags='数码,手机,零售', note='评分4.8；暂无线上团购', coupons=[]))
M.append(dict(name='苏宁易购（3C家电）', cat='零售便利数码银行',
    area='牡丹江路1228号', hours='09:30-20:30', percap='',
    tags='3C,家电,零售', note='评分3.8；暂无线上团购', coupons=[]))
M.append(dict(name='全家便利店(牡丹江路5店)', cat='零售便利数码银行',
    area='1层F1-07室', hours='06:00-22:00', percap='',
    tags='便利店,零售', note='暂无线上团购', coupons=[]))
M.append(dict(name='秀目眼镜', cat='零售便利数码银行',
    area='1层A1-04室', hours='09:00-21:00', percap='',
    tags='眼镜,蔡司授权配镜,零售', note='评分4.6；暂无线上团购', coupons=[]))
M.append(dict(name='招商银行宝山支行', cat='零售便利数码银行',
    area='F区', hours='09:00-17:00', percap='',
    tags='银行,金融网点,配套', note='暂无线上团购', coupons=[]))

# 十、生鲜超市类
M.append(dict(name='澄田农场（海江新天地店）', cat='生鲜超市',
    area='牡丹江路1258号A区1楼A1-30-1室', hours='08:30-22:00', percap='',
    tags='生鲜超市,蔬果,鲜肉,水产,粮油', note='支持海鲜现场加工；每周三会员日称重生鲜（蔬菜/水果/鲜肉/水产）全场8.8折，标品不参与；无线上团购',
    coupons=[]))

# ---------------------------------------------------------------- 商场通用全域优惠
MALL = [
    dict(name='海江新天地停车优惠',
         answer="""【海江新天地 · 停车全域优惠】
· 地下700车位
· 任意商户消费小票可兑换免费停车2小时""",
         keywords='停车,免费停车,车位,停车优惠,消费小票,海江新天地'),
    dict(name='海江新天地平台通用补贴',
         answer="""【海江新天地 · 平台通用补贴（全商户通用）】
· 美团：美食每日满30减8，新客全业态立减15元
· 大众点评：商场主页5元无门槛餐饮券，每周五更新
· 抖音：商场官方账号不定期发放全场10元代金券（餐饮/娱乐可用）""",
         keywords='平台补贴,美团,大众点评,抖音,满减,代金券,通用优惠,新客立减'),
    dict(name='海江新天地团购通用规则',
         answer="""【海江新天地 · 团购通用规则】
· 绝大多数套餐未使用、过期自动全额退款
· 节假日餐饮、KTV套餐部分需补差价""",
         keywords='团购规则,退款,过期退款,补差价,退改'),
]


def build_answer(d):
    lines = [f"【商户名称】{d['name']}",
             f"【类别】{d['cat']}"]
    if d.get('area'):
        lines.append(f"【位置】{d['area']}")
    if d.get('hours'):
        lines.append(f"【营业时间】{d['hours']}")
    if d.get('percap'):
        lines.append(f"【人均】{d['percap']}")
    if d.get('note'):
        lines.append(f"【特色/备注】{d['note']}")
    coupons = d.get('coupons') or []
    if coupons:
        lines.append("【优惠】")
        for plat, txt in coupons:
            lines.append(f"· {plat}：{txt}")
    else:
        lines.append("【优惠】暂无线上团购")
    return '\n'.join(lines)


def build_keywords(d):
    kw = [d['name'], d['cat']]
    if d.get('tags'):
        kw.append(d['tags'])
    # 平台关键词
    for plat in ['美团', '抖音', '大众点评', '携程']:
        if any(c[0] == plat for c in (d.get('coupons') or [])) or plat in (d.get('note') or ''):
            kw.append(plat)
    if d.get('area'):
        # 抽取位置关键词（牡丹江路 / 区字母）
        import re
        for token in re.findall(r'(牡丹江路|安信|\w区|E区|F区|A区|B区|C区|D区|\d+层|\d+楼)', d['area']):
            kw.append(token)
    kw.append('优惠,团购,营业时间,人均,海江新天地')
    # 去重保序
    seen = set(); out = []
    for k in kw:
        for part in k.split(','):
            part = part.strip()
            if part and part not in seen:
                seen.add(part); out.append(part)
    return ','.join(out)


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM knowledge_base")
    before = c.fetchone()[0]

    ins = upd = 0
    for d in M:
        q = d['name']
        ans = build_answer(d)
        kw = build_keywords(d)
        c.execute("SELECT id FROM knowledge_base WHERE tenant_id=1 AND category='merchant' AND question=?",
                  (q,))
        row = c.fetchone()
        if row:
            c.execute("UPDATE knowledge_base SET answer=?, keywords=? WHERE id=?",
                      (ans, kw, row['id']))
            upd += 1
        else:
            c.execute("INSERT INTO knowledge_base (tenant_id,category,question,answer,keywords) VALUES (?,?,?,?,?)",
                      (1, 'merchant', q, ans, kw))
            ins += 1

    for m in MALL:
        q = m['name']
        c.execute("SELECT id FROM knowledge_base WHERE tenant_id=1 AND category='mall' AND question=?",
                  (q,))
        row = c.fetchone()
        if row:
            c.execute("UPDATE knowledge_base SET answer=?, keywords=? WHERE id=?",
                      (m['answer'], m['keywords'], row['id']))
            upd += 1
        else:
            c.execute("INSERT INTO knowledge_base (tenant_id,category,question,answer,keywords) VALUES (?,?,?,?,?)",
                      (1, 'mall', q, m['answer'], m['keywords']))
            ins += 1

    conn.commit()
    c.execute("SELECT COUNT(*) FROM knowledge_base")
    after = c.fetchone()[0]
    conn.close()
    print(f"before={before} inserted={ins} updated={upd} after={after}")


if __name__ == '__main__':
    main()
