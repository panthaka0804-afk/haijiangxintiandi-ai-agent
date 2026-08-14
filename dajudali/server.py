# -*- coding: utf-8 -*-
"""海江新天地系统 - 社区商业AI客服"""
import os, sys, json, sqlite3, hashlib, secrets, re, time, io, base64, subprocess, tempfile, random, traceback, logging as _logging
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

# 常驻错误日志（替换临时 /tmp/srv500.log 调试手段）：结构化落盘，后续可一键接 Sentry
os.makedirs(os.path.join(HERE, 'logs'), exist_ok=True)
_logging.basicConfig(filename=os.path.join(HERE, 'logs', 'error.log'), level=_logging.ERROR,
                     format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger = _logging.getLogger('dajudali')

@app.errorhandler(500)
def _handle_500(e):
    logger.error('500 %s %s\n%s', request.method, request.path, traceback.format_exc())
    return jsonify(ok=False, error='服务器内部错误'), 500

# 看板聚合缓存（单租户；gunicorn 多 worker 下为 per-worker 缓存，仍显著降 DB 压力）
_DASHBOARD_CACHE = {'data': None, 'ts': 0.0, 'ttl': 300}

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
        conn.execute('PRAGMA busy_timeout=30000')
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
    resp = _do_chat(tid, uid, user_input)
    _persist_chat_if_ok(tid, uid, user_input, resp)
    return resp

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
    resp = _do_chat(1, sid, user_input, large_font=large_font)
    _persist_chat_if_ok(1, sid, user_input, resp)
    return resp

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

@app.route('/api/member/coupon/redeem', methods=['POST'])
def api_member_coupon_redeem():
    """会员核销已领取的优惠券（真实数据链路：写入 redeemed/redeem_amount/redeem_at）"""
    data = request.get_json()
    phone = (data.get('phone') or '').strip()
    claim_id = data.get('claim_id') or data.get('id')
    amount = float(data.get('amount') or 0)
    if not phone or not claim_id:
        return jsonify(ok=False, error='参数不完整')
    conn = get_db()
    _ensure_tables(conn)
    row = conn.execute('SELECT * FROM coupon_claims WHERE id=? AND user_phone=?', (claim_id, phone)).fetchone()
    if not row:
        conn.close()
        return jsonify(ok=False, error='未找到该券或不属于当前会员')
    if row['redeemed']:
        conn.close()
        return jsonify(ok=False, error='该券已核销')
    amt = amount if amount > 0 else (row['amount'] or 0)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute('UPDATE coupon_claims SET redeemed=1, redeem_amount=?, redeem_at=? WHERE id=?',
                 (amt, now, claim_id))
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={'message': '核销成功', 'redeem_amount': amt})

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
            'claim_id': c['id'], 'offer_id': c['offer_id'], 'shop_name': c['shop_name'],
            'label': c['label'], 'amount': c['amount'],
            'redeemed': c['redeemed'], 'redeem_amount': c['redeem_amount'],
            'time': str(c['claimed_at'])[:10], 'type': 'claim'
        })
    for r in orders:
        try:
            d = json.loads(r[0])
            coupons.append({'code': d.get('code','?'), 'item': d.get('item','?'), 'time': str(r[1])[:10], 'type': 'redeem'})
        except:
            pass
    return jsonify(ok=True, coupons=coupons, claimed_ids=list(claimed_ids))


@app.route('/api/member/messages', methods=['POST'])
def api_member_messages():
    """会员站内消息（当前为全员广播消息，user_id=0）"""
    phone = (request.json or {}).get('phone', '').strip()
    if not phone:
        return jsonify(ok=False, error='请输入手机号')
    conn = get_db()
    _ensure_tables(conn)
    rows = conn.execute("SELECT id,type,title,body,ref_type,ref_id,created_at,read FROM messages WHERE user_id=0 ORDER BY id DESC LIMIT 50").fetchall()
    unread = conn.execute("SELECT COUNT(*) FROM messages WHERE user_id=0 AND read=0").fetchone()[0]
    conn.close()
    return jsonify(ok=True, messages=[dict(r) for r in rows], unread=unread)


@app.route('/api/member/message/read', methods=['POST'])
def api_member_message_read():
    """标记消息已读（id=all 或省略则全部已读）"""
    data = request.get_json() or {}
    mid = data.get('id')
    conn = get_db()
    _ensure_tables(conn)
    if mid == 'all' or mid is None:
        conn.execute("UPDATE messages SET read=1 WHERE user_id=0")
    else:
        conn.execute("UPDATE messages SET read=1 WHERE id=? AND user_id=0", (mid,))
    conn.commit()
    conn.close()
    return jsonify(ok=True)


# ========== API - 会员专属内容（新品试吃 / 内测名额 / 专属体验） ==========
# 演示用种子数据（内存态，服务重启会重置名额/领取记录；生产可迁 DB）
MEMBER_EXCLUSIVES = [
    {'id': 'taste_zgzy', 'type': '新品试吃', 'title': '朱光玉火锅·秋季新品内测试吃', 'shop': '朱光玉火锅',
     'cover': 'linear-gradient(135deg,#E2574C,#B83227)', 'summary': '新锅底+限定蘸料，试吃席位先到先得',
     'detail': '秋日暖锅内测：牛油番茄双拼锅底、手打虾滑新品，到场即赠限定蘸料瓶。每场限20人，体验后填写问卷再赠50元券。',
     'level_required': '普卡', 'quota_total': 60, 'quota_left': 52, 'deadline': '2026-08-31', 'location': '海江新天地 3F 朱光玉'},
    {'id': 'taste_mstand', 'type': '新品试吃', 'title': 'M Stand×海江限定特调品鉴', 'shop': 'M Stand',
     'cover': 'linear-gradient(135deg,#6B4F3A,#3E2D20)', 'summary': '银卡及以上专享，咖啡×中式茶底限定特调',
     'detail': '仅向银卡及以上会员开放：桂花酒酿冷萃、陈皮美式两款限定特调，配手作茶点。每场限15人，由主理人讲解拼配思路。',
     'level_required': '银卡', 'quota_total': 40, 'quota_left': 33, 'deadline': '2026-09-15', 'location': '海江新天地 1F M Stand'},
    {'id': 'beta_food', 'type': '内测名额', 'title': '海江食集·新店开业内测官', 'shop': '海江食集',
     'cover': 'linear-gradient(135deg,#C4923A,#9A7425)', 'summary': '新档口开业前内测，所有会员可报名',
     'detail': '新入驻档口开业前 3 天邀请会员内测，免费试吃招牌单品并提建议。名额充足，登录即可报名。',
     'level_required': '普卡', 'quota_total': 120, 'quota_left': 98, 'deadline': '2026-09-10', 'location': '海江新天地 B1 海江食集'},
    {'id': 'beta_nelbo', 'type': '内测名额', 'title': '奈尔宝亲子乐园·新设施体验官', 'shop': '奈尔宝',
     'cover': 'linear-gradient(135deg,#4F9CC9,#3A7BA0)', 'summary': '金卡及以上专享，新滑梯/新剧场首发体验',
     'detail': '新扩建区（攀爬网+沉浸剧场）向金卡及以上会员首发体验，每名会员可携 1 名儿童，含专属引导员。每场限25组家庭。',
     'level_required': '金卡', 'quota_total': 25, 'quota_left': 19, 'deadline': '2026-09-20', 'location': '海江新天地 2F 奈尔宝'},
    {'id': 'vip_lounge', 'type': '专属体验', 'title': 'VIP休息室·私享品鉴日', 'shop': '海江新天地',
     'cover': 'linear-gradient(135deg,#9B4A3E,#6E332A)', 'summary': '钻石卡专享，月度私享品鉴+主理人面对面',
     'detail': '钻石卡会员专属：每月一场 VIP 休息室私享品鉴，含精选茶歇、品牌主理人分享、限定伴手礼。每场限15人。',
     'level_required': '钻石卡', 'quota_total': 15, 'quota_left': 11, 'deadline': '2026-09-30', 'location': '海江新天地 L4 VIP休息室'},
    {'id': 'black_gala', 'type': '专属体验', 'title': '黑钻会员·年度私享晚宴', 'shop': '海江新天地',
     'cover': 'linear-gradient(135deg,#6B6E64,#3C3E36)', 'summary': '黑钻卡专属，年度高定晚宴席位',
     'detail': '仅黑钻卡会员：年度私享晚宴，主厨定制菜单、专属管家服务、限量纪念礼。每场限8席，需审核资格。',
     'level_required': '黑钻卡', 'quota_total': 8, 'quota_left': 6, 'deadline': '2026-12-31', 'location': '海江新天地 顶楼宴会厅'},
    {'id': 'md_blindbox', 'type': '会员日', 'title': '周三会员日·专属试吃盲盒', 'shop': '海江新天地',
     'cover': 'linear-gradient(135deg,#C9956C,#A87C48)', 'summary': '所有会员可报名，会员日随机试吃盲盒',
     'detail': '每周三会员日开放报名，随机抽取 3 家商户试吃盲盒（价值约 60 元），名额充足，先到先得。',
     'level_required': '普卡', 'quota_total': 200, 'quota_left': 176, 'deadline': '长期有效', 'location': '海江新天地 各楼层'},
]
EXCLUSIVE_CLAIMS = {}  # key: f'{phone}|{id}' -> {'claimed_at': ...}

LEVEL_RANK = {'普卡': 1, '银卡': 2, '金卡': 3, '铂金卡': 4, '钻石卡': 5, '黑钻卡': 6}

def _member_level(phone):
    conn = get_db()
    row = conn.execute('SELECT membership_level FROM users WHERE phone=?', (phone,)).fetchone()
    conn.close()
    return (row['membership_level'] if row else None) or '普卡'

@app.route('/api/member/exclusives', methods=['POST'])
def api_member_exclusives():
    phone = (request.json or {}).get('phone', '').strip()
    level = _member_level(phone) if phone else None
    items = []
    for it in MEMBER_EXCLUSIVES:
        req_rank = LEVEL_RANK.get(it['level_required'], 1)
        cur_rank = LEVEL_RANK.get(level, 0) if level else 0
        # 登录后校验资格；未登录不锁定（点击报名时再校验）
        eligible = (cur_rank >= req_rank) if level else True
        claimed = bool(phone and EXCLUSIVE_CLAIMS.get(f'{phone}|{it["id"]}'))
        items.append({**it, 'eligible': eligible, 'claimed': claimed})
    return jsonify(ok=True, level=level, items=items)

@app.route('/api/member/exclusive/claim', methods=['POST'])
def api_member_exclusive_claim():
    data = request.get_json(force=True)
    phone = (data.get('phone') or '').strip()
    eid = data.get('id')
    if not phone:
        return jsonify(ok=False, error='请先登录会员')
    if not eid:
        return jsonify(ok=False, error='参数不完整'), 400
    it = next((x for x in MEMBER_EXCLUSIVES if x['id'] == eid), None)
    if not it:
        return jsonify(ok=False, error='专属内容不存在'), 404
    level = _member_level(phone)
    req_rank = LEVEL_RANK.get(it['level_required'], 1)
    cur_rank = LEVEL_RANK.get(level, 0)
    if cur_rank < req_rank:
        return jsonify(ok=False, error=f'需「{it["level_required"]}」及以上会员参与')
    key = f'{phone}|{eid}'
    if EXCLUSIVE_CLAIMS.get(key):
        return jsonify(ok=False, error='您已报名该专属内容')
    if it['quota_left'] <= 0:
        return jsonify(ok=False, error='名额已抢光，下次早点来~')
    it['quota_left'] -= 1
    EXCLUSIVE_CLAIMS[key] = {'claimed_at': datetime.now().strftime('%Y-%m-%d %H:%M')}
    return jsonify(ok=True, item={**it, 'eligible': True, 'claimed': True}, message='报名成功！详情见会员消息')

# ========== API - 会员自动化（沉默召回 / 生日·周年庆专属权益日） ==========
# 打开 App 即检测：3 个月没来的推「回来看看」定向券；生日/周年庆当天发「专属权益日」让他必须来。
# 发放/领取状态落 DB（member_auto_coupons），跨 gunicorn 多 worker 一致且重启不丢。
SILENT_DAYS = 90
AUTO_PREF_CATS = ['美食天地', '亲子乐园', '服饰零售', '数码电器', '健身养生', '咖啡茶饮']
AUTO_COVER = {
    'recall': 'linear-gradient(135deg,#E85D04,#B8430A)',       # 橙：回来看看
    'birthday': 'linear-gradient(135deg,#E8809E,#C95B7E)',      # 粉：生日
    'anniversary': 'linear-gradient(135deg,#C4923A,#9A7425)',  # 金：周年庆
}

def _pref_cat(phone, row_pref):
    """历史消费偏好：有记录用记录，否则按手机号稳定派生，保证每个会员都有定向内容。"""
    if row_pref:
        return row_pref
    p = phone or ''
    h = 0
    for ch in p:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return AUTO_PREF_CATS[h % len(AUTO_PREF_CATS)]

def _is_silent(last_visit):
    """最近一次到店距今 >= 90 天视为沉默会员。"""
    if not last_visit:
        return False
    try:
        lv = datetime.strptime(last_visit, '%Y-%m-%d %H:%M:%S')
    except Exception:
        return False
    return (datetime.now() - lv).days >= SILENT_DAYS

@app.route('/api/member/auto-coupons', methods=['POST'])
def api_member_auto_coupons():
    """打开即检测：返回当前会员适用的自动化定向券（沉默召回 / 生日 / 周年庆）。"""
    phone = (request.json or {}).get('phone', '').strip()
    if not phone:
        return jsonify(ok=True, coupons=[])
    conn = get_db()
    _ensure_tables(conn)
    row = conn.execute(
        "SELECT last_visit, birthday, anniversary, preferred_category FROM users WHERE phone=?",
        (phone,)
    ).fetchone()
    now = datetime.now()
    today_md = now.strftime('%m-%d')
    coupons = []
    if row:
        pref = _pref_cat(phone, row['preferred_category'])
        # 1) 沉默召回：3 个月没来 → 推一张针对历史偏好的「回来看看」定向券（发放一次，领前常驻）
        recall_row = conn.execute(
            "SELECT claimed FROM member_auto_coupons WHERE phone=? AND kind='recall' AND cycle='recall'",
            (phone,)
        ).fetchone()
        if recall_row is None and _is_silent(row['last_visit']):
            conn.execute(
                "INSERT OR IGNORE INTO member_auto_coupons (phone, kind, cycle, claimed) VALUES (?,?,?,0)",
                (phone, 'recall', 'recall')
            )
            conn.commit()
            recall_row = {'claimed': 0}
        if recall_row is not None and not recall_row['claimed']:
            coupons.append({
                'id': 'auto_recall', 'kind': 'recall', 'kind_label': '回来看看',
                'title': f'回来看看·{pref}专属券',
                'reason': f'您已 {SILENT_DAYS} 天没来啦，{pref}为您留了份心意',
                'desc': f'针对您常逛的「{pref}」定制：到店即赠专属好礼 / 满减券一张，限 30 天内使用。',
                'cover': AUTO_COVER['recall'],
                'validity': (now + timedelta(days=30)).strftime('%Y-%m-%d'),
                'pref': pref,
            })
        # 2) 生日专属权益日（仅生日当天）
        if row['birthday'] and row['birthday'][:5] == today_md:
            bcycle = str(now.year)
            bkey = conn.execute(
                "SELECT claimed FROM member_auto_coupons WHERE phone=? AND kind='birthday' AND cycle=?",
                (phone, bcycle)
            ).fetchone()
            if bkey is None:
                conn.execute(
                    "INSERT OR IGNORE INTO member_auto_coupons (phone, kind, cycle, claimed) VALUES (?,?,?,0)",
                    (phone, 'birthday', bcycle)
                )
                conn.commit()
                bkey = {'claimed': 0}
            if not bkey['claimed']:
                coupons.append({
                    'id': 'auto_birthday', 'kind': 'birthday', 'kind_label': '生日',
                    'title': '生日专属权益日',
                    'reason': '生日快乐！今天专属权益只为您开放',
                    'desc': '生日当月到店享：双倍积分 + 专属生日礼 + 指定商户满减券，今天不来就亏啦~',
                    'cover': AUTO_COVER['birthday'],
                    'validity': today_md,
                    'pref': pref,
                })
        # 3) 周年庆专属权益日（仅入会纪念日当天）
        if row['anniversary'] and row['anniversary'][:5] == today_md:
            acycle = str(now.year)
            akey = conn.execute(
                "SELECT claimed FROM member_auto_coupons WHERE phone=? AND kind='anniversary' AND cycle=?",
                (phone, acycle)
            ).fetchone()
            if akey is None:
                conn.execute(
                    "INSERT OR IGNORE INTO member_auto_coupons (phone, kind, cycle, claimed) VALUES (?,?,?,0)",
                    (phone, 'anniversary', acycle)
                )
                conn.commit()
                akey = {'claimed': 0}
            if not akey['claimed']:
                coupons.append({
                    'id': 'auto_anniversary', 'kind': 'anniversary', 'kind_label': '周年庆',
                    'title': '周年庆专属权益日',
                    'reason': '会员周年庆！今天专属权益只为您开放',
                    'desc': '入会纪念日专属：到店领周年礼盒 + 全场 95 折券，今天必须来！',
                    'cover': AUTO_COVER['anniversary'],
                    'validity': today_md,
                    'pref': pref,
                })
        # 打开即更新 last_visit（沉默召回判定依据）；非沉默会员保持活跃状态
        conn.execute("UPDATE users SET last_visit=? WHERE phone=?", (now.strftime('%Y-%m-%d %H:%M:%S'), phone))
        conn.commit()
    conn.close()
    return jsonify(ok=True, coupons=coupons)

@app.route('/api/member/auto-coupon/claim', methods=['POST'])
def api_member_auto_coupon_claim():
    """领取自动化定向券：标记已领并落地到会员券包（coupon_claims）。"""
    data = request.get_json(force=True)
    phone = (data.get('phone') or '').strip()
    cid = data.get('id')
    if not phone:
        return jsonify(ok=False, error='请先登录会员')
    if cid not in ('auto_recall', 'auto_birthday', 'auto_anniversary'):
        return jsonify(ok=False, error='自动券不存在'), 404
    kind_cycle = {
        'auto_recall': ('recall', 'recall'),
        'auto_birthday': ('birthday', str(datetime.now().year)),
        'auto_anniversary': ('anniversary', str(datetime.now().year)),
    }
    kind, cycle = kind_cycle[cid]
    conn = get_db()
    _ensure_tables(conn)
    row = conn.execute(
        "SELECT id, claimed FROM member_auto_coupons WHERE phone=? AND kind=? AND cycle=?",
        (phone, kind, cycle)
    ).fetchone()
    if not row:
        conn.close()
        return jsonify(ok=False, error='该自动券暂不可领取')
    if row['claimed']:
        conn.close()
        return jsonify(ok=False, error='您已领取该自动券')
    conn.execute("UPDATE member_auto_coupons SET claimed=1 WHERE id=?", (row['id'],))
    # 落地券包：offer_id 用合成负值避免与真实券冲突；按年区分可次年再领
    year = datetime.now().year
    offer_id = {'auto_recall': -1, 'auto_birthday': -200 - (year % 100), 'auto_anniversary': -300 - (year % 100)}[cid]
    label_map = {'auto_recall': '回来看看专属券', 'auto_birthday': '生日专属权益日', 'auto_anniversary': '周年庆专属权益日'}
    conn.execute(
        "INSERT OR IGNORE INTO coupon_claims (user_phone, offer_id, shop_name, label, amount) VALUES (?,?,?,?,?)",
        (phone, offer_id, '海江新天地', label_map[cid], 0)
    )
    conn.commit()
    conn.close()
    return jsonify(ok=True, message='已存入您的券包，记得今天来用哦~')

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

# ========== API - 会员互赠 / 人脉引荐（邻里特权） ==========

@app.route('/api/gift/quota', methods=['POST'])
def api_gift_quota():
    """查询当前会员本月可赠折扣权次数 + 我的引荐码 + 待核销券。"""
    phone = (request.json or {}).get('phone', '').strip()
    if not phone:
        return jsonify(ok=False, error='缺少手机号')
    conn = get_db()
    _ensure_tables(conn)
    reset_gift_quota_if_new_month(conn)
    u = conn.execute('SELECT membership_level, gift_quota, temp_level FROM users WHERE phone=?', (phone,)).fetchone()
    if not u:
        conn.close()
        return jsonify(ok=False, error='会员不存在')
    level = u['membership_level'] or '普卡'
    is_high = level in _HIGH_TIERS
    # 我的引荐码（用手机号可逆编码，NB 前缀 + 完整手机号，解码可直接还原引荐人）
    ref_code = 'NB' + phone
    # 待核销的券（我赠出的、unused 的）
    my_cards = conn.execute(
        "SELECT code, from_level, to_phone, status, expire_at, created_at FROM gift_cards WHERE from_phone=? ORDER BY id DESC LIMIT 20",
        (phone,)).fetchall()
    cards = [dict(c) for c in my_cards]
    # 我收到的券（to_phone 为我、unused）
    received = conn.execute(
        "SELECT code, from_level, from_phone, status, expire_at FROM gift_cards WHERE to_phone=? AND status='unused' ORDER BY id DESC LIMIT 5",
        (phone,)).fetchall()
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={
        'level': level,
        'is_high_tier': is_high,
        'gift_quota': (u['gift_quota'] or 0) if is_high else 0,
        'referral_code': ref_code,
        'sent_cards': cards,
        'received_cards': [dict(r) for r in received],
        'gift_card_valid_days': GIFT_CARD_VALID_DAYS,
    })


# ============================ 便民生活：车主权益 / 预约 / 签到 / 会员日 ============================
def _level_of(phone, conn=None):
    own = conn is None
    if own:
        conn = get_db()
    _ensure_tables(conn)
    u = conn.execute('SELECT membership_level, temp_level, temp_level_expire FROM users WHERE phone=?', (phone,)).fetchone()
    if own:
        conn.close()
    if not u:
        return '普卡'
    temp = u['temp_level'] or ''
    exp = u['temp_level_expire'] or ''
    if temp and exp:
        try:
            if datetime.strptime(exp[:10], '%Y-%m-%d') >= datetime.now():
                return temp
        except:
            pass
    return u['membership_level'] or '普卡'


# ---------- 车主权益：月卡 / 充电包 ----------
@app.route('/api/life/cards', methods=['POST'])
def api_life_cards():
    """我的车主权益（含低阶可购档位 + 高阶自动赠送状态）。"""
    phone = (request.json or {}).get('phone', '').strip()
    if not phone:
        return jsonify(ok=False, error='手机号缺失')
    conn = get_db()
    _ensure_tables(conn)
    level = _level_of(phone, conn)
    # 已持有的权益
    owned = conn.execute(
        "SELECT plan_type, status, end_date, auto_granted, granted_level FROM parking_monthly_cards WHERE phone=? AND status='active'",
        (phone,)).fetchall()
    owned_map = {r['plan_type']: dict(r) for r in owned}
    # 低阶可购档位
    plans = []
    monthly_auto = _level_rank(level) >= _level_rank(AUTO_MONTHLY_LEVEL)
    charging_auto = _level_rank(level) >= _level_rank(AUTO_CHARGING_LEVEL)
    plans.append({
        'plan_type': 'monthly', 'plan_name': '停车月卡', 'price': MONTHLY_CARD_PRICE,
        'auto_granted': monthly_auto,
        'owned': owned_map.get('monthly'),
    })
    plans.append({
        'plan_type': 'charging', 'plan_name': '充电桩权益包', 'price': CHARGING_PACK_PRICE,
        'auto_granted': charging_auto,
        'owned': owned_map.get('charging'),
    })
    conn.close()
    return jsonify(ok=True, data={'level': level, 'plans': plans, 'auto_monthly_level': AUTO_MONTHLY_LEVEL, 'auto_charging_level': AUTO_CHARGING_LEVEL})


@app.route('/api/life/cards/subscribe', methods=['POST'])
def api_life_cards_subscribe():
    """付费订阅车主权益（低阶购买；高阶若未自动送也可补购）。"""
    data = request.json or {}
    phone = data.get('phone', '').strip()
    plan_type = data.get('plan_type', '')
    if not phone or plan_type not in ('monthly', 'charging'):
        return jsonify(ok=False, error='参数不完整')
    conn = get_db()
    _ensure_tables(conn)
    user = conn.execute('SELECT id, points FROM users WHERE phone=?', (phone,)).fetchone()
    if not user:
        conn.close()
        return jsonify(ok=False, error='用户不存在，请先注册会员')
    level = _level_of(phone, conn)
    price = MONTHLY_CARD_PRICE if plan_type == 'monthly' else CHARGING_PACK_PRICE
    plan_name = '停车月卡' if plan_type == 'monthly' else '充电桩权益包'
    # 高阶自动赠送的，无需付费（若已赠送则提示）
    auto = (_level_rank(level) >= _level_rank(AUTO_MONTHLY_LEVEL)) if plan_type == 'monthly' else (_level_rank(level) >= _level_rank(AUTO_CHARGING_LEVEL))
    existing = conn.execute("SELECT id FROM parking_monthly_cards WHERE phone=? AND plan_type=? AND status='active'", (phone, plan_type)).fetchone()
    if auto:
        if existing:
            conn.close()
            return jsonify(ok=False, error='您已是%s，权益已自动生效' % AUTO_MONTHLY_LEVEL if plan_type == 'monthly' else '您已是%s，权益已自动生效' % AUTO_CHARGING_LEVEL)
        # 自动赠送：写入 auto_granted 记录（不扣积分）
        end = (datetime.now() + timedelta(days=30 * AUTO_GRANT_MONTHS)).strftime('%Y-%m-%d')
        conn.execute(
            "INSERT INTO parking_monthly_cards (phone, plan_type, plan_name, price, auto_granted, granted_level, status, start_date, end_date) VALUES (?,?,?,?,1,?, 'active',?,?)",
            (phone, plan_type, plan_name, 0, level, datetime.now().strftime('%Y-%m-%d'), end))
        conn.commit()
        conn.close()
        return jsonify(ok=True, data={'auto_granted': True, 'plan_type': plan_type, 'end_date': end, 'message': '权益已自动生效'})
    # 付费购买：扣积分
    if user['points'] < price:
        conn.close()
        return jsonify(ok=False, error='积分不足，需 %d 分' % price)
    add_points(phone, -price, 'buy_card', '%s订阅' % plan_name, conn)
    end = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    conn.execute(
        "INSERT INTO parking_monthly_cards (phone, plan_type, plan_name, price, auto_granted, status, start_date, end_date) VALUES (?,?,?,?,0, 'active',?,?)",
        (phone, plan_type, plan_name, price, datetime.now().strftime('%Y-%m-%d'), end))
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={'auto_granted': False, 'plan_type': plan_type, 'paid': price, 'end_date': end, 'message': '订阅成功'})


# ---------- 母婴室预约 ----------
@app.route('/api/life/nursery/slots', methods=['GET'])
def api_life_nursery_slots():
    return jsonify(ok=True, data={'slots': NURSERY_SLOTS})


@app.route('/api/life/nursery/book', methods=['POST'])
def api_life_nursery_book():
    data = request.json or {}
    phone = data.get('phone', '').strip()
    name = data.get('name', '').strip()
    date = data.get('date', '').strip()
    slot = data.get('slot', '').strip()
    note = data.get('note', '').strip()
    if not phone or not date or not slot:
        return jsonify(ok=False, error='请填写日期与时段')
    conn = get_db()
    _ensure_tables(conn)
    # 同人同日同时段防重复
    dup = conn.execute("SELECT id FROM nursery_bookings WHERE phone=? AND date=? AND slot=? AND status='booked'", (phone, date, slot)).fetchone()
    if dup:
        conn.close()
        return jsonify(ok=False, error='该时段您已预约，请勿重复')
    # 该时段总预约数防超（每时段最多4间）
    cnt = conn.execute("SELECT COUNT(*) FROM nursery_bookings WHERE date=? AND slot=? AND status='booked'", (date, slot)).fetchone()[0]
    if cnt >= 4:
        conn.close()
        return jsonify(ok=False, error='该时段母婴室已满，请换时段')
    conn.execute("INSERT INTO nursery_bookings (phone, name, date, slot, note, status) VALUES (?,?,?,?,?, 'booked')",
                 (phone, name, date, slot, note))
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={'message': '预约成功，凭手机尾号到场使用'})


@app.route('/api/life/nursery/cancel', methods=['POST'])
def api_life_nursery_cancel():
    data = request.json or {}
    phone = data.get('phone', '').strip()
    bid = data.get('id')
    if not phone or not bid:
        return jsonify(ok=False, error='参数缺失')
    conn = get_db()
    _ensure_tables(conn)
    r = conn.execute("UPDATE nursery_bookings SET status='cancelled' WHERE id=? AND phone=? AND status='booked'", (bid, phone))
    conn.commit()
    affected = r.rowcount
    conn.close()
    return jsonify(ok=affected > 0, data={'message': '已取消预约' if affected > 0 else '预约不存在或已处理'})


@app.route('/api/life/nursery/mine', methods=['POST'])
def api_life_nursery_mine():
    phone = (request.json or {}).get('phone', '').strip()
    if not phone:
        return jsonify(ok=False, error='手机号缺失')
    conn = get_db()
    _ensure_tables(conn)
    rows = conn.execute("SELECT * FROM nursery_bookings WHERE phone=? ORDER BY date DESC, slot DESC", (phone,)).fetchall()
    conn.close()
    out = [{'id': r['id'], 'date': r['date'], 'slot': r['slot'], 'note': r['note'], 'status': r['status'], 'mask': r['phone'][-4:]} for r in rows]
    return jsonify(ok=True, data=out)


# ---------- 宠物托管预约 ----------
@app.route('/api/life/pet/slots', methods=['GET'])
def api_life_pet_slots():
    return jsonify(ok=True, data={'slots': PET_SLOTS})


@app.route('/api/life/pet/book', methods=['POST'])
def api_life_pet_book():
    data = request.json or {}
    phone = data.get('phone', '').strip()
    name = data.get('name', '').strip()
    pet_type = data.get('pet_type', '狗').strip() or '狗'
    pet_name = data.get('pet_name', '').strip()
    date = data.get('date', '').strip()
    slot = data.get('slot', '').strip()
    note = data.get('note', '').strip()
    if not phone or not date or not slot:
        return jsonify(ok=False, error='请填写日期与时段')
    conn = get_db()
    _ensure_tables(conn)
    dup = conn.execute("SELECT id FROM pet_boardings WHERE phone=? AND date=? AND slot=? AND status='booked'", (phone, date, slot)).fetchone()
    if dup:
        conn.close()
        return jsonify(ok=False, error='该时段您已有宠物托管预约')
    cnt = conn.execute("SELECT COUNT(*) FROM pet_boardings WHERE date=? AND slot=? AND status='booked'", (date, slot)).fetchone()[0]
    if cnt >= 6:
        conn.close()
        return jsonify(ok=False, error='该时段托管位已满，请换时段')
    conn.execute("INSERT INTO pet_boardings (phone, name, pet_type, pet_name, date, slot, note, status) VALUES (?,?,?,?,?,?,?, 'booked')",
                 (phone, name, pet_type, pet_name, date, slot, note))
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={'message': '托管预约成功，请按时送达宠物'})


@app.route('/api/life/pet/cancel', methods=['POST'])
def api_life_pet_cancel():
    data = request.json or {}
    phone = data.get('phone', '').strip()
    bid = data.get('id')
    if not phone or not bid:
        return jsonify(ok=False, error='参数缺失')
    conn = get_db()
    _ensure_tables(conn)
    r = conn.execute("UPDATE pet_boardings SET status='cancelled' WHERE id=? AND phone=? AND status='booked'", (bid, phone))
    conn.commit()
    affected = r.rowcount
    conn.close()
    return jsonify(ok=affected > 0, data={'message': '已取消托管预约' if affected > 0 else '预约不存在或已处理'})


@app.route('/api/life/pet/mine', methods=['POST'])
def api_life_pet_mine():
    phone = (request.json or {}).get('phone', '').strip()
    if not phone:
        return jsonify(ok=False, error='手机号缺失')
    conn = get_db()
    _ensure_tables(conn)
    rows = conn.execute("SELECT * FROM pet_boardings WHERE phone=? ORDER BY date DESC, slot DESC", (phone,)).fetchall()
    conn.close()
    out = [{'id': r['id'], 'pet_type': r['pet_type'], 'pet_name': r['pet_name'], 'date': r['date'], 'slot': r['slot'], 'note': r['note'], 'status': r['status'], 'mask': r['phone'][-4:]} for r in rows]
    return jsonify(ok=True, data=out)


# ---------- 每日签到抽奖 ----------
@app.route('/api/life/checkin/status', methods=['POST'])
def api_life_checkin_status():
    phone = (request.json or {}).get('phone', '').strip()
    if not phone:
        return jsonify(ok=False, error='手机号缺失')
    today = datetime.now().strftime('%Y-%m-%d')
    conn = get_db()
    _ensure_tables(conn)
    today_row = conn.execute("SELECT * FROM daily_checkins WHERE phone=? AND checkin_date=?", (phone, today)).fetchone()
    # 连续天数（向前数）
    streak = 0
    d = datetime.now()
    while True:
        ds = d.strftime('%Y-%m-%d')
        ex = conn.execute("SELECT id FROM daily_checkins WHERE phone=? AND checkin_date=?", (phone, ds)).fetchone()
        if not ex:
            break
        streak += 1
        d = d - timedelta(days=1)
    total = conn.execute("SELECT COUNT(*) FROM daily_checkins WHERE phone=?", (phone,)).fetchone()[0]
    conn.close()
    return jsonify(ok=True, data={
        'today_checked': bool(today_row),
        'today_points': today_row['points_gained'] if today_row else 0,
        'today_coupon': today_row['coupon_label'] if today_row else '',
        'streak': streak,
        'total': total,
    })


@app.route('/api/life/checkin', methods=['POST'])
def api_life_checkin():
    phone = (request.json or {}).get('phone', '').strip()
    if not phone:
        return jsonify(ok=False, error='手机号缺失')
    today = datetime.now().strftime('%Y-%m-%d')
    conn = get_db()
    _ensure_tables(conn)
    existing = conn.execute("SELECT id FROM daily_checkins WHERE phone=? AND checkin_date=?", (phone, today)).fetchone()
    if existing:
        conn.close()
        return jsonify(ok=False, error='今日已签到，明天再来')
    # 随机积分
    pts = random.randint(CHECKIN_MIN_POINTS, CHECKIN_MAX_POINTS)
    coupon_label = ''
    coupon_offer_id = 0
    won = random.random() < CHECKIN_COUPON_PROB
    if won:
        c = random.choice(CHECKIN_COUPON_POOL)
        coupon_label = c['label']
        coupon_offer_id = c['offer_id']
        # 写入 coupon_claims（负 offer_id 规避 UNIQUE 冲突；前端按 label/amount 展示）
        conn.execute("INSERT OR IGNORE INTO coupon_claims (user_phone, offer_id, shop_name, label, amount) VALUES (?,?,?,?,?)",
                     (phone, coupon_offer_id, c['shop_name'], c['label'], c['amount']))
    add_points(phone, pts, 'daily_checkin', '每日签到', conn)
    conn.execute("INSERT INTO daily_checkins (phone, checkin_date, points_gained, coupon_offer_id, coupon_label) VALUES (?,?,?,?,?)",
                 (phone, today, pts, coupon_offer_id, coupon_label))
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={'points_gained': pts, 'coupon_won': won, 'coupon_label': coupon_label, 'message': '签到成功'})


# ---------- 周三会员日发券 ----------
@app.route('/api/life/member-day/status', methods=['POST'])
def api_life_member_day_status():
    phone = (request.json or {}).get('phone', '').strip()
    if not phone:
        return jsonify(ok=False, error='手机号缺失')
    now = datetime.now()
    week_key = now.strftime('%Y-W%W')
    conn = get_db()
    _ensure_tables(conn)
    row = conn.execute("SELECT * FROM member_day_awards WHERE phone=? AND week_key=?", (phone, week_key)).fetchone()
    # 本周三是否到来（用于前端提示）
    conn.close()
    return jsonify(ok=True, data={
        'week_key': week_key,
        'claimed': bool(row),
        'coupon_label': row['coupon_label'] if row else '',
        'coupon_amount': row['coupon_amount'] if row else 0,
        'coupons': MEMBER_DAY_COUPONS,
    })


@app.route('/api/life/member-day/claim', methods=['POST'])
def api_life_member_day_claim():
    phone = (request.json or {}).get('phone', '').strip()
    if not phone:
        return jsonify(ok=False, error='手机号缺失')
    now = datetime.now()
    weekday = now.weekday()  # 0=周一 ... 2=周三
    if weekday != 2:
        return jsonify(ok=False, error='会员日为每周三，周三再来领取')
    week_key = now.strftime('%Y-W%W')
    conn = get_db()
    _ensure_tables(conn)
    existing = conn.execute("SELECT id FROM member_day_awards WHERE phone=? AND week_key=?", (phone, week_key)).fetchone()
    if existing:
        conn.close()
        return jsonify(ok=False, error='本周会员日券已领取')
    c = random.choice(MEMBER_DAY_COUPONS)
    conn.execute("INSERT OR IGNORE INTO coupon_claims (user_phone, offer_id, shop_name, label, amount) VALUES (?,?,?,?,?)",
                 (phone, c['offer_id'], c['shop_name'], c['label'], c['amount']))
    conn.execute("INSERT INTO member_day_awards (phone, week_key, coupon_offer_id, coupon_label, coupon_amount) VALUES (?,?,?,?,?)",
                 (phone, week_key, c['offer_id'], c['label'], c['amount']))
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={'coupon_label': c['label'], 'coupon_amount': c['amount'], 'shop_name': c['shop_name'], 'message': '会员日专享券已到账'})


def _gen_help_no():
    """生成悬赏编号 HJ + 时间简短串（避免与已有撞号）。"""
    return 'HJ' + datetime.now().strftime('%y%m%d%H%M%S') + uuid.uuid4().hex[:3].upper()


def _help_public_view(row):
    """把 neighbor_helps 行转成前端卡片所需的安全视图（含发/接单人昵称脱敏）。"""
    d = dict(row)
    # 手机号脱敏展示：保留后4位
    def mask(p):
        return ('***' + p[-4:]) if p and len(p) >= 4 else (p or '')
    d['publisher_mask'] = mask(d.get('publisher_phone'))
    d['acceptor_mask'] = mask(d.get('acceptor_phone')) if d.get('acceptor_phone') else ''
    return d


@app.route('/api/neighbor-help/list', methods=['GET'])
def api_neighbor_help_list():
    """悬赏墙：本街区所有可抢的悬赏（open / accepted 都展示，completed 后隐藏）。"""
    try:
        scope = (request.args.get('scope') or 'wall').strip()  # wall=广场 / published=我发的 / accepted=我接的
        phone = (request.args.get('phone') or '').strip()
        conn = get_db()
        _ensure_tables(conn)
        if scope == 'published' and phone:
            rows = conn.execute(
                "SELECT * FROM neighbor_helps WHERE publisher_phone=? ORDER BY id DESC LIMIT 50", (phone,)).fetchall()
        elif scope == 'accepted' and phone:
            rows = conn.execute(
                "SELECT * FROM neighbor_helps WHERE acceptor_phone=? ORDER BY id DESC LIMIT 50", (phone,)).fetchall()
        else:
            # 广场：未取消、未确认完成的都展示（open / accepted / completed）
            rows = conn.execute(
                "SELECT * FROM neighbor_helps WHERE status NOT IN ('cancelled') ORDER BY id DESC LIMIT 80").fetchall()
        conn.close()
        return jsonify(ok=True, data=[_help_public_view(r) for r in rows])
    except Exception as e:
        return jsonify(ok=False, error='加载失败：' + str(e))


@app.route('/api/neighbor-help/publish', methods=['POST'])
def api_neighbor_help_publish():
    """发单：预付冻结赏金（从发单人积分扣除），生成悬赏。"""
    data = request.json or {}
    phone = (data.get('phone') or '').strip()
    title = (data.get('title') or '').strip()
    category = (data.get('category') or '其他').strip()
    reward = int(data.get('reward') or 0)
    detail = (data.get('detail') or '').strip()
    location = (data.get('location') or '').strip()
    expire_at = (data.get('expire_at') or '').strip()
    if not phone or not title:
        return jsonify(ok=False, error='手机号和求助标题必填')
    if category not in HELP_CATEGORIES:
        category = '其他'
    if reward < HELP_MIN_REWARD or reward > HELP_MAX_REWARD:
        return jsonify(ok=False, error=f'赏金需在 {HELP_MIN_REWARD}~{HELP_MAX_REWARD} 积分之间')
    conn = get_db()
    _ensure_tables(conn)
    u = conn.execute('SELECT display_name, points FROM users WHERE phone=?', (phone,)).fetchone()
    if not u:
        conn.close()
        return jsonify(ok=False, error='会员不存在，请先注册')
    if (u['points'] or 0) < reward:
        conn.close()
        return jsonify(ok=False, error=f'积分不足，需 {reward} 分（当前 {u["points"] or 0} 分）')
    name = (u['display_name'] or '邻居').strip() or '邻居'
    help_no = _gen_help_no()
    conn.execute(
        '''INSERT INTO neighbor_helps
           (help_no, publisher_phone, publisher_name, category, title, detail, location, expire_at, reward, status)
           VALUES (?,?,?,?,?,?,?,?,?, 'open')''',
        (help_no, phone, name, category, title, detail, location, expire_at, reward))
    # 预付：冻结赏金（直接从积分扣除，确认完成后再给接单人；取消则退还）
    add_points(phone, -reward, 'neighbor_help_pay', f'发布悬赏#{help_no}预付赏金{reward}', conn)
    conn.commit()
    conn.close()
    return jsonify(ok=True, help_no=help_no, message=f'已发布，预付 {reward} 积分已冻结')


@app.route('/api/neighbor-help/accept', methods=['POST'])
def api_neighbor_help_accept():
    """抢单：附近会员接单，状态 open->accepted。"""
    data = request.json or {}
    phone = (data.get('phone') or '').strip()
    help_no = (data.get('help_no') or '').strip()
    if not phone or not help_no:
        return jsonify(ok=False, error='信息不完整')
    conn = get_db()
    _ensure_tables(conn)
    h = conn.execute('SELECT * FROM neighbor_helps WHERE help_no=?', (help_no,)).fetchone()
    if not h:
        conn.close()
        return jsonify(ok=False, error='悬赏不存在')
    if h['status'] != 'open':
        conn.close()
        return jsonify(ok=False, error='该悬赏已被接单或不可抢')
    if h['publisher_phone'] == phone:
        conn.close()
        return jsonify(ok=False, error='不能抢自己发布的悬赏')
    u = conn.execute('SELECT display_name FROM users WHERE phone=?', (phone,)).fetchone()
    name = (u['display_name'] if u else '邻居') or '邻居'
    conn.execute(
        "UPDATE neighbor_helps SET status='accepted', acceptor_phone=?, acceptor_name=? WHERE help_no=?",
        (phone, name, help_no))
    conn.commit()
    conn.close()
    return jsonify(ok=True, message='接单成功，请尽快联系邻居完成')


@app.route('/api/neighbor-help/complete', methods=['POST'])
def api_neighbor_help_complete():
    """接单人标记完成：accepted->completed（待发单人确认）。"""
    data = request.json or {}
    phone = (data.get('phone') or '').strip()
    help_no = (data.get('help_no') or '').strip()
    if not phone or not help_no:
        return jsonify(ok=False, error='信息不完整')
    conn = get_db()
    _ensure_tables(conn)
    h = conn.execute('SELECT * FROM neighbor_helps WHERE help_no=?', (help_no,)).fetchone()
    if not h:
        conn.close()
        return jsonify(ok=False, error='悬赏不存在')
    if h['status'] != 'accepted':
        conn.close()
        return jsonify(ok=False, error='当前状态不可标记完成')
    if h['acceptor_phone'] != phone:
        conn.close()
        return jsonify(ok=False, error='只有接单人可以标记完成')
    conn.execute("UPDATE neighbor_helps SET status='completed', completed_at=CURRENT_TIMESTAMP WHERE help_no=?", (help_no,))
    conn.commit()
    conn.close()
    return jsonify(ok=True, message='已标记为完成，等待发单人确认')


@app.route('/api/neighbor-help/confirm', methods=['POST'])
def api_neighbor_help_confirm():
    """发单人确认完成：completed->confirmed，结算赏金 + 系统加成给接单人。"""
    data = request.json or {}
    phone = (data.get('phone') or '').strip()
    help_no = (data.get('help_no') or '').strip()
    if not phone or not help_no:
        return jsonify(ok=False, error='信息不完整')
    conn = get_db()
    _ensure_tables(conn)
    h = conn.execute('SELECT * FROM neighbor_helps WHERE help_no=?', (help_no,)).fetchone()
    if not h:
        conn.close()
        return jsonify(ok=False, error='悬赏不存在')
    if h['status'] != 'completed':
        conn.close()
        return jsonify(ok=False, error='只有被标记完成的悬赏才能确认')
    if h['publisher_phone'] != phone:
        conn.close()
        return jsonify(ok=False, error='只有发单人可以确认')
    reward = h['reward'] or 0
    acceptor = h['acceptor_phone']
    # 结算：接单人得预付赏金（发单时已冻结扣除） + 系统额外加成
    total = reward + HELP_SYSTEM_BONUS
    add_points(acceptor, total, 'neighbor_help_done', f'完成悬赏#{help_no}得赏金{reward}+平台补贴{HELP_SYSTEM_BONUS}', conn)
    conn.execute("UPDATE neighbor_helps SET status='confirmed', confirmed_at=CURRENT_TIMESTAMP WHERE help_no=?", (help_no,))
    conn.commit()
    conn.close()
    return jsonify(ok=True, message=f'已确认，接单人获得 {total} 积分（含平台补贴 {HELP_SYSTEM_BONUS}）',
                   awarded=total)


@app.route('/api/neighbor-help/cancel', methods=['POST'])
def api_neighbor_help_cancel():
    """发单人取消未接单的悬赏：open->cancelled，退回预付赏金。"""
    data = request.json or {}
    phone = (data.get('phone') or '').strip()
    help_no = (data.get('help_no') or '').strip()
    if not phone or not help_no:
        return jsonify(ok=False, error='信息不完整')
    conn = get_db()
    _ensure_tables(conn)
    h = conn.execute('SELECT * FROM neighbor_helps WHERE help_no=?', (help_no,)).fetchone()
    if not h:
        conn.close()
        return jsonify(ok=False, error='悬赏不存在')
    if h['status'] != 'open':
        conn.close()
        return jsonify(ok=False, error='悬赏已被接单，无法取消')
    if h['publisher_phone'] != phone:
        conn.close()
        return jsonify(ok=False, error='只有发单人可以取消')
    reward = h['reward'] or 0
    add_points(phone, reward, 'neighbor_help_refund', f'取消悬赏#{help_no}退回预付{reward}', conn)
    conn.execute("UPDATE neighbor_helps SET status='cancelled', cancelled_at=CURRENT_TIMESTAMP WHERE help_no=?", (help_no,))
    conn.commit()
    conn.close()
    return jsonify(ok=True, message=f'已取消，退回 {reward} 积分')


@app.route('/api/gift/send', methods=['POST'])
def api_gift_send():
    """高阶会员赠出一张折扣权券（朋友凭码核销后临时升级）。"""
    data = request.json or {}
    phone = (data.get('phone') or '').strip()
    friend_phone = (data.get('friend_phone') or '').strip()
    friend_name = (data.get('friend_name') or '邻居').strip()
    if not phone or not friend_phone:
        return jsonify(ok=False, error='信息不完整')
    if not re.match(r'^1\d{10}$', friend_phone):
        return jsonify(ok=False, error='朋友手机号格式不正确')
    conn = get_db()
    _ensure_tables(conn)
    reset_gift_quota_if_new_month(conn)
    u = conn.execute('SELECT membership_level, gift_quota FROM users WHERE phone=?', (phone,)).fetchone()
    if not u:
        conn.close()
        return jsonify(ok=False, error='会员不存在')
    level = u['membership_level'] or '普卡'
    if level not in _HIGH_TIERS:
        conn.close()
        return jsonify(ok=False, error='仅金卡/钻石卡会员可赠出折扣权')
    if (u['gift_quota'] or 0) <= 0:
        conn.close()
        return jsonify(ok=False, error='本月赠出次数已用完（每月1次）')
    # 朋友必须是已注册会员（低阶），不允许给自己赠
    fu = conn.execute('SELECT id, membership_level FROM users WHERE phone=?', (friend_phone,)).fetchone()
    if not fu:
        conn.close()
        return jsonify(ok=False, error='朋友尚未注册会员，请先让TA注册')
    if friend_phone == phone:
        conn.close()
        return jsonify(ok=False, error='不能赠给自己')
    code = gen_gift_code()
    expire = (datetime.now() + timedelta(days=GIFT_CARD_VALID_DAYS)).strftime('%Y-%m-%d')
    conn.execute(
        "INSERT INTO gift_cards (code, from_phone, from_level, to_phone, to_name, status, expire_at) VALUES (?,?,?,?,?, 'unused', ?)",
        (code, phone, level, friend_phone, friend_name, expire))
    # 赠卡人得社交勋章分（复用主连接）
    add_points(phone, GIFT_BASE_POINTS, 'gift_send', f'赠折扣权给{friend_name}', conn)
    # 扣配额 + 记录月份
    conn.execute('UPDATE users SET gift_quota=gift_quota-1, gift_month=? WHERE phone=?',
                 (datetime.now().strftime('%Y-%m'), phone))
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={
        'code': code, 'from_level': level, 'expire_at': expire,
        'message': f'已赠出{level}折扣权，朋友核销后首单享{int(_LEVEL_DISCOUNT[level]*100)}折'
    })


@app.route('/api/gift/redeem', methods=['POST'])
def api_gift_redeem():
    """朋友核销折扣权券 → 临时升级为赠卡人卡级（有效期30天，首单后回落）。"""
    data = request.json or {}
    phone = (data.get('phone') or '').strip()
    code = (data.get('code') or '').strip().upper()
    if not phone or not code:
        return jsonify(ok=False, error='信息不完整')
    conn = get_db()
    _ensure_tables(conn)
    card = conn.execute('SELECT * FROM gift_cards WHERE code=?', (code,)).fetchone()
    if not card:
        conn.close()
        return jsonify(ok=False, error='券码不存在')
    if card['status'] != 'unused':
        conn.close()
        return jsonify(ok=False, error='该券已使用或已失效')
    if card['to_phone'] and card['to_phone'] != phone:
        conn.close()
        return jsonify(ok=False, error='该券非赠予您')
    # 过期判断
    try:
        if datetime.strptime(card['expire_at'], '%Y-%m-%d').date() < datetime.now().date():
            conn.execute("UPDATE gift_cards SET status='expired' WHERE code=?", (code,))
            conn.commit(); conn.close()
            return jsonify(ok=False, error='该券已过期')
    except Exception:
        pass
    # 临时升级
    expire = (datetime.now() + timedelta(days=GIFT_CARD_VALID_DAYS)).strftime('%Y-%m-%d')
    conn.execute('UPDATE users SET temp_level=?, temp_level_expire=? WHERE phone=?',
                 (card['from_level'], expire, phone))
    conn.execute("UPDATE gift_cards SET status='used', to_phone=?, to_name=?, used_at=CURRENT_TIMESTAMP WHERE code=?",
                 (phone, card['to_name'] or '邻居', code))
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={
        'temp_level': card['from_level'],
        'expire_at': expire,
        'discount': int(_LEVEL_DISCOUNT.get(card['from_level'], 0.98) * 100),
        'message': f'已升级为{card["from_level"]}，有效期至{expire}，首单消费后恢复本人卡级'
    })


@app.route('/api/referral/bind', methods=['POST'])
def api_referral_bind():
    """朋友注册后填引荐码，建立邻里引荐关系 + 双方各得基础分。"""
    data = request.json or {}
    phone = (data.get('phone') or '').strip()
    name = (data.get('name') or '邻居').strip()
    code = (data.get('code') or '').strip().upper()
    if not phone or not code:
        return jsonify(ok=False, error='信息不完整')
    # 解析引荐人手机号（NB 前缀 + 完整手机号）
    if not code.startswith('NB') or len(code) != 13:
        return jsonify(ok=False, error='引荐码格式不正确')
    referrer_phone = code[2:]
    if not re.match(r'^1\d{10}$', referrer_phone):
        return jsonify(ok=False, error='引荐码无效')
    if referrer_phone == phone:
        return jsonify(ok=False, error='不能填自己的引荐码')
    conn = get_db()
    _ensure_tables(conn)
    ref_u = conn.execute('SELECT id FROM users WHERE phone=?', (referrer_phone,)).fetchone()
    if not ref_u:
        conn.close()
        return jsonify(ok=False, error='引荐人不存在')
    me = conn.execute('SELECT id FROM users WHERE phone=?', (phone,)).fetchone()
    if not me:
        conn.close()
        return jsonify(ok=False, error='请先注册会员')
    # 记录 referrer_phone 到 users（便于展示"我引荐了谁"），并发基础分
    conn.execute('UPDATE users SET referrer_phone=? WHERE phone=?', (referrer_phone, phone))
    res = grant_referral_base(referrer_phone, phone, name, conn)
    conn.commit()
    conn.close()
    return jsonify(ok=True, data={
        'base_awarded': res['base_awarded'],
        'first_order_pending': res['first_order_pending'],
        'base_points': REFER_BASE_POINTS,
        'message': '引荐关系已建立，双方各得%d分；朋友首单再各得%d分' % (REFER_BASE_POINTS, REFER_FIRST_ORDER_POINTS)
    })


@app.route('/api/consumption/record', methods=['POST'])
def api_consumption_record():
    """记录会员消费（邻里消费/活动报名等），触发引荐首单奖励 + 被赠临时卡级回落。"""
    data = request.json or {}
    phone = (data.get('phone') or '').strip()
    amount = float(data.get('amount', 0) or 0)
    source = (data.get('source') or '邻里消费').strip()
    if not phone:
        return jsonify(ok=False, error='缺少手机号')
    conn = get_db()
    _ensure_tables(conn)
    info = mark_consumption(phone, amount, source, conn)
    conn.commit()
    conn.close()
    return jsonify(ok=True, data=info)


# ========== API - Dashboard ==========
@app.route('/api/dashboard')
@admin_required
def api_dashboard():
    # 看板聚合较重，加 5 分钟缓存（单租户；gunicorn 多 worker 下为 per-worker 缓存，仍显著降 DB 压力）
    _now = time.time()
    if _DASHBOARD_CACHE['data'] and (_now - _DASHBOARD_CACHE['ts']) < _DASHBOARD_CACHE['ttl']:
        return jsonify(ok=True, **_DASHBOARD_CACHE['data'])
    tid = session['tenant_id']
    conn = get_db()
    now = datetime.now()
    today = now.strftime('%Y-%m-%d')
    today_start = today + ' 00:00:00'

    # ---- 基础计数 ----
    today_chats = conn.execute("SELECT COUNT(*) FROM conversations WHERE tenant_id=? AND role='user' AND created_at >= date('now','localtime')", (tid,)).fetchone()[0] or 0
    active_members = conn.execute("SELECT COUNT(*) FROM users WHERE tenant_id=? AND role='user'", (tid,)).fetchone()[0] or 0
    total_orders = conn.execute("SELECT COUNT(*) FROM work_orders WHERE tenant_id=?", (tid,)).fetchone()[0] or 0
    pending_orders = conn.execute("SELECT COUNT(*) FROM work_orders WHERE tenant_id=? AND status='pending'", (tid,)).fetchone()[0] or 0
    activity_count = conn.execute("SELECT COUNT(*) FROM activities", ()).fetchone()[0] or 0
    reg_count = conn.execute("SELECT COUNT(*) FROM registrations", ()).fetchone()[0] or 0

    # ---- 真实满意度 / 办结率 / AI 自助率 ----
    sat = conn.execute("SELECT AVG(rating) FROM feedbacks").fetchone()[0]
    satisfaction = round(sat, 1) if sat else '—'
    # 工单办结率：累计口径（全部工单 - 待处理）/ 全部工单
    order_done_rate = round((total_orders - pending_orders) / total_orders * 100, 1) if total_orders else '—'
    # AI 自助解决率：统一用近 7 日窗口，避免"今日恰巧 0 转人工→100%"的脆弱假象
    w7_start = (now - timedelta(days=7)).strftime('%Y-%m-%d') + ' 00:00:00'
    chats_7 = conn.execute("SELECT COUNT(*) FROM conversations WHERE tenant_id=? AND role='user' AND created_at >= ?", (tid, w7_start)).fetchone()[0] or 0
    esc_7 = conn.execute("SELECT COUNT(*) FROM human_chat_messages WHERE work_order_id IS NOT NULL AND created_at >= ?", (w7_start,)).fetchone()[0] or 0
    ai_rate = round((chats_7 - esc_7) / chats_7 * 100, 1) if chats_7 else '—'

    # ---- GMV / 核销 / 积分 ----
    gmv_today = conn.execute("SELECT COALESCE(SUM(amount),0) FROM member_consumptions WHERE created_at >= ?", (today_start,)).fetchone()[0] or 0
    gmv_total = conn.execute("SELECT COALESCE(SUM(amount),0) FROM member_consumptions").fetchone()[0] or 0
    redeemed_today = conn.execute("SELECT COUNT(*) FROM coupon_claims WHERE redeemed=1 AND redeem_at LIKE ?", (today + '%',)).fetchone()[0] or 0
    redeemed_total = conn.execute("SELECT COUNT(*) FROM coupon_claims WHERE redeemed=1").fetchone()[0] or 0
    pi = conn.execute("SELECT COALESCE(SUM(points),0) FROM points_log WHERE points>0 AND created_at >= ?", (today_start,)).fetchone()[0] or 0
    pu = conn.execute("SELECT COALESCE(SUM(points),0) FROM points_log WHERE points<0 AND created_at >= ?", (today_start,)).fetchone()[0] or 0
    points_issued_today = pi or 0
    points_used_today = abs(pu) or 0

    # ---- 会员结构 ----
    new_members_today = conn.execute("SELECT COUNT(*) FROM users WHERE role='user' AND created_at >= ?", (today_start,)).fetchone()[0] or 0
    members = conn.execute("SELECT phone, last_visit, created_at FROM users WHERE role='user'").fetchall()
    silent = 0
    active_30 = 0
    new_30 = 0
    thr30 = now - timedelta(days=30)
    for m in members:
        lv = _parse_dt(m['last_visit']) or _parse_dt(m['created_at'])
        crt = _parse_dt(m['created_at'])
        if lv and (now - lv).days > 90:
            silent += 1
        if lv and lv >= thr30:
            active_30 += 1
        if crt and crt >= thr30:
            new_30 += 1
    silent_members = silent
    silent_ratio = round(silent / len(members) * 100, 1) if members else 0
    member_segments = {'total': len(members), 'new_30': new_30, 'active_30': active_30, 'silent': silent}
    # 演示数据标记：存在 demo 行时返回 demo_active，前端给出"演示数据"提示，避免运营误读暴跌/占比
    demo_rows = conn.execute("SELECT COUNT(*) FROM member_consumptions WHERE demo=1").fetchone()[0] or 0
    demo_active = bool(demo_rows)
    level_rows = conn.execute("SELECT COALESCE(NULLIF(membership_level,''),'普卡') level, COUNT(*) c FROM users WHERE role='user' GROUP BY level").fetchall()
    member_levels = [{'level': r['level'], 'count': r['c']} for r in level_rows]

    shops_total = conn.execute("SELECT COUNT(*) FROM shops").fetchone()[0] or 0
    pending_kb = conn.execute("SELECT COUNT(*) FROM kb_pending WHERE status='pending'").fetchone()[0] or 0
    pending_activities = conn.execute("SELECT COUNT(*) FROM activities WHERE status='pending'").fetchone()[0] or 0

    # ---- 7 日序列（sparkline）----
    dates = [(now - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6, -1, -1)]
    series_chats = [{'date': d, 'value': conn.execute("SELECT COUNT(*) FROM conversations WHERE tenant_id=? AND date(created_at)=?", (tid, d)).fetchone()[0] or 0} for d in dates]
    series_gmv = [{'date': d, 'value': round(conn.execute("SELECT COALESCE(SUM(amount),0) FROM member_consumptions WHERE date(created_at)=?", (d,)).fetchone()[0] or 0, 2)} for d in dates]
    active_map = {}
    for table, col, pcol in [('sign_in_records', 'sign_date', 'user_phone'), ('daily_checkins', 'checkin_date', 'phone'), ('member_consumptions', 'created_at', 'phone')]:
        if table == 'member_consumptions':
            rows = conn.execute("SELECT date(created_at) d, phone FROM member_consumptions").fetchall()
        else:
            rows = conn.execute(f"SELECT {col} d, {pcol} FROM {table}").fetchall()
        for r in rows:
            d0 = (r['d'] or '')[:10]
            if d0:
                active_map.setdefault(d0, set()).add(r[pcol])
    series_active = [{'date': d, 'value': len(active_map.get(d, set()))} for d in dates]

    # ---- 营销转化漏斗（统一口径：全部以"券实例/会员"为度量，保证 发放≥领取≥核销）----
    # 发放 = 已发券张数（coupon_claims 每条 = 1 张已发给会员的券）
    # 领取 = 领券会员数（去重手机号，必然 ≤ 已发券张数）
    # 核销 = 已核销张数（redeemed=1，必然 ≤ 已发券张数）
    issued = conn.execute("SELECT COUNT(*) FROM coupon_claims").fetchone()[0] or 0
    claimed = conn.execute("SELECT COUNT(DISTINCT user_phone) FROM coupon_claims").fetchone()[0] or 0
    redeemed = redeemed_total
    # 领券会员渗透率 = 领券会员 / 已发券张数（≤100）
    claim_rate = round(claimed / issued * 100, 1) if issued else 0
    # 核销率 = 已核销 / 已发券（≤100）
    redeem_rate = round(redeemed / issued * 100, 1) if issued else 0
    funnel = {'issued': issued, 'claimed': claimed, 'redeemed': redeemed, 'claim_rate': claim_rate, 'redeem_rate': redeem_rate}

    # ---- 运营预警 ----
    alerts = []
    if pending_orders > 0:
        alerts.append({'level': 'danger' if pending_orders >= 10 else 'warn', 'text': f'待处理工单 {pending_orders} 单', 'key': 'orders'})
    if pending_kb > 0:
        alerts.append({'level': 'danger' if pending_kb >= 10 else 'warn', 'text': f'知识库待优化 {pending_kb} 条', 'key': 'kb'})
    if silent_ratio >= 40:
        txt = f'沉默会员占比 {silent_ratio}%' + ('（演示样本）' if demo_active else '')
        alerts.append({'level': 'danger', 'text': txt, 'key': 'silent'})
    if issued > 0 and redeem_rate < 5:
        alerts.append({'level': 'warn', 'text': f'券核销率偏低 {redeem_rate}%', 'key': 'redeem'})
    neg_today = conn.execute("SELECT COUNT(*) FROM feedbacks WHERE rating<=3 AND created_at >= ?", (today_start,)).fetchone()[0] or 0
    if neg_today > 0:
        alerts.append({'level': 'warn', 'text': f'今日差评/投诉 {neg_today} 条', 'key': 'neg'})

    # ---- KPI 环比（等比滑动窗口：近 24h vs 前 24h / 近 7d vs 前 7d）----
    # 旧逻辑用"今日片段 vs 昨日/上周全天"导致周环比假暴跌，这里统一等长时间窗。
    def _win_gmv(a, b):
        return conn.execute("SELECT COALESCE(SUM(amount),0) FROM member_consumptions WHERE created_at >= ? AND created_at < ?", (a, b)).fetchone()[0] or 0
    def _win_redeem(a, b):
        return conn.execute("SELECT COUNT(*) FROM coupon_claims WHERE redeemed=1 AND redeem_at >= ? AND redeem_at < ?", (a, b)).fetchone()[0] or 0
    def _win_chats(a, b):
        return conn.execute("SELECT COUNT(*) FROM conversations WHERE role='user' AND created_at >= ? AND created_at < ?", (a, b)).fetchone()[0] or 0
    def _win_pts(a, b):
        return conn.execute("SELECT COALESCE(SUM(points),0) FROM points_log WHERE points>0 AND created_at >= ? AND created_at < ?", (a, b)).fetchone()[0] or 0
    def _chg(cur, base):
        return round((cur - base)/base*100, 1) if base else None
    now_iso = now.strftime('%Y-%m-%d %H:%M:%S')
    d24 = (now - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
    d48 = (now - timedelta(hours=48)).strftime('%Y-%m-%d %H:%M:%S')
    d7 = (now - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    d14 = (now - timedelta(days=14)).strftime('%Y-%m-%d %H:%M:%S')
    gmv_dod = _chg(_win_gmv(d24, now_iso), _win_gmv(d48, d24))
    gmv_wow = _chg(_win_gmv(d7, now_iso), _win_gmv(d14, d7))
    redeemed_dod = _chg(_win_redeem(d24, now_iso), _win_redeem(d48, d24))
    redeemed_wow = _chg(_win_redeem(d7, now_iso), _win_redeem(d14, d7))
    chats_dod = _chg(_win_chats(d24, now_iso), _win_chats(d48, d24))
    chats_wow = _chg(_win_chats(d7, now_iso), _win_chats(d14, d7))
    pts_dod = _chg(_win_pts(d24, now_iso), _win_pts(d48, d24))
    pts_wow = _chg(_win_pts(d7, now_iso), _win_pts(d14, d7))
    this7_gmv = _win_gmv(d7, now_iso); prev7_gmv = _win_gmv(d14, d7)
    this7_chats = _win_chats(d7, now_iso); prev7_chats = _win_chats(d14, d7)
    this7_redeem = _win_redeem(d7, now_iso); prev7_redeem = _win_redeem(d14, d7)
    cands = [('GMV', _chg(this7_gmv, prev7_gmv)), ('咨询量', _chg(this7_chats, prev7_chats)), ('核销量', _chg(this7_redeem, prev7_redeem))]
    pos = sorted([c for c in cands if c[1] is not None and c[1] > 0], key=lambda x: x[1], reverse=True)
    neg = sorted([c for c in cands if c[1] is not None and c[1] < 0], key=lambda x: x[1])
    weekly_headline = ''
    if pos:
        weekly_headline += f"近7日亮点：{pos[0][0]}环比+{pos[0][1]}%"
    if neg:
        weekly_headline += ('；' if weekly_headline else '') + f"最大风险：{neg[0][0]}环比{neg[0][1]}%"
    if not weekly_headline:
        weekly_headline = '近7日各项指标平稳，暂无显著波动'
    if demo_active:
        weekly_headline = '【演示数据】' + weekly_headline

    acts = conn.execute("SELECT id,title,enrolled FROM activities WHERE status='open' ORDER BY enrolled DESC LIMIT 5").fetchall()
    payload = dict(
        today_chats=today_chats, active_members=active_members, total_orders=total_orders,
        pending_orders=pending_orders, activity_count=activity_count, reg_count=reg_count,
        satisfaction=satisfaction, ai_rate=ai_rate, order_done_rate=order_done_rate,
        gmv_today=round(gmv_today, 2), gmv_total=round(gmv_total, 2),
        redeemed_today=redeemed_today, redeemed_total=redeemed_total,
        points_issued_today=points_issued_today, points_used_today=points_used_today,
        new_members_today=new_members_today, silent_members=silent_members, shops_total=shops_total,
        pending_kb=pending_kb, pending_activities=pending_activities, silent_ratio=silent_ratio,
        series_chats=series_chats, series_gmv=series_gmv, series_active=series_active,
        funnel=funnel, member_levels=member_levels, member_segments=member_segments,
        alerts=alerts, hot_activities=[dict(r) for r in acts],
        gmv_dod=gmv_dod, gmv_wow=gmv_wow, redeemed_dod=redeemed_dod, redeemed_wow=redeemed_wow,
        chats_dod=chats_dod, chats_wow=chats_wow, points_dod=pts_dod, points_wow=pts_wow,
        weekly_headline=weekly_headline, demo_active=demo_active
    )
    _DASHBOARD_CACHE['data'] = payload
    _DASHBOARD_CACHE['ts'] = time.time()
    conn.close()
    return jsonify(ok=True, **payload)

# ========== 触达：主动短信扫描 + 发送日志 ==========
@app.route('/api/admin/notify/scan', methods=['POST'])
@admin_required
def api_admin_notify_scan():
    """主动触达扫描：今日生日 / 周年庆 / 沉默会员 → 发短信（去重，当天不重复发）。"""
    conn = get_db()
    _ensure_tables(conn)
    now = datetime.now()
    today_md = now.strftime('%m-%d')
    today = now.strftime('%Y-%m-%d')
    birthday = [r['phone'] for r in conn.execute(
        "SELECT phone FROM users WHERE role='user' AND birthday=?", (today_md,)).fetchall() if r['phone']]
    anniv = [r['phone'] for r in conn.execute(
        "SELECT phone FROM users WHERE role='user' AND anniversary=?", (today_md,)).fetchall() if r['phone']]
    silent = []
    for r in conn.execute("SELECT phone, last_visit, created_at FROM users WHERE role='user'").fetchall():
        if not r['phone']:
            continue
        lv = _parse_dt(r['last_visit']) or _parse_dt(r['created_at'])
        if lv and (now - lv).days >= SILENT_DAYS:
            silent.append(r['phone'])
    conn.close()
    sent = 0
    for phone in birthday:
        if _push_sms(phone, 'birthday', '【海江新天地】生日快乐！今天专属权益日只为您开放：双倍积分+生日礼+指定商户满减券，今天不来就亏啦~', cycle=today):
            sent += 1
    for phone in anniv:
        if _push_sms(phone, 'anniversary', '【海江新天地】会员周年庆！今天专属权益日，到店领周年礼盒+全场95折券，必须来哦~', cycle=today):
            sent += 1
    for phone in silent:
        if _push_sms(phone, 'recall', '【海江新天地】您已很久没来啦，特为您留了张专属券，回来看看吧~', cycle=today):
            sent += 1
    return jsonify(ok=True, birthday=len(birthday), anniversary=len(anniv), silent=len(silent), sent=sent)

@app.route('/api/admin/notify/log', methods=['GET'])
@admin_required
def api_admin_notify_log():
    """最近 50 条触达发送记录。"""
    conn = get_db()
    rows = conn.execute(
        "SELECT phone, kind, content, status, created_at FROM notification_log ORDER BY id DESC LIMIT 50").fetchall()
    conn.close()
    return jsonify(ok=True, logs=[dict(r) for r in rows])


# ========== 演示数据：种入近 90 天仿真历史（让看板/洞察"有故事"，可一键清空） ==========
_SEED_QA = [
    ('停车怎么收费', '停车前2小时免费，之后5元/小时，会员每日赠1张2小时停车券，可在「我的-优惠券」查看。'),
    ('哪里有充电桩', 'B1停车场设有新能源充电桩，扫码即可使用，收费标准见场内指示牌。'),
    ('积分怎么兑换', '进入「会员中心-积分商城」可用积分兑换停车券、餐饮券、电影票等好礼。'),
    ('优惠券在哪领', '首页「每日特惠」和「会员权益」定期发券，关注推送别错过哦。'),
    ('营业时间', '海江新天地营业时间 10:00-22:00，餐饮部分商户延至 22:30。'),
    ('有没有亲子活动', '每周末泡泡米儿童、小荧星艺校有亲子活动，详见「活动」页报名。'),
    ('瑞幸在哪', '瑞幸咖啡位于1区1F，靠近主入口，营业 07:00-22:00。'),
    ('怎么注册会员', '在「我的」页点击开通会员，注册即送500积分，享专属折扣。'),
    ('会员等级', '会员分普卡/银卡/金卡/钻石卡，消费累积升级，等级越高折扣越多。'),
    ('发票怎么开', '消费后可在服务台或「我的-开票」申请电子发票。'),
    ('卫生间在哪', '每层两端均设卫生间，3区另有无障碍卫生间。'),
    ('最近有什么活动', '本周有夏日消费季，满200减30，还有抽奖，详见活动页。'),
    ('停车券怎么用', '出场前在「我的-优惠券」点击停车券核销，或出示券码给岗亭。'),
    ('招商电话', '招商热线 021-8888-0001，欢迎品牌入驻海江新天地。'),
    ('失物招领', '遗失物品请到1F服务台登记，或拨打021-8888-0001。'),
    ('wifi密码', '全场覆盖海江免费WiFi，连接后微信一键登录即可。'),
    ('宠物能带吗', '公共区域可牵绳携带宠物，餐饮店内请依规。'),
    ('生日礼遇', '会员生日月双倍积分+专属生日礼，记得完善生日信息哦。'),
]
_SEED_UNANSWERED = ['你们那有盲人引导吗', '能不能外摆', '会员卡能借人用吗', '周末停车排队久吗', '有母婴室吗']


@app.route('/api/admin/seed-demo', methods=['POST'])
@admin_required
def api_admin_seed_demo():
    """种入近 90 天仿真历史（GMV/核销/咨询/积分/评价），全部标记 demo=1，可一键清空。
    幂等：已种过则提示，force=1 强制重种（先清后种）。"""
    conn = get_db(); _ensure_tables(conn)
    force = (request.get_json() or {}).get('force', 0)
    seeded = conn.execute("SELECT COUNT(*) FROM member_consumptions WHERE demo=1").fetchone()[0] or 0
    if seeded and not force:
        conn.close()
        return jsonify(ok=True, already_seeded=True, count=seeded,
                       msg='演示数据已存在，无需重复种入（可用 force=1 重种或 seed-clear 清空）')
    if force:
        _seed_clear(conn)
    phones = [r[0] for r in conn.execute("SELECT phone FROM users WHERE role='user' AND phone<>''").fetchall()]
    if not phones:
        phones = ['13800000001', '13800000002', '13800000003']
    offers = [r[0] for r in conn.execute("SELECT id FROM offers WHERE status='active'").fetchall()]
    if not offers:
        offers = [r[0] for r in conn.execute("SELECT id FROM offers LIMIT 30").fetchall()]
    shops = [r[0] for r in conn.execute("SELECT id FROM shops LIMIT 40").fetchall()]
    now = datetime.now()
    cnt_cons = cnt_claim = cnt_redeem = cnt_pt = cnt_conv = cnt_fb = 0
    # 预生成全局唯一的 (phone,offer) 对，避免 UNIQUE(user_phone,offer_id) 冲突
    pairs = [(p, o) for p in phones for o in offers]
    random.shuffle(pairs)
    # 90 天里挑 ~45% 的天数发放券，每天 1-4 张
    claim_plan = []
    day_iter = 0
    for _ in range(min(len(pairs), 90 * 3)):
        d = now - timedelta(days=random.randint(0, 89))
        claim_plan.append((pairs.pop() if pairs else (random.choice(phones), random.choice(offers)), d))
    for idx in range(90):
        d = now - timedelta(days=89 - idx)
        day_base = d.strftime('%Y-%m-%d')
        # GMV：5-15 笔消费
        for _ in range(random.randint(5, 15)):
            amt = round(random.uniform(38, 1980), 2)
            ts = day_base + ' ' + f'{random.randint(10,21):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}'
            conn.execute("INSERT INTO member_consumptions (phone,amount,source,awarded_first_order,created_at,demo) VALUES (?,?,?,0,?,1)",
                         (random.choice(phones), amt, random.choice(['餐饮','零售','亲子','娱乐','生活服务']), ts))
            cnt_cons += 1
        # 积分发放：6-18 条
        for _ in range(random.randint(6, 18)):
            ts = day_base + ' ' + f'{random.randint(10,21):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}'
            conn.execute("INSERT INTO points_log (user_phone,action,points,remark,created_at,demo) VALUES (?,?,?,?,?,1)",
                         (random.choice(phones), '消费赠分', random.randint(5, 200), '模拟消费奖励', ts))
            cnt_pt += 1
        # 券领取：当天分配的 claim_plan
        for (p, o), _ in [c for c in claim_plan if c[1].strftime('%Y-%m-%d') == day_base]:
            ts = day_base + ' ' + f'{random.randint(10,21):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}'
            is_redeem = random.random() < 0.45
            red_at = ts if is_redeem else ''
            red_amt = round(random.uniform(5, 50), 2) if is_redeem else 0
            try:
                conn.execute("INSERT INTO coupon_claims (user_phone,offer_id,claimed_at,redeemed,redeem_amount,redeem_at,demo) VALUES (?,?,?,?,?,?,1)",
                             (p, o, ts, 1 if is_redeem else 0, red_amt, red_at))
                cnt_claim += 1
                if is_redeem:
                    cnt_redeem += 1
            except Exception:
                pass
        # 对话：10-28 轮（user+assistant），约 12% 未命中
        for _ in range(random.randint(10, 28)):
            ts = day_base + ' ' + f'{random.randint(10,21):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}'
            uid = random.choice(phones)
            if random.random() < 0.12:
                q = random.choice(_SEED_UNANSWERED)
                a = '哎呀，小江暂时没找到相关信息，你可以换个问法试试~'
                ans = 0
            else:
                q, a = random.choice(_SEED_QA)
                ans = 1
            conn.execute("INSERT INTO conversations (tenant_id,uid,role,content,intent,answered,created_at,demo) VALUES (1,?,?,?,?,?,?,1)",
                         (str(uid), 'user', q[:2000], q[:40], 1, ts))
            conn.execute("INSERT INTO conversations (tenant_id,uid,role,content,intent,answered,created_at,demo) VALUES (1,?,?,?,?,?,?,1)",
                         (str(uid), 'assistant', a[:2000], '', ans, ts))
            cnt_conv += 1
        # 评价：约每 3 天 1-3 条
        if idx % 3 == 0 and shops:
            for _ in range(random.randint(1, 3)):
                ts = day_base + ' ' + f'{random.randint(10,21):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}'
                conn.execute("INSERT INTO feedbacks (user_phone,feedback_type,biz_type,shop_id,rating,feedback_text,created_at,demo) VALUES (?,?,?,?,?,?,?,1)",
                             (random.choice(phones), '商铺评价', 'shop', random.choice(shops), random.randint(3, 5), '体验不错，会继续来。', ts))
                cnt_fb += 1
        conn.commit()
    conn.close()
    return jsonify(ok=True, already_seeded=False,
                   count={'consumptions': cnt_cons, 'coupon_claims': cnt_claim, 'redeemed': cnt_redeem,
                          'points': cnt_pt, 'conversations': cnt_conv, 'feedbacks': cnt_fb},
                   msg='演示数据已种入近90天历史')


def _seed_clear(conn):
    """清空所有 demo=1 的演示数据。"""
    n = {}
    for t in ('member_consumptions', 'coupon_claims', 'points_log', 'conversations', 'feedbacks'):
        try:
            c = conn.execute(f"DELETE FROM {t} WHERE demo=1").rowcount
            n[t] = c
        except Exception:
            n[t] = 0
    conn.commit()
    return n


@app.route('/api/admin/seed-clear', methods=['POST'])
@admin_required
def api_admin_seed_clear():
    """一键清空演示数据（只删 demo=1 行，不影响真实数据）。"""
    conn = get_db(); _ensure_tables(conn)
    n = _seed_clear(conn)
    conn.close()
    return jsonify(ok=True, removed=n, msg='演示数据已清空')


@app.route('/api/admin/recall-list', methods=['GET'])
@admin_required
def api_admin_recall_list():
    """沉默会员召回名单（超 90 天未到店），供智能中心/触达/导出使用。"""
    conn = get_db(); _ensure_tables(conn)
    now = datetime.now()
    rows = conn.execute(
        "SELECT phone, display_name, membership_level, last_visit, created_at FROM users WHERE role='user' AND phone<>''").fetchall()
    out = []
    for m in rows:
        lv = _parse_dt(m['last_visit']) or _parse_dt(m['created_at'])
        d = (now - lv).days if lv else 9999
        if d > 90:
            out.append({'phone': m['phone'], 'name': m['display_name'] or '', 'level': m['membership_level'] or '',
                       'last_visit': (lv.strftime('%Y-%m-%d') if lv else ''), 'silent_days': d})
    conn.close()
    return jsonify(ok=True, total=len(out), list=out)


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

@app.route('/api/referral/qrcode', methods=['GET'])
def api_referral_qrcode():
    """生成我的引荐码二维码（前端展示，朋友扫码可识别码值后手动填码）。"""
    code = request.args.get('code', '').strip()
    if not code:
        return jsonify(ok=False, error='缺少引荐码')
    try:
        import qrcode, io, base64
        from PIL import Image
        qr = qrcode.QRCode(box_size=8, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
        qr.add_data('HJXTD://referral/' + code)
        qr.make(fit=True)
        img = qr.make_image(fill_color='#FF7B2C', back_color='#1C1C1E').convert('RGB').resize((220, 220))
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        b64 = base64.b64encode(buf.getvalue()).decode()
        return jsonify(ok=True, qr='data:image/png;base64,' + b64, code=code)
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
            # 会员折扣（含被赠临时卡级：朋友临时升级后首单同样享高阶折扣）
            discount = effective_discount(phone, conn) if conn else effective_discount(phone)
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

    # 真实付费（pay 且金额>0）记为消费，触发引荐首单奖励 / 被赠临时卡级首单回落
    if pay_method == 'pay' and amount > 0:
        mark_consumption(phone, amount, '活动报名', conn)

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
    c.execute('''INSERT INTO activities (title,"desc",venue,start_date,end_date,gradient,price,points_price,max_people,enrolled,status,offer_ids,budget)
                 VALUES (?,?,?,?,?,?,?,?,?,0,"open",?,?)''',
              (data.get('title',''), data.get('desc',''), data.get('venue',''),
               data.get('start_date',''), data.get('end_date',''), data.get('gradient',''),
               data.get('price',0), data.get('points_price',0), data.get('max_people',100),
               data.get('offer_ids','') or '', data.get('budget',0) or 0))
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
    for f in ['title','desc','venue','start_date','end_date','gradient','price','points_price','max_people','status','offer_ids','budget']:
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
    """获取跨进程初始化文件锁（阻塞直到拿到）。
    用 os.open(O_CREAT|O_RDWR) 创建/打开，避免 open('w') 的截断写权限要求；
    锁文件若由其他用户(如 admin)创建过，www-data 用截断模式会 PermissionError。
    """
    global _init_lock_fd
    if _init_lock_fd is None:
        fd = os.open(_INIT_LOCK_FILE, os.O_CREAT | os.O_RDWR, 0o666)
        try:
            os.chmod(_INIT_LOCK_FILE, 0o666)
        except Exception:
            pass
        _init_lock_fd = os.fdopen(fd, 'r+')
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

def _col_add(conn, table, col, ddl):
    """幂等给表加列（仅当该列不存在时 ALTER）；遇锁库重试，避免冷启动多 worker 竞争时漏建列。"""
    import time as _t
    for _ in range(6):
        try:
            cols = [r[1] for r in conn.execute(f'PRAGMA table_info({table})').fetchall()]
            if col not in cols:
                conn.execute(f'ALTER TABLE {table} ADD COLUMN {col} {ddl}')
            return
        except Exception as e:
            if 'locked' in str(e).lower():
                _t.sleep(0.5)
                continue
            return

def _migrate_schema(conn):
    """幂等 DDL 迁移：无论 _init_done 如何，每个进程都确保表结构到位（防 gunicorn 多 worker 初始化竞态漏建）。"""
    try:
        _col_add(conn, 'users', 'referrer_phone', "TEXT DEFAULT ''")
        _col_add(conn, 'users', 'gift_quota', 'INTEGER DEFAULT 1')
        _col_add(conn, 'users', 'gift_month', "TEXT DEFAULT ''")
        _col_add(conn, 'users', 'temp_level', "TEXT DEFAULT ''")
        _col_add(conn, 'users', 'temp_level_expire', "TEXT DEFAULT ''")
        # 会员自动化：沉默召回 / 生日·周年庆专属权益日
        _col_add(conn, 'users', 'last_visit', "TEXT DEFAULT ''")        # 最近一次打开 App 时间（ISO）
        _col_add(conn, 'users', 'birthday', "TEXT DEFAULT ''")          # MM-DD
        _col_add(conn, 'users', 'anniversary', "TEXT DEFAULT ''")       # MM-DD（入会纪念日）
        _col_add(conn, 'users', 'preferred_category', "TEXT DEFAULT ''") # 历史消费偏好
        # 真实数据链路：评价→商户 / 活动绑券+核销
        _col_add(conn, 'feedbacks', 'shop_id', "TEXT DEFAULT ''")          # 关联真实商户(shops.id)
        _col_add(conn, 'activities', 'offer_ids', "TEXT DEFAULT ''")       # 绑定的券 offer_id 列表(逗号分隔)
        _col_add(conn, 'activities', 'budget', 'REAL DEFAULT 0')           # 活动预算成本(元)
        _col_add(conn, 'coupon_claims', 'redeemed', 'INTEGER DEFAULT 0')   # 是否已核销
        _col_add(conn, 'coupon_claims', 'redeem_amount', 'REAL DEFAULT 0') # 核销金额
        _col_add(conn, 'coupon_claims', 'redeem_at', "TEXT DEFAULT ''")    # 核销时间
        conn.execute('''CREATE TABLE IF NOT EXISTS gift_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL,
            from_phone TEXT NOT NULL, from_level TEXT NOT NULL,
            to_phone TEXT DEFAULT '', to_name TEXT DEFAULT '', status TEXT DEFAULT 'unused',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, expire_at TEXT DEFAULT '', used_at TIMESTAMP DEFAULT NULL)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT, referrer_phone TEXT NOT NULL, referee_phone TEXT NOT NULL,
            referee_name TEXT DEFAULT '', base_awarded INTEGER DEFAULT 0, first_order_awarded INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(referrer_phone, referee_phone))''')
        conn.execute('''CREATE TABLE IF NOT EXISTS member_consumptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, phone TEXT NOT NULL, amount REAL DEFAULT 0,
            source TEXT DEFAULT '', awarded_first_order INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS member_auto_coupons (
            id INTEGER PRIMARY KEY AUTOINCREMENT, phone TEXT NOT NULL, kind TEXT NOT NULL,
            cycle TEXT NOT NULL, claimed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(phone, kind, cycle))''')
        # 上架自动推送：站内消息（user_id=0 表示全员广播）
        _col_add(conn, 'offers', 'target_level', "TEXT DEFAULT ''")  # 定向人群(空=全部)
        conn.execute('''CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER DEFAULT 0,
            type TEXT DEFAULT 'system', title TEXT DEFAULT '', body TEXT DEFAULT '',
            ref_type TEXT DEFAULT '', ref_id INTEGER DEFAULT 0,
            created_at TEXT DEFAULT '', read INTEGER DEFAULT 0)''')
        # 运营洞察：预警/建议处置留痕（一键处置 / 群发定向券）
        conn.execute('''CREATE TABLE IF NOT EXISTS insight_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, action_type TEXT NOT NULL,
            ref_key TEXT DEFAULT '', created_at TEXT DEFAULT '', note TEXT DEFAULT '')''')
        # 触达：短信/通知发送日志（发送状态可追溯）
        conn.execute('''CREATE TABLE IF NOT EXISTS notification_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, phone TEXT DEFAULT '',
            channel TEXT DEFAULT 'sms', kind TEXT DEFAULT '', content TEXT DEFAULT '',
            status TEXT DEFAULT '', provider_resp TEXT DEFAULT '', cycle TEXT DEFAULT '',
            created_at TEXT DEFAULT '')''')
        # 客服对话落库（让"今日咨询/AI自助率"计数真实，且支撑 AI 对话洞察反哺）
        conn.execute('''CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id INTEGER DEFAULT 1,
            uid TEXT DEFAULT '', role TEXT DEFAULT 'user',
            content TEXT DEFAULT '', intent TEXT DEFAULT '',
            answered INTEGER DEFAULT 1, created_at TEXT DEFAULT '')''')
        # 演示数据标记列（seed-demo 写入，可一键清空，不影响真实数据）
        _col_add(conn, 'member_consumptions', 'demo', 'INTEGER DEFAULT 0')
        _col_add(conn, 'coupon_claims', 'demo', 'INTEGER DEFAULT 0')
        _col_add(conn, 'points_log', 'demo', 'INTEGER DEFAULT 0')
        _col_add(conn, 'conversations', 'demo', 'INTEGER DEFAULT 0')
        _col_add(conn, 'feedbacks', 'demo', 'INTEGER DEFAULT 0')
        # 客服对话落库：补齐历史表可能缺失的列（老库 conversations 仅有 id/tenant_id/created_at/demo）
        _col_add(conn, 'conversations', 'uid', "TEXT DEFAULT ''")
        _col_add(conn, 'conversations', 'role', "TEXT DEFAULT 'user'")
        _col_add(conn, 'conversations', 'content', "TEXT DEFAULT ''")
        _col_add(conn, 'conversations', 'intent', "TEXT DEFAULT ''")
        _col_add(conn, 'conversations', 'answered', 'INTEGER DEFAULT 1')
        conn.commit()
    except Exception:
        pass

def _push_message(conn, title, body, mtype='system', user_id=0, ref_type='', ref_id=0):
    """向站内消息表写入一条消息（user_id=0 表示全员广播）。失败静默。"""
    try:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute(
            "INSERT INTO messages (user_id,type,title,body,ref_type,ref_id,created_at,read) VALUES (?,?,?,?,?,?,?,0)",
            (user_id, mtype, title, body, ref_type, ref_id, now))
        conn.commit()
    except Exception:
        pass

# ========== 触达：统一通知服务（provider-agnostic；当前接短信，微信订阅消息待域名后接入） ==========
def _log_notification(phone, channel, kind, content, status, resp='', cycle=''):
    """落通知发送日志，发送状态可追溯。失败静默。"""
    try:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = get_db()
        conn.execute(
            "INSERT INTO notification_log (phone,channel,kind,content,status,provider_resp,cycle,created_at) VALUES (?,?,?,?,?,?,?,?)",
            (phone, channel, kind, content, status, str(resp)[:500], cycle, now))
        conn.commit()
    except Exception:
        pass

def send_sms(phone, content):
    """发短信。无密钥走 sandbox（仅返回 sandbox 状态，落库由调用方负责）；配置真实密钥则真实发送。
    返回 {'status': 'sandbox'|'sent'|'failed', 'resp': ...}。"""
    provider = os.environ.get('SMS_PROVIDER', 'sandbox').strip().lower()
    ak = os.environ.get('SMS_ACCESS_KEY', '').strip()
    sk = os.environ.get('SMS_ACCESS_SECRET', '').strip()
    if provider in ('sandbox', '') or not ak or not sk:
        return {'status': 'sandbox', 'resp': 'no-provider'}
    if provider == 'aliyun':
        return _sms_aliyun(phone, content, ak, sk)
    return {'status': 'sandbox', 'resp': 'unsupported-provider:' + provider}

def _sms_aliyun(phone, content, ak, sk):
    """阿里云短信 SendSms；TemplateParam 传 {"content": 文案}，需配置 SMS_TPL_GENERAL。
    任何异常均回退 sandbox，保证触达管道不中断。"""
    try:
        from urllib.parse import urlencode, quote
        import hmac, hashlib as _hl
        tpl = os.environ.get('SMS_TPL_GENERAL', '').strip()
        sign = os.environ.get('SMS_SIGN', '海江新天地')
        if not tpl:
            return {'status': 'sandbox', 'resp': 'no-template'}
        ts = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        params = {
            'AccessKeyId': ak, 'Action': 'SendSms', 'Format': 'JSON',
            'PhoneNumbers': phone, 'RegionId': 'cn-hangzhou', 'SignName': sign,
            'TemplateCode': tpl, 'TemplateParam': json.dumps({'content': content}, ensure_ascii=False),
            'Timestamp': ts, 'Version': '2017-05-25', 'SignatureMethod': 'HMAC-SHA1',
            'SignatureNonce': secrets.token_hex(16), 'SignatureVersion': '1.0',
        }
        keys = sorted(params.keys())
        canon = '&'.join([quote(k, safe='') + '=' + quote(str(params[k]), safe='') for k in keys])
        str_to_sign = 'GET&' + quote('/', safe='') + '&' + quote(canon, safe='')
        sig = base64.b64encode(_hl.hmac.new((sk + '&').encode('utf-8'), str_to_sign.encode('utf-8'), _hl.sha1).digest()).decode()
        params['Signature'] = sig
        url = 'https://dysmsapi.aliyuncs.com/?' + urlencode(params)
        r = _sp.run(['curl', '-s', '--max-time', '8', url], capture_output=True, text=True, timeout=12)
        return {'status': 'sent', 'resp': r.stdout[:200]}
    except Exception as e:
        logger.error('sms_aliyun fail %s: %s', phone, e)
        return {'status': 'sandbox', 'resp': 'fallback:' + str(e)[:200]}

def _push_sms(phone, kind, content, cycle=''):
    """对单个会员发短信并落库（带去重：同 phone+kind+cycle 已发则跳过）。返回是否发送。"""
    try:
        if cycle:
            ex = get_db().execute(
                "SELECT id FROM notification_log WHERE phone=? AND kind=? AND cycle=? AND status IN ('sent','sandbox')",
                (phone, kind, cycle)).fetchone()
            if ex:
                return False
    except Exception:
        pass
    res = send_sms(phone, content)
    _log_notification(phone, 'sms', kind, content, res.get('status', 'sandbox'), res.get('resp', ''), cycle)
    return True

def _persist_conversation(tid, uid, user_msg, ai_reply):
    """把一轮客服对话落库到 conversations 表（user + assistant 两条）。
    失败静默；AI 未命中(含降级/无答案特征)标记为 answered=0，供知识库缺口分析。"""
    try:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        fail_markers = ('转不过来', '没找到相关信息', '换个问法', '小江暂时没找到', '脑子有点转不过来')
        answered_ai = 0 if any(m in (ai_reply or '')) else 1
        conn = get_db()
        conn.execute(
            "INSERT INTO conversations (tenant_id,uid,role,content,intent,answered,created_at) VALUES (?,?,?,?,?,?,?)",
            (tid, str(uid), 'user', (user_msg or '')[:2000], (user_msg or '')[:40], 1, now))
        conn.execute(
            "INSERT INTO conversations (tenant_id,uid,role,content,intent,answered,created_at) VALUES (?,?,?,?,?,?,?)",
            (tid, str(uid), 'assistant', (ai_reply or '')[:2000], '', answered_ai, now))
        conn.commit()
    except Exception:
        pass

def _persist_chat_if_ok(tid, uid, user_input, resp):
    """从 _do_chat 的响应里取出回复并落库（不影响原响应返回）。"""
    try:
        j = resp.get_json()
        reply = j.get('reply', '')
        if user_input and reply:
            _persist_conversation(tid, uid, user_input, reply)
    except Exception:
        pass

def _ensure_tables(conn):
    """确保数据表存在并填充初始数据。表结构(DDL)并发安全；初始数据写入每个进程只跑一次，避免 gunicorn 多 worker 并发竞争 SQLite 锁。"""
    global _init_done
    # 每进程都先确保表结构到位（防多 worker 初始化竞态漏建），幂等开销极小
    _migrate_schema(conn)
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

    # ========== 会员互赠 / 人脉引荐 扩展字段 ==========
    # users 表加列（幂等：仅当列不存在时 ALTER）
    _col_add(conn, 'users', 'referrer_phone', 'TEXT DEFAULT \'\'')
    _col_add(conn, 'users', 'gift_quota', 'INTEGER DEFAULT 1')        # 本月可赠折扣权次数（高阶会员默认1）
    _col_add(conn, 'users', 'gift_month', 'TEXT DEFAULT \'\'')        # 上次赠送对应的月份(YYYY-MM)，用于每月重置配额
    _col_add(conn, 'users', 'temp_level', 'TEXT DEFAULT \'\'')        # 被赠后临时卡级（如 钻石卡），空=无
    _col_add(conn, 'users', 'temp_level_expire', 'TEXT DEFAULT \'\'') # 临时卡级有效期(YYYY-MM-DD)，过期回落

    # 会员互赠折扣权（券）
    conn.execute('''CREATE TABLE IF NOT EXISTS gift_cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        from_phone TEXT NOT NULL,
        from_level TEXT NOT NULL,
        to_phone TEXT DEFAULT '',
        to_name TEXT DEFAULT '',
        status TEXT DEFAULT 'unused',       -- unused / used / expired
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expire_at TEXT DEFAULT '',
        used_at TIMESTAMP DEFAULT NULL
    )''')
    # 人脉引荐关系
    conn.execute('''CREATE TABLE IF NOT EXISTS referrals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_phone TEXT NOT NULL,        -- 引荐人（老会员）
        referee_phone TEXT NOT NULL,         -- 被引荐人（新会员）
        referee_name TEXT DEFAULT '',
        base_awarded INTEGER DEFAULT 0,      -- 注册基础分是否已发(双方)
        first_order_awarded INTEGER DEFAULT 0, -- 首单奖励分是否已发(双方)
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(referrer_phone, referee_phone)
    )''')
    # 会员消费记录（邻里消费 / 首单触发）
    conn.execute('''CREATE TABLE IF NOT EXISTS member_consumptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT NOT NULL,
        amount REAL DEFAULT 0,
        source TEXT DEFAULT '',              -- 来源备注（如 活动报名/停车/邻里消费）
        awarded_first_order INTEGER DEFAULT 0, -- 本条是否已触发引荐首单奖励
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    # 邻里帮悬赏墙（谁家要搬箱子/代取快递/临时照看，发小忙，附近会员抢单赚积分）
    conn.execute('''CREATE TABLE IF NOT EXISTS neighbor_helps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        help_no TEXT UNIQUE NOT NULL,        -- HJ + 时间戳简短号
        publisher_phone TEXT NOT NULL,       -- 发单人（冻结赏金者）
        publisher_name TEXT DEFAULT '',
        category TEXT DEFAULT '其他',        -- 搬家/代取/照看/问路/其他
        title TEXT NOT NULL,
        detail TEXT DEFAULT '',
        location TEXT DEFAULT '',            -- 楼栋/区域描述
        expire_at TEXT DEFAULT '',           -- 期望完成时间
        reward INTEGER NOT NULL,             -- 赏金积分（发单人预付，完成时结算给接单人）
        status TEXT DEFAULT 'open',          -- open / accepted / completed / confirmed / cancelled
        acceptor_phone TEXT DEFAULT '',      -- 接单人
        acceptor_name TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP DEFAULT NULL,
        confirmed_at TIMESTAMP DEFAULT NULL,
        cancelled_at TIMESTAMP DEFAULT NULL
    )''')

    # ========== 便民生活：车主权益（停车月卡 / 充电桩权益包） ==========
    conn.execute('''CREATE TABLE IF NOT EXISTS parking_monthly_cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT NOT NULL,
        plan_type TEXT NOT NULL,          -- monthly(月卡) / charging(充电包)
        plan_name TEXT NOT NULL,
        price INTEGER NOT NULL,
        auto_granted INTEGER DEFAULT 0,
        granted_level TEXT DEFAULT '',
        status TEXT DEFAULT 'active',
        start_date TEXT DEFAULT '',
        end_date TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS nursery_bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT NOT NULL,
        name TEXT DEFAULT '',
        date TEXT NOT NULL,
        slot TEXT NOT NULL,
        note TEXT DEFAULT '',
        status TEXT DEFAULT 'booked',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS pet_boardings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT NOT NULL,
        name TEXT DEFAULT '',
        pet_type TEXT DEFAULT '狗',
        pet_name TEXT DEFAULT '',
        date TEXT NOT NULL,
        slot TEXT NOT NULL,
        note TEXT DEFAULT '',
        status TEXT DEFAULT 'booked',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS daily_checkins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT NOT NULL,
        checkin_date TEXT NOT NULL,
        points_gained INTEGER DEFAULT 0,
        coupon_offer_id INTEGER DEFAULT 0,
        coupon_label TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(phone, checkin_date)
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS member_day_awards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT NOT NULL,
        week_key TEXT NOT NULL,
        coupon_offer_id INTEGER DEFAULT 0,
        coupon_label TEXT DEFAULT '',
        coupon_amount INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(phone, week_key)
    )''')

    # ── 会员自动化演示种子（幂等，仅首次初始化执行） ──
    today_md = datetime.now().strftime('%m-%d')
    # 历史会员：无 last_visit 的视为久未到店，置为 120 天前，使「沉默召回」可演示
    silent_rows = conn.execute(
        "SELECT phone, preferred_category FROM users WHERE last_visit IS NULL OR last_visit=''"
    ).fetchall()
    for r in silent_rows:
        ph = r['phone']
        if not ph:
            continue
        lv = (datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d %H:%M:%S')
        pref = _pref_cat(ph, r['preferred_category'])
        conn.execute("UPDATE users SET last_visit=?, preferred_category=? WHERE phone=?", (lv, pref, ph))
    # 演示账号：生日/周年庆=今天、久未到店，登录即可一次性看到三种自动化
    demo_phone = '13800138000'
    if not conn.execute("SELECT id FROM users WHERE phone=?", (demo_phone,)).fetchone():
        import hashlib
        pw = hashlib.sha256(('member' + demo_phone).encode()).hexdigest()
        conn.execute(
            "INSERT INTO users (tenant_id, username, password_hash, display_name, role, phone, points, membership_level) VALUES (?,?,?,?,?,?,?,?)",
            (1, 'm' + demo_phone, pw, '演示会员', 'user', demo_phone, 1200, '金卡')
        )
    conn.execute(
        "UPDATE users SET last_visit=?, birthday=?, anniversary=?, preferred_category=? WHERE phone=?",
        ((datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d %H:%M:%S'), today_md, today_md, '美食天地', demo_phone)
    )

    conn.commit()
    _init_done = True
    _release_init_flock()


# ========== 会员互赠 / 人脉引荐 核心逻辑 ==========
# 会员等级 -> 折扣率（被赠朋友临时升级后也走这套）
_LEVEL_DISCOUNT = {'普卡': 0.98, '银卡': 0.95, '金卡': 0.90, '钻石卡': 0.88}
# 高阶卡（可赠折扣权）：金卡 / 钻石卡
_HIGH_TIERS = ('金卡', '钻石卡')
# 互赠 / 引荐 积分配置
GIFT_BASE_POINTS = 20        # 赠出折扣权，赠卡人得（社交勋章感）
REFER_BASE_POINTS = 50       # 朋友注册，双方各得
REFER_FIRST_ORDER_POINTS = 150  # 朋友首单，双方各得
GIFT_CARD_VALID_DAYS = 30    # 折扣权券有效期

# ===== 邻里帮悬赏墙 =====
HELP_CATEGORIES = ['搬家', '代取快递', '临时照看', '问路带路', '其他']
HELP_MIN_REWARD = 10         # 单次悬赏最低赏金
HELP_MAX_REWARD = 500        # 单次悬赏最高赏金
HELP_SYSTEM_BONUS = 20       # 系统额外补贴（接单人完成确认后额外得，平台激励互助）
HELP_EXPIRE_HOURS = 48       # 悬赏墙默认展示有效期（小时），超过则视为过期不可抢

# ========== 便民生活：车主权益 ==========
# 计划档位（低阶付费买 / 高阶自动送）。price 用积分示意抵扣金额。
MONTHLY_CARD_PRICE = 300       # 停车月卡 300 积分/月
CHARGING_PACK_PRICE = 200      # 充电桩权益包 200 积分/月（含每月免费充电额度）
# 高阶会员自动送的等级门槛（两者都要：高阶自动送，低阶付费买）
AUTO_MONTHLY_LEVEL = '金卡'    # 金卡及以上自动送停车月卡
AUTO_CHARGING_LEVEL = '钻石卡' # 钻石卡自动送充电桩权益包
# 自动赠送权益的有效期（月）
AUTO_GRANT_MONTHS = 12

# ========== 便民生活：预约时段 ==========
NURSERY_SLOTS = ['09:00-11:00', '11:00-13:00', '13:00-15:00', '15:00-17:00', '17:00-19:00', '19:00-21:00']
PET_SLOTS = ['09:00-12:00', '12:00-15:00', '15:00-18:00', '18:00-21:00']

# ========== 便民生活：签到抽奖 ==========
CHECKIN_MIN_POINTS = 5
CHECKIN_MAX_POINTS = 50
CHECKIN_COUPON_PROB = 0.15     # 抽中优惠券概率
# 签到可能抽中的券池（用负 offer_id 写入 coupon_claims 规避 UNIQUE 冲突；前端按 label/amount 展示）
CHECKIN_COUPON_POOL = [
    {'offer_id': -101, 'shop_name': '瑞幸咖啡', 'label': '签到专享 9.9 元咖啡券', 'amount': 10},
    {'offer_id': -102, 'shop_name': '霸王茶姬', 'label': '签到专享 指定饮品买一赠一', 'amount': 18},
    {'offer_id': -103, 'shop_name': '小杨生煎', 'label': '签到专享 买单立减 8 元', 'amount': 8},
]

# ========== 便民生活：周三会员日发券 ==========
MEMBER_DAY_COUPONS = [
    {'offer_id': -201, 'shop_name': '星巴克', 'label': '会员日专享 中杯拿铁买一赠一', 'amount': 33},
    {'offer_id': -202, 'shop_name': '海江烘焙坊', 'label': '会员日专享 面包 8 折券', 'amount': 12},
]


def effective_level(phone, conn=None):
    """用户当前有效卡级：优先临时卡级（被赠且在有效期内），否则真实卡级。"""
    own = conn is None
    if own:
        conn = get_db()
    _ensure_tables(conn)
    u = conn.execute('SELECT membership_level, temp_level, temp_level_expire FROM users WHERE phone=?', (phone,)).fetchone()
    if own:
        conn.close()
    if not u:
        return '普卡'
    temp = u['temp_level'] or ''
    exp = u['temp_level_expire'] or ''
    if temp and exp:
        try:
            if datetime.strptime(exp, '%Y-%m-%d').date() >= datetime.now().date():
                return temp
        except Exception:
            pass
    return u['membership_level'] or '普卡'


def effective_discount(phone, conn=None):
    """用户当前有效折扣率（含被赠临时卡级）。"""
    return _LEVEL_DISCOUNT.get(effective_level(phone, conn), 0.98)


def reset_gift_quota_if_new_month(conn):
    """把 gift_quota 按月重置（高阶会员默认1次/月）。返回当前月字符串。"""
    this_month = datetime.now().strftime('%Y-%m')
    rows = conn.execute('SELECT phone, gift_month, membership_level FROM users WHERE gift_month IS NOT NULL AND gift_month != ?', (this_month,)).fetchall()
    for r in rows:
        # 仅高阶会员恢复配额；低阶本就无赠权，配额保持0也无妨
        if (r['membership_level'] or '普卡') in _HIGH_TIERS:
            conn.execute('UPDATE users SET gift_quota=1, gift_month=? WHERE phone=?', (this_month, r['phone']))
        else:
            conn.execute('UPDATE users SET gift_month=? WHERE phone=?', (this_month, r['phone']))
    return this_month


def gen_gift_code():
    return 'GJ' + uuid.uuid4().hex[:10].upper()


def grant_referral_base(referrer_phone, referee_phone, referee_name, conn=None):
    """朋友用引荐码注册：建立关系 + 双方各得基础分（幂等：关系已存在则补发漏发的分）。"""
    own = conn is None
    if own:
        conn = get_db()
    _ensure_tables(conn)
    reset_gift_quota_if_new_month(conn)
    ref = conn.execute('SELECT * FROM referrals WHERE referrer_phone=? AND referee_phone=?',
                       (referrer_phone, referee_phone)).fetchone()
    if not ref:
        conn.execute('INSERT INTO referrals (referrer_phone, referee_phone, referee_name, base_awarded) VALUES (?,?,?,1)',
                     (referrer_phone, referee_phone, referee_name))
        # 双方各得基础分（复用主连接，统一提交）
        add_points(referrer_phone, REFER_BASE_POINTS, 'refer_base', f'引荐{referee_name}注册', conn)
        add_points(referee_phone, REFER_BASE_POINTS, 'refer_base', '被引荐注册奖励', conn)
        result = {'ok': True, 'base_awarded': True, 'first_order_pending': True}
    else:
        result = {'ok': True, 'base_awarded': False, 'first_order_pending': not ref['first_order_awarded']}
        if not ref['base_awarded']:
            conn.execute('UPDATE referrals SET base_awarded=1 WHERE id=?', (ref['id'],))
            add_points(referrer_phone, REFER_BASE_POINTS, 'refer_base', f'引荐{referee_name}注册', conn)
            add_points(referee_phone, REFER_BASE_POINTS, 'refer_base', '被引荐注册奖励', conn)
            result['base_awarded'] = True
    if own:
        conn.commit()
        conn.close()
    return result


def mark_consumption(phone, amount, source='', conn=None):
    """记录会员消费。触发：①引荐首单奖励（朋友首单双方各得奖励分）②被赠临时卡级首单后回落。返回 dict。"""
    own = conn is None
    if own:
        conn = get_db()
    _ensure_tables(conn)
    reset_gift_quota_if_new_month(conn)
    # 写入消费记录
    conn.execute('INSERT INTO member_consumptions (phone, amount, source, awarded_first_order) VALUES (?,?,?,0)',
                 (phone, amount, source))
    cid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]

    info = {'first_order_awarded': False, 'gift_reverted': False}
    # ① 引荐首单奖励
    ref = conn.execute('SELECT * FROM referrals WHERE referee_phone=? AND first_order_awarded=0', (phone,)).fetchone()
    if ref and amount and amount > 0:
        conn.execute('UPDATE referrals SET first_order_awarded=1 WHERE id=?', (ref['id'],))
        conn.execute('UPDATE member_consumptions SET awarded_first_order=1 WHERE id=?', (cid,))
        # 双方各得首单奖励分
        add_points(ref['referrer_phone'], REFER_FIRST_ORDER_POINTS, 'refer_first_order', f'引荐{ref["referee_name"] or ""}首单', conn)
        add_points(phone, REFER_FIRST_ORDER_POINTS, 'refer_first_order', '首单达成奖励', conn)
        info['first_order_awarded'] = True

    # ② 被赠临时卡级：首单消费后回落（仅当是通过赠卡获得临时卡级的情况）
    u = conn.execute('SELECT temp_level, temp_level_expire FROM users WHERE phone=?', (phone,)).fetchone()
    if u and u['temp_level']:
        # 临时卡级在"首单消费"后回落为真实卡级（被赠人自己的普卡等）
        conn.execute('UPDATE users SET temp_level=?, temp_level_expire=? WHERE phone=?', ('', '', phone))
        info['gift_reverted'] = True

    if own:
        conn.commit()
        conn.close()
    return info


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

def add_points(phone, points, action, remark='', conn=None):
    """统一加分入口：加分 + 记流水 + 自动升级等级 + 检查徽章。
    后续内容层/互动层行为（发帖/评论/被赞）直接调用此函数即可，无需重复造轮子。
    conn 由调用方传入时复用其事务（不自行提交/关闭），避免同一请求内多连接互锁 SQLite。
    """
    if not phone or points == 0:
        return {'ok': False, 'error': '参数错误'}
    own = conn is None
    if own:
        conn = get_db()
    _ensure_tables(conn)
    user = conn.execute('SELECT id, points, membership_level FROM users WHERE phone=?', (phone,)).fetchone()
    if not user:
        if own:
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
    if own:
        conn.commit()
        conn.close()
    new_badges = check_badges(phone, conn)
    return {'ok': True, 'points': new_points, 'added': points, 'level': new_level,
            'level_up': level_up, 'new_badges': new_badges}

def check_badges(phone, conn=None):
    """检查并自动颁发达成条件的徽章，返回本次新获得的徽章 code 列表。
    conn 由调用方传入时复用其事务（不自行提交/关闭），否则自建连接。
    """
    if not phone:
        return []
    own = conn is None
    if own:
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
    if own:
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


# ========== API - Admin: 积分商城管理（上架/编辑/下架/删除） ==========
@app.route('/api/admin/redeem-goods', methods=['GET'])
@login_required
def api_admin_redeem_goods_list():
    """管理端查看全部积分商品（含已下架）"""
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    conn = get_db(); _ensure_tables(conn)
    rows = conn.execute("SELECT * FROM redeem_goods ORDER BY (status='active') DESC, points").fetchall()
    conn.close()
    return jsonify(ok=True, data=[dict(r) for r in rows])


@app.route('/api/admin/redeem-goods', methods=['POST'])
@login_required
def api_admin_redeem_goods_create():
    """新增积分商品（上架）"""
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify(ok=False, error='请填写商品名称')
    try:
        points = int(data.get('points', 0))
    except (ValueError, TypeError):
        return jsonify(ok=False, error='积分必须为整数')
    if points <= 0:
        return jsonify(ok=False, error='积分必须大于 0')
    category = (data.get('category') or '餐饮').strip() or '餐饮'
    gradient = (data.get('gradient') or '').strip()
    status = 'active' if data.get('status') == 'active' else 'inactive'
    try:
        stock = int(data.get('stock', -1))
    except (ValueError, TypeError):
        stock = -1
    conn = get_db(); _ensure_tables(conn)
    nums = []
    for r in conn.execute("SELECT id FROM redeem_goods").fetchall():
        try:
            nums.append(int(str(r['id']).lstrip('g')))
        except (ValueError, TypeError):
            pass
    nid = 'g' + str((max(nums) + 1) if nums else 1)
    conn.execute(
        "INSERT INTO redeem_goods (id,name,points,category,gradient,status,stock) VALUES (?,?,?,?,?,?,?)",
        (nid, name, points, category, gradient, status, stock))
    if status == 'active':
        _push_message(conn, '积分商城上新', f"「{name}」已上架积分商城，快去用积分兑换吧～", 'redeem', 0, 'redeem', 0)
    conn.commit(); conn.close()
    return jsonify(ok=True, data={'id': nid, 'message': '已上架' if status == 'active' else '已添加（下架）'})


@app.route('/api/admin/redeem-goods/<gid>', methods=['PUT'])
@login_required
def api_admin_redeem_goods_update(gid):
    """编辑积分商品"""
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    data = request.get_json(force=True, silent=True) or {}
    conn = get_db(); _ensure_tables(conn)
    row = conn.execute("SELECT id FROM redeem_goods WHERE id=?", (gid,)).fetchone()
    if not row:
        conn.close(); return jsonify(ok=False, error='商品不存在')
    fields = {}
    if 'name' in data:
        fields['name'] = str(data['name']).strip()
    if 'points' in data:
        try:
            p = int(data['points'])
        except (ValueError, TypeError):
            return jsonify(ok=False, error='积分必须为整数')
        if p <= 0:
            return jsonify(ok=False, error='积分必须大于 0')
        fields['points'] = p
    if 'category' in data:
        fields['category'] = str(data['category']).strip() or '餐饮'
    if 'gradient' in data:
        fields['gradient'] = str(data['gradient'])
    if 'stock' in data:
        try:
            s = int(data['stock'])
        except (ValueError, TypeError):
            s = -1
        fields['stock'] = s
    if 'status' in data:
        fields['status'] = data['status'] if data['status'] in ('active', 'inactive') else 'inactive'
    if fields:
        conn.execute(
            "UPDATE redeem_goods SET " + ", ".join(f"{k}=?" for k in fields) + " WHERE id=?",
            list(fields.values()) + [gid])
        conn.commit()
    conn.close()
    return jsonify(ok=True, data={'message': '已更新'})


@app.route('/api/admin/redeem-goods/<gid>/toggle', methods=['POST'])
@login_required
def api_admin_redeem_goods_toggle(gid):
    """上架 / 下架切换"""
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    conn = get_db(); _ensure_tables(conn)
    row = conn.execute("SELECT status, name FROM redeem_goods WHERE id=?", (gid,)).fetchone()
    if not row:
        conn.close(); return jsonify(ok=False, error='商品不存在')
    new_status = 'inactive' if row['status'] == 'active' else 'active'
    conn.execute("UPDATE redeem_goods SET status=? WHERE id=?", (new_status, gid))
    if new_status == 'active':
        _push_message(conn, '积分商城上新', f"「{row['name']}」已上架积分商城，快去用积分兑换吧～", 'redeem', 0, 'redeem', 0)
    conn.commit(); conn.close()
    return jsonify(ok=True, data={'status': new_status, 'message': '已上架' if new_status == 'active' else '已下架'})


@app.route('/api/admin/redeem-goods/<gid>', methods=['DELETE'])
@login_required
def api_admin_redeem_goods_delete(gid):
    """删除积分商品"""
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    conn = get_db(); _ensure_tables(conn)
    conn.execute("DELETE FROM redeem_goods WHERE id=?", (gid,))
    conn.commit(); conn.close()
    return jsonify(ok=True, data={'message': '已删除'})


# ========== API - Admin: 优惠券管理（上架/编辑/下架/删除） ==========
@app.route('/api/admin/offers', methods=['GET'])
@login_required
def api_admin_offers_list():
    """管理端查看全部优惠券（含已停用）"""
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    conn = get_db(); _ensure_tables(conn)
    rows = conn.execute("SELECT * FROM offers ORDER BY (status='active') DESC, id").fetchall()
    conn.close()
    return jsonify(ok=True, data=[dict(r) for r in rows])


@app.route('/api/admin/offers', methods=['POST'])
@login_required
def api_admin_offers_create():
    """新增优惠券（默认上架）"""
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    data = request.get_json(force=True, silent=True) or {}
    shop_name = (data.get('shop_name') or '').strip()
    label = (data.get('label') or '').strip()
    if not shop_name:
        return jsonify(ok=False, error='请填写商户名称')
    if not label:
        return jsonify(ok=False, error='请填写券说明')
    try:
        amount = int(data.get('amount', 0))
    except (ValueError, TypeError):
        return jsonify(ok=False, error='面额必须为整数')
    if amount < 0:
        return jsonify(ok=False, error='面额不能为负')
    category = (data.get('category') or 'food').strip() or 'food'
    color = (data.get('color') or '#FF7B2C').strip() or '#FF7B2C'
    expire = (data.get('expire') or '').strip()
    status = 'active' if data.get('status') == 'active' else 'inactive'
    target_level = (data.get('target_level') or '').strip()
    conn = get_db(); _ensure_tables(conn)
    conn.execute(
        "INSERT INTO offers (shop_name,label,expire,amount,category,color,status,target_level) VALUES (?,?,?,?,?,?,?,?)",
        (shop_name, label, expire, amount, category, color, status, target_level))
    oid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    if status == 'active':
        _push_message(conn, '新优惠券上架', f"{shop_name} 的「{label}」已上架，打开 App 即可领取～", 'offer', 0, 'offer', oid)
    conn.commit(); conn.close()
    return jsonify(ok=True, data={'id': oid, 'message': '已上架' if status == 'active' else '已添加（下架）'})


@app.route('/api/admin/offers/<int:oid>', methods=['PUT'])
@login_required
def api_admin_offers_update(oid):
    """编辑优惠券"""
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    data = request.get_json(force=True, silent=True) or {}
    conn = get_db(); _ensure_tables(conn)
    row = conn.execute("SELECT id FROM offers WHERE id=?", (oid,)).fetchone()
    if not row:
        conn.close(); return jsonify(ok=False, error='优惠券不存在')
    fields = {}
    if 'shop_name' in data:
        fields['shop_name'] = str(data['shop_name']).strip()
    if 'label' in data:
        fields['label'] = str(data['label']).strip()
    if 'amount' in data:
        try:
            a = int(data['amount'])
        except (ValueError, TypeError):
            return jsonify(ok=False, error='面额必须为整数')
        if a < 0:
            return jsonify(ok=False, error='面额不能为负')
        fields['amount'] = a
    if 'category' in data:
        fields['category'] = str(data['category']).strip() or 'food'
    if 'color' in data:
        fields['color'] = str(data['color']).strip() or '#FF7B2C'
    if 'expire' in data:
        fields['expire'] = str(data['expire']).strip()
    if 'status' in data:
        fields['status'] = data['status'] if data['status'] in ('active', 'inactive') else 'inactive'
    if fields:
        conn.execute(
            "UPDATE offers SET " + ", ".join(f"{k}=?" for k in fields) + " WHERE id=?",
            list(fields.values()) + [oid])
        conn.commit()
    conn.close()
    return jsonify(ok=True, data={'message': '已更新'})


@app.route('/api/admin/offers/<int:oid>/toggle', methods=['POST'])
@login_required
def api_admin_offers_toggle(oid):
    """上架 / 下架切换"""
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    conn = get_db(); _ensure_tables(conn)
    row = conn.execute("SELECT status, shop_name, label FROM offers WHERE id=?", (oid,)).fetchone()
    if not row:
        conn.close(); return jsonify(ok=False, error='优惠券不存在')
    new_status = 'inactive' if row['status'] == 'active' else 'active'
    conn.execute("UPDATE offers SET status=? WHERE id=?", (new_status, oid))
    if new_status == 'active':
        _push_message(conn, '新优惠券上架', f"{row['shop_name']} 的「{row['label']}」已上架，打开 App 即可领取～", 'offer', 0, 'offer', oid)
    conn.commit(); conn.close()
    return jsonify(ok=True, data={'status': new_status, 'message': '已上架' if new_status == 'active' else '已下架'})


@app.route('/api/admin/offers/<int:oid>', methods=['DELETE'])
@login_required
def api_admin_offers_delete(oid):
    """删除优惠券"""
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    conn = get_db(); _ensure_tables(conn)
    conn.execute("DELETE FROM offers WHERE id=?", (oid,))
    conn.commit(); conn.close()
    return jsonify(ok=True, data={'message': '已删除'})


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
    shop_id = data.get('shop_id', '').strip()
    if not rating or rating < 1 or rating > 5:
        return jsonify(ok=False, error='请选择评分（1-5星）')
    conn = get_db()
    _ensure_tables(conn)
    conn.execute(
        "INSERT INTO feedbacks (user_phone, feedback_type, biz_type, order_id, shop_id, rating, feedback_text) VALUES (?,?,?,?,?,?,?)",
        (phone, feedback_type, biz_type, order_id, shop_id, rating, feedback_text)
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

# ========== 运营洞察聚合辅助函数 ==========
def _parse_dt(s):
    """容错解析日期字符串 -> datetime 或 None"""
    if not s:
        return None
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return None

def _daily_agg(conn, table, date_col, days, agg='COUNT(*)', where=''):
    """返回最近 days 天每日聚合序列 [{date, value}]（缺失补 0）。table/agg/where 均为内部常量。"""
    now = datetime.now()
    start = now - timedelta(days=days - 1)
    start_str = start.strftime('%Y-%m-%d 00:00:00')
    w = f" AND {where}" if where else ""
    sql = f"SELECT strftime('%Y-%m-%d', {date_col}) AS d, {agg} FROM {table} WHERE {date_col} >= ?{w} GROUP BY d"
    m = {}
    try:
        for r in conn.execute(sql, (start_str,)).fetchall():
            m[r['d']] = r[1] or 0
    except Exception:
        pass
    series = []
    d = start.date()
    while d <= now.date():
        ds = d.strftime('%Y-%m-%d')
        series.append({'date': ds, 'value': m.get(ds, 0)})
        d += timedelta(days=1)
    return series

def _window_total(conn, table, date_col, days, agg='COUNT(*)', where=''):
    """返回 (当前 days 窗口合计, 上一周期合计)，用于环比。table/agg/where 均为内部常量。"""
    now = datetime.now()
    start = now - timedelta(days=days)
    prev_start = now - timedelta(days=2 * days)
    w = f" AND {where}" if where else ""
    cur = conn.execute(f"SELECT {agg} FROM {table} WHERE {date_col} >= ?{w}", (start.strftime('%Y-%m-%d %H:%M:%S'),)).fetchone()[0] or 0
    prev = conn.execute(f"SELECT {agg} FROM {table} WHERE {date_col} >= ? AND {date_col} < ?{w}", (prev_start.strftime('%Y-%m-%d %H:%M:%S'), start.strftime('%Y-%m-%d %H:%M:%S'))).fetchone()[0] or 0
    return cur, prev

@app.route('/api/admin/insights', methods=['GET'])
@login_required
def api_admin_insights():
    """运营洞察（全量）：趋势/转化/预警/健康度 + 基础诊断，均基于真实表实时聚合。
    支持 ?days=7|30|90（默认 30）。"""
    if session.get('role') not in ('admin','super_admin','tenant_admin'):
        return jsonify(ok=False, error='权限不足')
    try:
        days = int(request.args.get('days', 30))
    except Exception:
        days = 30
    if days not in (7, 30, 90):
        days = 30
    conn = get_db()
    _ensure_tables(conn)
    now = datetime.now()
    start = now - timedelta(days=days - 1)
    start_str = start.strftime('%Y-%m-%d 00:00:00')
    prev_start = now - timedelta(days=2 * days)

    # ---------- 基础诊断（保留旧结构） ----------
    complaints = conn.execute("SELECT COUNT(*) FROM work_orders WHERE type='投诉建议'").fetchone()[0]
    complaint_categories = conn.execute("SELECT title FROM work_orders WHERE type='投诉建议' ORDER BY id DESC LIMIT 200").fetchall()
    pending = conn.execute("SELECT question, COUNT(*) as cnt FROM kb_pending WHERE status='pending' GROUP BY question ORDER BY cnt DESC LIMIT 10").fetchall()
    pending_total = conn.execute("SELECT COUNT(*) FROM kb_pending WHERE status='pending'").fetchone()[0]
    low_feedback = conn.execute("SELECT * FROM feedbacks WHERE rating <= 3 ORDER BY id DESC LIMIT 20").fetchall()
    from collections import Counter
    cat_counter = Counter()
    for c in complaint_categories:
        t = c['title'] or ''
        parts = t.split(' - ')
        if len(parts) >= 3:
            cat_counter[parts[2]] += 1
        elif len(parts) == 2:
            cat_counter[parts[1]] += 1
    top_complaints = [{'category': k, 'count': v} for k, v in cat_counter.most_common(8)]

    # ========== A. 投诉/评分趋势 + 环比 ==========
    complaint_trend = _daily_agg(conn, 'work_orders', 'created_at', days, where="type='投诉建议'")
    rating_rows = conn.execute(
        "SELECT strftime('%Y-%m-%d',created_at) d, AVG(rating) avg_r, SUM(CASE WHEN rating<=3 THEN 1 ELSE 0 END) low, COUNT(*) c FROM feedbacks WHERE created_at >= ? GROUP BY d",
        (start_str,)).fetchall()
    rating_map = {r['d']: r for r in rating_rows}
    rating_trend = []
    d = start.date()
    while d <= now.date():
        ds = d.strftime('%Y-%m-%d')
        rr = rating_map.get(ds)
        rating_trend.append({'date': ds, 'avg': round(rr['avg_r'], 2) if rr and rr['avg_r'] else None, 'low': rr['low'] if rr else 0})
        d += timedelta(days=1)
    comp_cur, comp_prev = _window_total(conn, 'work_orders', 'created_at', days, where="type='投诉建议'")
    r_cur = conn.execute("SELECT AVG(rating), SUM(CASE WHEN rating<=3 THEN 1 ELSE 0 END), COUNT(*) FROM feedbacks WHERE created_at >= ?", (start.strftime('%Y-%m-%d %H:%M:%S'),)).fetchone()
    r_prev = conn.execute("SELECT AVG(rating), SUM(CASE WHEN rating<=3 THEN 1 ELSE 0 END), COUNT(*) FROM feedbacks WHERE created_at >= ? AND created_at < ?", (prev_start.strftime('%Y-%m-%d %H:%M:%S'), start.strftime('%Y-%m-%d %H:%M:%S'))).fetchone()
    rating_cur = round(r_cur[0], 2) if r_cur[0] else 0
    rating_prev = round(r_prev[0], 2) if r_prev[0] else 0
    lowrate_cur = round(r_cur[1] / r_cur[2] * 100, 1) if r_cur[2] else 0
    lowrate_prev = round(r_prev[1] / r_prev[2] * 100, 1) if r_prev[2] else 0

    # ========== B. 会员新增/活跃/沉默趋势 ==========
    members = conn.execute("SELECT phone, last_visit, created_at FROM users WHERE role='user'").fetchall()
    silent = 0
    for m in members:
        lv = _parse_dt(m['last_visit']) or _parse_dt(m['created_at'])
        ds_since = (now - lv).days if lv else 9999
        if ds_since > 90:
            silent += 1
    silent_total = len(members)
    silent_ratio = round(silent / silent_total * 100, 1) if silent_total else 0
    # 每日活跃（签到/打卡/消费去重）+ 每日新增
    active_map = {}
    for table, col, mode, pcol in [('sign_in_records', 'sign_date', 'date', 'user_phone'),
                                   ('daily_checkins', 'checkin_date', 'date', 'phone'),
                                   ('member_consumptions', 'created_at', 'dt', 'phone')]:
        if mode == 'date':
            for r in conn.execute(f"SELECT {col}, {pcol} FROM {table} WHERE {col} >= ?", (start.strftime('%Y-%m-%d'),)).fetchall():
                d0 = (r[col] or '')[:10]
                if d0:
                    active_map.setdefault(d0, set()).add(r[pcol])
        else:
            for r in conn.execute(f"SELECT strftime('%Y-%m-%d',{col}) d, {pcol} FROM {table} WHERE {col} >= ?", (start_str,)).fetchall():
                d0 = (r['d'] or '')[:10]
                if d0:
                    active_map.setdefault(d0, set()).add(r[pcol])
    new_map = {}
    for r in conn.execute("SELECT strftime('%Y-%m-%d',created_at) d, phone FROM users WHERE role='user' AND created_at >= ?", (start_str,)).fetchall():
        new_map.setdefault(r['d'], set()).add(r['phone'])
    member_trend = []
    d = start.date()
    while d <= now.date():
        ds = d.strftime('%Y-%m-%d')
        member_trend.append({'date': ds, 'active': len(active_map.get(ds, set())), 'new': len(new_map.get(ds, set()))})
        d += timedelta(days=1)
    # 沉默会员趋势：每个统计日，last_visit/created_at 早于 (该日-90天) 的人数
    silent_trend = []
    d = start.date()
    while d <= now.date():
        ds = d.strftime('%Y-%m-%d')
        thr = datetime(d.year, d.month, d.day) - timedelta(days=90)
        cnt = 0
        for m in members:
            lv = _parse_dt(m['last_visit']) or _parse_dt(m['created_at'])
            if lv and lv < thr:
                cnt += 1
        silent_trend.append({'date': ds, 'value': cnt})
        d += timedelta(days=1)

    # ========== C. 营销转化漏斗（券：发放→领取→核销 + 活动转化） ==========
    issued = conn.execute("SELECT COUNT(*) FROM offers WHERE status='active'").fetchone()[0]
    cr = conn.execute("SELECT COUNT(*), COALESCE(SUM(CASE WHEN redeemed=1 THEN 1 ELSE 0 END),0) FROM coupon_claims WHERE claimed_at >= ?", (start_str,)).fetchone()
    claimed = cr[0] or 0
    redeemed = cr[1] or 0
    claim_rate = round(claimed / issued * 100, 1) if issued else 0
    redeem_rate = round(redeemed / claimed * 100, 1) if claimed else 0
    act_rows = conn.execute("SELECT COUNT(*), COALESCE(SUM(enrolled),0), COALESCE(SUM(CASE WHEN offer_ids IS NOT NULL AND offer_ids<>'' THEN 1 ELSE 0 END),0) FROM activities").fetchone()
    act_count = act_rows[0] or 0
    act_enrolled = act_rows[1] or 0
    act_with_offer = act_rows[2] or 0
    act_offer_ids = set()
    for s in conn.execute("SELECT offer_ids FROM activities WHERE offer_ids IS NOT NULL AND offer_ids<>''").fetchall():
        for o in (s[0] or '').split(','):
            o = o.strip()
            if o:
                act_offer_ids.add(o)
    act_redeemed = 0
    if act_offer_ids:
        ph = ','.join('?' * len(act_offer_ids))
        act_redeemed = conn.execute(f"SELECT COUNT(*) FROM coupon_claims WHERE redeemed=1 AND offer_id IN ({ph})", tuple(act_offer_ids)).fetchone()[0] or 0
    funnel = {'issued': issued, 'claimed': claimed, 'redeemed': redeemed,
              'claim_rate': claim_rate, 'redeem_rate': redeem_rate,
              'act_count': act_count, 'act_enrolled': act_enrolled,
              'act_with_offer': act_with_offer, 'act_redeemed': act_redeemed}

    # ========== D. AI 命中率 / 知识库健康度 ==========
    kb_total = conn.execute("SELECT COUNT(*) FROM kb_pending").fetchone()[0]
    kb_imported = conn.execute("SELECT COUNT(*) FROM kb_pending WHERE status='imported'").fetchone()[0]
    kb_dismissed = conn.execute("SELECT COUNT(*) FROM kb_pending WHERE status='dismissed'").fetchone()[0]
    kb_handled = kb_imported + kb_dismissed
    kb_hit_rate = round(kb_handled / kb_total * 100, 1) if kb_total else 100
    kb_pending_trend = _daily_agg(conn, 'kb_pending', 'created_at', days)
    esc_rows = conn.execute("SELECT strftime('%Y-%m-%d',created_at) d, COUNT(*) c FROM human_chat_messages WHERE work_order_id IS NOT NULL AND created_at >= ? GROUP BY d", (start_str,)).fetchall()
    esc_map = {r['d']: r['c'] for r in esc_rows}
    esc_trend = []
    d = start.date()
    while d <= now.date():
        ds = d.strftime('%Y-%m-%d')
        esc_trend.append({'date': ds, 'value': esc_map.get(ds, 0)})
        d += timedelta(days=1)
    kb_health = {'total': kb_total, 'pending': pending_total, 'imported': kb_imported,
                 'dismissed': kb_dismissed, 'hit_rate': kb_hit_rate,
                 'pending_trend': kb_pending_trend, 'escalation_trend': esc_trend}

    # ========== F. GMV / 客单价 / 人均趋势 + 环比 ==========
    gmv_trend = _daily_agg(conn, 'member_consumptions', 'created_at', days, agg='COALESCE(SUM(amount),0)')
    gmv_rows = conn.execute("SELECT strftime('%Y-%m-%d',created_at) d, SUM(amount) s, COUNT(*) c, COUNT(DISTINCT phone) p FROM member_consumptions WHERE created_at >= ? GROUP BY d", (start_str,)).fetchall()
    gmv_map = {r['d']: r for r in gmv_rows}
    aov_trend = []
    percap_trend = []
    d = start.date()
    while d <= now.date():
        ds = d.strftime('%Y-%m-%d')
        g = gmv_map.get(ds)
        aov_trend.append({'date': ds, 'value': round(g['s'] / g['c'], 1) if g and g['c'] else 0})
        percap_trend.append({'date': ds, 'value': round(g['s'] / g['p'], 1) if g and g['p'] else 0})
        d += timedelta(days=1)
    gmv_cur, gmv_prev = _window_total(conn, 'member_consumptions', 'created_at', days, agg='COALESCE(SUM(amount),0)')
    ac = conn.execute("SELECT COALESCE(SUM(amount),0), COUNT(*) FROM member_consumptions WHERE created_at >= ?", (start.strftime('%Y-%m-%d %H:%M:%S'),)).fetchone()
    ap = conn.execute("SELECT COUNT(DISTINCT phone) FROM member_consumptions WHERE created_at >= ?", (start.strftime('%Y-%m-%d %H:%M:%S'),)).fetchone()[0] or 0
    aov_cur = round(ac[0] / ac[1], 1) if ac[1] else 0
    percap_cur = round(ac[0] / ap, 1) if ap else 0

    # ========== E. 智能预警雷达 ==========
    alerts = []
    merch = conn.execute("SELECT shop_id, COUNT(*) c, SUM(CASE WHEN rating<=3 THEN 1 ELSE 0 END) low FROM feedbacks WHERE created_at >= ? GROUP BY shop_id HAVING c>=2", (start_str,)).fetchall()
    for r in merch:
        nr = round((r['low'] or 0) / r['c'] * 100, 0)
        if nr >= 50:
            sid = r['shop_id'] or '未知商户'
            alerts.append({'level': 'high', 'title': f'{sid} 差评率突增',
                           'detail': f'近 {days} 天 {r["c"]} 条评价中 {r["low"]} 条差评（{nr:.0f}%）'})
    comp_vals = [x['value'] for x in complaint_trend]
    avg_comp = sum(comp_vals) / len(comp_vals) if comp_vals else 0
    for x in complaint_trend:
        if avg_comp > 0 and x['value'] >= 2 * avg_comp and x['value'] > 0:
            alerts.append({'level': 'mid', 'title': f'{x["date"]} 投诉量异常',
                           'detail': f'当日 {x["value"]} 起投诉，约为均值（{avg_comp:.1f}）的 {x["value"]/avg_comp:.1f} 倍'})
    if claimed > 0 and redeem_rate < 5:
        alerts.append({'level': 'mid', 'title': '券核销率偏低',
                       'detail': f'近 {days} 天领取 {claimed} 张，核销率仅 {redeem_rate}%，需排查核销链路/引导'})
    if silent_ratio >= 40:
        alerts.append({'level': 'high' if silent_ratio >= 60 else 'mid', 'title': '沉默会员占比偏高',
                       'detail': f'超 90 天未到店会员 {silent} 人，占 {silent_ratio}%，建议定向召回'})
    if pending_total >= 5:
        alerts.append({'level': 'mid', 'title': '知识库待补充积压',
                       'detail': f'尚有 {pending_total} 条未命中问题待入库，影响 AI 应答准确率'})
    alerts.sort(key=lambda a: 0 if a['level'] == 'high' else 1 if a['level'] == 'mid' else 2)

    # ========== G. 可点选建议（跳转对应模块/动作） ==========
    avg_low = round(sum(f['rating'] for f in low_feedback) / len(low_feedback), 1) if low_feedback else 0
    suggestions = []
    if top_complaints:
        top = top_complaints[0]
        suggestions.append({'text': f'高频投诉集中在「{top["category"]}」类（{top["count"]}次），建议优先优化该环节服务', 'target': '/admin/intelligence', 'tab': '口碑运营'})
    if pending_total:
        suggestions.append({'text': f'知识库有 {pending_total} 条未命中问题待补充，建议尽快整理入库提升 AI 准确率', 'action': 'scroll-kb'})
    if low_feedback:
        suggestions.append({'text': f'近期有 {len(low_feedback)} 条低分评价（均分 {avg_low}），建议复盘服务卡点', 'target': '/admin/intelligence', 'tab': '口碑运营'})
    if silent_ratio >= 40:
        suggestions.append({'text': f'{silent} 位会员已超 90 天未到店，建议发起「回来看看」定向召回', 'action': 'send-coupon', 'key': 'silent_recall'})
    if claimed > 0 and redeem_rate < 20:
        suggestions.append({'text': f'券核销率仅 {redeem_rate}%，建议群发「核销提醒」定向券拉动到店', 'action': 'send-coupon', 'key': 'redeem_boost'})

    # ========== H. AI 对话洞察反哺（客服小江到底在答什么/哪些没答上） ==========
    chat_rows = conn.execute(
        "SELECT content, COUNT(*) c FROM conversations WHERE role='user' AND created_at >= ? GROUP BY content ORDER BY c DESC LIMIT 10",
        (start_str,)).fetchall()
    chat_topics = [{'question': r['content'], 'count': r['c']} for r in chat_rows]
    unanswered_count = conn.execute(
        "SELECT COUNT(*) FROM conversations WHERE role='assistant' AND answered=0 AND created_at >= ?", (start_str,)).fetchone()[0] or 0
    kb_pending_sample = conn.execute(
        "SELECT id, question FROM kb_pending WHERE status='pending' ORDER BY id DESC LIMIT 10").fetchall()
    unanswered_sample = [{'id': r['id'], 'question': r['question']} for r in kb_pending_sample]

    handled_rows = conn.execute("SELECT ref_key FROM insight_actions WHERE action_type='alert'").fetchall()
    handled_alerts = [r['ref_key'] for r in handled_rows]
    exec_rows = conn.execute("SELECT ref_key FROM insight_actions WHERE action_type='suggestion'").fetchall()
    executed_suggestions = [r['ref_key'] for r in exec_rows]
    conn.close()
    return jsonify(ok=True, data={
        'complaint_total': complaints,
        'top_complaints': top_complaints,
        'pending_total': pending_total,
        'top_pending': [{'question': p['question'], 'count': p['cnt']} for p in pending],
        'low_feedback_count': len(low_feedback),
        # A 投诉/评分趋势
        'complaint_trend': complaint_trend,
        'rating_trend': rating_trend,
        'comp_cur': comp_cur, 'comp_prev': comp_prev,
        'rating_cur': rating_cur, 'rating_prev': rating_prev,
        'lowrate_cur': lowrate_cur, 'lowrate_prev': lowrate_prev,
        # B 会员趋势
        'member_trend': member_trend,
        'silent_count': silent, 'silent_ratio': silent_ratio, 'silent_trend': silent_trend,
        'member_total': silent_total,
        # C 漏斗
        'funnel': funnel,
        # D KB 健康度
        'kb_health': kb_health,
        # F GMV
        'gmv_trend': gmv_trend, 'aov_trend': aov_trend, 'percap_trend': percap_trend,
        'gmv_cur': gmv_cur, 'gmv_prev': gmv_prev, 'aov_cur': aov_cur, 'percap_cur': percap_cur,
        # E 预警
        'alerts': alerts,
        # G 可点建议
        'suggestions': suggestions,
        # H AI 对话洞察反哺
        'chat_topics': chat_topics,
        'unanswered_count': unanswered_count,
        'unanswered_sample': unanswered_sample,
        # H 时间范围
        'days': days,
        # 处置留痕（预警一键已处理 / 建议已执行）
        'handled_alerts': handled_alerts,
        'executed_suggestions': executed_suggestions,
    })


# ========== 运营洞察：预警一键处置 / 建议直接执行（动作闭环） ==========
@app.route('/api/admin/insight-alert/handle', methods=['POST'])
@login_required
def api_admin_insight_alert_handle():
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    key = (request.get_json() or {}).get('key') or ''
    if not key:
        return jsonify(ok=False, error='缺少 key')
    conn = get_db(); _ensure_tables(conn)
    conn.execute("INSERT INTO insight_actions (action_type, ref_key, created_at) VALUES ('alert',?,?)",
                 (key, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit(); conn.close()
    return jsonify(ok=True)


@app.route('/api/admin/insight-suggestion/exec', methods=['POST'])
@login_required
def api_admin_insight_suggestion_exec():
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    data = request.get_json() or {}
    key = data.get('key') or ''
    if not key:
        return jsonify(ok=False, error='缺少 key')
    conn = get_db(); _ensure_tables(conn)
    today = datetime.now().strftime('%Y-%m-%d')
    pushed = 0
    target = '/admin/notify'
    if key == 'silent_recall':
        # 沉默召回：超 90 天未到店会员，真实推送召回券
        members = conn.execute("SELECT phone, display_name, last_visit, created_at FROM users WHERE role='user' AND phone<>''").fetchall()
        now = datetime.now()
        for m in members:
            lv = _parse_dt(m['last_visit']) or _parse_dt(m['created_at'])
            ds = (now - lv).days if lv else 9999
            if ds > 90 and m['phone']:
                name = m['display_name'] or '会员'
                content = f'【海江新天地】{name}，好久不见！专属回归礼：满100减30券已为您备好，到店出示手机号即可用~退订回T'
                if _push_sms(m['phone'], 'silent_recall', content, cycle=today):
                    pushed += 1
    elif key == 'redeem_boost':
        # 核销拉动：有未核销券的会员，提醒核销
        rows = conn.execute("SELECT DISTINCT user_phone FROM coupon_claims WHERE redeemed=0 AND user_phone<>''").fetchall()
        for r in rows:
            phone = r['user_phone']
            if not phone:
                continue
            content = '【海江新天地】您有一张券还未核销，快来门店使用享专属优惠，逾期作废哦~退订回T'
            if _push_sms(phone, 'redeem_boost', content, cycle=today):
                pushed += 1
    # 记录已执行（防重复处置）
    conn.execute("INSERT INTO insight_actions (action_type, ref_key, created_at) VALUES ('suggestion',?,?)",
                 (key, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit(); conn.close()
    return jsonify(ok=True, pushed=pushed, target=target, key=key)



# ========== 会员智能分层（RFM）+ 流失预警 ==========
def ai_text(messages, max_tokens=400):
    """调用 DeepSeek 生成文本；无 key 或异常时返回 None（交由调用方兜底）。"""
    if not DS_API_KEY:
        return None
    try:
        resp = ds_client.chat.completions.create(
            model='deepseek-chat', messages=messages, max_tokens=max_tokens, temperature=0.5
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return None

def _rfm_scores(last_visit, freq, monetary):
    """返回 (R,F,M 分数1-5, 分段, 流失风险等级)"""
    now = datetime.now()
    if last_visit:
        try:
            lv = datetime.strptime(last_visit, '%Y-%m-%d %H:%M:%S')
        except Exception:
            lv = None
    else:
        lv = None
    d = (now - lv).days if lv else 999
    R = 5 if d <= 7 else 4 if d <= 30 else 3 if d <= 90 else 2 if d <= 180 else 1
    F = 1 if freq <= 0 else 2 if freq <= 2 else 3 if freq <= 5 else 4 if freq <= 10 else 5
    M = 1 if monetary < 100 else 2 if monetary < 500 else 3 if monetary < 2000 else 4 if monetary < 5000 else 5
    if R <= 2:
        seg = '沉睡/流失风险'
    elif F >= 4 and M >= 4:
        seg = '高价值'
    elif M >= 4 and F <= 2:
        seg = '潜力客户'
    elif R >= 4 and F <= 2 and M <= 2:
        seg = '新客活跃'
    else:
        seg = '稳定常客'
    churn = 'high' if (R <= 2 and F <= 1) else ('mid' if R <= 2 else 'low')
    return R, F, M, seg, churn

@app.route('/api/admin/rfm', methods=['GET'])
@login_required
def api_admin_rfm():
    """会员 RFM 智能分层 + 流失预警（复用 member_consumptions / users）"""
    if session.get('role') not in ('admin','super_admin','tenant_admin'):
        return jsonify(ok=False, error='权限不足')
    tid = session.get('tenant_id', 1)
    conn = get_db()
    _ensure_tables(conn)
    members = conn.execute(
        "SELECT id, phone, display_name, membership_level, last_visit, points, preferred_category FROM users WHERE tenant_id=? AND role='user'",
        (tid,)
    ).fetchall()
    cons = conn.execute(
        "SELECT phone, COUNT(*) AS cnt, COALESCE(SUM(amount),0) AS amt FROM member_consumptions GROUP BY phone"
    ).fetchall()
    cons_map = {c['phone']: (c['cnt'], c['amt']) for c in cons}
    segments = {}
    churn_high = 0
    churn_mid = 0
    rows = []
    for m in members:
        freq, mon = cons_map.get(m['phone'], (0, 0))
        R, F, M, seg, churn = _rfm_scores(m['last_visit'], freq, mon)
        segments[seg] = segments.get(seg, 0) + 1
        if churn == 'high': churn_high += 1
        elif churn == 'mid': churn_mid += 1
        rows.append({
            'phone': m['phone'], 'name': m['display_name'], 'level': m['membership_level'],
            'last_visit': m['last_visit'], 'points': m['points'], 'pref': m['preferred_category'],
            'R': R, 'F': F, 'M': M, 'segment': seg, 'churn': churn, 'freq': freq, 'monetary': round(mon, 2)
        })
    rows.sort(key=lambda x: (x['R'], x['F']))
    conn.close()
    return jsonify(ok=True, data={
        'total': len(members),
        'segments': segments,
        'churn_high': churn_high,
        'churn_mid': churn_mid,
        'list': rows[:300]
    })


# ========== 评价情感分析（LLM 优先，词典兜底） ==========
_SENT_NEG = ['差','慢','贵','难','投诉','垃圾','失望','退款','假','坑','乱','坏','差评','敷衍','冷漠','态度','卫生','脏','吵','卡','崩','无法','不能','不行','骗']
_SENT_POS = ['好','棒','满意','赞','不错','喜欢','贴心','热情','快','方便','优秀','给力','舒服']
_TOPIC_KW = {
    '停车': ['停车','车位','泊车'],
    '服务态度': ['态度','冷漠','热情','敷衍','服务'],
    '活动': ['活动','体验','好玩','没意思'],
    '商品': ['商品','货','质量','假','正品'],
    '环境': ['环境','卫生','脏','吵','装修','空调'],
    '价格': ['贵','便宜','价格','性价比','划算'],
    '物流配送': ['配送','快递','外卖','送达','物流'],
}

def _sentiment_heuristic(text, rating):
    t = (text or '').lower()
    neg = sum(1 for k in _SENT_NEG if k in t)
    pos = sum(1 for k in _SENT_POS if k in t)
    if rating and rating <= 2:
        sent = '投诉' if neg else '负面'
    elif rating and rating >= 4:
        sent = '正面' if (pos or not neg) else '中性'
    elif neg > pos:
        sent = '负面'
    elif pos > neg:
        sent = '正面'
    else:
        sent = '中性'
    topics = [tp for tp, kws in _TOPIC_KW.items() if any(k in t for k in kws)]
    return sent, (topics or ['其他'])

@app.route('/api/admin/feedback/sentiment', methods=['GET'])
@login_required
def api_admin_feedback_sentiment():
    """评价情感分析：正面/负面/投诉分布 + 主题聚类（LLM 优先，无 key 用词典兜底）"""
    if session.get('role') not in ('admin','super_admin','tenant_admin'):
        return jsonify(ok=False, error='权限不足')
    conn = get_db()
    _ensure_tables(conn)
    rows = conn.execute(
        "SELECT id, feedback_text, feedback_type, rating, created_at FROM feedbacks ORDER BY id DESC LIMIT 200"
    ).fetchall()
    conn.close()
    items = [{'id': r['id'], 'text': r['feedback_text'], 'type': r['feedback_type'], 'rating': r['rating'], 'created_at': r['created_at']} for r in rows]
    engine = 'heuristic'
    if DS_API_KEY and items:
        batch = [f"[{it['id']}] 评分{it['rating']}：{it['text']}" for it in items if it['text']]
        if batch:
            prompt = ("你是商场评价分析助手。下面是若干顾客评价，每条带编号。请为每条判断情感(sentiment: 正面/负面/投诉/中性)和主题(topic: 从[停车,服务态度,活动,商品,环境,价格,物流配送,其他]选最相关的1个)。\n"
                      "只返回 JSON 数组，元素格式：{\"id\":编号,\"sentiment\":\"...\",\"topic\":\"...\"}，不要其他文字。\n评价：\n" + "\n".join(batch))
            out = ai_text([{'role':'system','content':'你是严谨的数据标注助手，只输出 JSON。'}, {'role':'user','content': prompt}], max_tokens=1500)
            if out:
                try:
                    arr = json.loads(out)
                    mapping = {str(x.get('id')): x for x in arr}
                    for it in items:
                        m = mapping.get(str(it['id']))
                        if m:
                            it['sentiment'] = m.get('sentiment', '中性')
                            it['topic'] = m.get('topic', '其他')
                        else:
                            s, tp = _sentiment_heuristic(it['text'], it['rating'])
                            it['sentiment'], it['topic'] = s, tp[0]
                    engine = 'llm'
                except Exception:
                    for it in items:
                        s, tp = _sentiment_heuristic(it['text'], it['rating'])
                        it['sentiment'], it['topic'] = s, tp[0]
    else:
        for it in items:
            s, tp = _sentiment_heuristic(it['text'], it['rating'])
            it['sentiment'], it['topic'] = s, tp[0]
    from collections import Counter
    sent_cnt = Counter(it['sentiment'] for it in items)
    topic_cnt = Counter(it['topic'] for it in items)
    negatives = [it for it in items if it['sentiment'] in ('负面','投诉')]
    return jsonify(ok=True, data={
        'engine': engine,
        'total': len(items),
        'by_sentiment': dict(sent_cnt),
        'by_topic': dict(topic_cnt),
        'negatives': negatives[:50],
    })


# ========== AI 经营日报（LLM 生成，模板兜底） ==========
@app.route('/api/admin/daily-report', methods=['GET'])
@login_required
def api_admin_daily_report():
    """AI 经营日报：聚合会员/券/活动/评价，LLM 生成人话日报（无 key 用模板）"""
    if session.get('role') not in ('admin','super_admin','tenant_admin'):
        return jsonify(ok=False, error='权限不足')
    tid = session.get('tenant_id', 1)
    conn = get_db()
    _ensure_tables(conn)
    today = datetime.now().strftime('%Y-%m-%d')
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    total_members = conn.execute("SELECT COUNT(*) FROM users WHERE tenant_id=? AND role='user'", (tid,)).fetchone()[0]
    new_week = conn.execute("SELECT COUNT(*) FROM users WHERE tenant_id=? AND role='user' AND created_at >= ?", (tid, week_ago)).fetchone()[0]
    active_week = conn.execute("SELECT COUNT(*) FROM users WHERE tenant_id=? AND role='user' AND last_visit >= ?", (tid, week_ago)).fetchone()[0]
    churn = conn.execute("SELECT COUNT(*) FROM users WHERE tenant_id=? AND role='user' AND (last_visit IS NULL OR last_visit='' OR last_visit <= ?)", (tid, (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d %H:%M:%S'))).fetchone()[0]
    coupons_total = conn.execute("SELECT COUNT(*) FROM coupon_claims").fetchone()[0]
    coupons_today = conn.execute("SELECT COUNT(*) FROM coupon_claims WHERE DATE(claimed_at)=?", (today,)).fetchone()[0]
    activities_open = conn.execute("SELECT COUNT(*) FROM activities WHERE status='open'").fetchone()[0]
    fb_total = conn.execute("SELECT COUNT(*) FROM feedbacks").fetchone()[0]
    fb_today = conn.execute("SELECT COUNT(*) FROM feedbacks WHERE DATE(created_at)=?", (today,)).fetchone()[0]
    fb_avg = conn.execute("SELECT AVG(rating) FROM feedbacks").fetchone()[0]
    low_fb = conn.execute("SELECT COUNT(*) FROM feedbacks WHERE rating <= 2").fetchone()[0]
    conn.close()
    metrics = {
        'date': today,
        'total_members': total_members,
        'new_members_week': new_week,
        'active_members_week': active_week,
        'churn_risk_members': churn,
        'coupons_total': coupons_total,
        'coupons_today': coupons_today,
        'activities_open': activities_open,
        'feedback_total': fb_total,
        'feedback_today': fb_today,
        'feedback_avg': round(fb_avg, 2) if fb_avg else 0,
        'low_feedback': low_fb,
    }
    engine = 'heuristic'
    report = ''
    if DS_API_KEY:
        mp = metrics
        prompt = (f"你是商场运营助手。以下是海江新天地今日/本周经营数据：\n"
                  f"会员总数 {mp['total_members']}，本周新增 {mp['new_members_week']}，本周活跃 {mp['active_members_week']}，流失风险会员 {mp['churn_risk_members']}；\n"
                  f"券累计领取 {mp['coupons_total']}，今日领取 {mp['coupons_today']}；进行中活动 {mp['activities_open']} 个；\n"
                  f"评价总数 {mp['feedback_total']}，今日 {mp['feedback_today']}，平均评分 {mp['feedback_avg']}，差评(≤2分) {mp['low_feedback']} 条。\n"
                  f"请写一段 150 字内的中文经营日报：先一句话总评，再 3 条具体发现与建议（用 • 开头）。只输出日报正文。")
        out = ai_text([{'role':'system','content':'你是专业商场运营分析师。'}, {'role':'user','content': prompt}], max_tokens=400)
        if out:
            report = out
            engine = 'llm'
    if not report:
        report = (
            f"【海江新天地经营日报 {today}】\n"
            f"• 会员总数 {total_members}，本周新增 {new_week}、活跃 {active_week}；流失风险会员 {churn} 人，建议针对沉默会员推送「回来看看」定向券。\n"
            f"• 优惠券累计领取 {coupons_total} 张、今日 {coupons_today} 张；进行中活动 {activities_open} 个，可结合会员日加大曝光。\n"
            f"• 评价均分 {metrics['feedback_avg']}（共 {fb_total} 条），今日 {fb_today} 条、差评 {low_fb} 条"
            + (f"，请尽快跟进差评服务卡点。" if low_fb else "，口碑平稳。")
        )
    return jsonify(ok=True, data={'engine': engine, 'report': report, 'metrics': metrics})


# ========== 智能运营中心 · 衍生功能（RFM/情感/日报/跨模块，共 17 项） ==========
def _admin_role_ok():
    return session.get('role') in ('admin', 'super_admin', 'tenant_admin')

_NEXT_POINTS = {'普卡': 2000, '银卡': 5000, '金卡': 20000, '铂金卡': 40000, '钻石卡': 80000, '黑钻卡': None}

# 1) 一键召回名单（沉睡/流失风险会员 + 建议券）
@app.route('/api/admin/recall-candidates', methods=['GET'])
@login_required
def api_admin_recall_candidates():
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    tid = session.get('tenant_id', 1)
    conn = get_db(); _ensure_tables(conn)
    members = conn.execute(
        "SELECT id,phone,display_name,membership_level,last_visit,points,preferred_category FROM users WHERE tenant_id=? AND role='user'",
        (tid,)).fetchall()
    cons = conn.execute("SELECT phone, COUNT(*) cnt, COALESCE(SUM(amount),0) amt FROM member_consumptions GROUP BY phone").fetchall()
    cons_map = {c['phone']: (c['cnt'], c['amt']) for c in cons}
    rows = []
    for m in members:
        freq, mon = cons_map.get(m['phone'], (0, 0))
        R, F, M, seg, churn = _rfm_scores(m['last_visit'], freq, mon)
        if churn in ('high', 'mid'):
            pref = m['preferred_category'] or '专属'
            name = m['display_name'] or '会员'
            rows.append({
                'phone': m['phone'], 'name': name,
                'level': m['membership_level'] or '普卡',
                'last_visit': m['last_visit'], 'points': m['points'],
                'R': R, 'segment': seg, 'churn': churn,
                'suggest_coupon': '回来看看·' + pref + '专属券',
                'suggest_copy': '好久不见，' + name + '！特为您准备了「' + pref + '」专属回馈，点击立即领取>>'
            })
    rows.sort(key=lambda x: (0 if x['churn'] == 'high' else 1, x['R']))
    conn.close()
    return jsonify(ok=True, data={'total': len(rows), 'list': rows[:200]})

# 1.5) 单会员一键召回推送
@app.route('/api/admin/recall-push', methods=['POST'])
@login_required
def api_admin_recall_push():
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    try:
        data = request.get_json(force=True) or {}
    except Exception:
        data = {}
    phone = (data.get('phone') or '').strip()
    content = (data.get('content') or '').strip()
    if not phone:
        return jsonify(ok=False, error='缺少手机号')
    if not content:
        content = '好久不见！海江新天地为您准备了专属回归礼，点击立即领取>>'
    cycle = datetime.now().strftime('%Y-%m-%d')
    conn = get_db(); _ensure_tables(conn)
    sent = _push_sms(phone, 'recall', content, cycle=cycle)
    conn.close()
    return jsonify(ok=True, sent=bool(sent), phone=phone)

# 2) 复购 / 到店预测
@app.route('/api/admin/repurchase', methods=['GET'])
@login_required
def api_admin_repurchase():
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    conn = get_db(); _ensure_tables(conn)
    rows = conn.execute("SELECT phone, created_at FROM member_consumptions ORDER BY created_at").fetchall()
    from collections import defaultdict
    by_phone = defaultdict(list)
    for r in rows:
        if r['created_at']:
            by_phone[r['phone']].append(r['created_at'])
    preds = []
    now = datetime.now()
    for phone, ts in by_phone.items():
        ts.sort()
        if len(ts) < 2:
            continue
        deltas = []
        for i in range(1, len(ts)):
            try:
                d1 = datetime.strptime(ts[i-1][:19], '%Y-%m-%d %H:%M:%S')
                d2 = datetime.strptime(ts[i][:19], '%Y-%m-%d %H:%M:%S')
                deltas.append((d2 - d1).days)
            except Exception:
                pass
        if not deltas:
            continue
        avg = sum(deltas) / len(deltas)
        try:
            last = datetime.strptime(ts[-1][:19], '%Y-%m-%d %H:%M:%S')
        except Exception:
            continue
        nxt = last + timedelta(days=avg)
        due = (nxt - now).days
        if 0 <= due <= 30:
            u = conn.execute("SELECT display_name,membership_level FROM users WHERE phone=?", (phone,)).fetchone()
            preds.append({
                'phone': phone,
                'name': u['display_name'] if u else '',
                'level': (u['membership_level'] if u else '') or '普卡',
                'last_buy': ts[-1][:10], 'avg_gap': round(avg, 1),
                'predict_next': nxt.strftime('%Y-%m-%d'), 'due_in': due
            })
    preds.sort(key=lambda x: x['due_in'])
    conn.close()
    return jsonify(ok=True, data={'total': len(preds), 'list': preds[:200]})

# 3) 高价值会员管家（按消费额 Top N）
@app.route('/api/admin/high-value', methods=['GET'])
@login_required
def api_admin_high_value():
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    tid = session.get('tenant_id', 1)
    conn = get_db(); _ensure_tables(conn)
    members = conn.execute(
        "SELECT phone,display_name,membership_level,last_visit,points,birthday,preferred_category FROM users WHERE tenant_id=? AND role='user'",
        (tid,)).fetchall()
    cons = conn.execute("SELECT phone, COUNT(*) cnt, COALESCE(SUM(amount),0) amt FROM member_consumptions GROUP BY phone").fetchall()
    cons_map = {c['phone']: (c['cnt'], c['amt']) for c in cons}
    rows = []
    for m in members:
        freq, mon = cons_map.get(m['phone'], (0, 0))
        if mon <= 0:
            continue
        R, F, M, seg, churn = _rfm_scores(m['last_visit'], freq, mon)
        rows.append({
            'phone': m['phone'], 'name': m['display_name'] or '会员',
            'level': m['membership_level'] or '普卡', 'monetary': round(mon, 2),
            'freq': freq, 'points': m['points'], 'segment': seg, 'last_visit': m['last_visit'],
            'pref': m['preferred_category'] or '', 'birthday': m['birthday'] or ''
        })
    rows.sort(key=lambda x: x['monetary'], reverse=True)
    conn.close()
    return jsonify(ok=True, data={'total': len(rows), 'list': rows[:20]})

# 4) 等级跃迁冲刺（接近下一等级门槛的会员）
@app.route('/api/admin/tier-sprint', methods=['GET'])
@login_required
def api_admin_tier_sprint():
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    tid = session.get('tenant_id', 1)
    conn = get_db(); _ensure_tables(conn)
    members = conn.execute(
        "SELECT phone,display_name,membership_level,points FROM users WHERE tenant_id=? AND role='user'",
        (tid,)).fetchall()
    rows = []
    for m in members:
        lvl = m['membership_level'] or '普卡'
        np_ = _NEXT_POINTS.get(lvl)
        if not np_:
            continue
        gap = np_ - (m['points'] or 0)
        if gap <= 0 or gap > np_ * 0.4:
            continue
        rows.append({
            'phone': m['phone'], 'name': m['display_name'] or '会员', 'level': lvl,
            'points': m['points'] or 0, 'next_level': _next_level_name(lvl),
            'next_points': np_, 'gap': gap, 'progress': round((m['points'] or 0) / np_ * 100, 1)
        })
    rows.sort(key=lambda x: x['progress'], reverse=True)
    conn.close()
    return jsonify(ok=True, data={'total': len(rows), 'list': rows[:100]})

def _next_level_name(lvl):
    order = ['普卡', '银卡', '金卡', '铂金卡', '钻石卡', '黑钻卡']
    try:
        i = order.index(lvl)
        return order[i+1] if i+1 < len(order) else '黑钻卡'
    except Exception:
        return '银卡'

# 5) 差评实时告警 + 跟进
@app.route('/api/admin/feedback/alerts', methods=['GET'])
@login_required
def api_admin_feedback_alerts():
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    conn = get_db(); _ensure_tables(conn)
    conn.execute('''CREATE TABLE IF NOT EXISTS feedback_followups (
        id INTEGER PRIMARY KEY AUTOINCREMENT, feedback_id INTEGER NOT NULL,
        note TEXT DEFAULT '', at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    rows = conn.execute(
        "SELECT id, user_phone, feedback_type, rating, feedback_text, created_at FROM feedbacks ORDER BY id DESC LIMIT 100").fetchall()
    foll = {r['feedback_id']: r['at'] for r in conn.execute("SELECT feedback_id, at FROM feedback_followups").fetchall()}
    alerts = []
    now = datetime.now()
    for r in rows:
        if r['rating'] is not None and r['rating'] <= 2:
            try:
                age_h = int((now - datetime.strptime(r['created_at'][:19], '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600)
            except Exception:
                age_h = -1
            alerts.append({
                'id': r['id'], 'phone': r['user_phone'], 'type': r['feedback_type'],
                'rating': r['rating'], 'text': r['feedback_text'], 'created_at': r['created_at'],
                'age_hours': age_h, 'followed_at': foll.get(r['id'])
            })
    alerts.sort(key=lambda x: x['age_hours'] if x['age_hours'] >= 0 else 9999)
    conn.close()
    return jsonify(ok=True, data={'total': len(alerts), 'list': alerts[:50]})

@app.route('/api/admin/feedback/alerts/follow', methods=['POST'])
@login_required
def api_admin_feedback_follow():
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    data = request.get_json() or {}
    fid = data.get('feedback_id')
    note = (data.get('note') or '').strip()
    if not fid:
        return jsonify(ok=False, error='缺少 feedback_id')
    conn = get_db(); _ensure_tables(conn)
    conn.execute('''CREATE TABLE IF NOT EXISTS feedback_followups (
        id INTEGER PRIMARY KEY AUTOINCREMENT, feedback_id INTEGER NOT NULL,
        note TEXT DEFAULT '', at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.execute("INSERT INTO feedback_followups(feedback_id, note) VALUES(?,?)", (fid, note))
    conn.commit(); conn.close()
    return jsonify(ok=True)

# 6) 痛点根因聚类
@app.route('/api/admin/feedback/painpoints', methods=['GET'])
@login_required
def api_admin_feedback_painpoints():
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    conn = get_db(); _ensure_tables(conn)
    rows = conn.execute("SELECT id, feedback_text, rating, created_at FROM feedbacks ORDER BY id DESC LIMIT 200").fetchall()
    conn.close()
    from collections import Counter
    topic_cnt = Counter()
    items = []
    for r in rows:
        s, tp = _sentiment_heuristic(r['feedback_text'], r['rating'])
        if s in ('负面', '投诉'):
            for t in (tp if isinstance(tp, list) else [tp]):
                topic_cnt[t] += 1
            items.append({'id': r['id'], 'topic': tp, 'text': r['feedback_text']})
    ranked = [{'topic': t, 'count': c} for t, c in topic_cnt.most_common()]
    return jsonify(ok=True, data={'total': len(items), 'ranked': ranked, 'list': items[:50]})

# 7) 商户 / 品类情感榜（按真实商户 shop_id 维度，JOIN shops）
@app.route('/api/admin/feedback/merchant-sentiment', methods=['GET'])
@login_required
def api_admin_feedback_merchant_sentiment():
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    conn = get_db(); _ensure_tables(conn)
    rows = conn.execute(
        "SELECT f.shop_id, f.rating, f.feedback_text, s.name, s.category, s.floor, s.zone "
        "FROM feedbacks f LEFT JOIN shops s ON f.shop_id = s.id").fetchall()
    conn.close()
    agg = {}
    for r in rows:
        sid = (r['shop_id'] or '').strip()
        if not sid:
            dim = '未关联商户'
        else:
            dim = r['name'] or r['shop_id']
        a = agg.setdefault(sid or 'none', {'shop_id': sid, 'shop_name': dim,
                                           'category': r['category'] or '', 'floor': r['floor'] or '',
                                           'zone': r['zone'] or '', 'cnt': 0, 'sum': 0, 'neg': 0})
        a['cnt'] += 1
        a['sum'] += (r['rating'] or 0)
        s, tp = _sentiment_heuristic(r['feedback_text'], r['rating'])
        if s in ('负面', '投诉'):
            a['neg'] += 1
    out = []
    for a in agg.values():
        avg = round(a['sum'] / a['cnt'], 2) if a['cnt'] else 0
        out.append({'shop_id': a['shop_id'], 'shop_name': a['shop_name'], 'category': a['category'],
                    'floor': a['floor'], 'zone': a['zone'], 'cnt': a['cnt'], 'avg_rating': avg,
                    'neg_rate': round(a['neg'] / a['cnt'] * 100, 1) if a['cnt'] else 0,
                    'neg': a['neg']})
    out.sort(key=lambda x: (x['neg_rate'], x['cnt']), reverse=True)
    # 品类维度汇总
    cat_agg = {}
    for o in out:
        if o['shop_id'] == '未关联商户' or not o['category']:
            continue
        c = cat_agg.setdefault(o['category'], {'category': o['category'], 'cnt': 0, 'sum': 0, 'neg': 0})
        c['cnt'] += o['cnt']; c['sum'] += o['cnt'] * o['avg_rating']; c['neg'] += o['neg']
    cat_out = []
    for c in cat_agg.values():
        cat_out.append({'category': c['category'], 'cnt': c['cnt'],
                        'avg_rating': round(c['sum'] / c['cnt'], 2) if c['cnt'] else 0,
                        'neg_rate': round(c['neg'] / c['cnt'] * 100, 1) if c['cnt'] else 0})
    cat_out.sort(key=lambda x: x['neg_rate'], reverse=True)
    return jsonify(ok=True, data={'list': out, 'by_category': cat_out, 'real': True})

# 8) 口碑周趋势 + NPS
@app.route('/api/admin/feedback/trend', methods=['GET'])
@login_required
def api_admin_feedback_trend():
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    conn = get_db(); _ensure_tables(conn)
    rows = conn.execute("SELECT rating, created_at FROM feedbacks WHERE created_at >= date('now','-56 days')").fetchall()
    conn.close()
    from collections import defaultdict
    by_week = defaultdict(lambda: {'cnt': 0, 'sum': 0, 'prom': 0, 'detr': 0})
    for r in rows:
        try:
            wk = datetime.strptime(r['created_at'][:10], '%Y-%m-%d').strftime('%Y-%W')
        except Exception:
            continue
        b = by_week[wk]
        b['cnt'] += 1
        b['sum'] += (r['rating'] or 0)
        if (r['rating'] or 0) >= 4:
            b['prom'] += 1
        elif (r['rating'] or 0) <= 2:
            b['detr'] += 1
    weeks = []
    for wk in sorted(by_week.keys()):
        b = by_week[wk]
        nps = round((b['prom'] - b['detr']) / b['cnt'] * 100) if b['cnt'] else 0
        weeks.append({'week': wk, 'cnt': b['cnt'], 'avg_rating': round(b['sum']/b['cnt'], 2) if b['cnt'] else 0, 'nps': nps})
    return jsonify(ok=True, data={'weeks': weeks})

# 9) 周报 / 月报
@app.route('/api/admin/report-period', methods=['GET'])
@login_required
def api_admin_report_period():
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    period = request.args.get('period', 'weekly')
    tid = session.get('tenant_id', 1)
    conn = get_db(); _ensure_tables(conn)
    now = datetime.now()
    if period == 'monthly':
        start = (now.replace(day=1)).strftime('%Y-%m-%d %H:%M:%S')
        label = now.strftime('%Y-%m') + ' 月报'
    else:
        start = (now - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        label = '近 7 天周报'
    total_members = conn.execute("SELECT COUNT(*) FROM users WHERE tenant_id=? AND role='user'", (tid,)).fetchone()[0]
    new_m = conn.execute("SELECT COUNT(*) FROM users WHERE tenant_id=? AND role='user' AND created_at >= ?", (tid, start)).fetchone()[0]
    active = conn.execute("SELECT COUNT(*) FROM users WHERE tenant_id=? AND role='user' AND last_visit >= ?", (tid, start)).fetchone()[0]
    coupons = conn.execute("SELECT COUNT(*) FROM coupon_claims WHERE claimed_at >= ?", (start,)).fetchone()[0]
    acts = conn.execute("SELECT COUNT(*) FROM activities WHERE status='open'").fetchone()[0]
    fb_total = conn.execute("SELECT COUNT(*) FROM feedbacks WHERE created_at >= ?", (start,)).fetchone()[0]
    fb_avg = conn.execute("SELECT AVG(rating) FROM feedbacks WHERE created_at >= ?", (start,)).fetchone()[0]
    fb_low = conn.execute("SELECT COUNT(*) FROM feedbacks WHERE created_at >= ? AND rating <= 2", (start,)).fetchone()[0]
    conn.close()
    metrics = {'period': period, 'total_members': total_members, 'new_members': new_m,
               'active_members': active, 'coupons': coupons, 'activities_open': acts,
               'feedback_total': fb_total, 'feedback_avg': round(fb_avg, 2) if fb_avg else 0, 'low_feedback': fb_low}
    engine = 'heuristic'
    report = ''
    if DS_API_KEY:
        prompt = (f"你是商场运营助手，请基于以下{label}数据写一段 180 字内的中文经营分析：先总评，再 3 条发现与建议（用 • 开头）。只输出正文。\n"
                  f"会员总数 {total_members}，本期新增 {new_m}、活跃 {active}；券领取 {coupons} 张；进行中活动 {acts} 个；评价 {fb_total} 条、均分 {metrics['feedback_avg']}、差评 {fb_low} 条。")
        out = ai_text([{'role': 'system', 'content': '你是专业商场运营分析师。'}, {'role': 'user', 'content': prompt}], max_tokens=500)
        if out:
            report = out; engine = 'llm'
    if not report:
        report = (f"【海江新天地{label}】\n"
                  f"• 会员总数 {total_members}，本期新增 {new_m}、活跃 {active}。\n"
                  f"• 券领取 {coupons} 张，进行中活动 {acts} 个，可加大会员日曝光。\n"
                  f"• 评价 {fb_total} 条、均分 {metrics['feedback_avg']}、差评 {fb_low} 条"
                  + ("，请跟进差评服务卡点。" if fb_low else "，口碑平稳。"))
    return jsonify(ok=True, data={'engine': engine, 'label': label, 'report': report, 'metrics': metrics})

# 10) 异常指标自动预警
@app.route('/api/admin/anomaly', methods=['GET'])
@login_required
def api_admin_anomaly():
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    tid = session.get('tenant_id', 1)
    conn = get_db(); _ensure_tables(conn)
    today = datetime.now().strftime('%Y-%m-%d')
    yest = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    wk_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    t_new = conn.execute("SELECT COUNT(*) FROM users WHERE tenant_id=? AND role='user' AND DATE(created_at)=?", (tid, today)).fetchone()[0]
    a_new = conn.execute("SELECT COUNT(*) FROM users WHERE tenant_id=? AND role='user' AND created_at>=?", (tid, wk_ago)).fetchone()[0] / 7.0
    t_act = conn.execute("SELECT COUNT(*) FROM users WHERE tenant_id=? AND role='user' AND last_visit>=?", (tid, today + ' 00:00:00')).fetchone()[0]
    a_act = conn.execute("SELECT COUNT(*) FROM users WHERE tenant_id=? AND role='user' AND last_visit>=?", (tid, wk_ago)).fetchone()[0] / 7.0
    t_cou = conn.execute("SELECT COUNT(*) FROM coupon_claims WHERE DATE(claimed_at)=?", (today,)).fetchone()[0]
    a_cou = conn.execute("SELECT COUNT(*) FROM coupon_claims WHERE claimed_at>=?", (wk_ago,)).fetchone()[0] / 7.0
    t_fb = conn.execute("SELECT COUNT(*) FROM feedbacks WHERE DATE(created_at)=?", (today,)).fetchone()[0]
    a_fb = conn.execute("SELECT COUNT(*) FROM feedbacks WHERE created_at>=?", (wk_ago,)).fetchone()[0] / 7.0
    t_low = conn.execute("SELECT COUNT(*) FROM feedbacks WHERE DATE(created_at)=? AND rating<=2", (today,)).fetchone()[0]
    a_low = conn.execute("SELECT COUNT(*) FROM feedbacks WHERE created_at>=? AND rating<=2", (wk_ago,)).fetchone()[0] / 7.0
    conn.close()
    checks = [
        ('新增会员', t_new, a_new), ('活跃会员', t_act, a_act),
        ('券领取', t_cou, a_cou), ('评价数', t_fb, a_fb), ('差评数', t_low, a_low)
    ]
    alerts = []
    for name, t, a in checks:
        if a and t <= a * 0.6:
            pct = round((t - a) / a * 100)
            alerts.append({'metric': name, 'today': t, 'avg': round(a, 1), 'pct': pct,
                           'level': 'high' if t <= a * 0.4 else 'mid'})
    return jsonify(ok=True, data={'alerts': alerts, 'checked': [c[0] for c in checks]})

# 11) KPI 目标完成率
@app.route('/api/admin/kpi', methods=['GET'])
@login_required
def api_admin_kpi():
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    tid = session.get('tenant_id', 1)
    conn = get_db(); _ensure_tables(conn)
    conn.execute('CREATE TABLE IF NOT EXISTS kpi_targets (metric TEXT PRIMARY KEY, target REAL)')
    defaults = {'new_members_week': 20, 'active_members_week': 8, 'churn_risk_members': 5,
                'coupons_today': 10, 'feedback_avg': 4.5}
    for k, v in defaults.items():
        conn.execute("INSERT OR IGNORE INTO kpi_targets(metric,target) VALUES(?,?)", (k, v))
    targets = {r['metric']: r['target'] for r in conn.execute("SELECT metric,target FROM kpi_targets").fetchall()}
    now = datetime.now(); wk_ago = (now - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    today = now.strftime('%Y-%m-%d')
    cur = {
        'new_members_week': conn.execute("SELECT COUNT(*) FROM users WHERE tenant_id=? AND role='user' AND created_at>=?", (tid, wk_ago)).fetchone()[0],
        'active_members_week': conn.execute("SELECT COUNT(*) FROM users WHERE tenant_id=? AND role='user' AND last_visit>=?", (tid, wk_ago)).fetchone()[0],
        'churn_risk_members': conn.execute("SELECT COUNT(*) FROM users WHERE tenant_id=? AND role='user' AND (last_visit IS NULL OR last_visit='' OR last_visit<=?)", (tid, (now - timedelta(days=90)).strftime('%Y-%m-%d %H:%M:%S'))).fetchone()[0],
        'coupons_today': conn.execute("SELECT COUNT(*) FROM coupon_claims WHERE DATE(claimed_at)=?", (today,)).fetchone()[0],
        'feedback_avg': conn.execute("SELECT AVG(rating) FROM feedbacks").fetchone()[0] or 0
    }
    conn.close()
    out = []
    for k, target in targets.items():
        val = cur.get(k, 0)
        comp = round(val / target * 100) if target else 0
        out.append({'metric': k, 'current': val, 'target': target, 'completion': comp})
    return jsonify(ok=True, data={'list': out})

@app.route('/api/admin/kpi', methods=['POST'])
@login_required
def api_admin_kpi_update():
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    data = request.get_json() or {}
    metric = data.get('metric'); target = data.get('target')
    if not metric or target is None:
        return jsonify(ok=False, error='缺少参数')
    conn = get_db(); _ensure_tables(conn)
    conn.execute('CREATE TABLE IF NOT EXISTS kpi_targets (metric TEXT PRIMARY KEY, target REAL)')
    conn.execute("INSERT OR REPLACE INTO kpi_targets(metric,target) VALUES(?,?)", (metric, float(target)))
    conn.commit(); conn.close()
    return jsonify(ok=True)

# 12) 活动 ROI 估算
@app.route('/api/admin/activity-roi', methods=['GET'])
@login_required
def api_admin_activity_roi():
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    conn = get_db(); _ensure_tables(conn)
    rows = conn.execute("SELECT id,title,venue,start_date,end_date,price,points_price,max_people,enrolled,status,offer_ids,budget FROM activities").fetchall()
    # 该活动绑定券的真实核销金额
    redeem_rows = conn.execute(
        "SELECT offer_id, SUM(redeem_amount) AS amt, COUNT(*) AS cnt FROM coupon_claims "
        "WHERE redeemed=1 AND offer_id IS NOT NULL AND offer_id<>'' GROUP BY offer_id").fetchall()
    redeem_map = {r['offer_id']: {'amt': r['amt'] or 0, 'cnt': r['cnt'] or 0} for r in redeem_rows}
    conn.close()
    out = []
    for r in rows:
        price = r['price'] or 0
        pp = r['points_price'] or 0
        enrolled = r['enrolled'] or 0
        maxp = r['max_people'] or 0
        budget = r['budget'] or 0
        offer_ids = [o.strip() for o in (r['offer_ids'] or '').split(',') if o.strip()]
        real_redeem = sum(redeem_map.get(o, {'amt': 0})['amt'] for o in offer_ids)
        redeem_cnt = sum(redeem_map.get(o, {'cnt': 0})['cnt'] for o in offer_ids)
        # 真实成本：填了预算用预算；否则按报名人数×客单价估算成本
        cost = budget if budget > 0 else (enrolled * max(price, pp * 0.1))
        roi = round(real_redeem / cost, 2) if cost > 0 else 0
        out.append({
            'id': r['id'], 'title': r['title'], 'venue': r['venue'], 'status': r['status'],
            'enrolled': enrolled, 'max_people': maxp,
            'full_rate': round(enrolled / maxp * 100, 1) if maxp else 0,
            'budget': budget, 'offer_ids': offer_ids,
            'redeem_amount': round(real_redeem, 0), 'redeem_count': redeem_cnt,
            'roi': roi, 'cost': round(cost, 0),
            'real': bool(offer_ids and real_redeem > 0)
        })
    out.sort(key=lambda x: (x['real'], x['redeem_amount']), reverse=True)
    return jsonify(ok=True, data={'list': out})

# 13) AI 推送文案生成
@app.route('/api/admin/push-copy', methods=['POST'])
@login_required
def api_admin_push_copy():
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    data = request.get_json() or {}
    segment = data.get('segment', '会员')
    theme = data.get('theme', '回馈')
    channel = data.get('channel', '短信')
    engine = 'heuristic'
    copy = ''
    if DS_API_KEY:
        prompt = f"你是商场会员运营文案高手。面向「{segment}」会员，渠道「{channel}」，主题「{theme}」。请写一条 60 字内的推送文案，口语化、有钩子、带行动号召，不要标点堆砌。"
        out = ai_text([{'role': 'system', 'content': '你是资深会员运营文案专家。'}, {'role': 'user', 'content': prompt}], max_tokens=200)
        if out:
            copy = out; engine = 'llm'
    if not copy:
        copy = f"【海江新天地】亲爱的{segment}会员：{theme}专属福利已就位，戳进来领走你的专属惊喜>>退订回T"
    return jsonify(ok=True, data={'engine': engine, 'copy': copy, 'segment': segment, 'channel': channel})

# 14) 经营参谋（自然语言问答）
@app.route('/api/admin/advisor', methods=['POST'])
@login_required
def api_admin_advisor():
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    data = request.get_json() or {}
    q = (data.get('question') or '').strip()
    if not q:
        return jsonify(ok=False, error='缺少问题')
    tid = session.get('tenant_id', 1)
    conn = get_db(); _ensure_tables(conn)
    total = conn.execute("SELECT COUNT(*) FROM users WHERE tenant_id=? AND role='user'", (tid,)).fetchone()[0]
    churn = conn.execute("SELECT COUNT(*) FROM users WHERE tenant_id=? AND role='user' AND (last_visit IS NULL OR last_visit<=?)", (tid, (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d %H:%M:%S'))).fetchone()[0]
    fb_low = conn.execute("SELECT COUNT(*) FROM feedbacks WHERE rating<=2").fetchone()[0]
    fb_avg = conn.execute("SELECT AVG(rating) FROM feedbacks").fetchone()[0] or 0
    conn.close()
    ctx = f"会员总数{total}，流失风险{churn}人，差评{fb_low}条，评价均分{round(fb_avg,2)}。"
    engine = 'heuristic'
    ans = ''
    if DS_API_KEY:
        prompt = f"你是商场经营参谋。已知数据：{ctx}。用户问题：{q}。请基于数据用中文简洁回答（3 句内），不知道就明说。"
        out = ai_text([{'role': 'system', 'content': '你是严谨的商场经营分析参谋。'}, {'role': 'user', 'content': prompt}], max_tokens=300)
        if out:
            ans = out; engine = 'llm'
    if not ans:
        if '流失' in q:
            ans = f"当前流失风险会员约 {churn} 人，建议对沉睡会员推送「回来看看」定向券。"
        elif '差评' in q or '投诉' in q:
            ans = f"近期差评 {fb_low} 条，评价均分 {round(fb_avg,2)}，建议查看「差评实时告警」跟进。"
        else:
            ans = '暂无可回答的数据维度，可问：流失会员多少？差评情况？会员总规模？'
    return jsonify(ok=True, data={'engine': engine, 'answer': ans, 'context': ctx})

# 15) 智能招商建议
@app.route('/api/admin/leasing', methods=['GET'])
@login_required
def api_admin_leasing():
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    conn = get_db(); _ensure_tables(conn)
    shops = conn.execute("SELECT category FROM shops").fetchall()
    fbs = conn.execute("SELECT biz_type, feedback_text, rating FROM feedbacks").fetchall()
    conn.close()
    from collections import Counter
    cat_cnt = Counter((s['category'] or '其他') for s in shops)
    topic_cnt = Counter()
    for f in fbs:
        s, tp = _sentiment_heuristic(f['feedback_text'], f['rating'])
        for t in (tp if isinstance(tp, list) else [tp]):
            topic_cnt[t] += 1
    # 好评主题但对应品类门店少 → 招商机会
    suggest = []
    for topic, cnt in topic_cnt.most_common():
        have = cat_cnt.get(topic, 0)
        if cnt >= 2 and have <= 1:
            suggest.append({'category': topic, 'demand': cnt, 'shops_now': have, 'advice': '需求高但供给少，建议招商引进'})
    # 门店多但无评价/低关注的品类提示
    return jsonify(ok=True, data={'shop_category_dist': dict(cat_cnt), 'topic_demand': dict(topic_cnt), 'suggestions': suggest})

# 16) 营销日历（未来 14 天触达点）
@app.route('/api/admin/marketing-calendar', methods=['GET'])
@login_required
def api_admin_marketing_calendar():
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    tid = session.get('tenant_id', 1)
    conn = get_db(); _ensure_tables(conn)
    users = conn.execute("SELECT display_name,birthday,anniversary FROM users WHERE tenant_id=? AND role='user'", (tid,)).fetchall()
    acts = conn.execute("SELECT title,start_date,end_date,status FROM activities WHERE status='open'").fetchall()
    conn.close()
    now = datetime.now()
    events = []
    for d in range(0, 14):
        day = now + timedelta(days=d)
        mmdd = day.strftime('%m-%d')
        for u in users:
            for fld, kind in (('birthday', '生日权益日'), ('anniversary', '周年庆权益日')):
                v = u[fld] or ''
                if len(v) >= 5 and v[-5:] == mmdd:
                    events.append({'date': day.strftime('%Y-%m-%d'), 'type': kind, 'member': u['display_name'] or '会员'})
        if day.weekday() == 2:  # 周三会员日
            events.append({'date': day.strftime('%Y-%m-%d'), 'type': '周三会员日', 'member': '全量会员'})
        for a in acts:
            sd = (a['start_date'] or '')[:10]
            if sd == day.strftime('%Y-%m-%d'):
                events.append({'date': sd, 'type': '活动开始', 'member': a['title']})
    events.sort(key=lambda x: x['date'])
    return jsonify(ok=True, data={'events': events[:60], 'total': len(events)})

# 17) 时段冷热热力（按消费记录小时分布）
@app.route('/api/admin/timeslot-heat', methods=['GET'])
@login_required
def api_admin_timeslot_heat():
    if not _admin_role_ok():
        return jsonify(ok=False, error='权限不足')
    conn = get_db(); _ensure_tables(conn)
    heat = [0] * 24
    total = 0
    # 真实到店信号：会员签到(sign_in_records)、每日打卡(daily_checkins)、消费(member_consumptions)
    sources = []
    for sql, col in [
        ("SELECT created_at FROM sign_in_records", 'created_at'),
        ("SELECT created_at FROM member_consumptions", 'created_at'),
    ]:
        try:
            rows = conn.execute(sql).fetchall()
            for r in rows:
                ts = r[col] or ''
                if len(ts) >= 13:
                    try:
                        heat[int(ts[11:13])] += 1; total += 1
                    except Exception:
                        pass
            sources.append(sql.split('FROM')[1].strip())
        except Exception:
            pass
    # daily_checkins 可能用 sign_date/created_at，容错读取
    try:
        for col in ('created_at', 'sign_date'):
            try:
                rows = conn.execute(f"SELECT {col} FROM daily_checkins").fetchall()
                for r in rows:
                    ts = r[col] or ''
                    if len(ts) >= 13:
                        try:
                            heat[int(ts[11:13])] += 1; total += 1
                        except Exception:
                            pass
                sources.append('daily_checkins')
                break
            except Exception:
                continue
    except Exception:
        pass
    conn.close()
    peak = max(range(24), key=lambda i: heat[i]) if any(heat) else -1
    return jsonify(ok=True, data={
        'heat': heat, 'peak_hour': peak, 'total': total,
        'sources': sources, 'real': True
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
            add_points(phone, 5, 'join_club', '加入兴趣社#' + str(club_id), conn)
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
    add_points(phone, 5, 'join_club_event', '加入活动群#' + str(eid), conn)
    joined = conn.execute("SELECT COUNT(*) FROM club_event_members WHERE event_id=?", (eid,)).fetchone()[0]
    conn.commit()
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
    add_points(phone, 2, 'club_event_msg', '活动群留言#' + str(eid), conn)
    conn.commit()
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

