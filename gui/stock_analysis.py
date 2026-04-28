"""
单股分析模块 - 获取单股历史数据并展示（支持日期选择，带单位显示）
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from gui.chart_widget import ChartWidget
import os
import sys
import platform
import calendar
import matplotlib.pyplot as plt


# ========== 修复：跨平台中文字体设置 ==========
def setup_chinese_font():
    """根据操作系统设置中文字体"""
    system = platform.system()

    if system == 'Windows':
        font_list = ['SimHei', 'Microsoft YaHei', 'SimSun', 'NSimSun', 'FangSong']
    elif system == 'Darwin':
        font_list = ['STHeiti', 'Heiti TC', 'PingFang SC', 'Arial Unicode MS']
    else:
        font_list = ['WenQuanYi Micro Hei', 'Noto Sans CJK SC', 'DejaVu Sans']

    for font in font_list:
        try:
            plt.rcParams['font.sans-serif'] = [font] + plt.rcParams['font.sans-serif']
            plt.rcParams['axes.unicode_minus'] = False
            print(f"成功设置中文字体: {font}")
            return
        except:
            continue

    plt.rcParams['font.sans-serif'] = ['sans-serif']
    plt.rcParams['axes.unicode_minus'] = False


setup_chinese_font()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_fetcher import DataFetcher
from config import DATA_DIR


class StockAnalysisPanel:
    """单股分析面板"""

    def __init__(self, parent):
        self.parent = parent
        self.current_stock_code = None
        self.current_market = 'A'
        self.current_data = None
        self.data_fetcher = DataFetcher()
        self.available_years = [str(year) for year in range(1990, datetime.now().year + 1)]
        self.available_months = [f"{month:02d}" for month in range(1, 13)]
        self.start_date_var = tk.StringVar()
        self.end_date_var = tk.StringVar()

        self.history_dir = os.path.join(DATA_DIR, '历史行情')
        os.makedirs(self.history_dir, exist_ok=True)

        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        search_frame = ttk.Frame(self.parent)
        search_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(search_frame, text="股票代码:").pack(side=tk.LEFT, padx=5)
        self.stock_code_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.stock_code_var, width=15).pack(side=tk.LEFT, padx=5)

        ttk.Label(search_frame, text="市场:").pack(side=tk.LEFT, padx=(15, 5))
        self.market_var = tk.StringVar(value='A')
        ttk.Radiobutton(search_frame, text="A股", variable=self.market_var, value='A').pack(side=tk.LEFT)
        ttk.Radiobutton(search_frame, text="B股", variable=self.market_var, value='B').pack(side=tk.LEFT, padx=(0, 10))

        date_frame = ttk.LabelFrame(self.parent, text="日期范围", padding="5")
        date_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(date_frame, text="起始日期:").pack(side=tk.LEFT, padx=5)
        self._create_date_dropdowns(date_frame, 'start', datetime.now() - timedelta(days=30))

        ttk.Label(date_frame, text="截止日期:").pack(side=tk.LEFT, padx=(15, 5))
        self._create_date_dropdowns(date_frame, 'end', datetime.now())

        ttk.Button(date_frame, text="近一周", command=lambda: self.set_date_range(7)).pack(side=tk.LEFT, padx=2)
        ttk.Button(date_frame, text="近一月", command=lambda: self.set_date_range(30)).pack(side=tk.LEFT, padx=2)
        ttk.Button(date_frame, text="近三月", command=lambda: self.set_date_range(90)).pack(side=tk.LEFT, padx=2)
        ttk.Button(date_frame, text="近一年", command=lambda: self.set_date_range(365)).pack(side=tk.LEFT, padx=2)
        ttk.Button(date_frame, text="今年", command=self.set_year_to_date).pack(side=tk.LEFT, padx=2)
        ttk.Button(date_frame, text="全部", command=self.set_all_time).pack(side=tk.LEFT, padx=2)

        ttk.Label(date_frame, text="请通过下拉框选择日期", foreground="gray").pack(side=tk.LEFT, padx=10)

        button_frame = ttk.Frame(self.parent)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(button_frame, text="查询", command=self.search_stock, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="保存CSV", command=self.save_to_csv, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Label(button_frame, text="提示: 请输入完整代码，如 sz000001 / sh600000（A股）/ sh900901（B股）", foreground="gray").pack(side=tk.LEFT, padx=10)

        # ====================== 信息区域（表格，显示全部数据） ======================
        info_frame = ttk.LabelFrame(self.parent, text="基本信息", padding="10")
        info_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 创建带滚动条的表格
        tree_container = ttk.Frame(info_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)

        self.info_tree = ttk.Treeview(tree_container, show="headings")
        self.info_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 垂直滚动条
        v_scroll = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.info_tree.yview)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.info_tree.configure(yscrollcommand=v_scroll.set)

        # 水平滚动条
        h_scroll = ttk.Scrollbar(info_frame, orient=tk.HORIZONTAL, command=self.info_tree.xview)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.info_tree.configure(xscrollcommand=h_scroll.set)

        # 图表类型
        chart_type_frame = ttk.Frame(self.parent)
        chart_type_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(chart_type_frame, text="图表类型:").pack(side=tk.LEFT, padx=5)
        self.chart_type_var = tk.StringVar(value='line')
        chart_types = [('收盘价走势', 'line'), ('日涨跌幅', 'bar'), ('成交量走势', 'volume')]
        for text, value in chart_types:
            ttk.Radiobutton(chart_type_frame, text=text, variable=self.chart_type_var, value=value, command=self.update_chart).pack(side=tk.LEFT, padx=5)

        ttk.Button(chart_type_frame, text="🔍 放大图表", command=self.show_enlarged_chart, width=15).pack(side=tk.RIGHT, padx=5)

        chart_frame = ttk.LabelFrame(self.parent, text="历史走势", padding="10")
        chart_frame.pack(fill=tk.BOTH, expand=True)
        self.chart_widget = ChartWidget(chart_frame, figsize=(10, 5))

    def _create_date_dropdowns(self, parent, prefix, default_date):
        """创建年/月/日三级只读下拉框。"""
        year_var = tk.StringVar(value=str(default_date.year))
        month_var = tk.StringVar(value=f"{default_date.month:02d}")
        day_var = tk.StringVar(value=f"{default_date.day:02d}")
        setattr(self, f"{prefix}_year_var", year_var)
        setattr(self, f"{prefix}_month_var", month_var)
        setattr(self, f"{prefix}_day_var", day_var)

        year_combo = ttk.Combobox(parent, textvariable=year_var, values=self.available_years, state='readonly', width=6)
        month_combo = ttk.Combobox(parent, textvariable=month_var, values=self.available_months, state='readonly', width=4)
        day_combo = ttk.Combobox(parent, textvariable=day_var, state='readonly', width=4)
        setattr(self, f"{prefix}_day_combo", day_combo)

        year_combo.pack(side=tk.LEFT, padx=(0, 2))
        ttk.Label(parent, text="-").pack(side=tk.LEFT)
        month_combo.pack(side=tk.LEFT, padx=2)
        ttk.Label(parent, text="-").pack(side=tk.LEFT)
        day_combo.pack(side=tk.LEFT, padx=(2, 5))

        year_combo.bind('<<ComboboxSelected>>', lambda _event, key=prefix: self._on_date_part_changed(key))
        month_combo.bind('<<ComboboxSelected>>', lambda _event, key=prefix: self._on_date_part_changed(key))
        day_combo.bind('<<ComboboxSelected>>', lambda _event: self._sync_date_vars())

        self._update_day_values(prefix)
        self._sync_date_vars()

    def _on_date_part_changed(self, prefix):
        """年份或月份变化时刷新日期下拉值。"""
        self._update_day_values(prefix)
        self._sync_date_vars()

    def _update_day_values(self, prefix):
        """根据当前年月更新对应的日期列表。"""
        year = int(getattr(self, f"{prefix}_year_var").get())
        month = int(getattr(self, f"{prefix}_month_var").get())
        max_day = calendar.monthrange(year, month)[1]
        day_values = [f"{day:02d}" for day in range(1, max_day + 1)]
        day_var = getattr(self, f"{prefix}_day_var")
        day_combo = getattr(self, f"{prefix}_day_combo")
        day_combo['values'] = day_values
        if day_var.get() not in day_values:
            day_var.set(day_values[-1])

    def _set_date_picker(self, prefix, date_value):
        """按指定日期更新年/月/日下拉框。"""
        getattr(self, f"{prefix}_year_var").set(str(date_value.year))
        getattr(self, f"{prefix}_month_var").set(f"{date_value.month:02d}")
        self._update_day_values(prefix)
        getattr(self, f"{prefix}_day_var").set(f"{date_value.day:02d}")
        self._sync_date_vars()

    def _sync_date_vars(self):
        """同步维护 YYYYMMDD 字符串，供查询和导出复用。"""
        if hasattr(self, 'start_year_var') and hasattr(self, 'start_month_var') and hasattr(self, 'start_day_var'):
            self.start_date_var.set(self._get_date_string('start'))
        if hasattr(self, 'end_year_var') and hasattr(self, 'end_month_var') and hasattr(self, 'end_day_var'):
            self.end_date_var.set(self._get_date_string('end'))

    def _get_date_string(self, prefix):
        """从年月日下拉框拼出 YYYYMMDD 字符串。"""
        year = getattr(self, f"{prefix}_year_var").get()
        month = getattr(self, f"{prefix}_month_var").get()
        day = getattr(self, f"{prefix}_day_var").get()
        return f"{year}{month}{day}"

    def set_date_range(self, days):
        end = datetime.now()
        start = end - timedelta(days=days)
        self._set_date_picker('end', end)
        self._set_date_picker('start', start)

    def set_year_to_date(self):
        now = datetime.now()
        start = datetime(now.year, 1, 1)
        self._set_date_picker('end', now)
        self._set_date_picker('start', start)

    def set_all_time(self):
        self._set_date_picker('start', datetime(1990, 1, 1))
        self._set_date_picker('end', datetime.now())

    def validate_dates(self):
        self._sync_date_vars()
        start_str = self.start_date_var.get().strip()
        end_str = self.end_date_var.get().strip()
        if len(start_str) != 8 or len(end_str) != 8:
            messagebox.showerror("错误", "日期选择无效，请重新选择日期")
            return None, None
        try:
            start_date = datetime.strptime(start_str, '%Y%m%d')
            end_date = datetime.strptime(end_str, '%Y%m%d')
        except ValueError:
            messagebox.showerror("错误", "日期选择无效，请重新选择日期")
            return None, None
        if start_date > end_date:
            messagebox.showerror("错误", "起始日期不能晚于截止日期")
            return None, None
        if end_date > datetime.now():
            end_date = datetime.now()
            end_str = end_date.strftime('%Y%m%d')
            self._set_date_picker('end', end_date)
        return start_str, end_str

    def format_volume(self, volume):
        if pd.isna(volume): return "0手"
        volume_shou = volume / 100
        if volume_shou >= 10000: return f"{volume_shou/10000:.2f}万手"
        else: return f"{volume_shou:.0f}手"

    def format_amount(self, amount):
        if pd.isna(amount) or amount == 0: return "0元"
        if amount >= 100000000: return f"{amount/100000000:.2f}亿元"
        elif amount >= 10000: return f"{amount/10000:.2f}万元"
        else: return f"{amount:.2f}元"

    def format_chart_volume(self, volume_shou):
        """格式化图表中的成交量文本，输入单位为手。"""
        if pd.isna(volume_shou):
            return "N/A"
        if volume_shou >= 10000:
            return f"{volume_shou / 10000:.2f}万手"
        return f"{volume_shou:.0f}手"

    def format_chart_price(self, price):
        """格式化图表中的价格文本。"""
        if pd.isna(price):
            return "N/A"
        return f"{price:.2f}"

    def format_percentage_text(self, value):
        """格式化百分比文本，缺失值统一显示为 N/A。"""
        if pd.isna(value):
            return "N/A"
        return f"{value:+.2f}%"

    def format_ratio_text(self, value):
        """格式化倍数文本，缺失值统一显示为 N/A。"""
        if pd.isna(value):
            return "N/A"
        return f"{value:.2f}倍"

    def get_latest_valid_value(self, values):
        """获取序列中最后一个有效值，用于展示最新状态。"""
        valid_values = pd.Series(values, dtype="float64").dropna()
        if valid_values.empty:
            return float('nan')
        return valid_values.iloc[-1]

    def calculate_period_return(self, values, period):
        """
        计算最近 N 日收益率。

        这里按“最新值”与“向前第 N 个有效值”比较，样本不足时返回 NaN。
        """
        valid_values = pd.Series(values, dtype="float64").dropna().reset_index(drop=True)
        if len(valid_values) <= period:
            return float('nan')

        latest_value = valid_values.iloc[-1]
        base_value = valid_values.iloc[-period - 1]
        if base_value == 0:
            return 0.0

        return ((latest_value - base_value) / base_value) * 100

    def calculate_window_drawdown(self, values, window):
        """
        计算最近窗口期内相对最高点的回撤。

        样本不足时返回 NaN，避免把更短区间误当成 60 日区间。
        """
        valid_values = pd.Series(values, dtype="float64").dropna().reset_index(drop=True)
        if len(valid_values) < window:
            return float('nan')

        window_values = valid_values.iloc[-window:]
        latest_value = window_values.iloc[-1]
        peak_value = window_values.max()
        if peak_value == 0:
            return 0.0

        return ((latest_value - peak_value) / peak_value) * 100

    def calculate_moving_average(self, values, window):
        """计算最近窗口期均值，样本不足时返回 NaN。"""
        valid_values = pd.Series(values, dtype="float64").dropna().reset_index(drop=True)
        if len(valid_values) < window:
            return float('nan')
        return valid_values.iloc[-window:].mean()

    def build_close_chart_info(self, close_prices):
        """
        构建收盘价走势图的实用摘要指标。

        这些指标直接服务于趋势判断与风险评估：
        1. 5/20/60 日收益率看短中期趋势强弱。
        2. 60 日回撤看当前位置距离阶段高点有多远。
        """
        latest_close = self.get_latest_valid_value(close_prices)
        info_lines = [
            f"最新收盘: {latest_close:.2f}" if pd.notna(latest_close) else "最新收盘: N/A",
            f"5日收益: {self.format_percentage_text(self.calculate_period_return(close_prices, 5))}",
            f"20日收益: {self.format_percentage_text(self.calculate_period_return(close_prices, 20))}",
            f"60日收益: {self.format_percentage_text(self.calculate_period_return(close_prices, 60))}",
            f"60日回撤: {self.format_percentage_text(self.calculate_window_drawdown(close_prices, 60))}",
        ]
        return {
            "title": "价格关键指标",
            "lines": info_lines,
            "facecolor": "#eef6ff",
            "edgecolor": "#4a90e2",
        }

    def build_volume_chart_info(self, volumes):
        """
        构建成交量走势图的实用摘要指标。

        这些指标直接服务于量能确认：
        1. 最新量和 5/20 日均量看当前量能位置。
        2. 量比和 5/20 均量比看是放量确认还是量能不足。
        """
        latest_volume = self.get_latest_valid_value(volumes)
        volume_ma_5 = self.calculate_moving_average(volumes, 5)
        volume_ma_20 = self.calculate_moving_average(volumes, 20)

        volume_ratio = float('nan')
        if pd.notna(latest_volume) and pd.notna(volume_ma_20) and volume_ma_20 != 0:
            volume_ratio = latest_volume / volume_ma_20

        volume_ma_ratio = float('nan')
        if pd.notna(volume_ma_5) and pd.notna(volume_ma_20) and volume_ma_20 != 0:
            volume_ma_ratio = volume_ma_5 / volume_ma_20

        info_lines = [
            f"最新成交量: {self.format_chart_volume(latest_volume)}",
            f"5日均量: {self.format_chart_volume(volume_ma_5)}",
            f"20日均量: {self.format_chart_volume(volume_ma_20)}",
            f"量比(现/20均): {self.format_ratio_text(volume_ratio)}",
            f"5/20均量比: {self.format_ratio_text(volume_ma_ratio)}",
        ]
        return {
            "title": "量能关键指标",
            "lines": info_lines,
            "facecolor": "#fff4e8",
            "edgecolor": "#d9822b",
        }

    def calculate_turning_point_annotations(self, dates, values, value_formatter=None):
        """
        计算折线图转折点标注。

        标注规则：
        1. 只在趋势反转的高点或低点显示标注，普通点不显示文字。
        2. 上升转下降时，高点与前一个已确认低点比较，显示增长率。
        3. 下降转上升时，低点与前一个已确认高点比较，显示下降率。
        4. 如果前面没有已确认的相反转折点，则当前首个转折点不显示增长率或下降率。
        5. 标注只显示增长率/下降率和对比用的前一个转折点日期，避免图上文字过长。
        6. 遇到 NaN 自动跳过，基准值为 0 时按 0% 处理，避免除零。

        Args:
            dates: 日期列表
            values: 数值列表
            value_formatter: 数值格式化函数

        Returns:
            list[dict | None]: 与原始数据等长的标注配置列表
        """
        annotations = [None] * len(values)
        if value_formatter is None:
            value_formatter = lambda value: f"{value:.2f}" if pd.notna(value) else "N/A"

        ordered_points = []
        for index, (date_value, point_value) in enumerate(zip(dates, values)):
            if pd.isna(point_value):
                continue
            parsed_date = pd.to_datetime(date_value, errors="coerce")
            sort_key = parsed_date if pd.notna(parsed_date) else pd.Timestamp.max
            ordered_points.append(
                {
                    "index": index,
                    "date": date_value,
                    "value": point_value,
                    "sort_key": sort_key,
                }
            )

        ordered_points.sort(key=lambda point: (point["sort_key"], point["index"]))

        if len(ordered_points) < 2:
            return annotations

        previous_point = ordered_points[0]
        trend = None
        last_peak_point = None
        last_trough_point = None

        for current_point in ordered_points[1:]:
            previous_value = previous_point["value"]
            current_value = current_point["value"]

            if current_value == previous_value:
                previous_point = current_point
                continue

            current_trend = 'up' if current_value > previous_value else 'down'

            if trend is None:
                trend = current_trend
                previous_point = current_point
                continue

            if trend == 'up' and current_trend == 'down':
                peak_point = previous_point
                if last_trough_point is not None:
                    base_value = last_trough_point["value"]
                    peak_value = peak_point["value"]
                    rate = 0.0 if base_value == 0 else ((peak_value - base_value) / base_value) * 100
                    annotations[peak_point["index"]] = {
                        "text": (
                            f"增长率: {rate:.2f}%\n"
                            f"对比: {last_trough_point['date']}"
                        ),
                        "color": "#ff4444",
                        "xytext": (0, 8),
                        "va": "bottom",
                    }
                last_peak_point = peak_point

            elif trend == 'down' and current_trend == 'up':
                trough_point = previous_point
                if last_peak_point is not None:
                    base_value = last_peak_point["value"]
                    trough_value = trough_point["value"]
                    rate = 0.0 if base_value == 0 else ((base_value - trough_value) / base_value) * 100
                    annotations[trough_point["index"]] = {
                        "text": (
                            f"下降率: {rate:.2f}%\n"
                            f"对比: {last_peak_point['date']}"
                        ),
                        "color": "#44aa44",
                        "xytext": (0, -12),
                        "va": "top",
                    }
                last_trough_point = trough_point

            trend = current_trend
            previous_point = current_point

        return annotations

    def build_chronological_chart_dataframe(self):
        """
        按日期升序整理单股分析图表数据，确保“前一个数据”始终是更早的交易日。

        Returns:
            pandas.DataFrame: 已按日期升序排序的图表数据
        """
        chart_df = self.current_data.copy()
        chart_df["_chart_date_sort_key"] = pd.to_datetime(chart_df["日期"], errors="coerce")
        chart_df = chart_df.sort_values(
            by="_chart_date_sort_key",
            ascending=True,
            kind="stable",
            na_position="last",
        ).reset_index(drop=True)
        return chart_df.drop(columns=["_chart_date_sort_key"])

    def search_stock(self):
        stock_code = self.stock_code_var.get().strip()
        if not stock_code:
            messagebox.showwarning("警告", "请输入股票代码")
            return
        start_date, end_date = self.validate_dates()
        if start_date is None: return

        market = self.market_var.get()
        self.current_market = market
        try:
            self.current_stock_code = stock_code
            df = self.data_fetcher.fetch_stock_history(
                symbol=stock_code, market=market, period='daily', adjust='qfq',
                start_date=start_date, end_date=end_date
            )
            if df.empty:
                messagebox.showwarning("提示", "未找到数据")
                return
            self.current_data = df
            self.show_info(df)
            self.update_chart()
        except Exception as e:
            messagebox.showerror("错误", f"查询失败: {str(e)}")

    def show_info(self, df):
        """
        严格按照 HISTORY_A_COLUMNS / HISTORY_B_COLUMNS 显示所有字段
        A股：日期、开盘、最高、最低、收盘、成交量、成交额、流动股本、换手率
        B股：日期、开盘、收盘、最高、最低、成交量、流动股本、换手率
        """
        # 清空表格
        for item in self.info_tree.get_children():
            self.info_tree.delete(item)

        # ============= A 股 显示全部字段 =============
        if self.current_market == "A":
            cols = [
                "日期", "开盘", "最高", "最低", "收盘",
                "成交量", "成交额", "流动股本", "换手率"
            ]

        # ============= B 股 显示对应字段 =============
        else:
            cols = [
                "日期", "开盘", "收盘", "最高", "最低",
                "成交量", "流动股本", "换手率"
            ]

        # 设置表格列
        self.info_tree["columns"] = cols
        for col in cols:
            self.info_tree.heading(col, text=col)
            self.info_tree.column(col, width=100, anchor=tk.CENTER)

        # 插入所有数据行（按日期从新到旧）
        for idx, row in df.iterrows():
            values = []
            for col in cols:
                val = row.get(col, "")

                # 数值格式化
                if col in ["开盘", "最高", "最低", "收盘"]:
                    values.append(f"{val:.2f}" if pd.notna(val) else "")
                elif col == "成交量":
                    values.append(self.format_volume(val))
                elif col == "成交额":
                    values.append(self.format_amount(val))
                elif col == "换手率":
                    values.append(f"{val:.2%}" if pd.notna(val) else "")
                elif col == "流动股本":
                    values.append(f"{val:.0f}" if pd.notna(val) else "")
                else:
                    values.append(str(val))

            self.info_tree.insert("", tk.END, values=values)

    def update_chart(self):
        if self.current_data is None or self.current_data.empty: return
        chart_type = self.chart_type_var.get()
        df = self.build_chronological_chart_dataframe()
        dates = df['日期'].tolist()

        if chart_type == 'line':
            close_prices = df['收盘'].tolist()
            # 仅在转折点标注与前一极值相比的增长率/下降率，并显示基准日期和价格
            annotations = self.calculate_turning_point_annotations(dates, close_prices, self.format_chart_price)
            info_box = self.build_close_chart_info(close_prices)
            self.chart_widget.plot_line(dates, close_prices,
                title=f'{self.current_stock_code} 收盘价走势', xlabel='日期', ylabel='收盘价（元）', color='blue', show_values=False, annotations=annotations, info_box=info_box)

        elif chart_type == 'bar':
            # 根据收盘价计算涨跌幅
            close = df['收盘'].tolist()
            changes = []
            for i in range(len(close)):
                if i == 0:
                    # 第一天没有前一天数据，设为0
                    changes.append(0)
                else:
                    prev_close = close[i-1]
                    curr_close = close[i]
                    if pd.isna(prev_close) or pd.isna(curr_close) or prev_close == 0:
                        changes.append(0)
                    else:
                        change_pct = ((curr_close - prev_close) / prev_close) * 100
                        changes.append(change_pct)

            self.chart_widget.plot_bar(dates, changes,
                title=f'{self.current_stock_code} 日涨跌幅', xlabel='日期', ylabel='涨跌幅（%）', show_values=False)

        elif chart_type == 'volume':
            volumes = [v/100 for v in df['成交量'].tolist()]
            # 仅在转折点标注与前一极值相比的增长率/下降率，并显示基准日期和成交量
            annotations = self.calculate_turning_point_annotations(dates, volumes, self.format_chart_volume)
            info_box = self.build_volume_chart_info(volumes)
            self.chart_widget.plot_line(dates, volumes,
                title=f'{self.current_stock_code} 成交量走势', xlabel='日期', ylabel='成交量（手）', color='orange', show_values=False, annotations=annotations, info_box=info_box)

    def show_enlarged_chart(self):
        """显示放大的图表窗口（支持缩放和平移）"""
        if self.current_data is None or self.current_data.empty:
            messagebox.showwarning("警告", "没有数据，请先查询股票")
            return

        # 创建新窗口
        enlarged_window = tk.Toplevel(self.parent)
        enlarged_window.title(f"{self.current_stock_code} - 放大图表（支持滚轮缩放和拖动）")
        enlarged_window.geometry("1400x1000")

        # 创建控制面板
        control_frame = ttk.Frame(enlarged_window)
        control_frame.pack(fill=tk.X, pady=5, padx=5)

        ttk.Label(control_frame, text="操作提示: 🖱️ 滚轮缩放 | 拖动平移 | 🏠 恢复视图").pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="关闭", command=enlarged_window.destroy).pack(side=tk.RIGHT, padx=5)

        # 创建图表容器
        chart_container = ttk.Frame(enlarged_window)
        chart_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 创建放大的图表组件（启用导航工具栏）
        enlarged_chart = ChartWidget(chart_container, figsize=(14, 8), enable_navigation=True)

        # 获取当前图表类型并绘制
        chart_type = self.chart_type_var.get()
        df = self.build_chronological_chart_dataframe()
        dates = df['日期'].tolist()

        if chart_type == 'line':
            close_prices = df['收盘'].tolist()
            # 仅在转折点标注与前一极值相比的增长率/下降率，并显示基准日期和价格
            annotations = self.calculate_turning_point_annotations(dates, close_prices, self.format_chart_price)
            info_box = self.build_close_chart_info(close_prices)
            enlarged_chart.plot_line(dates, close_prices,
                title=f'{self.current_stock_code} 收盘价走势（放大）', xlabel='日期', ylabel='收盘价（元）', color='blue', show_values=False, annotations=annotations, info_box=info_box)

        elif chart_type == 'bar':
            # 根据收盘价计算涨跌幅
            close = df['收盘'].tolist()
            changes = []
            for i in range(len(close)):
                if i == 0:
                    changes.append(0)
                else:
                    prev_close = close[i-1]
                    curr_close = close[i]
                    if pd.isna(prev_close) or pd.isna(curr_close) or prev_close == 0:
                        changes.append(0)
                    else:
                        change_pct = ((curr_close - prev_close) / prev_close) * 100
                        changes.append(change_pct)

            enlarged_chart.plot_bar(dates, changes,
                title=f'{self.current_stock_code} 日涨跌幅（放大）', xlabel='日期', ylabel='涨跌幅（%）', show_values=True)

        elif chart_type == 'volume':
            volumes = [v/100 for v in df['成交量'].tolist()]
            # 仅在转折点标注与前一极值相比的增长率/下降率，并显示基准日期和成交量
            annotations = self.calculate_turning_point_annotations(dates, volumes, self.format_chart_volume)
            info_box = self.build_volume_chart_info(volumes)
            enlarged_chart.plot_line(dates, volumes,
                title=f'{self.current_stock_code} 成交量走势（放大）', xlabel='日期', ylabel='成交量（手）', color='orange', show_values=False, annotations=annotations, info_box=info_box)

    def save_to_csv(self):
        if self.current_data is None or self.current_data.empty:
            messagebox.showwarning("警告", "没有数据可保存")
            return

        try:
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            market = 'A股' if self.current_market == 'A' else 'B股'
            default_filename = f"{self.current_stock_code}_{market}_{self.start_date_var.get()}_{self.end_date_var.get()}_{timestamp}.csv"

            # 打开文件选择对话框
            filepath = filedialog.asksaveasfilename(
                title="保存CSV文件",
                defaultextension=".csv",
                initialfile=default_filename,
                initialdir=self.history_dir,
                filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
            )

            if not filepath:  # 用户取消了保存
                return

            with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
                f.write("# 单位：价格(元),成交量(股),成交额(元),换手率(%)\n")
                self.current_data.to_csv(f, index=False)

            messagebox.showinfo("成功", f"已保存：\n{filepath}")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败：{str(e)}")
