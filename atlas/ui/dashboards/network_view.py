from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QScrollArea,
    QFrame, QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from atlas.ui.themes.dark_theme import COLORS
from atlas.ui.widgets.metric_charts import MetricChart
from atlas.ui.widgets.components import AtlasCard, AtlasBadge, AtlasEmptyState, AtlasSearchBox


class NetworkView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._raw_connections = []
        self._active_filter = "ALL"
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

        header_row = QHBoxLayout()
        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        title = QLabel("Network Observability")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {COLORS['text_primary']};")
        title_vbox.addWidget(title)
        sub = QLabel("Interface throughput, adapter states, and active TCP/UDP socket telemetry")
        sub.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 12px;")
        title_vbox.addWidget(sub)
        header_row.addLayout(title_vbox)
        header_row.addStretch()
        layout.addLayout(header_row)

        charts_row = QHBoxLayout()
        charts_row.setSpacing(16)
        self._sent_chart = MetricChart("Interface Upload Rate", COLORS["chart_network"], unit=" KB/s")
        self._sent_chart.set_range(0, 500)
        self._recv_chart = MetricChart("Interface Download Rate", COLORS["accent_cyan"], unit=" KB/s")
        self._recv_chart.set_range(0, 1000)
        charts_row.addWidget(self._sent_chart)
        charts_row.addWidget(self._recv_chart)
        layout.addLayout(charts_row)

        self._adapters_card = AtlasCard("Network Adapters", "Physical and virtual network interfaces")
        self._adapters_layout = QVBoxLayout()
        self._adapters_layout.setSpacing(8)
        self._adapters_container = QWidget()
        self._adapters_container.setLayout(self._adapters_layout)
        self._adapters_card.add_widget(self._adapters_container)
        layout.addWidget(self._adapters_card)

        self._conn_card = AtlasCard("Active Sockets & Connections", "Current socket table bound to host PIDs")
        filter_row = QHBoxLayout()
        filter_row.setSpacing(6)
        for f_name in ["ALL", "TCP", "UDP", "ESTABLISHED", "LISTENING"]:
            btn = QPushButton(f_name)
            btn.setFixedHeight(24)
            btn.setCursor(Qt.PointingHandCursor)
            if f_name == "ALL":
                btn.setStyleSheet(f"background-color: {COLORS['bg_surface_raised']}; color: {COLORS['accent_blue']}; border: 1px solid {COLORS['accent_blue']}; border-radius: 4px; padding: 0 10px; font-size: 11px; font-weight: 600;")
            else:
                btn.setStyleSheet(f"background-color: transparent; color: {COLORS['text_secondary']}; border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 0 10px; font-size: 11px;")
            btn.clicked.connect(lambda checked, n=f_name: self._set_filter(n))
            filter_row.addWidget(btn)
        self._conn_card.add_header_widget(filter_row)

        self._conn_table = QTableWidget()
        self._conn_table.setColumnCount(6)
        self._conn_table.setHorizontalHeaderLabels([
            "PROCESS", "PROTOCOL", "LOCAL ENDPOINT", "REMOTE ENDPOINT", "STATUS", "PID"
        ])
        self._conn_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._conn_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._conn_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self._conn_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self._conn_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._conn_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self._conn_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._conn_table.verticalHeader().setVisible(False)
        self._conn_table.setShowGrid(False)
        self._conn_table.setMinimumHeight(280)
        self._conn_card.add_widget(self._conn_table)
        layout.addWidget(self._conn_card)

        scroll.setWidget(content)
        root_layout.addWidget(scroll)

    def _set_filter(self, filter_name: str):
        self._active_filter = filter_name
        self.update_connections(self._raw_connections)

    def update_throughput(self, sent_kbps: float, recv_kbps: float):
        self._sent_chart.add_value(sent_kbps)
        self._recv_chart.add_value(recv_kbps)

    def update_adapters(self, adapters: list):
        while self._adapters_layout.count():
            it = self._adapters_layout.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

        if not adapters:
            empty = AtlasEmptyState("No adapters detected", "Scanning network interface controllers...")
            self._adapters_layout.addWidget(empty)
            return

        for a in adapters:
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
            r_layout.setContentsMargins(8, 4, 8, 4)
            r_layout.setSpacing(12)

            is_up = a.get("is_up", False)
            badge = AtlasBadge("UP" if is_up else "DOWN", variant="success" if is_up else "neutral")
            r_layout.addWidget(badge)

            name_lbl = QLabel(a.get("name", "Interface"))
            name_lbl.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 13px; font-weight: 600;")
            r_layout.addWidget(name_lbl, stretch=2)

            ips = ", ".join(a.get("ipv4_addresses", [])) or "No IP assigned"
            ip_lbl = QLabel(ips)
            ip_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; font-family: monospace;")
            r_layout.addWidget(ip_lbl, stretch=2)

            spd = a.get("speed_mbps", 0)
            spd_lbl = QLabel(f"{spd:,} Mbps" if spd > 0 else "Virtual Link")
            spd_lbl.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 11px;")
            r_layout.addWidget(spd_lbl)

            self._adapters_layout.addWidget(row)

    def update_connections(self, connections: list):
        self._raw_connections = connections or []
        filtered = []
        for c in self._raw_connections:
            proto = c.get("protocol", "").upper()
            status = c.get("status", "").upper()
            if self._active_filter == "ALL":
                filtered.append(c)
            elif self._active_filter in ("TCP", "UDP") and proto == self._active_filter:
                filtered.append(c)
            elif self._active_filter in ("ESTABLISHED", "LISTENING") and self._active_filter in status:
                filtered.append(c)

        self._conn_table.setRowCount(len(filtered))
        for i, conn in enumerate(filtered):
            self._conn_table.setItem(i, 0, QTableWidgetItem(conn.get("process_name", "Unknown")))
            self._conn_table.setItem(i, 1, QTableWidgetItem(conn.get("protocol", "").upper()))
            self._conn_table.setItem(i, 2, QTableWidgetItem(f"{conn.get('local_address', '')}:{conn.get('local_port', '')}"))
            self._conn_table.setItem(i, 3, QTableWidgetItem(f"{conn.get('remote_address', '')}:{conn.get('remote_port', '')}"))
            self._conn_table.setItem(i, 4, QTableWidgetItem(conn.get("status", "")))
            pid_item = QTableWidgetItem()
            pid_item.setData(Qt.DisplayRole, conn.get("pid", 0))
            self._conn_table.setItem(i, 5, pid_item)


class IncidentsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(20)

        header_row = QHBoxLayout()
        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        title = QLabel("Incidents & Anomalies")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {COLORS['text_primary']};")
        title_vbox.addWidget(title)
        sub = QLabel("Correlated system failures, memory leak trajectories, and anomaly clusters")
        sub.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 12px;")
        title_vbox.addWidget(sub)
        header_row.addLayout(title_vbox)
        header_row.addStretch()
        layout.addLayout(header_row)

        stats_cards = QHBoxLayout()
        stats_cards.setSpacing(16)
        self._active_count_lbl = QLabel("0")
        self._active_count_lbl.setStyleSheet(f"font-size: 28px; font-weight: 700; color: {COLORS['danger']};")
        self._recent_count_lbl = QLabel("0")
        self._recent_count_lbl.setStyleSheet(f"font-size: 28px; font-weight: 700; color: {COLORS['warning']};")
        self._resolved_count_lbl = QLabel("0")
        self._resolved_count_lbl.setStyleSheet(f"font-size: 28px; font-weight: 700; color: {COLORS['success']};")

        for val_lbl, title_text, col in [
            (self._active_count_lbl, "ACTIVE INCIDENTS", COLORS["danger"]),
            (self._recent_count_lbl, "TOTAL FLAGGED", COLORS["warning"]),
            (self._resolved_count_lbl, "RESOLVED", COLORS["success"]),
        ]:
            c = AtlasCard(title_text)
            c.add_widget(val_lbl)
            stats_cards.addWidget(c)
        layout.addLayout(stats_cards)

        self._incidents_card = AtlasCard("Incident Stream", "Chronological incident log")
        self._incidents_layout = QVBoxLayout()
        self._incidents_layout.setSpacing(8)
        self._incidents_container = QWidget()
        self._incidents_container.setLayout(self._incidents_layout)
        self._incidents_card.add_widget(self._incidents_container)
        layout.addWidget(self._incidents_card)
        layout.addStretch()

    def update_incidents(self, active: list, recent: list):
        act = active or []
        rec = recent or []

        self._active_count_lbl.setText(str(len(act)))
        self._recent_count_lbl.setText(str(len(rec)))
        resolved_count = len([r for r in rec if r.get("status") == "resolved"])
        self._resolved_count_lbl.setText(str(resolved_count))

        while self._incidents_layout.count():
            it = self._incidents_layout.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

        if not act and not rec:
            empty = AtlasEmptyState(
                "No Incidents Recorded",
                "ATLAS has not detected any crash events, handle exhaustion, or uncontained baseline deviations."
            )
            self._incidents_layout.addWidget(empty)
            return

        for inc in act:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['bg_surface_raised']};
                    border: 1px solid {COLORS['danger']};
                    border-radius: 5px;
                    padding: 10px 14px;
                }}
            """)
            c_layout = QVBoxLayout(card)
            c_layout.setSpacing(4)

            top = QHBoxLayout()
            sev = inc.get("severity", "medium").upper()
            badge = AtlasBadge(sev, variant="danger")
            top.addWidget(badge)

            title = QLabel(inc.get("name", "Unknown Incident"))
            title.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 13px; font-weight: 600;")
            top.addWidget(title)
            top.addStretch()

            ts = inc.get("started_at", "")
            time_lbl = QLabel(ts[11:19] if len(ts) > 19 else ts)
            time_lbl.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 11px;")
            top.addWidget(time_lbl)
            c_layout.addLayout(top)

            desc = QLabel(inc.get("description", ""))
            desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
            c_layout.addWidget(desc)
            self._incidents_layout.addWidget(card)

        for inc in rec[:8]:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['bg_surface_raised']};
                    border: 1px solid {COLORS['border_subtle']};
                    border-radius: 5px;
                    padding: 8px 12px;
                }}
            """)
            c_layout = QHBoxLayout(card)
            c_layout.setSpacing(10)

            st = inc.get("status", "resolved")
            badge = AtlasBadge(st.upper(), variant="success" if st == "resolved" else "warning")
            c_layout.addWidget(badge)

            name = QLabel(inc.get("name", "Incident"))
            name.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 12px;")
            c_layout.addWidget(name, stretch=1)

            self._incidents_layout.addWidget(card)


class ChangesView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(20)

        header_row = QHBoxLayout()
        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        title = QLabel("System Changes & State Drift")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {COLORS['text_primary']};")
        title_vbox.addWidget(title)
        sub = QLabel("Differential comparison of machine state over time")
        sub.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 12px;")
        title_vbox.addWidget(sub)
        header_row.addLayout(title_vbox)
        header_row.addStretch()
        layout.addLayout(header_row)

        self._card = AtlasCard("State Drift Feed", "Captured mutations between snapshots")
        self._feed_layout = QVBoxLayout()
        self._feed_layout.setSpacing(8)

        sample_changes = [
            ("Application Registered", "Google Chrome 128.0.6613.120 installed", "2 hours ago", "info"),
            ("Service Start-Type Drift", "DiagTrack service modified: Automatic -> Manual", "6 hours ago", "warning"),
            ("Baseline Recalibration", "CPU baseline updated for peak daytime work profile", "Yesterday", "success"),
            ("Hardware Reconciliation", "Primary partition free space delta: -1.2 GB", "Yesterday", "info"),
        ]
        for c_type, c_desc, c_time, c_var in sample_changes:
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
            r_layout.setSpacing(12)

            badge = AtlasBadge(c_type, variant=c_var)
            r_layout.addWidget(badge)

            desc = QLabel(c_desc)
            desc.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 12px;")
            r_layout.addWidget(desc, stretch=1)

            t_lbl = QLabel(c_time)
            t_lbl.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 11px;")
            r_layout.addWidget(t_lbl)

            self._feed_layout.addWidget(row)

        feed_widget = QWidget()
        feed_widget.setLayout(self._feed_layout)
        self._card.add_widget(feed_widget)
        layout.addWidget(self._card)
        layout.addStretch()

    def update_changes(self, changes: list):
        while self._feed_layout.count():
            item = self._feed_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not changes:
            empty = QLabel("No system state drift or mutations detected.")
            empty.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; padding: 12px;")
            self._feed_layout.addWidget(empty)
            return

        for c in changes:
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
            r_layout.setSpacing(12)

            c_type = c.get("type", "Change")
            c_desc = str(c.get("details", c.get("description", c_type)))
            c_time = c.get("timestamp", "")
            c_var = "warning" if "error" in c_type.lower() or "alert" in c_type.lower() else "info"

            badge = AtlasBadge(c_type.replace("_", " ").title(), variant=c_var)
            r_layout.addWidget(badge)

            desc = QLabel(c_desc)
            desc.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 12px;")
            r_layout.addWidget(desc, stretch=1)

            if c_time:
                t_lbl = QLabel(str(c_time))
                t_lbl.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 11px;")
                r_layout.addWidget(t_lbl)

            self._feed_layout.addWidget(row)
