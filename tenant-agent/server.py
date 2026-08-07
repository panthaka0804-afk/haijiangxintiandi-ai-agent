# -*- coding: utf-8 -*-
import os, sys, json, sqlite3, hashlib, secrets
from datetime import datetime
from functools import wraps
from flask import Flask, request, redirect, url_for, session, jsonify
from openai import OpenAI

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, 'data.db')

DS_API_KEY = 'sk-e44072546dd64cf4872568b54b0d3884'
ds_client = OpenAI(api_key=DS_API_KEY, base_url='https://api.deepseek.com')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT,
            role TEXT DEFAULT 'user',
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            project_name TEXT,
            positioning TEXT,
            total_floors INTEGER,
            floor_area INTEGER,
            config_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    if not conn.execute('SELECT id FROM users WHERE username=?', ('admin',)).fetchone():
        pw = hashlib.sha256('admin123'.encode()).hexdigest()
        conn.execute("INSERT INTO users (username,password_hash,display_name,role) VALUES (?,?,?,?)",
                     ('admin', pw, 'Admin', 'admin'))
    conn.commit()
    conn.close()

init_db()

def login_required(f):
    @wraps(f)
    def d(*a,**k):
        if not session.get('user_id'): return redirect(url_for('login_page'))
        return f(*a,**k)
    return d

def admin_required(f):
    @wraps(f)
    def d(*a,**k):
        if not session.get('user_id'): return redirect(url_for('login_page'))
        if session.get('role') != 'admin': return 'Forbidden', 403
        return f(*a,**k)
    return d

def ai_chat(system_prompt, user_prompt):
    try:
        resp = ds_client.chat.completions.create(
            model='deepseek-chat',
            messages=[{'role':'system','content':system_prompt},{'role':'user','content':user_prompt}],
            temperature=0.7, max_tokens=2000
        )
        text = resp.choices[0].message.content
        # Clean markdown symbols
        import re
        text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'^-\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'_{2,}', '——', text)
        return text
    except Exception as e:
        return '[AI Error] ' + str(e)[:300]

# Simple HTML helpers
def login_html(error=False):
    err_style = '' if error else 'display:none'
    return '''<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Login</title><style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Arial,sans-serif;background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);min-height:100vh;display:flex;align-items:center;justify-content:center}
.box{background:#fff;border-radius:16px;padding:40px;width:400px;box-shadow:0 20px 60px rgba(0,0,0,.3)}
.box h2{font-size:24px;color:#1a1a2e;margin-bottom:4px}
.box p{color:#888;font-size:13px;margin-bottom:28px}
.fg{margin-bottom:20px}
.fg label{display:block;font-weight:600;font-size:13px;color:#555;margin-bottom:6px}
.fg input{width:100%;padding:12px;border:1px solid #ddd;border-radius:8px;font-size:14px}
.fg input:focus{outline:none;border-color:#1a73e8;box-shadow:0 0 0 3px rgba(26,115,232,.1)}
.btn{width:100%;padding:12px;background:#1a73e8;color:#fff;border:none;border-radius:8px;font-size:16px;font-weight:600;cursor:pointer}
.error{background:#fce8e6;color:#c5221f;padding:10px;border-radius:8px;font-size:13px;margin-bottom:16px;''' + err_style + '''}
.foot{text-align:center;margin-top:20px;font-size:12px;color:#999}
</style></head><body>
<div class="box"><h2>Tenant Agent</h2><p>Commercial Real Estate Leasing Platform</p>
<div class="error">Invalid username or password</div>
<form method="POST" action="/login">
<div class="fg"><label>Username</label><input name="username" required autofocus></div>
<div class="fg"><label>Password</label><input name="password" type="password" required></div>
<button class="btn" type="submit">Login</button>
</form><div class="foot">Default: admin / admin123</div></div></body></html>'''

def admin_page(content, tab, **ctx):
    name = ctx.get('display_name','')
    user = ctx.get('username','')
    return '''<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Admin Panel</title><style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Arial,sans-serif;background:#f0f2f5}
.bar{background:#1a1a2e;color:#fff;padding:8px 20px;display:flex;justify-content:space-between;align-items:center;font-size:13px}
.bar a{color:#ffb3b3;text-decoration:none;margin-left:12px}
.nav{background:#fff;border-bottom:1px solid #e0e0e0;padding:0 20px;display:flex}
.nav a{padding:12px 20px;font-size:14px;text-decoration:none;color:#555;border-bottom:2px solid transparent}
.nav a:hover,.nav a.active{color:#1a73e8;border-bottom-color:#1a73e8}
.main{padding:20px;max-width:1200px;margin:0 auto}
.card{background:#fff;border-radius:8px;padding:20px;margin-bottom:16px;box-shadow:0 1px 4px rgba(0,0,0,.06)}
.card h3{font-size:16px;margin-bottom:16px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:10px 12px;text-align:left;border-bottom:1px solid #eee}
th{background:#f8f9fa;font-weight:600;color:#555}
.btn{padding:6px 14px;border:none;border-radius:5px;font-size:12px;font-weight:600;cursor:pointer}
.btn-blue{background:#1a73e8;color:#fff}
.btn-red{background:#ea4335;color:#fff}
.btn-green{background:#0f9d58;color:#fff}
.btn-gray{background:#e0e0e0;color:#333}
.tag{padding:2px 8px;border-radius:4px;font-size:11px;color:#fff}
.tag-admin{background:#c5221f}
.tag-user{background:#1a73e8}
.tag-active{background:#0f9d58}
.tag-disabled{background:#999}
.flex{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
input,select{padding:8px 10px;border:1px solid #ddd;border-radius:5px;font-size:13px}
.modal-overlay{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.4);z-index:100;align-items:center;justify-content:center}
.modal-overlay.show{display:flex}
.modal{background:#fff;border-radius:12px;padding:28px;width:420px;max-width:90vw}
.modal h3{margin-bottom:20px}
.modal .fg{margin-bottom:14px}
.modal .fg label{display:block;font-weight:600;font-size:13px;color:#555;margin-bottom:4px}
.modal .fg input,.modal .fg select{width:100%}
.toast{position:fixed;top:20px;right:20px;padding:12px 20px;border-radius:8px;color:#fff;font-size:13px;z-index:999;display:none}
.toast.show{display:block}
.toast-success{background:#0f9d58}
.toast-error{background:#ea4335}
</style></head><body>
<div class="bar"><span>Admin Panel</span><span>''' + name + ' (' + user + ''') <a href="/app">App</a> <a href="/logout">Logout</a></span></div>
<div class="nav">
<a href="/admin" class="''' + ('active' if tab=='users' else '') + '''">Users</a>
</div><div class="main">''' + content + '''</div>
<div class="toast" id="toast"></div>
<script>function toast(m,t){var e=document.getElementById('toast');e.textContent=m;e.className='toast toast-'+t+' show';setTimeout(function(){e.classList.remove('show')},2500)}</script>
</body></html>'''

# ===== Routes =====
@app.route('/')
def index():
    return redirect(url_for('app_page') if session.get('user_id') else url_for('login_page'))

@app.route('/login', methods=['GET','POST'])
def login_page():
    error = False
    if request.method == 'POST':
        u = request.form.get('username','').strip()
        p = request.form.get('password','').strip()
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=? AND status='active'", (u,)).fetchone()
        if user and user['password_hash'] == hashlib.sha256(p.encode()).hexdigest():
            conn.execute("UPDATE users SET last_login=? WHERE id=?", (datetime.now(), user['id']))
            conn.commit()
            session.update(user_id=user['id'], username=user['username'],
                          display_name=user['display_name'] or user['username'], role=user['role'])
            conn.close()
            return redirect(url_for('app_page'))
        conn.close()
        error = True
    return login_html(error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/app')
@login_required
def app_page():
    with open(os.path.join(HERE, 'index.html'), 'r', encoding='utf-8') as f:
        html = f.read()
    admin = session.get('role')=='admin'
    alink = '<a href="/admin" style="color:#81c784;text-decoration:none;margin-right:12px">Admin</a>' if admin else ''
    bar = '<div style="background:#1a1a2e;color:#fff;padding:8px 20px;display:flex;justify-content:space-between;align-items:center;font-size:13px"><span>{} ({}) | {}</span><span>{}<a href="/logout" style="color:#ffb3b3;text-decoration:none">Logout</a></span></div>'.format(
        session.get('display_name'), session.get('username'), session.get('role'), alink)
    return html.replace('<div class="container">', bar + '\n<div class="container">')

# ===== Admin Users =====
@app.route('/admin')
@admin_required
def admin_users():
    conn = get_db()
    rows = conn.execute('SELECT id,username,display_name,role,status,created_at,last_login FROM users ORDER BY id').fetchall()
    conn.close()
    rows_html = ''
    for u in rows:
        uid=u['id']; un=u['username']; dn=u['display_name'] or '-'; rl=u['role']; st=u['status']
        ct=(u['created_at'] or '')[:10]; ll=(u['last_login'] or 'Never')[:16]
        rtag='tag-admin' if rl=='admin' else 'tag-user'
        stag='tag-active' if st=='active' else 'tag-disabled'
        tb = '<button class="btn btn-red" style="padding:4px 8px;font-size:11px" onclick="toggleUser({0},\'disable\')">Disable</button>'.format(uid) if st=='active' else '<button class="btn btn-green" style="padding:4px 8px;font-size:11px" onclick="toggleUser({0},\'enable\')">Enable</button>'.format(uid)
        rows_html += '<tr><td>{0}</td><td><strong>{1}</strong></td><td>{2}</td><td><span class="tag {3}">{4}</span></td><td><span class="tag {5}">{6}</span></td><td>{7}</td><td>{8}</td><td class="flex"><button class="btn btn-blue" style="padding:4px 8px;font-size:11px" onclick="editUser({0},\'{1}\',\'{2}\',\'{4}\')">Edit</button>{9}<button class="btn btn-gray" style="padding:4px 8px;font-size:11px" onclick="resetPw({0},\'{1}\')">Reset PW</button></td></tr>'.format(uid,un,dn,rtag,rl,stag,st,ct,ll,tb)
    content = '''<div class="card"><h3>User Management</h3>
<div class="flex" style="margin-bottom:12px"><button class="btn btn-blue" onclick="openModal()">+ New User</button></div>
<table><thead><tr><th>ID</th><th>Username</th><th>Name</th><th>Role</th><th>Status</th><th>Created</th><th>Last Login</th><th>Actions</th></tr></thead>
<tbody>''' + rows_html + '''</tbody></table></div>
<div class="modal-overlay" id="userModal">
<div class="modal"><h3 id="modalTitle">New User</h3>
<input type="hidden" id="eid">
<div class="fg"><label>Username</label><input id="uname" required></div>
<div class="fg"><label>Display Name</label><input id="udisplay"></div>
<div class="fg"><label>Password</label><input id="upw" type="password"><small id="pwhint"></small></div>
<div class="fg"><label>Role</label><select id="urole"><option value="user">User</option><option value="admin">Admin</option></select></div>
<div class="flex" style="justify-content:flex-end;margin-top:20px"><button class="btn btn-gray" onclick="document.getElementById(\'userModal\').classList.remove(\'show\')">Cancel</button><button class="btn btn-blue" onclick="saveUser()">Save</button></div></div></div>
<script>
function openModal(){document.getElementById("eid").value="";document.getElementById("modalTitle").textContent="New User";document.getElementById("uname").value="";document.getElementById("udisplay").value="";document.getElementById("upw").value="";document.getElementById("upw").required=true;document.getElementById("pwhint").textContent="";document.getElementById("urole").value="user";document.getElementById("userModal").classList.add("show")}
function editUser(id,nm,dp,rl){document.getElementById("eid").value=id;document.getElementById("modalTitle").textContent="Edit User";document.getElementById("uname").value=nm;document.getElementById("udisplay").value=dp;document.getElementById("upw").value="";document.getElementById("upw").required=false;document.getElementById("pwhint").textContent="Leave blank to keep current";document.getElementById("urole").value=rl;document.getElementById("userModal").classList.add("show")}
function saveUser(){var id=document.getElementById("eid").value,data={display_name:document.getElementById("udisplay").value,role:document.getElementById("urole").value},pw=document.getElementById("upw").value;if(!id)data.username=document.getElementById("uname").value;if(pw)data.password=pw;var url=id?"/api/users/"+id:"/api/users";fetch(url,{method:id?"PUT":"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)}).then(function(r){return r.json()}).then(function(j){if(j.ok){location.reload()}else{toast(j.error||"Error","error")}})}
function toggleUser(id,act){fetch("/api/users/"+id+"/status",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({status:act=="enable"?"active":"disabled"})}).then(function(r){return r.json()}).then(function(j){if(j.ok)location.reload();else toast(j.error||"Error","error")})}
function resetPw(id,nm){if(!confirm("Reset password for "+nm+" to 123456?"))return;fetch("/api/users/"+id+"/reset-pw",{method:"POST"}).then(function(r){return r.json()}).then(function(j){if(j.ok)toast("Password reset","success");else toast(j.error||"Error","error")})}
</script>'''
    return admin_page(content, 'users', **session)

# ===== API Users =====
@app.route('/api/users', methods=['GET','POST'])
@admin_required
def api_users():
    if request.method == 'GET':
        conn = get_db()
        users = conn.execute('SELECT id,username,display_name,role,status,created_at,last_login FROM users ORDER BY id').fetchall()
        conn.close()
        return jsonify([dict(u) for u in users])
    data = request.get_json()
    un = data.get('username','')
    pw = data.get('password','')
    if len(un)<2: return jsonify(ok=False,error='Username too short'),400
    if len(pw)<6: return jsonify(ok=False,error='Password min 6 chars'),400
    conn = get_db()
    if conn.execute('SELECT id FROM users WHERE username=?',(un,)).fetchone():
        conn.close(); return jsonify(ok=False,error='Username exists'),400
    conn.execute('INSERT INTO users (username,password_hash,display_name,role) VALUES (?,?,?,?)',
                 (un,hashlib.sha256(pw.encode()).hexdigest(),data.get('display_name',''),data.get('role','user')))
    conn.commit(); conn.close()
    return jsonify(ok=True)

@app.route('/api/users/<int:uid>', methods=['PUT'])
@admin_required
def api_user_update(uid):
    data = request.get_json()
    conn = get_db()
    if not conn.execute('SELECT id FROM users WHERE id=?',(uid,)).fetchone():
        conn.close(); return jsonify(ok=False,error='Not found'),404
    sets=[]; vals=[]
    if 'display_name' in data: sets.append('display_name=?'); vals.append(data['display_name'])
    if 'role' in data: sets.append('role=?'); vals.append(data['role'])
    if data.get('password'): sets.append('password_hash=?'); vals.append(hashlib.sha256(data['password'].encode()).hexdigest())
    if sets:
        vals.append(uid)
        conn.execute('UPDATE users SET {} WHERE id=?'.format(','.join(sets)), vals)
    conn.commit(); conn.close()
    return jsonify(ok=True)

@app.route('/api/users/<int:uid>/status', methods=['PUT'])
@admin_required
def api_user_status(uid):
    data = request.get_json()
    if data['status'] not in ('active','disabled'): return jsonify(ok=False,error='Bad status'),400
    conn = get_db()
    conn.execute("UPDATE users SET status=? WHERE id=? AND username!='admin'",(data['status'],uid))
    conn.commit(); conn.close()
    return jsonify(ok=True)

@app.route('/api/users/<int:uid>/reset-pw', methods=['POST'])
@admin_required
def api_user_reset_pw(uid):
    conn = get_db()
    conn.execute('UPDATE users SET password_hash=? WHERE id=?',(hashlib.sha256('123456'.encode()).hexdigest(),uid))
    conn.commit(); conn.close()
    return jsonify(ok=True)

# ===== AI APIs =====
@app.route('/api/ai/analyze-brands', methods=['POST'])
@login_required
def ai_analyze_brands():
    data = request.get_json()
    brands_data = data.get('brands', [])
    positioning = data.get('positioning', 'premium')
    pos_names = {'community':'Community Mall','premium':'Premium Mall','lifestyle':'Lifestyle Center','outlet':'Outlet','street':'Street Mall'}
    sp = 'You are a commercial real estate leasing expert. Analyze the tenant mix. Evaluate: category mix, brand conflicts, positioning fit, anchor sufficiency, optimization. Reply in Chinese, plain text only, no markdown formatting, no asterisks, no hash marks, no numbered lists with symbols. Use Chinese punctuation and natural paragraph breaks.'
    up = 'Mall: {}\nTenant mix:\n{}\nAnalyze and suggest optimizations.'.format(pos_names.get(positioning,positioning), json.dumps(brands_data,ensure_ascii=False,indent=2))
    result = ai_chat(sp, up)
    if result.startswith('[AI Error]'): return jsonify(ok=False, error=result), 500
    return jsonify(ok=True, result=result)

@app.route('/api/ai/recommend-brands', methods=['POST'])
@login_required
def ai_recommend_brands():
    data = request.get_json()
    floor = data.get('floor','1F')
    area = data.get('area',500)
    positioning = data.get('positioning','premium')
    existing = data.get('existing_brands',[])
    pos_names = {'community':'Community Mall','premium':'Premium Mall','lifestyle':'Lifestyle Center','outlet':'Outlet','street':'Street Mall'}
    sp = 'You are a commercial real estate expert. Recommend 3-5 brands for a vacant unit. Consider floor, area, existing brands, positioning. Reply in Chinese, plain text only, no markdown formatting, no asterisks, no hash marks. Use natural paragraph structure.'
    up = 'Mall: {}\nUnit: {} ~{}sqm\nNearby: {}\nRecommend brands.'.format(pos_names.get(positioning,positioning), floor, area, ', '.join(existing) if existing else 'none')
    result = ai_chat(sp, up)
    if result.startswith('[AI Error]'): return jsonify(ok=False, error=result), 500
    return jsonify(ok=True, result=result)

@app.route('/api/ai/strategy-advice', methods=['POST'])
@login_required
def ai_strategy_advice():
    data = request.get_json()
    signed = data.get('signed',0)
    total = data.get('total',0)
    floor_stats = data.get('floorStats',[])
    positioning = data.get('positioning','premium')
    rate = round(signed/total*100,1) if total>0 else 0
    sp = 'You are a leasing strategy consultant. Based on progress, recommend next steps: weak floors, vacancy risks, brand balance, tactics. Reply in Chinese, plain text only, no markdown, no asterisks, no hash marks. 3-5 actionable suggestions with natural paragraph formatting.'
    up = 'Mall: {}\nProgress: {}/{} ({}%)\nFloors: {}\nRecommend next steps.'.format(positioning, signed, total, rate, json.dumps(floor_stats,ensure_ascii=False))
    result = ai_chat(sp, up)
    if result.startswith('[AI Error]'): return jsonify(ok=False, error=result), 500
    return jsonify(ok=True, result=result)

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print('[OK] Tenant Agent v3 DeepSeek: http://localhost:8766')
    app.run(host='0.0.0.0', port=8766, debug=False)
