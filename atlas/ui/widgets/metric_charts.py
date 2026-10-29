import math
import time
from collections import deque

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QFrame,
    QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, Signal
from PySide6.QtGui import (
    QPainter, QPen, QColor, QLinearGradient, QPainterPath,
    QFont, QFontMetrics
)

from atlas.ui.themes.dark_theme import COLORS


class MetricChart(QFrame):
    def __init__(self, title="", color=COLORS["chart_cpu"], max_points=120,
                 unit="%", parent=None):
        super().__init__(parent)
        self._title = title
        self._color = QColor(color)
        self._max_points = max_points
        self._unit = unit
        self._data = deque(maxlen=max_points)
        self._timestamps = deque(maxlen=max_points)
        self._current_value = 0.0
        self._min_value = 0.0
        self._max_value = 100.0
        self._active_window = "5m"

        self.setStyleSheet(f"""
            MetricChart {{
                background-color: {COLORS['bg_surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
            }}
        """)
        self.setMinimumHeight(170)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 12)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        title_vbox = QVBoxLayout()
        title_vbox.setContentsMargins(0, 0, 0, 0)
        title_vbox.setSpacing(2)

        self._title_label = QLabel(self._title.upper())
        self._title_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.8px;
        """)
        title_vbox.addWidget(self._title_label)

        self._stats_label = QLabel("AVG --  ·  MIN --  ·  MAX --")
        self._stats_label.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 10px;")
        title_vbox.addWidget(self._stats_label)
        header_layout.addLayout(title_vbox)

        header_layout.addStretch()

        self._value_label = QLabel(f"0.0{self._unit}")
        self._value_label.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: 20px;
            font-weight: 700;
        """)
        header_layout.addWidget(self._value_label)

        layout.addLayout(header_layout)

        self._canvas = _ChartCanvas(self)
        layout.addWidget(self._canvas, stretch=1)

    def add_value(self, value: float):
        v = float(value)
        self._data.append(v)
        self._timestamps.append(time.time())
        self._current_value = v
        self._value_label.setText(f"{v:.1f}{self._unit}")

        if len(self._data) > 0:
            d_list = list(self._data)
            avg_v = sum(d_list) / len(d_list)
            min_v = min(d_list)
            max_v = max(d_list)
            self._stats_label.setText(
                f"AVG {avg_v:.1f}{self._unit}  ·  MIN {min_v:.1f}{self._unit}  ·  MAX {max_v:.1f}{self._unit}"
            )
        self._canvas.update()

    def set_range(self, min_val: float, max_val: float):
        self._min_value = float(min_val)
        self._max_value = float(max_val)
        self._canvas.update()


class _ChartCanvas(QWidget):
    def __init__(self, chart: MetricChart):
        super().__init__(chart)
        self._chart = chart
        self.setMinimumHeight(80)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        data = list(self._chart._data)

        if len(data) < 2:
            painter.setPen(QColor(COLORS["text_tertiary"]))
            font = QFont("Segoe UI Variable Text", 11)
            painter.setFont(font)
            painter.drawText(
                QRectF(0, 0, w, h),
                Qt.AlignCenter,
                "Collecting real-time baseline data..."
            )
            painter.end()
            return

        pad_top = 8
        pad_bottom = 12
        pad_left = 6
        pad_right = 6
        chart_w = w - pad_left - pad_right
        chart_h = h - pad_top - pad_bottom

        painter.setPen(QPen(QColor(COLORS["border_subtle"]), 1, Qt.DashLine))
        for y_ratio in [0.25, 0.5, 0.75]:
            grid_y = pad_top + int(chart_h * y_ratio)
            painter.drawLine(pad_left, grid_y, w - pad_right, grid_y)

        val_min = self._chart._min_value
        val_max = self._chart._max_value
        val_range = max(val_max - val_min, 1.0)

        step = chart_w / max(len(data) - 1, 1)
        points = []
        for i, val in enumerate(data):
            x = pad_left + i * step
            norm = (max(val_min, min(val_max, val)) - val_min) / val_range
            y = pad_top + chart_h - (norm * chart_h)
            points.append(QPointF(x, y))

        grad = QLinearGradient(0, pad_top, 0, h - pad_bottom)
        c = QColor(self._chart._color)
        c.setAlpha(35)
        grad.setColorAt(0.0, c)
        c.setAlpha(0)
        grad.setColorAt(1.0, c)

        fill_path = QPainterPath()
        fill_path.moveTo(points[0].x(), h - pad_bottom)
        for p in points:
            fill_path.lineTo(p)
        fill_path.lineTo(points[-1].x(), h - pad_bottom)
        fill_path.closeSubpath()
        painter.fillPath(fill_path, grad)

        line_path = QPainterPath()
        line_path.moveTo(points[0])
        for p in points[1:]:
            line_path.lineTo(p)

        painter.setPen(QPen(self._chart._color, 1.8))
        painter.drawPath(line_path)

        last_p = points[-1]
        painter.setBrush(self._chart._color)
        painter.setPen(QPen(QColor(COLORS["bg_surface"]), 2))
        painter.drawEllipse(last_p, 3.5, 3.5)

        painter.end()


class MetricResourceCard(QFrame):
    def __init__(self, title: str, unit: str = "%", color: str = None, parent=None):
        super().__init__(parent)
        self._title = title
        self._unit = unit
        self._color = color or COLORS["accent_blue"]
        self._value = 0.0

        self.setStyleSheet(f"""
            MetricResourceCard {{
                background-color: {COLORS['bg_surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
            }}
        """)
        self.setFixedHeight(100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        self._title_label = QLabel(self._title.upper())
        self._title_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.8px;
        """)
        top_row.addWidget(self._title_label)
        top_row.addStretch()

        self._status_label = QLabel("Nominal")
        self._status_label.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 11px;")
        top_row.addWidget(self._status_label)
        layout.addLayout(top_row)

        mid_row = QHBoxLayout()
        mid_row.setContentsMargins(0, 0, 0, 0)
        self._value_label = QLabel(f"0{self._unit}")
        self._value_label.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: 22px;
            font-weight: 700;
        """)
        mid_row.addWidget(self._value_label)
        mid_row.addStretch()

        self._subtitle_label = QLabel("")
        self._subtitle_label.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 11px;")
        mid_row.addWidget(self._subtitle_label)
        layout.addLayout(mid_row)

        self._progress = QWidget()
        self._progress.setFixedHeight(4)
        self._progress.paintEvent = self._paint_progress
        layout.addWidget(self._progress)

    def _paint_progress(self, event):
        painter = QPainter(self._progress)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self._progress.width()
        h = self._progress.height()

        painter.setBrush(QColor(COLORS["bg_surface_raised"]))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, w, h, 2, 2)

        fill_w = int(w * (min(max(self._value, 0.0), 100.0) / 100.0))
        if fill_w > 0:
            c = QColor(self._color)
            if self._value > 85:
                c = QColor(COLORS["danger"])
            elif self._value > 70:
                c = QColor(COLORS["warning"])
            painter.setBrush(c)
            painter.drawRoundedRect(0, 0, fill_w, h, 2, 2)
        painter.end()

    def set_value(self, value: float, subtitle: str = "", status: str = ""):
        self._value = float(value)
        if self._unit == "%":
            self._value_label.setText(f"{self._value:.0f}%")
        else:
            self._value_label.setText(f"{self._value:.1f}{self._unit}")

        if subtitle:
            self._subtitle_label.setText(subtitle)
        if status:
            self._status_label.setText(status)
        elif self._value > 85:
            self._status_label.setText("Critical")
            self._status_label.setStyleSheet(f"color: {COLORS['danger']}; font-size: 11px; font-weight: 600;")
        elif self._value > 70:
            self._status_label.setText("Elevated")
            self._status_label.setStyleSheet(f"color: {COLORS['warning']}; font-size: 11px; font-weight: 600;")
        else:
            self._status_label.setText("Nominal")
            self._status_label.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 11px;")

        self._progress.update()


class GaugeWidget(MetricResourceCard):
    def __init__(self, title="", color=COLORS["chart_cpu"], parent=None):
        super().__init__(title=title, unit="%", color=color, parent=parent)


class StatusIndicator(QWidget):
    def __init__(self, label="", parent=None):
        super().__init__(parent)
        self._label = label
        self._status = "unknown"
        self._color = QColor(COLORS["health_unknown"])
        self.setFixedHeight(24)

    def set_status(self, status: str, color=None):
        self._status = status
        if color:
            self._color = QColor(color)
        elif status in ("healthy", "nominal", "active", "online"):
            self._color = QColor(COLORS["health_healthy"])
        elif status in ("warning", "elevated", "degraded"):
            self._color = QColor(COLORS["health_warning"])
        elif status in ("critical", "danger", "error"):
            self._color = QColor(COLORS["health_critical"])
        else:
            self._color = QColor(COLORS["health_unknown"])
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        dot_radius = 3.5
        cy = self.height() / 2
        cx = dot_radius + 4

        glow = QColor(self._color)
        glow.setAlpha(40)
        painter.setBrush(glow)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(cx, cy), dot_radius + 2.5, dot_radius + 2.5)

        painter.setBrush(self._color)
        painter.drawEllipse(QPointF(cx, cy), dot_radius, dot_radius)

        painter.setPen(QColor(COLORS["text_secondary"]))
        font = QFont("Segoe UI Variable Text", 11)
        painter.setFont(font)
        text = f"{self._label}: {self._status.title()}" if self._label else self._status.title()
        painter.drawText(int(cx + dot_radius + 6), int(cy + 4), text)

        painter.end()
