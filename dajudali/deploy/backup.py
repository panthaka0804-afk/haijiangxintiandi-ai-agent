#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
海江新天地 - 每日自动全量备份脚本
- SQLite 一致性在线备份（sqlite3 backup API，不中断服务）
- 同时备份 .env（密钥配置）与 chat_history.json（会话记忆）
- 打包为 tar.gz，保留 30 天，自动清理过期备份
- 用法: python3 backup.py           # 执行一次备份
        python3 backup.py --list    # 列出可用备份
"""
import os
import sys
import shutil
import sqlite3
import datetime
import glob
import tarfile

BASE = '/opt/dajudali'
DB = os.path.join(BASE, 'dajudali.db')
ENV = os.path.join(BASE, '.env')
CHAT = os.path.join(BASE, 'chat_history.json')
BACKUP_DIR = os.path.join(BASE, 'backups')
RETENTION_DAYS = 30
LOG_FILE = os.path.join(BACKUP_DIR, 'backup.log')


def log(msg):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    line = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' ' + msg
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')
    print(line)


def do_backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    tmp_dir = os.path.join(BACKUP_DIR, '.tmp-' + ts)
    os.makedirs(tmp_dir, exist_ok=True)

    # 1) SQLite 一致性在线备份（服务运行中也可安全执行）
    src = sqlite3.connect(DB)
    dst = sqlite3.connect(os.path.join(tmp_dir, 'dajudali.db'))
    with dst:
        src.backup(dst)
    dst.close()
    src.close()

    # 2) 复制 .env（密钥）与 chat_history.json（会话记忆）
    for f in [ENV, CHAT]:
        if os.path.exists(f):
            shutil.copy2(f, os.path.join(tmp_dir, os.path.basename(f)))

    # 3) 打包 tar.gz（跳过 SQLite 临时文件，避免打包竞态）
    tar_path = os.path.join(BACKUP_DIR, 'backup-' + ts + '.tar.gz')
    with tarfile.open(tar_path, 'w:gz') as tar:
        for name in sorted(os.listdir(tmp_dir)):
            if name.endswith('-journal') or name.endswith('-wal') or name.endswith('-shm'):
                continue
            tar.add(os.path.join(tmp_dir, name), arcname=name)
    shutil.rmtree(tmp_dir, ignore_errors=True)

    # 4) 清理 30 天前的过期备份
    cutoff = datetime.datetime.now() - datetime.timedelta(days=RETENTION_DAYS)
    removed = 0
    for old in glob.glob(os.path.join(BACKUP_DIR, 'backup-*.tar.gz')):
        try:
            base = os.path.basename(old).replace('backup-', '').replace('.tar.gz', '')
            t = datetime.datetime.strptime(base.split('-')[0] + '-' + base.split('-')[1], '%Y%m%d-%H%M%S')
            if t < cutoff:
                os.remove(old)
                removed += 1
        except Exception:
            pass

    size = os.path.getsize(tar_path)
    log('备份完成: {} ({} bytes){}'.format(
        os.path.basename(tar_path), size,
        ', 清理过期 {} 份'.format(removed) if removed else ''))


def list_backups():
    files = sorted(glob.glob(os.path.join(BACKUP_DIR, 'backup-*.tar.gz')), reverse=True)
    if not files:
        print('暂无备份')
        return
    print('共 {} 份备份（保留 {} 天）:'.format(len(files), RETENTION_DAYS))
    for f in files[:15]:
        size = os.path.getsize(f)
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(f)).strftime('%Y-%m-%d %H:%M')
        print('  {}  {} bytes  ({})'.format(os.path.basename(f), size, mtime))


if __name__ == '__main__':
    if '--list' in sys.argv:
        list_backups()
    else:
        do_backup()
