from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from atlas.ui.themes.dark_theme import COLORS


class SidebarItem:
    def __init__(self, name: str, icon_glyph: str, view_name: str, category: str = ""):
        self.name = name
        self.icon_glyph = icon_glyph
        self.view_name = view_name
        self.category = category


SIDEBAR_SECTIONS = [
    ("SYSTEM", [
        SidebarItem("Overview", "⊞", "overview"),
        SidebarItem("Machine", "⬡", "machine"),
        SidebarItem("Processes", "☵", "processes"),
        SidebarItem("Applications", "▦", "applications"),
        SidebarItem("Services", "◎", "services"),
        SidebarItem("Network", "⌖", "network"),
    ]),
    ("INTELLIGENCE", [
        SidebarItem("Incidents", "⚠", "incidents"),
        SidebarItem("Changes", "◬", "changes"),
        SidebarItem("Timeline", "◷", "timeline"),
        SidebarItem("Graph", "◈", "graph"),
        SidebarItem("AI Copilot", "✦", "ai"),
    ]),
    ("CONFIGURATION", [
        SidebarItem("Settings", "⚙", "settings"),
    ]),
]


class SidebarButton(QPushButton):
    def __init__(self, item: SidebarItem, parent=None):
        super().__init__(parent)
        self.item = item
        self.setFixedHeight(34)
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        self.setText(f"  {item.icon_glyph}   {item.name}")
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['sidebar_text']};
                border: none;
                border-left: 3px solid transparent;
                border-radius: 4px;
                text-align: left;
                padding-left: 10px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {COLORS['sidebar_hover']};
                color: {COLORS['text_primary']};
            }}
            QPushButton:checked {{
                background-color: {COLORS['sidebar_active']};
                color: {COLORS['sidebar_text_active']};
                border-left: 3px solid {COLORS['accent_blue']};
                font-weight: 600;
            }}
        """)


class Sidebar(QWidget):
    view_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)
        self.setStyleSheet(f"""
            Sidebar {{
                background-color: {COLORS['sidebar_bg']};
                border-right: 1px solid {COLORS['border']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 16, 10, 12)
        layout.setSpacing(4)

        header_box = QVBoxLayout()
        header_box.setContentsMargins(8, 4, 8, 12)
        header_box.setSpacing(4)

        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(0, 0, 0, 0)
        brand_row.setSpacing(8)

        logo_icon = QLabel("✦")
        logo_icon.setStyleSheet(f"color: {COLORS['accent_blue']}; font-size: 16px; font-weight: 800;")
        brand_row.addWidget(logo_icon)

        title_lbl = QLabel("ATLAS")
        title_lbl.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: 16px;
            font-weight: 800;
            letter-spacing: 1.5px;
        """)
        brand_row.addWidget(title_lbl)

        version_badge = QLabel("v1.0")
        version_badge.setStyleSheet(f"""
            color: {COLORS['text_tertiary']};
            background-color: {COLORS['bg_surface_raised']};
            border: 1px solid {COLORS['border']};
            border-radius: 3px;
            padding: 1px 4px;
            font-size: 9px;
            font-weight: 600;
        """)
        brand_row.addWidget(version_badge)
        brand_row.addStretch()
        header_box.addLayout(brand_row)

        tagline = QLabel("Windows Digital Twin")
        tagline.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 11px;")
        header_box.addWidget(tagline)

        layout.addLayout(header_box)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background-color: {COLORS['border_subtle']}; max-height: 1px;")
        layout.addWidget(sep)
        layout.addSpacing(6)

        self._buttons = []
        for sec_name, items in SIDEBAR_SECTIONS:
            sec_lbl = QLabel(sec_name)
            sec_lbl.setStyleSheet(f"""
                color: {COLORS['text_tertiary']};
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.8px;
                padding: 8px 10px 4px 10px;
            """)
            layout.addWidget(sec_lbl)

            for item in items:
                btn = SidebarButton(item)
                btn.clicked.connect(lambda checked, v=item.view_name: self._on_click(v))
                layout.addWidget(btn)
                self._buttons.append(btn)

        layout.addStretch()

        self._status_card = QFrame()
        self._status_card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_surface']};
                border: 1px solid {COLORS['border_subtle']};
                border-radius: 6px;
                padding: 8px;
            }}
        """)
        sc_layout = QVBoxLayout(self._status_card)
        sc_layout.setContentsMargins(6, 6, 6, 6)
        sc_layout.setSpacing(4)

        self._sc_monitoring = QLabel("●  Monitoring Active")
        self._sc_monitoring.setStyleSheet(f"color: {COLORS['success']}; font-size: 11px; font-weight: 600;")
        sc_layout.addWidget(self._sc_monitoring)

        self._sc_ollama = QLabel("○  Ollama Ready")
        self._sc_ollama.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        sc_layout.addWidget(self._sc_ollama)

        layout.addWidget(self._status_card)

    def _on_click(self, view_name: str):
        for btn in self._buttons:
            btn.setChecked(btn.item.view_name == view_name)
        self.view_changed.emit(view_name)

    def set_active(self, view_name: str):
        for btn in self._buttons:
            btn.setChecked(btn.item.view_name == view_name)

    def update_status(self, monitoring: bool, ollama_connected: bool, ai_model: str = ""):
        if monitoring:
            self._sc_monitoring.setText("●  Monitoring Active")
            self._sc_monitoring.setStyleSheet(f"color: {COLORS['success']}; font-size: 11px; font-weight: 600;")
        else:
            self._sc_monitoring.setText("○  Monitoring Paused")
            self._sc_monitoring.setStyleSheet(f"color: {COLORS['warning']}; font-size: 11px;")

        if ollama_connected:
            text = f"●  AI Online ({ai_model})" if ai_model else "●  AI Online"
            self._sc_ollama.setText(text)
            self._sc_ollama.setStyleSheet(f"color: {COLORS['accent_blue']}; font-size: 11px; font-weight: 600;")
        else:
            self._sc_ollama.setText("○  AI Offline")
            self._sc_ollama.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 11px;")

    def set_footer_status(self, version: str = "v0.2.0", ai_status: str = "Online", ollama_status: str = "Online", monitoring: str = "Active"):
        self.update_status(monitoring.lower() == "active", ai_status.lower() == "online" or ollama_status.lower() == "online", "")
