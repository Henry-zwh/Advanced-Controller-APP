import tkinter as tk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from collections import deque


class PlotManager:
    """Manage a Matplotlib plot embedded in a Tkinter frame."""
    """Handle real-time data plotting for 2 channels. """

    def __init__(self, parent_frame):
        """Initialize the PlotManager."""
        self.fig = Figure(figsize=(8, 3), dpi=90)
        self.ax = self.fig.add_subplot()
        
        # --- Plot Aesthetics ---
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Voltage (V)")
        self.ax.grid(True)
        self.ax.set_facecolor('#f0f0f0')

        # --- 【核心修改】: 使用deque来存储 (time, value) 对 ---
        self.max_time_span = 180.0
        # deque是高效的，但我们仍需手动管理基于时间的窗口大小
        self.data_ch1 = deque()
        self.data_ch2 = deque()

        # --- 【核心修改】: 添加Marker管理 ---
        self.markers = deque() # 存储marker的时间戳
        self.marker_lines = deque() # 存储matplotlib的垂直线对象
        
        # --- Plot Lines (初始化为空)---
        self.line1, = self.ax.plot([], [], 'royalblue', label="CH 1")
        self.line2, = self.ax.plot([], [], 'orangered', label="CH 2")
        self.ax.legend(loc='upper right')
        
        # --- Axis Configuration ---
        self.ax.set_xlim(0, self.max_time_span)
        self.ax.set_ylim(-0.5, 3.5)

        # --- Embed Plot in Tkinter ---
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.fig.tight_layout()

    def add_marker(self, time):
        """
        Adds a visual marker (a vertical red line) at a specific time point.
        """
        # 存储marker的时间戳
        self.markers.append(time)
        
        # 在图上绘制一条新的垂直线
        # ymin=0, ymax=1 表示该线从Y轴底部贯穿到顶部
        line = self.ax.axvline(x=time, color='r', linestyle='--', linewidth=1.5)
        
        # 存储这条线的对象，以便后续管理
        self.marker_lines.append(line)

    def add_data_point(self, channel, time, value):
        """
        【核心修改】: 接口变更，接收时间戳。
        Adds a new (time, value) data point to the appropriate channel's deque.
        """
        if channel == 1:
            self.data_ch1.append((time, value))
            # 移除超出180秒时间窗口的旧数据
            while self.data_ch1[-1][0] - self.data_ch1[0][0] > self.max_time_span:
                self.data_ch1.popleft()
        elif channel == 2:
            self.data_ch2.append((time, value))
            while self.data_ch2[-1][0] - self.data_ch2[0][0] > self.max_time_span:
                self.data_ch2.popleft()

    def update_plot(self):
        """
        【核心修改】: 全新的更新逻辑。
        Redraws the plot, updating both data and axis limits dynamically.
        """
        # --- 1. 更新线条数据 ---
        if self.data_ch1:
            t1, v1 = zip(*self.data_ch1)
            self.line1.set_data(t1, v1)
        else:
            self.line1.set_data([], [])

        if self.data_ch2:
            t2, v2 = zip(*self.data_ch2)
            self.line2.set_data(t2, v2)
        else:
            self.line2.set_data([], [])
            
        # --- 2. 智能更新X轴范围 ---
        all_times = [item[0] for item in self.data_ch1] + [item[0] for item in self.data_ch2]
        if all_times:
            latest_time = max(all_times)
            if latest_time <= self.max_time_span:
                # 填充阶段: 保持X轴固定为 [0, 180]
                # 检查当前范围是否正确，避免不必要的重设
                if self.ax.get_xlim() != (0, self.max_time_span):
                    self.ax.set_xlim(0, self.max_time_span)
            else:
                # 滚动阶段: 移动X轴窗口
                self.ax.set_xlim(latest_time - self.max_time_span, latest_time)

        # --- 【核心修改】: 管理和清理旧的Markers ---
        x_min, _ = self.ax.get_xlim()
        # 只要最左侧的marker已经滚出视图，就清理它
        while self.markers and self.markers[0] < x_min:
            # 从数据中移除时间戳
            self.markers.popleft()
            # 从图形中移除对应的线对象
            line_to_remove = self.marker_lines.popleft()
            line_to_remove.remove()    
        
        # --- 3. 智能更新Y轴范围 (逻辑不变，但数据源变了) ---
        all_values = [item[1] for item in self.data_ch1] + [item[1] for item in self.data_ch2]
        
        # 只有当缓冲区中至少有2个数据点时，才进行缩放
        if len(all_values) > 1:
            min_val = min(all_values)
            max_val = max(all_values)
            
            # 计算数据的动态范围 (range)
            data_range = max_val - min_val
            
            # 处理特殊情况：如果所有数据点都相同（一条平线）
            if data_range < 1e-9: # 使用一个很小的数来判断是否为0
                # 给一个以数据点为中心的固定范围，例如 +/- 0.5
                margin = 0.2
            else:
                # 正常情况：计算10%的边距
                # 总范围是 data_range + 2 * margin = 1.2 * data_range
                margin = data_range * 0.1
            
            # 计算新的Y轴上下限
            new_min = min_val - margin
            new_max = max_val + margin
            
            # 直接设置新的Y轴范围，不再与旧范围比较
            self.ax.set_ylim(new_min, new_max)
        
        # 安排重绘
        self.canvas.draw_idle()

    def clear_plot(self):
        """Reset the plot to its initial state."""
        self.data_ch1.clear()
        self.data_ch2.clear()
        for line in self.marker_lines:
            line.remove()
        self.markers.clear()
        self.marker_lines.clear()
        self.line1.set_data([], [])
        self.line2.set_data([], [])
        self.ax.set_xlim(0, self.max_time_span)
        self.ax.set_ylim(-1, 1)
        self.update_plot()
