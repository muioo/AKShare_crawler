"""
配置文件
"""
import os

# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 数据存储目录
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# 定时任务配置
SCHEDULE_TIMES = ['09:30', '15:00']  # 每天 9:30 和 15:00 执行

# 请求配置
REQUEST_TIMEOUT = 30  # 请求超时时间（秒）
MAX_RETRIES = 3  # 最大重试次数
RETRY_DELAY = 5  # 重试间隔（秒）

# 数据类型标识
DATA_TYPES = {
    'quote': '实时行情',
    'quote_沪深京A股': '实时行情_沪深京',
    'quote_B股': '实时行情_B股',
    'quote_AH股': '实时行情_AH股',
    'quote_科创版': '实时行情_科创版',
    'quote_港股': '实时行情_港股',
    'fund_flow': '资金流向',
}

# 数据源说明
# 实时行情_沪深京：新浪财经 - ak.stock_zh_a_spot
# 实时行情_B股：ak.stock_zh_b_spot
# 实时行情_AH股：ak.stock_zh_ah_spot
# 实时行情_科创版：ak.stock_zh_kcb_spot
# 实时行情_港股：ak.stock_hk_spot
# 资金流向：同花顺 - ak.stock_fund_flow_individual
