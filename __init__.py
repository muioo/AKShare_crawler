"""
AKShare 股票数据爬取工具包

功能：
- 获取全部A股财务报表数据
- 获取实时股票行情数据
- 获取个股资金流向数据
- 支持定时任务调度

使用示例:
    # 单次获取数据
    from AKShare_crawl.data_fetcher import DataFetcher
    fetcher = DataFetcher()
    results = fetcher.fetch_all()

    # 定时获取数据
    from AKShare_crawl.scheduler import DataScheduler
    scheduler = DataScheduler()
    scheduler.run()

    # 命令行运行
    python -m AKShare_crawl.main --mode once         # 单次执行
    python -m AKShare_crawl.main --mode scheduled    # 定时执行
"""

from .data_fetcher import DataFetcher
from .scheduler import DataScheduler

__all__ = ['DataFetcher', 'DataScheduler']
__version__ = '1.0.0'
