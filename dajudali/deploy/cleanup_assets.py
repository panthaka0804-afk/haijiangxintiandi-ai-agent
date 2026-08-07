#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理 static/vue/assets 中的孤儿构建文件（多轮 vite build 残留的旧哈希分块）。

原理：
  Vite 路由级懒加载分块不会出现在 index.html 中，而是被入口 chunk 动态 import() 引用。
  因此不能用「index.html 没引用的就删」这种简单规则——会误删正在使用的分块。
  本脚本从 index.html 出发，递归跟随：
    - <script src> / <link href> / <link modulepreload>
    - JS 中的 import('...') 与 import '...' / from '...'
    - CSS 中的 @import 与 url(...)
  计算「真正会被用到的文件」闭包，之外的才是孤儿。

默认 dry-run（只打印将要删除的文件），加 --apply 才真正删除。
"""
import os
import re
import sys

# 自动定位 dajudali 目录（脚本放在 deploy/ 下）
HERE = os.path.dirname(os.path.abspath(__file__))
CANDIDATES = [
    os.path.join(HERE, ".."),                       # deploy/.. -> dajudali
    os.path.dirname(HERE),
    os.getcwd(),
]
STATIC_VUE = None
for c in CANDIDATES:
    p = os.path.join(c, "static", "vue")
    if os.path.isfile(os.path.join(p, "index.html")):
        STATIC_VUE = p
        break

if STATIC_VUE is None:
    print("找不到 static/vue/index.html，请在 dajudali 目录下运行，或用 --dir 指定。")
    sys.exit(1)

ASSETS_DIR = os.path.normpath(os.path.join(STATIC_VUE, "assets"))
INDEX_HTML = os.path.normpath(os.path.join(STATIC_VUE, "index.html"))

# 提取 HTML 中 /vue/assets/xxx 引用
HTML_REF = re.compile(r'(?:src|href)=["\'](/vue/assets/[^"\']+)["\']')
# JS: import(`x`) / import('x') / import "x" / from 'x'（Vite 动态导入用反引号模板字符串）
JS_IMPORT = re.compile(r'''import\s*\(\s*[`"']([^`"']+)[`"']\s*\)|(?:import|from)\s+[`"']([^`"']+)[`"']''')
# CSS: url(x) / @import 'x'
CSS_URL = re.compile(r'''url\(\s*[`"']?([^`"\'()\s]+)[`"']?\s*\)|@import\s+[`"']([^`"']+)[`"']''')


def resolve(spec, base_file):
    """把引用解析为 assets 目录下的绝对路径；无法解析返回 None。"""
    if spec.startswith("/vue/assets/"):
        rel = spec[len("/vue/assets/"):]
        return os.path.join(ASSETS_DIR, rel)
    if spec.startswith("./") or spec.startswith("../"):
        return os.path.normpath(os.path.join(os.path.dirname(base_file), spec))
    if spec.startswith("/"):
        return None
    # 裸相对名
    return os.path.normpath(os.path.join(os.path.dirname(base_file), spec))


def main():
    apply = "--apply" in sys.argv

    needed = set()
    queue = []

    # 1) 种子：index.html 直接引用
    html = open(INDEX_HTML, encoding="utf-8").read()
    for m in HTML_REF.findall(html):
        path = resolve(m, INDEX_HTML)
        if path and path not in needed and os.path.isfile(path):
            needed.add(path)
            queue.append(path)

    # 2) 闭包：递归跟随 JS/CSS 引用
    seen_in_queue = set(queue)
    while queue:
        f = queue.pop()
        try:
            text = open(f, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        if f.endswith(".css"):
            specs = CSS_URL.findall(text)
            specs = [s[0] or s[1] for s in specs]
        else:
            specs = [a or b for a, b in JS_IMPORT.findall(text)]
        for spec in specs:
            # 跳过明显非本地资源（http/ data/ 绝对外链）
            if spec.startswith(("http:", "https:", "data:", "//")):
                continue
            path = resolve(spec, f)
            if path and os.path.isfile(path) and path not in needed:
                needed.add(path)
                if path not in seen_in_queue:
                    seen_in_queue.add(path)
                    queue.append(path)

    # 3) 找出孤儿
    all_assets = []
    for fn in os.listdir(ASSETS_DIR):
        full = os.path.normpath(os.path.join(ASSETS_DIR, fn))
        if os.path.isfile(full):
            all_assets.append(full)

    orphans = [a for a in all_assets if a not in needed]
    orphans.sort()

    print(f"index.html 位置 : {INDEX_HTML}")
    print(f"assets 目录     : {ASSETS_DIR}")
    print(f"保留（在用）    : {len(needed)} 个文件")
    print(f"孤儿（可删）    : {len(orphans)} 个文件")
    print("-" * 60)
    for o in orphans:
        print("  " + os.path.basename(o))

    if not orphans:
        print("没有孤儿文件，无需清理。")
        return

    if not apply:
        print("-" * 60)
        print("【DRY-RUN】以上文件将被删除。确认无误后执行：")
        print(f"  python {os.path.basename(__file__)} --apply")
        return

    # 4) 真正删除
    deleted = 0
    for o in orphans:
        try:
            os.remove(o)
            deleted += 1
        except Exception as e:
            print(f"  删除失败 {os.path.basename(o)}: {e}")
    print("-" * 60)
    print(f"已删除 {deleted} 个孤儿文件。")


if __name__ == "__main__":
    main()
