from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QLineEdit, QPushButton, QScrollArea, QFrame, QSizePolicy, QGridLayout
)
from PySide6.QtCore import Qt, Signal, QTimer, QDateTime
from PySide6.QtGui import QFont, QTextCursor, QColor

from atlas.ui.themes.dark_theme import COLORS
from atlas.ui.widgets.components import AtlasCard, AtlasBadge, AtlasEmptyState


class ChatMessage(QFrame):
    def __init__(self, text, is_user=True, parent=None):
        super().__init__(parent)
        self._is_user = is_user
        self._text = text
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(f"""
            ChatMessage {{
                background-color: {COLORS['bg_surface'] if not self._is_user else COLORS['bg_raised']};
                border: 1px solid {COLORS['border_light'] if not self._is_user else COLORS['border']};
                border-radius: 6px;
                margin: 4px {'60px 4px 4px' if self._is_user else '4px 4px 60px'};
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        if self._is_user:
            role_badge = AtlasBadge("USER", "info")
            header_layout.addWidget(role_badge)
            role_title = QLabel("Query")
            role_title.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {COLORS['text_secondary']};")
            header_layout.addWidget(role_title)
        else:
            role_badge = AtlasBadge("ATLAS INTELLIGENCE", "accent")
            header_layout.addWidget(role_badge)
            conf_badge = AtlasBadge("CONFIDENCE: HIGH", "healthy")
            header_layout.addWidget(conf_badge)

        header_layout.addStretch()

        time_str = QDateTime.currentDateTime().toString("HH:mm:ss")
        time_lbl = QLabel(time_str)
        time_lbl.setStyleSheet(f"font-size: 10px; color: {COLORS['text_muted']}; font-family: 'Consolas', monospace;")
        header_layout.addWidget(time_lbl)

        layout.addLayout(header_layout)

        if self._is_user:
            body = QLabel(self._text)
            body.setWordWrap(True)
            body.setTextInteractionFlags(Qt.TextSelectableByMouse)
            body.setStyleSheet(f"""
                color: {COLORS['text_primary']};
                font-size: 13px;
                line-height: 1.5;
            """)
            layout.addWidget(body)
        else:
            self._render_ai_response(layout, self._text)

    def _render_ai_response(self, layout, raw_text):
        has_sections = any(keyword in raw_text.upper() for keyword in ["FINDING:", "EVIDENCE:", "RECOMMEND", "HYPOTHESIS:"])

        if has_sections:
            lines = raw_text.split("\n")
            current_section = None
            section_content = []

            def flush_section(sec_name, lines_list):
                if not lines_list:
                    return
                block = QFrame()
                block.setStyleSheet(f"""
                    QFrame {{
                        background-color: {COLORS['bg_subtle']};
                        border: 1px solid {COLORS['border']};
                        border-left: 3px solid {COLORS['accent']};
                        border-radius: 4px;
                    }}
                """)
                b_layout = QVBoxLayout(block)
                b_layout.setContentsMargins(12, 10, 12, 10)
                b_layout.setSpacing(4)

                sec_label = QLabel(sec_name)
                sec_label.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {COLORS['accent']}; letter-spacing: 0.5px;")
                b_layout.addWidget(sec_label)

                content_lbl = QLabel("\n".join(lines_list).strip())
                content_lbl.setWordWrap(True)
                content_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
                content_lbl.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 12px; line-height: 1.4;")
                b_layout.addWidget(content_lbl)

                layout.addWidget(block)

            for line in lines:
                upper = line.strip().upper()
                if upper.startswith("FINDING:") or upper.startswith("FINDINGS:"):
                    flush_section(current_section, section_content)
                    current_section = "FINDINGS"
                    section_content = [line.split(":", 1)[1].strip()] if ":" in line else []
                elif upper.startswith("EVIDENCE:") or upper.startswith("EVIDENCE GATHERED:"):
                    flush_section(current_section, section_content)
                    current_section = "EVIDENCE GATHERED"
                    section_content = [line.split(":", 1)[1].strip()] if ":" in line else []
                elif upper.startswith("RECOMMEND") or upper.startswith("ACTIONS:"):
                    flush_section(current_section, section_content)
                    current_section = "RECOMMENDED ACTIONS"
                    section_content = [line.split(":", 1)[1].strip()] if ":" in line else []
                elif upper.startswith("HYPOTHESIS:"):
                    flush_section(current_section, section_content)
                    current_section = "DIAGNOSTIC HYPOTHESIS"
                    section_content = [line.split(":", 1)[1].strip()] if ":" in line else []
                else:
                    if current_section:
                        section_content.append(line)
                    else:
                        if not hasattr(self, "_intro_lines"):
                            self._intro_lines = []
                        self._intro_lines.append(line)

            flush_section(current_section, section_content)

            if hasattr(self, "_intro_lines") and self._intro_lines:
                intro_text = "\n".join(self._intro_lines).strip()
                if intro_text:
                    intro_lbl = QLabel(intro_text)
                    intro_lbl.setWordWrap(True)
                    intro_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
                    intro_lbl.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 13px; line-height: 1.5;")
                    layout.insertWidget(1, intro_lbl)
        else:
            body = QLabel(raw_text)
            body.setWordWrap(True)
            body.setTextInteractionFlags(Qt.TextSelectableByMouse)
            body.setStyleSheet(f"""
                color: {COLORS['text_primary']};
                font-size: 13px;
                line-height: 1.6;
            """)
            layout.addWidget(body)


class AIChatView(QWidget):
    query_submitted = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_ai_connected = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        header_card = QFrame()
        header_card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
            }}
        """)
        hc_layout = QHBoxLayout(header_card)
        hc_layout.setContentsMargins(20, 16, 20, 16)
        hc_layout.setSpacing(16)

        title_col = QVBoxLayout()
        title_col.setSpacing(3)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        title = QLabel("System Intelligence Studio")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {COLORS['text_primary']};")
        title_row.addWidget(title)
        badge = AtlasBadge("COGNITIVE REASONING", "accent")
        title_row.addWidget(badge)
        title_row.addStretch()
        title_col.addLayout(title_row)

        desc = QLabel("Ask questions about machine performance, anomalies, root causes, and hardware baselines.")
        desc.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 12px;")
        title_col.addWidget(desc)
        hc_layout.addLayout(title_col, 1)

        status_col = QHBoxLayout()
        status_col.setSpacing(10)

        self._ollama_pill = AtlasBadge("Ollama: Checking...", "warning")
        status_col.addWidget(self._ollama_pill)

        self._model_pill = AtlasBadge("Model: qwen2.5:7b", "info")
        status_col.addWidget(self._model_pill)

        self._twin_pill = AtlasBadge("Digital Twin: Synced", "healthy")
        status_col.addWidget(self._twin_pill)

        hc_layout.addLayout(status_col)
        layout.addWidget(header_card)

        sugg_box = QFrame()
        sugg_box.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_raised']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 6px;
            }}
        """)
        sugg_layout = QHBoxLayout(sugg_box)
        sugg_layout.setContentsMargins(14, 8, 14, 8)
        sugg_layout.setSpacing(10)

        sugg_label = QLabel("QUICK INQUIRY:")
        sugg_label.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {COLORS['text_muted']}; letter-spacing: 0.5px;")
        sugg_layout.addWidget(sugg_label)

        suggestions = [
            "Why is my PC slow?",
            "What changed today?",
            "What is using the most memory?",
            "What depends on this service?",
            "Why did this process crash?",
        ]
        for s in suggestions:
            btn = QPushButton(s)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['bg_surface']};
                    color: {COLORS['text_secondary']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 4px;
                    padding: 5px 12px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['bg_subtle']};
                    color: {COLORS['accent']};
                    border-color: {COLORS['accent']};
                }}
            """)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, text=s: self._submit_suggestion(text))
            sugg_layout.addWidget(btn)

        sugg_layout.addStretch()
        layout.addWidget(sugg_box)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self._messages_widget = QWidget()
        self._messages_layout = QVBoxLayout(self._messages_widget)
        self._messages_layout.setContentsMargins(0, 0, 0, 0)
        self._messages_layout.setSpacing(12)

        self._welcome_state = AtlasEmptyState(
            title="ATLAS Machine Intelligence",
            message="Direct conversational access to your system's digital twin, processes, baseline drift, and topology graph.\nAsk a diagnostic question above or select a quick inquiry to begin.",
            icon_symbol="✦"
        )
        self._messages_layout.addWidget(self._welcome_state)
        self._messages_layout.addStretch()

        self._scroll.setWidget(self._messages_widget)
        layout.addWidget(self._scroll, 1)

        self._thinking_card = QFrame()
        self._thinking_card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_surface']};
                border: 1px solid {COLORS['accent_muted']};
                border-radius: 6px;
            }}
        """)
        th_layout = QHBoxLayout(self._thinking_card)
        th_layout.setContentsMargins(14, 10, 14, 10)
        th_layout.setSpacing(10)

        th_icon = QLabel("✦")
        th_icon.setStyleSheet(f"font-size: 14px; color: {COLORS['accent']}; font-weight: 700;")
        th_layout.addWidget(th_icon)

        self._thinking_text = QLabel("Analyzing digital twin topology and telemetry data...")
        self._thinking_text.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        th_layout.addWidget(self._thinking_text)
        th_layout.addStretch()

        self._thinking_card.setVisible(False)
        layout.addWidget(self._thinking_card)

        input_container = QFrame()
        input_container.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
            }}
            QFrame:focus-within {{
                border-color: {COLORS['accent']};
            }}
        """)
        in_layout = QHBoxLayout(input_container)
        in_layout.setContentsMargins(12, 6, 8, 6)
        in_layout.setSpacing(10)

        cmd_icon = QLabel("✦")
        cmd_icon.setStyleSheet(f"font-size: 13px; color: {COLORS['accent']}; font-weight: bold;")
        in_layout.addWidget(cmd_icon)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Ask ATLAS anything about your machine... (e.g. Why is my PC slow?)")
        self._input.setFixedHeight(34)
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                color: {COLORS['text_primary']};
                border: none;
                font-size: 13px;
            }}
        """)
        self._input.returnPressed.connect(self._submit)
        in_layout.addWidget(self._input, 1)

        self._send_btn = QPushButton("Ask ATLAS ↵")
        self._send_btn.setFixedHeight(32)
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: #06090E;
                border: none;
                border-radius: 4px;
                padding: 0 16px;
                font-size: 12px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: #60CDFF;
            }}
            QPushButton:disabled {{
                background-color: {COLORS['bg_raised']};
                color: {COLORS['text_muted']};
            }}
        """)
        self._send_btn.setCursor(Qt.PointingHandCursor)
        self._send_btn.clicked.connect(self._submit)
        in_layout.addWidget(self._send_btn)

        layout.addWidget(input_container)

    def _submit(self):
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        if self._welcome_state.isVisible():
            self._welcome_state.setVisible(False)
        self.add_message(text, is_user=True)
        self.set_thinking(True)
        self.query_submitted.emit(text)

    def _submit_suggestion(self, text):
        self._input.setText(text)
        self._submit()

    def add_message(self, text, is_user=True):
        if self._welcome_state.isVisible():
            self._welcome_state.setVisible(False)
        msg = ChatMessage(text, is_user)
        count = self._messages_layout.count()
        self._messages_layout.insertWidget(count - 1, msg)
        QTimer.singleShot(50, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        ))

    def set_thinking(self, thinking, text=None):
        self._thinking_card.setVisible(thinking)
        if text:
            self._thinking_text.setText(text)
        else:
            self._thinking_text.setText("Analyzing digital twin topology and telemetry data...")
        self._send_btn.setEnabled(not thinking)
        self._input.setEnabled(not thinking)
        if not thinking:
            self._input.setFocus()

    def set_ai_status(self, connected, model_name="qwen2.5:7b"):
        self._is_ai_connected = connected
        if connected:
            self._ollama_pill.set_text("Ollama: Online")
            self._ollama_pill.set_variant("healthy")
            self._model_pill.set_text(f"Model: {model_name}")
            self._model_pill.set_variant("info")
        else:
            self._ollama_pill.set_text("Ollama: Offline")
            self._ollama_pill.set_variant("warning")
            self._model_pill.set_text("Engine: Deterministic")
            self._model_pill.set_variant("default")
