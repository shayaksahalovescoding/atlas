from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

COLORS = {
    "bg_base": "#0B0F14",
    "bg_primary": "#0B0F14",
    "bg_surface": "#11161D",
    "bg_surface_raised": "#161C24",
    "bg_surface_hover": "#1C232E",
    "bg_surface_active": "#222B38",
    "bg_raised": "#161C24",
    "bg_subtle": "#161C24",
    "bg_card": "#11161D",
    "bg_secondary": "#11161D",
    "bg_tertiary": "#161C24",
    "bg_hover": "#1C232E",
    "bg_selected": "rgba(56, 189, 248, 0.12)",

    "border": "#242B35",
    "border_subtle": "#1B222B",
    "border_light": "#2E3744",
    "border_focus": "#38BDF8",

    "text_primary": "#F1F5F9",
    "text_secondary": "#94A3B8",
    "text_tertiary": "#64748B",
    "text_muted": "#475569",
    "text_link": "#38BDF8",

    "accent": "#38BDF8",
    "accent_muted": "#1E293B",
    "accent_blue": "#38BDF8",
    "accent_primary": "#38BDF8",
    "accent_hover": "#7DD3FC",
    "accent_glow": "rgba(56, 189, 248, 0.15)",
    "accent_cyan": "#06B6D4",
    "accent_purple": "#A855F7",
    "accent_pink": "#EC4899",
    "accent_green": "#22C55E",
    "accent_orange": "#F59E0B",
    "accent_red": "#EF4444",

    "success": "#22C55E",
    "success_bg": "rgba(34, 197, 94, 0.12)",
    "warning": "#F59E0B",
    "warning_bg": "rgba(245, 158, 11, 0.12)",
    "danger": "#EF4444",
    "error": "#EF4444",
    "error_bg": "rgba(239, 68, 68, 0.12)",
    "info": "#38BDF8",
    "info_bg": "rgba(56, 189, 248, 0.12)",

    "chart_cpu": "#38BDF8",
    "chart_memory": "#A855F7",
    "chart_gpu": "#22C55E",
    "chart_disk": "#F59E0B",
    "chart_network": "#06B6D4",

    "health_healthy": "#22C55E",
    "health_warning": "#F59E0B",
    "health_critical": "#EF4444",
    "health_unknown": "#64748B",

    "graph_node": "#38BDF8",
    "graph_edge": "#242B35",
    "graph_node_selected": "#7DD3FC",
    "graph_node_process": "#A855F7",
    "graph_node_service": "#22C55E",
    "graph_node_app": "#F59E0B",
    "graph_node_hardware": "#06B6D4",

    "sidebar_bg": "#080B0F",
    "sidebar_surface": "#0E131A",
    "sidebar_hover": "#141A22",
    "sidebar_active": "rgba(56, 189, 248, 0.10)",
    "sidebar_text": "#94A3B8",
    "sidebar_text_active": "#F1F5F9",

    "header_bg": "#0B0F14",
    "header_border": "#1B222B",

    "scrollbar": "#242B35",
    "scrollbar_hover": "#3E4856",
}

STYLESHEET = f"""
QMainWindow {{
    background-color: {COLORS['bg_base']};
}}

QWidget {{
    background-color: transparent;
    color: {COLORS['text_primary']};
    font-family: 'Segoe UI Variable Text', 'Segoe UI', -apple-system, sans-serif;
    font-size: 13px;
}}

QLabel {{
    color: {COLORS['text_primary']};
    background: transparent;
}}

QPushButton {{
    background-color: {COLORS['bg_surface_raised']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 5px;
    padding: 6px 14px;
    font-weight: 500;
    font-size: 12px;
}}

QPushButton:hover {{
    background-color: {COLORS['bg_surface_hover']};
    border-color: {COLORS['border_light']};
}}

QPushButton:pressed {{
    background-color: {COLORS['bg_surface_active']};
}}

QPushButton#primary {{
    background-color: {COLORS['accent_blue']};
    color: #0B0F14;
    border: 1px solid {COLORS['accent_blue']};
    font-weight: 600;
}}

QPushButton#primary:hover {{
    background-color: {COLORS['accent_hover']};
    border-color: {COLORS['accent_hover']};
}}

QPushButton#danger {{
    background-color: {COLORS['error_bg']};
    color: {COLORS['error']};
    border: 1px solid {COLORS['error']};
}}

QPushButton#danger:hover {{
    background-color: {COLORS['error']};
    color: #FFFFFF;
}}

QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {COLORS['bg_surface']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 5px;
    padding: 7px 12px;
    font-size: 12px;
    selection-background-color: {COLORS['accent_blue']};
    selection-color: #0B0F14;
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {COLORS['border_focus']};
    background-color: {COLORS['bg_surface_raised']};
}}

QScrollBar:vertical {{
    background-color: transparent;
    width: 6px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: {COLORS['scrollbar']};
    border-radius: 3px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {COLORS['scrollbar_hover']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    background: transparent;
}}

QScrollBar:horizontal {{
    background-color: transparent;
    height: 6px;
}}

QScrollBar::handle:horizontal {{
    background-color: {COLORS['scrollbar']};
    border-radius: 3px;
    min-width: 24px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {COLORS['scrollbar_hover']};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
    background: transparent;
}}

QTableWidget, QTreeWidget, QListWidget {{
    background-color: {COLORS['bg_surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    gridline-color: transparent;
    outline: none;
}}

QTableWidget::item, QTreeWidget::item, QListWidget::item {{
    padding: 6px 10px;
    border: none;
    border-bottom: 1px solid {COLORS['border_subtle']};
}}

QTableWidget::item:selected, QTreeWidget::item:selected, QListWidget::item:selected {{
    background-color: {COLORS['bg_selected']};
    color: {COLORS['text_primary']};
}}

QTableWidget::item:hover, QTreeWidget::item:hover, QListWidget::item:hover {{
    background-color: {COLORS['bg_surface_hover']};
}}

QHeaderView::section {{
    background-color: {COLORS['bg_surface_raised']};
    color: {COLORS['text_secondary']};
    padding: 8px 10px;
    border: none;
    border-bottom: 1px solid {COLORS['border']};
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 0.5px;
}}

QHeaderView::section:hover {{
    background-color: {COLORS['bg_surface_hover']};
    color: {COLORS['text_primary']};
}}

QTabWidget::pane {{
    background-color: {COLORS['bg_surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
}}

QTabBar::tab {{
    background-color: {COLORS['bg_surface_raised']};
    color: {COLORS['text_secondary']};
    padding: 6px 14px;
    border: 1px solid {COLORS['border']};
    border-bottom: none;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    margin-right: 2px;
    font-size: 12px;
}}

QTabBar::tab:selected {{
    background-color: {COLORS['bg_surface']};
    color: {COLORS['text_primary']};
    border-bottom: 2px solid {COLORS['accent_blue']};
}}

QTabBar::tab:hover {{
    color: {COLORS['text_primary']};
}}

QComboBox {{
    background-color: {COLORS['bg_surface_raised']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 5px;
    padding: 5px 12px;
    font-size: 12px;
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS['bg_surface_raised']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    selection-background-color: {COLORS['bg_selected']};
    outline: none;
}}

QProgressBar {{
    background-color: {COLORS['bg_surface_raised']};
    border: none;
    border-radius: 2px;
    height: 4px;
    text-align: center;
    color: transparent;
}}

QProgressBar::chunk {{
    border-radius: 2px;
    background-color: {COLORS['accent_blue']};
}}

QToolTip {{
    background-color: {COLORS['bg_surface_raised']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_light']};
    border-radius: 4px;
    padding: 5px 9px;
    font-size: 11px;
}}

QSplitter::handle {{
    background-color: {COLORS['border_subtle']};
}}

QSplitter::handle:hover {{
    background-color: {COLORS['accent_blue']};
}}
"""

def apply_theme(app: QApplication):
    app.setStyleSheet(STYLESHEET)
    font = QFont("Segoe UI Variable Text", 10)
    font.setStyleHint(QFont.SansSerif)
    app.setFont(font)
