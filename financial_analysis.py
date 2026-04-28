"""
财报分析模块 - 使用ak.stock_yjbb_em获取财报数据
"""
import akshare as ak
import pandas as pd
from config import REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY
from utils import retry, logger


class FinancialAnalysis:
    """财报分析数据获取器"""

    # 列名映射（简化显示）
    COLUMN_MAPPING = {
        '序号': '序号',
        '股票代码': '股票代码',
        '股票简称': '股票简称',
        '每股收益': '每股收益(元)',
        '营业总收入-营业总收入': '营业总收入(元)',
        '营业总收入-同比增长': '营收同比增长(%)',
        '营业总收入-季度环比增长': '营收环比增长(%)',
        '净利润-净利润': '净利润(元)',
        '净利润-同比增长': '净利润同比增长(%)',
        '净利润-季度环比增长': '净利润环比增长(%)',
        '每股净资产': '每股净资产(元)',
        '净资产收益率': '净资产收益率(%)',
        '每股经营现金流量': '每股经营现金流量(元)',
        '销售毛利率': '销售毛利率(%)',
        '所处行业': '所处行业',
        '最新公告日期': '最新公告日期',
    }

    # 支持的季度
    QUARTERS = {
        '一季报': '0331',
        '中报': '0630',
        '三季报': '0930',
        '年报': '1231',
    }

    def __init__(self):
        self.current_date = None

    @retry(max_retries=3, delay=5)
    def fetch_data(self, year, quarter_code):
        """
        获取指定年份和季度的财报数据

        Args:
            year: 年份，如 2024
            quarter_code: 季度代码，如 '0331'、'0630'、'0930'、'1231'

        Returns:
            DataFrame: 财报分析数据
        """
        # 构建date参数：YYYYMMDD格式
        date = f"{year}{quarter_code}"
        self.current_date = date

        logger.info(f"正在获取财报分析数据: {date}")

        try:
            df = ak.stock_yjbb_em(date=date)

            if df is None or df.empty:
                logger.warning(f"未获取到 {date} 的财报数据")
                return pd.DataFrame()

            # 列名映射
            df = self._rename_columns(df)

            logger.info(f"成功获取 {date} 财报数据，共 {len(df)} 条")

            return df

        except Exception as e:
            logger.error(f"获取财报数据失败 {date}: {e}")
            raise

    def _rename_columns(self, df):
        """
        重命名列，简化显示

        Args:
            df: 原始DataFrame

        Returns:
            DataFrame: 重命名后的DataFrame
        """
        return df.rename(columns=self.COLUMN_MAPPING)

    @staticmethod
    def get_available_years(start_year=2010):
        """
        获取可用的年份列表

        Args:
            start_year: 起始年份，默认2010（数据从20100331开始）

        Returns:
            list: 年份列表，从start_year到当前年份
        """
        from datetime import datetime
        current_year = datetime.now().year
        return list(range(start_year, current_year + 1))

    @staticmethod
    def get_available_quarters():
        """
        获取可用的季度

        Returns:
            dict: 季度名称到季度代码的映射
        """
        return FinancialAnalysis.QUARTERS.copy()

    @staticmethod
    def format_date(year, quarter_code):
        """
        格式化日期为字符串

        Args:
            year: 年份
            quarter_code: 季度代码

        Returns:
            str: 格式化的日期字符串
        """
        quarter_name = {v: k for k, v in FinancialAnalysis.QUARTERS.items()}.get(quarter_code, quarter_code)
        return f"{year}年{quarter_name}"

    def get_current_date(self):
        """获取当前查询的日期"""
        return self.current_date


if __name__ == '__main__':
    # 测试代码
    fa = FinancialAnalysis()

    print("可用年份:", fa.get_available_years())
    print("可用季度:", fa.get_available_quarters())

    # 测试获取数据
    print("\n测试获取2024年年报数据...")
    df = fa.fetch_data(2024, '1231')

    if not df.empty:
        print(f"获取成功，共 {len(df)} 条数据")
        print(f"列名: {df.columns.tolist()}")
        print("\n前3条数据:")
        print(df.head(3))
