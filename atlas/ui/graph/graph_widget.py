import math
import random
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QGraphicsScene, QGraphicsView, QGraphicsEllipseItem,
    QGraphicsPathItem, QGraphicsTextItem, QGraphicsItem,
    QPushButton, QSlider, QFrame, QSplitter, QSizePolicy
)
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import (
    QColor, QPen, QBrush, QFont, QPainter, QPainterPath,
    QWheelEvent
)

from atlas.ui.themes.dark_theme import COLORS
from atlas.ui.widgets.components import AtlasCard, AtlasBadge, AtlasEmptyState


class GraphNode(QGraphicsEllipseItem):
    def __init__(self, entity_id: str, name: str, entity_type: str, x: float, y: float, radius: float = 16):
        super().__init__(-radius, -radius, radius * 2, radius * 2)
        self.entity_id = entity_id
        self.entity_name = name
        self.entity_type = entity_type
        self.radius = radius

        type_colors = {
            "process": COLORS["graph_node_process"],
            "service": COLORS["graph_node_service"],
            "application": COLORS["graph_node_app"],
            "cpu": COLORS["graph_node_hardware"],
            "gpu": COLORS["graph_node_hardware"],
            "memory": COLORS["graph_node_hardware"],
            "storage_device": COLORS["graph_node_hardware"],
            "network_adapter": COLORS["graph_node_hardware"],
            "machine": COLORS["accent_blue"],
            "partition": COLORS["chart_disk"],
            "network_connection": COLORS["chart_network"],
            "project": COLORS["accent_pink"],
        }
        self.base_color = QColor(type_colors.get(entity_type, COLORS["graph_node"]))
        self.setBrush(QBrush(self.base_color))
        self.setPen(QPen(QColor(COLORS["bg_base"]), 2))
        self.setPos(x, y)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setCursor(Qt.PointingHandCursor)
        self.setAcceptHoverEvents(True)
        self.setToolTip(f"{entity_type.upper()}: {name}")

        self._label = QGraphicsTextItem(name[:18], self)
        self._label.setDefaultTextColor(QColor(COLORS["text_secondary"]))
        font = QFont("Segoe UI Variable Text", 8)
        font.setWeight(QFont.DemiBold)
        self._label.setFont(font)
        br = self._label.boundingRect()
        self._label.setPos(-br.width() / 2, radius + 3)
        self._edges = []

    def add_edge(self, edge):
        self._edges.append(edge)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            for edge in self._edges:
                edge.update_position()
        return super().itemChange(change, value)

    def hoverEnterEvent(self, event):
        self.setPen(QPen(QColor(COLORS["accent_blue"]), 3))
        self.setScale(1.15)
        self._label.setDefaultTextColor(QColor(COLORS["text_primary"]))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setPen(QPen(QColor(COLORS["bg_base"]), 2))
        self.setScale(1.0)
        self._label.setDefaultTextColor(QColor(COLORS["text_secondary"]))
        super().hoverLeaveEvent(event)


class GraphEdge(QGraphicsPathItem):
    def __init__(self, source_node: GraphNode, target_node: GraphNode, rel_type: str = ""):
        super().__init__()
        self.source_node = source_node
        self.target_node = target_node
        self.rel_type = rel_type

        pen = QPen(QColor(COLORS["border"]), 1.2)
        pen.setStyle(Qt.SolidLine)
        self.setPen(pen)
        self.setZValue(-1)
        self.update_position()

        source_node.add_edge(self)
        target_node.add_edge(self)

    def update_position(self):
        p1 = self.source_node.pos()
        p2 = self.target_node.pos()

        path = QPainterPath()
        path.moveTo(p1)
        ctrl_x = (p1.x() + p2.x()) / 2
        ctrl_y = (p1.y() + p2.y()) / 2 - 15
        path.quadTo(ctrl_x, ctrl_y, p2.x(), p2.y())
        self.setPath(path)


class InteractiveGraphView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet(f"background-color: {COLORS['bg_surface']}; border-radius: 6px;")

    def wheelEvent(self, event: QWheelEvent):
        factor = 1.15 if event.angleDelta().y() > 0 else 1.0 / 1.15
        self.scale(factor, factor)


class GraphWidget(QWidget):
    node_selected = Signal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._nodes = {}
        self._edges = []
        self._raw_entities = []
        self._raw_relationships = []
        self._active_mode = "FULL SYSTEM"
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(16)

        header_row = QHBoxLayout()
        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        title = QLabel("Digital Twin Topology Explorer")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {COLORS['text_primary']};")
        title_vbox.addWidget(title)
        sub = QLabel("Interactive 2D graph modeling live semantic relationships and dependencies")
        sub.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 12px;")
        title_vbox.addWidget(sub)
        header_row.addLayout(title_vbox)
        header_row.addStretch()

        mode_row = QHBoxLayout()
        mode_row.setSpacing(6)
        for m in ["FULL SYSTEM", "PROCESSES", "SERVICES", "APPLICATIONS", "HARDWARE"]:
            btn = QPushButton(m)
            btn.setFixedHeight(26)
            btn.setCursor(Qt.PointingHandCursor)
            if m == "FULL SYSTEM":
                btn.setStyleSheet(f"background-color: {COLORS['bg_surface_raised']}; color: {COLORS['accent_blue']}; border: 1px solid {COLORS['accent_blue']}; border-radius: 4px; padding: 0 10px; font-size: 11px; font-weight: 600;")
            else:
                btn.setStyleSheet(f"background-color: transparent; color: {COLORS['text_secondary']}; border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 0 10px; font-size: 11px;")
            btn.clicked.connect(lambda checked, name=m: self._set_mode(name))
            mode_row.addWidget(btn)
        header_row.addLayout(mode_row)
        layout.addLayout(header_row)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: transparent; width: 8px; }")

        graph_card = AtlasCard()
        gc_layout = QVBoxLayout()
        gc_layout.setContentsMargins(0, 0, 0, 0)

        self._scene = QGraphicsScene(self)
        self._scene.setSceneRect(-1500, -1500, 3000, 3000)
        self._scene.selectionChanged.connect(self._on_selection_changed)

        self._view = InteractiveGraphView(self._scene)
        gc_layout.addWidget(self._view)
        graph_card.add_layout(gc_layout)
        splitter.addWidget(graph_card)

        self._inspector = AtlasCard("Node Inspector")
        self._inspector.setMinimumWidth(320)
        self._inspector.setMaximumWidth(420)

        insp_vbox = QVBoxLayout()
        insp_vbox.setSpacing(12)

        self._empty_node = AtlasEmptyState(
            "Select a Graph Node",
            "Click any node in the topology canvas to inspect identity, type, incoming/outgoing edges, and dependent entities."
        )
        insp_vbox.addWidget(self._empty_node)

        self._node_panel = QWidget()
        np_layout = QVBoxLayout(self._node_panel)
        np_layout.setContentsMargins(0, 0, 0, 0)
        np_layout.setSpacing(10)

        self._node_name_lbl = QLabel("Node Name")
        self._node_name_lbl.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLORS['text_primary']};")
        np_layout.addWidget(self._node_name_lbl)

        self._node_badge = AtlasBadge("PROCESS", variant="info")
        np_layout.addWidget(self._node_badge)

        sec1 = QLabel("CONNECTED TOPOLOGY EDGES")
        sec1.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 10px; font-weight: 700; margin-top: 6px;")
        np_layout.addWidget(sec1)

        self._edges_label = QLabel("No active connections")
        self._edges_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; line-height: 1.5;")
        self._edges_label.setWordWrap(True)
        np_layout.addWidget(self._edges_label)

        np_layout.addStretch()
        self._node_panel.setVisible(False)
        insp_vbox.addWidget(self._node_panel)

        self._inspector.add_layout(insp_vbox)
        splitter.addWidget(self._inspector)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

    def _set_mode(self, mode: str):
        self._active_mode = mode
        self.update_graph(self._raw_entities, self._raw_relationships)

    def update_graph(self, entities: list, relationships: list):
        self._raw_entities = entities or []
        self._raw_relationships = relationships or []
        self._scene.clear()
        self._nodes = {}
        self._edges = []

        type_filter_map = {
            "FULL SYSTEM": None,
            "PROCESSES": {"process"},
            "SERVICES": {"service"},
            "APPLICATIONS": {"application"},
            "HARDWARE": {"machine", "cpu", "gpu", "memory", "partition", "network_adapter"},
        }
        allowed = type_filter_map.get(self._active_mode)

        filtered_entities = []
        for e in self._raw_entities:
            etype = e.get("entity_type", "")
            if allowed is None or etype in allowed:
                filtered_entities.append(e)

        if not filtered_entities:
            return

        total = len(filtered_entities)
        radius = min(400.0, max(180.0, total * 9.0))
        cx, cy = 0.0, 0.0

        for i, ent in enumerate(filtered_entities):
            angle = 2.0 * math.pi * (i / max(total, 1))
            jitter = (random.random() - 0.5) * 40.0
            r = radius + jitter
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)

            eid = ent.get("id", "")
            node = GraphNode(eid, ent.get("name", "Node"), ent.get("entity_type", "entity"), x, y)
            self._scene.addItem(node)
            self._nodes[eid] = node

        for rel in self._raw_relationships:
            s_id = rel.get("source_id", "")
            t_id = rel.get("target_id", "")
            if s_id in self._nodes and t_id in self._nodes:
                edge = GraphEdge(self._nodes[s_id], self._nodes[t_id], rel.get("relationship_type", ""))
                self._scene.addItem(edge)
                self._edges.append(edge)

        self._view.setSceneRect(self._scene.itemsBoundingRect().adjusted(-60, -60, 60, 60))

    def _on_selection_changed(self):
        items = self._scene.selectedItems()
        if not items:
            return
        node = items[0]
        if isinstance(node, GraphNode):
            self._empty_node.setVisible(False)
            self._node_panel.setVisible(True)
            self._node_name_lbl.setText(node.entity_name)
            self._node_badge.set_text(node.entity_type.upper(), variant="info")

            edge_lines = []
            for edge in node._edges:
                other = edge.target_node if edge.source_node == node else edge.source_node
                dir_arrow = "→" if edge.source_node == node else "←"
                edge_lines.append(f"{dir_arrow} {edge.rel_type or 'linked'}: {other.entity_name}")

            self._edges_label.setText("\n".join(edge_lines[:10]) if edge_lines else "No connected edges")
            self.node_selected.emit(node.entity_id, node.entity_name, node.entity_type)
