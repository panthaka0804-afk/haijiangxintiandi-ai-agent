# -*- coding: utf-8 -*-
"""大橘大利系统 - 社区商业AI客服"""
import os, sys, json, sqlite3, hashlib, secrets, re, time, io, base64
from datetime import datetime
from functools import wraps
from flask import Flask, request, session, jsonify, send_from_directory
from openai import OpenAI
import floor_data

app = Flask(__name__)
app.secret_key = os.environ.get('DJDL_SECRET_KEY', 'dajudali-2026-secret-key-v1')
HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, 'dajudali.db')
DS_API_KEY = 'sk-e44072546dd64cf4872568b54b0d3884'
ds_client = OpenAI(api_key=DS_API_KEY, base_url='https://api.deepseek.com')

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
SYSTEM_PROMPT = '''你是大橘邻里社区商业中心的客服助手小橘。服务友好、专业、简洁。

【核心规则】
1. 基于知识库内容回答，不知道就诚实说暂时不了解，会记录下来帮忙查询
2. 严禁编造任何信息！不准编造店铺名称、品牌、价格、菜单、营业时间
3. 回复简短清晰，控制在3-5句内
4. 保持小橘人设：可爱、有活力，偶尔卖萌
5. 不要显示Markdown格式符号
6. 可以推荐商户但不过度推销
7. 活动报名告知可在聊天中直接报名，或访问公众号菜单栏
8. 用户需求模糊时主动反问澄清
9. 严禁编造店铺名称、价格、菜单、电话
10. 知识库置信度>70%直接回答，40-70%结合判断，<40%转人工
11. 当用户问"有什么优惠""有什么套餐""有什么折扣"时，先列出【优惠套餐目录】：包含美食优惠、四大场景套餐、银行叠加优惠
12. 算价/优惠叠加：逐条列出可用优惠，推荐最优方案，给出到手价
13. 场景套餐识别：用户提及"亲子""夜生活""祖孙""会员价"时，自动匹配对应套餐规则核算
13. 套餐核算格式：【方案】列出适用优惠 → 【逐项算价】→ 【总价比原价省多少】→ 【最优建议】
14. 价格对比按知识库如实说明
15. 退款/投诉/安全立即升级高优先级工单
16. 不确定用户会员等级时提醒用户提供手机号查询，或保守估算按最低折扣
17. 用户提供手机号时，自动已查询其会员等级（见上方【会员查询结果】），直接基于该等级算价，不需要再问
18. 用户询问场地租赁/摊位/教室/广告位/会客厅时，告知可以点击下方橙色「场地报价」按钮实时生成报价明细，或直接回复各类场地计费规则供参考
19. 用户询问积分/升级/兑换/会员权益时，自动计算：当前等级和折扣→距离升级还需多少分/消费→最优兑换推荐→积分使用建议。优先推荐性价比最高的兑换（价值/积分最大）
20. 用户说"兑换XX""换XX""用积分换"时，确认兑换项目后回复：兑换项目名称、所需积分、剩余积分。告知用户回复"确认兑换(ID)"完成兑换（例如"确认兑换3"兑换星巴克），可兑换ID：1=停车券500分 2=B1美食券800分 3=星巴克1000分 4=电影票2000分 5=蜀大侠券3000分 6=乐园门票5000分 7=棒约翰双人餐8000分 8=购物卡10000分 9=火锅套餐15000分
21. 用户消息以"确认兑换"开头时，自动解析兑换ID，告知已记录，实际兑换请通过小程序操作
22. 用户说"注册会员""开通会员""怎么注册"等注册话术时：如果消息里包含手机号，回复引导格式"确认注册 姓名 手机号"来创建会员，不要说去服务台！如果消息里没有手机号，让用户提供手机号。绝对禁止回复"去服务台办理"、"到B1层服务台"等推卸话术。
23. 会员查询结果显示"NOT_FOUND"时，主动告知用户该手机号未注册，并引导：回复"我要注册"即可开通会员，赠送500积分。绝对不要回复"去服务台注册"。

24. 【全域智能检索】当用户消息仅为"找优惠"（无额外参数）时，回复简洁的可选项让用户回数字即可：
 找优惠·请回复数字：
1 餐饮优惠  2 亲子优惠  3 夜校优惠  4 便民优惠
当用户回复数字1/2/3/4时，按对应业态从知识库promo分类筛选优惠活动，列出：①优惠内容 ②有效期 ③适用商户 ④使用条件。
25. 当用户消息仅为"找活动"（无额外参数）时回复：
 找活动·请回复数字：
1 亲子活动  2 老年活动  3 青年活动  4 全部活动
用户回复数字后，按对应人群从知识库event分类筛选。
26. 当用户消息仅为"找店铺"（无额外参数）时回复：
 找店铺·请回复数字：
1 火锅  2 披萨  3 咖啡  4 亲子餐厅  5 美食广场  6 教培
用户回复数字后，按对应业态从知识库store分类检索。
27. 当用户消息仅为"找商品"（无额外参数）时回复：
 找商品·请回复数字：
1 夜校课程  2 演出票务  3 零售商品
用户回复数字后，检索对应词条展示详情。

【导航规则】
28. 当用户问"XXX在哪里""XXX怎么走""怎么去XXX"时，从knowledge_base的navigation分类检索目标点位，生成文字步行指引，格式：
【当前楼层→目标楼层】
Step1: 找到最近的电梯/扶梯（标注位置）
Step2: 到达目标楼层后→标注方向（左转/右转/直行）
Step3: 沿通道步行，经过哪个参照物（对面店名、标志点）
Step4: 到达目标
注意：跨楼层时标注电梯/扶梯位置；同一楼层走通道不必提电梯
29. 用户问"卫生间/厕所/WC"时，告知最近卫生间位置（每层电梯厅旁）
30. 用户问"电梯在哪里"时，说明3部客梯+扶梯位置

严禁在回复中使用"AI"字样，你是客服小橘，不是AI。回复前请自检：去掉所有"AI"字眼。

你是大橘邻里最可爱的小橘！'''

CHAT_HISTORY = {}
MAX_HISTORY = 20
MAX_SESSIONS = 500

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
    return jsonify(ok=True, user=dict(user))

@app.route('/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify(ok=True)

@app.route('/api/session')
def api_session():
    if session.get('user_id'):
        return jsonify(ok=True, user={
            'id': session['user_id'],
            'tenant_id': session['tenant_id'],
            'role': session.get('role'),
            'display_name': session.get('display_name')
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
                            CHAT_HISTORY[chat_key] = history[-MAX_HISTORY*2:]
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
                            CHAT_HISTORY[chat_key] = history[-MAX_HISTORY*2:]
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
                CHAT_HISTORY[chat_key] = history[-MAX_HISTORY*2:]
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
                CHAT_HISTORY[chat_key] = history[-MAX_HISTORY*2:]
                return jsonify(ok=True, reply=reply)
            else:
                reply = '请发送您的11位手机号，我来帮您注册会员~（注册即送500积分）'
                history.append({'role':'user','content':user_input})
                history.append({'role':'assistant','content':reply})
                CHAT_HISTORY[chat_key] = history[-MAX_HISTORY*2:]
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
            CHAT_HISTORY[chat_key] = history[-MAX_HISTORY*2:]
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
            CHAT_HISTORY[chat_key] = history[-MAX_HISTORY*2:]
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
                        CHAT_HISTORY[chat_key] = history[-MAX_HISTORY*2:]
                        return jsonify(ok=True, reply=reply)
                    else:
                        cdb.close() if 'cdb' in dir() else None
                else:
                    cdb.close() if 'cdb' in dir() else None
            else:
                reply = '请发送您的11位手机号，我帮您查优惠券~'
                history.append({'role':'user','content':user_input})
                history.append({'role':'assistant','content':reply})
                CHAT_HISTORY[chat_key] = history[-MAX_HISTORY*2:]
                return jsonify(ok=True, reply=reply)
        except Exception:
            pass

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
    messages = [{'role':'system','content':sp}]
    for h in history:
        messages.append(h)
    messages.append({'role':'user','content': user_input})
    try:
        resp = ds_client.chat.completions.create(model='deepseek-chat', messages=messages, max_tokens=600, temperature=0.7)
        reply = resp.choices[0].message.content
    except Exception:
        reply = '哎呀，小橘的脑子有点转不过来...要不你重新说一遍？'
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
    CHAT_HISTORY[chat_key] = history[-MAX_HISTORY*2:]
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
        return jsonify([dict(r) for r in rows])
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
        rows = conn.execute("SELECT * FROM work_orders WHERE tenant_id=? ORDER BY created_at DESC LIMIT 200", (tid,)).fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    data = request.get_json()
    conn = get_db()
    conn.execute(
        "INSERT INTO work_orders (tenant_id, type, title, description, priority, status, reporter, reporter_contact) VALUES (?,?,?,?,?,?,?,?)",
        (tid, data.get('type','inquiry'), data.get('title',''), data.get('description',''),
         data.get('priority','normal'), data.get('status','pending'), data.get('reporter',''), data.get('reporter_contact',''))
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
    orders = conn.execute("SELECT COUNT(*) as c FROM work_orders WHERE tenant_id=? AND status!='closed'", (tid,)).fetchone()['c']
    kb = conn.execute("SELECT COUNT(*) as c FROM knowledge_base WHERE tenant_id=?", (tid,)).fetchone()['c']
    users = conn.execute("SELECT COUNT(*) as c FROM users WHERE tenant_id=?", (tid,)).fetchone()['c']
    pending = conn.execute("SELECT COUNT(*) as c FROM work_orders WHERE tenant_id=? AND status='pending'", (tid,)).fetchone()['c']
    conn.close()
    return jsonify(ok=True, orders=orders, kb_count=kb, users=users, pending=pending)

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
