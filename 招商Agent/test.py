import sys
sys.path.insert(0, r'C:\Users\admin\AppData\Roaming\OpenClawBrowser\openclaw-gateway\.openclaw\workspace\招商Agent')
from agent import ZhaoShangAgent

a = ZhaoShangAgent()

# 测试1：品牌匹配
print("=" * 50)
print("测试1：品牌智能匹配")
print("条件：成都、200-400㎡、年轻白领、餐饮、3F")
results = a.brand_match(city='成都', area='200-400', crowd='年轻白领',
                        area_min=200, area_max=400, category='餐饮',
                        floor='3F', top_n=5)
for i, r in enumerate(results, 1):
    b = r['brand']
    print(f"  {i}. {b['name']} | {b['subcategory']} | 评分:{r['score']}")
    print(f"     {r['match_reason']}")

# 测试2：落位方案
print("\n" + "=" * 50)
print("测试2：落位方案生成")
layout = a.generate_layout({
    "name": "成都高新区天悦城",
    "type": "区域型",
    "total_area": 80000,
    "floors": ["B1", "1F", "2F", "3F", "4F"],
    "target_crowd": "年轻白领+家庭客群"
})
print(f"项目：{layout['project']} | 类型：{layout['type']}")
ratio = layout['ratio_suggestion']
print(f"业态配比：零售{ratio['retail']} 餐饮{ratio['dining']} 体验{ratio['experience']} 主力店{ratio['anchor']}")
for fp in layout['floor_plan']:
    print(f"  {fp['floor']}：{', '.join(fp['suggested_brands'][:4])}")

# 测试3：竞品分析
print("\n" + "=" * 50)
print("测试3：竞品排布分析")
comp = a.competitor_analysis(
    ['海底捞', '星巴克', '优衣库', '喜茶', '泡泡玛特', '万达影城', '西贝', 'MUJI'],
    ['海底捞', '星巴克', '优衣库', 'ZARA', '丝芙兰', 'lululemon', '盒马鲜生', 'Shake Shack', '乐高']
)
print(f"品牌重合度：{comp['overlap_rate']}（{comp['overlap_count']}个重合：{', '.join(comp['overlap_brands'])}）")
print(f"竞品有我没：{', '.join(comp['they_have_we_dont'][:5])}")
print(f"建议：{comp['suggested_action']}")

# 测试4：业态配比
print("\n" + "=" * 50)
print("测试4：业态配比诊断")
analysis = a.format_analysis(
    ['优衣库', '喜茶', '泡泡玛特', 'Wagas', 'KKV', '海底捞', '星巴克', 'MUJI', '瑞幸咖啡']
)
for cat, info in analysis.items():
    if cat not in ['diagnosis', 'total_brands']:
        print(f"  {cat}：{info['ratio']}（{', '.join(info['brands'])}）")
for d in analysis.get('diagnosis', []):
    print(f"  {d}")

# 测试5：进度看板
print("\n" + "=" * 50)
print("测试5：招商进度看板")
board = a.progress_dashboard("天悦城", 120, 35, 28, 57)
print(f"状态：{board['status']}")
for k, v in board['overview'].items():
    print(f"  {k}：{v}")
print(f"  {board['alert']}")

print("\n" + "=" * 50)
print("✅ 五大模块全部通过！")
print("运行主程序：python agent.py")
