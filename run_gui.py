"""
启动GUI应用
"""
import sys
import os

# 添加AKShare_crawl到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.app import main

if __name__ == '__main__':
    main()
