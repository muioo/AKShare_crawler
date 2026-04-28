"""
数据获取模块
"""
import akshare as ak
import pandas as pd
from config import DATA_DIR, REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY
from utils import retry, get_timestamp, logger
from column_mapping import rename_columns
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from financial_analysis import FinancialAnalysis


class DataFetcher:
    """数据获取器"""

    def __init__(self):
        self.data_dir = DATA_DIR
        self._lock = threading.Lock()
        self.financial_analyzer = FinancialAnalysis()

    @retry(max_retries=3, delay=5)
    def fetch_financial_data(self):
        """
        获取财务报表数据
        使用: ak.stock_financial_analysis_indicator_em - 财务分析指标（东方财富）
        """
        logger.info("Fetching financial data...")
        try:
            # 获取A股财务分析指标
            df = ak.stock_financial_analysis_indicator_em()
            df = rename_columns(df, 'financial')  # 转换为中文列名
            return df, 'financial', '财务报表'
        except Exception as e:
            logger.error(f"Failed to fetch financial data: {e}")
            raise

    @retry(max_retries=3, delay=5)
    def fetch_quote_zh_a_spot(self):
        """
        获取实时股票行情 - 沪深京 A股（新浪财经）
        """
        logger.info("Fetching real-time quote data (沪深京A股) from Sina Finance...")
        try:
            df = ak.stock_zh_a_spot()
            df = rename_columns(df, 'quote')  # 转换为中文列名
            return df, 'quote', '实时行情_沪深京'
        except Exception as e:
            logger.error(f"Failed to fetch quote data (沪深京A股): {e}")
            raise

    @retry(max_retries=3, delay=5)
    def fetch_quote_zh_b_spot(self):
        """
        获取实时股票行情 - B股市场
        B股已返回中文列名，跳过重命名
        """
        logger.info("Fetching real-time quote data (B股)...")
        try:
            df = ak.stock_zh_b_spot()
            return df, 'quote', '实时行情_B股'
        except Exception as e:
            logger.error(f"Failed to fetch quote data (B股): {e}")
            raise

    @retry(max_retries=3, delay=5)
    def fetch_quote_zh_ah_spot(self):
        """
        获取实时股票行情 - AH股市场
        AH股已返回中文列名，跳过重命名
        """
        logger.info("Fetching real-time quote data (AH股)...")
        try:
            df = ak.stock_zh_ah_spot()
            return df, 'quote', '实时行情_AH股'
        except Exception as e:
            logger.error(f"Failed to fetch quote data (AH股): {e}")
            raise

    @retry(max_retries=3, delay=5)
    def fetch_quote_zh_kcb_spot(self):
        """
        获取实时股票行情 - 科创板
        科创板已返回中文列名，跳过重命名
        """
        logger.info("Fetching real-time quote data (科创版)...")
        try:
            df = ak.stock_zh_kcb_spot()
            return df, 'quote', '实时行情_科创版'
        except Exception as e:
            logger.error(f"Failed to fetch quote data (科创版): {e}")
            raise

    @retry(max_retries=3, delay=5)
    def fetch_quote_hk_spot(self):
        """
        获取实时股票行情 - 港股市场
        港股已返回中文列名，跳过重命名
        """
        logger.info("Fetching real-time quote data (港股)...")
        try:
            df = ak.stock_hk_spot()
            return df, 'quote', '实时行情_港股'
        except Exception as e:
            logger.error(f"Failed to fetch quote data (港股): {e}")
            raise

    @retry(max_retries=3, delay=5)
    def fetch_all_quote_data(self):
        """
        获取所有实时行情数据（并行获取多个数据源）
        """
        logger.info("=" * 50)
        logger.info("Starting to fetch all quote data sources in parallel...")

        # 要获取的所有行情数据源
        fetch_tasks = [
            self.fetch_quote_zh_a_spot,
            self.fetch_quote_zh_b_spot,
            self.fetch_quote_zh_ah_spot,
            self.fetch_quote_zh_kcb_spot,
            self.fetch_quote_hk_spot,
        ]

        results = {}

        # 使用线程池并行获取
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_task = {executor.submit(task): task for task in fetch_tasks}

            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    df, data_type, subtype = future.result()
                    results[subtype] = (df, data_type, subtype)
                    logger.info(f"Success: {subtype} - {len(df)} records")
                except Exception as e:
                    logger.error(f"Task {task.__name__} failed: {e}")

        # 统计结果
        success_count = len(results)
        logger.info(f"All quote data fetch completed: {success_count}/5 succeeded")
        logger.info("=" * 50)

        return results

    @retry(max_retries=3, delay=5)
    def fetch_financial_analysis(self, year=None, quarter_code=None, date=None):
        """
        获取财报分析数据
        使用: ak.stock_yjbb_em - 东方财富研报

        Args:
            year: 年份（如 2024）
            quarter_code: 季度代码（如 '1231'、'0331'、'0630'、'0930'）
            date: 完整日期字符串（格式：YYYYMMDD，如 '20241231'），优先使用date参数

        Returns:
            DataFrame: 财报分析数据
        """
        logger.info(f"Fetching financial analysis...")
        try:
            # 优先使用date参数
            if date:
                year = int(date[:4])
                quarter_code = date[4:]
            elif year is None or quarter_code is None:
                # 默认使用当前年份数据
                from datetime import datetime
                year = datetime.now().year
                quarter_code = '1231'  # 默认年报

            df = self.financial_analyzer.fetch_data(year, quarter_code)

            # 调试信息
            print(f"[data_fetcher] 获取 {year}{quarter_code} 财报分析成功")
            print(f"[data_fetcher] 数据类型: {type(df)}")
            print(f"[data_fetcher] 数据形状: {df.shape if df is not None else 'None'}")
            if df is not None and not df.empty:
                print(f"[data_fetcher] 列名: {df.columns.tolist()}")

            # 东方财富已返回中文列名，使用映射
            return df, 'financial_analysis', '财报分析'
        except Exception as e:
            logger.error(f"Failed to fetch financial analysis: {e}")
            raise

    @retry(max_retries=3, delay=5)
    def fetch_stock_history(self, symbol, market='A', period='daily', adjust='qfq', start_date=None, end_date=None):
        """
        获取个股历史行情数据

        Args:
            symbol: 股票代码（A股需要带前缀，如 sz000001 / sh600000；B股如 sh900901）
            market: 市场 ('A' - A股, 'B' - B股)
            period: 周期 ('daily' - 日线, 'weekly' - 周线, 'monthly' - 月线)
            adjust: 复权类型 ('qfq' - 前复权, 'hfq' - 后复权, '' - 不复权)
            start_date: 开始日期 (格式: 'YYYYMMDD')
            end_date: 结束日期 (格式: 'YYYYMMDD')

        Returns:
            DataFrame: 历史行情数据
        """
        logger.info(f"Fetching stock history: {symbol} ({market}股)")

        if market == 'A':
            df = ak.stock_zh_a_daily(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
            df = rename_columns(df, 'history_a')
        elif market == 'B':
            df = ak.stock_zh_b_daily(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
            df = rename_columns(df, 'history_b')
        else:
            raise ValueError(f"Unsupported market: {market}")

        logger.info(f"Fetched {len(df)} records for {symbol} ({market}股)")
        return df

    @retry(max_retries=3, delay=5)
    def fetch_growth_comparison(self, symbol):
        """
        获取同行比较数据（东方财富）

        Args:
            symbol: 股票代码（需要带市场前缀，如 SZ000895 / SH600000）

        Returns:
            DataFrame: 同行比较数据
        """
        logger.info(f"Fetching growth comparison for: {symbol}")
        try:
            df = ak.stock_zh_growth_comparison_em(symbol=symbol)
            logger.info(f"Fetched {len(df)} comparison records for {symbol}")
            return df
        except Exception as e:
            logger.error(f"Failed to fetch growth comparison for {symbol}: {e}")
            raise

    def fetch_all_quote_data_only(self):
        """
        只获取实时股票行情数据（立即爬取和自动爬取使用）

        Returns:
            字典 {subtype: (df, data_type, subtype)}
        """
        logger.info("=" * 50)
        logger.info("Starting to fetch quote data only...")

        results = self.fetch_all_quote_data()

        logger.info("=" * 50)
        logger.info(f"Quote data fetch completed: {len(results)} data sources succeeded")

        return results

    def fetch_all_parallel(self):
        """
        并行获取所有数据（财务、行情、资金流向）

        Returns:
            字典 {subtype: (df, data_type, subtype)}
        """
        logger.info("=" * 50)
        logger.info("Starting to fetch all data in parallel...")

        results = {}

        # 并行获取三大类数据
        with ThreadPoolExecutor(max_workers=3) as executor:
            # 财务报表
            future_financial = executor.submit(self.fetch_financial_data)

            # 实时行情（内部已经并行）
            future_quote = executor.submit(self.fetch_all_quote_data)

            # 财报分析
            future_financial_analysis = executor.submit(self.fetch_financial_analysis)

            # 等待并收集结果
            try:
                df, data_type, subtype = future_financial.result()
                results[subtype] = (df, data_type, subtype)
                logger.info(f"Success: {subtype}")
            except Exception as e:
                logger.error(f"Financial data fetch failed: {e}")

            try:
                quote_results = future_quote.result()
                results.update(quote_results)
            except Exception as e:
                logger.error(f"Quote data fetch failed: {e}")

            try:
                df, data_type, subtype = future_financial_comparison.result()
                results[subtype] = (df, data_type, subtype)
                logger.info(f"Success: {subtype}")
            except Exception as e:
                logger.error(f"Financial comparison data fetch failed: {e}")

        logger.info("=" * 50)
        logger.info(f"Parallel fetch completed: {len(results)} data sources succeeded")

        return results

    def fetch_all(self):
        """
        获取所有数据（财务、行情、资金流向）- 串行方式，保持兼容性
        """
        logger.info("=" * 50)
        logger.info("Starting to fetch all data...")

        results = {
            'financial': None,
            'quote': None,
            'fund_flow': None,
        }

        try:
            # 1. 获取财务报表
            results['financial'] = self.fetch_financial_data()
        except Exception as e:
            logger.error(f"Financial data fetch failed: {e}")

        try:
            # 2. 获取所有实时行情（多个数据源）
            results['quote'] = self.fetch_all_quote_data()
        except Exception as e:
            logger.error(f"Quote data fetch failed: {e}")

        try:
            # 3. 获取财报分析
            results['financial_analysis'] = self.fetch_financial_analysis()
        except Exception as e:
            logger.error(f"Financial analysis data fetch failed: {e}")

        logger.info("=" * 50)
        return results


if __name__ == '__main__':
    fetcher = DataFetcher()
    fetcher.fetch_all_parallel()
