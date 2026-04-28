"""图表滚轮缩放和拖动平移辅助模块。"""

from utils import logger


class ChartZoomController:
    """为 matplotlib 嵌入图表提供缩放、拖动和平移复原能力。"""

    def __init__(
        self,
        figure,
        canvas,
        tk_widget,
        toolbar=None,
        base_scale=1.15,
        history_delay_ms=120,
        drag_threshold=2,
    ):
        """初始化控制器，并绑定 matplotlib 原生交互事件。"""
        self.figure = figure
        self.canvas = canvas
        self.tk_widget = tk_widget
        self.toolbar = toolbar
        self.base_scale = base_scale
        self.history_delay_ms = history_delay_ms
        self.drag_threshold = drag_threshold
        self.default_axes_state = {}
        self.pan_state = None
        self.history_job = None
        self.mpl_connections = []
        self._connect_events()

    def _connect_events(self):
        """绑定画布聚焦和 matplotlib 原生滚轮、拖动事件。"""
        self.tk_widget.bind("<Enter>", self._focus_canvas, add="+")
        self.mpl_connections = [
            self.canvas.mpl_connect("scroll_event", self.on_mouse_wheel),
            self.canvas.mpl_connect("button_press_event", self.on_button_press),
            self.canvas.mpl_connect("motion_notify_event", self.on_button_drag),
            self.canvas.mpl_connect("button_release_event", self.on_button_release),
        ]

    def _focus_canvas(self, _event):
        """鼠标进入图表后主动聚焦，提升滚轮事件命中率。"""
        self.tk_widget.focus_set()

    def capture_defaults(self):
        """记录当前图表的默认视图和默认字号，用于复原。"""
        self.default_axes_state = {}
        for axis in self.figure.axes:
            self.default_axes_state[id(axis)] = {
                "xlim": axis.get_xlim(),
                "ylim": axis.get_ylim(),
                "tick_font": self._pick_tick_font(axis),
                "text_fonts": [text.get_fontsize() for text in axis.texts],
                "x_offset_font": axis.xaxis.offsetText.get_fontsize(),
                "y_offset_font": axis.yaxis.offsetText.get_fontsize(),
            }

    def remember_view(self):
        """记录当前视图，便于工具栏 Home/Back 恢复。"""
        if self.toolbar and hasattr(self.toolbar, "push_current"):
            self.toolbar.push_current()

    def reset_view(self):
        """恢复默认视图和默认字号。"""
        if not self.default_axes_state:
            return
        self._cancel_view_snapshot()
        try:
            for axis in self.figure.axes:
                state = self.default_axes_state.get(id(axis))
                if state:
                    axis.set_xlim(*state["xlim"])
                    axis.set_ylim(*state["ylim"])
                    self._apply_font_scale(axis, state, 1.0)
            self.canvas.draw_idle()
            self.remember_view()
        except Exception as exc:
            logger.exception("复原图表视图失败: %s", exc)

    def on_mouse_wheel(self, event):
        """处理滚轮缩放，并同步更新数字字号。"""
        if self._toolbar_is_active() or event.inaxes is None:
            return
        try:
            if not self.default_axes_state:
                self.capture_defaults()
            scale = self._resolve_scale(event)
            if scale is None:
                return
            self._zoom_axis(event.inaxes, event.xdata, event.ydata, scale)
            self._update_all_font_sizes()
            self.canvas.draw_idle()
            self._schedule_view_snapshot()
        except Exception as exc:
            logger.exception("处理图表滚轮缩放失败: %s", exc)

    def on_button_press(self, event):
        """记录左键按下时的像素起点和视图范围，为平移做准备。"""
        if self._toolbar_is_active() or event.inaxes is None or event.button != 1:
            return
        try:
            if not self.default_axes_state:
                self.capture_defaults()
            axis = event.inaxes
            self.pan_state = {
                "axis": axis,
                "start_pixel": (event.x, event.y),
                "start_xlim": axis.get_xlim(),
                "start_ylim": axis.get_ylim(),
                "lock_y": self._should_lock_y_pan(axis),
                "dragged": False,
            }
        except Exception as exc:
            logger.exception("记录图表拖动起点失败: %s", exc)

    def on_button_drag(self, event):
        """按住左键拖动时按像素位移平移视图，避免坐标反算抖动。"""
        if not self.pan_state or self._toolbar_is_active():
            return
        if event.x is None or event.y is None:
            return
        try:
            axis = self.pan_state["axis"]
            start_x, start_y = self.pan_state["start_pixel"]
            delta_x_pixels = event.x - start_x
            delta_y_pixels = event.y - start_y
            lock_y = self.pan_state["lock_y"]

            if abs(delta_x_pixels) < self.drag_threshold and (lock_y or abs(delta_y_pixels) < self.drag_threshold):
                return

            target_xlim, target_ylim = self._calculate_pan_target_limits(
                axis=axis,
                start_xlim=self.pan_state["start_xlim"],
                start_ylim=self.pan_state["start_ylim"],
                delta_x_pixels=delta_x_pixels,
                delta_y_pixels=delta_y_pixels,
                lock_y=lock_y,
            )
            axis.set_xlim(*target_xlim)
            if not lock_y:
                axis.set_ylim(*target_ylim)
            self.pan_state["dragged"] = True
            self.canvas.draw_idle()
        except Exception as exc:
            logger.exception("处理图表拖动平移失败: %s", exc)

    def on_button_release(self, _event):
        """结束拖动，并把当前视图记录到工具栏历史。"""
        if not self.pan_state:
            return
        dragged = self.pan_state.get("dragged", False)
        self.pan_state = None
        if dragged:
            self.remember_view()

    def _toolbar_is_active(self):
        """工具栏处于内置 Pan/Zoom 状态时让 matplotlib 自己接管。"""
        return bool(self.toolbar and getattr(self.toolbar, "mode", ""))

    def _resolve_scale(self, event):
        """根据滚轮方向计算缩放系数。"""
        button = getattr(event, "button", None)
        step = getattr(event, "step", 0)
        if button == "up" or step > 0:
            return 1 / self.base_scale
        if button == "down" or step < 0:
            return self.base_scale
        return None

    def _zoom_axis(self, axis, x_anchor, y_anchor, scale):
        """同时缩放 X/Y 轴，并以鼠标位置为中心。"""
        left, right = axis.get_xlim()
        bottom, top = axis.get_ylim()
        axis.set_xlim(*self._scaled_limits(left, right, self._resolve_anchor(left, right, x_anchor), scale))
        axis.set_ylim(*self._scaled_limits(bottom, top, self._resolve_anchor(bottom, top, y_anchor), scale))

    def _resolve_anchor(self, lower, upper, anchor):
        """鼠标坐标无效时退回到当前坐标轴中心点。"""
        return anchor if anchor is not None else (lower + upper) / 2

    def _scaled_limits(self, lower, upper, anchor, scale):
        """计算缩放后的新边界，避免坐标轴被压缩到不可见。"""
        if upper - lower == 0:
            lower, upper = anchor - 0.5, anchor + 0.5
        new_lower = anchor - (anchor - lower) * scale
        new_upper = anchor + (upper - anchor) * scale
        return (lower, upper) if abs(new_upper - new_lower) < 1e-9 else (new_lower, new_upper)

    def _update_all_font_sizes(self):
        """根据当前缩放比例同步更新所有坐标轴上的数字字号。"""
        for axis in self.figure.axes:
            state = self.default_axes_state.get(id(axis))
            if state:
                self._apply_font_scale(axis, state, self._calculate_zoom_ratio(axis, state))

    def _calculate_zoom_ratio(self, axis, state):
        """计算当前视图相对默认视图的缩放倍数。"""
        default_x_span = abs(state["xlim"][1] - state["xlim"][0]) or 1.0
        default_y_span = abs(state["ylim"][1] - state["ylim"][0]) or 1.0
        current_x_span = abs(axis.get_xlim()[1] - axis.get_xlim()[0]) or 1.0
        current_y_span = abs(axis.get_ylim()[1] - axis.get_ylim()[0]) or 1.0
        return min(max(max(default_x_span / current_x_span, default_y_span / current_y_span), 0.8), 3.0)

    def _apply_font_scale(self, axis, state, scale_ratio):
        """把缩放倍数应用到刻度数字和图内数值标注。"""
        axis.tick_params(axis="both", labelsize=state["tick_font"] * scale_ratio)
        axis.xaxis.offsetText.set_fontsize(state["x_offset_font"] * scale_ratio)
        axis.yaxis.offsetText.set_fontsize(state["y_offset_font"] * scale_ratio)
        for index, text in enumerate(axis.texts):
            text.set_fontsize(self._pick_text_font(state["text_fonts"], index) * scale_ratio)

    def _pick_tick_font(self, axis):
        """优先从当前刻度标签中提取默认字号。"""
        for label in axis.get_xticklabels() + axis.get_yticklabels():
            if label.get_fontsize():
                return label.get_fontsize()
        return 10.0

    def _pick_text_font(self, fonts, index):
        """按顺序获取文本默认字号，避免文本数量变化时报错。"""
        if index < len(fonts):
            return fonts[index]
        return fonts[-1] if fonts else 8.0

    def _schedule_view_snapshot(self):
        """把滚轮缩放历史记录节流到一次，避免连续滚动时视图栈膨胀。"""
        if not self.toolbar or not hasattr(self.toolbar, "push_current"):
            return
        self._cancel_view_snapshot()
        try:
            self.history_job = self.tk_widget.after(self.history_delay_ms, self._flush_view_snapshot)
        except Exception as exc:
            logger.exception("安排图表视图快照失败: %s", exc)

    def _cancel_view_snapshot(self):
        """取消尚未执行的历史视图快照，避免重复压栈。"""
        if not self.history_job:
            return
        try:
            self.tk_widget.after_cancel(self.history_job)
        except Exception as exc:
            logger.exception("取消图表视图快照失败: %s", exc)
        finally:
            self.history_job = None

    def _flush_view_snapshot(self):
        """在滚轮操作停顿后再记录一次最终视图。"""
        self.history_job = None
        self.remember_view()

    @staticmethod
    def _should_lock_y_pan(axis):
        """单股分析图表默认支持双轴平移，因此拖动时不锁定 Y 轴。"""
        return False

    @staticmethod
    def _calculate_pan_target_limits(axis, start_xlim, start_ylim, delta_x_pixels, delta_y_pixels, lock_y):
        """按像素位移换算目标坐标范围，避免在变化中的坐标系里重复反算。"""
        axis_width = axis.bbox.width or 1.0
        axis_height = axis.bbox.height or 1.0
        x_span = start_xlim[1] - start_xlim[0]
        y_span = start_ylim[1] - start_ylim[0]
        delta_x_data = (delta_x_pixels / axis_width) * x_span
        target_xlim = (start_xlim[0] - delta_x_data, start_xlim[1] - delta_x_data)
        if lock_y:
            return target_xlim, start_ylim

        delta_y_data = (delta_y_pixels / axis_height) * y_span
        target_ylim = (start_ylim[0] - delta_y_data, start_ylim[1] - delta_y_data)
        return target_xlim, target_ylim
