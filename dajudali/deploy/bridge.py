#!/usr/bin/env python3
"""
海江新天地 · 商户桥接器
======================
接收海江AI系统推送的取号/预订事件 → 打印到商户现有热敏打印机

使用方法:
  python3 bridge.py --printer-ip 192.168.1.100 --port 9100 --listen-port 9527

然后在海江后台设置商户 Webhook 地址:
  PUT /api/merchant/webhook  { "shop_id": "s040", "token": "xxx", "webhook_url": "http://商户内网IP:9527/webhook" }

支持的打印机: 任何支持 ESC/POS 的网络热敏打印机 (58mm / 80mm)
常见品牌: Xprinter, Epson TM-T88, Rongta, Bixolon, Gprinter 等
"""

import http.server
import json
import socket
import sys
import argparse
from datetime import datetime

# ===== 配置 =====
PRINTER_IP = "192.168.1.100"
PRINTER_PORT = 9100
LISTEN_PORT = 9527

def print_ticket(printer_ip, printer_port, data):
    """发送 ESC/POS 指令到网络热敏打印机"""
    esc = b'\x1b'
    shop_name = data.get('shop_name', '海江新天地')
    queue_num = data.get('queue_number', '?')
    party_size = data.get('party_size', 2)
    phone = data.get('phone', '')
    name = data.get('name', '')
    est_wait = data.get('estimated_wait', 15)

    cmds = []
    # 初始化
    cmds.append(esc + b'@')
    # 居中 + 加粗
    cmds.append(esc + b'a\x01')
    cmds.append(esc + b'E\x01')
    cmds.append(f'{shop_name}\n'.encode('gbk', errors='replace'))
    cmds.append(esc + b'E\x00')
    cmds.append(b'-' * 32 + b'\n')
    # 排队号大字
    cmds.append(esc + b'a\x01')
    cmds.append(esc + b'!\x30')  # 双倍高宽
    cmds.append(f'{queue_num}号\n'.encode('gbk', errors='replace'))
    cmds.append(esc + b'!\x00')  # 恢复正常
    cmds.append(b'\n')
    # 详情
    cmds.append(esc + b'a\x00')  # 左对齐
    cmds.append(f'人数: {party_size}人\n'.encode('gbk', errors='replace'))
    if name:
        cmds.append(f'姓名: {name}\n'.encode('gbk', errors='replace'))
    if phone:
        cmds.append(f'手机: {phone}\n'.encode('gbk', errors='replace'))
    cmds.append(f'时间: {datetime.now().strftime("%m-%d %H:%M")}\n'.encode('gbk', errors='replace'))
    cmds.append(f'前面等候: {max(0, queue_num - 1)}桌\n'.encode('gbk', errors='replace'))
    cmds.append(f'预计等待: {est_wait}分钟\n'.encode('gbk', errors='replace'))
    cmds.append(b'-' * 32 + b'\n')
    cmds.append(esc + b'a\x01')
    cmds.append('海江新天地 · 小江AI客服\n'.encode('gbk', errors='replace'))
    cmds.append(esc + b'a\x00')
    cmds.append(b'\n' * 3)
    cmds.append(esc + b'm')  # 切纸

    payload = b''.join(cmds)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((printer_ip, printer_port))
        sock.send(payload)
        sock.close()
        print(f"[OK] 打印成功 → {printer_ip}:{printer_port} ({len(payload)} bytes)")
        return True
    except Exception as e:
        print(f"[ERROR] 打印失败: {e}")
        return False


class WebhookHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/webhook':
            self.send_response(404)
            self.end_headers()
            return
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            event = json.loads(body)
            evt_type = event.get('event', '')
            evt_data = event.get('data', {})

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"ok":true}')

            if evt_type in ('new_queue', 'new_queue_chat'):
                shop = evt_data.get('shop_name', event.get('shop_id', '?'))
                print(f"\n[取号] {shop} {evt_data.get('queue_number')}号 {evt_data.get('party_size')}人")
                print_ticket(PRINTER_IP, PRINTER_PORT, {**evt_data, 'shop_name': shop})

            elif evt_type in ('new_reservation', 'new_reservation_chat'):
                shop = evt_data.get('shop_name', event.get('shop_id', '?'))
                print(f"[预订] {shop} {evt_data.get('date')} {evt_data.get('time')} {evt_data.get('party_size')}人")

            elif evt_type == 'queue_called':
                print(f"[叫号] {evt_data.get('queue_number')}号 {evt_data.get('party_size')}人")
                # 可以打印叫号提醒小票或触发语音播报

            else:
                print(f"[事件] {evt_type}: {json.dumps(evt_data, ensure_ascii=False)}")

        except Exception as e:
            print(f"[ERROR] 处理 Webhook 失败: {e}")

    def log_message(self, format, *args):
        pass  # 抑制 HTTP 日志


def main():
    parser = argparse.ArgumentParser(description='海江商户桥接器')
    parser.add_argument('--printer-ip', default=PRINTER_IP, help='热敏打印机 IP 地址')
    parser.add_argument('--port', type=int, default=PRINTER_PORT, help='打印机端口 (默认 9100)')
    parser.add_argument('--listen-port', type=int, default=LISTEN_PORT, help='桥接器监听端口')
    args = parser.parse_args()

    global PRINTER_IP, PRINTER_PORT, LISTEN_PORT
    PRINTER_IP = args.printer_ip
    PRINTER_PORT = args.port
    LISTEN_PORT = args.listen_port

    print("=" * 50)
    print(" 海江新天地 · 商户桥接器 v1.0")
    print("=" * 50)
    print(f" 打印机: {PRINTER_IP}:{PRINTER_PORT}")
    print(f" 监听端口: {LISTEN_PORT}")
    print()
    print(" 在海江后台设置 Webhook:")
    print(f" http://本机IP:{LISTEN_PORT}/webhook")
    print()
    print(" 等待接收取号事件... (Ctrl+C 停止)")
    print("=" * 50)

    server = http.server.HTTPServer(('0.0.0.0', LISTEN_PORT), WebhookHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == '__main__':
    main()
