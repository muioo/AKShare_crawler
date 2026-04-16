"""
AKShare 股票数据爬取 - 主程序
功能：定时获取全部A股的财务报表、实时行情和资金流向数据
"""
import argparse
from data_fetcher import DataFetcher
from scheduler import DataScheduler
from utils import logger


def run_once():
    """单次运行模式 - 立即获取数据"""
    logger.info("Running in single-execution mode")
    fetcher = DataFetcher()
    results = fetcher.fetch_all()
    return results


def run_scheduled():
    """定时运行模式 - 按配置的时间定时获取数据"""
    logger.info("Running in scheduled mode")
    scheduler = DataScheduler()
    scheduler.run()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='AKShare 股票数据爬取工具')
    parser.add_argument(
        '--mode',
        choices=['once', 'scheduled'],
        default='once',
        help='运行模式: once(单次执行), scheduled(定时执行)'
    )

    args = parser.parse_args()

    try:
        if args.mode == 'once':
            run_once()
        elif args.mode == 'scheduled':
            run_scheduled()
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
    except Exception as e:
        logger.error(f"Program error: {e}")
        raise


if __name__ == '__main__':
    main()
