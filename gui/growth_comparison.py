"""
同行比较模块 - 获取同类股票的财务指标对比
"""
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_fetcher import DataFetcher
from config import DATA_DIR
from column_mapping import rename_columns


class GrowthComparisonPanel:
    """同行比较面板"""

    def __init__(self, parent):
        self.parent = parent
        self.current_data = None
        self.current_stock_code = None
        self.data_fetcher = DataFetcher()

        # 创建同行比较数据目录
        self.comparison_dir = os.path.join(DATA_DIR, '同行比较')
        os.makedirs(self.comparison_dir, exist_ok=True)

        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        # 搜索区域
        search_frame = ttk.Frame(self.parent)
        search_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(search_frame, text="股票代码:").pack(side=tk.LEFT, padx=5)

        self.stock_code_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.stock_code_var, width=15).pack(side=tk.LEFT, padx=5)

        ttk.Button(search_frame, text="查询", command=self.search_stock, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="保存CSV", command=self.save_to_csv, width=10).pack(side=tk.LEFT, padx=5)

        # 提示文字
        tk.Label(search_frame, text="提示: 输入完整代码，如 SZ000895 / SH600000 / BJ920001", foreground="gray").pack(side=tk.LEFT, padx=10)

        # 状态显示
        self.status_var = tk.StringVar(value="请输入股票代码进行查询")
        status_label = tk.Label(search_frame, textvariable=self.status_var, foreground="blue")
        status_label.pack(side=tk.RIGHT, padx=10)

        # 数据显示区域（带滚动条）
        data_frame = ttk.LabelFrame(self.parent, text="同行比较数据", padding="10")
        data_frame.pack(fill=tk.BOTH, expand=True)

        # 创建带滚动条的表格
        tree_container = ttk.Frame(data_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(tree_container, show="headings")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 垂直滚动条
        v_scroll = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.tree.yview)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=v_scroll.set)

        # 水平滚动条
        h_scroll = ttk.Scrollbar(data_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.configure(xscrollcommand=h_scroll.set)

    def format_stock_code(self, code):
        """格式化股票代码，确保有市场前缀"""
        code = code.strip().upper()
        if code.startswith(('SH', 'SZ', 'BJ')):
            return code
        # 根据6位代码前缀判断
        if code.startswith(('000', '001', '002', '003', '300')):
            return f'SZ{code}'
        elif code.startswith(('600', '601', '603', '605', '688')):
            return f'SH{code}'
        elif code.startswith(('8', '920')):
            return f'BJ{code}'
        else:
            return f'SH{code}'

    def search_stock(self):
        """查询同行比较数据"""
        stock_code = self.stock_code_var.get().strip()
        if not stock_code:
            messagebox.showwarning("警告", "请输入股票代码")
            return

        # 格式化代码
        formatted_code = self.format_stock_code(stock_code)
        self.current_stock_code = formatted_code

        self.status_var.set(f"正在查询 {formatted_code} 的同行比较数据...")

        def run_fetch():
            try:
                df = self.data_fetcher.fetch_growth_comparison(formatted_code)
                if df is None or df.empty:
                    self.parent.after(0, lambda: self._on_empty_data(formatted_code))
                    return

                self.current_data = df
                self.parent.after(0, lambda: self._on_data_received(df, formatted_code))

            except Exception as e:
                error_msg = f"查询失败: {str(e)}"
                self.parent.after(0, lambda: self._on_error(error_msg))

        import threading
        thread = threading.Thread(target=run_fetch)
        thread.start()

    def _on_data_received(self, df, code):
        """数据接收成功回调"""
        # 应用列名映射
        df = rename_columns(df, 'growth_comparison')

        # 清空表格
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 设置列
        columns = list(df.columns)
        self.tree["columns"] = columns

        # 设置列头和宽度
        for col in columns:
            self.tree.heading(col, text=str(col))
            # 根据列名设置不同宽度
            if col in ['代码', '名称']:
                width = 80
            elif col in ['股票简称', '简称']:
                width = 120
            elif col in ['最新价']:
                width = 80
            elif col in ['总市值', '流通市值']:
                width = 100
            elif col in ['涨跌幅', '换手率']:
                width = 80
            elif '增长率' in col:
                width = 110
            elif '排名' in col:
                width = 100
            else:
                width = 100
            self.tree.column(col, width=width, anchor=tk.W)

        # 添加数据
        for idx, row in df.iterrows():
            values = [str(val) if pd.notna(val) else "" for val in row]
            self.tree.insert("", tk.END, values=values)

        self.status_var.set(f"✅ 查询成功: {code} - 共 {len(df)} 家同行公司")

    def _on_empty_data(self, code):
        """空数据回调"""
        self.status_var.set(f"⚠️ 未找到 {code} 的同行比较数据")
        messagebox.showwarning("提示", f"未找到 {code} 的同行比较数据，请检查股票代码是否正确")

    def _on_error(self, error_msg):
        """错误回调"""
        self.status_var.set(f"❌ {error_msg}")
        messagebox.showwarning("查询失败", f"{error_msg}\n\n请过段时间后重试")

    def save_to_csv(self):
        """保存同行比较数据到CSV文件"""
        if self.current_data is None or self.current_data.empty:
            messagebox.showwarning("警告", "没有数据可保存，请先查询股票")
            return

        try:
            # 生成默认文件名
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            default_filename = f"{self.current_stock_code}_同行比较_{timestamp}.csv"

            # 打开文件选择对话框
            filepath = filedialog.asksaveasfilename(
                title="保存CSV文件",
                defaultextension=".csv",
                initialfile=default_filename,
                initialdir=self.comparison_dir,
                filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
            )

            if not filepath:  # 用户取消了保存
                return

            # 保存数据
            self.current_data.to_csv(filepath, index=False, encoding='utf-8-sig')

            messagebox.showinfo("成功", f"同行比较数据已保存到:\n{filepath}")
            self.status_var.set(f"✅ 数据已保存: {os.path.basename(filepath)}")

        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")
