"""
启动GUI应用
"""
import sys
import os
import ssl
import threading

# ======================== 【1. 强制修复 SSL 联网问题】 ========================
ssl._create_default_https_context = ssl._create_unverified_context
os.environ["REQUESTS_CA_BUNDLE"] = ""
os.environ["CURL_CA_BUNDLE"] = ""

# ======================== 【2. 强制修复 akshare 缓存目录】 ========================
os.environ["AKSHARE_CACHE_DIR"] = os.path.join(os.path.expanduser("~"), "akshare_cache")

# ======================== 【3. 打包环境路径适配】 ========================
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    os.chdir(BASE_DIR)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE_DIR)

# ======================== 【4. 多线程打包必须加这一行】 ========================
if hasattr(sys, 'frozen'):
    threading.current_thread().name = "MainThread"

# ======================== 启动GUI ========================
from gui.app import main

if __name__ == '__main__':
    main()