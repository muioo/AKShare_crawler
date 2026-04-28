"""图表组件，负责在 tkinter 中嵌入 matplotlib 图表。"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from gui.chart_zoom import ChartZoomController


class ChartWidget:
    """通用图表组件，封装常用绘图能力和滚轮缩放能力。"""

    def __init__(self, parent, figsize=(8, 5), enable_navigation=False):
        """初始化图表画布。"""
        self.parent = parent
        self.figsize = figsize
        self.enable_navigation = enable_navigation
        self.figure = None
        self.canvas = None
        self.toolbar = None
        self.zoom_controller = None
        self.control_frame = None
        self.reset_button = None
        self.create_chart()

    def create_chart(self):
        """创建 matplotlib 画布，并接入滚轮缩放控制器。"""
        self.control_frame = ttk.Frame(self.parent)
        self.control_frame.pack(fill=tk.X, pady=(0, 4))
        self.figure = plt.Figure(figsize=self.figsize, dpi=100)
        self.figure.patch.set_facecolor("#f5f5f5")
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.parent)
        if self.enable_navigation:
            self.toolbar = NavigationToolbar2Tk(self.canvas, self.control_frame, pack_toolbar=False)
            self.toolbar.update()
            self.toolbar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.reset_button = ttk.Button(self.control_frame, text="复原", width=8, command=self.reset_view)
        self.reset_button.pack(side=tk.RIGHT)
        canvas_widget = self.canvas.get_tk_widget()
        canvas_widget.pack(fill=tk.BOTH, expand=True)
        self.zoom_controller = ChartZoomController(self.figure, self.canvas, canvas_widget, self.toolbar)

    def reset_view(self):
        """恢复图表默认视图和默认字号。"""
        if self.zoom_controller:
            self.zoom_controller.reset_view()

    def clear(self):
        """清空当前图表。"""
        self.figure.clear()
        self.canvas.draw()

    def plot_line(self, dates, values, title="", xlabel="", ylabel="", color="blue", show_values=True, annotations=None, info_box=None):
        """绘制折线图，可选显示数值、自定义转折点标注和图内摘要信息框。"""
        self.clear()
        dates = self._normalize_dates(dates)
        axis = self.figure.add_subplot(111)
        axis.plot(dates, values, color=color, linewidth=2, alpha=0.85, solid_capstyle="round")
        axis.set_title(title, fontsize=12, fontweight="bold")
        axis.set_xlabel(xlabel, fontsize=10)
        axis.set_ylabel(ylabel, fontsize=10)
        # 显式保留 Y 轴刻度，避免图表只依赖点位标注传达数值。
        axis.tick_params(axis="y", labelleft=True)
        axis.margins(x=0.02, y=0.15)
        if show_values or annotations:
            self._annotate_line(axis, dates, values, ylabel, color, show_values, annotations)
        if info_box:
            self._draw_info_box(axis, info_box)
        self._format_date_axis(axis)
        axis.grid(True, alpha=0.2, linestyle="--", linewidth=0.5)
        axis.set_facecolor("#fafafa")
        self._finalize_chart()

    def plot_candlestick(self, dates, open_prices, high_prices, low_prices, close_prices, title=""):
        """绘制 K 线示意图，并保留缩放能力。"""
        self.clear()
        dates_num = mdates.date2num(self._normalize_dates(dates))
        price_axis = self.figure.add_subplot(211)
        volume_axis = self.figure.add_subplot(212, sharex=price_axis)
        for date, open_price, high_price, low_price, close_price in zip(
            dates_num, open_prices, high_prices, low_prices, close_prices
        ):
            color = "red" if close_price >= open_price else "green"
            price_axis.plot([date, date], [low_price, high_price], color=color, linewidth=1)
            price_axis.bar(
                date,
                abs(close_price - open_price),
                width=0.6,
                bottom=min(open_price, close_price),
                color=color,
                edgecolor=color,
                align="center",
            )
        price_axis.set_title(title, fontsize=12, fontweight="bold")
        price_axis.set_ylabel("价格", fontsize=10)
        price_axis.grid(True, alpha=0.3)
        self._format_date_axis(price_axis, show_labels=False)
        volume_axis.set_xlabel("日期", fontsize=10)
        volume_axis.set_ylabel("成交量", fontsize=10)
        volume_axis.grid(True, alpha=0.3)
        self._finalize_chart()

    def plot_bar(self, labels, values, title="", xlabel="", ylabel="", color="steelblue", show_values=True):
        """绘制柱状图，并按涨跌方向自动着色。"""
        self.clear()
        axis = self.figure.add_subplot(111)
        bars = axis.bar(labels, values, color=["red" if value > 0 else "green" for value in values], alpha=0.7)
        axis.set_title(title, fontsize=12, fontweight="bold")
        axis.set_xlabel(xlabel, fontsize=10)
        axis.set_ylabel(ylabel, fontsize=10)
        if show_values:
            for bar, value, label in zip(bars, values, labels):
                axis.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{value:.2f}", ha="center", va="bottom", fontsize=8)
                label_text = label.strftime("%Y-%m-%d") if isinstance(label, datetime) else str(label)
                axis.text(bar.get_x() + bar.get_width() / 2, bar.get_y(), label_text, ha="center", va="top", fontsize=7)
        axis.grid(True, alpha=0.3, axis="y")
        plt.setp(axis.xaxis.get_majorticklabels(), rotation=45, ha="right")
        self._finalize_chart()

    def plot_multi_line(self, dates, data_dict, title="", xlabel="", ylabel=""):
        """绘制多条折线图。"""
        self.clear()
        dates = self._normalize_dates(dates)
        axis = self.figure.add_subplot(111)
        colors = ["blue", "red", "green", "orange", "purple", "brown", "pink", "gray"]
        for index, (name, values) in enumerate(data_dict.items()):
            axis.plot(dates, values, label=name, color=colors[index % len(colors)], linewidth=2, marker="o", markersize=3)
        axis.set_title(title, fontsize=12, fontweight="bold")
        axis.set_xlabel(xlabel, fontsize=10)
        axis.set_ylabel(ylabel, fontsize=10)
        axis.legend(loc="best", fontsize=9)
        self._format_date_axis(axis)
        axis.grid(True, alpha=0.3)
        self._finalize_chart()

    def _normalize_dates(self, dates):
        """统一把日期字符串转换为 datetime。"""
        if dates and isinstance(dates[0], str):
            return [datetime.strptime(date_text, "%Y-%m-%d") for date_text in dates]
        return dates

    def _annotate_line(self, axis, dates, values, ylabel, default_color, show_values, annotations):
        """给折线图数据点追加说明文字。"""
        for index, (date_value, point_value) in enumerate(zip(dates, values)):
            if pd.isna(point_value):
                continue
            annotation = annotations[index] if annotations and index < len(annotations) else None
            if not show_values and not annotation:
                continue

            text = f"{ylabel}: {point_value:.2f}"
            text_color = default_color
            xytext = (0, 8)
            vertical_alignment = "bottom"

            if annotation:
                text = annotation.get("text", text)
                text_color = annotation.get("color", default_color)
                xytext = annotation.get("xytext", xytext)
                vertical_alignment = annotation.get("va", vertical_alignment)
                axis.scatter(
                    [date_value],
                    [point_value],
                    s=28,
                    color=annotation.get("marker_color", text_color),
                    edgecolors="#ffffff",
                    linewidths=0.8,
                    zorder=3,
                )

            axis.annotate(
                text,
                xy=(date_value, point_value),
                xytext=xytext,
                textcoords="offset points",
                ha="center",
                va=vertical_alignment,
                fontsize=7,
                color=text_color,
            )

    def _draw_info_box(self, axis, info_box):
        """在图表左上角绘制摘要信息框，集中展示当前最有用的指标。"""
        title = info_box.get("title", "")
        lines = info_box.get("lines", [])
        if not title and not lines:
            return

        text_parts = []
        if title:
            text_parts.append(title)
        text_parts.extend(lines)
        text = "\n".join(text_parts)

        axis.text(
            info_box.get("x", 0.02),
            info_box.get("y", 0.98),
            text,
            transform=axis.transAxes,
            ha=info_box.get("ha", "left"),
            va=info_box.get("va", "top"),
            fontsize=info_box.get("fontsize", 8),
            color=info_box.get("color", "#333333"),
            bbox={
                "boxstyle": "round,pad=0.4",
                "facecolor": info_box.get("facecolor", "#ffffff"),
                "edgecolor": info_box.get("edgecolor", "#cccccc"),
                "alpha": info_box.get("alpha", 0.95),
            },
        )

    def _format_date_axis(self, axis, show_labels=True):
        """格式化日期坐标轴显示。"""
        axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        axis.xaxis.set_major_locator(mdates.AutoDateLocator())
        if show_labels:
            plt.setp(axis.xaxis.get_majorticklabels(), rotation=45, ha="right")
        else:
            plt.setp(axis.xaxis.get_majorticklabels(), visible=False)

    def _finalize_chart(self):
        """统一完成布局、重绘和默认视图记录。"""
        self._apply_layout()
        if self.toolbar:
            self.toolbar.update()
        self.canvas.draw()
        if self.zoom_controller:
            self.zoom_controller.capture_defaults()
            self.zoom_controller.remember_view()

    def _apply_layout(self):
        """使用固定边距预留标题、日期标签、摘要框和转折标注空间。"""
        if hasattr(self.figure, "set_layout_engine"):
            self.figure.set_layout_engine(None)
        self.figure.subplots_adjust(**self._build_layout_config())

    def _build_layout_config(self):
        """根据子图数量返回稳定的边距配置，避免 tight_layout 警告。"""
        if len(self.figure.axes) > 1:
            return {
                "left": 0.09,
                "right": 0.98,
                "top": 0.92,
                "bottom": 0.16,
                "hspace": 0.20,
            }
        return {
            "left": 0.09,
            "right": 0.98,
            "top": 0.90,
            "bottom": 0.24,
        }
