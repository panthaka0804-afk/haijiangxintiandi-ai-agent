# -*- coding: utf-8 -*-
"""大橘大利系统 - 社区商业AI客服"""
import os, sys, json, sqlite3, hashlib, secrets, re, time, io, base64, subprocess, tempfile
from datetime import datetime
from functools import wraps
from flask import Flask, request, session, jsonify, send_from_directory
from openai import OpenAI
import floor_data

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

def _call_deepseek(messages, max_tokens=600):
    """用 curl 调 DeepSeek（绕过 Python SSL 问题）"""
    import tempfile
    payload = json.dumps({
        'model': 'deepseek-chat',
        'messages': messages,
        'max_tokens': max_tokens,
        'temperature': 0.7
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
            return True, resp['choices'][0]['message']['content']
        return False, resp.get('error', {}).get('message', str(resp))
    except Exception as e:
        return False, str(e)
    finally:
        try: os.unlink(tmp.name)
        except: pass

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

【积分/兑换】优先推荐性价比最高的兑换（价值÷积分最大）。可兑换：1停车券500分 2美食券800分 3星巴克1000分 4电影票2000分 5蜀大侠3000分 6乐园5000分 7棒约翰8000分 8购物卡10000分 9火锅15000分。"确认兑换N"→告知已记录请小程序操作。

【会员】有手机号就查，没注册就说"回复我要注册即可开通，送500积分"。绝不回复"去服务台"。

【检索导航】找优惠/找活动/找店铺/找商品/导航——代码已本地处理，AI只需友好回复检索结果。

你是海江新天地最暖心的小江~'''

CHAT_HISTORY = {}
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
        return '积分商城可兑换：\n1停车券500分 2美食券800分 3星巴克1000分\n4电影票2000分 5蜀大侠3000分 6乐园5000分\n7棒约翰8000分 8购物卡10000分 9火锅15000分\n\n回复"确认兑换+编号"来兑换，比如"确认兑换3"换星巴克嘛~\n也可以点击下方按钮去积分商城 👇'

    # 营业时间
    if any(w in m for w in ('营业时间','几点开门','几点关门','营业到几点','什么时候开门')):
        return '海江新天地营业时间：周一至周日 10:00-22:00~个别商户可能稍有不同，用餐和玩都要趁早哦！'

    # 停车场
    if any(w in m for w in ('停车','停车场','车位','停车费','停车怎么收','停车收费')):
        return '海江新天地有800+智能车位~\n收费标准：\n· 前30分钟免费\n· 5元/小时，40元/天封顶\n· 会员消费满50元免费停2小时\n· 夜场18:00-次日08:00 10元/次\n\n点击下方按钮去车辆管理绑定车牌~'

    return None

def web_search_inject(query):
    try:
        import urllib.request, urllib.parse
        url = 'https://api.duckduckgo.com/?q=' + urllib.parse.quote(query) + '&format=json&no_html=1&skip_disambig=1'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        parts = []
        if data.get('AbstractText'):
            parts.append(data['AbstractText'])
        for t in data.get('RelatedTopics', [])[:3]:
            if t.get('Text'):
                parts.append(t['Text'])
        text = ' '.join(parts)
        if len(text) > 20:
            return "\n【网络搜索结果】" + text[:600]
    except:
        pass
    return ""

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
        return jsonify(ok=True, user={
            'id': uid,
            'tenant_id': session['tenant_id'],
            'role': session.get('role'),
            'display_name': session.get('display_name'),
            'phone': phone,
            'headimgurl': headimgurl
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
    # 使用 session cookie 作为匿名 key
    sid = request.cookies.get('session', 'anonymous')
    # tenant 固定为 1
    return _do_chat(1, sid, user_input)

def _do_chat(tid, uid, user_input):
    chat_key = str(tid) + ':' + str(uid)
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
                        2: ('B1美食满50减10券', 800, 'B1CP'),
                        3: ('星巴克饮品券', 1000, 'SBUX'),
                        4: ('电影票', 2000, 'MOVI'),
                        5: ('蜀大侠100元券', 3000, 'SDX'),
                        6: ('亲子乐园门票', 5000, 'PARK'),
                        7: ('棒约翰双人餐', 8000, 'PAPA'),
                        8: ('200元购物卡', 10000, 'CARD'),
                        9: ('蜀大侠4人火锅', 15000, 'SDX4'),
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
            member_hint += '积分商城可兑礼品参考：500停车券/1000星巴克/3000蜀大侠100元券/5000亲子乐园/10000购物卡/15000火锅套餐。请基于此会员等级进行算价，提醒积分使用建议。'
        else:
            member_hint = f'\n【会员查询结果】手机号{phone}未注册。请直接引导用户在此对话中回复"我要注册"即可开通会员，赠送500积分。绝对不能回复"去服务台注册"。'
    kb_block = ''
    if kb_results:
        kb_block = '\n【知识库匹配】'
        for r in kb_results:
            kb_block += f'\n[{r["category"]}] {r["question"]}: {r["answer"][:300]}'
    web_block = web_search_inject(user_input)
    sp = SYSTEM_PROMPT + '\n当前时间: ' + datetime.now().strftime('%Y-%m-%d %H:%M') + kb_block + web_block
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
        ok, result = _call_deepseek(messages, max_tokens=600)
        if ok:
            reply = result
        else:
            raise Exception(result)
    except Exception:
        # DeepSeek 失败 → 情感关键词温暖回复优先
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
            kb = kb_search(tid, user_input, limit=3)
            if kb:
                reply = '\n'.join([f'[{r["category"]}] {r["answer"][:200]}' for r in kb[:3]])
                if len(reply) < 20:
                    reply = '抱歉，小江暂时没找到相关信息，你可以换个问法试试~'
            elif any(w in user_input for w in ['你好','嗨','hi','hello']):
                reply = '嗨！我是小江，海江新天地的客服助手~\n想找店铺、查优惠、问路、看活动，尽管问我！'
            else:
                reply = '哎呀，小江的脑子有点转不过来...要不你重新说一遍？'
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
    return jsonify(ok=True, reply=reply)

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
    conn = get_db()
    sql = "SELECT * FROM work_orders"
    params = []
    if status:
        sql += " WHERE status=?"
        params.append(status)
    count = conn.execute("SELECT COUNT(*) FROM (" + sql + ")", params).fetchone()[0]
    rows = conn.execute(sql + " ORDER BY created_at DESC LIMIT ? OFFSET ?", params + [limit, (page-1)*limit]).fetchall()
    conn.close()
    items = [dict(r) for r in rows]
    return jsonify(ok=True, items=items, total=count)

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
        {'id': 2, 'name': 'B1美食满减券', 'cost': 800, 'value': 10},
        {'id': 3, 'name': '星巴克饮品券', 'cost': 1000, 'value': 35},
        {'id': 4, 'name': '电影票', 'cost': 2000, 'value': 60},
        {'id': 5, 'name': '蜀大侠100元券', 'cost': 3000, 'value': 100},
        {'id': 6, 'name': '亲子乐园门票', 'cost': 5000, 'value': 128},
        {'id': 7, 'name': '棒约翰双人餐', 'cost': 8000, 'value': 156},
        {'id': 8, 'name': '200元购物卡', 'cost': 10000, 'value': 200},
        {'id': 9, 'name': '蜀大侠4人火锅', 'cost': 15000, 'value': 368},
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
        2: {'name': 'B1美食满50减10券', 'cost': 800, 'code_prefix': 'B1CP', 'desc': 'B1美食广场满50减10'},
        3: {'name': '星巴克饮品券', 'cost': 1000, 'code_prefix': 'SBUX', 'desc': '中杯饮品一杯'},
        4: {'name': '电影票', 'cost': 2000, 'code_prefix': 'MOVI', 'desc': '通用电影票一张'},
        5: {'name': '蜀大侠100元券', 'cost': 3000, 'code_prefix': 'SDX', 'desc': '蜀大侠消费抵用100元'},
        6: {'name': '亲子乐园门票', 'cost': 5000, 'code_prefix': 'PARK', 'desc': '3F儿童乐园门票一张'},
        7: {'name': '棒约翰双人餐', 'cost': 8000, 'code_prefix': 'PAPA', 'desc': '棒约翰双人套餐券'},
        8: {'name': '200元购物卡', 'cost': 10000, 'code_prefix': 'CARD', 'desc': '大橘邻里全场通用购物卡'},
        9: {'name': '蜀大侠4人火锅', 'cost': 15000, 'code_prefix': 'SDX4', 'desc': '蜀大侠4人火锅套餐券'},
    }

    cat = redeem_catalog.get(redeem_id)
    if not cat:
        conn.close()
        return jsonify(ok=False, error='无效的兑换项目，可用ID：1=停车券 2=美食券 3=星巴克 4=电影票 5=蜀大侠券 6=乐园 7=棒约翰 8=购物卡 9=火锅套餐')

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
    for f in ['name','contact','plan','monthly_quota','status']:
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
    if sess[5] + count > sess[4]:
        conn.close()
        return jsonify(ok=False, error=f'名额不足，剩余{sess[4]-sess[5]}个位置'), 400

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
        if user[5] < need_points:
            conn.close()
            return jsonify(ok=False, error=f'积分不足，需要{need_points}分，当前{user[5]}分'), 400
        points_used = need_points
        amount = 0
    elif pay_method == 'pay':
        if amount > 0 and user:
            # 会员折扣
            discount = 0.98
            if user[9] == '银卡': discount = 0.95
            elif user[9] == '金卡': discount = 0.9
            elif user[9] == '钻石卡': discount = 0.88
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
    c.execute('''SELECT r.*, a.title as activity_title, s.session_date, s.session_time
                 FROM registrations r
                 LEFT JOIN activities a ON r.activity_id = a.id
                 LEFT JOIN activity_sessions s ON r.session_id = s.id
                 WHERE r.user_phone = ?
                 ORDER BY r.created_at DESC''', (phone,))
    rows = c.fetchall()
    cols = ['id','registration_no','activity_id','session_id','user_phone','user_name','people_count','amount','pay_method','points_used','status','ticket_code','created_at','updated_at','activity_title','session_date','session_time']
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
    if reg[9] == 'cancelled':
        conn.close()
        return jsonify(ok=False, error='已取消的订单不能改签'), 400
    # 减少旧场次人数
    c.execute('UPDATE activity_sessions SET enrolled = enrolled - ? WHERE id=?', (reg[5], reg[3]))
    # 检查新场次是否满
    c.execute('SELECT * FROM activity_sessions WHERE id=?', (new_session_id,))
    ns = c.fetchone()
    if ns and ns[5] + reg[5] > ns[4]:
        conn.close()
        return jsonify(ok=False, error='新场次名额不足'), 400
    # 改
    c.execute('UPDATE registrations SET session_id=?, updated_at=CURRENT_TIMESTAMP WHERE id=?', (new_session_id, reg_id))
    c.execute('UPDATE activity_sessions SET enrolled = enrolled + ? WHERE id=?', (reg[5], new_session_id))
    conn.commit()
    conn.close()
    return jsonify(ok=True)

@app.route('/api/activities/refund', methods=['POST'])
def api_activity_refund():
    '''退款申请'''
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
    if reg[9] == 'cancelled':
        conn.close()
        return jsonify(ok=False, error='已取消'), 400
    c.execute('UPDATE registrations SET status="refunding", updated_at=CURRENT_TIMESTAMP WHERE id=?', (reg_id,))
    c.execute('UPDATE activity_sessions SET enrolled = enrolled - ? WHERE id=?', (reg[5], reg[3]))
    # 退积分
    if reg[8] > 0:
        c.execute('UPDATE users SET points = points + ? WHERE username=?', (reg[8], f'm{reg[4]}'))
    conn.commit()
    conn.close()
    return jsonify(ok=True, message='退款申请已提交，将在1-3个工作日内处理')


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

