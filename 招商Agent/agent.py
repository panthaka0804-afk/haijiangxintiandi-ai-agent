"""
商业综合体招商Agent - 核心引擎
五大模块：品牌匹配 / 落位生成 / 竞品分析 / 业态配比 / 招商看板
"""
from brands_data import BRANDS
from rules import FORMAT_RATIOS, FLOOR_RULES, COMPETITION_RULES
import json


class ZhaoShangAgent:
    def __init__(self):
        self.brands = BRANDS

    # ========== 模块1：品牌智能匹配 ==========
    def brand_match(self, city="", area="", crowd="", area_min=0, area_max=99999,
                    category="", floor="", top_n=10):
        """
        根据项目条件匹配合适品牌
        """
        results = []
        for b in self.brands:
            score = 0

            # 面积匹配
            area_parts = b["area_need"].split("-")
            b_min, b_max = int(area_parts[0]), int(area_parts[1])
            if area_min <= b_max and area_max >= b_min:
                req_area = (area_min + area_max) / 2 if area_min and area_max else (b_min + b_max) / 2
                overlap = min(b_max, area_max or b_max) - max(b_min, area_min or b_min)
                score += min(overlap / b_max * 30, 30) if b_max else 0
            else:
                continue  # 面积不匹配直接跳过

            # 品类匹配
            if category and category in b["category"] or category and category in b["subcategory"]:
                score += 25

            # 客群匹配
            if crowd:
                crowd_lower = crowd.lower()
                if "年轻" in crowd_lower and "年轻" in b["target_crowd"]:
                    score += 20
                if "家庭" in crowd_lower and "家庭" in b["target_crowd"]:
                    score += 20
                if "白领" in crowd_lower and "白领" in b["target_crowd"]:
                    score += 20
                if "高净值" in crowd_lower and "高净值" in b["target_crowd"]:
                    score += 20
                if "全客群" in b["target_crowd"]:
                    score += 10

            # 楼层匹配
            if floor:
                floors = b["floors"].replace("+", "").split("-")
                if floor in b["floors"]:
                    score += 15

            # 扩张意愿加分
            if b["expansion"] == "极活跃":
                score += 10
            elif b["expansion"] == "活跃":
                score += 8
            elif b["expansion"] == "稳定":
                score += 5

            # 城市/区域商圈（简化：品牌曝光度越高越容易谈）
            if city:
                score += 3  # 实际应根据城市匹配度加权

            results.append({
                "brand": b,
                "score": round(score, 1),
                "match_reason": self._gen_match_reason(b, city, area, crowd)
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_n]

    def _gen_match_reason(self, brand, city, area, crowd):
        reasons = []
        if crowd and crowd in brand["target_crowd"] or any(t in brand["target_crowd"] for t in (crowd or "").split()):
            reasons.append(f"目标客群匹配({brand['target_crowd']})")
        reasons.append(f"面积需求{brand['area_need']}㎡")
        reasons.append(f"{brand['expansion']}扩张")
        if brand["competitors"]:
            reasons.append(f"需注意竞品：{'、'.join(brand['competitors'])}")
        return " | ".join(reasons)

    # ========== 模块2：落位方案生成 ==========
    def generate_layout(self, project_info):
        """
        根据项目信息生成推荐的业态落位方案
        project_info = {
            "name": "项目名",
            "type": "社区型/区域型/城市级/文旅商业",
            "total_area": 80000,
            "floors": ["B1", "1F", "2F", "3F", "4F"],
            "anchor_brands": ["盒马鲜生", "万达影城"],
            "target_crowd": "年轻白领+家庭客群"
        }
        """
        ptype = project_info.get("type", "区域型")
        floors = project_info.get("floors", ["B1", "1F", "2F", "3F", "4F"])
        crowd = project_info.get("target_crowd", "")

        ratio = FORMAT_RATIOS.get(ptype, FORMAT_RATIOS["区域型"])
        total = project_info.get("total_area", 50000)

        # 为每层推荐品牌
        floor_plan = []
        for floor in floors:
            # 找适合该楼层的品牌
            candidates = []
            for b in self.brands:
                if floor in b["floors"]:
                    # 客群匹配加分
                    crowd_match = 0
                    if "全客群" in b["target_crowd"]:
                        crowd_match = 5
                    elif crowd and any(t in b["target_crowd"] for t in crowd.split("+")):
                        crowd_match = 10

                    candidates.append({
                        "name": b["name"],
                        "category": b["category"],
                        "subcategory": b["subcategory"],
                        "area_need": b["area_need"],
                        "crowd_match": crowd_match
                    })

            candidates.sort(key=lambda x: x["crowd_match"], reverse=True)
            floor_plan.append({
                "floor": floor,
                "rule": FLOOR_RULES.get(floor, "灵活配置"),
                "suggested_brands": [c["name"] for c in candidates[:8]],
                "suggested_area": f"{total//len(floors)*0.8:.0f}-{total//len(floors)*1.2:.0f}㎡"
            })

        return {
            "project": project_info.get("name", "未命名项目"),
            "type": ptype,
            "ratio_suggestion": ratio,
            "floor_plan": floor_plan,
            "rules_applied": COMPETITION_RULES
        }

    # ========== 模块3：竞品排布分析 ==========
    def competitor_analysis(self, our_brands, competitor_brands):
        """
        对比我和竞品的品牌排布
        our_brands: 我们已有的/计划的品牌列表
        competitor_brands: 竞品已有的品牌列表
        """
        our_set = set(our_brands)
        comp_set = set(competitor_brands)

        # 竞品有我们没有的
        they_have_we_dont = comp_set - our_set
        # 我们有竞品没有的
        we_have_they_dont = our_set - comp_set
        # 重合
        overlap = our_set & comp_set

        # 对 "他们有的" 进行优先级排序（按品牌重要性）
        priority_brands = []
        for brand_name in they_have_we_dont:
            for b in self.brands:
                if b["name"] == brand_name:
                    priority_brands.append({
                        "name": brand_name,
                        "category": b["category"],
                        "subcategory": b["subcategory"],
                        "expansion": b["expansion"],
                        "importance": "高" if b["expansion"] in ["极活跃", "活跃"] else "中"
                    })
                    break

        priority_brands.sort(key=lambda x: x["importance"] == "高", reverse=True)

        return {
            "overlap_count": len(overlap),
            "overlap_brands": list(overlap),
            "overlap_rate": f"{len(overlap)/max(len(our_brands),1)*100:.0f}%",
            "they_have_we_dont": [b["name"] for b in priority_brands],
            "we_have_they_dont": list(we_have_they_dont),
            "differentiation_index": f"{len(we_have_they_dont)/max(len(our_brands),1)*100:.0f}%",
            "suggested_action": self._comp_action(priority_brands, overlap)
        }

    def _comp_action(self, priority_brands, overlap):
        if len(priority_brands) > 5:
            return "竞品品牌矩阵明显优于你们，建议优先引入前5个必抢品牌"
        elif len(overlap) > len(priority_brands):
            return "品牌重合度高，需加强差异化，建议发展自有特色品牌组合"
        else:
            return "品牌结构相对健康，继续巩固优势品类"

    # ========== 模块4：业态配比分析 ==========
    def format_analysis(self, current_brands):
        """
        分析当前品牌组合的业态配比是否合理
        current_brands: 当前已确定/在谈的品牌名列表
        """
        stats = {"零售": [], "餐饮": [], "体验": [], "主力店": []}
        total = 0

        for brand_name in current_brands:
            for b in self.brands:
                if b["name"] == brand_name:
                    cat = b["category"]
                    if cat in stats:
                        stats[cat].append(brand_name)
                    else:
                        stats["体验"].append(brand_name)
                    total += 1
                    break

        result = {}
        for cat, brands in stats.items():
            result[cat] = {
                "count": len(brands),
                "ratio": f"{len(brands)/max(total,1)*100:.0f}%",
                "brands": brands
            }

        # 诊断
        diagnosis = []
        retail_pct = stats["零售"][0] if isinstance(stats["零售"], list) else len(stats["零售"]) / max(total, 1)
        dining_pct = len(stats["餐饮"]) / max(total, 1)
        exp_pct = len(stats["体验"]) / max(total, 1)
        anchor_pct = len(stats["主力店"]) / max(total, 1)

        if dining_pct < 0.2:
            diagnosis.append("[!] 餐饮占比偏低（<20%），建议增加餐饮品牌以提升客流吸引力")
        if exp_pct < 0.1:
            diagnosis.append("[!] 体验业态不足（<10%），在现代商业中体验是核心增长极")
        if anchor_pct == 0 and total > 10:
            diagnosis.append("[!] 缺少主力店，建议引入超市/影院等带客流的锚点品牌")

        result["diagnosis"] = diagnosis if diagnosis else ["[OK] 业态配比基本合理"]
        result["total_brands"] = total

        return result

    # ========== 模块5：招商进度看板 ==========
    def progress_dashboard(self, project_name, total_slots, signed, in_talks, vacant):
        """
        生成招商进度看板
        """
        total = total_slots
        signed_pct = signed / total * 100 if total else 0
        in_talks_pct = in_talks / total * 100 if total else 0
        vacant_pct = vacant / total * 100 if total else 0

        status = "(OK) 健康" if signed_pct > 40 else ("(!) 需关注" if signed_pct > 20 else "(!!) 预警")

        return {
            "project": project_name,
            "status": status,
            "overview": {
                "总铺位数": total,
                "已签约": f"{signed} ({signed_pct:.0f}%)",
                "洽谈中": f"{in_talks} ({in_talks_pct:.0f}%)",
                "空置": f"{vacant} ({vacant_pct:.0f}%)"
            },
            "alert": "[!] 有铺位空置超3个月，建议调业态或降租金" if vacant_pct > 30 else "暂无预警"
        }


# ========== 命令行交互界面 ==========
def main():
    agent = ZhaoShangAgent()

    print("=" * 60)
    print("🏬 商业综合体招商落位AI Agent v1.0")
    print("=" * 60)
    print("五大功能模块：")
    print("  1. 品牌智能匹配")
    print("  2. 落位方案生成")
    print("  3. 竞品排布分析")
    print("  4. 业态配比诊断")
    print("  5. 招商进度看板")
    print("=" * 60)

    while True:
        print("\n请选择功能（输入数字1-5，输入q退出）：")
        choice = input("> ").strip()

        if choice == "q":
            print("再见，领导！")
            break
        elif choice == "1":
            print("\n--- 品牌智能匹配 ---")
            city = input("城市（如成都）：").strip()
            area = input("需求面积范围（如200-400）：").strip()
            crowd = input("目标客群（年轻白领/家庭客群/全客群）：").strip()
            category = input("品类偏好（餐饮/零售/体验/主力店，回车跳过）：").strip()
            floor = input("楼层（如1F，回车跳过）：").strip()

            try:
                parts = area.split("-")
                a_min, a_max = int(parts[0]), int(parts[1]) if len(parts) > 1 else int(parts[0])
            except:
                a_min, a_max = 0, 99999

            results = agent.brand_match(city=city, area=area, crowd=crowd,
                                        area_min=a_min, area_max=a_max,
                                        category=category, floor=floor, top_n=10)
            print(f"\n📊 匹配结果（共{len(results)}个）：")
            for i, r in enumerate(results, 1):
                b = r["brand"]
                print(f"\n  {i}. {b['name']} | {b['category']}/{b['subcategory']} | 评分:{r['score']}")
                print(f"     面积需求:{b['area_need']}㎡ | 租金承受:{b['avg_rent_bear']}")
                print(f"     {r['match_reason']}")

        elif choice == "2":
            print("\n--- 落位方案生成 ---")
            name = input("项目名称：").strip()
            ptype = input("项目类型（社区型/区域型/城市级/文旅商业）：").strip()
            area = input("总建筑面积（㎡）：").strip()
            floors_str = input("楼层列表（逗号分隔，如B1,1F,2F,3F,4F）：").strip()
            crowd = input("目标客群：").strip()

            floors = [f.strip() for f in floors_str.split(",")] if floors_str else ["B1", "1F", "2F", "3F", "4F"]

            layout = agent.generate_layout({
                "name": name,
                "type": ptype,
                "total_area": int(area) if area.isdigit() else 50000,
                "floors": floors,
                "target_crowd": crowd
            })

            print(f"\n🏗️ {layout['project']} 业态配比建议：")
            ratio = layout["ratio_suggestion"]
            print(f"  零售: {ratio['retail']} | 餐饮: {ratio['dining']} | 体验: {ratio['experience']} | 主力店: {ratio['anchor']}")
            print(f"\n  各楼层落位方案：")
            for fp in layout["floor_plan"]:
                print(f"\n  📍 {fp['floor']} | 面积约{fp['suggested_area']}")
                print(f"     定位: {fp['rule']}")
                print(f"     推荐品牌: {', '.join(fp['suggested_brands'][:5])}")

        elif choice == "3":
            print("\n--- 竞品排布分析 ---")
            our = input("我方品牌（逗号分隔）：").strip()
            comp = input("竞品品牌（逗号分隔）：").strip()
            our_list = [b.strip() for b in our.split(",")] if our else []
            comp_list = [b.strip() for b in comp.split(",")] if comp else []
            analysis = agent.competitor_analysis(our_list, comp_list)
            print(f"\n📊 竞品分析结果：")
            print(f"  品牌重合度: {analysis['overlap_rate']}（{analysis['overlap_count']}个）")
            print(f"  竞品有我们没有的: {', '.join(analysis['they_have_we_dont'][:10])}")
            print(f"  我们有竞品没有的: {', '.join(analysis['we_have_they_dont'])}")
            print(f"  差异化指数: {analysis['differentiation_index']}")
            print(f"  💡 建议: {analysis['suggested_action']}")

        elif choice == "4":
            print("\n--- 业态配比诊断 ---")
            brands_str = input("已确认/在谈品牌（逗号分隔）：").strip()
            brands = [b.strip() for b in brands_str.split(",")] if brands_str else []
            analysis = agent.format_analysis(brands)
            print(f"\n📊 业态配比分析（共{analysis['total_brands']}个品牌）：")
            for cat, info in analysis.items():
                if cat not in ["diagnosis", "total_brands"]:
                    print(f"  {cat}: {info['ratio']}（{info['count']}个）")
            print(f"\n  诊断：")
            for d in analysis.get("diagnosis", []):
                print(f"  {d}")

        elif choice == "5":
            print("\n--- 招商进度看板 ---")
            name = input("项目名称：").strip()
            total = int(input("总铺位数：").strip() or "100")
            signed = int(input("已签约数：").strip() or "0")
            talks = int(input("洽谈中：").strip() or "0")
            vacant = total - signed - talks
            board = agent.progress_dashboard(name, total, signed, talks, vacant)
            print(f"\n📊 {board['project']} 招商看板")
            print(f"  状态: {board['status']}")
            for k, v in board["overview"].items():
                print(f"  {k}: {v}")
            print(f"  {board['alert']}")

        else:
            print("输入有误，请输入1-5或q")


if __name__ == "__main__":
    main()
