import sqlite3
conn = sqlite3.connect('dajudali.db')

parking_kb = [
    ('停车', '停车怎么收费',
     '海江新天地停车场：10元/小时，30分钟内免费。会员折扣：普卡98折、银卡95折、金卡9折、钻石卡88折。积分可抵停车费，100积分=1元。',
     '停车费,停车怎么收费,停车多少钱', 10),
    ('停车', '怎么找我的车',
     '发送"找车位"或按底部按钮，输入车牌号即可查询车辆停放区域（如B2-G区），系统会生成步行导航路线。',
     '找车,反向寻车,我的车在哪,车辆定位', 10),
    ('停车', '停车怎么缴费',
     '发送"停车缴费"或按"找车位"按钮，输入手机号或车牌号即可查询费用。会员自动匹配折扣，支持积分抵扣，确认后一键支付。',
     '停车缴费,停车支付,交停车费,停车结算', 10),
    ('停车', '停车费可以积分抵扣吗',
     '可以！停车缴费时最多可用50%会员积分抵扣，100积分=1元。例如停车费20元，最多用1000积分抵10元，实付10元。',
     '积分抵停车费,停车积分,积分抵扣停车', 8),
]

for cat, q, a, kw, pri in parking_kb:
    conn.execute(
        'INSERT INTO knowledge_base (tenant_id, category, question, answer, keywords, priority, status) VALUES (?,?,?,?,?,?,?)',
        (1, cat, q, a, kw, pri, 'active')
    )
conn.commit()
conn.close()
print('done')
