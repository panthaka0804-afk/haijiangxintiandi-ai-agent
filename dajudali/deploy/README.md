# 海江新天地 - 小江AI · 服务器部署指南

本目录包含生产环境所需的 Nginx 配置与 systemd 服务文件。

| 文件 | 说明 |
|------|------|
| `nginx-haijiang.conf` | Nginx 虚拟主机配置：HTTPS + 反向代理 + 安全响应头 |
| `flask.service` | 把 Flask 后端注册成 Linux 系统服务（开机自启、崩溃自愈） |

---

## 一、前置条件

- 一台 Linux 服务器（Ubuntu / Debian 已验证）
- 一个已解析到服务器公网 IP 的域名（HTTPS 必须有域名）
- 已安装：`nginx`、`python3`、`certbot`（含 nginx 插件）

```bash
sudo apt update
sudo apt install -y nginx python3 certbot python3-certbot-nginx
```

> 当前项目前端 base 是 `/vue/`，Flask 监听 `127.0.0.1:8765`，
> Nginx 只做 HTTPS 终止 + 反代，前后端代码无需改动。

---

## 二、放置代码

```bash
sudo mkdir -p /opt/haijiang
# 把仓库里的 dajudali 目录上传/解压到 /opt/haijiang/dajudali
# 安装后端依赖
cd /opt/haijiang/dajudali
python3 -m pip install -r requirements.txt   # 若没有 requirements.txt，按 server.py 用到的包装：flask openai httpx
```

---

## 三、配置 Nginx

1. 编辑配置，把里面的 `your-domain.com` 全部替换成你的真实域名：

   ```bash
   sudo nano /opt/haijiang/dajudali/deploy/nginx-haijiang.conf
   ```

2. 软链到 Nginx 启用目录并测试：

   ```bash
   sudo ln -sf /opt/haijiang/dajudali/deploy/nginx-haijiang.conf /etc/nginx/sites-enabled/haijiang.conf
   # 关掉默认站点（避免冲突，可选）
   sudo rm -f /etc/nginx/sites-enabled/default
   sudo nginx -t
   ```

3. 先**不开启 HTTPS** 验证 HTTP 是否正常（此时证书还不存在，先注释掉 443 server 块里的 ssl_* 行，或仅保留 80 块）。
   确认 `http://你的域名/vue/?t=biz` 能打开后，再申请证书。

---

## 四、申请免费 SSL 证书（Let's Encrypt）

```bash
sudo certbot --nginx -d your-domain.com
```

certbot 会自动：
- 申请证书并写入 `/etc/letsencrypt/live/your-domain.com/`
- 修改 Nginx 配置启用 HTTPS（也可自己手动改，见配置文件里的路径）

> 如果你已经手动在 `nginx-haijiang.conf` 填好了证书路径，也可以只申请不修改：
> `sudo certbot certonly --nginx -d your-domain.com`

证书 90 天有效，设置自动续期：

```bash
sudo systemctl enable certbot.timer
sudo certbot renew --dry-run   # 测试续期
```

---

## 五、启动服务

```bash
# 1) 后端注册为系统服务
sudo cp /opt/haijiang/dajudali/deploy/flask.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now flask

# 2) 重载 Nginx 使配置生效
sudo nginx -t && sudo systemctl reload nginx
```

检查：

```bash
systemctl status flask        # 后端状态
curl -I https://你的域名/vue/?t=biz   # 应返回 200 且带安全头
```

---

## 六、验证安全头是否生效

```bash
curl -sI https://你的域名/vue/?t=biz | grep -iE "content-security|x-frame|x-content|strict-transport|referrer"
```

应能看到 `Content-Security-Policy`、`X-Frame-Options: DENY` 等。

---

## 七、安全响应头说明

配置文件已下发：`X-Content-Type-Options`、`X-Frame-Options: DENY`、
`X-XSS-Protection`、`Referrer-Policy`、`Permissions-Policy`、`Content-Security-Policy`。

关于 **CSP 里的 `'unsafe-inline'`**：
本项目的 `index.html` 由 Vite 构建，注入了少量**内联引导脚本**（legacy 兼容、模块探测等），
且加载了微信 JSSDK（`res.wx.qq.com`）。因此当前 CSP 必须保留 `'unsafe-inline'` 与 `'data:'`，
否则页面会白屏。

如果以后想彻底去掉 `'unsafe-inline'`，需要：
1. 给 Vite 构建加 nonce 注入插件（`vite-plugin-csp` 之类），把 nonce 写进 `<script>`；
2. CSP 改为 `script-src 'self' 'nonce-xxxx' https://res.wx.qq.com`；
3. 把内联 `<style>`（主题背景那段）挪到外部 css 或加 nonce。

**HSTS** 已写进配置文件但默认注释，确认 HTTPS 全链路正常后再打开
（打开后无法快速回退到 HTTP，配错会导致长时间无法访问）。

---

## 八、可选加固（后续）

- 在 Nginx 给 `/api/` 加 `limit_req` 限流（防刷聊天/爬虫）
- 用 `fail2ban` 防 SSH/Web 爆破
- 定期 `certbot renew` + 监控证书到期
- 后端数据库 `dajudali.db` 定期备份
