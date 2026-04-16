"""
单股分析模块 - 获取单股历史数据并展示（支持日期选择，带单位显示）
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from AKShare_crawl.gui.chart_widget import ChartWidget
import os
import sys
import platform
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
from AKShare_crawl.data_fetcher import DataFetcher
from AKShare_crawl.config import DATA_DIR


class StockAnalysisPanel:
    """单股分析面板"""

    def __init__(self, parent):
        self.parent = parent
        self.current_stock_code = None
        self.current_market = 'A'
        self.current_data = None
        self.data_fetcher = DataFetcher()

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
        self.start_date_var = tk.StringVar()
        default_start = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        self.start_date_var.set(default_start)
        ttk.Entry(date_frame, textvariable=self.start_date_var, width=12).pack(side=tk.LEFT, padx=5)

        ttk.Label(date_frame, text="截止日期:").pack(side=tk.LEFT, padx=(15, 5))
        self.end_date_var = tk.StringVar()
        default_end = datetime.now().strftime('%Y%m%d')
        self.end_date_var.set(default_end)
        ttk.Entry(date_frame, textvariable=self.end_date_var, width=12).pack(side=tk.LEFT, padx=5)

        ttk.Button(date_frame, text="近一周", command=lambda: self.set_date_range(7)).pack(side=tk.LEFT, padx=2)
        ttk.Button(date_frame, text="近一月", command=lambda: self.set_date_range(30)).pack(side=tk.LEFT, padx=2)
        ttk.Button(date_frame, text="近三月", command=lambda: self.set_date_range(90)).pack(side=tk.LEFT, padx=2)
        ttk.Button(date_frame, text="近一年", command=lambda: self.set_date_range(365)).pack(side=tk.LEFT, padx=2)
        ttk.Button(date_frame, text="今年", command=self.set_year_to_date).pack(side=tk.LEFT, padx=2)
        ttk.Button(date_frame, text="全部", command=self.set_all_time).pack(side=tk.LEFT, padx=2)

        tk.Label(date_frame, text="格式: YYYYMMDD", foreground="gray").pack(side=tk.LEFT, padx=10)

        button_frame = ttk.Frame(self.parent)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(button_frame, text="查询", command=self.search_stock, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="保存CSV", command=self.save_to_csv, width=15).pack(side=tk.LEFT, padx=5)
        tk.Label(button_frame, text="提示: 请输入完整代码，如 sz000001 / sh600000（A股）/ sh900901（B股）", foreground="gray").pack(side=tk.LEFT, padx=10)

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

        chart_frame = ttk.LabelFrame(self.parent, text="历史走势", padding="10")
        chart_frame.pack(fill=tk.BOTH, expand=True)
        self.chart_widget = ChartWidget(chart_frame)

    def set_date_range(self, days):
        end = datetime.now()
        start = end - timedelta(days=days)
        self.end_date_var.set(end.strftime('%Y%m%d'))
        self.start_date_var.set(start.strftime('%Y%m%d'))

    def set_year_to_date(self):
        now = datetime.now()
        start = datetime(now.year, 1, 1)
        self.end_date_var.set(now.strftime('%Y%m%d'))
        self.start_date_var.set(start.strftime('%Y%m%d'))

    def set_all_time(self):
        self.start_date_var.set("19900101")
        self.end_date_var.set(datetime.now().strftime('%Y%m%d'))

    def validate_dates(self):
        start_str = self.start_date_var.get().strip()
        end_str = self.end_date_var.get().strip()
        if len(start_str) != 8 or len(end_str) != 8:
            messagebox.showerror("错误", "日期格式错误！请使用YYYYMMDD格式")
            return None, None
        try:
            start_date = datetime.strptime(start_str, '%Y%m%d')
            end_date = datetime.strptime(end_str, '%Y%m%d')
        except ValueError:
            messagebox.showerror("错误", "日期格式无效")
            return None, None
        if start_date > end_date:
            messagebox.showerror("错误", "起始日期不能晚于截止日期")
            return None, None
        if end_date > datetime.now():
            end_str = datetime.now().strftime('%Y%m%d')
            self.end_date_var.set(end_str)
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
        df = self.current_data.iloc[::-1]
        dates = df['日期'].tolist()

        if chart_type == 'line':
            close_prices = df['收盘'].tolist()
            self.chart_widget.plot_line(dates, close_prices,
                title=f'{self.current_stock_code} 收盘价走势', xlabel='日期', ylabel='收盘价（元）', color='blue')

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
                title=f'{self.current_stock_code} 日涨跌幅', xlabel='日期', ylabel='涨跌幅（%）')

        elif chart_type == 'volume':
            volumes = [v/100 for v in df['成交量'].tolist()]
            self.chart_widget.plot_line(dates, volumes,
                title=f'{self.current_stock_code} 成交量走势', xlabel='日期', ylabel='成交量（手）', color='orange')

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