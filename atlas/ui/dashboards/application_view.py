from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QScrollArea, QFrame, QSplitter, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QPushButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from atlas.ui.themes.dark_theme import COLORS
from atlas.ui.widgets.components import AtlasCard, AtlasBadge, AtlasSearchBox, AtlasEmptyState


class ApplicationView(QWidget):
    app_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_apps = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(16)

        header_row = QHBoxLayout()
        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        title = QLabel("Installed Applications")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {COLORS['text_primary']};")
        title_vbox.addWidget(title)

        self._count_label = QLabel("Cataloging system software inventory...")
        self._count_label.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 12px;")
        title_vbox.addWidget(self._count_label)
        header_row.addLayout(title_vbox)

        header_row.addStretch()

        self._search = AtlasSearchBox("Search applications by name or publisher...")
        self._search.setFixedWidth(280)
        self._search.text_changed.connect(self._filter_list)
        header_row.addWidget(self._search)
        layout.addLayout(header_row)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: transparent; width: 8px; }")

        list_card = AtlasCard()
        list_layout = QVBoxLayout()
        list_layout.setContentsMargins(0, 0, 0, 0)
        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.SingleSelection)
        self._list.currentItemChanged.connect(self._on_select)
        list_layout.addWidget(self._list)
        list_card.add_layout(list_layout)
        splitter.addWidget(list_card)

        self._detail_card = AtlasCard("Application Metadata")
        self._detail_card.setMinimumWidth(340)
        self._detail_card.setMaximumWidth(450)

        detail_scroll = QScrollArea()
        detail_scroll.setWidgetResizable(True)
        detail_scroll.setFrameShape(QFrame.NoFrame)
        detail_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self._detail_content = QWidget()
        dc_layout = QVBoxLayout(self._detail_content)
        dc_layout.setContentsMargins(0, 0, 0, 0)
        dc_layout.setSpacing(12)

        self._empty_detail = AtlasEmptyState(
            "Select an application",
            "Select software from the inventory list to view installation manifests, versioning, publisher, and disk footprint."
        )
        dc_layout.addWidget(self._empty_detail)

        self._detail_panel = QWidget()
        dp_layout = QVBoxLayout(self._detail_panel)
        dp_layout.setContentsMargins(0, 0, 0, 0)
        dp_layout.setSpacing(10)

        self._app_name_lbl = QLabel("Application")
        self._app_name_lbl.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {COLORS['text_primary']};")
        dp_layout.addWidget(self._app_name_lbl)

        sec1 = QLabel("PACKAGE INFORMATION")
        sec1.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 10px; font-weight: 700;")
        dp_layout.addWidget(sec1)

        self._info_box = QFrame()
        self._info_box.setStyleSheet(f"background-color: {COLORS['bg_surface_raised']}; border-radius: 5px; padding: 8px;")
        ib_layout = QVBoxLayout(self._info_box)
        ib_layout.setSpacing(6)
        self._info_labels = {}
        for k in ["Publisher", "Version", "Install Date", "Install Location", "Storage Size"]:
            row = QHBoxLayout()
            l1 = QLabel(k)
            l1.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
            l2 = QLabel("--")
            l2.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 11px; font-weight: 600;")
            l2.setAlignment(Qt.AlignRight)
            row.addWidget(l1)
            row.addWidget(l2)
            ib_layout.addLayout(row)
            self._info_labels[k] = l2
        dp_layout.addWidget(self._info_box)

        dp_layout.addStretch()
        self._detail_panel.setVisible(False)
        dc_layout.addWidget(self._detail_panel)

        detail_scroll.setWidget(self._detail_content)
        self._detail_card.add_widget(detail_scroll)
        splitter.addWidget(self._detail_card)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

    def update_applications(self, apps: list):
        self._all_apps = apps or []
        self._list.clear()
        for a in self._all_apps:
            name = a.get("name", "Unknown Software")
            ver = a.get("version", "")
            ver_text = f"v{ver}" if ver else ""
            item = QListWidgetItem(f"▦  {name}   {ver_text}")
            item.setData(Qt.UserRole, a.get("entity_id", ""))
            self._list.addItem(item)
        self._count_label.setText(f"{len(self._all_apps):,} applications cataloged")

    def _filter_list(self, text: str):
        q = text.lower()
        for i in range(self._list.count()):
            it = self._list.item(i)
            it.setHidden(q not in it.text().lower())

    def _on_select(self, current, previous):
        if not current:
            return
        entity_id = current.data(Qt.UserRole)
        name = current.text().split("   ")[0].replace("▦  ", "")
        self._app_name_lbl.setText(name)
        self._empty_detail.setVisible(False)
        self._detail_panel.setVisible(True)
        self.app_selected.emit(entity_id or "")

    def update_detail(self, detail: dict):
        if not detail:
            return
        entity = detail.get("entity", {})
        props = entity.get("properties", {})

        self._info_labels["Publisher"].setText(str(props.get("publisher", "N/A")))
        self._info_labels["Version"].setText(str(props.get("version", "N/A")))
        self._info_labels["Install Date"].setText(str(props.get("install_date", "N/A")))

        loc = str(props.get("install_location", "N/A"))
        self._info_labels["Install Location"].setText(loc[:35] + "..." if len(loc) > 35 else loc)

        size_b = props.get("size_bytes", 0)
        size_str = f"{size_b / (1024*1024):.1f} MB" if size_b > 0 else "N/A"
        self._info_labels["Storage Size"].setText(size_str)


class ServiceView(QWidget):
    service_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_services = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(16)

        header_row = QHBoxLayout()
        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        title = QLabel("Windows Services")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {COLORS['text_primary']};")
        title_vbox.addWidget(title)

        self._count_label = QLabel("Querying Windows Service Control Manager...")
        self._count_label.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 12px;")
        title_vbox.addWidget(self._count_label)
        header_row.addLayout(title_vbox)

        header_row.addStretch()

        self._search = AtlasSearchBox("Filter services by name or status...")
        self._search.setFixedWidth(280)
        self._search.text_changed.connect(self._filter_list)
        header_row.addWidget(self._search)
        layout.addLayout(header_row)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: transparent; width: 8px; }")

        list_card = AtlasCard()
        list_layout = QVBoxLayout()
        list_layout.setContentsMargins(0, 0, 0, 0)
        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.SingleSelection)
        self._list.currentItemChanged.connect(self._on_select)
        list_layout.addWidget(self._list)
        list_card.add_layout(list_layout)
        splitter.addWidget(list_card)

        self._detail_card = AtlasCard("Service Manifest & Dependencies")
        self._detail_card.setMinimumWidth(340)
        self._detail_card.setMaximumWidth(450)

        detail_scroll = QScrollArea()
        detail_scroll.setWidgetResizable(True)
        detail_scroll.setFrameShape(QFrame.NoFrame)
        detail_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self._detail_content = QWidget()
        dc_layout = QVBoxLayout(self._detail_content)
        dc_layout.setContentsMargins(0, 0, 0, 0)
        dc_layout.setSpacing(12)

        self._empty_detail = AtlasEmptyState(
            "Select a service",
            "Choose a service from the inventory to inspect execution status, startup configuration, binary path, and dependency tree."
        )
        dc_layout.addWidget(self._empty_detail)

        self._detail_panel = QWidget()
        dp_layout = QVBoxLayout(self._detail_panel)
        dp_layout.setContentsMargins(0, 0, 0, 0)
        dp_layout.setSpacing(10)

        self._svc_title = QLabel("Service")
        self._svc_title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {COLORS['text_primary']};")
        dp_layout.addWidget(self._svc_title)

        sec1 = QLabel("SERVICE CONFIGURATION")
        sec1.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 10px; font-weight: 700;")
        dp_layout.addWidget(sec1)

        self._info_box = QFrame()
        self._info_box.setStyleSheet(f"background-color: {COLORS['bg_surface_raised']}; border-radius: 5px; padding: 8px;")
        ib_layout = QVBoxLayout(self._info_box)
        ib_layout.setSpacing(6)
        self._info_labels = {}
        for k in ["Service Identifier", "Current Status", "Startup Type", "Service Account"]:
            row = QHBoxLayout()
            l1 = QLabel(k)
            l1.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
            l2 = QLabel("--")
            l2.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 11px; font-weight: 600;")
            l2.setAlignment(Qt.AlignRight)
            row.addWidget(l1)
            row.addWidget(l2)
            ib_layout.addLayout(row)
            self._info_labels[k] = l2
        dp_layout.addWidget(self._info_box)

        sec2 = QLabel("BINARY EXECUTABLE PATH")
        sec2.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 10px; font-weight: 700;")
        dp_layout.addWidget(sec2)

        self._path_label = QLabel("N/A")
        self._path_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; background-color: {COLORS['bg_surface_raised']}; border-radius: 4px; padding: 6px;")
        self._path_label.setWordWrap(True)
        dp_layout.addWidget(self._path_label)

        sec3 = QLabel("DEPENDENCY GRAPH")
        sec3.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 10px; font-weight: 700;")
        dp_layout.addWidget(sec3)

        self._deps_label = QLabel("No dependencies")
        self._deps_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; line-height: 1.4;")
        self._deps_label.setWordWrap(True)
        dp_layout.addWidget(self._deps_label)

        dp_layout.addStretch()
        self._detail_panel.setVisible(False)
        dc_layout.addWidget(self._detail_panel)

        detail_scroll.setWidget(self._detail_content)
        self._detail_card.add_widget(detail_scroll)
        splitter.addWidget(self._detail_card)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

    def update_services(self, services: list):
        self._all_services = services or []
        self._list.clear()
        for svc in self._all_services:
            st = svc.get("status", "").lower()
            if st in ("running",):
                dot = "●"
            elif st in ("stopped",):
                dot = "○"
            elif st in ("disabled",):
                dot = "◌"
            else:
                dot = "·"

            display_name = svc.get("display_name", svc.get("name", "Unknown"))
            item = QListWidgetItem(f"{dot}  {display_name}")
            if st in ("running",):
                item.setForeground(QColor(COLORS["success"]))
            elif st in ("stopped",):
                item.setForeground(QColor(COLORS["text_tertiary"]))
            else:
                item.setForeground(QColor(COLORS["text_secondary"]))

            item.setData(Qt.UserRole, svc.get("entity_id", ""))
            item.setData(Qt.UserRole + 1, svc.get("service_name", ""))
            self._list.addItem(item)
        self._count_label.setText(f"{len(self._all_services):,} services monitored in digital twin")

    def _filter_list(self, text: str):
        q = text.lower()
        for i in range(self._list.count()):
            it = self._list.item(i)
            it.setHidden(q not in it.text().lower())

    def _on_select(self, current, previous):
        if not current:
            return
        entity_id = current.data(Qt.UserRole)
        name = current.text()[3:]
        self._svc_title.setText(name)
        self._empty_detail.setVisible(False)
        self._detail_panel.setVisible(True)
        self.service_selected.emit(entity_id or "")

    def update_detail(self, detail: dict):
        if not detail:
            return
        entity = detail.get("entity", {})
        props = entity.get("properties", {})

        self._info_labels["Service Identifier"].setText(str(props.get("service_name", "N/A")))
        self._info_labels["Current Status"].setText(str(props.get("status", "N/A")).title())
        self._info_labels["Startup Type"].setText(str(props.get("startup_type", "N/A")).title())
        self._info_labels["Service Account"].setText(str(props.get("account", "LocalSystem")))

        self._path_label.setText(str(props.get("executable_path", "N/A")))

        deps = props.get("dependencies", [])
        if deps:
            self._deps_label.setText("\n".join(f"• {d}" for d in deps))
        else:
            self._deps_label.setText("No upstream service dependencies")
