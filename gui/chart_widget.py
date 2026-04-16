"""
图表组件 - 使用matplotlib在tkinter中显示图表（已修复所有报错）
"""
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
from datetime import datetime
import numpy as np


class ChartWidget:
    """图表组件类"""

    def __init__(self, parent):
        self.parent = parent
        self.figure = None
        self.canvas = None
        self.create_chart()

    def create_chart(self):
        """创建图表"""
        # 创建图形
        self.figure = plt.Figure(figsize=(8, 5), dpi=100)
        self.figure.patch.set_facecolor('#f5f5f5')

        # 创建画布
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.parent)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def clear(self):
        """清空图表"""
        self.figure.clear()
        self.canvas.draw()

    def plot_line(self, dates, values, title='', xlabel='', ylabel='', color='blue'):
        """绘制折线图"""
        self.clear()

        ax = self.figure.add_subplot(111)

        # 转换日期
        if isinstance(dates[0], str):
            dates = [datetime.strptime(d, '%Y-%m-%d') for d in dates]

        ax.plot(dates, values, color=color, linewidth=2)
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.set_xlabel(xlabel, fontsize=10)
        ax.set_ylabel(ylabel, fontsize=10)

        # 格式化日期轴
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

        # 网格
        ax.grid(True, alpha=0.3)

        self.figure.tight_layout()
        self.canvas.draw()

    def plot_candlestick(self, dates, open_prices, high_prices, low_prices, close_prices, title=''):
        """
        绘制K线图

        Args:
            dates: 日期列表
            open_prices: 开盘价列表
            high_prices: 最高价列表
            low_prices: 最低价列表
            close_prices: 收盘价列表
            title: 标题
        """
        self.clear()

        # 创建两个子图：K线和成交量
        ax1 = self.figure.add_subplot(211)
        ax2 = self.figure.add_subplot(212, sharex=ax1)

        # 转换日期
        if isinstance(dates[0], str):
            dates = [datetime.strptime(d, '%Y-%m-%d') for d in dates]
        dates_num = mdates.date2num(dates)

        # 绘制K线
        width = 0.6
        for i, (date, open_p, high, low, close) in enumerate(zip(
            dates_num, open_prices, high_prices, low_prices, close_prices
        )):
            color = 'red' if close >= open_p else 'green'

            # 绘制影线
            ax1.plot([date, date], [low, high], color=color, linewidth=1)

            # 绘制实体
            body_height = abs(close - open_p)
            body_bottom = min(open_p, close)
            ax1.bar(date, body_height, width=width, bottom=body_bottom,
                    color=color, edgecolor=color, align='center')

        ax1.set_title(title, fontsize=12, fontweight='bold')
        ax1.set_ylabel('价格', fontsize=10)
        ax1.grid(True, alpha=0.3)

        # 格式化日期轴
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(ax1.xaxis.get_majorticklabels(), visible=False)

        # 成交量子图占位
        ax2.set_xlabel('日期', fontsize=10)
        ax2.set_ylabel('成交量', fontsize=10)
        ax2.grid(True, alpha=0.3)

        self.figure.tight_layout()
        self.canvas.draw()

    def plot_bar(self, labels, values, title='', xlabel='', ylabel='', color='steelblue'):
        """绘制柱状图"""
        self.clear()

        ax = self.figure.add_subplot(111)

        # 正值和负值不同颜色
        colors = ['red' if v > 0 else 'green' for v in values]

        bars = ax.bar(labels, values, color=colors, alpha=0.7)
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.set_xlabel(xlabel, fontsize=10)
        ax.set_ylabel(ylabel, fontsize=10)

        # 在柱子上显示数值
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2., height,
                    f'{value:.2f}', ha='center', va='bottom', fontsize=8)

        ax.grid(True, alpha=0.3, axis='y')
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

        self.figure.tight_layout()
        self.canvas.draw()

    def plot_multi_line(self, dates, data_dict, title='', xlabel='', ylabel=''):
        """
        绘制多条折线图

        Args:
            dates: 日期列表
            data_dict: 字典 {name: values}
        """
        self.clear()

        ax = self.figure.add_subplot(111)

        # 转换日期
        if isinstance(dates[0], str):
            dates = [datetime.strptime(d, '%Y-%m-%d') for d in dates]

        colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']

        for i, (name, values) in enumerate(data_dict.items()):
            color = colors[i % len(colors)]
            ax.plot(dates, values, label=name, color=color, linewidth=2, marker='o', markersize=3)

        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.set_xlabel(xlabel, fontsize=10)
        ax.set_ylabel(ylabel, fontsize=10)
        ax.legend(loc='best', fontsize=9)

        # 格式化日期轴
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

        ax.grid(True, alpha=0.3)
        self.figure.tight_layout()
        self.canvas.draw()


# ==================== 测试代码（可直接运行查看效果）====================
if __name__ == "__main__":
    root = tk.Tk()
    root.title("图表组件测试")
    root.geometry("900x600")

    # 创建图表组件
    chart = ChartWidget(root)

    # 测试数据
    test_dates = ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04", "2025-01-05"]
    test_values = [10, 15, 12, 18, 14]

    # 绘制测试折线图
    chart.plot_line(
        dates=test_dates,
        values=test_values,
        title="测试折线图",
        xlabel="日期",
        ylabel="数值"
    )

    root.mainloop()