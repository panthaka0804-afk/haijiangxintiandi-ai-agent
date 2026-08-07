#!/usr/bin/env bash
#
# 海江新天地 · 一键更新 + 重启 + 复测
# -------------------------------------------------------------
# 在服务器上执行：  bash deploy/update.sh
# 或指定仓库路径：  bash deploy/update.sh /opt/haijiang/haijiangxintiandi-ai-agent
#
# 动作：
#   1) git pull 拉最新代码（含本仓库已修复的 /api/shops /offers /parking 等接口）
#   2) 重启 Flask 后端（优先 systemctl，否则 fallback 杀进程 + nohup 重启）
#   3) 等待服务就绪
#   4) 自动复测关键接口，打印 PASS/FAIL
# -------------------------------------------------------------
set -uo pipefail

# 仓库目录：参数优先，否则取本脚本上一级（deploy/ 的父目录）
REPO_DIR="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$REPO_DIR" || { echo "无法进入仓库目录: $REPO_DIR"; exit 1; }

SERVER_PY="dajudali/server.py"
SERVICE_NAME="${FLASK_SERVICE:-flask}"
PORT="${FLASK_PORT:-8765}"
# 复测走 nginx(80) 完整链路；若 nginx 没起则用 Flask 直连
BASE="http://127.0.0.1"

echo "=================================================="
echo " 海江新天地 更新脚本"
echo " 仓库: $REPO_DIR"
echo "=================================================="

# ---------- 1) 拉代码 ----------
echo ""
echo "==> [1/4] git pull (ff-only)"
if git pull --ff-only 2>&1; then
  echo "    git pull OK，当前 HEAD: $(git rev-parse --short HEAD)"
else
  echo "    ⚠️ git pull 失败（可能本地有改动或非快进）。继续尝试重启..."
fi

# ---------- 2) 重启 Flask ----------
echo ""
echo "==> [2/4] 重启 Flask 后端"
RESTARTED=0
if command -v systemctl >/dev/null 2>&1; then
  if systemctl list-unit-files 2>/dev/null | grep -q "^${SERVICE_NAME}.service"; then
    echo "    使用 systemctl restart ${SERVICE_NAME}"
    sudo systemctl restart "${SERVICE_NAME}" && RESTARTED=1 || echo "    ⚠️ systemctl restart 失败，尝试 fallback"
  fi
fi
if [ "$RESTARTED" -eq 0 ]; then
  echo "    fallback: 杀掉旧 ${SERVER_PY} 进程并用 nohup 重启"
  pkill -f "${SERVER_PY}" 2>/dev/null || true
  sleep 2
  if [ -f "${SERVER_PY}" ]; then
    nohup python3 "${SERVER_PY}" > /tmp/flask_haijiang.log 2>&1 &
    RESTARTED=1
    echo "    已 nohup 启动 python3 ${SERVER_PY} (日志 /tmp/flask_haijiang.log)"
  else
    echo "    ❌ 找不到 ${SERVER_PY}，请检查仓库路径"
    exit 1
  fi
fi

# ---------- 3) 等待就绪 ----------
echo ""
echo "==> [3/4] 等待服务就绪 (最多 20s)"
READY=0
for i in $(seq 1 20); do
  # 优先探 nginx 80，失败则探 Flask 直连
  if curl -s -o /dev/null --max-time 3 "http://127.0.0.1/api/activities"; then
    READY=1; break
  elif curl -s -o /dev/null --max-time 3 "http://127.0.0.1:${PORT}/api/activities"; then
    BASE="http://127.0.0.1:${PORT}"; READY=1; break
  fi
  sleep 1
done
if [ "$READY" -eq 0 ]; then
  echo "    ⚠️ 服务 20s 内未就绪，仍继续复测（可能拿到旧结果）"
else
  echo "    服务已就绪 (BASE=${BASE})"
fi

# ---------- 4) 复测 ----------
echo ""
echo "==> [4/4] 复测关键接口"
PASS=0; FAIL=0
check_get() {
  local path="$1"; local expect="${2:-200}"
  local code; code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 8 "${BASE}${path}")
  if [ "$code" = "$expect" ]; then echo "  [PASS] GET  ${path} -> ${code}"; PASS=$((PASS+1));
  else echo "  [FAIL] GET  ${path} -> ${code} (期望 ${expect})"; FAIL=$((FAIL+1)); fi
}
check_post() {
  local path="$1"; local data="$2"; local expect="${3:-200}"
  local code; code=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d "$data" --max-time 8 "${BASE}${path}")
  if [ "$code" = "$expect" ]; then echo "  [PASS] POST ${path} -> ${code}"; PASS=$((PASS+1));
  else echo "  [FAIL] POST ${path} -> ${code} (期望 ${expect})"; FAIL=$((FAIL+1)); fi
}

# 之前 404 的三个接口（本次重点验证）
check_get  "/api/shops"
check_get  "/api/offers"
check_post "/api/parking/query" '{"plate":"沪A12345"}'
# 基础链路
check_get  "/api/activities"
check_post "/api/public/chat"   '{"message":"你们有火锅店吗"}'
check_get  "/vue/"
check_get  "/manage"
check_get  "/admin" "401"

echo ""
echo "=================================================="
echo " 复测结果: ${PASS} 通过 / ${FAIL} 失败"
echo "=================================================="
[ "$FAIL" -eq 0 ] && echo "✅ 全部通过，部署成功" || echo "❌ 仍有失败项，请查看上方 [FAIL] 并检查后端日志"
