# -*- coding: utf-8 -*-
"""
海江新天地 · 拼团发券商家补充脚本
依据 add_merchants_kb.py 知识库里的真实商户（M 列表），从已落库 shops 中
匹配出 shop_id，批量补入拼团活动（group_buys 表）。

设计原则：
  - 拼团商家全部来自知识库真实商户，shop_name/优惠/面额对应其实际团购数据；
  - 覆盖多业态（火锅/烧烤/茶饮/甜品/娱乐/亲子/零售），不堆砌单一品类；
  - 幂等：按 (shop_name, title) 去重，重复执行只跳过不新增；
  - 仅写入状态为 'open' 的拼团，不影响已 'full'/'closed' 的历史记录。

用法：
  python add_group_buys.py            # 默认操作 DB_PATH (dajudali.db)
  DB_PATH=/path/to/db python add_group_buys.py
"""
import os
import re
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get('DB_PATH', os.path.join(HERE, 'dajudali.db'))

# 复用知识库结构化商户数据
import add_merchants_kb as kb
M = kb.M

EXP_DEFAULT = '2026-12-31'

# 已知在 shops 表里已有"标准名"拼团的知识库商家（去掉门店括号后名），跳过其全名条目避免重复成团。
# 例：朱光玉火锅馆(海江新天地店) → shops 标准名"朱光玉火锅"(s040) 已有拼团。
SKIP_DUP = {
    '朱光玉火锅馆(海江新天地店)',
}


def norm_name(name):
    """与 add_merchants_shops_offers 一致：去掉末尾门店括号用于匹配标准名。"""
    return re.sub(r'[（(][^（）()]*[）)]\s*$', '', name).strip()


def extract_deal(txt):
    """从优惠文案中提取满减/代金：满A减B → (A,B)；A代B → (A, B-A)。"""
    m = re.search(r'满(\d+)减(\d+)', txt)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r'(\d+)代(\d+)', txt)
    if m:
        return int(m.group(1)), int(m.group(2)) - int(m.group(1))
    return 0, 0


# ------------------------------------------------------------------ 拼团蓝图
# 形态一：满减团（按各店真实满减/代金设计）
# 形态二：代金团购（用平台代金券面额，need_count 小一点）
# 每个条目：(知识库商户名, 拼团主题, 券文案, 券面额, 成团人数)
PLANS = [
    # 火锅串串（社交拼团首选）—— 朱光玉火锅已有标准名 s040 的拼团，此处直接复用，不再新增
    # ('朱光玉火锅馆(海江新天地店)', ...) 见下方 SKIP_DUP 跳过，避免与 s040 重复成团
    ('開縣徐妈串串火锅馆(海江新天地店)', '徐妈串串火锅 4 人拼团·满减券', '满150减40 代金券', 40, 4),
    ('潮汕草根·鲜牛肉·海鲜火锅排档(海江新天地店)', '潮汕草根牛肉火锅 4 人拼团·代金券', '168元3人套餐代金50', 50, 4),
    ('鱼石尚云南蒸汽石锅鱼(海江新天地店)', '鱼石尚石锅鱼 3 人拼团·代金券', '138元双人鱼锅代金40', 40, 3),
    # 烧烤夜宵酒馆
    ('阿国烤局·东北烧烤•小龙虾(海江新天地店)', '阿国烤局烧烤 4 人拼团·套餐券', '98元双人烧烤套餐代金30', 30, 4),
    ('暴走牛牛碳火烤肉(海江新天地店)', '暴走牛牛烤肉 4 人拼团·代金券', '109元双人和牛套餐代金40', 40, 4),
    ('刘栋梁大排档·小龙虾·江湖菜(海江新天地店)', '刘栋梁大排档 3 人拼团·代金券', '192元小龙虾双人餐代金40', 40, 3),
    ('沪小胖·小龙虾(宝山特许经营店)', '沪小胖小龙虾 3 人拼团·代金券', '138元3斤小龙虾代金40', 40, 3),
    # 茶饮咖啡（高频、低门槛、易成团）
    ('瑞幸咖啡(海江新天地店)', '瑞幸咖啡 2 人拼团·饮品券', '9.9元美式/生椰饮品券', 9, 2),
    ('霸王茶姬(海江新天地店)', '霸王茶姬 3 人拼团·饮品券', '9.9元伯牙绝弦单品券', 9, 3),
    ('星巴克(上海海江新天地店)', '星巴克 3 人拼团·下午茶券', '68元双人下午茶代金20', 20, 3),
    ('Manner Coffee(海江新天地店)', 'Manner Coffee 2 人拼团·咖啡券', '9.9元超大杯美式券', 9, 2),
    ('SilverFlow 银流咖啡(海江路店)', '银流咖啡 3 人拼团·咖啡券', '12.9元招牌咖啡代金10', 10, 3),
    # 甜品烘焙（轻决策、凑单）
    ('多乐之日(海江新天地店)', '多乐之日 3 人拼团·烘焙券', '19.9元蛋糕面包组合代金15', 15, 3),
    # 休闲娱乐（多人场景天然适合拼团）
    ('SFC上影国际影城(海江新天地店)', 'SFC影城 3 人拼团·电影券', '45元双人电影票代金20', 20, 3),
    ('魅影梦空间KTV', '魅影梦空间KTV 5 人拼团·欢唱券', '29.9元白天3小时欢唱代金20', 20, 5),
    ('锦光星耀桌球俱乐部', '锦光星耀桌球 2 人拼团·畅打券', '19.9元2小时桌球代金15', 15, 2),
    ('哇咔美式铁馆(海江新天地店)', '哇咔美式铁馆 2 人拼团·周卡券', '19.9元7天周卡代金15', 15, 2),
    ('合一瑜伽馆·蹦极·普拉提', '合一瑜伽 3 人拼团·体验券', '9.9元小班瑜伽课代金8', 8, 3),
    # 亲子 / 教育体验
    ('POP兔音乐教室·架子鼓·吉他·声乐', 'POP兔音乐教室 3 人拼团·体验券', '9.9元4节乐器体验课代金8', 8, 3),
    ('舞林园舞蹈', '舞林园舞蹈 3 人拼团·体验券', '19.9元3节舞蹈体验课代金15', 15, 3),
    ('誠之書院·书法写字篆刻', '誠之書院 3 人拼团·试听券', '6.9元硬笔/软笔试听代金5', 5, 3),
    # 康养美容（闺蜜拼团）
    ('康友四季(海江新天地店)', '康友四季 3 人拼团·足疗券', '69元60分钟足疗代金30', 30, 3),
    ('头道汤头疗养生馆·壹美兰心', '头道汤头疗 2 人拼团·头疗券', '59元头疗养护代金20', 20, 2),
    # 宠物（养宠邻居拼团）
    ('功夫宠·狗狗寄养·宠物训练', '功夫宠 2 人拼团·洗护券', '39.9元宠物洗护代金20', 20, 2),
    # 零售便利（高频刚需）
    ('全家便利店(牡丹江路5店)', '全家便利店 2 人拼团·代金券', '满30减6 代金券', 6, 2),
]


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # 现有 shops 名 → id
    existing = {r['name']: r['id'] for r in c.execute("SELECT id,name FROM shops")}
    # 现有拼团去重集合
    existing_gb = set((r['shop_name'], r['title'])
                      for r in c.execute("SELECT shop_name,title FROM group_buys"))

    ins = skip = 0
    unmatched = []
    skipped_dup = 0
    for kb_name, title, label, amount, need in PLANS:
        if kb_name in SKIP_DUP:
            skipped_dup += 1
            skip += 1
            continue
        nn = norm_name(kb_name)
        sid = existing.get(nn) or existing.get(kb_name)
        if not sid:
            unmatched.append(kb_name)
            skip += 1
            continue
        # 用 shops 标准名（可能与知识库名略有差异，如去掉门店括号）
        shop_name = existing.get(nn) and nn or kb_name
        # 优先用标准名
        final_name = nn if nn in existing else kb_name
        if (final_name, title) in existing_gb:
            skip += 1
            continue
        c.execute(
            "INSERT INTO group_buys (shop_id,shop_name,title,coupon_label,coupon_amount,need_count,expire_at,status) "
            "VALUES (?,?,?,?,?,?,?,'open')",
            (sid, final_name, title, label, amount, need, EXP_DEFAULT)
        )
        existing_gb.add((final_name, title))
        ins += 1

    conn.commit()
    conn.close()
    print('inserted=%d skipped=%d (未匹配 %d, 跳过重名 %d)' % (ins, skip, len(unmatched), skipped_dup))
    if unmatched:
        print('未匹配知识库名的商家：', unmatched)


if __name__ == '__main__':
    main()
