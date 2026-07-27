#!/usr/bin/env python3
"""
本地开发服务器 - 解决 CORS 跨域问题
直接双击或运行 python3 serve.py 即可启动本地服务器调试

使用方法:
    python3 serve.py [端口号]

默认端口: 8000
启动后访问: http://localhost:8000
"""

import sys
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler


class CORSRequestHandler(SimpleHTTPRequestHandler):
    """添加 CORS 头，允许本地开发跨域请求"""

    def end_headers(self):
        # 添加 CORS 头，允许所有来源（本地开发使用）
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

    def do_OPTIONS(self):
        """处理 OPTIONS 预检请求"""
        self.send_response(200)
        self.end_headers()


def main():
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"无效端口号: {sys.argv[1]}，使用默认端口 8000")

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    server_address = ('', port)
    httpd = HTTPServer(server_address, CORSRequestHandler)

    print(f"🚀 xiaolu-blog 本地开发服务器已启动")
    print(f"📂 目录: {os.getcwd()}")
    print(f"🔗 访问地址: http://localhost:{port}")
    print(f"⏹️  按 Ctrl+C 停止服务器")
    print("-" * 50)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n✅ 服务器已停止")
        httpd.server_close()


if __name__ == '__main__':
    main()
