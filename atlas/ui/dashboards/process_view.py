from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QLineEdit, QFrame, QAbstractItemView,
    QSplitter, QTreeWidget, QTreeWidgetItem, QScrollArea, QPushButton,
    QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont

from atlas.ui.themes.dark_theme import COLORS
from atlas.ui.widgets.metric_charts import MetricChart
from atlas.ui.widgets.components import AtlasCard, AtlasBadge, AtlasSearchBox, AtlasEmptyState, AtlasProgressBar


class ProcessView(QWidget):
    process_selected = Signal(str)
    investigate_process = Signal(str)
    open_in_graph = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_processes = []
        self._current_selected_id = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(16)

        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        title = QLabel("Process Explorer")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {COLORS['text_primary']};")
        title_vbox.addWidget(title)

        self._count_label = QLabel("Loading running processes...")
        self._count_label.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 12px;")
        title_vbox.addWidget(self._count_label)
        header_row.addLayout(title_vbox)

        header_row.addStretch()

        self._search = AtlasSearchBox("Filter by name, PID, or application...")
        self._search.setFixedWidth(280)
        self._search.text_changed.connect(self._filter_table)
        header_row.addWidget(self._search)

        layout.addLayout(header_row)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: transparent; width: 8px; }")

        table_card = AtlasCard()
        table_layout = QVBoxLayout()
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(0)

        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels([
            "PROCESS", "PID", "CPU", "MEMORY", "THREADS", "STATUS", "APPLICATION"
        ])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)

        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.currentCellChanged.connect(self._on_select)
        table_layout.addWidget(self._table)
        table_card.add_layout(table_layout)
        splitter.addWidget(table_card)

        self._detail_drawer = AtlasCard("Process Inspector")
        self._detail_drawer.setMinimumWidth(340)
        self._detail_drawer.setMaximumWidth(450)

        drawer_scroll = QScrollArea()
        drawer_scroll.setWidgetResizable(True)
        drawer_scroll.setFrameShape(QFrame.NoFrame)
        drawer_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self._drawer_content = QWidget()
        drawer_layout = QVBoxLayout(self._drawer_content)
        drawer_layout.setContentsMargins(0, 0, 0, 0)
        drawer_layout.setSpacing(14)

        self._empty_drawer = AtlasEmptyState(
            "Select a process",
            "Choose a process from the table to inspect telemetry, resource usage, hierarchy, and graph dependencies."
        )
        drawer_layout.addWidget(self._empty_drawer)

        self._inspector_panel = QWidget()
        insp_layout = QVBoxLayout(self._inspector_panel)
        insp_layout.setContentsMargins(0, 0, 0, 0)
        insp_layout.setSpacing(12)

        insp_header = QHBoxLayout()
        self._proc_title = QLabel("Process Details")
        self._proc_title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {COLORS['text_primary']};")
        insp_header.addWidget(self._proc_title)
        self._proc_badge = AtlasBadge("RUNNING", variant="success")
        insp_header.addWidget(self._proc_badge)
        insp_header.addStretch()
        insp_layout.addLayout(insp_header)

        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)
        self._ai_inv_btn = QPushButton("✦ Investigate with AI")
        self._ai_inv_btn.setObjectName("primary")
        self._ai_inv_btn.setCursor(Qt.PointingHandCursor)
        self._ai_inv_btn.clicked.connect(self._on_investigate_clicked)
        actions_row.addWidget(self._ai_inv_btn)

        self._graph_btn = QPushButton("Open in Graph")
        self._graph_btn.setCursor(Qt.PointingHandCursor)
        self._graph_btn.clicked.connect(self._on_graph_clicked)
        actions_row.addWidget(self._graph_btn)
        insp_layout.addLayout(actions_row)

        sec1 = QLabel("EXECUTION METRICS")
        sec1.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 10px; font-weight: 700; margin-top: 6px;")
        insp_layout.addWidget(sec1)

        self._metrics_box = QFrame()
        self._metrics_box.setStyleSheet(f"background-color: {COLORS['bg_surface_raised']}; border-radius: 5px; padding: 8px;")
        mb_layout = QVBoxLayout(self._metrics_box)
        mb_layout.setSpacing(6)
        self._metric_labels = {}
        for k in ["PID", "Parent PID", "User", "CPU Usage", "Memory Private", "Threads", "Handles", "I/O Read Rate", "I/O Write Rate"]:
            row = QHBoxLayout()
            l1 = QLabel(k)
            l1.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
            l2 = QLabel("--")
            l2.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 11px; font-weight: 600; font-family: monospace;")
            l2.setAlignment(Qt.AlignRight)
            row.addWidget(l1)
            row.addWidget(l2)
            mb_layout.addLayout(row)
            self._metric_labels[k] = l2
        insp_layout.addWidget(self._metrics_box)

        sec2 = QLabel("BINARY LOCATION")
        sec2.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 10px; font-weight: 700;")
        insp_layout.addWidget(sec2)

        self._path_label = QLabel("N/A")
        self._path_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; background-color: {COLORS['bg_surface_raised']}; border-radius: 4px; padding: 6px;")
        self._path_label.setWordWrap(True)
        insp_layout.addWidget(self._path_label)

        sec3 = QLabel("GRAPH RELATIONSHIPS")
        sec3.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 10px; font-weight: 700;")
        insp_layout.addWidget(sec3)

        self._rels_label = QLabel("No active edges")
        self._rels_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; line-height: 1.4;")
        self._rels_label.setWordWrap(True)
        insp_layout.addWidget(self._rels_label)

        insp_layout.addStretch()
        self._inspector_panel.setVisible(False)
        drawer_layout.addWidget(self._inspector_panel)

        drawer_scroll.setWidget(self._drawer_content)
        self._detail_drawer.add_widget(drawer_scroll)
        splitter.addWidget(self._detail_drawer)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

    def update_processes(self, processes: list):
        self._all_processes = processes or []
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(self._all_processes))

        for i, proc in enumerate(self._all_processes):
            name_item = QTableWidgetItem(proc.get("name", ""))
            name_item.setData(Qt.UserRole, proc.get("entity_id", ""))
            self._table.setItem(i, 0, name_item)

            pid_item = QTableWidgetItem()
            pid_item.setData(Qt.DisplayRole, proc.get("pid", 0))
            self._table.setItem(i, 1, pid_item)

            cpu_val = proc.get("cpu_percent", 0.0)
            cpu_item = QTableWidgetItem(f"{cpu_val:.1f}%")
            if cpu_val > 50.0:
                cpu_item.setForeground(QColor(COLORS["danger"]))
            elif cpu_val > 20.0:
                cpu_item.setForeground(QColor(COLORS["warning"]))
            else:
                cpu_item.setForeground(QColor(COLORS["text_secondary"]))
            self._table.setItem(i, 2, cpu_item)

            mem_bytes = proc.get("memory_bytes", 0)
            mem_mb = mem_bytes / (1024 * 1024)
            mem_str = f"{mem_mb:.0f} MB" if mem_mb < 1024 else f"{mem_mb/1024:.2f} GB"
            mem_item = QTableWidgetItem(mem_str)
            mem_item.setData(Qt.UserRole, mem_bytes)
            self._table.setItem(i, 3, mem_item)

            threads_item = QTableWidgetItem()
            threads_item.setData(Qt.DisplayRole, proc.get("thread_count", 0))
            self._table.setItem(i, 4, threads_item)

            status_str = proc.get("status", "running")
            self._table.setItem(i, 5, QTableWidgetItem(status_str.title()))
            self._table.setItem(i, 6, QTableWidgetItem(proc.get("application", "")))

        self._table.setSortingEnabled(True)
        self._count_label.setText(f"{len(self._all_processes):,} processes monitored in digital twin")

    def _filter_table(self, text: str):
        q = text.lower()
        for i in range(self._table.rowCount()):
            match = False
            for col in range(self._table.columnCount()):
                it = self._table.item(i, col)
                if it and q in it.text().lower():
                    match = True
                    break
            self._table.setRowHidden(i, not match)

    def _on_select(self, row: int, col: int, prev_row: int, prev_col: int):
        if row < 0:
            return
        it = self._table.item(row, 0)
        if it:
            entity_id = it.data(Qt.UserRole)
            self._current_selected_id = entity_id
            name = it.text()
            self._proc_title.setText(name)
            self._empty_drawer.setVisible(False)
            self._inspector_panel.setVisible(True)
            self.process_selected.emit(entity_id or "")

    def update_detail(self, detail: dict):
        if not detail:
            return
        entity = detail.get("entity", {})
        props = entity.get("properties", {})

        self._metric_labels["PID"].setText(str(props.get("pid", "N/A")))
        self._metric_labels["Parent PID"].setText(str(props.get("ppid", "N/A")))
        self._metric_labels["User"].setText(str(props.get("username", "N/A")))

        cpu_val = props.get("cpu_percent", 0)
        self._metric_labels["CPU Usage"].setText(f"{cpu_val:.1f}%")

        mem_bytes = props.get("memory_bytes", 0)
        mem_mb = mem_bytes / (1024 * 1024)
        self._metric_labels["Memory Private"].setText(f"{mem_mb:.1f} MB")

        self._metric_labels["Threads"].setText(str(props.get("thread_count", 0)))
        self._metric_labels["Handles"].setText(str(props.get("handle_count", 0)))

        io_r = props.get("io_read_bytes", 0) / (1024 * 1024)
        io_w = props.get("io_write_bytes", 0) / (1024 * 1024)
        self._metric_labels["I/O Read Rate"].setText(f"{io_r:.2f} MB/s")
        self._metric_labels["I/O Write Rate"].setText(f"{io_w:.2f} MB/s")

        self._path_label.setText(str(props.get("executable_path", "N/A")))

        rels = detail.get("relationships", {})
        lines = []
        for r in rels.get("outgoing", [])[:6]:
            lines.append(f"→ {r.get('type', 'rel')}: {r.get('target', '')}")
        for r in rels.get("incoming", [])[:6]:
            lines.append(f"← {r.get('type', 'rel')}: {r.get('source', '')}")
        self._rels_label.setText("\n".join(lines) if lines else "Isolated process node (no external edges)")

    def _on_investigate_clicked(self):
        name = self._proc_title.text()
        if name:
            self.investigate_process.emit(f"Why is {name} running and what resources is it using?")

    def _on_graph_clicked(self):
        if self._current_selected_id:
            self.open_in_graph.emit(self._current_selected_id)
