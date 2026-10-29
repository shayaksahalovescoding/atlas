from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QStatusBar, QLabel, QFrame
)
from PySide6.QtCore import Qt, QTimer, Signal, QDateTime
from PySide6.QtGui import QIcon, QColor

from atlas.ui.themes.dark_theme import COLORS
from atlas.ui.widgets.components import AtlasBadge
from atlas.ui.widgets.sidebar import Sidebar
from atlas.ui.dashboards.overview_dashboard import OverviewDashboard
from atlas.ui.dashboards.process_view import ProcessView
from atlas.ui.dashboards.application_view import ApplicationView, ServiceView
from atlas.ui.dashboards.network_view import NetworkView, IncidentsView, ChangesView
from atlas.ui.dashboards.timeline_view import TimelineView, MachineView, SettingsView
from atlas.ui.graph.graph_widget import GraphWidget
from atlas.ui.chat.ai_chat_view import AIChatView


VIEW_METADATA = {
    "overview": ("Overview", "Real-time system health and machine intelligence"),
    "machine": ("Machine Architecture", "Hardware topology, processors, memory, and storage drives"),
    "processes": ("Process Explorer", "Live process activity, threads, and memory allocations"),
    "applications": ("Application Inventory", "Installed packages, running software, and associated processes"),
    "services": ("System Services", "Windows background services, startup policies, and states"),
    "network": ("Network Observability", "Throughput telemetry, network adapters, and active sockets"),
    "incidents": ("Incidents & Diagnostics", "Detected system anomalies, crashes, and performance alerts"),
    "changes": ("State Drift & Changes", "System mutations, configuration deltas, and software installs"),
    "timeline": ("Event Timeline", "Chronological audit stream of hardware and process events"),
    "graph": ("Digital Twin Topology", "Interactive entity-relationship graph of your machine"),
    "ai": ("System Intelligence Studio", "Diagnostic reasoning and hypothesis testing over machine telemetry"),
    "settings": ("Settings & Preferences", "Monitoring intervals, telemetry collection, and local AI model"),
}


class AtlasTopBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(54)
        self.setStyleSheet(f"""
            AtlasTopBar {{
                background-color: {COLORS['bg_surface']};
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 0, 24, 0)
        layout.setSpacing(14)

        self._title_label = QLabel("Overview")
        self._title_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 700;
            color: {COLORS['text_primary']};
        """)
        layout.addWidget(self._title_label)

        sep = QLabel("/")
        sep.setStyleSheet(f"color: {COLORS['border_light']}; font-size: 14px; font-weight: 300;")
        layout.addWidget(sep)

        self._desc_label = QLabel("Real-time system health and machine intelligence")
        self._desc_label.setStyleSheet(f"""
            font-size: 12px;
            color: {COLORS['text_tertiary']};
        """)
        layout.addWidget(self._desc_label)

        layout.addStretch()

        self._monitoring_badge = AtlasBadge("● Monitoring", "healthy")
        layout.addWidget(self._monitoring_badge)

        self._ai_badge = AtlasBadge("● AI Online", "accent")
        layout.addWidget(self._ai_badge)

        self._ollama_badge = AtlasBadge("● Ollama", "info")
        layout.addWidget(self._ollama_badge)

        self._clock_label = QLabel("--:--:--")
        self._clock_label.setStyleSheet(f"""
            font-family: 'Consolas', monospace;
            font-size: 11px;
            color: {COLORS['text_secondary']};
            background-color: {COLORS['bg_raised']};
            border: 1px solid {COLORS['border']};
            border-radius: 4px;
            padding: 3px 8px;
        """)
        layout.addWidget(self._clock_label)

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()

    def _update_clock(self):
        now = QDateTime.currentDateTime().toString("HH:mm:ss")
        self._clock_label.setText(now)

    def set_view_meta(self, title: str, description: str):
        self._title_label.setText(title)
        self._desc_label.setText(description)

    def update_status(self, ai_connected: bool, monitoring: bool = True):
        if monitoring:
            self._monitoring_badge.set_text("● Monitoring")
            self._monitoring_badge.set_variant("healthy")
        else:
            self._monitoring_badge.set_text("● Paused")
            self._monitoring_badge.set_variant("warning")

        if ai_connected:
            self._ai_badge.set_text("● AI Online")
            self._ai_badge.set_variant("accent")
            self._ollama_badge.set_text("● Ollama")
            self._ollama_badge.set_variant("healthy")
        else:
            self._ai_badge.set_text("● AI Offline")
            self._ai_badge.set_variant("default")
            self._ollama_badge.set_text("● Ollama Offline")
            self._ollama_badge.set_variant("warning")


class MainWindow(QMainWindow):
    query_submitted = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ATLAS — Understand your machine.")
        self.setMinimumSize(1280, 800)
        self.resize(1600, 960)
        self.setStyleSheet(f"background-color: {COLORS['bg_primary']};")

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._sidebar = Sidebar()
        self._sidebar.view_changed.connect(self._switch_view)
        main_layout.addWidget(self._sidebar)

        content_pane = QWidget()
        content_layout = QVBoxLayout(content_pane)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self._top_bar = AtlasTopBar()
        content_layout.addWidget(self._top_bar)

        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f"background-color: {COLORS['bg_primary']};")
        content_layout.addWidget(self._stack, 1)

        main_layout.addWidget(content_pane, 1)

        self._overview = OverviewDashboard()
        self._machine = MachineView()
        self._processes = ProcessView()
        self._applications = ApplicationView()
        self._services = ServiceView()
        self._network = NetworkView()
        self._incidents = IncidentsView()
        self._changes = ChangesView()
        self._timeline = TimelineView()
        self._graph = GraphWidget()
        self._ai_chat = AIChatView()
        self._settings = SettingsView()

        self._views = {
            "overview": self._overview,
            "machine": self._machine,
            "processes": self._processes,
            "applications": self._applications,
            "services": self._services,
            "network": self._network,
            "incidents": self._incidents,
            "changes": self._changes,
            "timeline": self._timeline,
            "graph": self._graph,
            "ai": self._ai_chat,
            "settings": self._settings,
        }

        for name, view in self._views.items():
            self._stack.addWidget(view)

        self._overview.navigate_to_graph.connect(lambda: self.switch_view("graph"))
        self._overview.navigate_to_ai.connect(self._handle_ai_investigate)
        self._processes.investigate_process.connect(self._handle_ai_investigate)
        self._processes.open_in_graph.connect(lambda pid: self.switch_view("graph"))

        self._ai_chat.query_submitted.connect(self.query_submitted.emit)

        self._statusbar = QStatusBar()
        self._statusbar.setStyleSheet(f"""
            QStatusBar {{
                background-color: {COLORS['bg_surface']};
                color: {COLORS['text_muted']};
                border-top: 1px solid {COLORS['border']};
                padding: 3px 16px;
                font-size: 11px;
            }}
        """)
        self.setStatusBar(self._statusbar)

        self._status_entities = QLabel("Entities: 0")
        self._status_rels = QLabel("Relationships: 0")
        self._status_cpu = QLabel("CPU: 0%")
        self._status_ram = QLabel("RAM: 0%")
        self._status_ai = QLabel("AI: Offline")
        self._status_mode = QLabel("Mode: Normal")

        for w in [self._status_entities, self._status_rels, self._status_cpu,
                   self._status_ram, self._status_ai, self._status_mode]:
            w.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 11px; padding: 0 10px; font-family: 'Segoe UI Variable Text', 'Segoe UI', sans-serif;")
            self._statusbar.addPermanentWidget(w)

        self.switch_view("overview")

    def switch_view(self, view_name: str):
        self._sidebar.set_active(view_name)
        self._switch_view(view_name)

    def _switch_view(self, view_name: str):
        view = self._views.get(view_name)
        if view:
            self._stack.setCurrentWidget(view)
            meta = VIEW_METADATA.get(view_name, (view_name.title(), ""))
            self._top_bar.set_view_meta(meta[0], meta[1])

    def _handle_ai_investigate(self, query: str):
        self.switch_view("ai")
        if query:
            self._ai_chat.add_message(query, is_user=True)
            self._ai_chat.set_thinking(True)
            self.query_submitted.emit(query)

    @property
    def overview(self):
        return self._overview

    @property
    def process_view(self):
        return self._processes

    @property
    def application_view(self):
        return self._applications

    @property
    def service_view(self):
        return self._services

    @property
    def network_view(self):
        return self._network

    @property
    def incidents_view(self):
        return self._incidents

    @property
    def changes_view(self):
        return self._changes

    @property
    def timeline_view(self):
        return self._timeline

    @property
    def machine_view(self):
        return self._machine

    @property
    def graph_view(self):
        return self._graph

    @property
    def ai_chat(self):
        return self._ai_chat

    @property
    def settings_view(self):
        return self._settings

    def update_status_bar(self, entities=0, rels=0, cpu=0, ram=0,
                          ai_connected=False, mode="normal"):
        self._status_entities.setText(f"Entities: {entities:,}")
        self._status_rels.setText(f"Relationships: {rels:,}")
        self._status_cpu.setText(f"CPU: {cpu:.0f}%")
        self._status_ram.setText(f"RAM: {ram:.0f}%")
        self._status_ai.setText(f"AI: {'Online' if ai_connected else 'Offline'}")
        self._status_mode.setText(f"Mode: {mode.title()}")

        self._top_bar.update_status(ai_connected, monitoring=True)
        self._ai_chat.set_ai_status(ai_connected)
        self._sidebar.set_footer_status(
            version="v0.2.0",
            ai_status="Online" if ai_connected else "Offline",
            ollama_status="Online" if ai_connected else "Offline",
            monitoring="Active"
        )
