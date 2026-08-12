# -*- coding: utf-8 -*-
"""海江新天地系统 - 社区商业AI客服"""
import os, sys, json, sqlite3, hashlib, secrets, re, time, io, base64, subprocess, tempfile
from datetime import datetime, timedelta
from functools import wraps
import fcntl  # 跨进程文件锁，防止 gunicorn 多 worker 并发初始化抢 SQLite 写锁
from flask import Flask, request, session, jsonify, send_from_directory, Response
from openai import OpenAI
import floor_data

# 平台扩展配置层：业态/渠道/AI provider/知识库引擎 的集中配置与扩展点
from biz_platform import CATEGORY_ALIASES as _CATEGORY_ALIASES, ZONE_CANON as _ZONE_CANON, CHANNELS, AI_PROVIDERS, KB_ENGINE

HERE = os.path.dirname(os.path.abspath(__file__))

# Load .env file if present
_env_path = os.path.join(HERE, '.env')
if os.path.isfile(_env_path):
    with open(_env_path, 'r', encoding='utf-8') as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _v = _line.split('=', 1)
                os.environ.setdefault(_k.strip(), _v.strip())

app = Flask(__name__)
app.secret_key = os.environ.get('DJDL_SECRET_KEY', 'dajudali-2026-secret-key-v1')
DB_PATH = os.path.join(HERE, 'dajudali.db')
DS_API_KEY = os.environ.get('DS_API_KEY', '')
import subprocess as _sp

# AI 服务健康状态（故障降级 + /api/health 健康检查用）
AI_HEALTH = {'status': 'up', 'fail_count': 0, 'last_fail': None, 'last_check': None}

def _call_deepseek(messages, max_tokens=300):
    """用 curl 调 DeepSeek（绕过 Python SSL 问题）"""
    global AI_HEALTH
    import tempfile
    payload = json.dumps({
        'model': 'deepseek-chat',
        'messages': messages,
        'max_tokens': max_tokens,
        'temperature': 0.6
    }, ensure_ascii=False)
    # 用临时文件传参，避免命令行过长
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
    tmp.write(payload)
    tmp.close()
    try:
        result = _sp.run([
            'curl', '-s', '--max-time', '8', '--connect-timeout', '4',
            'https://api.deepseek.com/chat/completions',
            '-H', 'Content-Type: application/json',
            '-H', 'Authorization: Bearer ' + DS_API_KEY,
            '-d', '@' + tmp.name
        ], capture_output=True, text=True, timeout=15)
        resp = json.loads(result.stdout)
        if 'choices' in resp:
            AI_HEALTH['status'] = 'up'
            AI_HEALTH['fail_count'] = 0
            AI_HEALTH['last_fail'] = None
            AI_HEALTH['last_check'] = datetime.now().isoformat()
            return True, resp['choices'][0]['message']['content']
        AI_HEALTH['status'] = 'down'
        AI_HEALTH['fail_count'] += 1
        AI_HEALTH['last_fail'] = datetime.now().isoformat()
        AI_HEALTH['last_check'] = AI_HEALTH['last_fail']
        return False, resp.get('error', {}).get('message', str(resp))
    except Exception as e:
        AI_HEALTH['status'] = 'down'
        AI_HEALTH['fail_count'] += 1
        AI_HEALTH['last_fail'] = datetime.now().isoformat()
        AI_HEALTH['last_check'] = AI_HEALTH['last_fail']
        return False, str(e)
    finally:
        try: os.unlink(tmp.name)
        except: pass


def ai_chat(messages, max_tokens=300, capability='llm'):
    """AI 能力统一入口（扩展点）
    - 当前默认走 DeepSeek（capability='llm'）。
    - 【预留扩展】后续接入 AI 数字人 / 智能推荐等进阶能力时，
      在此按 capability 路由到对应 provider（见 biz_platform.AI_PROVIDERS），
      无需改动 _do_chat 等上层业务代码。
    """
    # 未来示例：
    # if capability == 'avatar':     return _call_digital_human(messages, ...)
    # if capability == 'recommend':  return _call_recommend_engine(messages, ...)
    return _call_deepseek(messages, max_tokens=max_tokens)

# 用 curl wrapper 替代 OpenAI 客户端
import httpx
httpx_client = httpx.Client(
    http2=False,
    timeout=10.0,
    follow_redirects=True,
    verify=False
)
ds_client = OpenAI(api_key=DS_API_KEY, base_url='https://api.deepseek.com', http_client=httpx_client)

# 通义千问 fallback (阿里云服务器上优先，走内网更快)
QWEN_API_KEY = os.environ.get('QWEN_API_KEY', '') or DS_API_KEY

# ========== DB ==========
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # 多进程容灾：WAL 模式 + 忙等待，避免 gunicorn 多 worker 并发写锁库
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=5000')
        conn.execute('PRAGMA synchronous=NORMAL')
    except Exception:
        pass
    return conn

# ========== Auth ==========
def login_required(f):
    @wraps(f)
    def d(*a,**k):
        if not session.get('user_id'):
            return jsonify(ok=False, error='Please login'), 401
        return f(*a,**k)
    return d

def admin_required(f):
    @wraps(f)
    def d(*a,**k):
        if not session.get('user_id'):
            return jsonify(ok=False, error='Please login'), 401
        if session.get('role') not in ('tenant_admin','super_admin'):
            return jsonify(ok=False, error='Permission denied'), 403
        return f(*a,**k)
    return d

def super_admin_required(f):
    @wraps(f)
    def d(*a,**k):
        if not session.get('user_id'):
            return jsonify(ok=False, error='Please login'), 401
        if session.get('role') != 'super_admin':
            return jsonify(ok=False, error='Permission denied'), 403
        return f(*a,**k)
    return d

# ========== AI ==========
SYSTEM_PROMPT = '''你是海江新天地社区商业中心的客服小江。自称小江。

【人设】可爱活泼的邻家小姐姐，热情有温度。先接情绪再给干货。语气自然有烟火气，不模板化。适当用"嗯嗯""嘿嘿""好嘞"。回复简短，简单问题一句话就够。不确定就诚实说"这个我不太确定，帮你记下来问问~"。严禁编造任何店铺名称/品牌/价格/菜单/营业时间。严禁用Markdown。严禁提"AI"字眼。

【算价/优惠】逐条列出可用优惠，推荐最优方案给到手价。格式：【方案】→【逐项算价】→【省多少】→【最优建议】。退款/投诉/安全立即升级工单。

【积分/兑换】优先推荐性价比最高的兑换（价值÷积分最大）。可兑换：1停车券500分 2海江食集券800分 3瑞幸咖啡券1000分 4SFC电影票2000分 5朱光玉火锅券3000分 6泡泡米体验课5000分 7华为30元券8000分 8购物卡10000分 9哇咔健身周卡15000分。"确认兑换N"→告知已记录请小程序操作。

【会员】有手机号就查，没注册就说"回复我要注册即可开通，送500积分"。绝不回复"去服务台"。

【检索导航】找优惠/找活动/找店铺/找商品/导航——代码已本地处理，AI只需友好回复检索结果。

你是海江新天地最暖心的小江~'''

CHAT_HISTORY = {}
CHAT_ROUNDS = {}  # {chat_key: round_count}  老年用户转人工: 轮次计数
MAX_HISTORY = 20
MAX_SESSIONS = 500
CHAT_HISTORY_FILE = os.path.join(HERE, 'chat_history.json')

# 启动时加载持久化的聊天历史
def _load_chat_history():
    global CHAT_HISTORY
    try:
        if os.path.exists(CHAT_HISTORY_FILE):
            with open(CHAT_HISTORY_FILE, 'r', encoding='utf-8') as f:
                raw = json.load(f)
                # 只保留最近 500 个会话，每个会话只保留最近 MAX_HISTORY*2 条
                trimmed = {}
                count = 0
                for k, v in sorted(raw.items(), key=lambda x: len(x[1]), reverse=True):
                    if count >= MAX_SESSIONS:
                        break
                    trimmed[k] = v[-MAX_HISTORY*2:]
                    count += 1
                CHAT_HISTORY = trimmed
                print(f'[CHAT] Loaded {len(CHAT_HISTORY)} sessions from disk')
    except Exception as e:
        print(f'[CHAT] Load error: {e}')
        CHAT_HISTORY = {}

def _save_chat_history():
    """异步写入（best effort，不影响性能）"""
    try:
        import threading
        # 深拷贝当前状态避免并发问题
        snapshot = {}
        for k in list(CHAT_HISTORY.keys()):
            snapshot[k] = list(CHAT_HISTORY[k])
        # 限制最多 MAX_SESSIONS 个会话
        if len(snapshot) > MAX_SESSIONS:
            keys_sorted = sorted(snapshot.keys(), key=lambda x: len(snapshot[x]))
            snapshot = {k: snapshot[k] for k in keys_sorted[-MAX_SESSIONS:]}
        def _write():
            try:
                with open(CHAT_HISTORY_FILE, 'w', encoding='utf-8') as f:
                    json.dump(snapshot, f, ensure_ascii=False)
            except:
                pass
        t = threading.Thread(target=_write, daemon=True)
        t.start()
    except:
        pass

_load_chat_history()

def kb_search(tenant_id, query, limit=5):
    conn = get_db()
    rows = conn.execute(
        "SELECT id, category, question, answer, keywords FROM knowledge_base WHERE tenant_id=? ORDER BY id",
        (tenant_id,)
    ).fetchall()
    conn.close()
    if not rows:
        return []
    q = query.lower()
    scored = []
    for r in rows:
        score = 0
        kw = (r['keywords'] or '').lower()
        ans = (r['answer'] or '').lower()
        quest = (r['question'] or '').lower()
        text = kw + ' ' + ans + ' ' + quest
        for w in q.split():
            if w in text:
                score += 10
        for i in range(len(q)-1):
            if q[i:i+2] in text:
                score += 1
        if score > 0:
            scored.append((score, dict(r)))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [s[1] for s in scored[:limit]]

def _add_kb_pending(tenant_id, question, source='chat'):
    """未命中问题自动归集到知识库待优化列表"""
    try:
        q = (question or '').strip()
        if not q or len(q) < 4:
            return
        conn = get_db()
        _ensure_tables(conn)
        # 去重：相同问题已存在则不重复归集
        exists = conn.execute(
            "SELECT id FROM kb_pending WHERE question=? AND status='pending'",
            (q,)
        ).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO kb_pending (tenant_id, question, source, status) VALUES (?,?,?,?)",
                (tenant_id, q, source, 'pending')
            )
            conn.commit()
        conn.close()
    except Exception:
        pass

# ===== 真实商户检索（基于 shops 表，支持 区域/楼层 + 品类 精准过滤） =====
# 品类关键词 -> shops.category 映射 已迁移至 biz_platform.py（顶部 import，新增业态只需改 biz_platform.py）
# 区域字母<->数字 别名映射：A↔1、B↔2、C↔3、D↔4、E↔5、F↔6，7区独立
# 库里 zone 命名混乱(1区/A区/A1/A3/安信财富中心A区 并存)，全部归一到标准数字区
_LETTER_TO_NUM = {'a':'1','b':'2','c':'3','d':'4','e':'5','f':'6'}
_NUM_TO_LETTER = {'1':'A','2':'B','3':'C','4':'D','5':'E','6':'F'}

def _zone_display(canon):
    """标准数字区 -> 可展示的区域名（含字母别名），如 '1' -> 'A区/1区'"""
    names = [canon + '区']
    letter = _NUM_TO_LETTER.get(canon)
    if letter:
        names.append(letter + '区')
    return '/'.join(names)

def _parse_zone(q):
    """从用户问题提取区域/楼层，返回 (zval, fval)。
    zval 为标准数字区('1'-'7')或 None；fval 为楼层数字或 None。
    区域与楼层可同时识别（如「F区1楼」）。"""
    ql = q.lower()
    zval = None
    fval = None
    # 1) 字母区优先（A区/F区...）
    for letter, num in _LETTER_TO_NUM.items():
        if letter + '区' in ql:
            zval = num
            break
    # 2) 裸 B1 / F1（不带"区"字，仍指向标准区 2 / 6；放在数字区之前避免被楼层误判）
    if zval is None:
        if 'b1' in ql and 'b区' not in ql:
            zval = '2'
        elif 'f1' in ql and 'f区' not in ql:
            zval = '6'
    # 3) 数字区（1区..7区），用"区"字限定避免与楼层"1楼"混淆
    if zval is None:
        m = re.search(r'([1-7])区', q)
        if m:
            zval = m.group(1)
    # 4) 楼层（1楼/一楼/二楼...）
    m = re.search(r'[一二三四五六七八九十\d]楼', q)
    if m:
        cn = {'一':'1','二':'2','三':'3','四':'4','五':'5','六':'6','七':'7','八':'8','九':'9','十':'10'}
        ch = m.group(0)[0]
        fval = cn.get(ch, ch) if ch in cn else ch
    return zval, fval

def shop_search(query):
    """识别区域/品类意图，查 shops 表返回真实商户清单。无命中返回 []。"""
    q = query.lower()
    # 1) 识别品类
    cats = set()
    for kw, clist in _CATEGORY_ALIASES.items():
        if kw in q:
            cats.update(clist)
    # 2) 识别区域/楼层（字母区与数字区别名互查，并归一到标准数字区）
    zval, fval = _parse_zone(query)
    if not cats and not zval and not fval:
        return []  # 既不是找品类也不是找区域/楼层，不触发商户检索
    conn = get_db()
    try:
        sql = "SELECT name, floor, zone, category, hours, description FROM shops WHERE 1=1"
        params = []
        if cats:
            ph = ','.join('?' * len(cats))
            sql += f" AND category IN ({ph})"
            params.extend(cats)
        if zval:
            # 把该标准数字区下所有别名 zone（如 A区/1区/A1/A3/安信财富中心A区）都查出来
            targets = [z for z, c in _ZONE_CANON.items() if c == zval]
            if targets:
                ph = ','.join('?' * len(targets))
                sql += f" AND zone IN ({ph})"
                params.extend(targets)
            else:
                # 标准区但库里无任何对应 zone（理论不会触发），用数字区兜底
                sql += " AND zone LIKE ?"
                params.append(f'%{zval}%')
        if fval:
            sql += " AND floor LIKE ?"
            params.append(f'%{fval}%')
        sql += " ORDER BY CAST(floor AS INTEGER), zone, name"
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()
    if not rows:
        return []
    return [dict(r) for r in rows]

def shop_block_build(query):
    """生成商户检索注入文本（用于 prompt）。无命中返回空字符串。"""
    rows = shop_search(query)
    if not rows:
        return ''
    zval, fval = _parse_zone(query)
    zone_label = _zone_display(zval) if zval else ''
    floor_label = (fval + '楼') if fval else ''
    scope_label = '/'.join(x for x in (floor_label, zone_label) if x)
    zone_hint = ''
    if zone_label:
        zone_hint = (f'\n（系统在「{zone_label}」收录以下真实商户——字母区与数字区为同一区域，'
                     f'例如问"A区"或"1区"都会返回这里的内容）')
    lines = [f'\n【真实商户检索结果{("· " + scope_label) if scope_label else ""}】'
             f'以下为系统中真实在册商户，必须基于它回答，严禁编造其他店铺：{zone_hint}']
    for r in rows:
        desc = (r.get('description') or '').strip()
        hours = (r.get('hours') or '').strip()
        floor = (r.get('floor') or '').strip()
        # 展示时把 zone 归一到标准"字母区/数字区"写法，避免库里 A1/A3 等混乱写法
        canon = _ZONE_CANON.get((r.get('zone') or '').strip())
        zone_disp = _zone_display(canon) if canon else ((r.get('zone') or '').strip())
        loc = ''
        if floor:
            loc += f'{floor}楼'
        if zone_disp:
            loc += zone_disp
        loc = loc or '位置未标注'
        extra = ''
        if desc:
            extra += f'（{desc}）'
        if hours:
            extra += f' 营业时间：{hours}'
        lines.append(f"- {loc}｜{r['name']}｜品类：{r['category']}{extra}")
    lines.append('若用户问"某区/某楼有什么吃的/玩的"，请只列出上面属于该品类且位于该区域的商户；若上面没有符合的，如实告知该区域暂无此类商户。')
    # 如果查询涉及餐饮，附加排队信息
    food_keywords = ['吃','美食','餐饮','火锅','烧烤','排队','取号','订餐','订位','餐厅','夜宵','晚餐','午餐','吃什么','有啥吃','好吃的']
    if any(w in query for w in food_keywords):
        is_peak, mult = _is_peak_hours()
        peak_note = f'当前为高峰时段（等位系数×{mult}），取号等候时间可能较长。' if is_peak else ''
        lines.append(f'【餐厅排队提示】用户可通过回复"取号+餐厅名"在线取号、回复"订位+餐厅名+日期+时间+人数"预约订座。{peak_note}')
    return '\n'.join(lines)

# 极速本地回复（O(1) 关键词匹配，<1ms，覆盖常见问题）
def _fast_reply(msg):
    m = msg.strip().lower()

    # 问候
    if m in ('你好','嗨','hi','hello','在吗','在不在','哈喽'):
        return '嗨！我是小江，海江新天地的客服助手~\n想找店铺、查优惠、问路、看活动，尽管问我！'

    # 情感
    if any(w in m for w in ('难受','伤心','难过','不开心','郁闷','烦','emo')):
        return '抱抱你呀~累了就来海江逛逛，吃点好的、看看热闹，心情会好很多的 💛 有什么小江能帮你的吗？'
    if any(w in m for w in ('无聊','没意思','不知道干嘛')):
        return '嘿嘿那来找小江聊天就对了！要不要看看最近有啥好玩的？亲子活动、夜校课程都挺有意思的~'
    if any(w in m for w in ('累','疲惫','困','好累')):
        return '辛苦啦！给自己放个小假嘛，来海江吃顿好的犒劳一下自己~小江觉得火锅最能治愈疲惫了！'
    if m in ('谢谢','多谢','谢谢你','谢谢啦','thanks'):
        return '不客气呀，能帮到你就好~有什么随时找小江！'
    if m in ('再见','拜拜','88','bye'):
        return '拜拜~下次来海江玩记得找小江聊天哦 👋'

    # 功能入口
    if m in ('找优惠','优惠','有什么优惠','有啥优惠','折扣'):
        return ' 找优惠·请回复数字：\n1 餐饮优惠  2 亲子优惠  3 夜校优惠  4 便民优惠'
    if m in ('找活动','活动','有什么活动','有啥活动'):
        return ' 找活动·请回复数字：\n1 亲子活动  2 老年活动  3 青年活动  4 全部活动'
    if m in ('找店铺','店铺','有什么店铺','有啥店','商家'):
        return ' 找店铺·请回复数字：\n1 火锅  2 披萨  3 咖啡  4 亲子餐厅  5 美食广场  6 教培'
    if m in ('找商品','商品','有什么商品','卖什么'):
        return ' 找商品·请回复数字：\n1 夜校课程  2 演出票务  3 零售商品'

    # 导航 — 精确匹配
    if any(w in m for w in ('在哪里','怎么走','怎么去','位置','找') or (len(m)<=6 and any(k in m for k in ('电梯','卫生间','厕所','wc','停车','服务台','地铁')))):
        pass  # 让知识库或AI处理
    if m in ('卫生间','厕所','wc','哪里有厕所','哪里有卫生间'):
        return '每层电梯厅旁边都有卫生间哦~找不到的话问问最近店铺的工作人员也行！'
    if m in ('电梯','电梯在哪里','电梯在哪'):
        return '海江新天地共有3部客梯+扶梯~大厅中央和两侧都有，很好找的！'

    # 优惠数字
    if m == '1': return ' 餐饮优惠来啦~看看知识库里有哪些好吃的在打折吧！回复"找店铺"可以浏览所有餐厅~\n（小江建议：先查会员等级再下单，积分加倍哦）'
    if m == '2': return ' 亲子优惠~带娃来海江超划算的！亲子餐厅、儿童乐园都有活动，具体看知识库里的优惠列表~'
    if m == '3': return ' 夜校优惠~海江的夜校课程又好玩又实惠，瑜伽、绘画、烘焙都有哦！'
    if m == '4': return ' 便民优惠~修鞋、洗衣、理发，日常需要都能在海江解决，还有优惠！'

    # 会员相关
    if any(w in m for w in ('注册会员','开通会员','我要注册','怎么注册','怎么加入','会员注册')):
        return '注册会员很方便的~\n1. 页面右上角点登录，微信一键授权就行\n2. 或者留一下手机号，小江帮你注册，还送500积分！'

    # 积分相关
    if any(w in m for w in ('积分','兑换','积分兑换','积分商城','积分怎么用')):
        return '积分商城可兑换：\n1停车券500分 2海江食集券800分 3瑞幸咖啡券1000分\n4SFC电影票2000分 5朱光玉火锅券3000分 6泡泡米体验课5000分\n7华为30元券8000分 8购物卡10000分 9哇咔健身周卡15000分\n\n回复"确认兑换+编号"来兑换，比如"确认兑换3"换瑞幸咖啡嘛~\n也可以点击下方按钮去积分商城 👇'

    # 营业时间
    if any(w in m for w in ('营业时间','几点开门','几点关门','营业到几点','什么时候开门')):
        return '海江新天地营业时间：周一至周日 10:00-22:00~个别商户可能稍有不同，用餐和玩都要趁早哦！'

    # 停车场
    if any(w in m for w in ('停车','停车场','车位','停车费','停车怎么收','停车收费')):
        return '海江新天地有800+智能车位~\n收费标准：\n· 前30分钟免费\n· 5元/小时，40元/天封顶\n· 会员消费满50元免费停2小时\n· 夜场18:00-次日08:00 10元/次\n\n点击下方按钮去车辆管理绑定车牌~'

    # 餐厅取号/排队
    if any(w in m for w in ('取号','排队','拿号','等位','排号','要排队','排队多久','等多久')):
        return '您想在哪家餐厅取号排队呢？告诉我餐厅名字（如"朱光玉火锅"），小江帮您取号 📋\n\n热门餐厅：朱光玉火锅、沪小胖、刘栋梁大排档、暴走牛牛·碳火烧肉、潮汕草根活鱼火锅'
    if any(w in m for w in ('排队进度','我的号','排到哪了','呼叫排队','查排队')):
        return '请回复您的手机号，小江帮您查排队进度~'

    # 餐厅预约订位
    if any(w in m for w in ('订餐','订位','预约餐厅','订座','预定','包厢','订包间','预约晚餐','预约午餐')):
        return '您想预订哪家餐厅呢？告诉我餐厅名+日期+时间+人数，如"朱光玉火锅 8月15日 晚上7点 4人"，小江帮您订位 🍽️\n\n支持预订的餐厅：朱光玉火锅、新鸳鸯、伴月楼、OX牛排、大城小野、尊柜KTV(包间)'

    # 我的预订查询
    if m in ('我的预订','预订列表','查看预订','查预订'):
        return '请回复您的手机号，小江帮您查询预订记录~'

    # 主理人/活动组织者入口
    if any(w in m for w in ('入驻申请','品牌入驻','我要入驻','怎么入驻','开店','招商','招租')):
        return '欢迎了解海江新天地入驻合作！\n📌 招商类目：特色餐饮 | 时尚零售 | 亲子娱乐 | 生活服务 | 教育培训 | 科技数码\n\n您可以："入驻申请 品牌名"，如回复"入驻申请 XXX品牌 手机号"即可提交，运营团队会尽快联系您~\n或点击下方按钮进入主理人中心 👇'
    if any(w in m for w in ('活动排期','排期报备','活动报备','场地预定','场地租赁','预定场地','租场地')):
        return '海江新天地提供多种场地：\n· 多经摊位（市集/快闪）\n· 共享教室（15-50人）\n· 会客厅/沙龙场地\n· 广告位投放\n\n回复"排期 活动名 日期 场地"即可报备，如"排期 夏日市集 8月20日 户外广场"'

    return None

def _restaurant_chat_handle(user_input):
    """处理餐厅取号/排队/预订对话意图，返回 {reply, card} 或 None"""
    m = user_input.strip().lower()
    # 取号意图: 取号 + 餐厅名
    queue_keywords = ['取号', '排队', '拿号', '等位', '排号', '要排队']
    reserve_keywords = ['订餐', '订位', '预约', '订座', '预定', '包厢']
    check_keywords = ['排队进度', '我的号', '排到哪', '查排队', '排队多久', '等多久']
    my_keywords = ['我的预订', '预订列表', '查看预订', '查预订']
    is_queue = any(w in m for w in queue_keywords)
    is_reserve = any(w in m for w in reserve_keywords)
    is_check = any(w in m for w in check_keywords)
    is_my = any(w in m for w in my_keywords)

    if not (is_queue or is_reserve or is_check or is_my):
        return None

    conn = get_db()
    _ensure_tables(conn)
    foods = conn.execute(
        "SELECT id,name,floor,zone,hours,phone FROM shops WHERE category='餐饮' ORDER BY name"
    ).fetchall()

    if is_check:
        # 查排队进度 - 需要手机号
        phone_match = re.search(r'1[3-9]\d{9}', user_input)
        if not phone_match:
            conn.close()
            return {'reply': '请回复您的手机号，小江帮您查排队进度~'}
        phone = phone_match.group(0)
        my_queues = conn.execute(
            "SELECT * FROM restaurant_queues WHERE customer_phone=? AND status='waiting' ORDER BY id DESC LIMIT 3",
            (phone,)
        ).fetchall()
        if not my_queues:
            conn.close()
            return {'reply': f'手机号 {phone} 暂无进行中的排队记录~ 回复"取号+餐厅名"开始排队吧！'}
        lines = ['您的排队进度：']
        for q in my_queues:
            ahead = conn.execute(
                "SELECT COUNT(*) FROM restaurant_queues WHERE shop_id=? AND status='waiting' AND id<?",
                (q['shop_id'], q['id'])
            ).fetchone()
            ahead_count = ahead[0] if ahead else 0
            lines.append(f'【{q["shop_name"]}】{q["party_size"]}人位 · {q["queue_number"]}号 · 前面{ahead_count}桌 · 预计{q["estimated_wait"]}分钟')
        conn.close()
        return {'reply': '\n'.join(lines)}

    # 查预订记录
    if any(w in m for w in ('我的预订', '预订列表', '查看预订', '查预订')):
        phone_match = re.search(r'1[3-9]\d{9}', user_input)
        if not phone_match:
            conn.close()
            return {'reply': '请回复您的手机号，小江帮您查询预订记录~'}
        phone = phone_match.group(0)
        reservations = conn.execute(
            "SELECT * FROM restaurant_reservations WHERE customer_phone=? ORDER BY reserve_date DESC LIMIT 10",
            (phone,)
        ).fetchall()
        conn.close()
        if not reservations:
            return {'reply': f'手机号 {phone} 暂无预订记录~'}
        items = []
        for r in reservations:
            items.append({
                'name': r['shop_name'],
                'desc': f'{r["reserve_date"]} {r["reserve_time"]} · {r["party_size"]}人',
                'tag': r['status'],
                'price': f'R{r["id"]:04d}'
            })
        card = {'title': '我的预订', 'items': items, 'footer': '到店时报预订编号即可'}
        return {'reply': f'手机号 {phone} 共有 {len(reservations)} 笔预订：', 'card': card}

    conn.close()

    # 匹配餐厅名
    matched_shop = None
    for s in foods:
        if s['name'] in user_input:
            matched_shop = s
            break
    if not matched_shop:
        # 列出可用的餐饮商户供选择
        shop_list = [f"{s['name']}（{s['zone']} {s['floor']}楼）" for s in foods[:12]]
        return {'reply': '请告诉小江您想在哪家餐厅取号/订位？\n\n' + '\n'.join(f'· {sl}' for sl in shop_list) + '\n\n回复"取号+餐厅名"或"订位+餐厅名+日期+时间+人数"即可~'}

    shop = matched_shop
    # 提取人数
    pp_match = re.search(r'(\d+)人', user_input)
    party_size = int(pp_match.group(1)) if pp_match else 2

    if is_queue:
        # 取号
        today = datetime.now().strftime('%Y-%m-%d')
        conn2 = get_db()
        _ensure_tables(conn2)
        today_count = conn2.execute(
            "SELECT COUNT(*) FROM restaurant_queues WHERE shop_id=? AND date(created_at)=?",
            (shop['id'], today)
        ).fetchone()[0]
        qnum = today_count + 1
        est = _estimate_wait(shop['id'], party_size, conn2)
        ahead = conn2.execute(
            "SELECT COUNT(*) FROM restaurant_queues WHERE shop_id=? AND status='waiting'",
            (shop['id'],)
        ).fetchone()[0]
        conn2.execute(
            "INSERT INTO restaurant_queues (shop_id,shop_name,queue_number,party_size,estimated_wait) VALUES (?,?,?,?,?)",
            (shop['id'], shop['name'], qnum, party_size, est)
        )
        conn2.commit()
        _webhook_push(shop['id'], 'new_queue_chat', {'queue_number': qnum, 'party_size': party_size, 'estimated_wait': est})
        conn2.close()
        is_peak, _ = _is_peak_hours()
        peak_note = '（当前为高峰时段，等候可能稍长）' if is_peak else ''
        reply = f'已为您在【{shop["name"]}】取号成功！\n排队号：{qnum}号\n人数：{party_size}人\n前面还有：{ahead}桌\n预计等待：{est}分钟{peak_note}\n营业时间：{shop["hours"]}\n电话：{shop["phone"]}\n\n回复"排队进度"可查询当前状态~'
        card = {
            'title': f'{shop["name"]} · 排队号',
            'items': [
                {'name': f'{qnum}号', 'desc': f'{party_size}人位 · 前面{ahead}桌', 'tag': '当前叫号', 'price': f'约{est}分钟'},
            ],
            'footer': '回复"排队进度"查询状态 | 过号需重新取号'
        }
        return {'reply': reply, 'card': card}

    if is_reserve:
        # 订位 - 尝试提取日期和时间
        date_match = re.search(r'(\d+)月(\d+)日?', user_input)
        time_match = re.search(r'(早上|中午|下午|晚上|傍晚)?(\d+)[点:：](\d+)?', user_input) or re.search(r'(\d+)[点:：](\d+)?', user_input)
        if not date_match or not time_match:
            return {'reply': f'请告诉我预约【{shop["name"]}】的具体信息~\n\n格式：订位 {shop["name"]} 月日 时间 人数\n如：订位 {shop["name"]} 8月15日 晚上7点 4人'}
        mo = date_match.group(1)
        dy = date_match.group(2)
        now_year = datetime.now().year
        reserve_date = f'{now_year}-{int(mo):02d}-{int(dy):02d}'
        # 解析时间
        hour_str = time_match.group(2) or time_match.group(1)
        minute_str = time_match.group(3) or '00'
        period = time_match.group(1) if time_match.lastindex and time_match.lastindex >= 1 else ''
        hour = int(hour_str) if hour_str and hour_str.isdigit() else 12
        if '下午' in (period or '') and hour < 12: hour += 12
        if '晚上' in (period or '') and hour < 18: hour += 12
        reserve_time = f'{hour:02d}:{int(minute_str):02d}'
        conn2 = get_db()
        _ensure_tables(conn2)
        conn2.execute(
            "INSERT INTO restaurant_reservations (shop_id,shop_name,customer_phone,customer_name,party_size,reserve_date,reserve_time) VALUES (?,?,?,?,?,?,?)",
            (shop['id'], shop['name'], '', '', party_size, reserve_date, reserve_time)
        )
        conn2.commit()
        rid = conn2.execute('SELECT last_insert_rowid()').fetchone()[0]
        _webhook_push(shop['id'], 'new_reservation_chat', {'reservation_id': rid, 'party_size': party_size, 'date': reserve_date, 'time': reserve_time})
        conn2.close()
        reply = f'已为您预订【{shop["name"]}】！\n日期：{mo}月{dy}日\n时间：{reserve_time}\n人数：{party_size}人\n预订编号：R{rid:04d}\n\n到店时报预订编号即可入座，如需取消或修改请提前通知~'
        card = {
            'title': f'{shop["name"]} · 预订确认',
            'items': [
                {'name': f'{mo}月{dy}日 {reserve_time}', 'desc': f'{party_size}人位', 'tag': '已确认', 'price': f'R{rid:04d}'},
            ],
            'footer': f'电话：{shop["phone"]} | 如需取消请提前告知'
        }
        return {'reply': reply, 'card': card}

    return None


_web_cache = {}
def web_search_inject(query):
    # 内存缓存，避免重复网络请求拖慢响应
    key = (query or '')[:20]
    if key in _web_cache:
        return _web_cache[key]
    result = ''
    try:
        import urllib.request, urllib.parse
        url = 'https://api.duckduckgo.com/?q=' + urllib.parse.quote(query) + '&format=json&no_html=1&skip_disambig=1'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        parts = []
        if data.get('AbstractText'):
            parts.append(data['AbstractText'])
        for t in data.get('RelatedTopics', [])[:3]:
            if t.get('Text'):
                parts.append(t['Text'])
        text = ' '.join(parts)
        if len(text) > 20:
            result = "\n【网络搜索结果】" + text[:600]
    except:
        pass
    _web_cache[key] = result
    return result

# ========== Routes - Pages ==========
@app.route('/')
def index():
    if not session.get('user_id'):
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username='guest' AND tenant_id=1").fetchone()
        if not user:
            conn.execute(
                "INSERT INTO users (tenant_id, username, password_hash, display_name, role) VALUES (1,'guest',?,?,?)",
                (hashlib.sha256('guest'.encode()).hexdigest(), '游客', 'user')
            )
            conn.commit()
            user = conn.execute("SELECT * FROM users WHERE username='guest' AND tenant_id=1").fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['tenant_id'] = user['tenant_id']
            session['role'] = user['role']
            session['display_name'] = user['display_name']
    return send_from_directory(os.path.join(HERE, 'static'), 'chat.html')

@app.route('/chat')
def chat_page():
    return index()

@app.route('/login-page')
def login_page():
    return send_from_directory(os.path.join(HERE, 'static'), 'login.html')

@app.route('/manage')
def manage_login():
    return send_from_directory(os.path.join(HERE, 'static'), 'login-admin.html')

@app.route('/admin')
@admin_required
def admin_page():
    return send_from_directory(os.path.join(HERE, 'static'), 'admin.html')

@app.route('/nav')
def nav_page():
    return send_from_directory(os.path.join(HERE, 'static'), 'nav.html')

@app.route('/platform')
@super_admin_required
def platform_page():
    return send_from_directory(os.path.join(HERE, 'static'), 'platform.html')

@app.route('/register-page')
def register_page():
    return send_from_directory(os.path.join(HERE, 'static'), 'register.html')

# ========== API - Auth ==========
@app.route('/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    admin_flag = data.get('admin', False)
    conn = get_db()
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    if admin_flag:
        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password_hash=? AND role IN ('tenant_admin','super_admin')",
            (username, pw_hash)
        ).fetchone()
    else:
        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password_hash=?",
            (username, pw_hash)
        ).fetchone()
    conn.close()
    if not user:
        return jsonify(ok=False, error='用户名或密码错误')
    session['user_id'] = user['id']
    session['tenant_id'] = user['tenant_id']
    session['role'] = user['role']
    session['display_name'] = user['display_name']
    session['phone'] = user['phone'] if user['phone'] else ''
    return jsonify(ok=True, user=dict(user))

@app.route('/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify(ok=True)

@app.route('/api/session')
def api_session():
    if session.get('user_id'):
        uid = session['user_id']
        # 如果 session 缺 phone/headimgurl，从数据库补
        phone = session.get('phone','')
        headimgurl = session.get('headimgurl','')
        if not phone or not headimgurl:
            conn = get_db()
            row = conn.execute('SELECT phone, headimgurl, display_name, points, membership_level FROM users WHERE id=?', (uid,)).fetchone()
            conn.close()
            if row:
                if not phone:
                    phone = row['phone'] or ''
                    session['phone'] = phone
                if not headimgurl:
                    headimgurl = row['headimgurl'] or ''
                    session['headimgurl'] = headimgurl
                if not session.get('display_name'):
                    session['display_name'] = row['display_name']
                points = row['points'] or 0
                membership_level = row['membership_level'] or '普卡'
            else:
                points = 0
                membership_level = '普卡'
        else:
            points = 0
            membership_level = '普卡'
        return jsonify(ok=True, user={
            'id': uid,
            'tenant_id': session['tenant_id'],
            'role': session.get('role'),
            'display_name': session.get('display_name'),
            'phone': phone,
            'headimgurl': headimgurl,
            'points': points,
            'membership_level': membership_level
        })
    return jsonify(ok=False)

# ========== API - Chat ==========
@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    data = request.get_json()
    user_input = data.get('message', '').strip()
    tid = session['tenant_id']
    uid = session['user_id']
    return _do_chat(tid, uid, user_input)

@app.route('/api/public/chat', methods=['POST'])
def api_public_chat():
    """C端公开聊天 — 不需要登录，用 session cookie 做 key"""
    data = request.get_json()
    user_input = data.get('message', '').strip()
    if len(user_input) > 500:
        return jsonify(ok=False, error='消息太长了，请精简到500字以内')
    # 使用 session cookie 作为匿名 key
    sid = request.cookies.get('session', 'anonymous')
    # tenant 固定为 1
    large_font = data.get('large_font', False)
    return _do_chat(1, sid, user_input, large_font=large_font)

@app.route('/api/public/chat/stream', methods=['POST'])
def api_public_chat_stream():
    """C端流式聊天 — 本地快速回复秒回，AI 回答逐字流式返回"""
    data = request.get_json()
    user_input = (data.get('message') or '').strip()
    if not user_input or len(user_input) > 500:
        return jsonify(ok=False, error='消息为空或过长')
    sid = request.cookies.get('session', 'anonymous')
    chat_key = '1:' + sid

    def generate():
        # 1. 本地快速回复（关键词 + 知识库高匹配）
        local = _fast_reply(user_input)
        if not local:
            kb = kb_search(1, user_input, limit=3)
            if kb:
                qw = set((kb[0]['question'] or '').lower().split())
                iw = set(user_input.lower().split())
                overlap = len(qw & iw)
                kw = (kb[0]['keywords'] or '').lower()
                if overlap >= 1 or any(w in kw for w in iw if len(w) > 1):
                    local = f'[{kb[0]["category"]}] {kb[0]["answer"][:500]}'
        if local:
            history = CHAT_HISTORY.get(chat_key, [])
            history.append({'role':'user','content':user_input})
            history.append({'role':'assistant','content':local})
            CHAT_HISTORY[chat_key] = history[-MAX_HISTORY*2:]
            yield f"data: {json.dumps({'reply': local, 'done': True}, ensure_ascii=False)}\n\n"
            return

        # 2. 流式 AI
        try:
            history = CHAT_HISTORY.get(chat_key, [])[-MAX_HISTORY*2:]
            sp = SYSTEM_PROMPT + '\n当前时间: ' + datetime.now().strftime('%Y-%m-%d %H:%M')
            messages = [{'role':'system','content':sp}]
            for h in history:
                messages.append(h)
            messages.append({'role':'user','content': user_input})
            stream = ds_client.chat.completions.create(
                model='deepseek-chat', messages=messages, stream=True,
                max_tokens=180, temperature=0.6
            )
            full = ''
            for chunk in stream:
                delta = ''
                try:
                    if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                        delta = chunk.choices[0].delta.content
                except Exception:
                    pass
                if delta:
                    full += delta
                    yield f"data: {json.dumps({'token': delta}, ensure_ascii=False)}\n\n"
            history.append({'role':'user','content':user_input})
            history.append({'role':'assistant','content':full})
            CHAT_HISTORY[chat_key] = history[-MAX_HISTORY*2:]
            _save_chat_history()
            yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
        except Exception:
            fallback = '哎呀，小江的脑子有点转不过来...要不你重新说一遍？'
            yield f"data: {json.dumps({'reply': fallback, 'done': True}, ensure_ascii=False)}\n\n"

    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})

def _do_chat(tid, uid, user_input, large_font=False):
    chat_key = str(tid) + ':' + str(uid)
    ai_degraded = False  # 本次是否触发 AI 服务降级（故障时引导人工客服）
    # 老年用户转人工: 轮次计数
    if large_font:
        CHAT_ROUNDS[chat_key] = CHAT_ROUNDS.get(chat_key, 0) + 1
    else:
        CHAT_ROUNDS.pop(chat_key, None)  # 非大字模式重置
    round_count = CHAT_ROUNDS.get(chat_key, 0)
    keys = list(CHAT_HISTORY.keys())
    while len(keys) > MAX_SESSIONS:
        del CHAT_HISTORY[keys[0]]
        keys = keys[1:]
    if chat_key not in CHAT_HISTORY:
        CHAT_HISTORY[chat_key] = []
    history = CHAT_HISTORY[chat_key][-MAX_HISTORY*2:]
    # Detect "确认兑换N" and execute redemption directly
    redeem_match = re.search(r'确认兑换(\d+)', user_input)
    if redeem_match:
        try:
            rid = int(redeem_match.group(1))
            # Find phone: first in current message, then in history
            rphone = None
            pm = re.search(r'1[3-9]\d{9}', user_input)
            if pm:
                rphone = pm.group(0)
            else:
                for h in reversed(CHAT_HISTORY.get(str(tid)+':'+str(uid), [])):
                    pm = re.search(r'1[3-9]\d{9}', h.get('content', ''))
                    if pm:
                        rphone = pm.group(0)
                        break
            if rphone:
                rdb = get_db()
                ruser = rdb.execute('SELECT id, display_name, phone, points, membership_level FROM users WHERE phone=?', (rphone,)).fetchone()
                if ruser:
                    redeem_catalog = {
                        1: ('停车券', 500, 'PARK'),
                        2: ('海江食集满50减10券', 800, 'B1CP'),
                        3: ('瑞幸咖啡饮品券', 1000, 'SBUX'),
                        4: ('SFC上影电影票', 2000, 'MOVI'),
                        5: ('朱光玉火锅50元券', 3000, 'ZGY'),
                        6: ('泡泡米儿童体验课', 5000, 'KID'),
                        7: ('华为授权店30元券', 8000, 'HW'),
                        8: ('200元购物卡', 10000, 'CARD'),
                        9: ('哇咔健身周卡', 15000, 'FIT'),
                    }
                    if rid in redeem_catalog:
                        rname, rcost, rprefix = redeem_catalog[rid]
                        if ruser['points'] >= rcost:
                            code_num = str(int(time.time()))[-6:]
                            rcode = f'{rprefix}{code_num}'
                            new_pts = ruser['points'] - rcost
                            rdb.execute('UPDATE users SET points=? WHERE phone=?', (new_pts, rphone))
                            rdb.execute(
                                'INSERT INTO work_orders (tenant_id, type, title, description, priority, status, reporter_contact) VALUES (?,?,?,?,?,?,?)',
                                (1, 'points_redeem', f'积分兑换：{rname}',
                                 json.dumps({'phone': rphone, 'redeem_id': rid, 'item': rname, 'cost': rcost, 'code': rcode, 'before_points': ruser['points'], 'after_points': new_pts}, ensure_ascii=False),
                                 'normal', 'resolved', rphone))
                            rdb.commit()
                            rdb.close()
                            reply = f'兑换成功！已用{rcost}积分兑换【{rname}】，券码：{rcode}，剩余{new_pts}分。请至小程序「我的→优惠券」查看或到店出示核销喵~'
                            history.append({'role':'user','content':user_input})
                            history.append({'role':'assistant','content':reply})
                            CHAT_HISTORY[chat_key] = history[-MAX_HISTORY*2:]; _save_chat_history()
                            return jsonify(ok=True, reply=reply)
                        else:
                            gap = rcost - ruser['points']
                            closest = None
                            for k, v in sorted(redeem_catalog.items(), key=lambda x: x[1][1]):
                                if v[1] <= ruser['points']:
                                    closest = v
                            hint = f'您当前可兑换：{closest[0]}（{closest[1]}分）' if closest else '目前暂无足够积分可兑换'
                            rdb.close()
                            reply = f'积分不足！兑换{rname}需要{rcost}分，您当前有{ruser["points"]}分，还差{gap}分。{hint}'
                            history.append({'role':'user','content':user_input})
                            history.append({'role':'assistant','content':reply})
                            CHAT_HISTORY[chat_key] = history[-MAX_HISTORY*2:]; _save_chat_history()
                            return jsonify(ok=True, reply=reply)
                    else:
                        rdb.close()
                else:
                    rdb.close()
            else:
                # No phone found - ask for it
                reply = '确认兑换需要先提供手机号哦~请发送您的11位手机号，我再帮您兑换！'
                history.append({'role':'user','content':user_input})
                history.append({'role':'assistant','content':reply})
                CHAT_HISTORY[chat_key] = history[-MAX_HISTORY*2:]; _save_chat_history()
                return jsonify(ok=True, reply=reply)
        except Exception:
            pass  # Fall through to normal AI chat

    # Detect member registration
    register_keywords = ['注册会员','我要注册','开通会员','申请会员']
    if any(k in user_input for k in register_keywords):
        try:
            pm = re.search(r'1[3-9]\d{9}', user_input)
            if pm:
                rphone = pm.group(0)
                rdb = get_db()
                exist = rdb.execute('SELECT id, display_name FROM users WHERE phone=?', (rphone,)).fetchone()
                if exist:
                    rdb.close()
                    reply = f'您已经是会员啦！{exist["display_name"]}，如有需要可以继续使用积分兑换等功能~'
                else:
                    rdb.close()
                    reply = f'请回复"确认注册 姓名 {rphone}"来开通会员（例如：确认注册 张三 {rphone}），注册即送500积分！'
                history.append({'role':'user','content':user_input})
                history.append({'role':'assistant','content':reply})
                CHAT_HISTORY[chat_key] = history[-MAX_HISTORY*2:]; _save_chat_history()
                return jsonify(ok=True, reply=reply)
            else:
                reply = '请发送您的11位手机号，我来帮您注册会员~（注册即送500积分）'
                history.append({'role':'user','content':user_input})
                history.append({'role':'assistant','content':reply})
                CHAT_HISTORY[chat_key] = history[-MAX_HISTORY*2:]; _save_chat_history()
                return jsonify(ok=True, reply=reply)
        except Exception:
            pass

    # Detect confirm registration: 确认注册 姓名 手机号
    reg_match = re.search(r'确认注册\s+(\S+)\s+(1[3-9]\d{9})', user_input)
    if reg_match:
        try:
            rname = reg_match.group(1)
            rphone = reg_match.group(2)
            rdb = get_db()
            exist = rdb.execute('SELECT id FROM users WHERE phone=?', (rphone,)).fetchone()
            if exist:
                rdb.close()
                reply = f'手机号 {rphone} 已注册过会员，无需重复注册~可以直接使用积分兑换等功能！'
            else:
                import hashlib
                pw_hash = hashlib.sha256(('member'+rphone).encode()).hexdigest()
                uname = 'm'+rphone
                rdb.execute(
                    'INSERT INTO users (tenant_id, username, password_hash, display_name, role, phone, points, membership_level) VALUES (?,?,?,?,?,?,?,?)',
                    (1, uname, pw_hash, rname, 'user', rphone, 500, '普卡'))
                rdb.commit()
                rdb.close()
                reply = f'注册成功！{rname}，您已是普卡会员，初始积分500分。购物可享98折，攒满2000分可升级银卡（95折）哦~回复"优惠券"看看能换什么！'
            history.append({'role':'user','content':user_input})
            history.append({'role':'assistant','content':reply})
            CHAT_HISTORY[chat_key] = history[-MAX_HISTORY*2:]; _save_chat_history()
            return jsonify(ok=True, reply=reply)
        except Exception:
            pass

    # Detect coupon/优惠券 query
    coupon_keywords = ['优惠券','我的券','兑换记录','我的兑换','查券','券码']

    # 智能检索引导 - 裸词拦截（不带参数时返回选项）
    ai_search_guides = {
        '找优惠': ' 找优惠·请回复数字：\n[1] 餐饮优惠  [2] 亲子优惠  [3] 夜校优惠  [4] 便民优惠',
        '找活动': ' 找活动·请回复数字：\n[1] 亲子活动  [2] 老年活动  [3] 青年活动  [4] 全部活动',
        '找店铺': ' 找店铺·请回复数字：\n[1] 火锅  [2] 披萨  [3] 咖啡  [4] 亲子餐厅  [5] 美食广场  [6] 教培',
        '找商品': ' 找商品·请回复数字：\n[1] 夜校课程  [2] 演出票务  [3] 零售商品',
    }
    for guide_key, guide_msg in ai_search_guides.items():
        if user_input == guide_key or user_input.strip() == guide_key:
            history.append({'role': 'user', 'content': guide_key})
            history.append({'role': 'assistant', 'content': guide_msg})
            CHAT_HISTORY[chat_key] = history[-MAX_HISTORY*2:]; _save_chat_history()
            return jsonify(ok=True, reply=guide_msg)

    coupon_keywords = ['优惠券','我的券','兑换记录','我的兑换','查券','券码']
    if any(k in user_input for k in coupon_keywords):
        try:
            cphone = None
            pm = re.search(r'1[3-9]\d{9}', user_input)
            if pm:
                cphone = pm.group(0)
            else:
                for h in reversed(history):
                    pm = re.search(r'1[3-9]\d{9}', h.get('content', ''))
                    if pm:
                        cphone = pm.group(0)
                        break
            if cphone:
                cdb = get_db()
                cuser = cdb.execute('SELECT display_name, points FROM users WHERE phone=?', (cphone,)).fetchone()
                if cuser:
                    coupons = cdb.execute(
                        "SELECT id, title, description, created_at FROM work_orders WHERE type='points_redeem' AND reporter_contact=? ORDER BY id DESC LIMIT 20",
                        (cphone,)
                    ).fetchall()
                    cdb.close()
                    if coupons:
                        lines = [f'您的优惠券（{cuser["display_name"]} {cuser["points"]}分）：']
                        for i, co in enumerate(coupons, 1):
                            try:
                                d = json.loads(co[2])
                                code = d.get('code', '?')
                                item = d.get('item', co[1])
                                tm = d.get('time', co[3])[:10] if d.get('time') else str(co[3])[:10]
                            except:
                                code = '?'
                                item = co[1]
                                tm = str(co[3])[:10] if co[3] else '?'
                            lines.append(f'{i}. {item} | 券码：{code} | {tm}')
                        lines.append('到店出示券码即可核销使用~')
                        reply = '\n'.join(lines)
                        history.append({'role':'user','content':user_input})
                        history.append({'role':'assistant','content':reply})
                        CHAT_HISTORY[chat_key] = history[-MAX_HISTORY*2:]; _save_chat_history()
                        return jsonify(ok=True, reply=reply)
                    else:
                        cdb.close() if 'cdb' in dir() else None
                else:
                    cdb.close() if 'cdb' in dir() else None
            else:
                reply = '请发送您的11位手机号，我帮您查优惠券~'
                history.append({'role':'user','content':user_input})
                history.append({'role':'assistant','content':reply})
                CHAT_HISTORY[chat_key] = history[-MAX_HISTORY*2:]; _save_chat_history()
                return jsonify(ok=True, reply=reply)
        except Exception:
            pass

    # ===== 餐厅取号/预订意图处理（优先于极速回复，处理含餐厅名的精确请求） =====
    rc_result = _restaurant_chat_handle(user_input)
    if rc_result:
        reply_text = rc_result.get('reply', '')
        card_data = rc_result.get('card')
        history.append({'role':'user','content':user_input})
        history.append({'role':'assistant','content':reply_text})
        CHAT_HISTORY[chat_key] = history[-MAX_HISTORY*2:]; _save_chat_history()
        resp = jsonify(ok=True, reply=reply_text)
        if card_data:
            resp = jsonify(ok=True, reply=reply_text, card=card_data)
        return resp
    # ============================================================

    # ===== 极速本地回复（<1ms，覆盖80%常见问题，不走AI） =====
    fast_reply = _fast_reply(user_input)
    if fast_reply:
        history.append({'role':'user','content':user_input})
        history.append({'role':'assistant','content':fast_reply})
        CHAT_HISTORY[chat_key] = history[-MAX_HISTORY*2:]; _save_chat_history()
        return jsonify(ok=True, reply=fast_reply)
    # ============================================================

    kb_results = kb_search(tid, user_input)

    # Auto-detect phone number for membership portal lookup
    phone_match = re.search(r'1[3-9]\d{9}', user_input)
    member_hint = ''
    if phone_match:
        phone = phone_match.group(0)
        mdb = get_db()
        mem = mdb.execute(
            'SELECT display_name, points, membership_level FROM users WHERE phone=?',
            (phone,)
        ).fetchone()
        mdb.close()
        if mem:
            levels = {
                '普卡': ('98折', 0.98, 0, '银卡', 2000, '消费1元=1积分'),
                '银卡': ('95折', 0.95, 2000, '金卡', 5000, '每月1张停车券、生日月双倍积分'),
                '金卡': ('9折', 0.90, 5000, '钻石卡', 20000, '每周二会员日额外95折、每月3张停车券、生日月专属礼'),
                '钻石卡': ('88折', 0.88, 20000, None, None, '免费停车、VIP休息室、优先预定、专属客服'),
            }
            lv = mem['membership_level'] or '普卡'
            disc, dr, min_pt, nl, np, desc = levels.get(lv, levels['普卡'])
            pts = mem['points'] or 0
            member_hint = f'\n【会员查询结果】手机号{phone} -> {mem["display_name"]}，等级：{lv}（{disc}），积分：{pts}分。权益：{desc}。'
            if nl:
                gap = np - pts
                pct = round(min(100, pts/np*100), 1)
                member_hint += f'距离升级{nl}还需{gap}分/消费{gap}元（进度{pct}%）。'
            member_hint += '积分商城可兑礼品参考：500停车券/800海江食集券/1000瑞幸咖啡券/2000SFC电影票/3000朱光玉火锅券/5000泡泡米体验课/8000华为30元券/15000哇咔健身周卡。请基于此会员等级进行算价，提醒积分使用建议。'
        else:
            member_hint = f'\n【会员查询结果】手机号{phone}未注册。请直接引导用户在此对话中回复"我要注册"即可开通会员，赠送500积分。绝对不能回复"去服务台注册"。'
    kb_block = ''
    if kb_results:
        kb_block = '\n【知识库匹配】'
        for r in kb_results:
            kb_block += f'\n[{r["category"]}] {r["question"]}: {r["answer"][:300]}'
    # 真实商户检索（区域/品类精准过滤，避免漏答）
    shop_block = shop_block_build(user_input)
    web_block = web_search_inject(user_input)
    sp = SYSTEM_PROMPT + '\n当前时间: ' + datetime.now().strftime('%Y-%m-%d %H:%M') + shop_block + kb_block + web_block
    sp += member_hint
    # 知识库匹配度检查：70分以上直接回复，跳过 AI
    best_kb = None
    best_kb_score = 0
    if kb_results:
        for r in kb_results:
            qw = set((r['question'] or '').lower().split())
            iw = set(user_input.lower().split())
            score = len(qw & iw) * 10
            kw = (r['keywords'] or '').lower()
            for w in iw:
                if w in kw:
                    score += 15
            if score > best_kb_score:
                best_kb_score = score
                best_kb = r
    if best_kb and best_kb_score >= 35:
        # 知识库匹配度高，直接回复
        reply = f'[{best_kb["category"]}] {best_kb["answer"][:500]}'
        history.append({'role':'user','content':user_input})
        history.append({'role':'assistant','content':reply})
        CHAT_HISTORY[chat_key] = history[-MAX_HISTORY*2:]; _save_chat_history()
        return jsonify(ok=True, reply=reply)

    messages = [{'role':'system','content':sp}]
    for h in history:
        messages.append(h)
    messages.append({'role':'user','content': user_input})
    try:
        ok, result = ai_chat(messages, max_tokens=180)
        if ok:
            reply = result
        else:
            raise Exception(result)
    except Exception:
        # DeepSeek 失败 → 降级为基础问答（情感关键词/真实商户检索/知识库兜底）
        ai_degraded = True
        emotion_map = {
            '难受': '抱抱你呀~虽然小江不知道具体发生了什么，但想说：累了就来海江逛逛，吃点好的、看看热闹，心情会好很多的 💛 有什么小江能帮你的吗？',
            '不开心': '哎呀别不开心啦~来海江散散心呗，小江陪你聊天！想吃啥玩啥跟我说~',
            '无聊': '嘿嘿那来找小江聊天就对了！要不要看看最近有啥好玩的？亲子活动、夜校课程都挺有意思的~',
            '烦': '是不是最近压力有点大呀？来海江逛逛换换心情吧，小江陪你聊聊~有好吃的推荐你哦！',
            '累': '辛苦啦！给自己放个小假嘛，来海江吃顿好的犒劳一下自己~小江觉得火锅最能治愈疲惫了！',
            '谢谢': '不客气呀，能帮到你就好~有什么随时找小江！',
            '再见': '拜拜~下次来海江玩记得找小江聊天哦 👋',
        }
        matched_emotion = None
        for kw, em_reply in emotion_map.items():
            if kw in user_input:
                matched_emotion = em_reply
                break
        if matched_emotion:
            reply = matched_emotion
        else:
            # 优先用真实商户检索（区域/品类精准），AI 不可用时也能答"某区有什么吃的"
            sb = shop_block_build(user_input)
            if sb:
                reply = sb.replace('\n【真实商户检索结果】', '').strip()
                reply = '为你查到海江新天地真实在册的商户：\n' + reply
            else:
                kb = kb_search(tid, user_input, limit=3)
                if kb:
                    reply = '\n'.join([f'[{r["category"]}] {r["answer"][:200]}' for r in kb[:3]])
                    if len(reply) < 20:
                        reply = '抱歉，小江暂时没找到相关信息，你可以换个问法试试~'
            if any(w in user_input for w in ['你好','嗨','hi','hello']):
                reply = '嗨！我是小江，海江新天地的客服助手~\n想找店铺、查优惠、问路、看活动，尽管问我！'
            else:
                reply = '哎呀，小江的脑子有点转不过来...要不你重新说一遍？'
    # 未命中问题自动归集到知识库待优化列表
    if '转不过来' in reply or '没找到相关信息' in reply or '换个问法' in reply:
        _add_kb_pending(tid, user_input, 'chat')
    reply = re.sub(r'\*\*|__', '', reply)
    reply = re.sub(r'#{1,6}\s*', '', reply)
    escalate_keywords = ['退款','投诉','找经理','找领导','赔偿','退一赔三','人身安全']
    needs_escalate = any(w in user_input for w in escalate_keywords)
    if needs_escalate:
        conn = get_db()
        conn.execute(
            "INSERT INTO work_orders (tenant_id, type, title, description, priority, status, reporter_contact) VALUES (?,?,?,?,?,?,?)",
            (tid, 'escalation', '升级工单: ' + user_input[:50], reply[:200], 'high', 'pending', 'session:'+chat_key)
        )
        conn.commit(); conn.close()
        reply = '您反馈的问题涉及重要权益，我已为您生成高优先级工单，会有专人尽快回电处理。如需紧急帮助请拨打021-8888-0001。\n\n' + reply
    history.append({'role':'user','content':user_input})
    history.append({'role':'assistant','content':reply})
    CHAT_HISTORY[chat_key] = history[-MAX_HISTORY*2:]; _save_chat_history()
    # 老年用户转人工: 超过2轮且不在已解决对话中，展示大按钮
    transfer_btn = None
    if large_font and round_count >= 2:
        resolved_words = ['谢谢', '不客气', '再见', '拜拜', '知道了', '好的', '明白了', '兑换成功', '取号成功', '预订成功', '报名成功', '领取成功']
        is_resolved = any(w in (user_input + reply) for w in resolved_words)
        if not is_resolved and not needs_escalate:
            transfer_btn = {
                'label': '一键呼叫人工客服',
                'phone': '021-8888-0001',
                'note': '小江好像没完全帮到您，需要人工客服帮您处理吗？'
            }
    elif ai_degraded:
        # AI 核心服务故障降级：主动引导转人工客服，保障基础服务可用
        transfer_btn = {
            'label': '转人工客服',
            'phone': '021-8888-0001',
            'note': 'AI 智能服务暂时繁忙，已为您切换基础问答。如未解决您的问题，可转人工客服~'
        }
    return jsonify(ok=True, reply=reply, transfer_btn=transfer_btn)

@app.route('/api/chat/clear', methods=['POST'])
@login_required
def api_chat_clear():
    tid = session['tenant_id']
    uid = session['user_id']
    CHAT_HISTORY.pop(str(tid)+':'+str(uid), None)
    return jsonify(ok=True)

# ========== API - External (token auth) ==========
EXTERNAL_TOKEN = 'djdl_8…942e'

@app.route('/api/ext/chat', methods=['POST'])
def api_ext_chat():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if token != EXTERNAL_TOKEN:
        return jsonify(ok=False, error='Invalid token'), 403
    data = request.get_json()
    user_input = data.get('message', '').strip()
    tid = data.get('tenant_id', 1)

    import re as _re3

    # Strip phone number and "AI " prefix from display-only messages
    clean_input = _re3.sub(r'1[3-9]\d{9}', '', user_input).strip()
    clean_input = _re3.sub(r'^AI\s+', '', clean_input).strip()

    # 智能检索引导 - 裸词拦截
    ai_search_guides = {
        '找优惠': '>>> 找优惠 · 请回复数字：\n[1] 餐饮优惠  [2] 亲子优惠  [3] 夜校优惠  [4] 便民优惠',
        '找活动': '>>> 找活动 · 请回复数字：\n[1] 亲子活动  [2] 老年活动  [3] 青年活动  [4] 全部活动',
        '找店铺': '>>> 找店铺 · 请回复数字：\n[1] 火锅  [2] 披萨  [3] 咖啡  [4] 亲子餐厅  [5] 美食广场  [6] 教培',
        '找商品': '>>> 找商品 · 请回复数字：\n[1] 夜校课程  [2] 演出票务  [3] 零售商品',
    }
    for guide_key, guide_msg in ai_search_guides.items():
        if clean_input == guide_key:
            return jsonify(ok=True, reply=guide_msg)

    phone_match = _re3.search(r'1[3-9]\d{9}', user_input)
    member_hint = ''
    if phone_match:
        phone = phone_match.group(0)
        # Only add hint for non-guide queries (avoid adding phone to guide replies)
        if clean_input not in ai_search_guides:
            mdb = get_db()
            mem = mdb.execute('SELECT display_name, points, membership_level FROM users WHERE phone=?', (phone,)).fetchone()
            mdb.close()
            if mem:
                lv = mem['membership_level'] or '普卡'
                levels = {'普卡':('98折','消费1元=1积分'),'银卡':('95折','每月1张停车券、生日月双倍积分'),'金卡':('9折','每周二会员日额外95折、每月3张停车券、生日月专属礼'),'钻石卡':('88折','免费停车、VIP休息室、优先预定、专属客服')}
                disc, desc = levels.get(lv, levels['普卡'])
                member_hint = '\n【会员查询结果】手机号'+phone[-4:]+' -> '+mem['display_name']+'，等级：'+lv+'（'+disc+'），积分：'+str(mem['points'])+'分。权益：'+desc+'。请基于此会员等级进行算价。'
            else:
                member_hint = '\n【会员查询结果】该手机号未注册。请提醒用户注册会员。'
    kb_results = kb_search(tid, user_input)
    kb_block = ''
    if kb_results:
        kb_block = '\n【知识库】'
        for r in kb_results:
            kb_block += f'\n[{r["category"]}] {r["question"]}: {r["answer"][:200]}'
    sp += member_hint
    messages = [{'role':'system','content': SYSTEM_PROMPT + kb_block}]
    messages.append({'role':'user','content': user_input})
    try:
        resp = ds_client.chat.completions.create(model='deepseek-chat', messages=messages, max_tokens=500)
        reply = resp.choices[0].message.content
    except:
        reply = 'AI service unavailable'
    reply = re.sub(r'\*\*|__|#{1,6}\s*', '', reply)
    return jsonify(ok=True, reply=reply)

# ========== API - Knowledge Base ==========
@app.route('/api/kb', methods=['GET','POST'])
@admin_required
def api_kb():
    tid = session['tenant_id']
    conn = get_db()
    if request.method == 'GET':
        cat = request.args.get('category', '')
        search = request.args.get('search', '')
        sql = "SELECT * FROM knowledge_base WHERE tenant_id=?"
        params = [tid]
        if cat:
            sql += " AND category=?"
            params.append(cat)
        if search:
            sql += " AND (question LIKE ? OR keywords LIKE ?)"
            params.extend(['%'+search+'%', '%'+search+'%'])
        rows = conn.execute(sql + " ORDER BY id DESC LIMIT 200", params).fetchall()
        conn.close()
        items = [dict(r) for r in rows]
        return jsonify(ok=True, items=items, total=len(items))
    data = request.get_json()
    conn.execute(
        "INSERT INTO knowledge_base (tenant_id, category, question, answer, keywords) VALUES (?,?,?,?,?)",
        (tid, data.get('category','service'), data.get('question',''), data.get('answer',''), data.get('keywords',''))
    )
    conn.commit(); conn.close()
    return jsonify(ok=True)

@app.route('/api/kb/<int:kid>', methods=['PUT','DELETE'])
@admin_required
def api_kb_item(kid):
    tid = session['tenant_id']
    conn = get_db()
    if request.method == 'DELETE':
        conn.execute("DELETE FROM knowledge_base WHERE id=? AND tenant_id=?", (kid, tid))
        conn.commit(); conn.close()
        return jsonify(ok=True)
    data = request.get_json()
    conn.execute(
        "UPDATE knowledge_base SET category=?, question=?, answer=?, keywords=? WHERE id=? AND tenant_id=?",
        (data.get('category','service'), data.get('question',''), data.get('answer',''), data.get('keywords',''), kid, tid)
    )
    conn.commit(); conn.close()
    return jsonify(ok=True)

# ========== API - Orders ==========
@app.route('/api/orders', methods=['GET','POST'])
@login_required
def api_orders():
    tid = session['tenant_id']
    if request.method == 'GET':
        conn = get_db()
        # tenant_admin only sees own merchant orders
        if session.get('role') == 'tenant_admin' and session.get('display_name'):
            m = session['display_name'].replace('管理员', '')
            rows = conn.execute(
                "SELECT * FROM work_orders WHERE tenant_id=? AND (merchant=? OR merchant='') ORDER BY created_at DESC LIMIT 200",
                (tid, m)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM work_orders WHERE tenant_id=? ORDER BY created_at DESC LIMIT 200", (tid,)).fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    data = request.get_json()
    conn = get_db()
    # Extract merchant from title
    title = data.get('title','')
    merchant = ''
    if ' - ' in title:
        merchant = title.split(' - ')[-1] if title.split(' - ')[-1] else ''
    conn.execute(
        "INSERT INTO work_orders (tenant_id, type, title, description, priority, status, reporter, reporter_contact, merchant) VALUES (?,?,?,?,?,?,?,?,?)",
        (tid, data.get('type','inquiry'), title, data.get('description',''),
         data.get('priority','normal'), data.get('status','pending'), data.get('reporter',''), data.get('reporter_contact',''), merchant)
    )
    conn.commit(); conn.close()
    return jsonify(ok=True)

@app.route('/api/orders/<int:oid>', methods=['PUT'])
@admin_required
def api_order_update(oid):
    data = request.get_json()
    tid = session['tenant_id']
    conn = get_db()
    if data.get('status'):
        conn.execute("UPDATE work_orders SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND tenant_id=?", (data['status'], oid, tid))
    conn.commit(); conn.close()
    return jsonify(ok=True)

# ========== API - Registration ==========
@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    conn = get_db()
    conn.execute(
        "INSERT INTO registrations (tenant_id, event, name, phone, count, note) VALUES (?,?,?,?,?,?)",
        (1, data.get('event',''), data.get('name',''), data.get('phone',''), int(data.get('count','1')), data.get('note',''))
    )
    conn.commit(); conn.close()
    return jsonify(ok=True)

# ========== API - Barcode + OCR ==========
@app.route('/api/barcode', methods=['POST'])
@login_required
def api_barcode():
    try:
        from PIL import Image, ImageEnhance, ImageFilter, ImageOps
        from pyzbar.pyzbar import decode as zbardecode
        img_data = base64.b64decode(request.json.get('image',''))
        img = Image.open(io.BytesIO(img_data))
        if img.mode != 'RGB':
            img = img.convert('RGB')
        W, H = img.size
        try:
            debug_dir = os.path.join(HERE, 'debug_barcodes')
            os.makedirs(debug_dir, exist_ok=True)
            ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            img.save(os.path.join(debug_dir, f'{ts}_orig.jpg'), 'JPEG', quality=85)
        except:
            pass
        gray = ImageOps.grayscale(img)
        variants = [('orig', img)]
        for s in (0.5, 0.25, 0.75):
            variants.append((f'scale{int(s*100)}', img.resize((int(W*s), int(H*s)), Image.LANCZOS)))
        variants.append(('gray', gray))
        variants.append(('autocontrast', ImageOps.autocontrast(img, cutoff=3)))
        variants.append(('equalize', ImageOps.equalize(img)))
        variants.append(('sharpen', img.filter(ImageFilter.SHARPEN)))
        variants.append(('upscale2x', img.resize((W*2, H*2), Image.LANCZOS)))
        for c in (2.0, 3.0):
            variants.append((f'contrast_{c}', ImageEnhance.Contrast(img).enhance(c)))
        for t in (80, 100, 120, 140, 160, 180):
            try:
                variants.append((f'binary_{t}', gray.point(lambda x, th=t: 0 if x < th else 255, '1')))
            except:
                pass
        for name, v in variants:
            results = zbardecode(v)
            if results:
                code = results[0].data.decode('utf-8').strip()
                if code:
                    return jsonify(ok=True, code=code, method='zbar_'+name)
        # Phase 2: OCR text recognition
        try:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            text = pytesseract.image_to_string(img, lang='eng+chi_sim')
            for p in [r'DJ\d{4}', r'PARK\d{2}', r'CPN\d+', r'VIP\d+']:
                matches = re.findall(p, text.upper())
                if matches:
                    return jsonify(ok=True, code=matches[0], method='ocr')
            fuzzy = re.findall(r'[A-Z]{2,4}\d{2,6}', text.upper().replace(' ', '').replace('\n', ''))
            if fuzzy:
                return jsonify(ok=True, code=fuzzy[0], method='ocr_fuzzy')
        except:
            pass
        return jsonify(ok=False, error='无法识别条码，请手动输入券码')
    except Exception as e:
        return jsonify(ok=False, error=str(e))

# ========== API - Indoor Navigation ==========
@app.route('/api/nav/search')
def api_nav_search():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    results = []
    for floor, rooms in floor_data.FLOOR_ROOMS.items():
        for r in rooms:
            if q in r['name'] or r['name'] in q or r['type'] in q:
                results.append({'floor': floor, 'name': r['name'], 'type': r['type'], 'x': r['x']+r['w']/2, 'y': r['y']+r['h']/2})
    return jsonify(results[:10])

@app.route('/api/nav/floors')
def api_nav_floors():
    return jsonify(list(floor_data.FLOOR_ROOMS.keys()))



# ========== API - Admin Members ==========
@app.route('/api/admin/orders')
@login_required
def api_admin_orders():
    if session.get('role') not in ('admin','super_admin','tenant_admin'):
        return jsonify(ok=False, error='权限不足')
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    status = request.args.get('status', '')
    otype = request.args.get('type', '')
    conn = get_db()
    sql = "SELECT * FROM work_orders"
    params = []
    where = []
    if status:
        where.append("status=?")
        params.append(status)
    if otype:
        where.append("type=?")
        params.append(otype)
    if where:
        sql += " WHERE " + " AND ".join(where)
    count = conn.execute("SELECT COUNT(*) FROM (" + sql + ")", params).fetchone()[0]
    rows = conn.execute(sql + " ORDER BY created_at DESC LIMIT ? OFFSET ?", params + [limit, (page-1)*limit]).fetchall()
    conn.close()
    items = [dict(r) for r in rows]
    return jsonify(ok=True, items=items, total=count)

@app.route('/api/admin/business-stats')
@login_required
def api_admin_business_stats():
    """业务中心统计：各类型工单数量汇总"""
    if session.get('role') not in ('admin','super_admin','tenant_admin'):
        return jsonify(ok=False, error='权限不足')
    conn = get_db()
    _ensure_tables(conn)
    types = ['场地看场', '商务意向', '团建定制', '入驻申请', '活动排期', '场地预定', '报修', '投诉建议', '人工客服']
    stats = {}
    for t in types:
        pending = conn.execute("SELECT COUNT(*) FROM work_orders WHERE type=? AND status='pending'", (t,)).fetchone()[0]
        total = conn.execute("SELECT COUNT(*) FROM work_orders WHERE type=?", (t,)).fetchone()[0]
        stats[t] = {'pending': pending, 'total': total}
    conn.close()
    return jsonify(ok=True, data=stats)

@app.route('/api/admin/orders/<int:order_id>', methods=['PUT'])
@login_required
def api_admin_update_order(order_id):
    if session.get('role') not in ('admin','super_admin','tenant_admin'):
        return jsonify(ok=False, error='权限不足')
    data = request.get_json()
    status = data.get('status', '')
    if not status:
        return jsonify(ok=False, error='缺少状态')
    conn = get_db()
    conn.execute("UPDATE work_orders SET status=?, updated_at=datetime('now','localtime') WHERE id=?", (status, order_id))
    conn.commit()
    conn.close()
    return jsonify(ok=True)

@app.route('/api/admin/members')
@login_required
def api_admin_members():
    if session.get('role') not in ('admin','super_admin'):
        return jsonify(ok=False, error='权限不足')
    search = request.args.get('search', '')
    level = request.args.get('level', '')
    conn = get_db()
    q = "SELECT id, display_name, phone, points, membership_level, created_at FROM users WHERE role IN ('user','tenant_admin')"
    args = []
    if search:
        q += " AND (phone LIKE ? OR display_name LIKE ?)"
        args.extend([f'%{search}%', f'%{search}%'])
    if level:
        q += " AND membership_level=?"
        args.append(level)
    q += " ORDER BY id DESC"
    rows = conn.execute(q, args).fetchall()
    members = []
    for r in rows:
        cc = conn.execute("SELECT COUNT(*) FROM work_orders WHERE type='points_redeem' AND reporter_contact=?",(r['phone'],)).fetchone()[0]
        members.append({
            'id': r['id'], 'display_name': r['display_name'], 'phone': r['phone'],
            'points': r['points'], 'membership_level': r['membership_level'],
            'created_at': str(r['created_at'])[:10] if r['created_at'] else '-',
            'coupon_count': cc
        })
    # Stats
    total = conn.execute("SELECT COUNT(*) FROM users WHERE role IN ('user','tenant_admin')").fetchone()[0]
    today = conn.execute("SELECT COUNT(*) FROM users WHERE role IN ('user','tenant_admin') AND date(created_at)=date('now','localtime')").fetchone()[0]
    diamond = conn.execute("SELECT COUNT(*) FROM users WHERE role IN ('user','tenant_admin') AND membership_level='钻石卡'").fetchone()[0]
    gold = conn.execute("SELECT COUNT(*) FROM users WHERE role IN ('user','tenant_admin') AND membership_level='金卡'").fetchone()[0]
    conn.close()
    return jsonify(ok=True, members=members, stats={'total':total,'today':today,'diamond':diamond,'gold':gold})

@app.route('/api/admin/member/<int:uid>', methods=['PUT'])
@login_required
def api_admin_member_update(uid):
    if session.get('role') not in ('admin','super_admin'):
        return jsonify(ok=False, error='权限不足')
    data = request.get_json()
    conn = get_db()
    conn.execute("UPDATE users SET display_name=?, phone=?, membership_level=?, points=? WHERE id=? AND tenant_id=?",
        (data.get('display_name',''), data.get('phone',''), data.get('membership_level','普卡'), int(data.get('points',0)), uid, session['tenant_id']))
    conn.commit()
    conn.close()
    return jsonify(ok=True)

@app.route('/api/admin/member/<int:uid>', methods=['DELETE'])
@login_required
def api_admin_member_delete(uid):
    if session.get('role') not in ('admin','super_admin'):
        return jsonify(ok=False, error='权限不足')
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id=? AND tenant_id=? AND role='user'",(uid,session['tenant_id']))
    conn.commit()
    conn.close()
    return jsonify(ok=True)

# ========== API - Venue Quotation ==========
@app.route('/api/venue/quotation', methods=['POST'])
@login_required
def api_venue_quotation():
    data = request.get_json()
    venue_type = data.get('venue_type', '')  # booth/classroom/lounge/ad
    date_str = data.get('date', '')
    hours = float(data.get('hours', 4))
    people = int(data.get('people', 20))
    extras = data.get('extras', [])  # list of str: ['tea','flower','photo']
    settlement = data.get('settlement', 'fixed')  # fixed/revenue/hybrid
    contact_name = data.get('contact_name', '')
    contact_phone = data.get('contact_phone', '')
    
    # Pricing tables
    pricing = {
        'booth': {
            'name': '多经摊位',
            'fixed': {'B1通道': 200, '1F中庭': 500, '户外广场': 300},
            'revenue_share': '营业额×15%-25%',
            'hybrid': '保底150元/天 + 超出部分×10%分成',
            'size': '3m×3m=9㎡（标准）',
            'default_pos': '1F中庭'
        },
        'classroom': {
            'name': '共享教室',
            'fixed': {'小型(15人)': 80, '中型(30人)': 120, '大型(50人)': 200},
            'default_size': '中型(30人)',
            'half_day_discount': 0.8,
            'full_day_discount': 0.7,
            'weekend_surcharge': 1.2
        },
        'lounge': {
            'name': '公共会客厅',
            'fixed': {'标准厅(20人)': 150, '精品厅(40人)': 300, 'VIP厅(60人)': 500},
            'default_size': '标准厅(20人)',
            'half_day': True,
            'full_day_discount': 0.8,
            'weekday_discount': 0.7
        },
        'ad': {
            'name': '广告位',
            'fixed': {'电梯口灯箱': 800, '中庭吊旗': 1500, 'LED大屏(天)': 300, '停车场道闸': 500, '卫生间镜面贴': 200, '扶梯侧板': 400},
            'monthly_discount': 0.88,
            'package': {'全媒体套餐': 12000}
        }
    }
    
    extras_pricing = {
        'tea': ('茶歇', 15),
        'flower': ('鲜花布置', 200),
        'photo': ('摄影摄像', 300),
        'print': ('物料代印', 2),
        'bartender': ('调酒服务', 50),
        'signwall': ('签到墙', 100),
        'table': ('桌子', 20),
        'shelf': ('展架', 30),
        'fridge': ('冷藏柜', 50),
        'design': ('设计制作', 300),
        'video': ('视频剪辑', 500),
    }
    
    subsidies = [
        '首周/首月5折（新商户）',
        '大学生创业前3天免费',
        '社区公益/邻里活动免租',
        '季度打包85折',
        '教育机构首月8折',
    ]
    
    p = pricing.get(venue_type)
    if not p:
        return jsonify(ok=False, error='未知场地类型，可选：booth/classroom/lounge/ad')
    
    # Calculate base
    base_price = 0
    price_detail = []
    
    if venue_type == 'booth':
        pos = data.get('position', p['default_pos'])
        rate = p['fixed'].get(pos, 500)
        days = max(1, int(data.get('days', 1)))
        base_price = rate * days
        price_detail.append(f'摊位位置：{pos}')
        price_detail.append(f'单价：¥{rate}/天 × {days}天 = ¥{base_price}')
        if settlement == 'revenue':
            price_detail.append(f'计费模式：流水分成 {p["revenue_share"]}（需接入收银系统）')
            base_price = 0  # Revenue share - can't pre-calculate
        elif settlement == 'hybrid':
            price_detail.append(f'计费模式：{p["hybrid"]}')
            base_price = 150 * days
    
    elif venue_type == 'classroom':
        size = data.get('size', p['default_size'])
        rate = p['fixed'].get(size, 120)
        base_price = rate * hours
        price_detail.append(f'教室规格：{size}')
        price_detail.append(f'单价：¥{rate}/小时 × {hours}小时 = ¥{base_price}')
        if hours >= 8:
            disc = p['full_day_discount']
            base_price *= disc
            price_detail.append(f'全天包场{int(disc*100)}折 → ¥{int(base_price)}')
        elif hours >= 4:
            disc = p['half_day_discount']
            base_price *= disc
            price_detail.append(f'半天包场{int(disc*100)}折 → ¥{int(base_price)}')
        # Check weekend
        if date_str:
            try:
                dt = datetime.strptime(date_str, '%Y-%m-%d')
                if dt.weekday() >= 5:
                    base_price = int(base_price * p['weekend_surcharge'])
                    price_detail.append(f'周末加价20% → ¥{base_price}')
            except:
                pass
    
    elif venue_type == 'lounge':
        size = data.get('size', p['default_size'])
        rate = p['fixed'].get(size, 150)
        base_price = rate  # per half day by default
        price_detail.append(f'会客厅规格：{size}')
        price_detail.append(f'半天单价：¥{rate}')
        if hours >= 8:
            base_price = int(rate * 2 * p['full_day_discount'])
            price_detail.append(f'全天{int(p["full_day_discount"]*100)}折 → ¥{base_price}')
        # Weekday discount
        if date_str:
            try:
                dt = datetime.strptime(date_str, '%Y-%m-%d')
                if dt.weekday() < 5:
                    base_price = int(base_price * p['weekday_discount'])
                    price_detail.append(f'工作日{int(p["weekday_discount"]*100)}折 → ¥{base_price}')
            except:
                pass
    
    elif venue_type == 'ad':
        ad_type = data.get('ad_type', '电梯口灯箱')
        weeks = max(1, int(data.get('weeks', 1)))
        rate = p['fixed'].get(ad_type, 800)
        base_price = rate * weeks
        price_detail.append(f'广告位类型：{ad_type}')
        price_detail.append(f'单价：¥{rate}/周 × {weeks}周 = ¥{base_price}')
        if weeks >= 4:
            base_price = int(base_price * p['monthly_discount'])
            price_detail.append(f'月租{int(p["monthly_discount"]*100)}折 → ¥{base_price}')
    
    # Extras
    extras_total = 0
    extras_list = []
    for ext in extras:
        if ext in extras_pricing:
            ename, eprice = extras_pricing[ext]
            extras_total += eprice
            extras_list.append(f'+ {ename}: ¥{eprice}')
    if extras_list:
        price_detail.append(f'增值服务：{"  ".join(extras_list)}（共¥{extras_total}）')
    
    total = base_price + extras_total
    
    # Build quotation
    order_data = {
        'type': 'venue_quotation',
        'venue_type': venue_type,
        'venue_name': p['name'],
        'date': date_str or '待定',
        'hours': hours,
        'people': people,
        'settlement': settlement,
        'base_price': base_price,
        'extras_total': extras_total,
        'total': total,
        'price_detail': price_detail,
        'subsidies': subsidies,
        'contact_name': contact_name,
        'contact_phone': contact_phone,
    }
    
    # Save to work_orders as lead
    tid = session['tenant_id']
    conn = get_db()
    conn.execute(
        "INSERT INTO work_orders (tenant_id, type, title, description, priority, status, reporter, reporter_contact) VALUES (?,?,?,?,?,?,?,?)",
        (tid, 'venue_quotation', f'场地报价：{p["name"]}（{date_str or "待定"}）',
         json.dumps(order_data, ensure_ascii=False),
         'normal', 'pending', contact_name or session.get('display_name', ''), contact_phone)
    )
    conn.commit()
    conn.close()
    
    return jsonify(ok=True, quotation=order_data)

# ========== API - Member Portal ==========
@app.route('/api/member/portal', methods=['POST'])
def api_member_portal():
    phone = request.json.get('phone', '').strip()
    if not phone or len(phone) < 11:
        return jsonify(ok=False, error='请输入正确的手机号')
    conn = get_db()
    user = conn.execute(
        'SELECT id, username, display_name, phone, points, membership_level FROM users WHERE phone=?',
        (phone,)
    ).fetchone()
    if not user:
        conn.close()
        return jsonify(ok=False, error='未找到该手机号的会员')
    
    level_info = {
        '普卡': {'discount': '98折', 'discount_rate': 0.98, 'min_points': 0, 'next_level': '银卡', 'next_points': 2000, 'desc': '消费1元=1积分'},
        '银卡': {'discount': '95折', 'discount_rate': 0.95, 'min_points': 2000, 'next_level': '金卡', 'next_points': 5000, 'desc': '每月1张停车券、生日月双倍积分'},
        '金卡': {'discount': '9折', 'discount_rate': 0.90, 'min_points': 5000, 'next_level': '钻石卡', 'next_points': 20000, 'desc': '周二会员日额外95折、每月3张停车券、生日月专属礼'},
        '钻石卡': {'discount': '88折', 'discount_rate': 0.88, 'min_points': 20000, 'next_level': None, 'next_points': None, 'desc': '免费停车、VIP休息室、优先预定、专属客服'},
    }
    
    level = user['membership_level'] or '普卡'
    info = level_info.get(level, level_info['普卡'])
    points = user['points'] or 0
    
    # Upgrade distance
    upgrade = None
    if info['next_level']:
        gap_points = info['next_points'] - points
        need_spend = max(0, gap_points)  # 1 yuan = 1 point
        upgrade = {
            'current_level': level,
            'next_level': info['next_level'],
            'current_points': points,
            'required_points': info['next_points'],
            'points_needed': max(0, gap_points),
            'spend_needed': max(0, gap_points),
            'progress_percent': round(min(100, points / info['next_points'] * 100), 1)
        }
    
    # Coupon status (from claimedCoupons in memory, we store in DB)
    # Simple: check if any venue quotation orders for this phone indicate coupons
    coupons_on_file = conn.execute(
        "SELECT COUNT(*) as c FROM work_orders WHERE reporter_contact=? AND type='venue_quotation'",
        (phone,)
    ).fetchone()
    
    # Gift recommendations based on points
    gift_catalog = [
        {'id': 1, 'name': '停车券', 'cost': 500, 'value': 10},
        {'id': 2, 'name': '海江食集满减券', 'cost': 800, 'value': 10},
        {'id': 3, 'name': '瑞幸咖啡饮品券', 'cost': 1000, 'value': 35},
        {'id': 4, 'name': 'SFC上影电影票', 'cost': 2000, 'value': 45},
        {'id': 5, 'name': '朱光玉火锅50元券', 'cost': 3000, 'value': 50},
        {'id': 6, 'name': '泡泡米儿童体验课', 'cost': 5000, 'value': 49},
        {'id': 7, 'name': '华为授权店30元券', 'cost': 8000, 'value': 30},
        {'id': 8, 'name': '200元购物卡', 'cost': 10000, 'value': 200},
        {'id': 9, 'name': '哇咔健身周卡', 'cost': 15000, 'value': 39},
    ]
    
    affordable = [g for g in gift_catalog if points >= g['cost']]
    closest = None
    for g in gift_catalog:
        if g['cost'] > points:
            closest = g
            break
    
    # Best value gift among affordable
    best_value = max(affordable, key=lambda g: g['value'] / g['cost'] * 1000) if affordable else None
    
    conn.close()
    
    result = {
        'display_name': user['display_name'],
        'phone': user['phone'],
        'points': points,
        'membership_level': level,
        'discount': info['discount'],
        'discount_rate': info['discount_rate'],
        'desc': info['desc'],
        'upgrade': upgrade,
        'affordable_gifts': [{'id': g['id'], 'name': g['name'], 'cost': g['cost'], 'value': g['value']} for g in affordable],
        'best_value_gift': {'name': best_value['name'], 'cost': best_value['cost'], 'value': best_value['value']} if best_value else None,
        'closest_gift': {'name': closest['name'], 'cost': closest['cost'], 'value': closest['value'], 'points_short': closest['cost'] - points} if closest else None,
        'points_expiry_hint': '积分有效期为获得之日起24个月，到期前30天短信提醒'
    }
    
    return jsonify(ok=True, member=result)

# ========== API - Member Register ==========

# ========== API - Member Coupons ==========
@app.route('/api/member/coupons', methods=['POST'])
def api_member_coupons():
    phone = request.json.get('phone', '').strip()
    if not phone or len(phone) < 11:
        return jsonify(ok=False, error='请输入正确的手机号')
    conn = get_db()
    rows = conn.execute(
        "SELECT description, created_at FROM work_orders WHERE type='points_redeem' AND reporter_contact=? ORDER BY id DESC LIMIT 50",
        (phone,)
    ).fetchall()
    conn.close()
    coupons = []
    for r in rows:
        try:
            d = json.loads(r[0])
            coupons.append({'code': d.get('code', '?'), 'item': d.get('item', '?'), 'time': (d.get('time') or str(r[1]))[:10]})
        except:
            coupons.append({'code': '?', 'item': '兑换记录', 'time': str(r[1])[:10] if r[1] else '?'})
    return jsonify(ok=True, coupons=coupons)

@app.route('/api/member/claim-coupon', methods=['POST'])
def api_member_claim_coupon():
    """领取优惠券（后端持久化，防重复）"""
    phone = request.json.get('phone', '').strip()
    offer_id = request.json.get('offer_id')
    shop_name = request.json.get('shop_name', '')
    label = request.json.get('label', '')
    amount = request.json.get('amount', 0)
    if not phone or not offer_id:
        return jsonify(ok=False, error='参数不完整')
    conn = get_db()
    _ensure_tables(conn)
    # 检查是否已领取
    existing = conn.execute(
        "SELECT id FROM coupon_claims WHERE user_phone=? AND offer_id=?",
        (phone, offer_id)
    ).fetchone()
    if existing:
        conn.close()
        return jsonify(ok=False, error='您已领取过该优惠券')
    conn.execute(
        "INSERT INTO coupon_claims (user_phone,offer_id,shop_name,label,amount) VALUES (?,?,?,?,?)",
        (phone, offer_id, shop_name, label, amount)
    )
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={'message': '领取成功！'})

@app.route('/api/member/my-coupons', methods=['POST'])
def api_member_my_coupons():
    """我的优惠券（含offers领取 + 积分兑换）"""
    phone = request.json.get('phone', '').strip()
    if not phone:
        return jsonify(ok=False, error='请输入手机号')
    conn = get_db()
    _ensure_tables(conn)
    # 已领取的优惠券
    claimed = conn.execute(
        "SELECT * FROM coupon_claims WHERE user_phone=? ORDER BY claimed_at DESC",
        (phone,)
    ).fetchall()
    # 积分兑换记录（保留原有逻辑）
    orders = conn.execute(
        "SELECT description, created_at FROM work_orders WHERE type='points_redeem' AND reporter_contact=? ORDER BY id DESC LIMIT 50",
        (phone,)
    ).fetchall()
    conn.close()
    coupons = []
    claimed_ids = set()
    for c in claimed:
        claimed_ids.add(c['offer_id'])
        coupons.append({
            'offer_id': c['offer_id'], 'shop_name': c['shop_name'],
            'label': c['label'], 'amount': c['amount'],
            'time': str(c['claimed_at'])[:10], 'type': 'claim'
        })
    for r in orders:
        try:
            d = json.loads(r[0])
            coupons.append({'code': d.get('code','?'), 'item': d.get('item','?'), 'time': str(r[1])[:10], 'type': 'redeem'})
        except:
            pass
    return jsonify(ok=True, coupons=coupons, claimed_ids=list(claimed_ids))

@app.route('/api/member/bind-phone', methods=['POST'])
def api_member_bind_phone():
    """微信用户绑定手机号（更新当前 session 用户的 phone 字段，不切换账号）"""
    uid = session.get('user_id')
    if not uid:
        return jsonify(ok=False, error='请先登录')
    phone = request.json.get('phone', '').strip()
    if not phone or len(phone) < 11:
        return jsonify(ok=False, error='请输入正确的手机号')
    conn = get_db()
    _ensure_tables(conn)
    user = conn.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
    if not user:
        conn.close()
        return jsonify(ok=False, error='用户不存在')
    # 检查手机号是否已被其他人绑定
    other = conn.execute("SELECT id, display_name FROM users WHERE phone=? AND id!=?", (phone, uid)).fetchone()
    if other:
        conn.close()
        return jsonify(ok=False, error=f'该手机号已被账号"{other["display_name"]}"绑定，请联系客服处理')
    conn.execute("UPDATE users SET phone=? WHERE id=?", (phone, uid))
    conn.commit()
    # 查询完整会员信息
    mem = conn.execute(
        'SELECT display_name, phone, points, membership_level, discount, wx_openid, headimgurl FROM users WHERE id=?',
        (uid,)
    ).fetchone()
    conn.close()
    session['phone'] = phone
    return jsonify(ok=True, user={
        'id': uid, 'display_name': mem['display_name'], 'phone': phone,
        'points': mem['points'], 'membership_level': mem['membership_level'],
        'discount': mem['discount'], 'wx_openid': mem['wx_openid'],
        'headimgurl': mem['headimgurl']
    })

@app.route('/api/member/register', methods=['POST'])
def api_member_register():
    data = request.get_json()
    display_name = data.get('display_name', '').strip()
    phone = data.get('phone', '').strip()
    if not display_name or len(display_name) < 1:
        return jsonify(ok=False, error='请输入姓名')
    if not phone or len(phone) != 11 or not phone.startswith('1'):
        return jsonify(ok=False, error='请输入正确的11位手机号')
    conn = get_db()
    exist = conn.execute('SELECT id FROM users WHERE phone=?', (phone,)).fetchone()
    if exist:
        conn.close()
        return jsonify(ok=False, error='该手机号已注册会员')
    import hashlib
    pw_hash = hashlib.sha256(('member'+phone).encode()).hexdigest()
    uname = 'm'+phone
    conn.execute(
        'INSERT INTO users (tenant_id, username, password_hash, display_name, role, phone, points, membership_level) VALUES (?,?,?,?,?,?,?,?)',
        (1, uname, pw_hash, display_name, 'user', phone, 500, '普卡'))
    conn.commit()
    uid = conn.execute('SELECT id FROM users WHERE phone=?', (phone,)).fetchone()[0]
    conn.close()
    return jsonify(ok=True, user={
        'id': uid,
        'display_name': display_name,
        'phone': phone,
        'points': 500,
        'membership_level': '普卡',
        'discount': '98',
        'discount_desc': '普卡 98折'
    })

# ========== API - Points Redeem ==========
@app.route('/api/member/redeem', methods=['POST'])
def api_member_redeem():
    phone = request.json.get('phone', '').strip()
    redeem_id = request.json.get('redeem_id', 0)
    if not phone or len(phone) < 11:
        return jsonify(ok=False, error='请输入正确的手机号')
    conn = get_db()
    user = conn.execute('SELECT id, display_name, phone, points, membership_level FROM users WHERE phone=?', (phone,)).fetchone()
    if not user:
        conn.close()
        return jsonify(ok=False, error='未找到该手机号的会员')

    redeem_catalog = {
        1: {'name': '停车券', 'cost': 500, 'code_prefix': 'PARK', 'desc': '抵扣2小时停车费'},
        2: {'name': '海江食集满50减10券', 'cost': 800, 'code_prefix': 'B1CP', 'desc': '海江食集满50减10'},
        3: {'name': '瑞幸咖啡饮品券', 'cost': 1000, 'code_prefix': 'SBUX', 'desc': '中杯饮品一杯'},
        4: {'name': 'SFC上影电影票', 'cost': 2000, 'code_prefix': 'MOVI', 'desc': 'SFC上影影城通用电影票一张'},
        5: {'name': '朱光玉火锅50元券', 'cost': 3000, 'code_prefix': 'ZGY', 'desc': '朱光玉火锅消费抵用50元'},
        6: {'name': '泡泡米儿童体验课', 'cost': 5000, 'code_prefix': 'KID', 'desc': '泡泡米儿童体验课一节'},
        7: {'name': '华为授权店30元券', 'cost': 8000, 'code_prefix': 'HW', 'desc': '华为授权店30元代金券'},
        8: {'name': '200元购物卡', 'cost': 10000, 'code_prefix': 'CARD', 'desc': '海江新天地全场通用购物卡'},
        9: {'name': '哇咔健身周卡', 'cost': 15000, 'code_prefix': 'FIT', 'desc': '哇咔健身体验周卡'},
    }

    cat = redeem_catalog.get(redeem_id)
    if not cat:
        conn.close()
        return jsonify(ok=False, error='无效的兑换项目，可用ID：1=停车券 2=海江食集券 3=瑞幸咖啡券 4=SFC电影票 5=朱光玉火锅券 6=泡泡米体验课 7=华为30元券 8=购物卡 9=哇咔健身周卡')

    if user['points'] < cat['cost']:
        gap = cat['cost'] - user['points']
        closest = None
        for k, v in sorted(redeem_catalog.items(), key=lambda x: x[1]['cost']):
            if v['cost'] <= user['points']:
                closest = v
        hint = ''
        if closest:
            hint = f'您的积分可以兑换：{closest["name"]}（{closest["cost"]}分）'
        conn.close()
        return jsonify(ok=False, error=f'积分不足！需要{cat["cost"]}分，当前{user["points"]}分，还差{gap}分。{hint}')

    # Deduct points
    now = datetime.now()
    code_num = str(int(time.time()))[-6:]
    coupon_code = f'{cat["code_prefix"]}{code_num}'
    new_points = user['points'] - cat['cost']

    conn.execute('UPDATE users SET points=? WHERE phone=?', (new_points, phone))
    conn.execute(
        'INSERT INTO work_orders (tenant_id, type, title, description, priority, status, reporter_contact) VALUES (?,?,?,?,?,?,?)',
        (1, 'points_redeem', f'积分兑换：{cat["name"]}',
         json.dumps({'phone': phone, 'redeem_id': redeem_id, 'item': cat['name'], 'cost': cat['cost'], 'code': coupon_code, 'before_points': user['points'], 'after_points': new_points, 'time': now.isoformat()}, ensure_ascii=False),
         'normal', 'resolved', phone)
    )
    conn.commit()
    conn.close()

    return jsonify(ok=True, redemption={
        'display_name': user['display_name'],
        'item': cat['name'],
        'cost': cat['cost'],
        'before_points': user['points'],
        'after_points': new_points,
        'coupon_code': coupon_code,
        'desc': cat['desc'],
        'time': now.strftime('%Y-%m-%d %H:%M'),
    })

# ========== API - Member Lookup ==========
@app.route('/api/member/lookup', methods=['POST'])
def api_member_lookup():
    phone = request.json.get('phone','').strip()
    if not phone or len(phone) < 11:
        return jsonify(ok=False, error='请输入正确的11位手机号')
    conn = get_db()
    user = conn.execute(
        'SELECT id, username, display_name, phone, points, membership_level FROM users WHERE phone=?',
        (phone,)
    ).fetchone()
    conn.close()
    if not user:
        return jsonify(ok=False, error='未找到该手机号的会员，请确认号码或至服务台注册')
    level_info = {
        '普卡': {'discount': '98折', 'desc': '消费1元=1积分，无额外权益'},
        '银卡': {'discount': '95折', 'desc': '每月1张停车券、生日月双倍积分'},
        '金卡': {'discount': '9折', 'desc': '每周二会员日额外95折、每月3张停车券、生日月专属礼'},
        '钻石卡': {'discount': '88折', 'desc': '免费停车、VIP休息室、优先预定、专属客服'},
    }
    level = user['membership_level'] or '普卡'
    info = level_info.get(level, level_info['普卡'])
    return jsonify(ok=True, member={
        'display_name': user['display_name'],
        'phone': user['phone'],
        'points': user['points'],
        'membership_level': level,
        'discount': info['discount'],
        'desc': info['desc'],
        'can_use_double_points': 'birthday' in info['desc'].lower()
    })
# ========== API - Dashboard ==========
@app.route('/api/dashboard')
@admin_required
def api_dashboard():
    tid = session['tenant_id']
    conn = get_db()
    today_chats = conn.execute("SELECT COUNT(*) FROM conversations WHERE tenant_id=? AND created_at >= date('now','localtime')", (tid,)).fetchone()[0] or 0
    active_members = conn.execute("SELECT COUNT(*) FROM users WHERE tenant_id=? AND role='user'", (tid,)).fetchone()[0] or 0
    total_orders = conn.execute("SELECT COUNT(*) FROM work_orders WHERE tenant_id=?", (tid,)).fetchone()[0] or 0
    pending_orders = conn.execute("SELECT COUNT(*) FROM work_orders WHERE tenant_id=? AND status='pending'", (tid,)).fetchone()[0] or 0
    activity_count = conn.execute("SELECT COUNT(*) FROM activities", ()).fetchone()[0] or 0
    reg_count = conn.execute("SELECT COUNT(*) FROM registrations", ()).fetchone()[0] or 0
    acts = conn.execute("SELECT id,title,enrolled FROM activities WHERE status='open' ORDER BY enrolled DESC LIMIT 5").fetchall()
    conn.close()
    return jsonify(ok=True,
        today_chats=today_chats,
        active_members=active_members,
        total_orders=total_orders,
        pending_orders=pending_orders,
        activity_count=activity_count,
        reg_count=reg_count,
        satisfaction='4.8',
        ai_rate='82%',
        order_done_rate='91%',
        hot_activities=[dict(r) for r in acts]
    )

@app.route('/api/users', methods=['GET','POST'])
@admin_required
def api_users():
    tid = session['tenant_id']
    conn = get_db()
    if request.method == 'GET':
        rows = conn.execute("SELECT id, username, display_name, role, created_at FROM users WHERE tenant_id=?", (tid,)).fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    data = request.get_json()
    conn.execute(
        "INSERT INTO users (tenant_id, username, password_hash, display_name, role) VALUES (?,?,?,?,?)",
        (tid, data['username'], hashlib.sha256(data.get('password','123456').encode()).hexdigest(),
         data.get('display_name',''), data.get('role','user'))
    )
    conn.commit(); conn.close()
    return jsonify(ok=True)

@app.route('/api/tenants', methods=['GET'])
@super_admin_required
def api_tenants():
    conn = get_db()
    rows = conn.execute("SELECT * FROM tenants ORDER BY id").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/tenants/<int:tid>', methods=['PUT'])
@super_admin_required
def api_tenant_update(tid):
    data = request.get_json()
    conn = get_db()
    sets = []; vals = []
    for f in ['name','contact','plan','monthly_quota','status','phone','address']:
        if f in data:
            sets.append(f'{f}=?')
            vals.append(data[f])
    if sets:
        vals.append(tid)
        conn.execute(f"UPDATE tenants SET {','.join(sets)} WHERE id=?", vals)
    conn.commit(); conn.close()
    return jsonify(ok=True)

# ============ 微信 JSSDK 签名 ============
WX_APPID = 'wxbdd219b39de37798'
WX_APPSECRET = os.environ.get('WX_APPSECRET', '')
# 百度语音识别
BAIDU_ASR_KEY = os.environ.get('BAIDU_ASR_KEY', '')
BAIDU_ASR_SECRET = os.environ.get('BAIDU_ASR_SECRET', '')
_wx_token_cache = {'token': '', 'expires': 0}
_wx_ticket_cache = {'ticket': '', 'expires': 0}

def _wx_get_access_token():
    now = time.time()
    if _wx_token_cache['token'] and _wx_token_cache['expires'] > now + 300:
        return _wx_token_cache['token']
    if not WX_APPSECRET:
        return ''
    try:
        import urllib.request, urllib.error
        url = f'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WX_APPID}&secret={WX_APPSECRET}'
        resp = urllib.request.urlopen(url, timeout=10)
        data = json.loads(resp.read())
        if 'access_token' in data:
            _wx_token_cache['token'] = data['access_token']
            _wx_token_cache['expires'] = now + data.get('expires_in', 7200)
            return _wx_token_cache['token']
    except Exception as e:
        print(f'[WX] get token error: {e}')
    return _wx_token_cache.get('token', '')

def _wx_get_jsapi_ticket():
    now = time.time()
    if _wx_ticket_cache['ticket'] and _wx_ticket_cache['expires'] > now + 300:
        return _wx_ticket_cache['ticket']
    token = _wx_get_access_token()
    if not token:
        return ''
    try:
        import urllib.request
        url = f'https://api.weixin.qq.com/cgi-bin/ticket/getticket?access_token={token}&type=jsapi'
        resp = urllib.request.urlopen(url, timeout=10)
        data = json.loads(resp.read())
        if data.get('errcode') == 0:
            _wx_ticket_cache['ticket'] = data['ticket']
            _wx_ticket_cache['expires'] = now + data.get('expires_in', 7200)
            return _wx_ticket_cache['ticket']
    except Exception as e:
        print(f'[WX] get ticket error: {e}')
    return _wx_ticket_cache.get('ticket', '')

@app.route('/api/wx-config')
def api_wx_config():
    url = request.args.get('url', request.headers.get('Referer', ''))
    ticket = _wx_get_jsapi_ticket()
    if not ticket:
        return jsonify(ok=False, error='ticket unavailable')
    nonce = secrets.token_hex(16)
    ts = int(time.time())
    raw = f'jsapi_ticket={ticket}&noncestr={nonce}&timestamp={ts}&url={url}'
    sig = hashlib.sha1(raw.encode()).hexdigest()
    return jsonify(ok=True, appId=WX_APPID, timestamp=ts, nonceStr=nonce, signature=sig)

# ============ 微信网页授权 ============
@app.route('/api/wx-auth', methods=['POST'])
def api_wx_auth():
    """微信网页授权 — 用 code 换 openid，自动注册/登录"""
    if not WX_APPSECRET:
        return jsonify(ok=False, error='未配置微信密钥')
    data = request.get_json()
    code = data.get('code', '').strip() if data else ''
    if not code:
        return jsonify(ok=False, error='缺少授权 code')
    try:
        import urllib.request, urllib.parse
        # Step 1: code → access_token + openid
        token_url = 'https://api.weixin.qq.com/sns/oauth2/access_token?' + urllib.parse.urlencode({
            'appid': WX_APPID,
            'secret': WX_APPSECRET,
            'code': code,
            'grant_type': 'authorization_code'
        })
        resp = urllib.request.urlopen(token_url, timeout=10)
        token_data = json.loads(resp.read())
        if 'errcode' in token_data:
            return jsonify(ok=False, error=token_data.get('errmsg', '微信授权失败'))
        openid = token_data.get('openid', '')
        access_token = token_data.get('access_token', '')
        if not openid:
            return jsonify(ok=False, error='获取 openid 失败')

        # Step 2: 获取用户信息（昵称、头像）
        nickname = ''
        headimgurl = ''
        if access_token:
            try:
                info_url = 'https://api.weixin.qq.com/sns/userinfo?' + urllib.parse.urlencode({
                    'access_token': access_token,
                    'openid': openid,
                    'lang': 'zh_CN'
                })
                info_resp = urllib.request.urlopen(info_url, timeout=10)
                info_data = json.loads(info_resp.read())
                nickname = info_data.get('nickname', '')
                headimgurl = info_data.get('headimgurl', '')
            except:
                pass

        # Step 3: 查 users 表，有就返回，没有就注册
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE wx_openid=?', (openid,)).fetchone()
        if user:
            conn.close()
            session['user_id'] = user['id']
            session['tenant_id'] = user['tenant_id']
            session['role'] = user['role']
            session['display_name'] = user['display_name']
            session['phone'] = user['phone'] or ''
            session['headimgurl'] = headimgurl or user['headimgurl'] or ''
            return jsonify(ok=True, user={
                'id': user['id'],
                'display_name': user['display_name'],
                'phone': user['phone'] or '',
                'points': user['points'],
                'membership_level': user['membership_level'],
                'discount': user['discount'] or '98',
                'headimgurl': headimgurl or user['headimgurl'] or ''
            })

        # 新用户注册
        import hashlib
        pw_hash = hashlib.sha256(('wx_' + openid).encode()).hexdigest()
        display_name = nickname or ('微信用户' + openid[-6:])
        conn.execute(
            '''INSERT INTO users (tenant_id, username, password_hash, display_name, role, phone, points, membership_level, discount, wx_openid, headimgurl)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
            (1, 'wx_' + openid, pw_hash, display_name, 'user', '', 500, '普卡', '98', openid, headimgurl))
        conn.commit()
        uid = conn.execute('SELECT id FROM users WHERE wx_openid=?', (openid,)).fetchone()[0]
        conn.close()
        session['user_id'] = uid
        session['tenant_id'] = 1
        session['role'] = 'user'
        session['display_name'] = display_name
        session['phone'] = ''
        session['headimgurl'] = headimgurl
        return jsonify(ok=True, user={
            'id': uid,
            'display_name': display_name,
            'phone': '',
            'points': 500,
            'membership_level': '普卡',
            'discount': '98',
            'headimgurl': headimgurl
        })
    except Exception as e:
        print(f'[WX Auth] error: {e}')
        return jsonify(ok=False, error=str(e))

# ============ 会员二维码 ============
@app.route('/api/member/qrcode', methods=['GET'])
def api_member_qrcode():
    if not session.get('user_id'):
        return jsonify(ok=False, error='请先登录')
    try:
        import qrcode, io, base64
        from PIL import Image
        uid = session['user_id']
        qr_data = f'HJXTD://member/{uid}'
        qr = qrcode.QRCode(box_size=10, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color='#FF7B2C', back_color='#1C1C1E').convert('RGB').resize((280, 280))
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        b64 = base64.b64encode(buf.getvalue()).decode()
        return jsonify(ok=True, qr='data:image/png;base64,' + b64)
    except Exception as e:
        return jsonify(ok=False, error=str(e))

# ============ 通用语音识别（接收音频文件） ============
@app.route('/api/asr', methods=['POST'])
def api_asr():
    if 'audio' not in request.files:
        return jsonify(ok=False, error='未上传音频文件')
    audio_file = request.files['audio']
    tmp_dir = os.path.join(HERE, 'tmp_audio')
    os.makedirs(tmp_dir, exist_ok=True)
    ext = audio_file.filename.rsplit('.', 1)[-1].lower() if audio_file.filename and '.' in audio_file.filename else 'wav'
    raw_path = os.path.join(tmp_dir, f'voice_{int(time.time()*1000)}.{ext}')
    audio_file.save(raw_path)
    try:
        # 转成 16kHz mono PCM WAV
        wav_path = raw_path + '.wav'
        result = subprocess.run(
            ['/usr/bin/ffmpeg', '-y', '-i', raw_path, '-ar', '16000', '-ac', '1', '-f', 'wav', wav_path],
            capture_output=True, timeout=30
        )
        if result.returncode != 0 or not os.path.exists(wav_path):
            return jsonify(ok=False, error='音频转码失败')
        # 百度 ASR
        text = _baidu_asr(wav_path)
        # 清理临时文件
        for p in (raw_path, wav_path):
            try: os.remove(p)
            except: pass
        if text:
            return jsonify(ok=True, text=text)
        return jsonify(ok=False, error='未识别到语音内容')
    except Exception as e:
        for p in (raw_path, raw_path + '.wav'):
            try: os.remove(p)
            except: pass
        return jsonify(ok=False, error=str(e))

# ============ 微信语音处理 ============
@app.route('/api/wx-voice', methods=['POST'])
def api_wx_voice():
    """接收微信语音 serverId，下载并转文字"""
    data = request.get_json()
    server_id = data.get('serverId', '') if data else ''
    if not server_id:
        return jsonify(ok=False, error='missing serverId')
    
    token = _wx_get_access_token()
    if not token:
        return jsonify(ok=False, error='wechat token unavailable')
    
    # Download voice file from WeChat
    try:
        import urllib.request
        import tempfile
        url = f'https://api.weixin.qq.com/cgi-bin/media/get?access_token={token}&media_id={server_id}'
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=30)
        voice_data = resp.read()
        if not voice_data or len(voice_data) < 100:
            return jsonify(ok=False, error='voice file too small')
        
        # Save to temp file
        tmp = tempfile.NamedTemporaryFile(suffix='.amr', delete=False)
        tmp.write(voice_data)
        tmp.close()
        
        # Convert AMR to WAV/PCM using ffmpeg
        import subprocess
        wav_path = tmp.name + '.wav'
        subprocess.run(['/usr/bin/ffmpeg', '-y', '-i', tmp.name, '-ar', '16000', '-ac', '1', '-f', 'wav', wav_path],
                       capture_output=True, timeout=15)
        os.unlink(tmp.name)
        
        if not os.path.exists(wav_path) or os.path.getsize(wav_path) < 100:
            return jsonify(ok=False, error='voice conversion failed')
        
        # Baidu ASR
        text = _baidu_asr(wav_path)
        os.unlink(wav_path)
        
        if text:
            return jsonify(ok=True, text=text)
        else:
            return jsonify(ok=False, error='speech recognition failed')
            
    except Exception as e:
        print(f'[WX Voice] error: {e}')
        return jsonify(ok=False, error=str(e))


def _baidu_asr(wav_path):
    """百度语音识别"""
    if not BAIDU_ASR_KEY or not BAIDU_ASR_SECRET:
        print('[ASR] Baidu keys not configured')
        return None
    try:
        import urllib.request, urllib.parse
        # Get token
        token_url = 'https://aip.baidubce.com/oauth/2.0/token'
        token_data = urllib.parse.urlencode({
            'grant_type': 'client_credentials',
            'client_id': BAIDU_ASR_KEY,
            'client_secret': BAIDU_ASR_SECRET
        }).encode()
        resp = urllib.request.urlopen(token_url, data=token_data, timeout=10)
        token_info = json.loads(resp.read())
        asr_token = token_info.get('access_token', '')
        if not asr_token:
            print('[ASR] Failed to get Baidu token')
            return None
        
        # Read WAV
        with open(wav_path, 'rb') as f:
            speech = base64.b64encode(f.read()).decode()
        
        # Call ASR API
        asr_url = 'https://vop.baidu.com/server_api'
        asr_data = json.dumps({
            'format': 'wav',
            'rate': 16000,
            'channel': 1,
            'cuid': 'haijiang_cs',
            'token': asr_token,
            'speech': speech,
            'len': os.path.getsize(wav_path)
        }).encode()
        req = urllib.request.Request(asr_url, data=asr_data, headers={'Content-Type': 'application/json'})
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())
        
        if result.get('err_no') == 0 and result.get('result'):
            return result['result'][0]
        else:
            print(f'[ASR] Error: {result}')
            return None
    except Exception as e:
        print(f'[ASR] Exception: {e}')
        return None


@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory(os.path.join(HERE, 'static'), path)

def migrate_db():
    """幂等迁移：补齐历史表可能缺失的列，保证前后端字段契约一致。"""
    conn = get_db()
    try:
        for col in ['phone', 'address']:
            try:
                conn.execute(f"ALTER TABLE tenants ADD COLUMN {col} TEXT")
            except Exception:
                pass
        conn.commit()
    finally:
        conn.close()

migrate_db()

# ========== 活动报名API ==========

import uuid

@app.route('/api/activities', methods=['GET'])
def api_activities():
    '''活动列表'''
    tid = request.args.get('tenant_id', 1)
    cat = request.args.get('cat', 'all')
    conn = get_db()
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d')
    if cat == 'ongoing':
        c.execute('SELECT * FROM activities WHERE start_date <= ? AND end_date >= ? AND status="open" ORDER BY start_date', (now, now))
    elif cat == 'upcoming':
        c.execute('SELECT * FROM activities WHERE start_date > ? AND status="open" ORDER BY start_date', (now,))
    elif cat == 'past':
        c.execute('SELECT * FROM activities WHERE end_date < ? ORDER BY end_date DESC', (now,))
    else:
        c.execute('SELECT * FROM activities ORDER BY start_date')
    rows = c.fetchall()
    cols = ['id','title','desc','venue','start_date','end_date','gradient','cover_url','price','points_price','max_people','enrolled','status','created_at']
    acts = [dict(zip(cols, r)) for r in rows]
    conn.close()
    return jsonify(ok=True, data=acts)

@app.route('/api/activities/<int:aid>', methods=['GET'])
def api_activity_detail(aid):
    '''活动详情+场次列表'''
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM activities WHERE id=?', (aid,))
    r = c.fetchone()
    if not r:
        conn.close()
        return jsonify(ok=False, error='活动不存在'), 404
    cols = ['id','title','desc','venue','start_date','end_date','gradient','cover_url','price','points_price','max_people','enrolled','status','created_at']
    act = dict(zip(cols, r))
    c.execute('SELECT * FROM activity_sessions WHERE activity_id=? ORDER BY session_date, session_time', (aid,))
    sess_cols = ['id','activity_id','session_date','session_time','venue','max_people','enrolled','status']
    sessions = [dict(zip(sess_cols, s)) for s in c.fetchall()]
    conn.close()
    return jsonify(ok=True, activity=act, sessions=sessions)

@app.route('/api/activities/register', methods=['POST'])
def api_activity_register():
    '''活动报名'''
    data = request.get_json(force=True)
    aid = data.get('activity_id')
    sid = data.get('session_id')
    phone = data.get('phone', '').strip()
    name = data.get('name', '').strip()
    count = int(data.get('people_count', 1))
    pay_method = data.get('pay_method', 'none')  # none / pay / points

    if not aid or not sid or not phone or not name:
        return jsonify(ok=False, error='信息不完整'), 400

    conn = get_db()
    c = conn.cursor()

    # 查活动
    c.execute('SELECT * FROM activities WHERE id=?', (aid,))
    act = c.fetchone()
    if not act:
        conn.close()
        return jsonify(ok=False, error='活动不存在'), 404
    price = act[8] or 0
    points_price = act[9] or 0

    # 查场次
    c.execute('SELECT * FROM activity_sessions WHERE id=? AND activity_id=?', (sid, aid))
    sess = c.fetchone()
    if not sess:
        conn.close()
        return jsonify(ok=False, error='场次不存在'), 404
    # 列顺序: id, activity_id, session_date, session_time, venue, max_people, enrolled, status
    max_people = int(sess[5] or 0)
    enrolled = int(sess[6] or 0)
    if enrolled + count > max_people:
        conn.close()
        return jsonify(ok=False, error=f'名额不足，剩余{max_people - enrolled}个位置'), 400

    # 查用户
    c.execute('SELECT * FROM users WHERE username=?', (f'm{phone}',))
    user = c.fetchone()

    amount = price * count
    points_used = 0

    if pay_method == 'points':
        if not user:
            conn.close()
            return jsonify(ok=False, error='请先注册会员才能使用积分'), 400
        need_points = (points_price or price * 25) * count
        user_points = int(user[7] or 0)
        if user_points < need_points:
            conn.close()
            return jsonify(ok=False, error=f'积分不足，需要{need_points}分，当前{user_points}分'), 400
        points_used = need_points
        amount = 0
    elif pay_method == 'pay':
        if amount > 0 and user:
            # 会员折扣
            discount = 0.98
            level = user[8] or '普卡'
            if level == '银卡': discount = 0.95
            elif level == '金卡': discount = 0.9
            elif level == '钻石卡': discount = 0.88
            amount = round(amount * discount, 2)

    # 生成票号
    ticket_code = f'ACT{aid:03d}S{sid:02d}{uuid.uuid4().hex[:6].upper()}'
    reg_no = f'REG{datetime.now().strftime("%Y%m%d%H%M%S")}{uuid.uuid4().hex[:4].upper()}'

    c.execute('''INSERT INTO registrations (registration_no,activity_id,session_id,user_phone,user_name,people_count,amount,pay_method,points_used,status,ticket_code)
                 VALUES (?,?,?,?,?,?,?,?,?,"confirmed",?)''',
              (reg_no, aid, sid, phone, name, count, amount, pay_method, points_used, ticket_code))

    # 更新场次人数
    c.execute('UPDATE activity_sessions SET enrolled = enrolled + ? WHERE id=?', (count, sid))

    # 积分抵扣
    if points_used > 0:
        c.execute('UPDATE users SET points = points - ? WHERE username=?', (points_used, f'm{phone}'))

    conn.commit()

    result = {
        'registration_no': reg_no,
        'ticket_code': ticket_code,
        'activity_title': act[1],
        'session': f'{sess[2]} {sess[3]}',
        'venue': sess[4] if isinstance(sess[4], str) else act[3],
        'amount': amount,
        'points_used': points_used,
        'status': 'confirmed'
    }
    conn.close()
    return jsonify(ok=True, data=result)

@app.route('/api/activities/registrations', methods=['GET'])
def api_my_registrations():
    '''我的报名记录'''
    phone = request.args.get('phone', '').strip()
    if not phone:
        return jsonify(ok=False, error='请提供手机号'), 400
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT r.id, r.registration_no, r.activity_id, r.session_id, r.user_phone, r.user_name,
                        r.people_count, r.amount, r.pay_method, r.points_used, r.status, r.ticket_code,
                        r.created_at, a.title as activity_title, s.session_date, s.session_time
                 FROM registrations r
                 LEFT JOIN activities a ON r.activity_id = a.id
                 LEFT JOIN activity_sessions s ON r.session_id = s.id
                 WHERE r.user_phone = ?
                 ORDER BY r.created_at DESC''', (phone,))
    rows = c.fetchall()
    cols = ['id','registration_no','activity_id','session_id','user_phone','user_name','people_count','amount','pay_method','points_used','status','ticket_code','created_at','activity_title','session_date','session_time']
    conn.close()
    return jsonify(ok=True, data=[dict(zip(cols, r)) for r in rows])

@app.route('/api/activities/reschedule', methods=['POST'])
def api_activity_reschedule():
    '''改签'''
    data = request.get_json(force=True)
    reg_id = data.get('registration_id')
    new_session_id = data.get('new_session_id')
    if not reg_id or not new_session_id:
        return jsonify(ok=False, error='参数不完整'), 400
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM registrations WHERE id=?', (reg_id,))
    reg = c.fetchone()
    if not reg:
        conn.close()
        return jsonify(ok=False, error='报名记录不存在'), 404
    # registrations 列顺序: ... session_id[4], people_count[11], status[16]
    session_id = reg[4]
    people_count = reg[11] or 1
    if reg[16] == 'cancelled':
        conn.close()
        return jsonify(ok=False, error='已取消的订单不能改签'), 400
    # 减少旧场次人数
    c.execute('UPDATE activity_sessions SET enrolled = enrolled - ? WHERE id=?', (people_count, session_id))
    # 检查新场次是否满
    c.execute('SELECT * FROM activity_sessions WHERE id=?', (new_session_id,))
    ns = c.fetchone()
    if ns and int(ns[6] or 0) + people_count > int(ns[5] or 0):
        conn.close()
        return jsonify(ok=False, error='新场次名额不足'), 400
    # 改
    c.execute('UPDATE registrations SET session_id=?, updated_at=CURRENT_TIMESTAMP WHERE id=?', (new_session_id, reg_id))
    c.execute('UPDATE activity_sessions SET enrolled = enrolled + ? WHERE id=?', (people_count, new_session_id))
    conn.commit()
    conn.close()
    return jsonify(ok=True, message='改签成功')

@app.route('/api/activities/refund', methods=['POST'])
def api_activity_refund():
    '''退款申请 — 积分支付退积分，现金支付退等值积分'''
    data = request.get_json(force=True)
    reg_id = data.get('registration_id')
    reason = data.get('reason', '')
    if not reg_id:
        return jsonify(ok=False, error='请指定报名记录'), 400
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM registrations WHERE id=?', (reg_id,))
    reg = c.fetchone()
    if not reg:
        conn.close()
        return jsonify(ok=False, error='报名记录不存在'), 404
    # registrations 列顺序: id, tenant_id, registration_no, activity_id, session_id, event, name, phone, user_phone, user_name, count, people_count, note, amount, pay_method, points_used, status, ticket_code
    session_id = reg[4]
    user_phone = reg[8]
    people_count = reg[11] or 1
    amount = reg[13] or 0
    pay_method = reg[14] or 'none'
    points_used = reg[15] or 0
    status = reg[16]
    if status in ('cancelled', 'refunding'):
        conn.close()
        return jsonify(ok=False, error='已退款或已取消'), 400
    # 释放场次名额
    c.execute('UPDATE activity_sessions SET enrolled = enrolled - ? WHERE id=?', (people_count, session_id))
    # 退款处理
    refund_points = 0
    if pay_method == 'points':
        # 积分支付 → 退积分
        refund_points = points_used
        c.execute('UPDATE users SET points = points + ? WHERE username=?', (refund_points, f'm{user_phone}'))
    elif pay_method == 'pay':
        # 现金支付 → 退等值积分 (1元=25积分)
        refund_points = int(amount * 25)
        c.execute('UPDATE users SET points = points + ? WHERE username=?', (refund_points, f'm{user_phone}'))
    # 直接取消（不再 pending）
    c.execute("UPDATE registrations SET status='cancelled', updated_at=CURRENT_TIMESTAMP WHERE id=?", (reg_id,))
    conn.commit()
    conn.close()
    msg = f'退款成功，已退还{refund_points}积分。' if refund_points > 0 else '退款申请已提交。'
    return jsonify(ok=True, message=msg, refund_points=refund_points)

@app.route('/api/activities/ticket/<int:reg_id>', methods=['GET'])
def api_activity_ticket(reg_id):
    """获取电子凭证详情（含活动/场次/票号信息）"""
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT r.id, r.registration_no, r.activity_id, r.session_id, r.user_phone, r.user_name,
                        r.people_count, r.amount, r.pay_method, r.points_used, r.status, r.ticket_code,
                        r.created_at, a.title as activity_title, s.session_date, s.session_time, a.venue
                 FROM registrations r
                 JOIN activities a ON r.activity_id = a.id
                 JOIN activity_sessions s ON r.session_id = s.id
                 WHERE r.id=?''', (reg_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return jsonify(ok=False, error='报名记录不存在'), 404
    cols = ['id','registration_no','activity_id','session_id','user_phone','user_name','people_count','amount','pay_method','points_used','status','ticket_code','created_at','activity_title','session_date','session_time','venue']
    return jsonify(ok=True, ticket=dict(zip(cols, row)))


# ========== 后台活动管理 API ==========

@app.route('/api/admin/activities', methods=['POST'])
def admin_create_activity():
    data = request.get_json(force=True)
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO activities (title,"desc",venue,start_date,end_date,gradient,price,points_price,max_people,enrolled,status)
                 VALUES (?,?,?,?,?,?,?,?,?,0,"open")''',
              (data.get('title',''), data.get('desc',''), data.get('venue',''),
               data.get('start_date',''), data.get('end_date',''), data.get('gradient',''),
               data.get('price',0), data.get('points_price',0), data.get('max_people',100)))
    aid = c.lastrowid
    for s in data.get('sessions', []):
        c.execute('INSERT INTO activity_sessions (activity_id,session_date,session_time,venue,max_people,enrolled) VALUES (?,?,?,?,?,0)',
                  (aid, s.get('session_date',''), s.get('session_time',''), s.get('venue',''), s.get('max_people',50)))
    conn.commit()
    conn.close()
    return jsonify(ok=True, id=aid)

@app.route('/api/admin/activities/<int:aid>', methods=['PUT'])
def admin_update_activity(aid):
    data = request.get_json(force=True)
    conn = get_db()
    c = conn.cursor()
    # 支持部分更新
    fields = []
    vals = []
    for f in ['title','desc','venue','start_date','end_date','gradient','price','points_price','max_people','status']:
        if f in data:
            field_name = '"desc"' if f == 'desc' else f
            fields.append(f'{field_name}=?')
            vals.append(data[f])
    if fields:
        vals.append(aid)
        c.execute(f'UPDATE activities SET {",".join(fields)} WHERE id=?', vals)
    # 场次：全量替换
    if 'sessions' in data:
        c.execute('DELETE FROM activity_sessions WHERE activity_id=?', (aid,))
        for s in data['sessions']:
            c.execute('INSERT INTO activity_sessions (activity_id,session_date,session_time,venue,max_people,enrolled) VALUES (?,?,?,?,?,0)',
                      (aid, s.get('session_date',''), s.get('session_time',''), s.get('venue',''), s.get('max_people',50)))
    conn.commit()
    conn.close()
    return jsonify(ok=True)

@app.route('/api/admin/activities/<int:aid>', methods=['DELETE'])
def admin_delete_activity(aid):
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM activity_sessions WHERE activity_id=?', (aid,))
    c.execute('DELETE FROM registrations WHERE activity_id=?', (aid,))
    c.execute('DELETE FROM activities WHERE id=?', (aid,))
    conn.commit()
    conn.close()
    return jsonify(ok=True)

@app.route('/api/admin/registrations', methods=['GET'])
def admin_registrations():
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT r.*, a.title as activity_title, s.session_date, s.session_time
                 FROM registrations r
                 LEFT JOIN activities a ON r.activity_id = a.id
                 LEFT JOIN activity_sessions s ON r.session_id = s.id
                 ORDER BY r.created_at DESC LIMIT 200''')
    rows = c.fetchall()
    cols = ['id','registration_no','activity_id','session_id','user_phone','user_name','people_count','amount','pay_method','points_used','status','ticket_code','created_at','updated_at','activity_title','session_date','session_time']
    conn.close()
    return jsonify(ok=True, data=[dict(zip(cols, r)) for r in rows])


# ========== 安全响应头 ==========
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    if request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    return response


# ========== 数据表初始化 ==========
_init_lock = __import__('threading').Lock()
_init_done = False

# 跨进程文件锁：gunicorn 多 worker = 多进程，threading.Lock 仅防进程内并发，
# 无法防多进程同时初始化抢 SQLite 写锁。用 fcntl.flock 保证同一时刻只有一个进程执行初始化写段。
_INIT_LOCK_FILE = os.path.join(HERE, '.init_lock')
_init_lock_fd = None

def _acquire_init_flock():
    """获取跨进程初始化文件锁（阻塞直到拿到）。"""
    global _init_lock_fd
    if _init_lock_fd is None:
        _init_lock_fd = open(_INIT_LOCK_FILE, 'w')
    fcntl.flock(_init_lock_fd.fileno(), fcntl.LOCK_EX)
    return _init_lock_fd

def _release_init_flock():
    """释放跨进程初始化文件锁。"""
    global _init_lock_fd
    if _init_lock_fd is not None:
        try:
            fcntl.flock(_init_lock_fd.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass

def _ensure_tables(conn):
    """确保数据表存在并填充初始数据。表结构(DDL)并发安全；初始数据写入每个进程只跑一次，避免 gunicorn 多 worker 并发竞争 SQLite 锁。"""
    global _init_done
    if _init_done:
        return
    _acquire_init_flock()
    with _init_lock:
        if _init_done:
            _release_init_flock()
            return
        # --- shops ---
        conn.execute('''CREATE TABLE IF NOT EXISTS shops (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, floor TEXT, zone TEXT,
        category TEXT, tags TEXT, color TEXT, hours TEXT, phone TEXT,
        description TEXT, has_coupon INTEGER DEFAULT 0,
        coupon_condition INTEGER DEFAULT 0, coupon_amount INTEGER DEFAULT 0,
        coupon_expire TEXT, features TEXT
    )''')
        if conn.execute('SELECT COUNT(*) FROM shops').fetchone()[0] == 0:
            shops_data = [
                ('s001','瑞幸咖啡','1','1区','餐饮','咖啡,快取','#0051A8','10:00 - 22:00','021-5656 8888','瑞幸咖啡位于海江新天地1区 1F，主营咖啡、快取。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s002','多乐之日','1','1区','餐饮','烘焙,面包','#8B5A2B','10:00 - 22:00','021-5656 8888','多乐之日位于海江新天地1区 1F，主营烘焙、面包。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s003','麦当劳','1','1区','餐饮','快餐,汉堡','#D52B1E','10:00 - 22:00','021-5656 8888','麦当劳位于海江新天地1区 1F，主营快餐、汉堡。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s004','秀目眼镜','1','1区','零售','眼镜,验光','#4A90D9','10:00 - 22:00','021-5656 8888','秀目眼镜位于海江新天地1区 1F，主营眼镜、验光。精选好物与品牌，打造舒适惬意的购物体验。',1,200,30,'2026-12-31','线上线下同价,支持退换,会员积分'),
                ('s005','霸王茶姬','1','1区','餐饮','茶饮,新茶饮','#6E4B3A','10:00 - 22:00','021-5656 8888','霸王茶姬位于海江新天地1区 1F，主营茶饮、新茶饮。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s006','小杨生煎','1','1区','餐饮','生煎,小吃','#C0392B','10:00 - 22:00','021-5656 8888','小杨生煎位于海江新天地1区 1F，主营生煎、小吃。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s007','新贝乐','1','1区','餐饮','本帮菜,家常菜','#E85D04','10:00 - 22:00','021-5656 8888','新贝乐位于海江新天地1区 1F，主营本帮菜、家常菜。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s008','手心兔小吐司','1','1区','餐饮','吐司,烘焙','#C9975A','10:00 - 22:00','021-5656 8888','手心兔小吐司位于海江新天地1区 1F，主营吐司、烘焙。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s009','贵华嫂','1','1区','餐饮','小吃,面点','#E85D04','10:00 - 22:00','021-5656 8888','贵华嫂位于海江新天地1区 1F，主营小吃、面点。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s010','成都你六姐','1','1区','餐饮','川菜,江湖菜','#C2185B','10:00 - 22:00','021-5656 8888','成都你六姐位于海江新天地1区 1F，主营川菜、江湖菜。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s011','晨光文具','1','1区','零售','文具,办公','#4A90D9','10:00 - 22:00','021-5656 8888','晨光文具位于海江新天地1区 1F，主营文具、办公。精选好物与品牌，打造舒适惬意的购物体验。',1,200,30,'2026-12-31','线上线下同价,支持退换,会员积分'),
                ('s012','老盛兴汤包馆','1','1区','餐饮','汤包,小吃','#C0392B','10:00 - 22:00','021-5656 8888','老盛兴汤包馆位于海江新天地1区 1F，主营汤包、小吃。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s013','烧饼文化','1','1区','餐饮','烧饼,小吃','#E85D04','10:00 - 22:00','021-5656 8888','烧饼文化位于海江新天地1区 1F，主营烧饼、小吃。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s014','潮纪','1','1区','餐饮','潮汕,牛肉','#C2185B','10:00 - 22:00','021-5656 8888','潮纪位于海江新天地1区 1F，主营潮汕、牛肉。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s015','喜姐炸串','1','1区','餐饮','炸串,小吃','#E85D04','10:00 - 22:00','021-5656 8888','喜姐炸串位于海江新天地1区 1F，主营炸串、小吃。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s016','临榆炸鸡腿','1','1区','餐饮','炸鸡,小吃','#D52B1E','10:00 - 22:00','021-5656 8888','临榆炸鸡腿位于海江新天地1区 1F，主营炸鸡、小吃。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s017','银流咖啡','1','1区','餐饮','咖啡,轻食','#6F4E37','10:00 - 22:00','021-5656 8888','银流咖啡位于海江新天地1区 1F，主营咖啡、轻食。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s018','海江食集','1','1区','餐饮','美食广场,小吃集合','#E85D04','10:00 - 22:00','021-5656 8888','海江食集位于海江新天地1区 1F，主营美食广场、小吃集合。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s019','万酒堂','1','1区','零售','酒水,零售','#4A90D9','10:00 - 22:00','021-5656 8888','万酒堂位于海江新天地1区 1F，主营酒水、零售。精选好物与品牌，打造舒适惬意的购物体验。',1,200,30,'2026-12-31','线上线下同价,支持退换,会员积分'),
                ('s020','诺家智慧大药房','1','1区','生活服务','药房,健康','#3E8E41','10:00 - 21:00','021-5656 8888','诺家智慧大药房位于海江新天地1区 1F，主营药房、健康。贴心周到的生活服务，便捷周边日常所需。',1,0,5,'2026-12-31','专业服务,可预约'),
                ('s021','古康元','1','1区','生活服务','理疗,养生','#3E8E41','10:00 - 21:00','021-5656 8888','古康元位于海江新天地1区 1F，主营理疗、养生。贴心周到的生活服务，便捷周边日常所需。',1,0,5,'2026-12-31','专业服务,可预约'),
                ('s022','美甲美睫','1','1区','生活服务','美甲,美睫','#3E8E41','10:00 - 21:00','021-5656 8888','美甲美睫位于海江新天地1区 1F，主营美甲、美睫。贴心周到的生活服务，便捷周边日常所需。',1,0,5,'2026-12-31','专业服务,可预约'),
                ('s023','美肤盾','1','1区','生活服务','护肤,美容','#3E8E41','10:00 - 21:00','021-5656 8888','美肤盾位于海江新天地1区 1F，主营护肤、美容。贴心周到的生活服务，便捷周边日常所需。',1,0,5,'2026-12-31','专业服务,可预约'),
                ('s024','通信钟表','1','1区','生活服务','通讯,钟表','#3E8E41','10:00 - 21:00','021-5656 8888','通信钟表位于海江新天地1区 1F，主营通讯、钟表。贴心周到的生活服务，便捷周边日常所需。',1,0,5,'2026-12-31','专业服务,可预约'),
                ('s025','体彩','1','1区','生活服务','彩票,便民','#3E8E41','10:00 - 21:00','021-5656 8888','体彩位于海江新天地1区 1F，主营彩票、便民。贴心周到的生活服务，便捷周边日常所需。',1,0,5,'2026-12-31','专业服务,可预约'),
                ('s026','福彩','1','1区','生活服务','彩票,便民','#3E8E41','10:00 - 21:00','021-5656 8888','福彩位于海江新天地1区 1F，主营彩票、便民。贴心周到的生活服务，便捷周边日常所需。',1,0,5,'2026-12-31','专业服务,可预约'),
                ('s027','泡泡米儿童','2','1区','亲子','儿童娱乐,亲子','#E8809E','10:00 - 21:00','021-5656 8888','泡泡米儿童位于海江新天地1区 2F，主营儿童娱乐、亲子。亲子同乐的成长空间，陪伴孩子快乐探索世界。',1,100,20,'2026-12-31','亲子友好,可免费体验'),
                ('s028','小荧星艺校','2','1区','亲子','艺术培训,舞蹈','#E8809E','10:00 - 21:00','021-5656 8888','小荧星艺校位于海江新天地1区 2F，主营艺术培训、舞蹈。亲子同乐的成长空间，陪伴孩子快乐探索世界。',1,100,20,'2026-12-31','亲子友好,可免费体验'),
                ('s029','海江活动艺术中心','2','1区','娱乐','艺术中心,演出','#9B7BD4','10:00 - 22:00','021-5656 8888','海江活动艺术中心位于海江新天地1区 2F，主营艺术中心、演出。潮流娱乐聚场，释放精彩的昼夜生活。',1,0,30,'2026-12-31','可预约,适合聚会'),
                ('s030','雀王棋牌','3','1区','娱乐','棋牌,休闲','#9B7BD4','10:00 - 24:00','021-5656 8888','雀王棋牌位于海江新天地1区 3F，主营棋牌、休闲。潮流娱乐聚场，释放精彩的昼夜生活。',1,0,30,'2026-12-31','可预约,适合聚会'),
                ('s031','哇咔健身','3','1区','娱乐','健身,团课','#9B7BD4','10:00 - 22:00','021-5656 8888','哇咔健身位于海江新天地1区 3F，主营健身、团课。潮流娱乐聚场，释放精彩的昼夜生活。',1,0,30,'2026-12-31','可预约,适合聚会'),
                ('s032','锦光星耀桌球俱乐部','3','1区','娱乐','桌球,台球','#9B7BD4','10:00 - 22:00','021-5656 8888','锦光星耀桌球俱乐部位于海江新天地1区 3F，主营桌球、台球。潮流娱乐聚场，释放精彩的昼夜生活。',1,0,30,'2026-12-31','可预约,适合聚会'),
                ('s033','尊柜KTV/棋牌室','4','1区','娱乐','KTV,棋牌','#9B7BD4','18:00 - 02:00','021-5656 8888','尊柜KTV/棋牌室位于海江新天地1区 4F，主营KTV、棋牌。潮流娱乐聚场，释放精彩的昼夜生活。',1,0,30,'2026-12-31','可预约,适合聚会'),
                ('s034','徐妈串串','1','3区','餐饮','串串,川味','#E85D04','10:00 - 22:00','021-5656 8888','徐妈串串位于海江新天地3区 1F，主营串串、川味。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s035','泰士多','1','3区','餐饮','东南亚,料理','#E85D04','10:00 - 22:00','021-5656 8888','泰士多位于海江新天地3区 1F，主营东南亚、料理。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s036','刘栋梁大排档','1','3区','餐饮','大排档,夜宵','#E85D04','10:00 - 22:00','021-5656 8888','刘栋梁大排档位于海江新天地3区 1F，主营大排档、夜宵。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s037','星巴克','1','3区','餐饮','咖啡,第三空间','#00704A','10:00 - 22:00','021-5656 8888','星巴克位于海江新天地3区 1F，主营咖啡、第三空间。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s038','味千拉面','1','3区','餐饮','拉面,日式','#E60012','10:00 - 22:00','021-5656 8888','味千拉面位于海江新天地3区 1F，主营拉面、日式。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s039','小灶湘','1','3区','餐饮','湘菜,剁椒','#C2185B','10:00 - 22:00','021-5656 8888','小灶湘位于海江新天地3区 1F，主营湘菜、剁椒。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s040','朱光玉火锅','1','3区','餐饮','火锅,重庆','#C2185B','10:00 - 22:00','021-5656 8888','朱光玉火锅位于海江新天地3区 1F，主营火锅、重庆。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s041','扬春茶社','1','3区','餐饮','茶馆,茶饮','#6E4B3A','10:00 - 22:00','021-5656 8888','扬春茶社位于海江新天地3区 1F，主营茶馆、茶饮。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s042','肖记公安牛杂','1','3区','餐饮','牛杂,湖北','#E85D04','10:00 - 22:00','021-5656 8888','肖记公安牛杂位于海江新天地3区 1F，主营牛杂、湖北。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s043','大城小野','2','3区','餐饮','料理,创意菜','#C2185B','10:00 - 22:00','021-5656 8888','大城小野位于海江新天地3区 2F，主营料理、创意菜。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s044','伴月楼','2','3区','餐饮','杭帮菜,本帮','#C0392B','10:00 - 22:00','021-5656 8888','伴月楼位于海江新天地3区 2F，主营杭帮菜、本帮。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s045','星巴克','2','3区','餐饮','咖啡,第三空间','#00704A','10:00 - 22:00','021-5656 8888','星巴克位于海江新天地3区 2F，主营咖啡、第三空间。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s046','汇通棋牌','3','3区','娱乐','棋牌,休闲','#9B7BD4','10:00 - 24:00','021-5656 8888','汇通棋牌位于海江新天地3区 3F，主营棋牌、休闲。潮流娱乐聚场，释放精彩的昼夜生活。',1,0,30,'2026-12-31','可预约,适合聚会'),
                ('s047','苏宁易购','1','4区','零售','电器,数码','#E60012','10:00 - 22:00','021-5656 8888','苏宁易购位于海江新天地4区 1F，主营电器、数码。精选好物与品牌，打造舒适惬意的购物体验。',1,200,30,'2026-12-31','线上线下同价,支持退换,会员积分'),
                ('s048','华为/迪信通','1','4区','零售','手机,数码','#4A90D9','10:00 - 22:00','021-5656 8888','华为/迪信通位于海江新天地4区 1F，主营手机、数码。精选好物与品牌，打造舒适惬意的购物体验。',1,200,30,'2026-12-31','线上线下同价,支持退换,会员积分'),
                ('s049','足浴养生','3','4区','生活服务','足浴,养生','#3E8E41','10:00 - 21:00','021-5656 8888','足浴养生位于海江新天地4区 3F，主营足浴、养生。贴心周到的生活服务，便捷周边日常所需。',1,0,5,'2026-12-31','专业服务,可预约'),
                ('s050','民谣星烧烤酒馆','1','6区','餐饮','烧烤,音乐','#E85D04','10:00 - 22:00','021-5656 8888','民谣星烧烤酒馆位于海江新天地6区 1F，主营烧烤、音乐。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s051','戴海川·美蛙','1','6区','餐饮','美蛙,川味','#C2185B','10:00 - 22:00','021-5656 8888','戴海川·美蛙位于海江新天地6区 1F，主营美蛙、川味。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s052','暴走牛牛·碳火烧肉','1','6区','餐饮','烧肉,日式','#C0392B','10:00 - 22:00','021-5656 8888','暴走牛牛·碳火烧肉位于海江新天地6区 1F，主营烧肉、日式。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s053','鱼石尚云南蒸石锅鱼','1','6区','餐饮','蒸汽石锅鱼,云南菜','#3E8E41','10:00 - 22:00','021-5656 8888','鱼石尚云南蒸石锅鱼位于海江新天地6区 1F，主营蒸汽石锅鱼、云南菜。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s054','福海面馆','1','6区','餐饮','面,快餐','#E60012','10:00 - 22:00','021-5656 8888','福海面馆位于海江新天地6区 1F，主营面、快餐。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s055','Jenga精酿啤酒馆','1','6区','餐饮','精酿,啤酒','#C9975A','10:00 - 22:00','021-5656 8888','Jenga精酿啤酒馆位于海江新天地6区 1F，主营精酿、啤酒。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s056','潮汕·草根活鱼火锅','1','6区','餐饮','火锅,潮汕','#C2185B','10:00 - 22:00','021-5656 8888','潮汕·草根活鱼火锅位于海江新天地6区 1F，主营火锅、潮汕。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s057','阿国烤局','1','6区','餐饮','烤串,夜宵','#E85D04','10:00 - 22:00','021-5656 8888','阿国烤局位于海江新天地6区 1F，主营烤串、夜宵。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s058','深夜食堂','1','6区','餐饮','夜宵,小炒','#E85D04','10:00 - 22:00','021-5656 8888','深夜食堂位于海江新天地6区 1F，主营夜宵、小炒。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s059','汽石锅鱼','1','6区','餐饮','石锅鱼,川味','#3E8E41','10:00 - 22:00','021-5656 8888','汽石锅鱼位于海江新天地6区 1F，主营石锅鱼、川味。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s060','牛肉档','1','6区','餐饮','牛肉,火锅','#C0392B','10:00 - 22:00','021-5656 8888','牛肉档位于海江新天地6区 1F，主营牛肉、火锅。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s061','合一瑜伽健身','2','6区','娱乐','瑜伽,健身','#9B7BD4','10:00 - 22:00','021-5656 8888','合一瑜伽健身位于海江新天地6区 2F，主营瑜伽、健身。潮流娱乐聚场，释放精彩的昼夜生活。',1,0,30,'2026-12-31','可预约,适合聚会'),
                ('s062','合一瑜伽普拉提','2','6区','娱乐','普拉提,健身','#9B7BD4','10:00 - 22:00','021-5656 8888','合一瑜伽普拉提位于海江新天地6区 2F，主营普拉提、健身。潮流娱乐聚场，释放精彩的昼夜生活。',1,0,30,'2026-12-31','可预约,适合聚会'),
                ('s063','L服饰','2','6区','零售','服饰,服装','#4A90D9','10:00 - 22:00','021-5656 8888','L服饰位于海江新天地6区 2F，主营服饰、服装。精选好物与品牌，打造舒适惬意的购物体验。',1,200,30,'2026-12-31','线上线下同价,支持退换,会员积分'),
                ('s064','网鱼电竞酒店','2','6区','娱乐','电竞,酒店','#9B7BD4','10:00 - 22:00','021-5656 8888','网鱼电竞酒店位于海江新天地6区 2F，主营电竞、酒店。潮流娱乐聚场，释放精彩的昼夜生活。',1,0,30,'2026-12-31','可预约,适合聚会'),
                ('s065','屿汀美容spa','2','6区','生活服务','美容,SPA','#3E8E41','10:00 - 21:00','021-5656 8888','屿汀美容spa位于海江新天地6区 2F，主营美容、SPA。贴心周到的生活服务，便捷周边日常所需。',1,0,5,'2026-12-31','专业服务,可预约'),
                ('s066','弘文书馆','2','6区','生活服务','书店,文创','#3E8E41','10:00 - 21:00','021-5656 8888','弘文书馆位于海江新天地6区 2F，主营书店、文创。贴心周到的生活服务，便捷周边日常所需。',1,0,5,'2026-12-31','专业服务,可预约'),
                ('s067','康友四季','2','6区','生活服务','洗浴,汗蒸','#3E8E41','10:00 - 21:00','021-5656 8888','康友四季位于海江新天地6区 2F，主营洗浴、汗蒸。贴心周到的生活服务，便捷周边日常所需。',1,0,5,'2026-12-31','专业服务,可预约'),
                ('s068','新鸳鸯','3','6区','餐饮','火锅,川味','#C2185B','10:00 - 22:00','021-5656 8888','新鸳鸯位于海江新天地6区 3F，主营火锅、川味。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s069','功夫汪宠物乐园','1','7区','亲子','宠物,亲子','#E8809E','10:00 - 21:00','021-5656 8888','功夫汪宠物乐园位于海江新天地7区 1F，主营宠物、亲子。亲子同乐的成长空间，陪伴孩子快乐探索世界。',1,100,20,'2026-12-31','亲子友好,可免费体验'),
                ('s070','东煜画室','1','7区','亲子','绘画,美术','#E8809E','10:00 - 21:00','021-5656 8888','东煜画室位于海江新天地7区 1F，主营绘画、美术。亲子同乐的成长空间，陪伴孩子快乐探索世界。',1,100,20,'2026-12-31','亲子友好,可免费体验'),
                ('s071','卡卡海洋','1','7区','亲子','亲子乐园,探索','#E8809E','10:00 - 21:00','021-5656 8888','卡卡海洋位于海江新天地7区 1F，主营亲子乐园、探索。亲子同乐的成长空间，陪伴孩子快乐探索世界。',1,100,20,'2026-12-31','亲子友好,可免费体验'),
                ('s072','招商银行','1','7区','生活服务','银行,金融','#4A90D9','09:00 - 17:00','021-5656 8888','招商银行位于海江新天地7区 1F，主营银行、金融。贴心周到的生活服务，便捷周边日常所需。',1,0,5,'2026-12-31','专业服务,可预约'),
                ('s073','壹品培优','1','7区','亲子','培优,托管','#E8809E','10:00 - 21:00','021-5656 8888','壹品培优位于海江新天地7区 1F，主营培优、托管。亲子同乐的成长空间，陪伴孩子快乐探索世界。',1,100,20,'2026-12-31','亲子友好,可免费体验'),
                ('s074','舞林园','1','7区','亲子','舞蹈,培训','#E8809E','10:00 - 21:00','021-5656 8888','舞林园位于海江新天地7区 1F，主营舞蹈、培训。亲子同乐的成长空间，陪伴孩子快乐探索世界。',1,100,20,'2026-12-31','亲子友好,可免费体验'),
                ('s075','OX牛排','1','7区','餐饮','牛排,西餐','#C0392B','10:00 - 22:00','021-5656 8888','OX牛排位于海江新天地7区 1F，主营牛排、西餐。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s076','MANNER','1','7区','餐饮','咖啡,精品咖啡','#B8915C','10:00 - 22:00','021-5656 8888','MANNER位于海江新天地7区 1F，主营咖啡、精品咖啡。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s077','赛百味','1','7区','餐饮','三明治,轻食','#2E8B57','10:00 - 22:00','021-5656 8888','赛百味位于海江新天地7区 1F，主营三明治、轻食。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s078','海鲜餐厅','1','7区','餐饮','海鲜,粤菜','#3E8E41','10:00 - 22:00','021-5656 8888','海鲜餐厅位于海江新天地7区 1F，主营海鲜、粤菜。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s079','大墨蒲公英','2','7区','亲子','儿童绘画,美术','#E8809E','10:00 - 21:00','021-5656 8888','大墨蒲公英位于海江新天地7区 2F，主营儿童绘画、美术。亲子同乐的成长空间，陪伴孩子快乐探索世界。',1,100,20,'2026-12-31','亲子友好,可免费体验'),
                ('s080','菁英之伽','2','7区','娱乐','瑜伽,健身','#9B7BD4','10:00 - 22:00','021-5656 8888','菁英之伽位于海江新天地7区 2F，主营瑜伽、健身。潮流娱乐聚场，释放精彩的昼夜生活。',1,0,30,'2026-12-31','可预约,适合聚会'),
                ('s081','招商银行','2','7区','生活服务','银行,金融','#4A90D9','09:00 - 17:00','021-5656 8888','招商银行位于海江新天地7区 2F，主营银行、金融。贴心周到的生活服务，便捷周边日常所需。',1,0,5,'2026-12-31','专业服务,可预约'),
                ('s082','健身房','2','7区','娱乐','健身,器械','#9B7BD4','10:00 - 22:00','021-5656 8888','健身房位于海江新天地7区 2F，主营健身、器械。潮流娱乐聚场，释放精彩的昼夜生活。',1,0,30,'2026-12-31','可预约,适合聚会'),
                ('s083','东方好艺考','2','7区','亲子','艺考,培训','#E8809E','10:00 - 21:00','021-5656 8888','东方好艺考位于海江新天地7区 2F，主营艺考、培训。亲子同乐的成长空间，陪伴孩子快乐探索世界。',1,100,20,'2026-12-31','亲子友好,可免费体验'),
                ('s084','POP兔','2','7区','亲子','早教,托育','#E8809E','10:00 - 21:00','021-5656 8888','POP兔位于海江新天地7区 2F，主营早教、托育。亲子同乐的成长空间，陪伴孩子快乐探索世界。',1,100,20,'2026-12-31','亲子友好,可免费体验'),
                ('s085','音乐教室','2','7区','亲子','音乐,培训','#E8809E','10:00 - 21:00','021-5656 8888','音乐教室位于海江新天地7区 2F，主营音乐、培训。亲子同乐的成长空间，陪伴孩子快乐探索世界。',1,100,20,'2026-12-31','亲子友好,可免费体验'),
                ('s086','南京银行','2','7区','生活服务','银行,金融','#4A90D9','09:00 - 17:00','021-5656 8888','南京银行位于海江新天地7区 2F，主营银行、金融。贴心周到的生活服务，便捷周边日常所需。',1,0,5,'2026-12-31','专业服务,可预约'),
                ('s087','诚之书院','2','7区','亲子','书院,国学','#E8809E','10:00 - 21:00','021-5656 8888','诚之书院位于海江新天地7区 2F，主营书院、国学。亲子同乐的成长空间，陪伴孩子快乐探索世界。',1,100,20,'2026-12-31','亲子友好,可免费体验'),
                ('s088','嘻戏英语','2','7区','亲子','英语,培训','#E8809E','10:00 - 21:00','021-5656 8888','嘻戏英语位于海江新天地7区 2F，主营英语、培训。亲子同乐的成长空间，陪伴孩子快乐探索世界。',1,100,20,'2026-12-31','亲子友好,可免费体验'),
                ('s089','沪小胖','3','7区','餐饮','小龙虾,夜宵','#E60012','10:00 - 22:00','021-5656 8888','沪小胖位于海江新天地7区 3F，主营小龙虾、夜宵。汇聚人气美食，满足全时段味蕾需求，是街区的活力引擎。',1,50,10,'2026-12-31','可堂食,外卖配送,支持扫码点单'),
                ('s090','SFC上影影城','3','7区','娱乐','影院,电影','#E85D04','10:00 - 22:00','021-5656 8888','SFC上影影城位于海江新天地7区 3F，主营影院、电影。潮流娱乐聚场，释放精彩的昼夜生活。',1,0,30,'2026-12-31','可预约,适合聚会'),
        ]
            conn.executemany('INSERT INTO shops VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', shops_data)

    # --- offers ---
    conn.execute('''CREATE TABLE IF NOT EXISTS offers (
        id INTEGER PRIMARY KEY AUTOINCREMENT, shop_name TEXT NOT NULL,
        label TEXT NOT NULL, expire TEXT, amount INTEGER DEFAULT 0,
        category TEXT DEFAULT 'food', color TEXT DEFAULT '#FF7B2C',
        status TEXT DEFAULT 'active', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    if conn.execute('SELECT COUNT(*) FROM offers').fetchone()[0] == 0:
        offers_data = [
            # 餐饮券
            ('海江食集','满50减5 代金券','2026-12-31',5,'food','#C4923A'),
            ('朱光玉火锅','到店赠秘制小菜2份（价值18元）','2026-12-31',18,'food','#9B4A3E'),
            ('成都你六姐','满60减10 代金券','2026-12-31',10,'food','#C4923A'),
            ('小杨生煎','买单立减8元','2026-12-31',8,'food','#C9956C'),
            ('霸王茶姬','指定饮品买一赠一','2026-12-31',18,'food','#D4A59A'),
            ('瑞幸咖啡','9.9元尝鲜券（立减10元）','2026-12-31',10,'food','#0051A8'),
            ('喜姐炸串','满30减6 代金券','2026-12-31',6,'food','#C4923A'),
            ('沪小胖·上海小龙虾','赠凉拌毛豆+花生1份','2026-12-31',15,'food','#9B4A3E'),
            ('麦当劳','满40减8 代金券','2026-12-31',8,'food','#D4A59A'),
            # 零售券
            ('华为授权店','手机满1000减50 代金券','2026-12-31',50,'retail','#4A90D9'),
            ('晨光文具','满38减5 代金券','2026-12-31',5,'retail','#C4923A'),
            ('苏宁易购','家电满2000减100','2026-12-31',100,'retail','#4A90D9'),
            ('诺家智慧大药房','满50减8 代金券','2026-12-31',8,'retail','#3E8E41'),
            # 娱乐券
            ('SFC上影影城','免费电影票1张（价值45元）','2026-12-31',45,'fun','#9B7BD4'),
            ('尊柜KTV','工作日欢唱2小时免房费','2026-12-31',88,'fun','#9B7BD4'),
            ('哇咔健身','新人免费体验课1节','2026-12-31',39,'fun','#3E8E41'),
            ('雀王棋牌','满100减20 代金券','2026-12-31',20,'fun','#9B7BD4'),
            # 亲子券
            ('泡泡米儿童','体验课免费1节','2026-12-31',49,'kids','#E8809E'),
            ('壹品培优','试听课立减30元','2026-12-31',30,'kids','#E8809E'),
            ('卡卡海洋','儿童票立减15元','2026-12-31',15,'kids','#4A90D9'),
            # 生活服务券
            ('招商银行','信用卡满100减15（观影/餐饮）','2026-12-31',15,'service','#4A90D9'),
            ('康友四季','足浴满150减30','2026-12-31',30,'service','#3E8E41'),
            ('屿汀美容spa','到店赠面部护理1次','2026-12-31',58,'service','#E8809E'),
            # 停车券
            ('海江新天地停车场','免费停车2小时','2026-12-31',10,'parking','#6B6E64'),
        ]
        conn.executemany('INSERT INTO offers (shop_name,label,expire,amount,category,color) VALUES (?,?,?,?,?,?)', offers_data)

    # --- redeem_goods ---
    conn.execute('''CREATE TABLE IF NOT EXISTS redeem_goods (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, points INTEGER NOT NULL,
        category TEXT DEFAULT '餐饮', gradient TEXT,
        status TEXT DEFAULT 'active', stock INTEGER DEFAULT -1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    if conn.execute('SELECT COUNT(*) FROM redeem_goods').fetchone()[0] == 0:
        goods_data = [
            ('g1','SFC上影影城 电影票',2000,'娱乐','linear-gradient(135deg, #9B7BD4, #C9B6E8)'),
            ('g2','朱光玉火锅 50元代金券',3000,'餐饮','linear-gradient(135deg, #9B4A3E, #C97A6E)'),
            ('g3','华为授权店 30元券',2500,'购物','linear-gradient(135deg, #4A90D9, #7DB8F0)'),
            ('g4','海江新天地 停车券10元',500,'停车','linear-gradient(135deg, #6B6E64, #9AA39A)'),
            ('g5','康友四季 足浴券',2500,'生活服务','linear-gradient(135deg, #3E8E41, #6FBF73)'),
            ('g6','泡泡米儿童 体验课',2000,'亲子','linear-gradient(135deg, #E8809E, #F0AAC0)'),
            ('g7','瑞幸咖啡 中杯券',1000,'餐饮','linear-gradient(135deg, #0051A8, #3E7FD0)'),
            ('g8','哇咔健身 体验周卡',4000,'娱乐','linear-gradient(135deg, #3E8E41, #6FBF73)'),
        ]
        conn.executemany('INSERT INTO redeem_goods (id,name,points,category,gradient) VALUES (?,?,?,?,?)', goods_data)

    # --- parking_records ---
    conn.execute('''CREATE TABLE IF NOT EXISTS parking_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plate TEXT NOT NULL, entry_time TEXT, exit_time TEXT,
        duration_minutes INTEGER DEFAULT 0, fee REAL DEFAULT 0,
        status TEXT DEFAULT 'parked',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # --- restaurant_queues (餐厅排队取号) ---
    conn.execute('''CREATE TABLE IF NOT EXISTS restaurant_queues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shop_id TEXT NOT NULL,
        shop_name TEXT NOT NULL,
        queue_number INTEGER NOT NULL,
        customer_phone TEXT DEFAULT '',
        customer_name TEXT DEFAULT '',
        party_size INTEGER DEFAULT 2,
        status TEXT DEFAULT 'waiting',
        estimated_wait INTEGER DEFAULT 15,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # --- restaurant_reservations (餐厅预约订位) ---
    conn.execute('''CREATE TABLE IF NOT EXISTS restaurant_reservations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shop_id TEXT NOT NULL,
        shop_name TEXT NOT NULL,
        customer_phone TEXT NOT NULL,
        customer_name TEXT NOT NULL,
        party_size INTEGER DEFAULT 2,
        reserve_date TEXT NOT NULL,
        reserve_time TEXT NOT NULL,
        status TEXT DEFAULT 'confirmed',
        special_requests TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # --- merchant_tokens (商户看板认证) ---
    conn.execute('''CREATE TABLE IF NOT EXISTS merchant_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shop_id TEXT NOT NULL UNIQUE,
        token TEXT NOT NULL UNIQUE,
        webhook_url TEXT DEFAULT '',
        phone_notify INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    # 为已有餐饮商户自动生成 token
    existing = {r['shop_id'] for r in conn.execute('SELECT shop_id FROM merchant_tokens').fetchall()}
    food_shops = conn.execute("SELECT id FROM shops WHERE category='餐饮'").fetchall()
    for fs in food_shops:
        if fs['id'] not in existing:
            t = uuid.uuid4().hex[:16]
            conn.execute("INSERT INTO merchant_tokens (shop_id,token) VALUES (?,?)", (fs['id'], t))
    conn.commit()

    # --- venue_bookings (场地时段预定) ---
    conn.execute('''CREATE TABLE IF NOT EXISTS venue_bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venue_name TEXT NOT NULL,
        venue_type TEXT NOT NULL,
        customer_phone TEXT NOT NULL,
        customer_name TEXT NOT NULL,
        booking_date TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        purpose TEXT DEFAULT '',
        fee REAL DEFAULT 0,
        status TEXT DEFAULT 'confirmed',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # --- event_schedules (活动排期报备) ---
    conn.execute('''CREATE TABLE IF NOT EXISTS event_schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        organizer_phone TEXT NOT NULL,
        organizer_name TEXT NOT NULL,
        event_name TEXT NOT NULL,
        event_type TEXT DEFAULT '',
        venue TEXT DEFAULT '',
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        expected_attendance INTEGER DEFAULT 0,
        description TEXT DEFAULT '',
        status TEXT DEFAULT 'pending',
        work_order_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # --- organizer_settlements (主理人结算) ---
    conn.execute('''CREATE TABLE IF NOT EXISTS organizer_settlements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        organizer_phone TEXT NOT NULL,
        organizer_name TEXT NOT NULL,
        event_name TEXT DEFAULT '',
        revenue REAL DEFAULT 0,
        platform_fee REAL DEFAULT 0,
        net_payout REAL DEFAULT 0,
        status TEXT DEFAULT 'pending',
        settled_at TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # --- coupon_claims (优惠券领取记录，防重复) ---
    conn.execute('''CREATE TABLE IF NOT EXISTS coupon_claims (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_phone TEXT NOT NULL,
        offer_id INTEGER NOT NULL,
        shop_name TEXT DEFAULT '',
        label TEXT DEFAULT '',
        amount INTEGER DEFAULT 0,
        claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_phone, offer_id)
    )''')

    # --- group_buys (拼团活动) ---
    conn.execute('''CREATE TABLE IF NOT EXISTS group_buys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shop_id TEXT DEFAULT '',
        shop_name TEXT NOT NULL,
        title TEXT NOT NULL,
        coupon_label TEXT NOT NULL,
        coupon_amount INTEGER DEFAULT 0,
        need_count INTEGER DEFAULT 5,
        expire_at TEXT DEFAULT '',
        status TEXT DEFAULT 'open',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    # --- group_buy_members (拼团成员) ---
    conn.execute('''CREATE TABLE IF NOT EXISTS group_buy_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER NOT NULL,
        user_phone TEXT NOT NULL,
        user_name TEXT DEFAULT '',
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(group_id, user_phone)
    )''')
    # 预置一个火锅店 5 人拼团示例（如未存在）
    if conn.execute('SELECT COUNT(*) FROM group_buys').fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO group_buys (shop_id,shop_name,title,coupon_label,coupon_amount,need_count,expire_at,status) "
            "VALUES ('s040','朱光玉火锅','朱光玉火锅 5 人拼团·满减券','满200减50 代金券',50,5,'2026-12-31','open')"
        )

    # --- human_chat_messages (人工客服聊天记录) ---
    conn.execute('''CREATE TABLE IF NOT EXISTS human_chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        user_phone TEXT DEFAULT '',
        user_name TEXT DEFAULT '',
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        work_order_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # --- feedbacks (满意度评价) ---
    conn.execute('''CREATE TABLE IF NOT EXISTS feedbacks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_phone TEXT DEFAULT '',
        feedback_type TEXT NOT NULL,
        biz_type TEXT DEFAULT '',
        order_id TEXT DEFAULT '',
        rating INTEGER NOT NULL,
        feedback_text TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # --- kb_pending (知识库待优化问题) ---
    conn.execute('''CREATE TABLE IF NOT EXISTS kb_pending (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER DEFAULT 1,
        question TEXT NOT NULL,
        category TEXT DEFAULT '',
        source TEXT DEFAULT 'chat',
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # --- points_log (积分/成长值流水) ---
    conn.execute('''CREATE TABLE IF NOT EXISTS points_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_phone TEXT NOT NULL,
        action TEXT NOT NULL,
        points INTEGER NOT NULL,
        remark TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # --- sign_in_records (签到记录，含连续天数) ---
    conn.execute('''CREATE TABLE IF NOT EXISTS sign_in_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_phone TEXT NOT NULL,
        sign_date TEXT NOT NULL,
        consecutive_days INTEGER DEFAULT 1,
        points_awarded INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_phone, sign_date)
    )''')

    # --- badges (徽章定义) ---
    conn.execute('''CREATE TABLE IF NOT EXISTS badges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        threshold INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # --- user_badges (用户已获徽章) ---
    conn.execute('''CREATE TABLE IF NOT EXISTS user_badges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_phone TEXT NOT NULL,
        badge_code TEXT NOT NULL,
        earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_phone, badge_code)
    )''')

    # 徽章预置（INSERT OR IGNORE 幂等，新增徽章可随时补充）
    badges_data = [
        ('first_sign', '初来乍到', '完成首次签到', 1),
        ('sign_7', '坚持一周', '连续签到 7 天', 7),
        ('sign_30', '月度常客', '累计签到 30 天', 30),
        ('points_1000', '成长新星', '累计成长值达 1000', 1000),
        ('points_5000', '成长达人', '累计成长值达 5000', 5000),
        ('level_silver', '银卡会员', '升级为银卡会员', 2000),
        ('level_gold', '金卡会员', '升级为金卡会员', 5000),
        ('level_diamond', '钻石会员', '升级为钻石卡会员', 20000),
        ('first_post', '首次发声', '发布第一篇邻里圈内容', 1),
        ('post_10', '内容达人', '发布 10 篇内容', 10),
        ('like_100', '人气之星', '获得 100 个赞', 100),
        ('club_join', '邻里搭子', '加入兴趣社活动', 1),
    ]
    conn.executemany('INSERT OR IGNORE INTO badges (code,name,description,threshold) VALUES (?,?,?,?)', badges_data)

    # --- community_posts (邻里圈帖子) ---
    conn.execute('''CREATE TABLE IF NOT EXISTS community_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_phone TEXT NOT NULL,
        user_name TEXT DEFAULT '',
        content TEXT NOT NULL,
        images TEXT DEFAULT '[]',
        topic TEXT DEFAULT '',
        category TEXT DEFAULT '',
        like_count INTEGER DEFAULT 0,
        comment_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # --- community_topics (话题) ---
    conn.execute('''CREATE TABLE IF NOT EXISTS community_topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL UNIQUE,
        description TEXT DEFAULT '',
        is_official INTEGER DEFAULT 1,
        post_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # --- community_comments (评论) ---
    conn.execute('''CREATE TABLE IF NOT EXISTS community_comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        user_phone TEXT DEFAULT '',
        user_name TEXT DEFAULT '',
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # --- community_likes (点赞) ---
    conn.execute('''CREATE TABLE IF NOT EXISTS community_likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        user_phone TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(post_id, user_phone)
    )''')

    if conn.execute('SELECT COUNT(*) FROM community_topics').fetchone()[0] == 0:
        topics = [
            ('周末去哪遛娃', '分享亲子遛娃好去处'),
            ('今晚吃什么', '推荐今晚的美食选择'),
            ('探店打卡', '晒出你的探店体验'),
            ('商场优惠', '发现商场里的划算好物'),
            ('邻里互助', '邻里之间的互帮互助'),
        ]
        conn.executemany('INSERT INTO community_topics (title, description) VALUES (?,?)', topics)

    # --- 兴趣社模块（活动驱动的轻组织：常驻兴趣社 + 临时活动群） ---
    # 常驻兴趣社：按标签归类，用户选标签后自动加入
    conn.execute('''CREATE TABLE IF NOT EXISTS interest_clubs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        tag TEXT NOT NULL,
        cover_emoji TEXT DEFAULT '🏷️',
        gradient TEXT DEFAULT 'linear-gradient(135deg,#FF7B2C,#E85D04)',
        intro TEXT DEFAULT '',
        member_count INTEGER DEFAULT 0,
        club_order INTEGER DEFAULT 0,
        status TEXT DEFAULT 'open'
    )''')
    # 用户-兴趣社 关系
    conn.execute('''CREATE TABLE IF NOT EXISTS user_club_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        club_id INTEGER NOT NULL,
        user_phone TEXT NOT NULL,
        user_name TEXT DEFAULT '',
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(club_id, user_phone)
    )''')
    # 临时活动群（活动驱动，活动结束自动散）
    conn.execute('''CREATE TABLE IF NOT EXISTS club_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        club_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        tag TEXT NOT NULL,
        detail TEXT DEFAULT '',
        place TEXT DEFAULT '',
        meet_time TEXT DEFAULT '',
        end_time TEXT DEFAULT '',
        need_count INTEGER DEFAULT 0,
        creator_phone TEXT DEFAULT '',
        creator_name TEXT DEFAULT '',
        status TEXT DEFAULT 'open',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    # 临时活动群成员（UNIQUE 防重复）
    conn.execute('''CREATE TABLE IF NOT EXISTS club_event_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL,
        user_phone TEXT NOT NULL,
        user_name TEXT DEFAULT '',
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(event_id, user_phone)
    )''')
    # 临时活动群留言接龙（非实时）
    conn.execute('''CREATE TABLE IF NOT EXISTS club_event_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL,
        user_phone TEXT NOT NULL,
        user_name TEXT DEFAULT '',
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # 预置兴趣社（COUNT==0 守卫 + name UNIQUE 双重幂等，防止重启/多进程重复插入）
    if conn.execute('SELECT COUNT(*) FROM interest_clubs').fetchone()[0] == 0:
        clubs_data = [
            ('周三夜跑团', '夜跑', '🌙', 'linear-gradient(135deg,#5B6CFF,#3A47C9)', '每周三晚 7 点集合，沿滨江步道约 5 公里，新手友好。', 1),
            ('宝妈遛娃群', '遛娃', '🍼', 'linear-gradient(135deg,#FF8FB1,#E85D8A)', '周末带娃去哪玩？母婴室、亲子餐厅、室内乐园一手情报。', 2),
            ('球友约战', '球类', '🏀', 'linear-gradient(135deg,#27AE60,#1E8449)', '篮球/羽毛球/足球约战招募，凑齐人数就开打。', 3),
            ('周末电影搭子', '观影', '🎬', 'linear-gradient(135deg,#9B59B6,#7D3C98)', '凑人看新片，SFC 影城拼团购票更划算。', 4),
            ('宠物社交局', '宠物', '🐾', 'linear-gradient(135deg,#E17055,#CA6F1E)', '带毛孩子认识新朋友，宠物友好商户线下聚会。', 5),
        ]
        for name, tag, emoji, grad, intro, order in clubs_data:
            conn.execute(
                "INSERT OR IGNORE INTO interest_clubs (name,tag,cover_emoji,gradient,intro,club_order,status) "
                "VALUES (?,?,?,?,?,?,'open')",
                (name, tag, emoji, grad, intro, order)
            )
        # 建立 name 唯一索引（无重复数据后才会成功），保证后续 INSERT OR IGNORE 真正按 name 幂等
        try:
            conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS uq_interest_clubs_name ON interest_clubs(name)')
        except Exception:
            pass

    # 预置临时活动群（status='open'，end_time 设在未来，活动结束即散）
    upcoming = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
    upcoming2 = (datetime.now() + timedelta(days=4)).strftime('%Y-%m-%d')
    upcoming3 = (datetime.now() + timedelta(days=6)).strftime('%Y-%m-%d')
    if conn.execute('SELECT COUNT(*) FROM club_events').fetchone()[0] == 0:
        # 取常驻社 id
        cid = {r['tag']: r['id'] for r in conn.execute('SELECT id,tag FROM interest_clubs').fetchall()}
        club_events_data = [
            (cid.get('夜跑'), '周三夜跑·第 12 期', '夜跑', '沿滨江步道 5 公里慢跑，配速 6′30″，新手可走跑结合。', '海江新天地北门集合', f'{upcoming} 19:00', f'{upcoming} 21:00', 8),
            (cid.get('遛娃'), '周末亲子·室内乐园日', '遛娃', '带娃打卡新开室内乐园，现场有亲子手工活动。', '海江新天地 1F 中庭', f'{upcoming2} 10:00', f'{upcoming2} 12:30', 15),
            (cid.get('球类'), '周末篮球 3V3 约战', '球类', '半场 3V3，三局两胜，缺 2 人即可开打。', '海江新天地 B1 球场', f'{upcoming3} 15:00', f'{upcoming3} 17:30', 6),
            (cid.get('观影'), '周末新片·拼团观影', '观影', '凑 4 人拼团买 SFC 影城票，每人立减 10 元。', 'SFC 上影国际影城', f'{upcoming2} 19:30', f'{upcoming2} 22:00', 4),
            (cid.get('宠物'), '宠物友好·户外茶歇局', '宠物', '带毛孩子露天茶歇，现场有宠物洗护体验券。', '海江新天地西广场', f'{upcoming} 16:00', f'{upcoming} 18:00', 10),
        ]
        for club_id, title, tag, detail, place, meet, end, need in club_events_data:
            if not club_id:
                continue
            conn.execute(
                "INSERT INTO club_events (club_id,title,tag,detail,place,meet_time,end_time,need_count,status) "
                "VALUES (?,?,?,?,?,?,?,?,'open')",
                (club_id, title, tag, detail, place, meet, end, need)
            )

    conn.commit()
    _init_done = True
    _release_init_flock()


# ========== 激励层：成长值/积分/徽章 ==========
_LEVELS = [('普卡', 0), ('银卡', 2000), ('金卡', 5000), ('钻石卡', 20000)]

def _level_rank(level):
    """等级 -> 序号（用于比较高低）"""
    for i, (name, _) in enumerate(_LEVELS):
        if name == level:
            return i
    return 0

def _auto_level(points):
    """根据成长值返回应达到的会员等级"""
    level = '普卡'
    for name, threshold in _LEVELS:
        if points >= threshold:
            level = name
    return level

def add_points(phone, points, action, remark=''):
    """统一加分入口：加分 + 记流水 + 自动升级等级 + 检查徽章。
    后续内容层/互动层行为（发帖/评论/被赞）直接调用此函数即可，无需重复造轮子。"""
    if not phone or points == 0:
        return {'ok': False, 'error': '参数错误'}
    conn = get_db()
    _ensure_tables(conn)
    user = conn.execute('SELECT id, points, membership_level FROM users WHERE phone=?', (phone,)).fetchone()
    if not user:
        conn.close()
        return {'ok': False, 'error': '用户不存在，请先注册会员'}
    old_points = user['points'] or 0
    new_points = old_points + points
    conn.execute('UPDATE users SET points=? WHERE phone=?', (new_points, phone))
    conn.execute('INSERT INTO points_log (user_phone, action, points, remark) VALUES (?,?,?,?)',
                 (phone, action, points, remark))
    # 自动升级（只升不降）
    old_level = user['membership_level'] or '普卡'
    new_level = _auto_level(new_points)
    level_up = None
    if _level_rank(new_level) > _level_rank(old_level):
        conn.execute('UPDATE users SET membership_level=? WHERE phone=?', (new_level, phone))
        level_up = new_level
    conn.commit()
    conn.close()
    new_badges = check_badges(phone)
    return {'ok': True, 'points': new_points, 'added': points, 'level': new_level,
            'level_up': level_up, 'new_badges': new_badges}

def check_badges(phone):
    """检查并自动颁发达成条件的徽章，返回本次新获得的徽章 code 列表"""
    if not phone:
        return []
    conn = get_db()
    _ensure_tables(conn)
    user = conn.execute('SELECT points, membership_level FROM users WHERE phone=?', (phone,)).fetchone()
    if not user:
        conn.close()
        return []
    sign_count = conn.execute('SELECT COUNT(*) FROM sign_in_records WHERE user_phone=?', (phone,)).fetchone()[0]
    max_consecutive = conn.execute('SELECT MAX(consecutive_days) FROM sign_in_records WHERE user_phone=?', (phone,)).fetchone()[0] or 0
    post_count = conn.execute('SELECT COUNT(*) FROM community_posts WHERE user_phone=?', (phone,)).fetchone()[0]
    total_likes = conn.execute('SELECT COALESCE(SUM(like_count),0) FROM community_posts WHERE user_phone=?', (phone,)).fetchone()[0] or 0
    total_points = user['points'] or 0
    level = user['membership_level'] or '普卡'
    conditions = {
        'first_sign': sign_count >= 1,
        'sign_7': max_consecutive >= 7,
        'sign_30': sign_count >= 30,
        'points_1000': total_points >= 1000,
        'points_5000': total_points >= 5000,
        'level_silver': level in ('银卡', '金卡', '钻石卡'),
        'level_gold': level in ('金卡', '钻石卡'),
        'level_diamond': level == '钻石卡',
        'first_post': post_count >= 1,
        'post_10': post_count >= 10,
        'like_100': total_likes >= 100,
        'group_1': conn.execute('SELECT COUNT(*) FROM group_buy_members WHERE user_phone=?', (phone,)).fetchone()[0] >= 1,
    }
    earned = []
    for code, ok in conditions.items():
        if not ok:
            continue
        exists = conn.execute('SELECT id FROM user_badges WHERE user_phone=? AND badge_code=?', (phone, code)).fetchone()
        if not exists:
            conn.execute('INSERT INTO user_badges (user_phone, badge_code) VALUES (?,?)', (phone, code))
            earned.append(code)
    conn.commit()
    conn.close()
    return earned


# ========== 餐厅排队/预订辅助函数 ==========
def _is_peak_hours():
    """判断当前是否为高峰时段，返回 (is_peak, multiplier)"""
    now = datetime.now()
    wd = now.weekday()  # 0=Mon, 6=Sun
    h = now.hour + now.minute / 60.0
    # 午餐高峰: 11:30-13:30 (工作日) / 11:00-14:00 (周末)
    lunch_peak = (11.5 <= h <= 13.5) if wd < 5 else (11.0 <= h <= 14.0)
    # 晚餐高峰: 18:00-20:30 (工作日) / 17:30-21:00 (周末)
    dinner_peak = (18.0 <= h <= 20.5) if wd < 5 else (17.5 <= h <= 21.0)
    # 夜巷高峰: 21:00-23:00 (周五-周日)
    night_peak = (21.0 <= h <= 23.0) and wd >= 4
    if lunch_peak or dinner_peak:
        return True, 2.0
    elif night_peak:
        return True, 1.5
    return False, 1.0

def _estimate_wait(shop_id, party_size, conn):
    """根据当前排队人数和高峰时段估算等候时间(分钟)"""
    is_peak, mult = _is_peak_hours()
    # 当前该商户排队中的组数
    waiting = conn.execute(
        "SELECT COUNT(*) FROM restaurant_queues WHERE shop_id=? AND status='waiting'",
        (shop_id,)
    ).fetchone()[0]
    # 基础等待: 每组约8分钟，高峰翻倍
    base = waiting * 8 * mult
    # 人数多也适当加时
    if party_size > 4:
        base += 10
    return max(5, int(base))


# ========== API - Shops ==========
@app.route('/api/shops')
def api_shops():
    conn = get_db()
    _ensure_tables(conn)
    rows = conn.execute('SELECT * FROM shops ORDER BY CAST(floor AS INTEGER), zone, name').fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d['tags'] = d['tags'].split(',') if d.get('tags') else []
        d['features'] = d['features'].split(',') if d.get('features') else []
        d['has_coupon'] = bool(d.get('has_coupon'))
        result.append(d)
    return jsonify(ok=True, data=result)


# ========== API - Offers ==========
@app.route('/api/offers')
def api_offers():
    conn = get_db()
    _ensure_tables(conn)
    rows = conn.execute("SELECT * FROM offers WHERE status='active' ORDER BY id").fetchall()
    conn.close()
    return jsonify(ok=True, data=[dict(r) for r in rows])


# ========== API - Redeem Goods ==========
@app.route('/api/redeem')
def api_redeem_goods():
    conn = get_db()
    _ensure_tables(conn)
    rows = conn.execute("SELECT * FROM redeem_goods WHERE status='active' ORDER BY points").fetchall()
    conn.close()
    return jsonify(ok=True, data=[dict(r) for r in rows])


# ========== API - Parking ==========
@app.route('/api/parking/query', methods=['POST'])
def api_parking_query():
    plate = request.json.get('plate', '').strip().upper()
    if not plate:
        return jsonify(ok=False, error='请输入车牌号')
    conn = get_db()
    _ensure_tables(conn)
    record = conn.execute(
        "SELECT * FROM parking_records WHERE plate=? AND status='parked' ORDER BY id DESC LIMIT 1",
        (plate,)
    ).fetchone()
    if not record:
        conn.close()
        return jsonify(ok=False, error=f'未查询到车牌 {plate} 的在场停车记录')
    entry = datetime.fromisoformat(record['entry_time']) if record['entry_time'] else datetime.now()
    now = datetime.now()
    duration = now - entry
    hours = duration.total_seconds() / 3600
    # 计费规则：首小时5元，之后每小时3元，封顶50元
    if hours <= 1:
        fee = 5.0
    else:
        fee = 5.0 + (hours - 1) * 3.0
    fee = min(fee, 50.0)
    fee = round(fee, 2)
    h = int(duration.total_seconds() // 3600)
    m = int((duration.total_seconds() % 3600) // 60)
    conn.close()
    return jsonify(ok=True, data={
        'plate': plate,
        'entry_time': entry.strftime('%Y-%m-%d %H:%M'),
        'duration': f'{h} 小时 {m} 分钟',
        'duration_minutes': int(duration.total_seconds() / 60),
        'fee': fee,
    })


@app.route('/api/parking/pay', methods=['POST'])
def api_parking_pay():
    plate = request.json.get('plate', '').strip().upper()
    if not plate:
        return jsonify(ok=False, error='请输入车牌号')
    conn = get_db()
    _ensure_tables(conn)
    record = conn.execute(
        "SELECT * FROM parking_records WHERE plate=? AND status='parked' ORDER BY id DESC LIMIT 1",
        (plate,)
    ).fetchone()
    if not record:
        conn.close()
        return jsonify(ok=False, error=f'未查询到车牌 {plate} 的待缴费记录')
    entry = datetime.fromisoformat(record['entry_time']) if record['entry_time'] else datetime.now()
    now = datetime.now()
    duration = now - entry
    hours = duration.total_seconds() / 3600
    if hours <= 1:
        fee = 5.0
    else:
        fee = 5.0 + (hours - 1) * 3.0
    fee = min(fee, 50.0)
    fee = round(fee, 2)
    conn.execute(
        "UPDATE parking_records SET status='paid', exit_time=?, fee=? WHERE id=?",
        (now.isoformat(), fee, record['id'])
    )
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={
        'plate': plate,
        'fee': fee,
        'paid_at': now.strftime('%Y-%m-%d %H:%M'),
        'message': f'缴费成功！车牌 {plate}，金额 ¥{fee:.2f}',
    })


# ========== API - 餐厅排队取号 ==========
@app.route('/api/restaurant/queue', methods=['POST'])
def api_restaurant_queue():
    """取号排队"""
    data = request.get_json()
    shop_id = data.get('shop_id', '').strip()
    phone = data.get('phone', '').strip()
    name = data.get('name', '').strip()
    party_size = int(data.get('party_size', 2))
    if not shop_id:
        return jsonify(ok=False, error='请选择餐厅')
    conn = get_db()
    _ensure_tables(conn)
    shop = conn.execute('SELECT name FROM shops WHERE id=? AND category="餐饮"', (shop_id,)).fetchone()
    if not shop:
        conn.close()
        return jsonify(ok=False, error='未找到该餐厅，请确认餐厅名称')
    # 生成排队号 (当日该商户的第N号)
    today = datetime.now().strftime('%Y-%m-%d')
    today_count = conn.execute(
        "SELECT COUNT(*) FROM restaurant_queues WHERE shop_id=? AND date(created_at)=?",
        (shop_id, today)
    ).fetchone()[0]
    qnum = today_count + 1
    est = _estimate_wait(shop_id, party_size, conn)
    # 前面还有几组
    ahead = conn.execute(
        "SELECT COUNT(*) FROM restaurant_queues WHERE shop_id=? AND status='waiting'",
        (shop_id,)
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO restaurant_queues (shop_id,shop_name,queue_number,customer_phone,customer_name,party_size,estimated_wait) VALUES (?,?,?,?,?,?,?)",
        (shop_id, shop['name'], qnum, phone, name, party_size, est)
    )
    conn.commit()
    _webhook_push(shop_id, 'new_queue', {'queue_number': qnum, 'party_size': party_size, 'phone': phone, 'name': name, 'estimated_wait': est})
    conn.close()
    return jsonify(ok=True, data={
        'shop_id': shop_id, 'shop_name': shop['name'],
        'queue_number': qnum, 'party_size': party_size,
        'estimated_wait': est, 'ahead_count': ahead,
        'peak_hours': _is_peak_hours()[0]
    })


@app.route('/api/restaurant/queue/<shop_id>', methods=['GET'])
def api_restaurant_queue_status(shop_id):
    """查询某餐厅排队状态 / 我的排队进度"""
    phone = request.args.get('phone', '')
    conn = get_db()
    _ensure_tables(conn)
    shop = conn.execute('SELECT name FROM shops WHERE id=?', (shop_id,)).fetchone()
    if not shop:
        conn.close()
        return jsonify(ok=False, error='餐厅不存在')
    # 当前排队组数
    waiting_count = conn.execute(
        "SELECT COUNT(*) FROM restaurant_queues WHERE shop_id=? AND status='waiting'",
        (shop_id,)
    ).fetchone()[0]
    # 估算等待时间
    est = _estimate_wait(shop_id, 2, conn)
    # 我的排队
    my_queue = None
    if phone:
        my = conn.execute(
            "SELECT * FROM restaurant_queues WHERE shop_id=? AND customer_phone=? AND status='waiting' ORDER BY id DESC LIMIT 1",
            (shop_id, phone)
        ).fetchone()
        if my:
            ahead = conn.execute(
                "SELECT COUNT(*) FROM restaurant_queues WHERE shop_id=? AND status='waiting' AND id<?",
                (shop_id, my['id'])
            ).fetchone()[0]
            my_queue = {
                'queue_number': my['queue_number'],
                'party_size': my['party_size'],
                'ahead_count': ahead,
                'estimated_wait': my['estimated_wait'],
                'status': my['status']
            }
    conn.close()
    return jsonify(ok=True, data={
        'shop_id': shop_id, 'shop_name': shop['name'],
        'waiting_groups': waiting_count,
        'estimated_wait': est,
        'peak_hours': _is_peak_hours()[0],
        'my_queue': my_queue
    })


@app.route('/api/restaurant/reserve', methods=['POST'])
def api_restaurant_reserve():
    """预约订位"""
    data = request.get_json()
    shop_id = data.get('shop_id', '').strip()
    phone = data.get('phone', '').strip()
    name = data.get('name', '').strip()
    party_size = int(data.get('party_size', 2))
    reserve_date = data.get('date', '').strip()
    reserve_time = data.get('time', '').strip()
    requests_text = data.get('requests', '').strip()
    if not shop_id or not phone or not name or not reserve_date or not reserve_time:
        return jsonify(ok=False, error='请填写完整的预约信息（餐厅/姓名/手机/日期/时间）')
    conn = get_db()
    _ensure_tables(conn)
    shop = conn.execute('SELECT name FROM shops WHERE id=?', (shop_id,)).fetchone()
    if not shop:
        conn.close()
        return jsonify(ok=False, error='未找到该餐厅')
    # 检查是否已有同日期冲突预约
    existing = conn.execute(
        "SELECT id FROM restaurant_reservations WHERE shop_id=? AND customer_phone=? AND reserve_date=? AND status='confirmed'",
        (shop_id, phone, reserve_date)
    ).fetchone()
    if existing:
        conn.close()
        return jsonify(ok=False, error='您已在该日期有预约，请勿重复预约')
    conn.execute(
        "INSERT INTO restaurant_reservations (shop_id,shop_name,customer_phone,customer_name,party_size,reserve_date,reserve_time,special_requests) VALUES (?,?,?,?,?,?,?,?)",
        (shop_id, shop['name'], phone, name, party_size, reserve_date, reserve_time, requests_text)
    )
    conn.commit()
    rid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    _webhook_push(shop_id, 'new_reservation', {'reservation_id': rid, 'phone': phone, 'name': name, 'party_size': party_size, 'date': reserve_date, 'time': reserve_time})
    conn.close()
    return jsonify(ok=True, data={
        'reservation_id': rid,
        'shop_name': shop['name'],
        'date': reserve_date,
        'time': reserve_time,
        'party_size': party_size
    })


@app.route('/api/restaurant/reservations', methods=['GET'])
def api_restaurant_reservations():
    """我的预约列表"""
    phone = request.args.get('phone', '')
    if not phone:
        return jsonify(ok=False, error='请提供手机号')
    conn = get_db()
    _ensure_tables(conn)
    rows = conn.execute(
        "SELECT * FROM restaurant_reservations WHERE customer_phone=? ORDER BY reserve_date DESC, reserve_time DESC LIMIT 20",
        (phone,)
    ).fetchall()
    conn.close()
    return jsonify(ok=True, data=[dict(r) for r in rows])


@app.route('/api/restaurant/status/<shop_id>', methods=['GET'])
def api_restaurant_live_status(shop_id):
    """餐厅实时状态：排队长度、营业状态、高峰标识"""
    conn = get_db()
    _ensure_tables(conn)
    shop = conn.execute('SELECT name,hours,category FROM shops WHERE id=?', (shop_id,)).fetchone()
    if not shop:
        conn.close()
        return jsonify(ok=False, error='餐厅不存在')
    waiting = conn.execute(
        "SELECT COUNT(*) FROM restaurant_queues WHERE shop_id=? AND status='waiting'",
        (shop_id,)
    ).fetchone()[0]
    is_peak, mult = _is_peak_hours()
    est = _estimate_wait(shop_id, 2, conn)
    # 当日已取号总数
    today = datetime.now().strftime('%Y-%m-%d')
    today_total = conn.execute(
        "SELECT COUNT(*) FROM restaurant_queues WHERE shop_id=? AND date(created_at)=?",
        (shop_id, today)
    ).fetchone()[0]
    conn.close()
    return jsonify(ok=True, data={
        'shop_id': shop_id,
        'shop_name': shop['name'],
        'hours': shop['hours'],
        'waiting_groups': waiting,
        'estimated_wait': est,
        'today_total': today_total,
        'peak_hours': is_peak,
        'peak_multiplier': mult
    })


# ========== 商户端 API（商户看板 + 叫号 + 核销） ==========
def _merchant_auth(shop_id, token):
    """验证商户 token，返回 shop 信息或 None"""
    conn = get_db()
    _ensure_tables(conn)
    row = conn.execute(
        "SELECT m.*, s.name,s.phone,s.hours FROM merchant_tokens m JOIN shops s ON m.shop_id=s.id WHERE m.shop_id=? AND m.token=?",
        (shop_id, token)
    ).fetchone()
    conn.close()
    return row

def _webhook_push(shop_id, event, data):
    """向商户 webhook URL 推送事件"""
    conn = get_db()
    _ensure_tables(conn)
    row = conn.execute(
        "SELECT m.webhook_url, s.name FROM merchant_tokens m JOIN shops s ON m.shop_id=s.id WHERE m.shop_id=?",
        (shop_id,)
    ).fetchone()
    conn.close()
    if not row or not row['webhook_url']:
        return
    try:
        import urllib.request
        payload = json.dumps({
            'event': event,
            'shop_id': shop_id,
            'shop_name': row['name'],
            'data': data,
            'time': datetime.now().isoformat()
        }, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(row['webhook_url'], data=payload, headers={'Content-Type': 'application/json'}, method='POST')
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass  # webhook 失败不影响主流程

@app.route('/api/merchant/dashboard', methods=['GET'])
def api_merchant_dashboard():
    """商户看板：当前排队列表 + 预订列表"""
    shop_id = request.args.get('shop_id', '')
    token = request.args.get('token', '')
    m = _merchant_auth(shop_id, token)
    if not m:
        return jsonify(ok=False, error='商户认证失败，请检查 shop_id 和 token')
    conn = get_db()
    _ensure_tables(conn)
    # 当前排队
    queues = conn.execute(
        "SELECT * FROM restaurant_queues WHERE shop_id=? AND status='waiting' ORDER BY id",
        (shop_id,)
    ).fetchall()
    # 今日预约
    today = datetime.now().strftime('%Y-%m-%d')
    reservations = conn.execute(
        "SELECT * FROM restaurant_reservations WHERE shop_id=? AND reserve_date>=? AND status='confirmed' ORDER BY reserve_date, reserve_time",
        (shop_id, today)
    ).fetchall()
    # 今日统计
    today_total = conn.execute(
        "SELECT COUNT(*) as cnt FROM restaurant_queues WHERE shop_id=? AND date(created_at)=?",
        (shop_id, today)
    ).fetchone()['cnt']
    conn.close()
    return jsonify(ok=True, data={
        'shop_name': m['name'],
        'shop_phone': m['phone'],
        'shop_hours': m['hours'],
        'webhook_url': m['webhook_url'],
        'token': m['token'],
        'queues': [dict(q) for q in queues],
        'reservations': [dict(r) for r in reservations],
        'today_total': today_total,
        'peak_hours': _is_peak_hours()[0]
    })

@app.route('/api/merchant/call', methods=['POST'])
def api_merchant_call():
    """商户叫号：将下一个等待中的号码标记为已叫号"""
    data = request.get_json()
    shop_id = data.get('shop_id', '')
    token = data.get('token', '')
    queue_id = data.get('queue_id')  # 可选，指定叫哪个号
    m = _merchant_auth(shop_id, token)
    if not m:
        return jsonify(ok=False, error='商户认证失败')
    conn = get_db()
    _ensure_tables(conn)
    if queue_id:
        q = conn.execute("SELECT * FROM restaurant_queues WHERE id=? AND shop_id=? AND status='waiting'", (queue_id, shop_id)).fetchone()
    else:
        q = conn.execute("SELECT * FROM restaurant_queues WHERE shop_id=? AND status='waiting' ORDER BY id LIMIT 1", (shop_id,)).fetchone()
    if not q:
        conn.close()
        return jsonify(ok=False, error='当前无等待中的排队')
    conn.execute("UPDATE restaurant_queues SET status='called' WHERE id=?", (q['id'],))
    conn.commit()
    conn.close()
    # 推送 webhook
    _webhook_push(shop_id, 'queue_called', {'queue_id': q['id'], 'queue_number': q['queue_number'], 'party_size': q['party_size'], 'customer_name': q['customer_name'], 'customer_phone': q['customer_phone']})
    return jsonify(ok=True, data={'queue': dict(q), 'message': f'已叫号 {q["queue_number"]} 号 · {q["party_size"]}人位'})

@app.route('/api/merchant/seat', methods=['POST'])
def api_merchant_seat():
    """商户确认入座"""
    data = request.get_json()
    shop_id = data.get('shop_id', '')
    token = data.get('token', '')
    queue_id = data.get('queue_id')
    m = _merchant_auth(shop_id, token)
    if not m:
        return jsonify(ok=False, error='商户认证失败')
    if not queue_id:
        return jsonify(ok=False, error='请提供 queue_id')
    conn = get_db()
    _ensure_tables(conn)
    conn.execute("UPDATE restaurant_queues SET status='seated' WHERE id=? AND shop_id=?", (queue_id, shop_id))
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={'message': '已确认入座'})

@app.route('/api/merchant/cancel-queue', methods=['POST'])
def api_merchant_cancel_queue():
    """商户取消排队（过号/客户放弃）"""
    data = request.get_json()
    shop_id = data.get('shop_id', '')
    token = data.get('token', '')
    queue_id = data.get('queue_id')
    m = _merchant_auth(shop_id, token)
    if not m:
        return jsonify(ok=False, error='商户认证失败')
    conn = get_db()
    _ensure_tables(conn)
    conn.execute("UPDATE restaurant_queues SET status='cancelled' WHERE id=? AND shop_id=?", (queue_id, shop_id))
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={'message': '已取消排队'})

@app.route('/api/merchant/reservation/confirm', methods=['POST'])
def api_merchant_confirm_reservation():
    """商户确认预订到场"""
    data = request.get_json()
    shop_id = data.get('shop_id', '')
    token = data.get('token', '')
    reservation_id = data.get('reservation_id')
    m = _merchant_auth(shop_id, token)
    if not m:
        return jsonify(ok=False, error='商户认证失败')
    conn = get_db()
    _ensure_tables(conn)
    conn.execute("UPDATE restaurant_reservations SET status='completed' WHERE id=? AND shop_id=?", (reservation_id, shop_id))
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={'message': '已确认到场'})

@app.route('/api/merchant/webhook', methods=['PUT'])
def api_merchant_set_webhook():
    """商户设置 webhook URL"""
    data = request.get_json()
    shop_id = data.get('shop_id', '')
    token = data.get('token', '')
    webhook_url = data.get('webhook_url', '')
    m = _merchant_auth(shop_id, token)
    if not m:
        return jsonify(ok=False, error='商户认证失败')
    conn = get_db()
    _ensure_tables(conn)
    conn.execute("UPDATE merchant_tokens SET webhook_url=? WHERE shop_id=?", (webhook_url, shop_id))
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={'message': 'Webhook 地址已更新'})

@app.route('/api/merchant/token', methods=['GET'])
def api_merchant_get_token():
    """查看/重置商户 token"""
    shop_id = request.args.get('shop_id', '')
    token = request.args.get('token', '')
    m = _merchant_auth(shop_id, token)
    if not m:
        return jsonify(ok=False, error='认证失败')
    conn = get_db()
    _ensure_tables(conn)
    row = conn.execute("SELECT token,webhook_url FROM merchant_tokens WHERE shop_id=?", (shop_id,)).fetchone()
    conn.close()
    return jsonify(ok=True, data={'shop_id': shop_id, 'token': row['token'], 'webhook_url': row['webhook_url']})

@app.route('/api/admin/merchant-tokens', methods=['GET'])
def api_admin_merchant_tokens():
    """管理员查看所有商户 token（生产环境需加权限）"""
    conn = get_db()
    _ensure_tables(conn)
    rows = conn.execute(
        "SELECT m.shop_id,s.name,s.category,s.zone,s.floor,m.token,m.webhook_url,m.phone_notify FROM merchant_tokens m JOIN shops s ON m.shop_id=s.id ORDER BY s.name"
    ).fetchall()
    conn.close()
    return jsonify(ok=True, data=[dict(r) for r in rows])

@app.route('/api/merchant/stream')
def api_merchant_sse():
    """SSE 实时推送 - 商户看板实时数据流"""
    shop_id = request.args.get('shop_id', '')
    token = request.args.get('token', '')
    m = _merchant_auth(shop_id, token)
    if not m:
        return jsonify(ok=False, error='商户认证失败')
    def generate():
        import time as _time
        last_hash = ''
        while True:
            conn = get_db()
            _ensure_tables(conn)
            queues = conn.execute(
                "SELECT * FROM restaurant_queues WHERE shop_id=? AND status='waiting' ORDER BY id",
                (shop_id,)
            ).fetchall()
            today = datetime.now().strftime('%Y-%m-%d')
            reservations = conn.execute(
                "SELECT * FROM restaurant_reservations WHERE shop_id=? AND reserve_date>=? AND status='confirmed' ORDER BY reserve_date, reserve_time",
                (shop_id, today)
            ).fetchall()
            today_total = conn.execute(
                "SELECT COUNT(*) FROM restaurant_queues WHERE shop_id=? AND date(created_at)=?",
                (shop_id, today)
            ).fetchone()[0]
            conn.close()
            data = {
                'queues': [dict(q) for q in queues],
                'reservations': [dict(r) for r in reservations],
                'today_total': today_total,
                'peak_hours': _is_peak_hours()[0]
            }
            current_hash = str(len(queues)) + str(today_total) + str([q['id'] for q in queues])
            if current_hash != last_hash:
                last_hash = current_hash
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            _time.sleep(3)
    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

@app.route('/api/merchant/print', methods=['POST'])
def api_merchant_print():
    """生成排队小票打印指令（ESC/POS 格式，base64 返回）"""
    data = request.get_json()
    shop_id = data.get('shop_id', '')
    token = data.get('token', '')
    queue_id = data.get('queue_id')
    m = _merchant_auth(shop_id, token)
    if not m:
        return jsonify(ok=False, error='商户认证失败')
    conn = get_db()
    _ensure_tables(conn)
    q = conn.execute("SELECT * FROM restaurant_queues WHERE id=?", (queue_id,)).fetchone()
    conn.close()
    if not q:
        return jsonify(ok=False, error='排队记录不存在')
    # 构造 ESC/POS 打印指令
    esc = b'\x1b'
    cmds = []
    cmds.append(esc + b'@')  # 初始化
    cmds.append(esc + b'a\x01')  # 居中
    cmds.append(f'{m["name"]}\n'.encode('gbk'))
    cmds.append(f'排队小票\n'.encode('gbk'))
    cmds.append(b'-' * 32 + b'\n')
    cmds.append(esc + b'a\x00')  # 左对齐
    cmds.append(f'排队号：{q["queue_number"]}号\n'.encode('gbk'))
    cmds.append(f'人数：{q["party_size"]}人\n'.encode('gbk'))
    cmds.append(f'时间：{q["created_at"]}\n'.encode('gbk'))
    cmds.append(f'前面还有：{q["estimated_wait"]//8}桌\n'.encode('gbk'))
    cmds.append(f'预计等待：{q["estimated_wait"]}分钟\n'.encode('gbk'))
    cmds.append(b'-' * 32 + b'\n')
    cmds.append(esc + b'a\x01')  # 居中
    cmds.append(f'前面排队{max(0,q["queue_number"]-1)}桌，过号重取\n'.encode('gbk'))
    cmds.append(b'\n' * 3)
    cmds.append(esc + b'm')  # 切纸
    import base64
    return jsonify(ok=True, data={
        'queue_number': q['queue_number'],
        'shop_name': m['name'],
        'print_base64': base64.b64encode(b''.join(cmds)).decode('ascii')
    })


# ========== 主理人/活动组织者 API ==========
@app.route('/api/organizer/apply', methods=['POST'])
def api_organizer_apply():
    """主理人在线提交入驻申请 → 自动生成工单对接运营"""
    data = request.get_json()
    phone = data.get('phone', '').strip()
    name = data.get('name', '').strip()
    brand = data.get('brand', '').strip()
    biz_type = data.get('biz_type', '').strip()
    area = data.get('area', '').strip()
    remark = data.get('remark', '').strip()
    if not phone or not name or not brand:
        return jsonify(ok=False, error='请填写手机号、姓名和品牌名称')
    conn = get_db()
    _ensure_tables(conn)
    title = f'入驻申请 - {brand}'
    desc = json.dumps({
        'phone': phone, 'name': name, 'brand': brand,
        'biz_type': biz_type, 'area': area, 'remark': remark
    }, ensure_ascii=False)
    conn.execute(
        "INSERT INTO work_orders (tenant_id, type, title, description, priority, status, reporter, reporter_contact, merchant) VALUES (?,?,?,?,?,?,?,?,?)",
        (1, '入驻申请', title, desc, 'normal', 'pending', name, phone, brand)
    )
    wid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={'work_order_id': wid, 'message': '入驻申请已提交，运营团队将在1-3个工作日内与您联系'})

@app.route('/api/event/schedule', methods=['POST'])
def api_event_schedule():
    """活动排期报备 → 自动生成工单"""
    data = request.get_json()
    phone = data.get('phone', '').strip()
    name = data.get('name', '').strip()
    event_name = data.get('event_name', '').strip()
    event_type = data.get('event_type', '')
    venue = data.get('venue', '')
    start_date = data.get('start_date', '')
    end_date = data.get('end_date', '')
    expected_attendance = int(data.get('expected_attendance', 0))
    description = data.get('description', '')
    if not phone or not name or not event_name or not start_date:
        return jsonify(ok=False, error='请填写手机号、姓名、活动名称和开始日期')
    conn = get_db()
    _ensure_tables(conn)
    # 检查日期冲突（同一场地已有排期）
    conflict = conn.execute(
        "SELECT * FROM event_schedules WHERE venue=? AND status='approved' AND ((start_date<=? AND end_date>=?) OR (start_date<=? AND end_date>=?))",
        (venue, end_date or start_date, start_date, start_date, end_date or start_date)
    ).fetchone()
    if conflict and venue:
        conn.close()
        return jsonify(ok=False, error=f'{venue} 在 {start_date}~{end_date} 已有排期，请选择其他日期')
    conn.execute(
        "INSERT INTO event_schedules (organizer_phone,organizer_name,event_name,event_type,venue,start_date,end_date,expected_attendance,description) VALUES (?,?,?,?,?,?,?,?,?)",
        (phone, name, event_name, event_type, venue, start_date, end_date, expected_attendance, description)
    )
    sid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    # 自动生成工单
    title = f'活动排期报备 - {event_name}'
    desc_content = json.dumps({
        'phone': phone, 'name': name, 'event_name': event_name,
        'event_type': event_type, 'venue': venue, 'start_date': start_date,
        'end_date': end_date, 'expected_attendance': expected_attendance,
        'description': description
    }, ensure_ascii=False)
    conn.execute(
        "INSERT INTO work_orders (tenant_id, type, title, description, priority, status, reporter, reporter_contact, merchant) VALUES (?,?,?,?,?,?,?,?,?)",
        (1, '活动排期', title, desc_content, 'normal', 'pending', name, phone, event_name)
    )
    wid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.execute("UPDATE event_schedules SET work_order_id=? WHERE id=?", (wid, sid))
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={'schedule_id': sid, 'work_order_id': wid, 'message': '排期报备已提交，运营团队将审核后与您确认'})

@app.route('/api/venue/book', methods=['POST'])
def api_venue_book():
    """场地时段预定"""
    data = request.get_json()
    phone = data.get('phone', '').strip()
    name = data.get('name', '').strip()
    venue_name = data.get('venue_name', '').strip()
    venue_type = data.get('venue_type', '').strip()
    booking_date = data.get('date', '').strip()
    start_time = data.get('start_time', '').strip()
    end_time = data.get('end_time', '').strip()
    purpose = data.get('purpose', '')
    if not phone or not venue_name or not booking_date or not start_time:
        return jsonify(ok=False, error='请填写完整信息')
    conn = get_db()
    _ensure_tables(conn)
    # 检查时段冲突
    conflict = conn.execute(
        "SELECT * FROM venue_bookings WHERE venue_name=? AND booking_date=? AND status='confirmed' AND ((start_time<=? AND end_time>?) OR (start_time<? AND end_time>=?))",
        (venue_name, booking_date, end_time or start_time, start_time, end_time or start_time, start_time)
    ).fetchone()
    if conflict:
        conn.close()
        return jsonify(ok=False, error=f'{venue_name} 在 {booking_date} {start_time}-{end_time} 已被预定')
    # 计费（根据 venue_type）
    fee_map = {'booth': 300, 'classroom': 120, 'lounge': 300, 'ad': 500}
    fee = fee_map.get(venue_type, 200)
    conn.execute(
        "INSERT INTO venue_bookings (venue_name,venue_type,customer_phone,customer_name,booking_date,start_time,end_time,purpose,fee) VALUES (?,?,?,?,?,?,?,?,?)",
        (venue_name, venue_type, phone, name, booking_date, start_time, end_time or start_time, purpose, fee)
    )
    bid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    # 自动生成工单
    title = f'场地预定 - {venue_name}'
    desc_content = json.dumps({
        'phone': phone, 'name': name, 'venue_name': venue_name,
        'venue_type': venue_type, 'date': booking_date,
        'start_time': start_time, 'end_time': end_time, 'purpose': purpose, 'fee': fee
    }, ensure_ascii=False)
    conn.execute(
        "INSERT INTO work_orders (tenant_id, type, title, description, priority, status, reporter, reporter_contact, merchant) VALUES (?,?,?,?,?,?,?,?,?)",
        (1, '场地预定', title, desc_content, 'normal', 'pending', name, phone, venue_name)
    )
    wid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={'booking_id': bid, 'work_order_id': wid, 'fee': fee, 'message': f'场地预定成功！{venue_name} {booking_date} {start_time}'})

@app.route('/api/venue/bookings', methods=['GET'])
def api_venue_bookings():
    """查询我的场地预定"""
    phone = request.args.get('phone', '')
    if not phone:
        return jsonify(ok=False, error='请提供手机号')
    conn = get_db()
    _ensure_tables(conn)
    bookings = conn.execute(
        "SELECT * FROM venue_bookings WHERE customer_phone=? ORDER BY booking_date DESC LIMIT 20",
        (phone,)
    ).fetchall()
    conn.close()
    return jsonify(ok=True, data=[dict(b) for b in bookings])

@app.route('/api/venue/slots', methods=['GET'])
def api_venue_slots():
    """查询场地可用时段"""
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    venue_name = request.args.get('venue', '')
    conn = get_db()
    _ensure_tables(conn)
    booked = conn.execute(
        "SELECT start_time,end_time FROM venue_bookings WHERE venue_name=? AND booking_date=? AND status='confirmed'",
        (venue_name, date) if venue_name else ('%', date)
    ).fetchall() if venue_name else []
    conn.close()
    # 默认营业时段 10:00-22:00，每小时一个 slot
    slots = []
    for h in range(10, 22):
        slot = f'{h:02d}:00'
        taken = any(b['start_time'] <= slot < b['end_time'] for b in booked)
        slots.append({'time': slot, 'available': not taken})
    return jsonify(ok=True, data={'date': date, 'venue': venue_name or '全部', 'slots': slots})

@app.route('/api/organizer/settlement', methods=['GET'])
def api_organizer_settlement():
    """主理人结算查询"""
    phone = request.args.get('phone', '')
    if not phone:
        return jsonify(ok=False, error='请提供手机号')
    conn = get_db()
    _ensure_tables(conn)
    settlements = conn.execute(
        "SELECT * FROM organizer_settlements WHERE organizer_phone=? ORDER BY created_at DESC LIMIT 20",
        (phone,)
    ).fetchall()
    # 同时返回活动排期统计
    events = conn.execute(
        "SELECT * FROM event_schedules WHERE organizer_phone=? ORDER BY start_date DESC LIMIT 10",
        (phone,)
    ).fetchall()
    bookings = conn.execute(
        "SELECT * FROM venue_bookings WHERE customer_phone=? AND status='confirmed' ORDER BY booking_date DESC LIMIT 10",
        (phone,)
    ).fetchall()
    conn.close()
    return jsonify(ok=True, data={
        'settlements': [dict(s) for s in settlements],
        'events': [dict(e) for e in events],
        'bookings': [dict(b) for b in bookings],
        'total_events': len(events),
        'total_bookings': len(bookings)
    })

@app.route('/api/organizer/applications', methods=['GET'])
def api_organizer_my_applications():
    """我的入驻申请/排期状态"""
    phone = request.args.get('phone', '')
    if not phone:
        return jsonify(ok=False, error='请提供手机号')
    conn = get_db()
    _ensure_tables(conn)
    orders = conn.execute(
        "SELECT id,type,title,status,created_at FROM work_orders WHERE reporter_contact=? AND type IN ('入驻申请','活动排期','场地预定') ORDER BY id DESC LIMIT 20",
        (phone,)
    ).fetchall()
    conn.close()
    return jsonify(ok=True, data=[dict(o) for o in orders])

@app.route('/api/organizer/my-schedules', methods=['GET'])
def api_organizer_my_schedules():
    """我的活动排期列表"""
    phone = request.args.get('phone', '')
    if not phone:
        return jsonify(ok=False, error='请提供手机号')
    conn = get_db()
    _ensure_tables(conn)
    schedules = conn.execute(
        "SELECT * FROM event_schedules WHERE organizer_phone=? ORDER BY start_date DESC LIMIT 20",
        (phone,)
    ).fetchall()
    conn.close()
    return jsonify(ok=True, data=[dict(s) for s in schedules])

@app.route('/api/admin/organizer-applications', methods=['GET'])
def api_admin_organizer_applications():
    """管理员查看所有入驻/排期/场地工单"""
    conn = get_db()
    _ensure_tables(conn)
    orders = conn.execute(
        "SELECT * FROM work_orders WHERE type IN ('入驻申请','活动排期','场地预定') ORDER BY id DESC LIMIT 100"
    ).fetchall()
    schedules = conn.execute(
        "SELECT * FROM event_schedules ORDER BY start_date DESC LIMIT 50"
    ).fetchall()
    bookings = conn.execute(
        "SELECT * FROM venue_bookings WHERE status='confirmed' ORDER BY booking_date DESC LIMIT 50"
    ).fetchall()
    conn.close()
    return jsonify(ok=True, data={
        'work_orders': [dict(o) for o in orders],
        'schedules': [dict(s) for s in schedules],
        'bookings': [dict(b) for b in bookings]
    })


# ========== 商务合作 API（场地看场 + 意向登记 + 团建定制） ==========
@app.route('/api/biz/visit', methods=['POST'])
def api_biz_visit():
    """场地预约看场：校验场地可用性 → 生成工单推市场专员"""
    data = request.get_json()
    venue_name = data.get('venue_name', '').strip()
    date = data.get('date', '').strip()
    time = data.get('time', '').strip()
    phone = data.get('phone', '').strip()
    name = data.get('name', '').strip()
    purpose = data.get('purpose', '').strip()
    if not venue_name or not date or not phone or not name:
        return jsonify(ok=False, error='请填写场地、日期、联系人和手机号')
    conn = get_db()
    _ensure_tables(conn)
    # 校验场地可用性（同场地同日已确认的看场/预定冲突）
    conflict = conn.execute(
        "SELECT * FROM venue_bookings WHERE venue_name=? AND booking_date=? AND status='confirmed' AND (? BETWEEN start_time AND end_time OR ? BETWEEN start_time AND end_time)",
        (venue_name, date, time, time)
    ).fetchone()
    if conflict:
        conn.close()
        return jsonify(ok=False, error=f'{venue_name} 在 {date} {time} 已有安排，请选择其他时段')
    # 记录看场预约
    conn.execute(
        "INSERT INTO venue_bookings (venue_name,venue_type,customer_phone,customer_name,booking_date,start_time,end_time,purpose,fee,status) VALUES (?,?,?,?,?,?,?,?,0,'visit')",
        (venue_name, 'visit', phone, name, date, time, time, purpose)
    )
    vid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    # 生成商务工单
    title = f'场地看场预约 - {venue_name}'
    desc = json.dumps({'venue_name': venue_name, 'date': date, 'time': time, 'phone': phone, 'name': name, 'purpose': purpose}, ensure_ascii=False)
    conn.execute(
        "INSERT INTO work_orders (tenant_id, type, title, description, priority, status, reporter, reporter_contact, merchant) VALUES (?,?,?,?,?,?,?,?,?)",
        (1, '场地看场', title, desc, 'normal', 'pending', name, phone, venue_name)
    )
    wid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={'visit_id': vid, 'work_order_id': wid, 'message': f'看场预约成功！{venue_name} {date} {time}，市场专员将尽快与您联系'})

@app.route('/api/biz/intent', methods=['POST'])
def api_biz_intent():
    """意向登记：品牌入驻/多经合作/广告投放 → 商务工单"""
    data = request.get_json()
    intent_type = data.get('intent_type', '').strip()
    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    brand = data.get('brand', '').strip()
    area = data.get('area', '').strip()
    remark = data.get('remark', '').strip()
    if not intent_type or not name or not phone:
        return jsonify(ok=False, error='请填写意向类型、联系人和手机号')
    conn = get_db()
    _ensure_tables(conn)
    title = f'商务意向 - {intent_type}'
    desc = json.dumps({'intent_type': intent_type, 'name': name, 'phone': phone, 'brand': brand, 'area': area, 'remark': remark}, ensure_ascii=False)
    conn.execute(
        "INSERT INTO work_orders (tenant_id, type, title, description, priority, status, reporter, reporter_contact, merchant) VALUES (?,?,?,?,?,?,?,?,?)",
        (1, '商务意向', title, desc, 'normal', 'pending', name, phone, brand)
    )
    wid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={'work_order_id': wid, 'message': '意向登记成功，24小时内将有专人对接'})

@app.route('/api/biz/team-building', methods=['POST'])
def api_biz_team_building():
    """团建/活动定制：AI 初步匹配方案与报价 → 转人工深化"""
    data = request.get_json()
    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    org_name = data.get('org_name', '').strip()
    people = int(data.get('people', 0) or 0)
    date = data.get('date', '').strip()
    budget = int(data.get('budget', 0) or 0)
    description = data.get('description', '').strip()
    if not name or not phone or not description:
        return jsonify(ok=False, error='请填写联系人、手机号和需求描述')
    # AI 初步匹配方案与报价（基于人数/预算）
    venue_suggest = '共享教室(中型30人)' if people <= 30 else ('会客厅(精品40人)' if people <= 40 else '中庭活动区')
    if budget > 0:
        est_low = int(budget * 0.7)
        est_high = int(budget * 1.2)
        quote = f'参考预算 ¥{est_low}~{est_high}'
    else:
        quote = f'参考价 ¥{people * 60}~{people * 120}（含场地+基础物料）'
    suggestion = f'推荐场地：{venue_suggest}；{quote}。具体方案将由专员与您深化确认。'
    conn = get_db()
    _ensure_tables(conn)
    title = f'团建/活动定制 - {org_name or name}'
    desc = json.dumps({'name': name, 'phone': phone, 'org_name': org_name, 'people': people, 'date': date, 'budget': budget, 'description': description, 'suggestion': suggestion}, ensure_ascii=False)
    conn.execute(
        "INSERT INTO work_orders (tenant_id, type, title, description, priority, status, reporter, reporter_contact, merchant) VALUES (?,?,?,?,?,?,?,?,?)",
        (1, '团建定制', title, desc, 'normal', 'pending', name, phone, org_name or name)
    )
    wid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={'work_order_id': wid, 'suggestion': suggestion, 'message': '需求已提交，专员将根据初步方案与您深化对接'})


# ========== 物业报修与投诉 API ==========
@app.route('/api/repair', methods=['POST'])
def api_repair():
    """设施报修：AI 自动分类 → 生成工单分派物业工程岗"""
    data = request.get_json()
    location = data.get('location', '').strip()
    description = data.get('description', '').strip()
    image = data.get('image', '')  # 可选 base64
    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    if not description or not name or not phone:
        return jsonify(ok=False, error='请填写问题描述、联系人和手机号')
    text = location + ' ' + description
    # AI 自动分类（具体关键词优先）
    repair_categories = {
        '漏水': ['漏水', '渗水', '积水', '地漏', '下水道'],
        '电梯': ['电梯', '扶梯', '升降', '卡住'],
        '空调': ['空调', '冷气', '暖气', '通风', '制冷', '不凉', '不热'],
        '门锁': ['门锁', '锁', '门窗', '玻璃', '卷帘', '把手'],
        '卫生': ['卫生', '垃圾', '清洁', '异味', '厕所', '洗手间', '污渍'],
        '水电': ['水管', '电路', '插座', '灯泡', '照明', '跳闸', '停水', '停电', '水', '电'],
    }
    category = '其他'
    for cat, kws in repair_categories.items():
        if any(k in text for k in kws):
            category = cat
            break
    # 三级分级：电梯/漏水/水电 = 紧急，其余 = 一般
    priority = 'urgent' if category in ('电梯', '漏水', '水电') else 'normal'
    assignee_map = {'水电': '水电工程组', '空调': '暖通工程组', '漏水': '给排水工程组', '门锁': '综合维修组', '电梯': '电梯维保组', '卫生': '保洁组', '其他': '综合维修组'}
    assignee = assignee_map.get(category, '综合维修组')
    conn = get_db()
    _ensure_tables(conn)
    title = f'报修 - {category} - {location or "待定位"}'
    desc = json.dumps({'location': location, 'description': description, 'category': category, 'assignee': assignee, 'image': image}, ensure_ascii=False)
    conn.execute(
        "INSERT INTO work_orders (tenant_id, type, title, description, priority, status, reporter, reporter_contact, merchant) VALUES (?,?,?,?,?,?,?,?,?)",
        (1, '报修', title, desc, priority, 'pending', name, phone, assignee)
    )
    wid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={'work_order_id': wid, 'category': category, 'assignee': assignee, 'message': f'报修工单已生成（{category}），已分派{assignee}，将尽快处理'})

def _classify_complaint_level(content):
    """投诉三级分级：返回 (level, level_name, deadline, requirement)"""
    critical_kw = ['人身安全', '伤亡', '受伤', '死亡', '中毒', '触电', '火灾', '群体', '集体', '聚众', '闹事', '食物中毒', '食品安全', '生命危险', '昏迷', '重伤', '突发疾病', '踩踏', '恐吓', '暴力', '休克', '窒息']
    urgent_kw = ['安全隐患', '安全', '消防', '危险', '电梯', '漏水', '漏电', '短路', '停电', '设施故障', '设备故障', '故障', '升级', '威胁', '纠纷', '赔偿', '燃气', '天然气', '爆炸', '隐患', '着火']
    if any(k in content for k in critical_kw):
        return 'critical', '重大投诉', '立即', '实时推送管理层，启动应急处理流程'
    if any(k in content for k in urgent_kw):
        return 'urgent', '紧急投诉', '4小时', '1小时内响应，4小时内给出处理方案'
    return 'normal', '一般投诉', '24小时', '24小时内处理回复'

@app.route('/api/complaint', methods=['POST'])
def api_complaint():
    """投诉建议：AI 自动分类 + 三级分级 → 生成工单分派负责人"""
    data = request.get_json()
    kind = data.get('kind', '投诉').strip()
    content = data.get('content', '').strip()
    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    if not content or not name or not phone:
        return jsonify(ok=False, error='请填写内容、联系人和手机号')
    # AI 分类（安全等关键类优先）
    categories = {
        '安全': ['安全', '消防', '危险', '隐患', '火灾'],
        '服务态度': ['态度', '服务', '骂', '敷衍', '冷漠'],
        '环境卫生': ['卫生', '脏', '垃圾', '异味', '清洁'],
        '设施设备': ['设备', '设施', '坏了', '故障', '损坏'],
        '停车': ['停车', '车位', '堵车', '收费'],
        '噪音': ['噪音', '吵', '扰民', '喧哗'],
    }
    category = '其他'
    for c, kws in categories.items():
        if any(k in content for k in kws):
            category = c
            break
    # 三级分级
    level, level_name, deadline, requirement = _classify_complaint_level(content)
    priority_map = {'critical': 'critical', 'urgent': 'urgent', 'normal': 'normal'}
    priority = priority_map[level]
    conn = get_db()
    _ensure_tables(conn)
    title = f'{kind} - {level_name} - {category}'
    desc = json.dumps({'kind': kind, 'content': content, 'category': category, 'level': level, 'level_name': level_name, 'deadline': deadline, 'requirement': requirement}, ensure_ascii=False)
    conn.execute(
        "INSERT INTO work_orders (tenant_id, type, title, description, priority, status, reporter, reporter_contact) VALUES (?,?,?,?,?,?,?,?)",
        (1, '投诉建议', title, desc, priority, 'pending', name, phone)
    )
    wid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={
        'work_order_id': wid,
        'category': category,
        'level': level,
        'level_name': level_name,
        'deadline': deadline,
        'requirement': requirement,
        'message': f'已提交（{level_name}），{requirement}'
    })

@app.route('/api/property/my-orders', methods=['GET'])
def api_property_my_orders():
    """我的报修/投诉工单进度查询"""
    phone = request.args.get('phone', '').strip()
    if not phone:
        return jsonify(ok=False, error='请提供手机号')
    conn = get_db()
    _ensure_tables(conn)
    orders = conn.execute(
        "SELECT id, type, title, description, priority, status, created_at, updated_at FROM work_orders WHERE reporter_contact=? AND type IN ('报修','投诉建议') ORDER BY id DESC LIMIT 20",
        (phone,)
    ).fetchall()
    conn.close()
    return jsonify(ok=True, data=[dict(o) for o in orders])


# ========== 人工客服对话 API ==========
@app.route('/api/human-chat', methods=['POST'])
def api_human_chat():
    """用户发送消息给人工客服"""
    data = request.get_json()
    sid = data.get('session_id', request.cookies.get('session', 'anonymous'))
    message = data.get('message', '').strip()
    phone = data.get('phone', '')
    name = data.get('name', '')
    if not message:
        return jsonify(ok=False, error='消息不能为空')
    conn = get_db()
    _ensure_tables(conn)
    # 首次消息自动创建工单
    existing = conn.execute(
        "SELECT work_order_id FROM human_chat_messages WHERE session_id=? AND role='user' LIMIT 1",
        (sid,)
    ).fetchone()
    wid = existing['work_order_id'] if existing else None
    if not wid:
        title = f'人工客服 - {name or phone or sid[:8]}'
        conn.execute(
            "INSERT INTO work_orders (tenant_id, type, title, description, priority, status, reporter, reporter_contact) VALUES (?,?,?,?,?,?,?,?)",
            (1, '人工客服', title, message[:200], 'high', 'pending', name or '匿名用户', phone or sid)
        )
        wid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    # 保存消息
    conn.execute(
        "INSERT INTO human_chat_messages (session_id, user_phone, user_name, role, content, work_order_id) VALUES (?,?,?,?,?,?)",
        (sid, phone, name, 'user', message, wid)
    )
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={'work_order_id': wid, 'status': 'pending'})

@app.route('/api/human-chat/session', methods=['GET'])
def api_human_chat_session():
    """获取人工客服对话历史"""
    sid = request.args.get('session_id', '')
    if not sid:
        sid = request.cookies.get('session', 'anonymous')
    conn = get_db()
    _ensure_tables(conn)
    msgs = conn.execute(
        "SELECT * FROM human_chat_messages WHERE session_id=? ORDER BY id",
        (sid,)
    ).fetchall()
    # 检查是否有 agent 回复
    last_agent = conn.execute(
        "SELECT * FROM human_chat_messages WHERE session_id=? AND role='agent' ORDER BY id DESC LIMIT 1",
        (sid,)
    ).fetchone()
    conn.close()
    return jsonify(ok=True, data={
        'messages': [dict(m) for m in msgs],
        'has_agent': bool(last_agent),
        'last_agent_msg': dict(last_agent) if last_agent else None
    })

@app.route('/api/human-chat/reply', methods=['POST'])
def api_human_chat_reply():
    """客服人员回复用户（管理员或后台调用）"""
    data = request.get_json()
    sid = data.get('session_id', '')
    message = data.get('message', '').strip()
    if not sid or not message:
        return jsonify(ok=False, error='参数不完整')
    conn = get_db()
    _ensure_tables(conn)
    conn.execute(
        "INSERT INTO human_chat_messages (session_id, role, content) VALUES (?,?,?)",
        (sid, 'agent', message)
    )
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={'status': 'replied'})

@app.route('/api/admin/human-chats', methods=['GET'])
def api_admin_human_chats():
    """管理员查看人工客服会话列表"""
    conn = get_db()
    _ensure_tables(conn)
    # 按 session 分组，取每个 session 的最新用户消息
    sessions = conn.execute("""
        SELECT session_id, user_phone, user_name,
               (SELECT content FROM human_chat_messages WHERE session_id=m.session_id AND role='user' ORDER BY id DESC LIMIT 1) as last_msg,
               (SELECT created_at FROM human_chat_messages WHERE session_id=m.session_id ORDER BY id DESC LIMIT 1) as last_time,
               COUNT(CASE WHEN role='agent' THEN 1 END) as agent_replies
        FROM human_chat_messages m
        GROUP BY session_id
        ORDER BY last_time DESC
        LIMIT 50
    """).fetchall()
    conn.close()
    return jsonify(ok=True, data=[dict(s) for s in sessions])


# ========== 满意度评价 API ==========
@app.route('/api/feedback', methods=['POST'])
def api_feedback():
    """提交满意度评价"""
    data = request.get_json()
    feedback_type = data.get('feedback_type', 'chat_ai')  # chat_ai / chat_human / business
    rating = int(data.get('rating', 0))
    feedback_text = data.get('feedback_text', '').strip()
    phone = data.get('phone', '').strip()
    biz_type = data.get('biz_type', '').strip()
    order_id = data.get('order_id', '').strip()
    if not rating or rating < 1 or rating > 5:
        return jsonify(ok=False, error='请选择评分（1-5星）')
    conn = get_db()
    _ensure_tables(conn)
    conn.execute(
        "INSERT INTO feedbacks (user_phone, feedback_type, biz_type, order_id, rating, feedback_text) VALUES (?,?,?,?,?,?)",
        (phone, feedback_type, biz_type, order_id, rating, feedback_text)
    )
    conn.commit()
    conn.close()
    # 低分反馈（≤2星）且含文字 → 归集为待优化问题（错误应答线索）
    if rating <= 2 and feedback_text:
        _add_kb_pending(1, feedback_text, 'feedback')
    return jsonify(ok=True, data={'message': '感谢您的评价！'})

@app.route('/api/admin/feedback', methods=['GET'])
@login_required
def api_admin_feedback():
    """后台查看评价汇总"""
    if session.get('role') not in ('admin','super_admin','tenant_admin'):
        return jsonify(ok=False, error='权限不足')
    conn = get_db()
    _ensure_tables(conn)
    rows = conn.execute("SELECT * FROM feedbacks ORDER BY id DESC LIMIT 100").fetchall()
    # 汇总
    total = conn.execute("SELECT COUNT(*) FROM feedbacks").fetchone()[0]
    avg = conn.execute("SELECT AVG(rating) FROM feedbacks").fetchone()[0]
    by_type = conn.execute("SELECT feedback_type, COUNT(*) as cnt, AVG(rating) as avg_r FROM feedbacks GROUP BY feedback_type").fetchall()
    conn.close()
    return jsonify(ok=True, data={
        'list': [dict(r) for r in rows],
        'total': total,
        'avg_rating': round(avg, 2) if avg else 0,
        'by_type': [dict(t) for t in by_type]
    })


# ========== 知识库待优化 + 运营洞察 API ==========
@app.route('/api/admin/kb-pending', methods=['GET'])
@login_required
def api_admin_kb_pending():
    """知识库待优化问题列表"""
    if session.get('role') not in ('admin','super_admin','tenant_admin'):
        return jsonify(ok=False, error='权限不足')
    conn = get_db()
    _ensure_tables(conn)
    status = request.args.get('status', 'pending')
    rows = conn.execute(
        "SELECT * FROM kb_pending WHERE status=? ORDER BY id DESC LIMIT 200",
        (status,)
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) FROM kb_pending WHERE status='pending'").fetchone()[0]
    conn.close()
    return jsonify(ok=True, items=[dict(r) for r in rows], pending_total=total)

@app.route('/api/admin/kb-pending/<int:pid>/import', methods=['POST'])
@login_required
def api_admin_kb_pending_import(pid):
    """一键补充入库：将待优化问题写入知识库"""
    if session.get('role') not in ('admin','super_admin','tenant_admin'):
        return jsonify(ok=False, error='权限不足')
    data = request.get_json()
    answer = data.get('answer', '').strip()
    category = data.get('category', 'service').strip()
    if not answer:
        return jsonify(ok=False, error='请填写答案')
    conn = get_db()
    _ensure_tables(conn)
    p = conn.execute("SELECT * FROM kb_pending WHERE id=?", (pid,)).fetchone()
    if not p:
        conn.close()
        return jsonify(ok=False, error='待优化问题不存在')
    # 写入知识库
    conn.execute(
        "INSERT INTO knowledge_base (tenant_id, category, question, answer, keywords) VALUES (?,?,?,?,?)",
        (session['tenant_id'], category, p['question'], answer, p['question'])
    )
    # 标记已入库
    conn.execute("UPDATE kb_pending SET status='imported' WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={'message': '已补充入库'})

@app.route('/api/admin/kb-pending/<int:pid>/dismiss', methods=['POST'])
@login_required
def api_admin_kb_pending_dismiss(pid):
    """忽略待优化问题"""
    if session.get('role') not in ('admin','super_admin','tenant_admin'):
        return jsonify(ok=False, error='权限不足')
    conn = get_db()
    _ensure_tables(conn)
    conn.execute("UPDATE kb_pending SET status='dismissed' WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={'message': '已忽略'})

@app.route('/api/admin/insights', methods=['GET'])
@login_required
def api_admin_insights():
    """运营洞察：高频投诉/建议/未命中问题汇总，形成优化建议"""
    if session.get('role') not in ('admin','super_admin','tenant_admin'):
        return jsonify(ok=False, error='权限不足')
    conn = get_db()
    _ensure_tables(conn)
    # 高频投诉（按分类统计）
    complaints = conn.execute(
        "SELECT COUNT(*) as cnt FROM work_orders WHERE type='投诉建议'"
    ).fetchone()['cnt']
    complaint_categories = conn.execute(
        "SELECT title FROM work_orders WHERE type='投诉建议' ORDER BY id DESC LIMIT 200"
    ).fetchall()
    # 高频未命中问题（kb_pending）
    pending = conn.execute(
        "SELECT question, COUNT(*) as cnt FROM kb_pending WHERE status='pending' GROUP BY question ORDER BY cnt DESC LIMIT 10"
    ).fetchall()
    pending_total = conn.execute("SELECT COUNT(*) FROM kb_pending WHERE status='pending'").fetchone()[0]
    # 低分评价
    low_feedback = conn.execute(
        "SELECT * FROM feedbacks WHERE rating <= 3 ORDER BY id DESC LIMIT 20"
    ).fetchall()
    conn.close()
    # 统计投诉类别频次
    from collections import Counter
    cat_counter = Counter()
    for c in complaint_categories:
        t = c['title'] or ''
        # 标题格式: 投诉 - 级别 - 类别
        parts = t.split(' - ')
        if len(parts) >= 3:
            cat_counter[parts[2]] += 1
        elif len(parts) == 2:
            cat_counter[parts[1]] += 1
    top_complaints = [{'category': k, 'count': v} for k, v in cat_counter.most_common(8)]
    suggestions = []
    if top_complaints:
        top = top_complaints[0]
        suggestions.append(f'高频投诉集中在「{top["category"]}」类（{top["count"]}次），建议优先优化该环节服务')
    if pending_total:
        suggestions.append(f'知识库有 {pending_total} 条未命中问题待补充，建议运营尽快整理入库以提升 AI 应答准确率')
    if low_feedback:
        avg_low = round(sum(f['rating'] for f in low_feedback) / len(low_feedback), 1)
        suggestions.append(f'近期有 {len(low_feedback)} 条低分评价（均分 {avg_low}），建议复盘服务卡点')
    return jsonify(ok=True, data={
        'complaint_total': complaints,
        'top_complaints': top_complaints,
        'pending_total': pending_total,
        'top_pending': [{'question': p['question'], 'count': p['cnt']} for p in pending],
        'low_feedback_count': len(low_feedback),
        'suggestions': suggestions
    })


# ========== 健康检查 ==========
@app.route('/api/health')
def api_health():
    """健康检查：数据库 + AI 服务状态（供监控/告警/故障降级判断）"""
    db_ok = True
    try:
        conn = get_db()
        conn.execute('SELECT 1').fetchone()
        conn.close()
    except Exception:
        db_ok = False
    overall = 'ok' if (db_ok and AI_HEALTH['status'] == 'up') else 'degraded'
    return jsonify(ok=True, data={
        'status': overall,
        'db': 'ok' if db_ok else 'down',
        'ai_status': AI_HEALTH['status'],
        'ai_fail_count': AI_HEALTH['fail_count'],
        'ai_last_fail': AI_HEALTH['last_fail'],
        'ai_last_check': AI_HEALTH['last_check'],
        'time': datetime.now().isoformat(),
    })


# ========== 激励层 API（签到/积分流水/徽章） ==========
@app.route('/api/community/sign-in', methods=['POST'])
def api_community_sign_in():
    """每日签到：连续签到奖励递增，赚成长值/积分"""
    data = request.get_json(force=True, silent=True) or {}
    phone = (data.get('phone') or '').strip()
    if not phone:
        return jsonify(ok=False, error='请提供手机号'), 400
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    conn = get_db()
    _ensure_tables(conn)
    existing = conn.execute('SELECT id FROM sign_in_records WHERE user_phone=? AND sign_date=?', (phone, today)).fetchone()
    if existing:
        conn.close()
        return jsonify(ok=False, error='今天已经签到过啦，明天再来~'), 400
    prev = conn.execute('SELECT consecutive_days FROM sign_in_records WHERE user_phone=? AND sign_date=?', (phone, yesterday)).fetchone()
    consecutive = (prev['consecutive_days'] + 1) if prev else 1
    base = 5
    bonus = 20 if consecutive % 7 == 0 else 0
    award = base + bonus
    conn.execute('INSERT INTO sign_in_records (user_phone, sign_date, consecutive_days, points_awarded) VALUES (?,?,?,?)',
                 (phone, today, consecutive, award))
    conn.commit()
    conn.close()
    result = add_points(phone, award, 'sign_in', ('连续签到%d天' % consecutive) + ('（7天周期奖励）' if bonus else ''))
    return jsonify(ok=True, data={
        'award': award, 'consecutive_days': consecutive,
        'points': result.get('points'), 'level': result.get('level'),
        'level_up': result.get('level_up'), 'new_badges': result.get('new_badges', []),
    })

@app.route('/api/community/sign-status', methods=['GET'])
def api_community_sign_status():
    """签到状态：今日是否已签到 + 连续天数"""
    phone = (request.args.get('phone') or '').strip()
    if not phone:
        return jsonify(ok=False, error='请提供手机号'), 400
    today = datetime.now().strftime('%Y-%m-%d')
    conn = get_db()
    _ensure_tables(conn)
    row = conn.execute('SELECT consecutive_days, points_awarded FROM sign_in_records WHERE user_phone=? AND sign_date=?', (phone, today)).fetchone()
    conn.close()
    if row:
        return jsonify(ok=True, data={'signed_today': True, 'consecutive_days': row['consecutive_days'], 'points_awarded': row['points_awarded']})
    # 今日未签到：返回昨天的连续天数（昨天签过则连续，否则为0）
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    conn = get_db()
    _ensure_tables(conn)
    prev = conn.execute('SELECT consecutive_days FROM sign_in_records WHERE user_phone=? AND sign_date=?', (phone, yesterday)).fetchone()
    conn.close()
    return jsonify(ok=True, data={'signed_today': False, 'consecutive_days': (prev['consecutive_days'] if prev else 0)})

@app.route('/api/community/points/log', methods=['GET'])
def api_community_points_log():
    """积分/成长值流水"""
    phone = (request.args.get('phone') or '').strip()
    if not phone:
        return jsonify(ok=False, error='请提供手机号'), 400
    limit = request.args.get('limit', 50, type=int)
    conn = get_db()
    _ensure_tables(conn)
    rows = conn.execute('SELECT * FROM points_log WHERE user_phone=? ORDER BY id DESC LIMIT ?', (phone, limit)).fetchall()
    conn.close()
    return jsonify(ok=True, data=[dict(r) for r in rows])

@app.route('/api/community/badges', methods=['GET'])
def api_community_badges():
    """徽章墙：全部徽章 + 我的已获状态"""
    phone = (request.args.get('phone') or '').strip()
    conn = get_db()
    _ensure_tables(conn)
    badges = conn.execute('SELECT * FROM badges ORDER BY threshold').fetchall()
    earned = set()
    if phone:
        earned_rows = conn.execute('SELECT badge_code FROM user_badges WHERE user_phone=?', (phone,)).fetchall()
        earned = set(r['badge_code'] for r in earned_rows)
    conn.close()
    items = []
    for b in badges:
        d = dict(b)
        d['earned'] = d['code'] in earned
        items.append(d)
    return jsonify(ok=True, data=items)


# ========== 邻里圈内容层 API（发帖/信息流/话题/点赞/评论） ==========
@app.route('/api/community/post', methods=['POST'])
def api_community_post():
    """发布邻里圈内容：发帖 +10 成长值"""
    data = request.get_json(force=True, silent=True) or {}
    phone = (data.get('phone') or '').strip()
    name = (data.get('name') or '').strip()
    content = (data.get('content') or '').strip()
    topic = (data.get('topic') or '').strip()
    category = (data.get('category') or '').strip()
    images = data.get('images') or []
    if not phone or not content:
        return jsonify(ok=False, error='请填写内容'), 400
    if len(content) > 2000:
        return jsonify(ok=False, error='内容过长，请精简到2000字以内'), 400
    if not name:
        name = '邻里' + phone[-4:]
    img_json = json.dumps(images[:3], ensure_ascii=False) if images else '[]'
    conn = get_db()
    _ensure_tables(conn)
    cur = conn.execute('INSERT INTO community_posts (user_phone, user_name, content, images, topic, category) VALUES (?,?,?,?,?,?)',
                       (phone, name, content, img_json, topic, category))
    pid = cur.lastrowid
    if topic:
        conn.execute('UPDATE community_topics SET post_count = post_count + 1 WHERE title=?', (topic,))
    conn.commit()
    conn.close()
    result = add_points(phone, 10, 'post', '发布邻里圈内容')
    return jsonify(ok=True, data={'post_id': pid, 'points': result.get('points'), 'new_badges': result.get('new_badges', [])})

@app.route('/api/community/feed', methods=['GET'])
def api_community_feed():
    """邻里圈信息流（按时间倒序，可选话题筛选）"""
    phone = (request.args.get('phone') or '').strip()
    topic = (request.args.get('topic') or '').strip()
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    conn = get_db()
    _ensure_tables(conn)
    if topic:
        rows = conn.execute('SELECT * FROM community_posts WHERE status=? AND topic=? ORDER BY id DESC LIMIT ? OFFSET ?',
                            ('active', topic, limit, (page-1)*limit)).fetchall()
    else:
        rows = conn.execute('SELECT * FROM community_posts WHERE status=? ORDER BY id DESC LIMIT ? OFFSET ?',
                            ('active', limit, (page-1)*limit)).fetchall()
    liked = set()
    if phone:
        liked_rows = conn.execute('SELECT post_id FROM community_likes WHERE user_phone=?', (phone,)).fetchall()
        liked = set(r['post_id'] for r in liked_rows)
    conn.close()
    items = []
    for r in rows:
        d = dict(r)
        d['liked_by_me'] = d['id'] in liked
        try:
            d['images'] = json.loads(d.get('images') or '[]')
        except Exception:
            d['images'] = []
        items.append(d)
    return jsonify(ok=True, data=items)

@app.route('/api/community/topics', methods=['GET'])
def api_community_topics():
    """话题列表"""
    conn = get_db()
    _ensure_tables(conn)
    rows = conn.execute('SELECT * FROM community_topics ORDER BY post_count DESC, id').fetchall()
    conn.close()
    return jsonify(ok=True, data=[dict(r) for r in rows])

@app.route('/api/community/like', methods=['POST'])
def api_community_like():
    """点赞/取消点赞：给帖主 +1/-1 成长值"""
    data = request.get_json(force=True, silent=True) or {}
    post_id = data.get('post_id')
    phone = (data.get('phone') or '').strip()
    if not post_id or not phone:
        return jsonify(ok=False, error='参数错误'), 400
    conn = get_db()
    _ensure_tables(conn)
    post = conn.execute('SELECT * FROM community_posts WHERE id=?', (post_id,)).fetchone()
    if not post:
        conn.close()
        return jsonify(ok=False, error='帖子不存在'), 404
    existing = conn.execute('SELECT id FROM community_likes WHERE post_id=? AND user_phone=?', (post_id, phone)).fetchone()
    if existing:
        # 取消点赞
        conn.execute('DELETE FROM community_likes WHERE post_id=? AND user_phone=?', (post_id, phone))
        conn.execute('UPDATE community_posts SET like_count = MAX(0, like_count - 1) WHERE id=?', (post_id,))
        conn.commit()
        conn.close()
        if post['user_phone'] != phone:
            add_points(post['user_phone'], -1, 'unliked', '被取消点赞')
        return jsonify(ok=True, data={'liked': False, 'like_count': max(0, post['like_count'] - 1)})
    else:
        # 点赞
        conn.execute('INSERT INTO community_likes (post_id, user_phone) VALUES (?,?)', (post_id, phone))
        conn.execute('UPDATE community_posts SET like_count = like_count + 1 WHERE id=?', (post_id,))
        conn.commit()
        conn.close()
        if post['user_phone'] != phone:
            add_points(post['user_phone'], 1, 'liked', '内容被点赞')
        return jsonify(ok=True, data={'liked': True, 'like_count': post['like_count'] + 1})

@app.route('/api/community/comment', methods=['POST'])
def api_community_comment():
    """评论：评论者 +2 成长值"""
    data = request.get_json(force=True, silent=True) or {}
    post_id = data.get('post_id')
    phone = (data.get('phone') or '').strip()
    name = (data.get('name') or '').strip()
    content = (data.get('content') or '').strip()
    if not post_id or not phone or not content:
        return jsonify(ok=False, error='请填写评论内容'), 400
    if len(content) > 500:
        return jsonify(ok=False, error='评论过长'), 400
    if not name:
        name = '邻里' + phone[-4:]
    conn = get_db()
    _ensure_tables(conn)
    post = conn.execute('SELECT id FROM community_posts WHERE id=?', (post_id,)).fetchone()
    if not post:
        conn.close()
        return jsonify(ok=False, error='帖子不存在'), 404
    conn.execute('INSERT INTO community_comments (post_id, user_phone, user_name, content) VALUES (?,?,?,?)',
                 (post_id, phone, name, content))
    conn.execute('UPDATE community_posts SET comment_count = comment_count + 1 WHERE id=?', (post_id,))
    conn.commit()
    conn.close()
    add_points(phone, 2, 'comment', '发表评论')
    return jsonify(ok=True, data={'message': '评论成功'})

@app.route('/api/community/post/<int:post_id>', methods=['GET'])
def api_community_post_detail(post_id):
    """帖子详情（含评论）"""
    phone = (request.args.get('phone') or '').strip()
    conn = get_db()
    _ensure_tables(conn)
    post = conn.execute('SELECT * FROM community_posts WHERE id=?', (post_id,)).fetchone()
    if not post:
        conn.close()
        return jsonify(ok=False, error='帖子不存在'), 404
    comments = conn.execute('SELECT * FROM community_comments WHERE post_id=? ORDER BY id', (post_id,)).fetchall()
    liked = False
    if phone:
        liked = conn.execute('SELECT id FROM community_likes WHERE post_id=? AND user_phone=?', (post_id, phone)).fetchone() is not None
    conn.close()
    d = dict(post)
    d['liked_by_me'] = liked
    try:
        d['images'] = json.loads(d.get('images') or '[]')
    except Exception:
        d['images'] = []
    return jsonify(ok=True, data={'post': d, 'comments': [dict(c) for c in comments]})

@app.route('/api/community/my', methods=['GET'])
def api_community_my():
    """我的帖子"""
    phone = (request.args.get('phone') or '').strip()
    if not phone:
        return jsonify(ok=False, error='请提供手机号'), 400
    conn = get_db()
    _ensure_tables(conn)
    rows = conn.execute('SELECT * FROM community_posts WHERE user_phone=? ORDER BY id DESC LIMIT 50', (phone,)).fetchall()
    conn.close()
    items = []
    for r in rows:
        d = dict(r)
        try:
            d['images'] = json.loads(d.get('images') or '[]')
        except Exception:
            d['images'] = []
        items.append(d)
    return jsonify(ok=True, data=items)


# ========== 互动裂变：拼团组队 + 商户发券 ==========
@app.route('/api/group-buy/list', methods=['GET'])
def api_group_buy_list():
    """拼团活动列表（仅进行中）"""
    conn = get_db()
    _ensure_tables(conn)
    rows = conn.execute(
        "SELECT id,shop_name,title,coupon_label,coupon_amount,need_count,expire_at,created_at "
        "FROM group_buys WHERE status='open' ORDER BY id DESC"
    ).fetchall()
    items = []
    for r in rows:
        joined = conn.execute('SELECT COUNT(*) FROM group_buy_members WHERE group_id=?', (r['id'],)).fetchone()[0]
        items.append({
            'id': r['id'], 'shop_name': r['shop_name'], 'title': r['title'],
            'coupon_label': r['coupon_label'], 'coupon_amount': r['coupon_amount'],
            'need_count': r['need_count'], 'joined_count': joined,
            'remain': max(0, r['need_count'] - joined), 'expire_at': r['expire_at'],
        })
    conn.close()
    return jsonify(ok=True, data=items)


@app.route('/api/group-buy/detail', methods=['GET'])
def api_group_buy_detail():
    """拼团详情 + 成员 + 是否已参团"""
    gid = request.args.get('group_id', type=int)
    phone = request.args.get('phone', '').strip()
    if not gid:
        return jsonify(ok=False, error='缺少 group_id')
    conn = get_db()
    _ensure_tables(conn)
    r = conn.execute(
        "SELECT id,shop_name,title,coupon_label,coupon_amount,need_count,expire_at,status "
        "FROM group_buys WHERE id=?", (gid,)
    ).fetchone()
    if not r:
        conn.close()
        return jsonify(ok=False, error='拼团不存在')
    joined = conn.execute('SELECT COUNT(*) FROM group_buy_members WHERE group_id=?', (gid,)).fetchone()[0]
    members = conn.execute(
        "SELECT user_name, joined_at FROM group_buy_members WHERE group_id=? ORDER BY joined_at", (gid,)
    ).fetchall()
    joined_by_me = False
    if phone:
        joined_by_me = conn.execute(
            'SELECT id FROM group_buy_members WHERE group_id=? AND user_phone=?', (gid, phone)
        ).fetchone() is not None
    conn.close()
    return jsonify(ok=True, data={
        'id': r['id'], 'shop_name': r['shop_name'], 'title': r['title'],
        'coupon_label': r['coupon_label'], 'coupon_amount': r['coupon_amount'],
        'need_count': r['need_count'], 'joined_count': joined,
        'remain': max(0, r['need_count'] - joined), 'expire_at': r['expire_at'],
        'status': r['status'], 'joined_by_me': joined_by_me,
        'members': [{'name': m['user_name'] or '邻居', 'time': str(m['joined_at'])[:16]} for m in members],
    })


@app.route('/api/group-buy/join', methods=['POST'])
def api_group_buy_join():
    """参团：满员自动给所有成员发券（写入 coupon_claims）+ 拼团积分奖励"""
    try:
        gid = int(request.json.get('group_id', 0) or 0)
    except (TypeError, ValueError):
        gid = 0
    phone = request.json.get('phone', '').strip()
    name = request.json.get('name', '').strip() or '邻居'
    if not gid or not phone:
        return jsonify(ok=False, error='参数不完整')
    conn = get_db()
    _ensure_tables(conn)
    r = conn.execute(
        "SELECT id,shop_name,title,coupon_label,coupon_amount,need_count,expire_at,status "
        "FROM group_buys WHERE id=?", (gid,)
    ).fetchone()
    if not r:
        conn.close()
        return jsonify(ok=False, error='拼团不存在')
    if r['status'] != 'open':
        conn.close()
        return jsonify(ok=False, error='该拼团已结束')
    # 防重复参团
    if conn.execute('SELECT id FROM group_buy_members WHERE group_id=? AND user_phone=?', (gid, phone)).fetchone():
        conn.close()
        return jsonify(ok=False, error='您已参与该拼团')
    conn.execute(
        "INSERT INTO group_buy_members (group_id,user_phone,user_name) VALUES (?,?,?)",
        (gid, phone, name)
    )
    conn.commit()  # 先提交成员写入，避免与 add_points 的独立连接竞争 SQLite 写锁
    # 拼团积分 +10（走统一入口，内部独立管理连接与提交）
    add_points(phone, 10, 'group_buy', '参与拼团:' + r['title'])
    joined = conn.execute('SELECT COUNT(*) FROM group_buy_members WHERE group_id=?', (gid,)).fetchone()[0]
    full = joined >= r['need_count']
    awarded = []
    if full:
        # 满员：给所有成员发券（写入 coupon_claims，复用 C 端领券+核销链路）
        members = conn.execute('SELECT user_phone FROM group_buy_members WHERE group_id=?', (gid,)).fetchall()
        # 先建一张 offer（拼团专属券），供 coupon_claims 关联
        conn.execute(
            "INSERT INTO offers (shop_name,label,expire,amount,category,color,status) "
            "VALUES (?,?,?,?,'group','#E85D04','active')",
            (r['shop_name'], '【拼团】' + r['coupon_label'], r['expire_at'], r['coupon_amount'])
        )
        offer_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        for m in members:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO coupon_claims (user_phone,offer_id,shop_name,label,amount) VALUES (?,?,?,?,?)",
                    (m['user_phone'], offer_id, r['shop_name'], '【拼团】' + r['coupon_label'], r['coupon_amount'])
                )
            except Exception:
                pass
        conn.execute("UPDATE group_buys SET status='full' WHERE id=?", (gid,))
        awarded.append({'phone': m['user_phone'] for m in members})
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={
        'full': full, 'joined_count': joined, 'need_count': r['need_count'],
        'coupon_label': ('【拼团】' + r['coupon_label']) if full else '',
        'coupon_amount': r['coupon_amount'] if full else 0,
        'message': ('拼团成功！专属券已发放到各位的「我的优惠券」' if full else '参团成功，还差 ' + str(max(0, r['need_count'] - joined)) + ' 人成团')
    })


@app.route('/api/group-buy/my', methods=['GET'])
def api_group_buy_my():
    """我的拼团（我参与的）"""
    phone = request.args.get('phone', '').strip()
    if not phone:
        return jsonify(ok=False, error='缺少 phone')
    conn = get_db()
    _ensure_tables(conn)
    rows = conn.execute(
        "SELECT g.id,g.shop_name,g.title,g.need_count,g.status,COUNT(m.id) as jc "
        "FROM group_buy_members m JOIN group_buys g ON m.group_id=g.id "
        "WHERE m.user_phone=? GROUP BY g.id ORDER BY g.id DESC", (phone,)
    ).fetchall()
    items = [{'id': r['id'], 'shop_name': r['shop_name'], 'title': r['title'],
              'need_count': r['need_count'], 'joined_count': r['jc'], 'status': r['status']} for r in rows]
    conn.close()
    return jsonify(ok=True, data=items)


@app.route('/api/merchant/issue-coupon', methods=['POST'])
def api_merchant_issue_coupon():
    """商户端发券：写入 offers 表（复用 C 端领券 + 核销链路）"""
    shop_id = request.json.get('shop_id', '').strip()
    token = request.json.get('token', '').strip()
    label = request.json.get('label', '').strip()
    try:
        amount = int(request.json.get('amount', 0) or 0)
    except (TypeError, ValueError):
        amount = 0
    expire = request.json.get('expire', '2026-12-31').strip()
    category = request.json.get('category', 'food').strip()
    if not shop_id or not token:
        return jsonify(ok=False, error='商户认证缺失')
    if not label:
        return jsonify(ok=False, error='请填写券说明')
    shop = _merchant_auth(shop_id, token)
    if not shop:
        return jsonify(ok=False, error='商户认证失败')
    conn = get_db()
    _ensure_tables(conn)
    conn.execute(
        "INSERT INTO offers (shop_name,label,expire,amount,category,color,status) VALUES (?,?,?,?,?,?,?)",
        (shop['name'], label, expire, amount, category, '#FF7B2C', 'active')
    )
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={'message': '发券成功，会员可在优惠券专区领取'})


# ========== 兴趣社 · 活动驱动轻组织 ==========
@app.route('/api/interest-clubs', methods=['GET'])
def api_interest_clubs():
    """常驻兴趣社列表（按 club_order 排序），标记当前用户是否已加入。"""
    phone = request.args.get('phone', '').strip()
    conn = get_db()
    _ensure_tables(conn)
    rows = conn.execute(
        "SELECT id,name,tag,cover_emoji,gradient,intro,member_count,status FROM interest_clubs "
        "WHERE status='open' ORDER BY club_order, id"
    ).fetchall()
    joined_ids = set()
    if phone:
        joined_ids = {r['club_id'] for r in conn.execute(
            "SELECT club_id FROM user_club_members WHERE user_phone=?", (phone,)).fetchall()}
    items = []
    for r in rows:
        items.append({
            'id': r['id'], 'name': r['name'], 'tag': r['tag'], 'cover_emoji': r['cover_emoji'],
            'gradient': r['gradient'], 'intro': r['intro'], 'member_count': r['member_count'],
            'joined': r['id'] in joined_ids,
        })
    conn.close()
    return jsonify(ok=True, data=items)


@app.route('/api/interest-club/join', methods=['POST'])
def api_interest_club_join():
    """加入/退出兴趣社（joined=true 加入，false 退出）。"""
    phone = (request.json.get('phone') or '').strip()
    name = (request.json.get('name') or '').strip() or '邻居'
    club_id = int(request.json.get('club_id', 0) or 0)
    joined = bool(request.json.get('joined', True))
    if not phone or not club_id:
        return jsonify(ok=False, error='参数不完整')
    conn = get_db()
    _ensure_tables(conn)
    club = conn.execute("SELECT id FROM interest_clubs WHERE id=? AND status='open'", (club_id,)).fetchone()
    if not club:
        conn.close()
        return jsonify(ok=False, error='兴趣社不存在')
    exists = conn.execute("SELECT id FROM user_club_members WHERE club_id=? AND user_phone=?", (club_id, phone)).fetchone()
    if joined:
        if not exists:
            conn.execute("INSERT INTO user_club_members (club_id,user_phone,user_name) VALUES (?,?,?)", (club_id, phone, name))
            conn.execute("UPDATE interest_clubs SET member_count = member_count + 1 WHERE id=?", (club_id,))
            add_points(phone, 5, 'join_club', '加入兴趣社#' + str(club_id))
    else:
        if exists:
            conn.execute("DELETE FROM user_club_members WHERE club_id=? AND user_phone=?", (club_id, phone))
            conn.execute("UPDATE interest_clubs SET member_count = MAX(0, member_count - 1) WHERE id=?", (club_id,))
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={'joined': joined})


@app.route('/api/club-events', methods=['GET'])
def api_club_events():
    """临时活动群列表（进行中，end_time 未到的活动群）。可按 club_id / tag 过滤。"""
    club_id = request.args.get('club_id', '').strip()
    tag = request.args.get('tag', '').strip()
    phone = request.args.get('phone', '').strip()
    conn = get_db()
    _ensure_tables(conn)
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    sql = ("SELECT e.id,e.club_id,e.title,e.tag,e.detail,e.place,e.meet_time,e.end_time,e.need_count,"
           "e.status,c.name AS club_name,c.cover_emoji,c.gradient "
           "FROM club_events e JOIN interest_clubs c ON e.club_id=c.id "
           "WHERE e.status='open' AND e.end_time >= ?")
    params = [now]
    if club_id:
        sql += " AND e.club_id=?"
        params.append(club_id)
    elif tag:
        sql += " AND e.tag=?"
        params.append(tag)
    sql += " ORDER BY e.meet_time"
    rows = conn.execute(sql, params).fetchall()
    joined_event_ids = set()
    if phone:
        joined_event_ids = {r['event_id'] for r in conn.execute(
            "SELECT event_id FROM club_event_members WHERE user_phone=?", (phone,)).fetchall()}
    items = []
    for r in rows:
        joined = conn.execute("SELECT COUNT(*) FROM club_event_members WHERE event_id=?", (r['id'],)).fetchone()[0]
        items.append({
            'id': r['id'], 'club_id': r['club_id'], 'club_name': r['club_name'], 'cover_emoji': r['cover_emoji'],
            'gradient': r['gradient'], 'title': r['title'], 'tag': r['tag'], 'detail': r['detail'],
            'place': r['place'], 'meet_time': r['meet_time'], 'end_time': r['end_time'],
            'need_count': r['need_count'], 'joined_count': joined, 'remain': max(0, (r['need_count'] or 0) - joined),
            'joined': r['id'] in joined_event_ids,
        })
    conn.close()
    return jsonify(ok=True, data=items)


@app.route('/api/club-event/detail', methods=['GET'])
def api_club_event_detail():
    """活动群详情：成员名单 + 留言接龙 + 是否已入群。"""
    eid = request.args.get('event_id', type=int)
    phone = request.args.get('phone', '').strip()
    if not eid:
        return jsonify(ok=False, error='缺少 event_id')
    conn = get_db()
    _ensure_tables(conn)
    r = conn.execute(
        "SELECT e.id,e.club_id,e.title,e.tag,e.detail,e.place,e.meet_time,e.end_time,e.need_count,e.status,"
        "c.name AS club_name,c.cover_emoji,c.gradient "
        "FROM club_events e JOIN interest_clubs c ON e.club_id=c.id WHERE e.id=?",
        (eid,)
    ).fetchone()
    if not r:
        conn.close()
        return jsonify(ok=False, error='活动群不存在')
    members = conn.execute(
        "SELECT user_name,joined_at FROM club_event_members WHERE event_id=? ORDER BY joined_at", (eid,)
    ).fetchall()
    msgs = conn.execute(
        "SELECT user_name,content,created_at FROM club_event_messages WHERE event_id=? ORDER BY id", (eid,)
    ).fetchall()
    joined_by_me = False
    if phone:
        joined_by_me = conn.execute(
            "SELECT id FROM club_event_members WHERE event_id=? AND user_phone=?", (eid, phone)
        ).fetchone() is not None
    conn.close()
    return jsonify(ok=True, data={
        'id': r['id'], 'club_id': r['club_id'], 'club_name': r['club_name'], 'cover_emoji': r['cover_emoji'],
        'gradient': r['gradient'], 'title': r['title'], 'tag': r['tag'], 'detail': r['detail'],
        'place': r['place'], 'meet_time': r['meet_time'], 'end_time': r['end_time'],
        'need_count': r['need_count'], 'status': r['status'],
        'joined_count': len(members), 'remain': max(0, (r['need_count'] or 0) - len(members)),
        'joined_by_me': joined_by_me,
        'members': [{'name': m['user_name'] or '邻居', 'time': str(m['joined_at'])[:16]} for m in members],
        'messages': [{'name': x['user_name'] or '邻居', 'content': x['content'], 'time': str(x['created_at'])[:16]} for x in msgs],
    })


@app.route('/api/club-event/join', methods=['POST'])
def api_club_event_join():
    """入群：加入活动驱动的临时群（幂等），参与积分 +5。"""
    phone = (request.json.get('phone') or '').strip()
    name = (request.json.get('name') or '').strip() or '邻居'
    eid = int(request.json.get('event_id', 0) or 0)
    if not phone or not eid:
        return jsonify(ok=False, error='参数不完整')
    conn = get_db()
    _ensure_tables(conn)
    r = conn.execute("SELECT id,status,end_time,need_count FROM club_events WHERE id=?", (eid,)).fetchone()
    if not r:
        conn.close()
        return jsonify(ok=False, error='活动群不存在')
    if r['status'] != 'open':
        conn.close()
        return jsonify(ok=False, error='该活动群已结束')
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    if r['end_time'] and r['end_time'] < now:
        conn.execute("UPDATE club_events SET status='closed' WHERE id=?", (eid,))
        conn.commit()
        conn.close()
        return jsonify(ok=False, error='活动已结束，群已自动散')
    if conn.execute("SELECT id FROM club_event_members WHERE event_id=? AND user_phone=?", (eid, phone)).fetchone():
        conn.close()
        return jsonify(ok=False, error='您已在该活动群')
    conn.execute("INSERT INTO club_event_members (event_id,user_phone,user_name) VALUES (?,?,?)", (eid, phone, name))
    conn.commit()
    add_points(phone, 5, 'join_club_event', '加入活动群#' + str(eid))
    joined = conn.execute("SELECT COUNT(*) FROM club_event_members WHERE event_id=?", (eid,)).fetchone()[0]
    conn.close()
    return jsonify(ok=True, data={
        'joined_count': joined, 'remain': max(0, (r['need_count'] or 0) - joined),
        'message': '入群成功！活动当天来集合点签到即可'
    })


@app.route('/api/club-event/message', methods=['POST'])
def api_club_event_message():
    """群内留言接龙（非实时），留言积分 +2。"""
    phone = (request.json.get('phone') or '').strip()
    name = (request.json.get('name') or '').strip() or '邻居'
    eid = int(request.json.get('event_id', 0) or 0)
    content = (request.json.get('content') or '').strip()
    if not phone or not eid or not content:
        return jsonify(ok=False, error='参数不完整')
    conn = get_db()
    _ensure_tables(conn)
    r = conn.execute("SELECT id,status FROM club_events WHERE id=?", (eid,)).fetchone()
    if not r:
        conn.close()
        return jsonify(ok=False, error='活动群不存在')
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    if r['status'] != 'open' or (r and conn.execute("SELECT end_time FROM club_events WHERE id=?", (eid,)).fetchone()[0] < now):
        conn.close()
        return jsonify(ok=False, error='活动群已结束，无法留言')
    # 仅群成员可留言
    if not conn.execute("SELECT id FROM club_event_members WHERE event_id=? AND user_phone=?", (eid, phone)).fetchone():
        conn.close()
        return jsonify(ok=False, error='请先加入该活动群再留言')
    conn.execute("INSERT INTO club_event_messages (event_id,user_phone,user_name,content) VALUES (?,?,?,?)",
                 (eid, phone, name, content[:300]))
    conn.commit()
    add_points(phone, 2, 'club_event_msg', '活动群留言#' + str(eid))
    conn.close()
    return jsonify(ok=True, data={'message': '留言已发送'})


@app.route('/api/club-event/my', methods=['GET'])
def api_club_event_my():
    """我的活动群 + 我的兴趣社。"""
    phone = request.args.get('phone', '').strip()
    if not phone:
        return jsonify(ok=False, error='缺少 phone')
    conn = get_db()
    _ensure_tables(conn)
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    events = conn.execute(
        "SELECT e.id,e.title,e.tag,e.meet_time,e.place,e.status,c.name AS club_name,c.cover_emoji "
        "FROM club_event_members m JOIN club_events e ON m.event_id=e.id "
        "JOIN interest_clubs c ON e.club_id=c.id WHERE m.user_phone=? AND e.end_time>=? "
        "ORDER BY e.meet_time", (phone, now)
    ).fetchall()
    clubs = conn.execute(
        "SELECT c.id,c.name,c.tag,c.cover_emoji,c.intro FROM user_club_members m "
        "JOIN interest_clubs c ON m.club_id=c.id WHERE m.user_phone=? ORDER BY c.club_order", (phone,)
    ).fetchall()
    conn.close()
    return jsonify(ok=True, data={
        'events': [{'id': e['id'], 'title': e['title'], 'tag': e['tag'], 'club_name': e['club_name'],
                    'cover_emoji': e['cover_emoji'], 'meet_time': e['meet_time'], 'place': e['place'],
                    'status': e['status']} for e in events],
        'clubs': [{'id': c['id'], 'name': c['name'], 'tag': c['tag'], 'cover_emoji': c['cover_emoji'],
                   'intro': c['intro']} for c in clubs],
    })


# ========== robots.txt ==========
def robots_txt():
    return app.response_class(
        'User-agent: *\nDisallow: /api/\nDisallow: /admin\nDisallow: /manage\n',
        mimetype='text/plain'
    )


# === DIAG_ROUTE ===
@app.route('/api/__diag')
def _diag_route():
    rs = [str(r) for r in app.url_map.iter_rules()]
    return jsonify({
        'count': len(rs),
        'has_activities': '/api/activities' in rs,
        'has_offers': '/api/offers' in rs,
        'file': os.path.abspath(__file__),
    })


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print('[OK] Dajudali V1.0: http://localhost:8765')
    try:
        from pyngrok import ngrok
        tunnel = ngrok.connect(8765, 'http')
        print('[Tunnel] ' + tunnel.public_url)
    except Exception as e:
        print('[Tunnel] ngrok unavailable: ' + str(e))
    app.run(host='0.0.0.0', port=8765, debug=False)

