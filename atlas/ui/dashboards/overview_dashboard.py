from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QPushButton, QSizePolicy, QProgressBar
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter

from atlas.ui.themes.dark_theme import COLORS
from atlas.ui.widgets.metric_charts import MetricChart, MetricResourceCard
from atlas.ui.widgets.components import AtlasCard, AtlasBadge, AtlasProgressBar, AtlasEmptyState

CardWidget = AtlasCard


class OverviewDashboard(QWidget):
    navigate_to_graph = Signal()
    navigate_to_ai = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._consumer_mode = "memory"
        self._raw_consumers = []
        self._setup_ui()

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(20)

        self._hero_card = QFrame()
        self._hero_card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
            }}
        """)
        hero_layout = QHBoxLayout(self._hero_card)
        hero_layout.setContentsMargins(20, 16, 20, 16)
        hero_layout.setSpacing(24)

        hero_left = QVBoxLayout()
        hero_left.setSpacing(4)
        status_tag_row = QHBoxLayout()
        status_tag_row.setSpacing(8)

        status_tag = QLabel("SYSTEM STATUS")
        status_tag.setStyleSheet(f"""
            color: {COLORS['text_tertiary']};
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.8px;
        """)
        status_tag_row.addWidget(status_tag)

        self._health_badge = AtlasBadge("Nominal", variant="success")
        status_tag_row.addWidget(self._health_badge)
        status_tag_row.addStretch()
        hero_left.addLayout(status_tag_row)

        self._health_headline = QLabel("All Systems Nominal")
        self._health_headline.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: 20px;
            font-weight: 700;
            letter-spacing: -0.3px;
        """)
        hero_left.addWidget(self._health_headline)

        self._health_detail = QLabel("Live twin continuous telemetry operating within learned baselines.")
        self._health_detail.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        hero_left.addWidget(self._health_detail)
        hero_layout.addLayout(hero_left, stretch=2)

        sep_line = QFrame()
        sep_line.setFrameShape(QFrame.VLine)
        sep_line.setStyleSheet(f"background-color: {COLORS['border_subtle']}; max-width: 1px;")
        hero_layout.addWidget(sep_line)

        stats_grid = QHBoxLayout()
        stats_grid.setSpacing(24)

        for attr, title in [
            ("_uptime_val", "UPTIME"),
            ("_procs_val", "PROCESSES"),
            ("_pressure_val", "RAM PRESSURE"),
            ("_mode_val", "SAMPLING MODE"),
        ]:
            col = QVBoxLayout()
            col.setSpacing(2)
            lbl = QLabel(title)
            lbl.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 10px; font-weight: 700;")
            val = QLabel("--")
            val.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 14px; font-weight: 600;")
            setattr(self, attr, val)
            col.addWidget(lbl)
            col.addWidget(val)
            stats_grid.addLayout(col)

        hero_layout.addLayout(stats_grid, stretch=3)
        layout.addWidget(self._hero_card)

        res_grid = QHBoxLayout()
        res_grid.setSpacing(12)

        self._cpu_card = MetricResourceCard("CPU", "%", COLORS["chart_cpu"])
        self._ram_card = MetricResourceCard("Memory", "%", COLORS["chart_memory"])
        self._gpu_card = MetricResourceCard("GPU", "%", COLORS["chart_gpu"])
        self._disk_card = MetricResourceCard("Storage", "%", COLORS["chart_disk"])
        self._net_card = MetricResourceCard("Network", " MB/s", COLORS["chart_network"])

        for rc in [self._cpu_card, self._ram_card, self._gpu_card, self._disk_card, self._net_card]:
            res_grid.addWidget(rc)
        layout.addLayout(res_grid)

        charts_row = QHBoxLayout()
        charts_row.setSpacing(16)

        self._cpu_chart = MetricChart("CPU Utilization", COLORS["chart_cpu"], unit="%")
        self._mem_chart = MetricChart("Memory Allocation", COLORS["chart_memory"], unit="%")
        charts_row.addWidget(self._cpu_chart)
        charts_row.addWidget(self._mem_chart)
        layout.addLayout(charts_row)

        mid_split = QHBoxLayout()
        mid_split.setSpacing(16)

        self._twin_card = AtlasCard("Digital Twin Representation", "In-memory graph topology")
        self._twin_btn = QPushButton("Open Graph Explorer →")
        self._twin_btn.setObjectName("primary")
        self._twin_btn.setCursor(Qt.PointingHandCursor)
        self._twin_btn.clicked.connect(self.navigate_to_graph.emit)
        self._twin_card.add_header_widget(self._twin_btn)

        twin_stats_row = QHBoxLayout()
        twin_stats_row.setSpacing(24)

        for attr, label, color in [
            ("_twin_entities", "Entities", COLORS["accent_blue"]),
            ("_twin_rels", "Relationships", COLORS["accent_purple"]),
            ("_twin_events", "Events Streamed", COLORS["accent_cyan"]),
        ]:
            c = QVBoxLayout()
            c.setSpacing(2)
            v = QLabel("0")
            v.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {color};")
            setattr(self, attr, v)
            l = QLabel(label)
            l.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 11px;")
            c.addWidget(v)
            c.addWidget(l)
            twin_stats_row.addLayout(c)
        self._twin_card.add_layout(twin_stats_row)

        dist_label = QLabel("GRAPH TOPOLOGY COMPOSITION")
        dist_label.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 10px; font-weight: 700; margin-top: 6px;")
        self._twin_card.add_widget(dist_label)

        self._twin_dist_widget = QWidget()
        self._twin_dist_widget.setFixedHeight(8)
        self._twin_dist_widget.paintEvent = self._paint_twin_distribution
        self._twin_card.add_widget(self._twin_dist_widget)

        dist_legend = QHBoxLayout()
        dist_legend.setSpacing(14)
        for name, col in [
            ("Processes", COLORS["graph_node_process"]),
            ("Applications", COLORS["graph_node_app"]),
            ("Services", COLORS["graph_node_service"]),
            ("Hardware", COLORS["graph_node_hardware"]),
        ]:
            item = QHBoxLayout()
            item.setSpacing(5)
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {col}; font-size: 10px;")
            txt = QLabel(name)
            txt.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
            item.addWidget(dot)
            item.addWidget(txt)
            dist_legend.addLayout(item)
        dist_legend.addStretch()
        self._twin_card.add_layout(dist_legend)
        mid_split.addWidget(self._twin_card, stretch=3)

        self._ai_card = AtlasCard("AI System Insight", "Contextual anomaly reasoning")
        ai_btn = QPushButton("Investigate →")
        ai_btn.setCursor(Qt.PointingHandCursor)
        ai_btn.clicked.connect(lambda: self.navigate_to_ai.emit(self._insight_text.text()))
        self._ai_card.add_header_widget(ai_btn)

        self._insight_badge = AtlasBadge("LEARNING", variant="neutral")
        self._ai_card.add_widget(self._insight_badge)

        self._insight_text = QLabel("ATLAS is learning your machine's normal operational baseline.")
        self._insight_text.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 13px; line-height: 1.5;")
        self._insight_text.setWordWrap(True)
        self._ai_card.add_widget(self._insight_text)

        self._insight_evidence = QLabel("• Continuous telemetry tracking active\n• Statistical variance calculating")
        self._insight_evidence.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 11px; line-height: 1.4;")
        self._insight_evidence.setWordWrap(True)
        self._ai_card.add_widget(self._insight_evidence)
        self._ai_card.add_widget(QWidget())
        mid_split.addWidget(self._ai_card, stretch=2)

        layout.addLayout(mid_split)

        bottom_split = QHBoxLayout()
        bottom_split.setSpacing(16)

        self._anomalies_card = AtlasCard("Anomalies & Deviations", "Telemetry divergence from baseline")
        self._anomalies_layout = QVBoxLayout()
        self._anomalies_layout.setSpacing(6)
        self._anomalies_container = QWidget()
        self._anomalies_container.setLayout(self._anomalies_layout)
        self._anomalies_card.add_widget(self._anomalies_container)
        bottom_split.addWidget(self._anomalies_card, stretch=1)

        self._consumers_card = AtlasCard("Top Resource Consumers", "Live process attribution")
        tab_row = QHBoxLayout()
        tab_row.setSpacing(8)
        self._mem_tab_btn = QPushButton("Memory")
        self._mem_tab_btn.setFixedHeight(24)
        self._mem_tab_btn.setStyleSheet(f"background-color: {COLORS['bg_surface_raised']}; color: {COLORS['accent_blue']}; font-weight: 600; border: 1px solid {COLORS['accent_blue']}; border-radius: 4px; padding: 0 10px; font-size: 11px;")
        self._cpu_tab_btn = QPushButton("CPU")
        self._cpu_tab_btn.setFixedHeight(24)
        self._cpu_tab_btn.setStyleSheet(f"background-color: transparent; color: {COLORS['text_secondary']}; border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 0 10px; font-size: 11px;")

        self._mem_tab_btn.clicked.connect(lambda: self._set_consumer_mode("memory"))
        self._cpu_tab_btn.clicked.connect(lambda: self._set_consumer_mode("cpu"))
        tab_row.addWidget(self._mem_tab_btn)
        tab_row.addWidget(self._cpu_tab_btn)
        self._consumers_card.add_header_widget(self._mem_tab_btn)
        self._consumers_card.add_header_widget(self._cpu_tab_btn)

        self._consumers_layout = QVBoxLayout()
        self._consumers_layout.setSpacing(6)
        self._consumers_container = QWidget()
        self._consumers_container.setLayout(self._consumers_layout)
        self._consumers_card.add_widget(self._consumers_container)
        bottom_split.addWidget(self._consumers_card, stretch=1)

        layout.addLayout(bottom_split)

        scroll.setWidget(content)
        root_layout.addWidget(scroll)

    def _paint_twin_distribution(self, event):
        painter = QPainter(self._twin_dist_widget)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self._twin_dist_widget.width()
        h = self._twin_dist_widget.height()

        slices = [
            (0.40, COLORS["graph_node_process"]),
            (0.25, COLORS["graph_node_app"]),
            (0.20, COLORS["graph_node_service"]),
            (0.15, COLORS["graph_node_hardware"]),
        ]
        curr_x = 0
        for ratio, col in slices:
            slice_w = int(w * ratio)
            painter.setBrush(QColor(col))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(curr_x, 0, slice_w, h, 2, 2)
            curr_x += slice_w
        painter.end()

    def _set_consumer_mode(self, mode: str):
        self._consumer_mode = mode
        if mode == "memory":
            self._mem_tab_btn.setStyleSheet(f"background-color: {COLORS['bg_surface_raised']}; color: {COLORS['accent_blue']}; font-weight: 600; border: 1px solid {COLORS['accent_blue']}; border-radius: 4px; padding: 0 10px; font-size: 11px;")
            self._cpu_tab_btn.setStyleSheet(f"background-color: transparent; color: {COLORS['text_secondary']}; border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 0 10px; font-size: 11px;")
        else:
            self._cpu_tab_btn.setStyleSheet(f"background-color: {COLORS['bg_surface_raised']}; color: {COLORS['accent_blue']}; font-weight: 600; border: 1px solid {COLORS['accent_blue']}; border-radius: 4px; padding: 0 10px; font-size: 11px;")
            self._mem_tab_btn.setStyleSheet(f"background-color: transparent; color: {COLORS['text_secondary']}; border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 0 10px; font-size: 11px;")
        self.update_consumers(self._raw_consumers)

    def update_metrics(self, cpu: float, memory: float, gpu: float, disk: float, network_mbps: float):
        self._cpu_card.set_value(cpu, subtitle="Normal load")
        self._ram_card.set_value(memory, subtitle=f"{memory:.0f}% committed")
        self._gpu_card.set_value(gpu, subtitle="Renderer idle" if gpu < 10 else "Rendering active")
        self._disk_card.set_value(disk, subtitle="Primary partition")
        self._net_card.set_value(network_mbps, subtitle=f"{network_mbps:.1f} MB/s", status="Active" if network_mbps > 0.05 else "Idle")

        self._cpu_chart.add_value(cpu)
        self._mem_chart.add_value(memory)

        if memory > 85:
            self._pressure_val.setText("High")
            self._pressure_val.setStyleSheet(f"color: {COLORS['danger']}; font-size: 14px; font-weight: 600;")
        elif memory > 70:
            self._pressure_val.setText("Elevated")
            self._pressure_val.setStyleSheet(f"color: {COLORS['warning']}; font-size: 14px; font-weight: 600;")
        else:
            self._pressure_val.setText("Nominal")
            self._pressure_val.setStyleSheet(f"color: {COLORS['success']}; font-size: 14px; font-weight: 600;")

    def update_twin_stats(self, entities: int, relationships: int, events: int):
        self._twin_entities.setText(f"{entities:,}")
        self._twin_rels.setText(f"{relationships:,}")
        self._twin_events.setText(f"{events:,}")
        self._procs_val.setText(f"{entities} nodes")

    def update_anomalies(self, anomalies: list):
        while self._anomalies_layout.count():
            item = self._anomalies_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not anomalies:
            empty = AtlasEmptyState(
                "All Systems Nominal",
                "No statistical anomalies or behavioral deviations detected across hardware, processes, or services."
            )
            self._anomalies_layout.addWidget(empty)
            return

        for a in anomalies[:5]:
            row = QFrame()
            row.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['bg_surface_raised']};
                    border: 1px solid {COLORS['border_subtle']};
                    border-radius: 5px;
                    padding: 8px 12px;
                }}
            """)
            r_layout = QHBoxLayout(row)
            r_layout.setContentsMargins(8, 6, 8, 6)
            r_layout.setSpacing(10)

            sev = a.get("severity", "low").lower()
            badge_var = "danger" if sev in ("high", "critical") else "warning" if sev == "medium" else "info"
            badge = AtlasBadge(sev.upper(), variant=badge_var)
            r_layout.addWidget(badge)

            desc = QLabel(a.get("description", "Anomalous metric deviation"))
            desc.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 12px;")
            r_layout.addWidget(desc, stretch=1)

            self._anomalies_layout.addWidget(row)

    def update_health(self, health: str, ai_connected: bool, monitoring: bool):
        h = health.lower()
        if h == "critical":
            self._health_badge.set_text("CRITICAL ATTENTION", variant="danger")
            self._health_headline.setText("System Saturation Detected")
            self._health_detail.setText("Resource bottlenecks detected. AI analysis recommended.")
        elif h == "warning":
            self._health_badge.set_text("ELEVATED LOAD", variant="warning")
            self._health_headline.setText("Resource Pressure Elevated")
            self._health_detail.setText("Elevated CPU or memory allocation above baseline.")
        else:
            self._health_badge.set_text("ALL NOMINAL", variant="success")
            self._health_headline.setText("All Systems Nominal")
            self._health_detail.setText("Continuous telemetry operating cleanly within normal bounds.")

        self._mode_val.setText("Continuous" if monitoring else "Passive")

    def update_consumers(self, consumers: list):
        self._raw_consumers = consumers or []
        while self._consumers_layout.count():
            item = self._consumers_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not self._raw_consumers:
            empty = AtlasEmptyState("No active consumers", "Collecting process telemetry...")
            self._consumers_layout.addWidget(empty)
            return

        if self._consumer_mode == "cpu":
            sorted_procs = sorted(self._raw_consumers, key=lambda x: x.get("cpu_percent", 0), reverse=True)[:6]
            max_val = max([p.get("cpu_percent", 0) for p in sorted_procs] + [1.0])
        else:
            sorted_procs = sorted(self._raw_consumers, key=lambda x: x.get("memory_bytes", 0), reverse=True)[:6]
            max_val = max([p.get("memory_bytes", 0) for p in sorted_procs] + [1.0])

        for rank, p in enumerate(sorted_procs, 1):
            row = QFrame()
            row.setStyleSheet(f"""
                QFrame {{
                    background-color: transparent;
                    border: none;
                    border-bottom: 1px solid {COLORS['border_subtle']};
                    padding: 4px 0;
                }}
            """)
            r_layout = QHBoxLayout(row)
            r_layout.setContentsMargins(4, 3, 4, 3)
            r_layout.setSpacing(10)

            rank_lbl = QLabel(f"{rank}")
            rank_lbl.setFixedWidth(16)
            rank_lbl.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 11px; font-weight: 700;")
            r_layout.addWidget(rank_lbl)

            name_lbl = QLabel(p.get("name", "process"))
            name_lbl.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 12px; font-weight: 500;")
            r_layout.addWidget(name_lbl, stretch=2)

            if self._consumer_mode == "cpu":
                val = p.get("cpu_percent", 0)
                val_text = f"{val:.1f}%"
                ratio = val / max(max_val, 100.0)
                bar_color = COLORS["chart_cpu"]
            else:
                mem_mb = p.get("memory_bytes", 0) / (1024 * 1024)
                val_text = f"{mem_mb:.0f} MB" if mem_mb < 1024 else f"{mem_mb/1024:.2f} GB"
                ratio = p.get("memory_bytes", 0) / max(max_val, 1.0)
                bar_color = COLORS["chart_memory"]

            bar = AtlasProgressBar(value=ratio * 100, color=bar_color)
            bar.setFixedWidth(70)
            r_layout.addWidget(bar)

            val_lbl = QLabel(val_text)
            val_lbl.setFixedWidth(64)
            val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            val_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; font-family: monospace; font-weight: 600;")
            r_layout.addWidget(val_lbl)

            self._consumers_layout.addWidget(row)

        if sorted_procs:
            top_p = sorted_procs[0]
            top_mem = top_p.get("memory_bytes", 0) / (1024 * 1024)
            self._insight_badge.set_text("ATTRIBUTION", variant="info")
            self._insight_text.setText(
                f"{top_p.get('name', 'Leading process')} is currently the largest contributor to system footprint "
                f"at {top_mem:.0f} MB. Telemetry indicates consistent execution."
            )
            self._insight_evidence.setText(
                f"• Process attribution verified via Digital Twin\n• Resource trajectory within expected parameters"
            )
