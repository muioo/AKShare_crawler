"""
文件管理模块 - 处理文件保存和清理
"""
import os
from datetime import datetime, timedelta
from config import DATA_DIR


class FileManager:
    """文件管理器"""

    # 保留天数
    RETENTION_DAYS = 3

    def __init__(self):
        self.data_dir = DATA_DIR

    def get_file_age_days(self, filepath):
        """获取文件年龄（天数）"""
        if not os.path.exists(filepath):
            return None

        file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
        age = datetime.now() - file_time
        return age.days

    def clean_old_files(self, subdirs=None):
        """
        清理超过保留天数的旧文件

        Args:
            subdirs: 子目录列表，如果为None则清理所有子目录
        """
        if subdirs is None:
            subdirs = ['实时行情', '资金流向']

        deleted_count = 0
        total_size = 0

        for subdir in subdirs:
            dir_path = os.path.join(self.data_dir, subdir)
            if not os.path.exists(dir_path):
                continue

            for filename in os.listdir(dir_path):
                filepath = os.path.join(dir_path, filename)

                # 跳过目录
                if os.path.isdir(filepath):
                    continue

                # 检查文件年龄
                age_days = self.get_file_age_days(filepath)
                if age_days is not None and age_days > self.RETENTION_DAYS:
                    try:
                        file_size = os.path.getsize(filepath)
                        os.remove(filepath)
                        deleted_count += 1
                        total_size += file_size
                    except Exception as e:
                        print(f"删除文件失败 {filepath}: {e}")

        return deleted_count, total_size

    def save_data(self, df, data_type, subtype=None):
        """
        保存数据到CSV文件，并先清理旧文件

        Args:
            df: pandas DataFrame
            data_type: 数据类型 ('quote', 'fund_flow')
            subtype: 子类型（仅quote需要，如 '沪深京A股'）

        Returns:
            保存的文件路径
        """
        if df is None or df.empty:
            return None

        # 确定子目录
        if data_type == 'quote':
            subdir = os.path.join(self.data_dir, '实时行情')
            prefix = subtype or '实时行情'
        else:  # fund_flow
            subdir = os.path.join(self.data_dir, '资金流向')
            prefix = '资金流向'

        # 确保目录存在
        os.makedirs(subdir, exist_ok=True)

        # 生成文件名
        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d')
        time_str = now.strftime('%H-%M-%S')
        filename = f"{prefix}_{date_str}_{time_str}.csv"
        filepath = os.path.join(subdir, filename)

        # 保存文件
        df.to_csv(filepath, index=False, encoding='utf-8-sig')

        return filepath

    def get_latest_files(self, subdirs=None, limit=5):
        """
        获取每个子目录最新的文件

        Args:
            subdirs: 子目录列表
            limit: 每个子目录返回的文件数量

        Returns:
            字典 {子目录: [文件路径列表]}
        """
        if subdirs is None:
            subdirs = ['实时行情', '资金流向']

        result = {}

        for subdir in subdirs:
            dir_path = os.path.join(self.data_dir, subdir)
            if not os.path.exists(dir_path):
                result[subdir] = []
                continue

            files = []
            for filename in os.listdir(dir_path):
                filepath = os.path.join(dir_path, filename)
                if os.path.isfile(filepath):
                    file_time = os.path.getmtime(filepath)
                    files.append((filepath, file_time))

            # 按修改时间排序，取最新的
            files.sort(key=lambda x: x[1], reverse=True)
            result[subdir] = [f[0] for f in files[:limit]]

        return result

    def get_file_count(self, subdirs=None):
        """获取文件统计信息"""
        if subdirs is None:
            subdirs = ['实时行情', '资金流向']

        stats = {}
        for subdir in subdirs:
            dir_path = os.path.join(self.data_dir, subdir)
            if os.path.exists(dir_path):
                count = len([f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))])
                stats[subdir] = count
            else:
                stats[subdir] = 0

        return stats
