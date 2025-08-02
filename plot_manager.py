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
        # --- Data Buffers ---
        self.max_time_span = 180.0
        self.data_ch1 = deque()
        self.data_ch2 = deque()
        # --- Marker Management ---
        self.markers = deque() # time stamps
        self.marker_lines = deque() # line objects
        # --- Plot Lines---
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
        """Add a visual marker (a vertical red line) at a specific time point."""
        self.markers.append(time)
        line = self.ax.axvline(x=time, color='r', linestyle='--', linewidth=1.5)
        self.marker_lines.append(line)

    def add_data_point(self, channel, time, value):
        """Add a new (time, value) data point to the appropriate channel's deque."""
        if channel == 1:
            self.data_ch1.append((time, value))
            # remove old data points if they exceed the max time span
            while self.data_ch1[-1][0] - self.data_ch1[0][0] > self.max_time_span:
                self.data_ch1.popleft()
        elif channel == 2:
            self.data_ch2.append((time, value))
            while self.data_ch2[-1][0] - self.data_ch2[0][0] > self.max_time_span:
                self.data_ch2.popleft()

    def update_plot(self):
        """Redraw the plot, updating both data and axis limits dynamically."""
        # 1. Update the data lines
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
        # 2. Update the X-axis limits
        all_times = [item[0] for item in self.data_ch1] + [item[0] for item in self.data_ch2]
        if all_times:
            latest_time = max(all_times)
            if latest_time <= self.max_time_span:
                # static phase: keep the X-axis fixed
                if self.ax.get_xlim() != (0, self.max_time_span):
                    self.ax.set_xlim(0, self.max_time_span)
            else:
                # dynamic phase: adjust the X-axis to show the latest data
                self.ax.set_xlim(latest_time - self.max_time_span, latest_time)
        # 3. Clean up old markers
        x_min, _ = self.ax.get_xlim()
        while self.markers and self.markers[0] < x_min:
            self.markers.popleft()
            line_to_remove = self.marker_lines.popleft()
            line_to_remove.remove()    
        # 4. Update the Y-axis limits dynamically
        all_values = [item[1] for item in self.data_ch1] + [item[1] for item in self.data_ch2]
        if len(all_values) > 1: # at least two points to calculate range
            min_val = min(all_values)
            max_val = max(all_values)
            # calculate the range of the data
            data_range = max_val - min_val
            if data_range < 1e-9:
                margin = 0.2 # if the range is too small, use a fixed margin
            else:
                margin = data_range * 0.1 # use 10% of the range as margin
            # calculate and set new limits
            new_min = min_val - margin
            new_max = max_val + margin
            self.ax.set_ylim(new_min, new_max)
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
