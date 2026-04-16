"""
工具函数
"""
import time
import logging
from functools import wraps
from datetime import datetime
import os
# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'app.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def retry(max_retries=3, delay=5):
    """
    重试装饰器

    Args:
        max_retries: 最大重试次数
        delay: 重试间隔（秒）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Function {func.__name__} failed after {max_retries} attempts: {e}")
                        raise
                    logger.warning(f"Function {func.__name__} attempt {attempt + 1} failed: {e}, retrying in {delay}s...")
                    time.sleep(delay)
        return wrapper
    return decorator


def get_timestamp():
    """获取当前时间戳字符串"""
    now = datetime.now()
    return now.strftime('%Y-%m-%d'), now.strftime('%H-%M-%S')


def save_to_csv(df, data_type, data_dir, date_str, time_str):
    """
    保存DataFrame到CSV文件

    Args:
        df: pandas DataFrame
        data_type: 数据类型
        data_dir: 数据目录
        date_str: 日期字符串
        time_str: 时间字符串
    """
    if df is None or df.empty:
        logger.warning(f"Data is empty, skipping save for {data_type}")
        return None

    # 获取中文文件名前缀
    from config import DATA_TYPES
    chinese_type = DATA_TYPES.get(data_type, data_type)

    filename = f"{chinese_type}_{date_str}_{time_str}.csv"
    filepath = os.path.join(data_dir, filename)

    df.to_csv(filepath, index=False, encoding='utf-8-sig')
    logger.info(f"Saved {len(df)} records to {filepath}")

    return filepath

