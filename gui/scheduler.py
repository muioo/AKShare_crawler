"""
定时调度模块 - 定时执行爬虫任务
"""
import threading
import time
from datetime import datetime, timedelta
from data_fetcher import DataFetcher
from gui.file_manager import FileManager
from utils import logger


class DataScheduler:
    """数据调度器 - 定时执行爬虫任务"""

    # 调度间隔（秒）- 30分钟
    SCHEDULE_INTERVAL = 30 * 60

    def __init__(self, callback=None):
        """
        初始化调度器

        Args:
            callback: 数据获取完成后的回调函数，参数为 (results, file_paths)
        """
        self.data_fetcher = DataFetcher()
        self.file_manager = FileManager()
        self.callback = callback

        self._running = False
        self._thread = None
        self._stop_event = threading.Event()
        self._last_run = None
        self._next_run = None

    def start(self):
        """启动调度器"""
        if self._running:
            logger.warning("Scheduler is already running")
            return

        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        logger.info("Scheduler started - will run every 30 minutes")
        self._update_next_run()

    def stop(self):
        """停止调度器"""
        if not self._running:
            return

        self._stop_event.set()
        self._running = False

        if self._thread:
            self._thread.join(timeout=5)

        logger.info("Scheduler stopped")

    def _run_loop(self):
        """调度循环"""
        while not self._stop_event.is_set():
            now = datetime.now()

            # 检查是否到了运行时间
            if self._last_run is None or (now - self._last_run) >= timedelta(seconds=self.SCHEDULE_INTERVAL):
                self._execute_task()
                self._last_run = now
                self._update_next_run()

            # 等待下一次检查
            self._stop_event.wait(60)  # 每分钟检查一次

    def _execute_task(self):
        """执行爬取任务 - 只爬取实时股票行情数据"""
        logger.info("=" * 60)
        logger.info(f"Executing scheduled task at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("只爬取实时股票行情数据")
        logger.info("=" * 60)

        try:
            # 1. 先清理超过3天的旧文件
            deleted_count, total_size = self.file_manager.clean_old_files()
            logger.info(f"Cleaned {deleted_count} old files, freed {total_size / 1024:.2f} KB")

            # 2. 只获取实时股票行情数据
            results = self.data_fetcher.fetch_all_quote_data_only()

            # 3. 保存所有获取到的数据
            file_paths = {}
            for subtype, (df, data_type, name) in results.items():
                if df is not None and not df.empty:
                    # 根据类型确定子类型名称
                    if data_type == 'quote':
                        subtype_name = subtype  # 如 '实时行情_沪深京'
                    else:
                        subtype_name = None

                    filepath = self.file_manager.save_data(df, data_type, subtype_name)
                    if filepath:
                        file_paths[subtype] = filepath
                        logger.info(f"Saved {subtype} to {filepath}")

            logger.info(f"Task completed: {len(file_paths)} files saved")

            # 4. 调用回调函数
            if self.callback:
                self.callback(results, file_paths)

        except Exception as e:
            logger.error(f"Scheduled task failed: {e}")

        logger.info("=" * 60)

    def _update_next_run(self):
        """更新下次运行时间"""
        if self._last_run:
            self._next_run = self._last_run + timedelta(seconds=self.SCHEDULE_INTERVAL)
        else:
            self._next_run = datetime.now() + timedelta(seconds=self.SCHEDULE_INTERVAL)

    def run_now(self):
        """立即执行一次任务"""
        def run_task():
            self._execute_task()
            self._last_run = datetime.now()
            self._update_next_run()

        # 在新线程中执行，避免阻塞
        thread = threading.Thread(target=run_task)
        thread.start()

    def get_status(self):
        """获取调度器状态"""
        return {
            'running': self._running,
            'last_run': self._last_run,
            'next_run': self._next_run,
            'interval': self.SCHEDULE_INTERVAL
        }
