#!/bin/bash
# ============================================================
# 海江新天地 - 数据库快速恢复脚本
# 用法: ./restore.sh /opt/dajudali/backups/backup-20260813-030000.tar.gz
#       不带参数则列出可用备份
# ============================================================
set -e

BACKUP_DIR="/opt/dajudali/backups"
DB="/opt/dajudali/dajudali.db"

if [ -z "$1" ]; then
  echo "用法: $0 <备份tar.gz路径>"
  echo ""
  echo "可用备份:"
  ls -lt "$BACKUP_DIR"/backup-*.tar.gz 2>/dev/null | head -10 || echo "  (无)"
  exit 1
fi

TAR="$1"
if [ ! -f "$TAR" ]; then
  echo "错误: 备份文件不存在 $TAR"
  exit 1
fi

TMP=$(mktemp -d)
tar xzf "$TAR" -C "$TMP"
SRC=$(find "$TMP" -name 'dajudali.db' | head -1)
if [ -z "$SRC" ]; then
  echo "错误: 备份包中未找到 dajudali.db"
  rm -rf "$TMP"
  exit 1
fi

echo "============================================"
echo " 即将恢复数据库"
echo "  备份文件: $TAR"
echo "  目标文件: $DB"
echo "============================================"
read -p "确认恢复？输入 yes 继续: " ANS
if [ "$ANS" != "yes" ]; then
  echo "已取消"
  rm -rf "$TMP"
  exit 0
fi

echo "1) 停止后端服务..."
sudo systemctl stop flask.service

echo "2) 备份当前数据库（安全起见）..."
cp "$DB" "$DB.pre-restore-$(date +%Y%m%d-%H%M%S)" 2>/dev/null || true

echo "3) 覆盖恢复..."
cp "$SRC" "$DB"
chown www-data:www-data "$DB"
chmod 666 "$DB"

echo "4) 启动后端服务..."
sudo systemctl start flask.service

echo "5) 清理临时文件..."
rm -rf "$TMP"

echo "============================================"
echo " ✅ 恢复完成，服务已重启"
echo "============================================"
