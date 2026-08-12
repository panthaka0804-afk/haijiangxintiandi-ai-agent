# -*- coding: utf-8 -*-
"""
区域/品类检索 回归测试清单（验收用）
==================================
验证 server.py 的 shop_search / _parse_zone / shop_block_build 在以下场景下的行为：
  1) 字母区 <-> 数字区 别名互查（A区==1区、F区==6区、E区==5区、C区==3区、B区==2区）
  2) 各区域品类过滤（F区餐饮/火锅、3区火锅、B区火锅、7区亲子、6区宠物…）
  3) 各楼层检索（1楼/2楼/3楼）
  4) 已知缺口（裸 B1/F1、区域+楼层组合）—— 标记为 gap，不计入失败

【运行方式】把本文件放到服务器 /opt/dajudali/ 下（与 server.py、dajudali.db 同目录），然后：
    cd /opt/dajudali && source venv/bin/activate && python3 regression_zone_category.py
退出码 0 = 全部非缺口用例通过；非 0 = 存在真实回归。

【已知缺口（已修复，现为正式验收用例）】
  - 裸 "B1"/"F1"（不带"区"字）现已识别为标准区 2 / 6。
  - "F区1楼" 这类 区域+楼层 组合，现已同时按区域与楼层过滤。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import server  # noqa: E402

# 标准数字区 -> 库中实际 zone 取值集合（别名归并后的合法 zone）
_ZONE_SETS = {
    '1': {'1区', 'A区', 'A1', 'A3', '安信财富中心A区'},
    '2': {'B1'},
    '3': {'3区', 'C区'},
    '4': {'4区'},
    '5': {'E1', 'E区'},
    '6': {'6区', 'F1', 'F区'},
    '7': {'7区'},
}

# 每个用例：
#   q        用户输入
#   zval     期望 _parse_zone 返回的标准数字区（'1'-'7'，或 None）
#   fval     期望 _parse_zone 返回的楼层数字（字符串，或 None）
#   min_n    期望返回商户数下限（>0 即可用此字段）
#   eq_n     期望返回商户数精确值（二选一）
#   zones    若给定，要求返回记录 zone 全部落在该标准区集合内
#   has_cats 期望返回记录至少包含这些品类
#   gap      标记为已知缺口（不计入失败，仅告警）
CASES = [
    # ---- 字母区 <-> 数字区 别名互查 ----
    dict(id='A区==1区', q='A区有什么吃的', zval='1', min_n=1, zones='1'),
    dict(id='1区==A区', q='1区有什么吃的', zval='1', min_n=1, zones='1'),
    dict(id='F区==6区', q='F区有什么吃的', zval='6', min_n=1, zones='6'),
    dict(id='6区==F区', q='6区有什么吃的', zval='6', min_n=1, zones='6'),
    dict(id='E区==5区', q='E区有什么吃的', zval='5', min_n=1, zones='5'),
    dict(id='5区==E区', q='5区有什么吃的', zval='5', min_n=1, zones='5'),
    dict(id='C区==3区', q='C区有什么吃的', zval='3', min_n=1, zones='3'),
    dict(id='3区==C区', q='3区有什么吃的', zval='3', min_n=1, zones='3'),
    dict(id='B区==2区', q='B区有什么吃的', zval='2', min_n=1, zones='2'),
    dict(id='2区==B区', q='2区有什么吃的', zval='2', min_n=1, zones='2'),

    # ---- 区域 + 品类 过滤 ----
    dict(id='A区/1区 咖啡', q='A区咖啡', zval='1', min_n=1, zones='1', has_cats={'茶饮咖啡', '餐饮'}),
    dict(id='1区 咖啡', q='1区咖啡', zval='1', min_n=1, zones='1', has_cats={'茶饮咖啡', '餐饮'}),
    dict(id='F区 餐饮', q='F区餐饮', zval='6', min_n=1, zones='6', has_cats={'餐饮'}),
    dict(id='F区 火锅(无串串->餐饮兜底)', q='F区火锅', zval='6', min_n=1, zones='6', has_cats={'餐饮'}),
    dict(id='3区 火锅(原漏答修复点)', q='3区火锅', zval='3', min_n=1, zones='3', has_cats={'餐饮'}),
    dict(id='E区 烧烤', q='E区烧烤', zval='5', min_n=1, zones='5', has_cats={'烧烤夜宵酒馆日料'}),
    dict(id='7区 亲子', q='7区亲子', zval='7', min_n=1, zones='7', has_cats={'亲子'}),
    dict(id='6区 宠物', q='6区宠物', zval='6', min_n=1, zones='6', has_cats={'宠物'}),
    dict(id='B区 火锅', q='B区火锅', zval='2', min_n=1, zones='2', has_cats={'火锅串串'}),
    dict(id='C区 餐饮', q='C区餐饮', zval='3', min_n=1, zones='3', has_cats={'餐饮'}),

    # ---- 各楼层检索 ----
    dict(id='1楼', q='1楼有什么', fval='1', min_n=1),
    dict(id='2楼', q='2楼有什么', fval='2', min_n=1),
    dict(id='3楼', q='3楼有什么', fval='3', min_n=1),

    # ---- 缺口修复后已转为正式验收 ----
    dict(id='裸B1不带区字', q='B1有什么吃的', zval='2', min_n=1, zones='2'),
    dict(id='区域+楼层组合 F区1楼', q='F区1楼有什么', zval='6', fval='1', min_n=1, zones='6'),
    dict(id='不存在的8区', q='8区有什么', zval=None, fval=None, eq_n=0),
]


def check(case):
    q = case['q']
    rows = server.shop_search(q)
    zv, fv = server._parse_zone(q)
    problems = []

    # zval / fval 解析校验
    if case.get('zval') is not None and zv != case['zval']:
        problems.append(f"解析zval期望 {case['zval']} 实际 {zv}")
    if case.get('fval') is not None and fv != case['fval']:
        problems.append(f"解析fval期望 {case['fval']} 实际 {fv}")

    # 数量校验
    if 'eq_n' in case:
        if len(rows) != case['eq_n']:
            problems.append(f"数量期望 =={case['eq_n']} 实际 {len(rows)}")
    if 'min_n' in case:
        if len(rows) < case['min_n']:
            problems.append(f"数量期望 >={case['min_n']} 实际 {len(rows)}")

    # zone 集合校验（返回记录必须全部落在该标准区）
    if case.get('zones'):
        allowed = _ZONE_SETS[case['zones']]
        bad = sorted({r.get('zone') for r in rows if (r.get('zone') or '') not in allowed})
        if bad:
            problems.append(f"跨区域污染，出现非本区zone: {bad}")

    # 品类校验（至少含其一）
    if case.get('has_cats'):
        got = {r['category'] for r in rows}
        if not (case['has_cats'] & got):
            problems.append(f"缺少期望品类 {sorted(case['has_cats'])}，实际 {sorted(got)}")

    return rows, problems


def main():
    passed, failed, gaps = [], [], []
    for case in CASES:
        rows, problems = check(case)
        if problems:
            if case.get('gap'):
                gaps.append((case, problems))
            else:
                failed.append((case, problems))
        else:
            passed.append(case['id'])

    print("=" * 64)
    print("区域/品类检索 回归测试")
    print("=" * 64)
    for cid in passed:
        print(f"  PASS  {cid}")
    for case, problems in failed:
        print(f"  FAIL  {case['id']}: {'; '.join(problems)}")
    for case, problems in gaps:
        print(f"  GAP   {case['id']}: {'; '.join(problems)}  | {case.get('note','')}")
    print("-" * 64)
    print(f"通过 {len(passed)} / 失败 {len(failed)} / 已知缺口 {len(gaps)}")

    if failed:
        print("存在真实回归，请修复后再验收。")
        return 1
    print("非缺口用例全部通过 ✓")
    return 0


if __name__ == '__main__':
    sys.exit(main())
