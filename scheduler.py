"""
定时任务模块
使用 apscheduler 实现定时数据获取
"""
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from data_fetcher import DataFetcher
from config import SCHEDULE_TIMES
from utils import logger


class DataScheduler:
    """数据获取定时调度器"""

    def __init__(self, schedule_times=None):
        """
        初始化调度器

        Args:
            schedule_times: 定时时间列表，格式如 ['09:30', '15:00']
        """
        self.schedule_times = schedule_times or SCHEDULE_TIMES
        self.scheduler = BlockingScheduler()
        self.fetcher = DataFetcher()

    def job(self):
        """定时任务执行函数"""
        logger.info("-" * 50)
        logger.info(f"Job started at {datetime.now()}")
        try:
            results = self.fetcher.fetch_all()
            logger.info(f"Job completed at {datetime.now()}")
        except Exception as e:
            logger.error(f"Job failed: {e}")
        logger.info("-" * 50)

    def add_jobs(self):
        """添加定时任务"""
        for time_str in self.schedule_times:
            hour, minute = map(int, time_str.split(':'))
            self.scheduler.add_job(
                self.job,
                trigger=CronTrigger(hour=hour, minute=minute),
                id=f'fetch_data_{time_str}',
                name=f'Fetch stock data at {time_str}',
                replace_existing=True
            )
            logger.info(f"Added scheduled job at {time_str}")

    def run(self):
        """启动调度器"""
        logger.info("=" * 50)
        logger.info("Data Scheduler is starting...")
        logger.info(f"Schedule times: {self.schedule_times}")

        try:
            self.add_jobs()
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped")
            self.scheduler.shutdown()
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            raise


if __name__ == '__main__':
    # 测试定时任务
    scheduler = DataScheduler()
    scheduler.run()
