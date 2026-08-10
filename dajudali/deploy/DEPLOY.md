# 海江新天地 · 小江AI —— 生产部署文档

> 本文档面向「把项目长期、稳定地部署到一台云服务器」的场景。
> 本地临时预览（cloudflared quick tunnel）请见文末「附录」，仅用于演示，不可作长期方案。

---

## 一、架构总览

```
                ┌───────────── 公网入口 ─────────────┐
   浏览器 ─────►│  nginx (HTTPS 终止 + 反代)         │
                │   /vue/  →  静态前端 / Flask 8765   │
                │   /api/  →  Flask 后端 127.0.0.1:8765│
                └─────────────────────────────────────┘
                          │
                  Flask (gunicorn 多 worker)
                   ├─ /vue/  提供 Vue 构建产物 (static/vue)
                   ├─ /api/* 业务接口（会员/停车/工单/聊天…）
                   └─ SQLite (dajudali.db)
```

- **前端**：Vue3 + Vite，构建为静态文件，由后端 `/vue/` 路径提供（或 nginx 直接 root 服务）。
- **后端**：Flask；生产用 **gunicorn** 多进程，监听 `127.0.0.1:8765`（只对内，不暴露公网）。
- **反向代理**：nginx 做 HTTPS 终止 + `/api/`、`/vue/` 反代。
- **进程守护**：systemd。
- **密钥**：通过同目录 **`.env`** 注入（已内置 python-dotenv），**绝不写进代码仓库**。

---

## 二、服务器准备

| 组件 | 版本要求 | 说明 |
|------|----------|------|
| 系统 | Ubuntu 20.04+ / CentOS 7+ | 本文以 Ubuntu 为例 |
| Python | 3.10+ | 后端运行环境 |
| Node | 18+ | **仅构建前端时需要**，运行时不需要 |
| nginx | 1.18+ | 反向代理 + HTTPS |
| certbot | 最新 | 申请/续期 Let's Encrypt 证书（有域名时） |

---

## 三、拉取代码

```bash
git clone <你的仓库地址> /opt/haijiang/haijiangxintiandi-ai-agent
cd /opt/haijiang/haijiangxintiandi-ai-agent
```

---

## 四、后端

```bash
cd dajudali
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 配置密钥：复制模板并填入你的 DeepSeek Key
cp .env.example .env
nano .env          # 把 DS_API_KEY 改成你自己在 https://platform.deepseek.com 申请的
```

> `server.py` 启动时会**自动从同目录 `.env` 读取** `DS_API_KEY` 等变量，无需手动 `export`。
> 系统环境变量优先级高于 `.env`（方便用 systemd `Environment=` 覆盖）。

---

## 五、前端构建并接入

```bash
cd daju-neighbor-vue
npm install
# 同源部署（nginx 与后端同域名，/api 由 nginx 反代）：不要设 VITE_API_BASE
npm run build
# 若前后端不同源/不同域名，构建时指定后端地址：
#   VITE_API_BASE=https://api.your.com npm run build

# 把构建产物放进后端 static/vue，Flask 的 /vue/ 会自动提供
cp -r dist/* ../static/vue/
```

> `vite.config.js` 已设为相对路径 `base: './'`，构建产物可放到任意子路径。

---

## 六、nginx（HTTPS 终止 + 反代）

```bash
cp deploy/nginx-haijiang.conf /etc/nginx/sites-available/haijiang
```

编辑该文件，把两处 `server_name your-domain.com;` 改成你的域名；
若暂时没域名做 HTTP 测试，把 443 段整体注释、80 段 `return 301` 改为 `proxy_pass http://127.0.0.1:8765;`。

```bash
ln -s /etc/nginx/sites-available/haijiang /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# 有域名后申请证书（自动改写 nginx 并配置续期）：
certbot --nginx -d your-domain.com
```

---

## 七、systemd 守护后端

```bash
cp deploy/flask.service /etc/systemd/system/
# 按需修改 User / WorkingDirectory / ExecStart 路径（默认 /opt/haijiang/dajudali）
systemctl daemon-reload
systemctl enable --now flask
```

验证：
```bash
curl -s 127.0.0.1:8765/api/shops | head -c 80   # 应返回店铺 JSON
curl -sI your-domain.com/vue/ | head -1          # 应 200
```

---

## 八、更新（git pull + 重启 + 复测）

```bash
bash deploy/update.sh                 # 默认仓库=/opt/haijiang/haijiangxintiandi-ai-agent
# 或指定路径： bash deploy/update.sh /opt/your/path
```

脚本会自动拉代码、重启 Flask（优先 systemctl，否则 nohup 兜底）、复测关键接口并打印 PASS/FAIL。

---

## 九、长期稳定方案（二选一）

### 方案 A：自有域名 + HTTPS（**推荐**）
按第六、七步配置 nginx + certbot。证书 90 天自动续期，最稳，适合正式对外。

### 方案 B：无域名 · Cloudflare Tunnel 免费长期暴露
不需要公网 IP、不需要备案，比 quick tunnel 稳定（地址固定、进程常驻）：

```bash
# 1) 安装 cloudflared（服务器上）
# 2) 登录并创建命名隧道（一次性）
cloudflared tunnel login
cloudflared tunnel create haijiang
# 3) 配置 ~/.cloudflared/config.yml
# tunnel: haijiang
# credentials-file: /root/.cloudflared/<id>.json
# ingress:
#   - hostname: haijiang.your-domain.com
#     service: http://localhost:8765
#   - service: http_status:404
# 4) systemd 守护（/etc/systemd/system/cloudflared.service）
#   ExecStart=/usr/bin/cloudflared tunnel run haijiang
#   Restart=always
systemctl enable --now cloudflared
```

> 若暂时不想配域名，也可用 `cloudflared tunnel --url http://localhost:8765` 拿到
> `*.trycloudflare.com` 临时地址，但**每次重启域名会变**，只适合临时演示。

---

## 十、安全清单（上线前必查）

- [ ] `.env` 里用的是**你自己的** DeepSeek Key，不是仓库自带的测试 Key。
- [ ] `.env`、`*.db`、`__pycache__`、`node_modules`、`static/vue`、`daju-neighbor-vue/dist` 均已在 `.gitignore`，未提交任何密钥。
- [ ] 密码已采用 **PBKDF2-HMAC-SHA256**（本项目已升级），新建用户为随机强口令。
- [ ] 公开聊天/语音接口已加**限流**；DeepSeek 调用 **SSL 校验默认开启**。
- [ ] nginx 已配置安全响应头 + HSTS（确认 HTTPS 正常后再开启 HSTS）。
- [ ] Flask 仅监听 `127.0.0.1`，公网入口只有 nginx / cloudflared。

---

## 附录：本地临时预览（非长期）

```bash
# 后端
cd dajudali && source venv/bin/activate && python server.py
# 前端构建产物已在 static/vue，直接访问 http://localhost:8765/vue/
# 如需把本地临时暴露到公网（演示用）：
cloudflared tunnel --url http://localhost:8765
```
