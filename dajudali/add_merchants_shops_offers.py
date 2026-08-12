# -*- coding: utf-8 -*-
"""
海江新天地 · 全商户信息汇总 → shops / offers 落库脚本
复用 add_merchants_kb.py 中的 M(商户) 结构化数据。
规则：
  shops: 按"店名归一化(去掉末尾门店括号)"匹配现有 90 家；命中则更新(保留 id/floor/zone/color)，
         未命中则新增(前缀 mx)。has_coupon/coupon_* 由优惠推导。
  offers: 每个平台优惠逐条插入，label=[平台]内容，按 (shop_name,label) 去重。
幂等：重复执行只更新/跳过，不重复插入。
"""
import os
import re
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, 'dajudali.db')

import add_merchants_kb as kb
M = kb.M

CAT_COLOR = {
    '住宿': '#6C5CE7', '茶饮咖啡': '#0051A8', '快餐简餐': '#D52B1E',
    '火锅串串': '#E8552A', '湘菜江湖菜': '#C0392B', '江浙本帮徽菜': '#8E44AD',
    '烧烤夜宵酒馆日料': '#E67E22', '水产特产': '#16A085', '甜品烘焙': '#8B5A2B',
    '休闲娱乐': '#0984E3', '教育培训': '#00B894', '康养美容': '#FD79A8',
    '宠物': '#E17055', '零售便利数码银行': '#636E72', '生鲜超市': '#27AE60',
}
OFFER_CAT = {
    '住宿': 'service', '茶饮咖啡': 'food', '快餐简餐': 'food', '火锅串串': 'food',
    '湘菜江湖菜': 'food', '江浙本帮徽菜': 'food', '烧烤夜宵酒馆日料': 'food',
    '水产特产': 'food', '甜品烘焙': 'food', '休闲娱乐': 'entertainment',
    '教育培训': 'service', '康养美容': 'service', '宠物': 'service',
    '零售便利数码银行': 'retail', '生鲜超市': 'retail',
}
EXP_DEFAULT = '2026-12-31'


def norm_name(name):
    """去掉末尾的门店/分店括号，用于匹配现有商铺标准名。"""
    return re.sub(r'[（(][^（）()]*[）)]\s*$', '', name).strip()


def parse_area(area):
    zone = ''
    m = re.search(r'([A-F]区|[A-F]\d区?|安信财富中心[A-F]区)', area)
    if m:
        zone = m.group(1)
    floor = ''
    m = re.search(r'([1-4])层|([1-4])楼', area)
    if m:
        floor = m.group(1)
    else:
        cn = re.search(r'(三|二|四|一)楼', area)
        if cn:
            floor = {'三': '3', '二': '2', '四': '4', '一': '1'}[cn.group(1)]
    return floor, zone


def extract_deal(txt):
    m = re.search(r'满(\d+)减(\d+)', txt)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r'(\d+)代(\d+)', txt)
    if m:
        return int(m.group(1)), int(m.group(2)) - int(m.group(1))
    m = re.search(r'(\d+)购(\d+)', txt)
    if m:
        return int(m.group(1)), int(m.group(2)) - int(m.group(1))
    return 0, 0


def build_description(d):
    parts = []
    if d.get('area'):
        parts.append('位于' + d['area'])
    if d.get('note'):
        parts.append('特色：' + d['note'])
    if d.get('percap'):
        parts.append('人均' + d['percap'])
    if d.get('tags'):
        parts.append('主营' + d['tags'].replace(',', '、'))
    return '。'.join(parts) + '。' if parts else ''


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # 现有 shops 名→id 映射
    existing = {r['name']: r for r in c.execute("SELECT * FROM shops")}
    used_ids = set(existing.keys())
    # 现有 offers 去重集合
    existing_offers = set((r['shop_name'], r['label'])
                          for r in c.execute("SELECT shop_name,label FROM offers"))

    new_idx = 1
    shops_upd = shops_ins = 0
    offers_ins = 0

    for d in M:
        name = d['name']
        nn = norm_name(name)
        match = existing.get(nn) or existing.get(name)
        final_name = match['name'] if match else name
        floor, zone = parse_area(d.get('area', '') or '')
        color = CAT_COLOR.get(d['cat'], '#999999')
        coupons = d.get('coupons') or []
        cond = amt = 0
        for _, txt in coupons:
            cond, amt = extract_deal(txt)
            if cond or amt:
                break
        desc = build_description(d)

        if match:
            c.execute(
                """UPDATE shops SET category=?, tags=?, hours=?, description=?,
                   has_coupon=?, coupon_condition=?, coupon_amount=?, coupon_expire=?, features=?
                   WHERE id=?""",
                (d['cat'], d.get('tags', ''), d.get('hours', ''), desc,
                 1 if coupons else 0, cond, amt, EXP_DEFAULT, d.get('note', ''),
                 match['id']))
            shops_upd += 1
        else:
            sid = 'mx%03d' % new_idx
            new_idx += 1
            c.execute(
                """INSERT INTO shops (id,name,floor,zone,category,tags,color,hours,phone,
                   description,has_coupon,coupon_condition,coupon_amount,coupon_expire,features)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (sid, final_name, floor, zone, d['cat'], d.get('tags', ''), color,
                 d.get('hours', ''), '', desc, 1 if coupons else 0, cond, amt,
                 EXP_DEFAULT, d.get('note', '')))
            shops_ins += 1

        # offers
        for plat, txt in coupons:
            label = '[%s] %s' % (plat, txt)
            label = label[:90]
            if (final_name, label) in existing_offers:
                continue
            cond2, amt2 = extract_deal(txt)
            oc = OFFER_CAT.get(d['cat'], 'food')
            c.execute(
                """INSERT INTO offers (shop_name,label,expire,amount,category,color,status)
                   VALUES (?,?,?,?,?,?,?)""",
                (final_name, label, EXP_DEFAULT, amt2, oc, color, 'active'))
            existing_offers.add((final_name, label))
            offers_ins += 1

    conn.commit()
    conn.close()
    print('shops_updated=%d shops_inserted=%d offers_inserted=%d' % (shops_upd, shops_ins, offers_ins))


if __name__ == '__main__':
    main()
