from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QLineEdit, QPushButton, QSizePolicy, QLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush

from atlas.ui.themes.dark_theme import COLORS


class AtlasBadge(QFrame):
    def __init__(self, text: str, variant: str = "info", parent=None):
        super().__init__(parent)
        self._text = text
        self._variant = variant
        self.setFixedHeight(22)
        self._setup_style()

    def set_text(self, text: str, variant: str = None):
        self._text = text
        if variant:
            self._variant = variant
        self._setup_style()
        self.update()

    def set_variant(self, variant: str):
        self._variant = variant
        self._setup_style()
        self.update()

    def _setup_style(self):
        palette = {
            "success": (COLORS["success_bg"], COLORS["success"], COLORS["success"]),
            "healthy": (COLORS["success_bg"], COLORS["success"], COLORS["success"]),
            "warning": (COLORS["warning_bg"], COLORS["warning"], COLORS["warning"]),
            "danger": (COLORS["error_bg"], COLORS["danger"], COLORS["danger"]),
            "critical": (COLORS["error_bg"], COLORS["danger"], COLORS["danger"]),
            "info": (COLORS["info_bg"], COLORS["info"], COLORS["info"]),
            "accent": (COLORS["info_bg"], COLORS["accent_blue"], COLORS["accent_blue"]),
            "neutral": (COLORS["bg_surface_raised"], COLORS["text_secondary"], COLORS["border"]),
            "default": (COLORS["bg_surface_raised"], COLORS["text_secondary"], COLORS["border"]),
        }
        bg, fg, border = palette.get(self._variant, palette["info"])
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 1px 8px;
            }}
            QLabel {{
                color: {fg};
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.3px;
                background: transparent;
                border: none;
            }}
        """)
        layout = self.layout()
        if not layout:
            layout = QHBoxLayout(self)
            layout.setContentsMargins(6, 0, 6, 0)
            layout.setSpacing(0)
            self._label = QLabel(self._text)
            self._label.setAlignment(Qt.AlignCenter)
            layout.addWidget(self._label)
        else:
            self._label.setText(self._text)


class AtlasCard(QFrame):
    def __init__(self, title: str = "", subtitle: str = "", parent=None):
        super().__init__(parent)
        self._title = title
        self._subtitle = subtitle
        self.setStyleSheet(f"""
            AtlasCard {{
                background-color: {COLORS['bg_surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
            }}
        """)
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(18, 16, 18, 16)
        self._main_layout.setSpacing(12)

        if title or subtitle:
            self._header_layout = QHBoxLayout()
            self._header_layout.setContentsMargins(0, 0, 0, 0)
            self._header_layout.setSpacing(8)

            titles_vbox = QVBoxLayout()
            titles_vbox.setContentsMargins(0, 0, 0, 0)
            titles_vbox.setSpacing(2)

            self._title_label = QLabel(title.upper() if title else "")
            self._title_label.setStyleSheet(f"""
                color: {COLORS['text_secondary']};
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.8px;
            """)
            titles_vbox.addWidget(self._title_label)

            if subtitle:
                self._sub_label = QLabel(subtitle)
                self._sub_label.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 11px;")
                titles_vbox.addWidget(self._sub_label)
            else:
                self._sub_label = None

            self._header_layout.addLayout(titles_vbox)
            self._header_layout.addStretch()
            self._main_layout.addLayout(self._header_layout)

    def add_header_widget(self, item):
        if hasattr(self, "_header_layout"):
            if isinstance(item, QLayout):
                self._header_layout.addLayout(item)
            else:
                self._header_layout.addWidget(item)

    def add_widget(self, widget: QWidget):
        self._main_layout.addWidget(widget)

    def add_layout(self, layout):
        self._main_layout.addLayout(layout)


class AtlasProgressBar(QWidget):
    def __init__(self, value: float = 0.0, color: str = None, parent=None):
        super().__init__(parent)
        self._value = max(0.0, min(100.0, float(value)))
        self._color = color or COLORS["accent_blue"]
        self.setFixedHeight(4)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_value(self, value: float, color: str = None):
        self._value = max(0.0, min(100.0, float(value)))
        if color:
            self._color = color
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()

        painter.setBrush(QColor(COLORS["bg_surface_raised"]))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, w, h, 2, 2)

        fill_w = int(w * (self._value / 100.0))
        if fill_w > 0:
            color = self._color
            if not self._color:
                if self._value > 85:
                    color = COLORS["danger"]
                elif self._value > 70:
                    color = COLORS["warning"]
                else:
                    color = COLORS["accent_blue"]
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(0, 0, fill_w, h, 2, 2)
        painter.end()


class AtlasSearchBox(QFrame):
    text_changed = Signal(str)

    def __init__(self, placeholder: str = "Search...", parent=None):
        super().__init__(parent)
        self.setFixedHeight(34)
        self.setStyleSheet(f"""
            AtlasSearchBox {{
                background-color: {COLORS['bg_surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 5px;
            }}
            AtlasSearchBox:focus-within {{
                border-color: {COLORS['border_focus']};
                background-color: {COLORS['bg_surface_raised']};
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(6)

        icon_label = QLabel("⌕")
        icon_label.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 14px;")
        layout.addWidget(icon_label)

        self._input = QLineEdit()
        self._input.setPlaceholderText(placeholder)
        self._input.setStyleSheet("border: none; background: transparent; padding: 0; font-size: 12px;")
        self._input.textChanged.connect(self.text_changed.emit)
        layout.addWidget(self._input)

    def text(self) -> str:
        return self._input.text()

    def clear(self):
        self._input.clear()


class AtlasEmptyState(QWidget):
    def __init__(self, title: str, description: str = "", action_text: str = "", icon_symbol: str = "", message: str = "", parent=None):
        super().__init__(parent)
        desc = description or message
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 32, 24, 32)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignCenter)

        if icon_symbol:
            i_lbl = QLabel(icon_symbol)
            i_lbl.setStyleSheet(f"font-size: 28px; color: {COLORS['accent_blue']};")
            i_lbl.setAlignment(Qt.AlignCenter)
            layout.addWidget(i_lbl)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {COLORS['text_primary']};")
        t_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(t_lbl)

        if desc:
            d_lbl = QLabel(desc)
            d_lbl.setStyleSheet(f"font-size: 12px; color: {COLORS['text_tertiary']}; line-height: 1.4;")
            d_lbl.setWordWrap(True)
            d_lbl.setAlignment(Qt.AlignCenter)
            layout.addWidget(d_lbl)

        if action_text:
            self._action_btn = QPushButton(action_text)
            self._action_btn.setObjectName("primary")
            self._action_btn.setCursor(Qt.PointingHandCursor)
            layout.addSpacing(6)
            layout.addWidget(self._action_btn, alignment=Qt.AlignCenter)
        else:
            self._action_btn = None
