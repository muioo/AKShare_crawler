"""
AKShare 股票数据爬取 GUI 应用
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import os
import sys
from datetime import datetime
import threading
import glob

# 获取图标路径
if getattr(sys, 'frozen', False):
    # 打包后的路径
    icon_path = os.path.join(sys._MEIPASS, 'gui', 'resources', 'icon.ico')
else:
    # 开发环境路径
    icon_path = os.path.join(os.path.dirname(__file__), 'resources', 'icon.ico')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_fetcher import DataFetcher
from config import DATA_DIR, DATA_TYPES
from gui.stock_analysis import StockAnalysisPanel
from gui.file_manager import FileManager
from gui.scheduler import DataScheduler
from gui.growth_comparison import GrowthComparisonPanel


class StockDataApp:
    QUOTE_SUBTYPES = {
        '沪深京A股': 'fetch_quote_zh_a_spot',
        'B股': 'fetch_quote_zh_b_spot',
        'AH股': 'fetch_quote_zh_ah_spot',
        '科创版': 'fetch_quote_zh_kcb_spot',
        '港股': 'fetch_quote_hk_spot',
    }

    def __init__(self, root):
        self.root = root
        self.root.title("股票数据爬取工具")
        self.root.geometry("1200x850")

        self.data_fetcher = DataFetcher()
        self.file_manager = FileManager()
        self.scheduler = DataScheduler(callback=self.on_scheduler_complete)

        self.current_data = None
        self.current_data_type = None
        self.current_subtype = None

        # 资金流向排序和显示变量
        self.fund_sort_column_var = tk.StringVar(value='请选择')
        self.fund_sort_order_var = tk.StringVar(value='desc')
        self.fund_display_count_var = tk.StringVar(value='50')

        self.all_data = {
            '实时行情_沪深京A股': None,
            '实时行情_B股': None,
            '实时行情_AH股': None,
            '实时行情_科创版': None,
            '实时行情_港股': None,
            '资金流向': None,
        }

        self.setup_ui()
        self.load_latest_data_on_start()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        control_bar = ttk.Frame(main_frame)
        control_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        self.auto_fetch_var = tk.BooleanVar(value=False)
        self.auto_fetch_check = ttk.Checkbutton(
            control_bar, text="自动爬取（每30分钟）", variable=self.auto_fetch_var, command=self.toggle_auto_fetch
        )
        self.auto_fetch_check.pack(side=tk.LEFT, padx=5)

        ttk.Button(control_bar, text="立即爬取全部", command=self.fetch_all_parallel).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_bar, text="清理旧文件", command=self.clean_old_files).pack(side=tk.LEFT, padx=5)

        ttk.Label(control_bar, text=f"文件保留: {self.file_manager.RETENTION_DAYS}天", foreground="gray").pack(side=tk.LEFT, padx=15)

        # ========== 全局股票搜索 ==========
        ttk.Separator(control_bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        ttk.Label(control_bar, text="股票搜索:").pack(side=tk.LEFT, padx=5)
        self.global_search_var = tk.StringVar()
        self.global_search_entry = ttk.Entry(control_bar, textvariable=self.global_search_var, width=15)
        self.global_search_entry.pack(side=tk.LEFT, padx=5)
        # 绑定回车键
        self.global_search_entry.bind('<Return>', lambda e: self.global_search_stock())

        ttk.Button(control_bar, text="搜索", command=self.global_search_stock).pack(side=tk.LEFT, padx=5)

        self.next_run_var = tk.StringVar(value="下次运行: 未启动")
        ttk.Label(control_bar, textvariable=self.next_run_var, foreground="blue").pack(side=tk.RIGHT, padx=5)

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        main_frame.rowconfigure(1, weight=1)

        self.quote_frame = ttk.Frame(self.notebook)
        self.fund_flow_frame = ttk.Frame(self.notebook)
        self.analysis_frame = ttk.Frame(self.notebook)
        self.growth_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.quote_frame, text="实时股票行情")
        self.notebook.add(self.fund_flow_frame, text="资金流向")
        self.notebook.add(self.analysis_frame, text="单股分析")
        self.notebook.add(self.growth_frame, text="同行比较")

        self.setup_quote_tab()
        self.setup_fund_flow_tab()
        self.setup_analysis_tab()
        self.setup_growth_tab()

        self.status_var = tk.StringVar(value="就绪")
        self.save_dir_var = tk.StringVar(value=f"保存目录: {DATA_DIR}")
        status_bar = ttk.Frame(main_frame)
        status_bar.grid(row=2, column=0, sticky=(tk.W, tk.E))
        ttk.Label(status_bar, textvariable=self.status_var).pack(side=tk.LEFT, padx=5)
        ttk.Label(status_bar, textvariable=self.save_dir_var, foreground="gray").pack(side=tk.RIGHT, padx=5)

        self.update_next_run_display()

    def setup_quote_tab(self):
        """设置实时股票行情选项卡"""
        control_panel = ttk.Frame(self.quote_frame, width=200)
        control_panel.grid(row=0, column=0, sticky=(tk.N, tk.S), padx=(0, 10))

        ttk.Label(control_panel, text="选择市场", font=('Arial', 10, 'bold')).pack(pady=(0, 5), anchor=tk.W)

        self.quote_subtype_var = tk.StringVar(value='沪深京A股')
        for subtype in self.QUOTE_SUBTYPES.keys():
            ttk.Radiobutton(
                control_panel,
                text=subtype,
                variable=self.quote_subtype_var,
                value=subtype,
                command=self.on_quote_subtype_change
            ).pack(anchor=tk.W, pady=2)

        ttk.Separator(control_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # ========== 动态排序设置 ==========
        ttk.Label(control_panel, text="排序设置", font=('Arial', 10, 'bold')).pack(pady=(0, 5), anchor=tk.W)

        ttk.Label(control_panel, text="排序指标:").pack(anchor=tk.W)

        # 动态排序列（根据当前表格列名更新）
        self.sort_column_var = tk.StringVar(value='请选择')
        self.sort_column_combo = ttk.Combobox(
            control_panel,
            textvariable=self.sort_column_var,
            values=['请先获取数据'],
            state='readonly',
            width=15
        )
        self.sort_column_combo.pack(anchor=tk.W, pady=2)

        ttk.Label(control_panel, text="排序方式:").pack(anchor=tk.W, pady=(5, 0))
        self.sort_order_var = tk.StringVar(value='desc')
        ttk.Radiobutton(control_panel, text="降序（从高到低）", variable=self.sort_order_var, value='desc').pack(anchor=tk.W)
        ttk.Radiobutton(control_panel, text="升序（从低到高）", variable=self.sort_order_var, value='asc').pack(anchor=tk.W)

        ttk.Separator(control_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        ttk.Label(control_panel, text="显示数量:").pack(anchor=tk.W, pady=(5, 0))
        self.display_count_var = tk.StringVar(value='50')
        count_combo = ttk.Combobox(control_panel, textvariable=self.display_count_var, values=['10', '20', '50', '100', '全部'], state='readonly', width=15)
        count_combo.pack(anchor=tk.W, pady=2)

        ttk.Separator(control_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        ttk.Button(control_panel, text="获取数据", command=self.fetch_quote_data, width=18).pack(pady=5)
        ttk.Button(control_panel, text="刷新排序", command=self.refresh_sort, width=18).pack(pady=5)
        ttk.Button(control_panel, text="保存CSV", command=lambda: self.save_to_csv('quote'), width=18).pack(pady=5)

        data_frame = ttk.Frame(self.quote_frame)
        data_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.quote_frame.columnconfigure(1, weight=1)
        self.quote_frame.rowconfigure(0, weight=1)

        self.quote_tree = ttk.Treeview(data_frame, show='headings')
        self.quote_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        data_frame.columnconfigure(0, weight=1)
        data_frame.rowconfigure(0, weight=1)

        v_scroll = ttk.Scrollbar(data_frame, orient=tk.VERTICAL, command=self.quote_tree.yview)
        v_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.quote_tree.configure(yscrollcommand=v_scroll.set)

        h_scroll = ttk.Scrollbar(data_frame, orient=tk.HORIZONTAL, command=self.quote_tree.xview)
        h_scroll.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.quote_tree.configure(xscrollcommand=h_scroll.set)

    def setup_fund_flow_tab(self):
        """设置资金流向选项卡"""
        # 左侧控制面板
        control_panel = ttk.Frame(self.fund_flow_frame, width=200)
        control_panel.grid(row=0, column=0, sticky=(tk.N, tk.S), padx=(0, 10))

        # 排序设置
        ttk.Label(control_panel, text="排序设置", font=('Arial', 10, 'bold')).pack(pady=(0, 5), anchor=tk.W)

        ttk.Label(control_panel, text="排序指标:").pack(anchor=tk.W)

        # 动态排序列（根据当前表格列名更新）
        self.fund_sort_column_combo = ttk.Combobox(
            control_panel,
            textvariable=self.fund_sort_column_var,
            values=['请先获取数据'],
            state='readonly',
            width=15
        )
        self.fund_sort_column_combo.pack(anchor=tk.W, pady=2)

        ttk.Label(control_panel, text="排序方式:").pack(anchor=tk.W, pady=(5, 0))
        ttk.Radiobutton(control_panel, text="降序（从高到低）", variable=self.fund_sort_order_var, value='desc').pack(anchor=tk.W)
        ttk.Radiobutton(control_panel, text="升序（从低到高）", variable=self.fund_sort_order_var, value='asc').pack(anchor=tk.W)

        ttk.Separator(control_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        ttk.Label(control_panel, text="显示数量:").pack(anchor=tk.W, pady=(5, 0))
        fund_count_combo = ttk.Combobox(
            control_panel,
            textvariable=self.fund_display_count_var,
            values=['10', '20', '50', '100', '全部'],
            state='readonly',
            width=15
        )
        fund_count_combo.pack(anchor=tk.W, pady=2)

        ttk.Separator(control_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # 按钮
        ttk.Button(control_panel, text="获取数据", command=self.fetch_fund_flow_data, width=18).pack(pady=5)
        ttk.Button(control_panel, text="刷新排序", command=self.refresh_fund_flow_sort, width=18).pack(pady=5)
        ttk.Button(control_panel, text="保存CSV", command=lambda: self.save_to_csv('fund_flow'), width=18).pack(pady=5)

        # 右侧数据显示区域
        data_frame = ttk.Frame(self.fund_flow_frame)
        data_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.fund_flow_frame.columnconfigure(1, weight=1)
        self.fund_flow_frame.rowconfigure(0, weight=1)

        self.fund_flow_tree = ttk.Treeview(data_frame, show='headings')
        self.fund_flow_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        data_frame.columnconfigure(0, weight=1)
        data_frame.rowconfigure(0, weight=1)

        v_scroll = ttk.Scrollbar(data_frame, orient=tk.VERTICAL, command=self.fund_flow_tree.yview)
        v_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.fund_flow_tree.configure(yscrollcommand=v_scroll.set)

        h_scroll = ttk.Scrollbar(data_frame, orient=tk.HORIZONTAL, command=self.fund_flow_tree.xview)
        h_scroll.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.fund_flow_tree.configure(xscrollcommand=h_scroll.set)

    def setup_analysis_tab(self):
        self.stock_analysis_panel = StockAnalysisPanel(self.analysis_frame)

    def setup_growth_tab(self):
        self.growth_comparison_panel = GrowthComparisonPanel(self.growth_frame)

    def update_sort_columns(self, columns):
        """根据当前表格列名更新实时行情排序选项"""
        # 排除不适合排序的列
        exclude_columns = ['序号', '代码', '名称', '相关', '市场', '相关链接']

        # 过滤出可排序的列
        sortable_columns = [col for col in columns if col not in exclude_columns]

        # 更新下拉框
        self.sort_column_combo['values'] = sortable_columns

        # 设置默认值（优先选择常用排序列）
        default_sort = None
        for col in ['涨跌幅', '今日主力净流入', '换手率', '成交量', '成交额', '主力净流入']:
            if col in sortable_columns:
                default_sort = col
                break

        if default_sort:
            self.sort_column_var.set(default_sort)
        elif sortable_columns:
            self.sort_column_var.set(sortable_columns[0])
        else:
            self.sort_column_var.set('请选择')

    def update_fund_sort_columns(self, columns):
        """根据当前表格列名更新资金流向排序选项"""
        # 排除不适合排序的列
        exclude_columns = ['序号', '代码', '名称', '相关', '市场', '相关链接']

        # 过滤出可排序的列
        sortable_columns = [col for col in columns if col not in exclude_columns]

        # 更新下拉框
        self.fund_sort_column_combo['values'] = sortable_columns

        # 设置默认值（优先选择常用排序列）
        default_sort = None
        for col in ['主力净流入', '涨跌幅', '超大单净流入', '大单净流入', '中单净流入', '小单净流入', '主力净占比']:
            if col in sortable_columns:
                default_sort = col
                break

        if default_sort:
            self.fund_sort_column_var.set(default_sort)
        elif sortable_columns:
            self.fund_sort_column_var.set(sortable_columns[0])
        else:
            self.fund_sort_column_var.set('请选择')

    def start_scheduler(self):
        self.scheduler.start()
        self.update_next_run_display()

    def stop_scheduler(self):
        self.scheduler.stop()

    def toggle_auto_fetch(self):
        if self.auto_fetch_var.get():
            if not self.scheduler.get_status()['running']:
                self.scheduler.start()
                self.status_var.set("自动爬取已启用 → 每30分钟爬取一次")
        else:
            self.scheduler.stop()
            self.status_var.set("自动爬取已停止")
            self.next_run_var.set("下次运行: 未启动")

    def update_next_run_display(self):
        def update():
            while True:
                if self.scheduler._running:
                    status = self.scheduler.get_status()
                    if status['next_run']:
                        time_str = status['next_run'].strftime('%H:%M:%S')
                        self.next_run_var.set(f"下次运行: {time_str}")
                import time
                time.sleep(10)
        thread = threading.Thread(target=update, daemon=True)
        thread.start()

    def on_scheduler_complete(self, results, file_paths):
        for subtype, (df, data_type, name) in results.items():
            if df is not None and not df.empty:
                self.all_data[subtype] = df

        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0:
            self.load_current_quote_data()
        elif current_tab == 1 and self.all_data.get('资金流向') is not None:
            # 资金流向使用排序
            self.current_data_type = 'fund_flow'
            self.display_data(self.all_data['资金流向'], self.fund_flow_tree, sort_data=True)

        self.status_var.set(f"自动爬取完成: {len(file_paths)} 个文件已保存")

    def load_current_quote_data(self):
        subtype = self.quote_subtype_var.get()
        subtype_key = f'实时行情_{subtype}'
        if self.all_data.get(subtype_key) is not None:
            self.current_data = self.all_data[subtype_key]
            self.current_data_type = 'quote'
            self.display_data(self.current_data, self.quote_tree, sort_data=True)

    def on_quote_subtype_change(self):
        self.current_subtype = self.quote_subtype_var.get()
        self.status_var.set(f"已选择: {self.current_subtype}")
        self.load_current_quote_data()

    def fetch_all_parallel(self):
        def run_fetch():
            self.status_var.set("正在并行获取所有数据...")
            try:
                deleted_count, total_size = self.file_manager.clean_old_files()
                self.status_var.set(f"已清理 {deleted_count} 个旧文件，正在获取数据...")
                results = self.data_fetcher.fetch_all_parallel()
                file_paths = {}
                for subtype, (df, data_type, name) in results.items():
                    if df is not None and not df.empty:
                        self.all_data[subtype] = df
                        subtype_name = None if data_type != 'quote' else subtype
                        filepath = self.file_manager.save_data(df, data_type, subtype_name)
                        if filepath:
                            file_paths[subtype] = filepath
                self.root.after(0, lambda: self.on_scheduler_complete(results, file_paths))
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"获取失败: {str(e)}"))
        thread = threading.Thread(target=run_fetch)
        thread.start()

    def clean_old_files(self):
        def run_clean():
            deleted_count, total_size = self.file_manager.clean_old_files()
            self.root.after(0, lambda: self.status_var.set(
                f"清理完成: 删除 {deleted_count} 个文件，释放 {total_size / 1024:.2f} KB"
            ))
        thread = threading.Thread(target=run_clean)
        thread.start()

    def display_data(self, df, tree, sort_data=True):
        """在表格中显示数据"""
        if df is None or df.empty:
            return

        # 判断是否为资金流向表格
        is_fund_flow = (tree == self.fund_flow_tree)

        # 如果需要排序
        if sort_data:
            if self.current_data_type == 'quote':
                df = self.sort_data(df.copy(), 'quote')
            elif is_fund_flow:
                df = self.sort_data(df.copy(), 'fund_flow')

        # 限制显示数量
        if is_fund_flow:
            display_count = self.fund_display_count_var.get()
        else:
            display_count = self.display_count_var.get()

        if display_count != '全部':
            df = df.head(int(display_count))

        # 清空表格
        for item in tree.get_children():
            tree.delete(item)

        # 设置列
        columns = list(df.columns)
        tree['columns'] = columns

        # 设置列头和宽度
        for col in columns:
            tree.heading(col, text=str(col))
            if col in ['代码', '名称']:
                width = 80
            elif col in ['最新价', '涨跌幅', '涨跌额', '今开', '昨收', '最高', '最低']:
                width = 80
            elif col in ['主力净流入', '超大单净流入', '大单净流入', '中单净流入', '小单净流入']:
                width = 100
            else:
                width = 100
            tree.column(col, width=width, anchor=tk.W)

        # 添加数据
        for idx, row in df.iterrows():
            tree.insert('', tk.END, values=list(row))

        # ========== 更新排序下拉框 ==========
        if is_fund_flow:
            self.update_fund_sort_columns(columns)
        else:
            self.update_sort_columns(columns)

        self.status_var.set(f"已显示 {len(df)} 条数据")

    def sort_data(self, df, data_type='quote'):
        """对数据进行排序"""
        if data_type == 'quote':
            sort_column = self.sort_column_var.get()
            sort_order = self.sort_order_var.get()
        else:  # fund_flow
            sort_column = self.fund_sort_column_var.get()
            sort_order = self.fund_sort_order_var.get()

        # 检查列是否存在
        if sort_column not in df.columns or sort_column in ['请选择', '请先获取数据']:
            return df

        try:
            ascending = (sort_order == 'asc')
            df = df.sort_values(by=sort_column, ascending=ascending, na_position='last')
        except Exception as e:
            print(f"排序失败: {e}")

        return df

    def refresh_sort(self):
        """刷新实时行情排序"""
        if self.current_data is None or self.current_data.empty:
            messagebox.showwarning("警告", "没有数据可排序，请先获取数据")
            return

        # 重新显示数据（会触发排序）
        self.display_data(self.current_data, self.quote_tree, sort_data=True)
        self.status_var.set(f"已按 {self.sort_column_var.get()} {self.sort_order_var.get()} 排序")

    def refresh_fund_flow_sort(self):
        """刷新资金流向排序"""
        fund_data = self.all_data.get('资金流向')
        if fund_data is None or fund_data.empty:
            messagebox.showwarning("警告", "没有数据可排序，请先获取数据")
            return

        # 重新显示数据（会触发排序）
        self.display_data(fund_data, self.fund_flow_tree, sort_data=True)
        self.status_var.set(f"已按 {self.fund_sort_column_var.get()} {self.fund_sort_order_var.get()} 排序")

    def global_search_stock(self):
        """全局股票搜索（跨市场搜索）"""
        search_text = self.global_search_var.get().strip()
        if not search_text:
            messagebox.showwarning("警告", "请输入股票代码或名称")
            return

        # 检查是否有数据
        has_data = False
        for key in self.all_data.keys():
            if self.all_data.get(key) is not None and not self.all_data[key].empty:
                has_data = True
                break

        if not has_data:
            messagebox.showwarning("警告", "没有数据可搜索，请先点击\"立即爬取全部\"获取数据")
            return

        # 跨市场搜索
        search_text_upper = search_text.upper()
        search_text_lower = search_text.lower()
        results = {}

        # 搜索所有市场
        for subtype, data in self.all_data.items():
            if data is None or data.empty:
                continue

            df = data.copy()

            # 查找代码列和名称列
            code_col = None
            name_col = None

            for col in df.columns:
                col_lower = str(col).lower()
                if '代码' in col_lower or 'code' in col_lower:
                    code_col = col
                elif '名称' in col_lower or 'name' in col_lower:
                    name_col = col

            # 搜索逻辑
            mask = pd.Series([False] * len(df), index=df.index)

            if code_col is not None:
                # 代码列模糊匹配
                mask |= df[code_col].astype(str).str.contains(search_text_upper, na=False, case=False)

            if name_col is not None:
                # 名称列模糊匹配
                mask |= df[name_col].astype(str).str.contains(search_text, na=False, case=False)

            # 筛选结果
            filtered_df = df[mask]

            if not filtered_df.empty:
                results[subtype] = filtered_df

        if not results:
            messagebox.showinfo("提示", f"未找到匹配的股票: {search_text}")
            return

        # 找到第一个有结果的市场
        first_subtype = list(results.keys())[0]
        first_result = results[first_subtype]

        # 获取市场名称
        market_name = None
        for subtype in self.QUOTE_SUBTYPES.keys():
            if f'实时行情_{subtype}' == first_subtype:
                market_name = subtype
                break

        # 切换到实时行情选项卡
        self.notebook.select(0)

        # 切换到对应的市场
        if market_name:
            self.quote_subtype_var.set(market_name)
            self.on_quote_subtype_change()

        # 显示搜索结果
        self.current_data = first_result
        self.current_data_type = 'quote'
        self.display_data(first_result, self.quote_tree, sort_data=False)

        # 显示搜索结果统计
        total_count = sum(len(df) for df in results.values())
        status_msg = f"搜索结果: {search_text} - 找到 {total_count} 条匹配记录"
        if len(results) > 1:
            status_msg += f"（跨{len(results)}个市场）"
        self.status_var.set(status_msg)

        # 清空搜索框
        self.global_search_var.set("")

    def fetch_quote_data(self):
        self.current_subtype = self.quote_subtype_var.get()
        method_name = self.QUOTE_SUBTYPES[self.current_subtype]
        self.status_var.set(f"正在获取 {self.current_subtype} 数据...")

        def run_fetch():
            try:
                method = getattr(self.data_fetcher, method_name)
                df = method()
                self.root.after(0, lambda: self._on_quote_data_received(df))
            except Exception as e:
                self.root.after(0, lambda: self._on_fetch_error(e))
        thread = threading.Thread(target=run_fetch)
        thread.start()

    def _on_quote_data_received(self, df):
        self.current_data = df
        self.current_data_type = 'quote'
        subtype = self.quote_subtype_var.get()
        subtype_key = f'实时行情_{subtype}'
        self.all_data[subtype_key] = df
        self.display_data(df, self.quote_tree, sort_data=True)
        self.status_var.set(f"{self.current_subtype} 数据获取成功，共 {len(df)} 条")

    def _on_fetch_error(self, error):
        messagebox.showerror("错误", f"获取数据失败: {str(error)}")
        self.status_var.set(f"获取失败: {str(error)}")

    def fetch_fund_flow_data(self):
        self.status_var.set("正在获取资金流向数据...")
        def run_fetch():
            try:
                df = self.data_fetcher.fetch_fund_flow_data()
                self.root.after(0, lambda: self._on_fund_flow_data_received(df))
            except Exception as e:
                self.root.after(0, lambda: self._on_fetch_error(e))
        thread = threading.Thread(target=run_fetch)
        thread.start()

    def _on_fund_flow_data_received(self, df):
        self.current_data = df
        self.current_data_type = 'fund_flow'
        self.all_data['资金流向'] = df
        self.display_data(df, self.fund_flow_tree, sort_data=True)
        self.status_var.set(f"资金流向数据获取成功，共 {len(df)} 条")

    def save_to_csv(self, data_type):
        if data_type == 'quote':
            df = self.all_data.get(f'实时行情_{self.quote_subtype_var.get()}')
            subtype = self.quote_subtype_var.get() or '沪深京A股'
            chinese_type = DATA_TYPES.get(f'quote_{subtype}', subtype)
            default_filename = f"{chinese_type}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
        elif data_type == 'fund_flow':
            df = self.all_data.get('资金流向')
            chinese_type = '资金流向'
            default_filename = f"{chinese_type}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
        else:
            messagebox.showwarning("警告", "不支持的数据类型")
            return

        if df is None or df.empty:
            messagebox.showwarning("警告", "没有数据可保存，请先获取数据")
            return

        # 打开文件选择对话框
        filepath = filedialog.asksaveasfilename(
            title="保存CSV文件",
            defaultextension=".csv",
            initialfile=default_filename,
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )

        if not filepath:  # 用户取消了保存
            return

        try:
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            messagebox.showinfo("成功", f"数据已保存到:\n{filepath}")
            self.status_var.set(f"数据已保存: {filepath}")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")
            self.status_var.set(f"保存失败: {str(e)}")

    def load_latest_data_on_start(self):
        def load():
            self.status_var.set("正在加载本地最新数据...")
            self.load_latest_csv_by_prefix("实时行情", "沪深京A股", "实时行情_沪深京A股")
            self.load_latest_csv_by_prefix("实时行情", "B股", "实时行情_B股")
            self.load_latest_csv_by_prefix("实时行情", "AH股", "实时行情_AH股")
            self.load_latest_csv_by_prefix("实时行情", "科创版", "实时行情_科创版")
            self.load_latest_csv_by_prefix("实时行情", "港股", "实时行情_港股")

            self.load_latest_csv_by_prefix("资金流向", "", "资金流向")

            self.root.after(0, self.auto_display_all)
            self.root.after(0, lambda: self.status_var.set("✅ 已自动加载最新数据"))
        threading.Thread(target=load, daemon=True).start()

    def load_latest_csv_by_prefix(self, folder_name, prefix, key_in_all_data):
        try:
            folder = os.path.join(DATA_DIR, folder_name)
            if not os.path.exists(folder):
                return

            if prefix == "沪深京A股":
                pattern = "*沪深京*.csv"
            elif prefix:
                pattern = f"*{prefix}*.csv"
            else:
                pattern = "*.csv"

            files = glob.glob(os.path.join(folder, pattern))
            if not files:
                return
            files.sort(key=os.path.getmtime, reverse=True)
            latest_file = files[0]
            df = pd.read_csv(latest_file, encoding='utf-8-sig')
            self.all_data[key_in_all_data] = df
            print(f"✅ 加载成功: {latest_file}")
        except Exception as e:
            print(f"加载失败 {folder}/{prefix}: {e}")

    def auto_display_all(self):
        self.load_current_quote_data()
        if self.all_data["资金流向"] is not None:
            self.current_data_type = 'fund_flow'
            self.display_data(self.all_data["资金流向"], self.fund_flow_tree, sort_data=True)


def main():
    root = tk.Tk()
    # 设置应用图标
    if os.path.exists(icon_path):
        root.iconbitmap(icon_path)
    app = StockDataApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()