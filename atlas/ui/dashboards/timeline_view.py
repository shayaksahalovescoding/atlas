from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QListWidget, QListWidgetItem, QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from atlas.ui.themes.dark_theme import COLORS
from atlas.ui.widgets.components import AtlasCard, AtlasBadge, AtlasProgressBar, AtlasEmptyState


class TimelineView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(16)

        header_row = QHBoxLayout()
        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        title = QLabel("System Event Timeline")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {COLORS['text_primary']};")
        title_vbox.addWidget(title)
        sub = QLabel("Chronological log of system events, process state mutations, and telemetry triggers")
        sub.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 12px;")
        title_vbox.addWidget(sub)
        header_row.addLayout(title_vbox)
        header_row.addStretch()
        layout.addLayout(header_row)

        card = AtlasCard("Event Stream")
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(0, 0, 0, 0)
        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SingleSelection)
        card_layout.addWidget(self._list)
        card.add_layout(card_layout)
        layout.addWidget(card)

    def update_events(self, events: list):
        self._list.clear()
        if not events:
            return

        for ev in reversed(events[-100:]):
            evt_type = ev.get("event_type", "event")
            ts = ev.get("timestamp", "")
            time_str = ts[11:19] if len(ts) > 19 else ts
            meta = ev.get("metadata", {})

            detail = ""
            if "application" in meta:
                detail = meta["application"]
            elif "name" in meta:
                detail = meta["name"]
            elif "description" in meta:
                detail = meta["description"][:80]
            elif "pid" in meta:
                detail = f"PID {meta['pid']}"

            title = evt_type.replace("_", " ").title()
            text = f"  {time_str}   {title}"
            if detail:
                text += f"  ·  {detail}"

            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, ev)

            if "anomaly" in evt_type or "crash" in evt_type or "incident" in evt_type:
                item.setForeground(QColor(COLORS["danger"]))
            elif "error" in evt_type:
                item.setForeground(QColor(COLORS["warning"]))
            elif "resolved" in evt_type:
                item.setForeground(QColor(COLORS["success"]))
            else:
                item.setForeground(QColor(COLORS["text_secondary"]))

            self._list.addItem(item)


class MachineView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
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
        title = QLabel("Hardware & Operating System")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {COLORS['text_primary']};")
        title_vbox.addWidget(title)
        sub = QLabel("Physical hardware topology, kernel descriptors, and subsystem identity")
        sub.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 12px;")
        title_vbox.addWidget(sub)
        header_row.addLayout(title_vbox)
        header_row.addStretch()
        layout.addLayout(header_row)

        self._sys_card = AtlasCard("System Identity")
        sys_grid = QHBoxLayout()
        sys_grid.setSpacing(20)
        self._sys_fields = {}
        for f in ["Hostname", "OS", "Build", "Architecture", "User", "Uptime"]:
            col = QVBoxLayout()
            col.setSpacing(2)
            lbl = QLabel(f.upper())
            lbl.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 10px; font-weight: 700;")
            val = QLabel("--")
            val.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 13px; font-weight: 600;")
            col.addWidget(lbl)
            col.addWidget(val)
            sys_grid.addLayout(col)
            self._sys_fields[f] = val
        self._sys_card.add_layout(sys_grid)
        layout.addWidget(self._sys_card)

        hw_split = QHBoxLayout()
        hw_split.setSpacing(16)

        self._cpu_card = AtlasCard("Processor")
        self._cpu_labels = {}
        cpu_layout = QVBoxLayout()
        cpu_layout.setSpacing(6)
        for k in ["Model", "Vendor", "Cores", "Frequency", "L2/L3 Cache", "Current Load"]:
            r = QHBoxLayout()
            l1 = QLabel(k)
            l1.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
            l2 = QLabel("--")
            l2.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 11px; font-weight: 600;")
            l2.setAlignment(Qt.AlignRight)
            r.addWidget(l1)
            r.addWidget(l2)
            cpu_layout.addLayout(r)
            self._cpu_labels[k] = l2
        self._cpu_card.add_layout(cpu_layout)
        hw_split.addWidget(self._cpu_card)

        self._mem_card = AtlasCard("Memory Subsystem")
        mem_layout = QVBoxLayout()
        mem_layout.setSpacing(6)
        self._mem_labels = {}
        for k in ["Total Physical", "Allocated", "Available", "Swap Allocation", "Clock Speed", "DIMM Slots"]:
            r = QHBoxLayout()
            l1 = QLabel(k)
            l1.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
            l2 = QLabel("--")
            l2.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 11px; font-weight: 600;")
            l2.setAlignment(Qt.AlignRight)
            r.addWidget(l1)
            r.addWidget(l2)
            mem_layout.addLayout(r)
            self._mem_labels[k] = l2
        self._mem_card.add_layout(mem_layout)
        hw_split.addWidget(self._mem_card)

        self._gpu_card = AtlasCard("Graphics Processing Unit")
        gpu_layout = QVBoxLayout()
        gpu_layout.setSpacing(6)
        self._gpu_labels = {}
        for k in ["Model", "Vendor", "Driver Version", "Video Memory"]:
            r = QHBoxLayout()
            l1 = QLabel(k)
            l1.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
            l2 = QLabel("--")
            l2.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 11px; font-weight: 600;")
            l2.setAlignment(Qt.AlignRight)
            r.addWidget(l1)
            r.addWidget(l2)
            gpu_layout.addLayout(r)
            self._gpu_labels[k] = l2
        self._gpu_card.add_layout(gpu_layout)
        hw_split.addWidget(self._gpu_card)

        layout.addLayout(hw_split)

        self._storage_card = AtlasCard("Storage Volumes & Partitions")
        self._storage_layout = QVBoxLayout()
        self._storage_layout.setSpacing(8)
        self._storage_container = QWidget()
        self._storage_container.setLayout(self._storage_layout)
        self._storage_card.add_widget(self._storage_container)
        layout.addWidget(self._storage_card)

        scroll.setWidget(content)
        root_layout.addWidget(scroll)

    def update_machine(self, graph):
        machines = graph.get_entities_by_type("machine")
        if machines:
            p = machines[0].properties
            self._sys_fields["Hostname"].setText(str(p.get("hostname", "N/A")))
            self._sys_fields["OS"].setText(f"Windows {p.get('os_version', 'N/A')}")
            self._sys_fields["Build"].setText(str(p.get("os_build", "N/A")))
            self._sys_fields["Architecture"].setText(str(p.get("architecture", "N/A")))
            self._sys_fields["User"].setText(str(p.get("username", "N/A")))
            secs = p.get("uptime_seconds", 0)
            self._sys_fields["Uptime"].setText(f"{secs // 3600}h {(secs % 3600) // 60}m")

        cpus = graph.get_entities_by_type("cpu")
        if cpus:
            c = cpus[0].properties
            self._cpu_labels["Model"].setText(str(c.get("brand", "N/A")))
            self._cpu_labels["Vendor"].setText(str(c.get("vendor", "N/A")))
            self._cpu_labels["Cores"].setText(f"{c.get('cores_physical', 0)} P / {c.get('cores_logical', 0)} L")
            self._cpu_labels["Frequency"].setText(f"{c.get('current_frequency_mhz', 0)} MHz")
            self._cpu_labels["L2/L3 Cache"].setText(f"{c.get('cache_l2_kb', 0)} KB / {c.get('cache_l3_kb', 0)} KB")
            self._cpu_labels["Current Load"].setText(f"{c.get('usage_percent', 0):.0f}%")

        mems = graph.get_entities_by_type("memory")
        if mems:
            m = mems[0].properties
            total_gb = m.get("total_bytes", 0) / (1024**3)
            used_gb = m.get("used_bytes", 0) / (1024**3)
            avail_gb = m.get("available_bytes", 0) / (1024**3)
            self._mem_labels["Total Physical"].setText(f"{total_gb:.1f} GB")
            self._mem_labels["Allocated"].setText(f"{used_gb:.1f} GB ({m.get('usage_percent', 0):.0f}%)")
            self._mem_labels["Available"].setText(f"{avail_gb:.1f} GB")
            swap_gb = m.get("swap_total_bytes", 0) / (1024**3)
            self._mem_labels["Swap Allocation"].setText(f"{swap_gb:.1f} GB ({m.get('swap_percent', 0):.0f}%)")
            self._mem_labels["Clock Speed"].setText(f"{m.get('speed_mhz', 0)} MHz")
            self._mem_labels["DIMM Slots"].setText(str(m.get("slots_used", "N/A")))

        gpus = graph.get_entities_by_type("gpu")
        if gpus:
            g = gpus[0]
            p = g.properties
            self._gpu_labels["Model"].setText(g.name[:25])
            self._gpu_labels["Vendor"].setText(str(p.get("vendor", "N/A")))
            self._gpu_labels["Driver Version"].setText(str(p.get("driver_version", "N/A")))
            self._gpu_labels["Video Memory"].setText(f"{p.get('memory_total_mb', 0):,} MB")

        partitions = graph.get_entities_by_type("partition")
        while self._storage_layout.count():
            it = self._storage_layout.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

        for p in partitions:
            props = p.properties
            total_gb = props.get("total_bytes", 0) / (1024**3)
            free_gb = props.get("free_bytes", 0) / (1024**3)
            used_pct = props.get("usage_percent", 0.0)

            row = QFrame()
            row.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['bg_surface_raised']};
                    border: 1px solid {COLORS['border_subtle']};
                    border-radius: 5px;
                    padding: 8px 14px;
                }}
            """)
            r_layout = QHBoxLayout(row)
            r_layout.setSpacing(16)

            badge = AtlasBadge(str(props.get("mount_point", "?")), variant="info")
            r_layout.addWidget(badge)

            info_lbl = QLabel(f"{total_gb:.0f} GB Total  ·  {free_gb:.0f} GB Free ({props.get('filesystem', 'NTFS')})")
            info_lbl.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 12px; font-weight: 500;")
            r_layout.addWidget(info_lbl, stretch=2)

            bar = AtlasProgressBar(value=used_pct, color=COLORS["chart_disk"])
            bar.setFixedWidth(160)
            r_layout.addWidget(bar)

            pct_lbl = QLabel(f"{used_pct:.0f}% used")
            pct_lbl.setFixedWidth(65)
            pct_lbl.setAlignment(Qt.AlignRight)
            pct_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; font-weight: 600;")
            r_layout.addWidget(pct_lbl)

            self._storage_layout.addWidget(row)


class SettingsView(QWidget):
    def __init__(self, settings=None, parent=None):
        super().__init__(parent)
        self._settings = settings
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
        title = QLabel("System Configuration")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {COLORS['text_primary']};")
        title_vbox.addWidget(title)
        sub = QLabel("Engine parameters, sampling profiles, AI providers, and privacy controls")
        sub.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 12px;")
        title_vbox.addWidget(sub)
        header_row.addLayout(title_vbox)
        header_row.addStretch()
        layout.addLayout(header_row)

        for cat_title, items in [
            ("MONITORING PROFILE & TELEMETRY", [
                ("Monitoring Mode", "Continuous Balanced (10s metrics, 60s services, 120s apps)"),
                ("Process Tree Resolution", "Full tree tracking with handle and thread attribution"),
                ("Windows Event Collector", "Active (System, Application, and Crash Channels)"),
            ]),
            ("LOCAL REASONING & AI (OLLAMA)", [
                ("Inference Provider", "Local Ollama HTTP endpoint (http://localhost:11434)"),
                ("Default Reasoning Model", "qwen2.5:7b (air-gapped local execution)"),
                ("Inference Timeout", "120 seconds with automatic retry backoff"),
            ]),
            ("PRIVACY & DATA REDACTION", [
                ("Secret & Token Redaction", "Enabled (automatic scrubbing of passwords, keys, and tokens)"),
                ("Audit Logging", "Active (immutable SQLite audit trail of all inspection calls)"),
                ("External Cloud Telemetry", "Disabled (100% air-gapped local-first policy)"),
            ]),
            ("STORAGE & RETENTION POLICY", [
                ("Persistence Engine", "SQLite (WAL mode enabled, PRAGMA synchronous = NORMAL)"),
                ("Data Directory", "atlas_data/atlas.db"),
                ("Metric History Retention", "14 days rolling window"),
                ("Snapshot Retention", "90 days differential historical snapshots"),
            ]),
        ]:
            card = AtlasCard(cat_title)
            card_layout = QVBoxLayout()
            card_layout.setSpacing(8)
            for name, val in items:
                row = QFrame()
                row.setStyleSheet(f"background-color: {COLORS['bg_surface_raised']}; border-radius: 5px; padding: 8px 12px;")
                r_l = QHBoxLayout(row)
                l1 = QLabel(name)
                l1.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 12px; font-weight: 600;")
                l2 = QLabel(val)
                l2.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
                r_l.addWidget(l1)
                r_l.addStretch()
                r_l.addWidget(l2)
                card_layout.addWidget(row)
            card.add_layout(card_layout)
            layout.addWidget(card)

        scroll.setWidget(content)
        root_layout.addWidget(scroll)

    def update_health(self, collector_health, ai_stats, metrics_stats):
        pass
