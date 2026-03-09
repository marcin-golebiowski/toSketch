# SPDX-License-Identifier: GPL-2.0-or-later
"""PySide2 dialog for AI-assisted smart face selection."""
import json
import threading

from PySide import QtCore, QtGui
try:
    from PySide import QtWidgets
except ImportError:
    QtWidgets = QtGui  # PySide1 fallback

from .faceAnalysis import full_analysis
from .ollamaClient import (
    get_preferences, save_preferences,
    check_ollama_available, list_ollama_models,
    build_prompt, query_ollama, apply_ollama_annotations,
)


# ── Color helpers ─────────────────────────────────────────────────
def _score_color(score):
    """Return a QColor on a red-yellow-green gradient for 0-100."""
    score = max(0, min(100, score))
    if score < 50:
        r = 220
        g = int(80 + 140 * (score / 50.0))
        b = 60
    else:
        r = int(220 - 180 * ((score - 50) / 50.0))
        g = 200
        b = 60
    return QtGui.QColor(r, g, b)


def _score_bar_widget(score, parent=None):
    """Create a small horizontal bar widget showing a score 0-100."""
    bar = QtWidgets.QProgressBar(parent)
    bar.setRange(0, 100)
    bar.setValue(int(score))
    bar.setTextVisible(True)
    bar.setFormat(f"{int(score)}")
    bar.setFixedHeight(18)
    color = _score_color(score)
    bar.setStyleSheet(
        f"QProgressBar {{ border: 1px solid #ccc; border-radius: 3px; "
        f"background: #f0f0f0; text-align: center; font-size: 11px; }}"
        f"QProgressBar::chunk {{ background: {color.name()}; border-radius: 2px; }}"
    )
    return bar


# ── Surface type icons (unicode) ──────────────────────────────────
_TYPE_ICONS = {
    "Plane": "\u25ad",      # white rectangle
    "Cylinder": "\u25ef",   # large circle
    "Cone": "\u25b3",       # triangle
    "Sphere": "\u25cf",     # filled circle
    "BSpline": "\u223f",    # sine wave
    "Toroid": "\u25c9",     # fisheye
    "Other": "\u25a1",      # white square
}


class OllamaWorker(QtCore.QThread):
    """Background thread for Ollama queries."""
    finished = QtCore.Signal(object)
    error = QtCore.Signal(str)
    raw_response = QtCore.Signal(str)

    def __init__(self, prompt, prefs, parent=None):
        super().__init__(parent)
        self.prompt = prompt
        self.prefs = prefs

    def run(self):
        import urllib.request
        try:
            url = self.prefs["url"].rstrip("/") + "/api/generate"
            body = {
                "model": self.prefs["model"],
                "prompt": self.prompt,
                "stream": True,
                "think": True,
                "format": "json",
            }
            system_prompt = self.prefs.get("system_prompt", "")
            if system_prompt:
                body["system"] = system_prompt
            temperature = self.prefs.get("temperature")
            if temperature is not None:
                body["options"] = {"temperature": temperature}

            payload = json.dumps(body).encode("utf-8")
            req = urllib.request.Request(
                url, data=payload, method="POST",
                headers={"Content-Type": "application/json"})

            self.raw_response.emit(f">>> POST {url}\n>>> Model: {body['model']}\n")
            self.raw_response.emit(f">>> Prompt:\n{self.prompt}\n\n")

            timeout = self.prefs.get("timeout", 60)
            face_count = self.prompt.count("Face ")
            timeout = max(timeout, 60 + face_count * 2)
            self.raw_response.emit(f">>> Timeout: {timeout}s ({face_count} faces)\n\n")

            with urllib.request.urlopen(req, timeout=timeout) as resp:
                response_text = ""
                thinking_text = ""
                in_thinking = False

                for line in resp:
                    line = line.decode().strip()
                    if not line:
                        continue
                    chunk = json.loads(line)

                    # Thinking content (streamed)
                    think_chunk = chunk.get("thinking", "")
                    if think_chunk:
                        if not in_thinking:
                            self.raw_response.emit("<<< Thinking:\n")
                            in_thinking = True
                        self.raw_response.emit(think_chunk)
                        thinking_text += think_chunk

                    # Response content (streamed)
                    resp_chunk = chunk.get("response", "")
                    if resp_chunk:
                        if in_thinking:
                            self.raw_response.emit("\n\n<<< Response:\n")
                            in_thinking = False
                        elif not response_text:
                            self.raw_response.emit("<<< Response:\n")
                        self.raw_response.emit(resp_chunk)
                        response_text += resp_chunk

                    if chunk.get("done"):
                        break

                self.raw_response.emit("\n\n>>> Done.\n")

                # Parse final result
                final_text = response_text
                if not final_text and thinking_text:
                    final_text = thinking_text
                result = json.loads(final_text) if final_text else None
                self.finished.emit(result)
        except Exception as e:
            self.raw_response.emit(f"\n!!! Error: {e}\n")
            self.error.emit(str(e))


class SmartSelectDialog(QtWidgets.QDialog):
    """Dialog for AI-assisted face selection from STEP shapes."""

    _sig_connection_checked = QtCore.Signal(bool, int)

    # Column indices
    COL_CHECK = 0
    COL_INDEX = 1
    COL_SCORE = 2
    COL_NAME = 3
    COL_GROUP = 4
    COL_TYPE = 5
    COL_AREA = 6
    COL_EDGES = 7
    COL_NORMAL = 8

    def __init__(self, shape, obj=None, parent=None):
        super().__init__(parent)
        self.shape = shape
        self.obj = obj
        self.analysis = None
        self.worker = None
        self._prev_selection = None
        self._type_filter = "All"
        self._group_filter = "All"
        self._search_text = ""

        self._sig_connection_checked.connect(self._on_connection_checked)
        self.setWindowTitle("Smart Face Selection")
        self.setMinimumSize(960, 700)
        self._build_ui()
        self._run_analysis()

    # ── UI Construction ───────────────────────────────────────────

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(8, 8, 8, 8)

        # ── Top: AI Analysis Panel ──
        ai_group = QtWidgets.QGroupBox("AI Analysis")
        ai_group.setStyleSheet(
            "QGroupBox { font-weight: bold; padding-top: 14px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 8px; }")
        ai_layout = QtWidgets.QGridLayout(ai_group)
        ai_layout.setSpacing(4)

        self.lbl_description = QtWidgets.QLabel("(analyzing...)")
        self.lbl_description.setWordWrap(True)
        self.lbl_description.setStyleSheet("color: #2c3e50; font-size: 12px;")

        self.lbl_strategy = QtWidgets.QLabel("")
        self.lbl_strategy.setWordWrap(True)
        self.lbl_strategy.setStyleSheet("color: #555; font-style: italic;")

        self.lbl_status = QtWidgets.QLabel("")
        self.lbl_status.setStyleSheet("font-size: 11px;")

        lbl_part = QtWidgets.QLabel("Part:")
        lbl_part.setStyleSheet("font-weight: bold; color: #666;")
        lbl_strat = QtWidgets.QLabel("Strategy:")
        lbl_strat.setStyleSheet("font-weight: bold; color: #666;")

        ai_layout.addWidget(lbl_part, 0, 0)
        ai_layout.addWidget(self.lbl_description, 0, 1)
        ai_layout.addWidget(lbl_strat, 1, 0)
        ai_layout.addWidget(self.lbl_strategy, 1, 1)

        # Context input for additional info
        lbl_context = QtWidgets.QLabel("Context:")
        lbl_context.setStyleSheet("font-weight: bold; color: #666;")
        ai_layout.addWidget(lbl_context, 2, 0, QtCore.Qt.AlignTop)

        self.txt_ai_context = QtWidgets.QLineEdit()
        self.txt_ai_context.setPlaceholderText(
            "Optional: describe the part, e.g. 'bearing housing', 'gear mount plate'...")
        self.txt_ai_context.setStyleSheet(
            "QLineEdit { border: 1px solid #ccc; border-radius: 3px; "
            "padding: 4px 6px; font-size: 11px; }")
        ai_layout.addWidget(self.txt_ai_context, 2, 1)

        # Analyze button + status on same row
        ai_btn_row = QtWidgets.QHBoxLayout()
        self.btn_analyze_ai = QtWidgets.QPushButton("Analyze with AI")
        self.btn_analyze_ai.setStyleSheet(
            "QPushButton { background: #2980b9; color: white; padding: 4px 14px; "
            "border-radius: 3px; font-size: 11px; font-weight: bold; }"
            "QPushButton:hover { background: #3498db; }"
            "QPushButton:disabled { background: #bdc3c7; }")
        self.btn_analyze_ai.clicked.connect(self._on_analyze_ai_clicked)
        ai_btn_row.addWidget(self.btn_analyze_ai)
        ai_btn_row.addWidget(self.lbl_status)
        ai_btn_row.addStretch()
        ai_layout.addLayout(ai_btn_row, 3, 0, 1, 2)

        ai_layout.setColumnStretch(1, 1)

        layout.addWidget(ai_group)

        # ── Filter / Search Bar ──
        filter_layout = QtWidgets.QHBoxLayout()
        filter_layout.setSpacing(8)

        # Search box
        self.txt_search = QtWidgets.QLineEdit()
        self.txt_search.setPlaceholderText("Search faces...")
        self.txt_search.setClearButtonEnabled(True)
        self.txt_search.setMaximumWidth(200)
        self.txt_search.textChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.txt_search)

        # Type filter
        filter_layout.addWidget(QtWidgets.QLabel("Type:"))
        self.combo_type_filter = QtWidgets.QComboBox()
        self.combo_type_filter.addItem("All")
        self.combo_type_filter.setMinimumWidth(100)
        self.combo_type_filter.currentTextChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.combo_type_filter)

        # Group filter
        filter_layout.addWidget(QtWidgets.QLabel("Group:"))
        self.combo_group_filter = QtWidgets.QComboBox()
        self.combo_group_filter.addItem("All")
        self.combo_group_filter.setMinimumWidth(120)
        self.combo_group_filter.currentTextChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.combo_group_filter)

        # Face count summary
        self.lbl_summary = QtWidgets.QLabel("")
        self.lbl_summary.setStyleSheet(
            "color: #666; font-size: 11px; padding-left: 8px;")
        filter_layout.addStretch()
        filter_layout.addWidget(self.lbl_summary)

        layout.addLayout(filter_layout)

        # ── Face Table ──
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "", "#", "Score", "AI Name", "Group", "Type", "Area (mm\u00b2)", "Edges", "Normal"
        ])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            "QTableWidget { gridline-color: #ddd; font-size: 12px; }"
            "QTableWidget::item { padding: 2px 6px; }"
            "QTableWidget::item:selected { background: #d4e6f9; color: #000; }"
            "QHeaderView::section { background: #e0e0e0; border: 1px solid #bbb; "
            "padding: 4px 6px; font-weight: bold; font-size: 11px; color: #333; }"
        )
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(self.COL_CHECK, QtWidgets.QHeaderView.Fixed)
        header.resizeSection(self.COL_CHECK, 30)
        header.setSectionResizeMode(self.COL_INDEX, QtWidgets.QHeaderView.Fixed)
        header.resizeSection(self.COL_INDEX, 40)
        header.setSectionResizeMode(self.COL_SCORE, QtWidgets.QHeaderView.Fixed)
        header.resizeSection(self.COL_SCORE, 80)

        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setVisible(True)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)
        self.table.verticalHeader().setDefaultSectionSize(26)
        self.table.setMouseTracking(True)
        self.table.cellEntered.connect(self._on_hover)
        self.table.cellDoubleClicked.connect(self._on_double_click)
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        # ── Tab Widget: Faces + Ollama Log ──
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(self.table, "Faces")

        self.txt_ollama_log = QtWidgets.QPlainTextEdit()
        self.txt_ollama_log.setReadOnly(True)
        self.txt_ollama_log.setStyleSheet(
            "QPlainTextEdit { font-family: monospace; font-size: 11px; "
            "background: #1e1e1e; color: #d4d4d4; border: none; }")
        self.txt_ollama_log.setPlaceholderText("Ollama responses will appear here...")
        self.tabs.addTab(self.txt_ollama_log, "Ollama Log")

        layout.addWidget(self.tabs, 1)  # stretch factor = 1

        # ── Button Row ──
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setSpacing(6)

        btn_all = QtWidgets.QPushButton(" Select All")
        btn_all.clicked.connect(self._select_all)
        btn_layout.addWidget(btn_all)

        btn_none = QtWidgets.QPushButton(" Deselect All")
        btn_none.clicked.connect(self._deselect_all)
        btn_layout.addWidget(btn_none)

        btn_invert = QtWidgets.QPushButton(" Invert")
        btn_invert.clicked.connect(self._invert_selection)
        btn_layout.addWidget(btn_invert)

        btn_check_sel = QtWidgets.QPushButton(" Check Highlighted")
        btn_check_sel.setToolTip("Check highlighted rows (Space)")
        btn_check_sel.clicked.connect(self._check_highlighted)
        btn_layout.addWidget(btn_check_sel)

        btn_uncheck_sel = QtWidgets.QPushButton(" Uncheck Highlighted")
        btn_uncheck_sel.setToolTip("Uncheck highlighted rows")
        btn_uncheck_sel.clicked.connect(self._uncheck_highlighted)
        btn_layout.addWidget(btn_uncheck_sel)

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.VLine)
        sep.setFrameShadow(QtWidgets.QFrame.Sunken)
        btn_layout.addWidget(sep)

        btn_ai = QtWidgets.QPushButton(" AI Recommended")
        btn_ai.setStyleSheet(
            "QPushButton { color: #d35400; font-weight: bold; }")
        btn_ai.clicked.connect(self._select_ai_recommended)
        btn_layout.addWidget(btn_ai)

        sep2 = QtWidgets.QFrame()
        sep2.setFrameShape(QtWidgets.QFrame.VLine)
        sep2.setFrameShadow(QtWidgets.QFrame.Sunken)
        btn_layout.addWidget(sep2)

        # Threshold slider + spinbox linked
        btn_layout.addWidget(QtWidgets.QLabel("Threshold:"))
        self.slider_threshold = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_threshold.setRange(0, 100)
        self.slider_threshold.setValue(60)
        self.slider_threshold.setMaximumWidth(120)
        self.slider_threshold.setStyleSheet(
            "QSlider::groove:horizontal { height: 6px; background: #ddd; "
            "border-radius: 3px; }"
            "QSlider::handle:horizontal { width: 14px; margin: -4px 0; "
            "background: #3498db; border-radius: 7px; }"
            "QSlider::sub-page:horizontal { background: #3498db; border-radius: 3px; }"
        )
        btn_layout.addWidget(self.slider_threshold)

        self.spin_threshold = QtWidgets.QSpinBox()
        self.spin_threshold.setRange(0, 100)
        self.spin_threshold.setValue(60)
        self.spin_threshold.setFixedWidth(50)
        btn_layout.addWidget(self.spin_threshold)

        # Link slider <-> spinbox
        self.slider_threshold.valueChanged.connect(self.spin_threshold.setValue)
        self.spin_threshold.valueChanged.connect(self.slider_threshold.setValue)
        self.spin_threshold.valueChanged.connect(self._apply_threshold)

        btn_layout.addStretch()

        # Selected count badge
        self.lbl_selected_count = QtWidgets.QLabel("0 selected")
        self.lbl_selected_count.setStyleSheet(
            "background: #3498db; color: white; padding: 2px 8px; "
            "border-radius: 10px; font-size: 11px; font-weight: bold;")
        btn_layout.addWidget(self.lbl_selected_count)

        layout.addLayout(btn_layout)

        # ── Inline Settings Bar ──
        settings_bar = QtWidgets.QHBoxLayout()
        settings_bar.setSpacing(8)

        self.chk_ai = QtWidgets.QCheckBox("Enable AI")
        self.chk_ai.setStyleSheet("font-size: 11px;")
        settings_bar.addWidget(self.chk_ai)

        self.lbl_model_badge = QtWidgets.QLabel("")
        self.lbl_model_badge.setStyleSheet(
            "background: #ecf0f1; border: 1px solid #bdc3c7; border-radius: 3px; "
            "padding: 1px 6px; font-size: 11px; color: #555;")
        settings_bar.addWidget(self.lbl_model_badge)

        btn_reanalyze = QtWidgets.QPushButton("Re-analyze")
        btn_reanalyze.setStyleSheet(
            "QPushButton { background: #2980b9; color: white; padding: 3px 10px; "
            "border-radius: 3px; font-size: 11px; }"
            "QPushButton:hover { background: #3498db; }")
        btn_reanalyze.clicked.connect(self._reanalyze)
        settings_bar.addWidget(btn_reanalyze)

        btn_config = QtWidgets.QPushButton("Ollama Settings...")
        btn_config.setStyleSheet(
            "QPushButton { padding: 3px 10px; border-radius: 3px; "
            "font-size: 11px; }")
        btn_config.clicked.connect(self._open_config_dialog)
        settings_bar.addWidget(btn_config)

        settings_bar.addStretch()
        layout.addLayout(settings_bar)

        # ── Progress Bar ──
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedHeight(4)
        self.progress.setStyleSheet(
            "QProgressBar { border: none; background: transparent; }"
            "QProgressBar::chunk { background: #3498db; }")
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # ── Status Bar ──
        status_layout = QtWidgets.QHBoxLayout()
        status_layout.setContentsMargins(0, 4, 0, 0)

        self.lbl_statusbar = QtWidgets.QLabel("")
        self.lbl_statusbar.setStyleSheet("color: #888; font-size: 11px;")
        status_layout.addWidget(self.lbl_statusbar)
        status_layout.addStretch()

        btn_create = QtWidgets.QPushButton("  Create Sketches")
        btn_create.setDefault(True)
        btn_create.setStyleSheet(
            "QPushButton { background: #27ae60; color: white; padding: 6px 20px; "
            "border-radius: 4px; font-weight: bold; font-size: 13px; }"
            "QPushButton:hover { background: #2ecc71; }"
            "QPushButton:disabled { background: #bdc3c7; }")
        btn_create.clicked.connect(self.accept)
        status_layout.addWidget(btn_create)

        btn_cancel = QtWidgets.QPushButton("Cancel")
        btn_cancel.setStyleSheet(
            "QPushButton { padding: 6px 16px; border-radius: 4px; "
            "font-size: 13px; }")
        btn_cancel.clicked.connect(self.reject)
        status_layout.addWidget(btn_cancel)

        layout.addLayout(status_layout)

        # Load preferences
        prefs = get_preferences()
        self.chk_ai.setChecked(prefs["enabled"])
        self._update_model_badge(prefs)

        self._load_models_async(prefs)

    # ── Config dialog ────────────────────────────────────────────

    def _open_config_dialog(self):
        from .ollamaConfigDialog import OllamaConfigDialog
        dialog = OllamaConfigDialog(self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            # Reload preferences after config changes
            prefs = get_preferences()
            self.chk_ai.setChecked(prefs["enabled"])
            self._update_model_badge(prefs)

    def _update_model_badge(self, prefs=None):
        if prefs is None:
            prefs = get_preferences()
        self.lbl_model_badge.setText(
            f"Model: {prefs['model']}  |  T={prefs.get('temperature', 0.3):.1f}")

    # ── Model loading ─────────────────────────────────────────────

    def _load_models_async(self, prefs):
        """Check connection status in background on dialog open."""
        def _load():
            available = check_ollama_available(prefs)
            if available:
                models = list_ollama_models(prefs)
                count = len(models)
            else:
                count = 0
            # Just update status — model selection is in config dialog
            self._sig_connection_checked.emit(available, count)
        t = threading.Thread(target=_load, daemon=True)
        t.start()

    def _on_connection_checked(self, available, model_count):
        if available:
            self._set_status(
                f"Ollama online ({model_count} models)", "#27ae60")
        else:
            self._set_status(
                "Ollama offline \u2014 algorithmic scoring only", "#e67e22")

    # ── Analysis ──────────────────────────────────────────────────

    def _run_analysis(self):
        self.analysis = full_analysis(self.shape)
        self._populate_filters()
        self._populate_table()
        self._apply_threshold(self.spin_threshold.value())
        self._update_summary()
        self._set_status("Algorithmic analysis complete. Click 'Analyze with AI' for AI scoring.", "#888")

    def _on_analyze_ai_clicked(self):
        if not self.analysis:
            return
        if not self.chk_ai.isChecked():
            self.chk_ai.setChecked(True)
        self._start_ollama_query()

    def _start_ollama_query(self):
        prefs = get_preferences()

        if not check_ollama_available(prefs):
            self._set_status(
                "Ollama unavailable \u2014 using algorithmic results only", "#e67e22")
            return

        self.btn_analyze_ai.setEnabled(False)
        self._set_status(
            f"Querying Ollama ({prefs['model']})...", "#2980b9")
        self.progress.setVisible(True)

        selected_indices = set(self.get_selected_faces())
        if selected_indices:
            faces = [fi for fi in self.analysis.faces
                     if fi.index in selected_indices]
        else:
            faces = self.analysis.faces
        prompt = build_prompt(faces, self.analysis.groups)
        context = self.txt_ai_context.text().strip()
        if context:
            prompt = f"Additional context about this part: {context}\n\n{prompt}"
        self.worker = OllamaWorker(prompt, prefs)
        self.worker.finished.connect(self._on_ollama_finished)
        self.worker.error.connect(self._on_ollama_error)
        self.worker.raw_response.connect(self._on_ollama_raw)
        self.txt_ollama_log.clear()
        self.worker.start()

    def _on_ollama_finished(self, result):
        self.progress.setVisible(False)
        self.btn_analyze_ai.setEnabled(True)
        if result:
            strategy = apply_ollama_annotations(
                self.analysis.faces, result)
            self.analysis.ai_description = result.get("part_description", "")
            self.analysis.ai_strategy = strategy

            self.lbl_description.setText(self.analysis.ai_description or "(no description)")
            self.lbl_strategy.setText(strategy or "(no strategy)")
            prefs = get_preferences()
            self._set_status(
                f"Ollama analysis complete ({prefs['model']})",
                "#27ae60")

            self._populate_filters()
            self._populate_table()
            self._apply_threshold(self.spin_threshold.value())
        else:
            self._set_status("Ollama returned no results", "#e74c3c")

    def _on_ollama_raw(self, text):
        cursor = self.txt_ollama_log.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertText(text)
        self.txt_ollama_log.setTextCursor(cursor)
        self.txt_ollama_log.ensureCursorVisible()

    def _on_ollama_error(self, error_msg):
        self.progress.setVisible(False)
        self.btn_analyze_ai.setEnabled(True)
        self._set_status(f"Ollama error: {error_msg}", "#e74c3c")

    def _set_status(self, text, color="#888"):
        self.lbl_status.setText(text)
        self.lbl_status.setStyleSheet(f"color: {color}; font-size: 11px;")
        self.lbl_statusbar.setText(text)

    # ── Filters ───────────────────────────────────────────────────

    def _populate_filters(self):
        if not self.analysis:
            return

        # Type filter
        current_type = self.combo_type_filter.currentText()
        self.combo_type_filter.blockSignals(True)
        self.combo_type_filter.clear()
        self.combo_type_filter.addItem("All")
        types = sorted({fi.surface_type for fi in self.analysis.faces})
        for t in types:
            icon = _TYPE_ICONS.get(t, "")
            count = sum(1 for fi in self.analysis.faces if fi.surface_type == t)
            self.combo_type_filter.addItem(f"{icon} {t} ({count})")
        idx = self.combo_type_filter.findText(current_type)
        if idx >= 0:
            self.combo_type_filter.setCurrentIndex(idx)
        self.combo_type_filter.blockSignals(False)

        # Group filter
        current_group = self.combo_group_filter.currentText()
        self.combo_group_filter.blockSignals(True)
        self.combo_group_filter.clear()
        self.combo_group_filter.addItem("All")
        groups = sorted({fi.ai_group for fi in self.analysis.faces if fi.ai_group})
        for g in groups:
            count = sum(1 for fi in self.analysis.faces if fi.ai_group == g)
            self.combo_group_filter.addItem(f"{g} ({count})")
        # Also add normal-based groups
        for g, indices in self.analysis.groups.items():
            self.combo_group_filter.addItem(f"{g} ({len(indices)})")
        idx = self.combo_group_filter.findText(current_group)
        if idx >= 0:
            self.combo_group_filter.setCurrentIndex(idx)
        self.combo_group_filter.blockSignals(False)

    def _on_filter_changed(self, _=None):
        self._apply_visibility()

    def _face_matches_filter(self, fi):
        """Check if a FaceInfo passes current filters."""
        # Search text
        search = self.txt_search.text().strip().lower()
        if search:
            searchable = f"{fi.ai_name} {fi.ai_group} {fi.surface_type} Face {fi.index}".lower()
            if search not in searchable:
                return False

        # Type filter
        type_text = self.combo_type_filter.currentText()
        if type_text != "All":
            # Extract type name from "icon Type (count)" format
            type_name = type_text.split("(")[0].strip()
            for icon in _TYPE_ICONS.values():
                type_name = type_name.replace(icon, "").strip()
            if fi.surface_type != type_name:
                return False

        # Group filter
        group_text = self.combo_group_filter.currentText()
        if group_text != "All":
            group_name = group_text.split("(")[0].strip()
            # Check AI group match
            if fi.ai_group == group_name:
                return True
            # Check normal-based groups
            groups = (self.analysis.groups if self.analysis else None) or {}
            for g, indices in groups.items():
                if g == group_name and fi.index in indices:
                    return True
            return False

        return True

    def _apply_visibility(self):
        """Show/hide table rows based on filters."""
        if not self.analysis:
            return
        face_map = {fi.index: fi for fi in self.analysis.faces}
        visible_count = 0
        for row in range(self.table.rowCount()):
            score_item = self.table.item(row, self.COL_SCORE)
            if not score_item:
                continue
            idx = int(score_item.data(QtCore.Qt.UserRole))
            fi = face_map.get(idx)
            if fi and self._face_matches_filter(fi):
                self.table.setRowHidden(row, False)
                visible_count += 1
            else:
                self.table.setRowHidden(row, True)
        self.lbl_summary.setText(
            f"Showing {visible_count} of {len(self.analysis.faces)} faces")

    # ── Table ─────────────────────────────────────────────────────

    def _populate_table(self):
        if not self.analysis:
            return

        # Save checkbox states
        checked = set()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, self.COL_CHECK)
            if item and item.checkState() == QtCore.Qt.Checked:
                score_item = self.table.item(row, self.COL_SCORE)
                if score_item:
                    checked.add(int(score_item.data(QtCore.Qt.UserRole)))

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.analysis.faces))

        for row, fi in enumerate(self.analysis.faces):
            # Checkbox
            chk = QtWidgets.QTableWidgetItem()
            chk.setFlags(chk.flags() | QtCore.Qt.ItemIsUserCheckable)
            chk.setCheckState(
                QtCore.Qt.Checked if fi.index in checked
                else QtCore.Qt.Unchecked)
            self.table.setItem(row, self.COL_CHECK, chk)

            # Index
            idx_item = QtWidgets.QTableWidgetItem()
            idx_item.setData(QtCore.Qt.DisplayRole, fi.index)
            idx_item.setTextAlignment(QtCore.Qt.AlignCenter)
            idx_item.setForeground(QtGui.QColor("#888"))
            self.table.setItem(row, self.COL_INDEX, idx_item)

            # Score — use cell widget for color bar
            score_item = QtWidgets.QTableWidgetItem()
            score_item.setData(QtCore.Qt.DisplayRole, int(fi.algo_score))
            score_item.setData(QtCore.Qt.UserRole, fi.index)
            # Color the background with gradient
            bg = _score_color(fi.algo_score)
            bg.setAlpha(60)
            score_item.setBackground(bg)
            score_item.setTextAlignment(QtCore.Qt.AlignCenter)
            self.table.setItem(row, self.COL_SCORE, score_item)

            # AI Name — bold if AI-recommended
            name_item = QtWidgets.QTableWidgetItem(fi.ai_name or f"Face {fi.index}")
            if fi.ai_recommended:
                font = name_item.font()
                font.setBold(True)
                name_item.setFont(font)
                name_item.setForeground(QtGui.QColor("#d35400"))
            self.table.setItem(row, self.COL_NAME, name_item)

            # Group
            group_text = fi.ai_group or ""
            if not group_text:
                # Fallback to normal-based group
                for g, indices in self.analysis.groups.items():
                    if fi.index in indices:
                        group_text = g
                        break
            self.table.setItem(row, self.COL_GROUP,
                QtWidgets.QTableWidgetItem(group_text or "\u2014"))

            # Surface type with icon
            icon = _TYPE_ICONS.get(fi.surface_type, "")
            type_item = QtWidgets.QTableWidgetItem(f"{icon} {fi.surface_type}")
            self.table.setItem(row, self.COL_TYPE, type_item)

            # Area
            area_item = QtWidgets.QTableWidgetItem()
            area_item.setData(QtCore.Qt.DisplayRole, round(fi.area, 1))
            area_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            self.table.setItem(row, self.COL_AREA, area_item)

            # Edges
            edge_item = QtWidgets.QTableWidgetItem()
            edge_item.setData(QtCore.Qt.DisplayRole, fi.edge_count)
            edge_item.setTextAlignment(QtCore.Qt.AlignCenter)
            self.table.setItem(row, self.COL_EDGES, edge_item)

            # Normal direction
            nx, ny, nz = fi.normal
            normal_item = QtWidgets.QTableWidgetItem(
                f"({nx:.2f}, {ny:.2f}, {nz:.2f})")
            normal_item.setForeground(QtGui.QColor("#999"))
            self.table.setItem(row, self.COL_NORMAL, normal_item)

        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()

        # Re-apply filters
        self._apply_visibility()
        self._update_summary()

    def _update_summary(self):
        if not self.analysis:
            return
        total = len(self.analysis.faces)
        checked = len(self.get_selected_faces())
        self.lbl_selected_count.setText(f"{checked} selected")

        # Update statusbar with face count breakdown
        types = {}
        for fi in self.analysis.faces:
            types[fi.surface_type] = types.get(fi.surface_type, 0) + 1
        parts = [f"{count} {t}" for t, count in sorted(types.items())]
        self.lbl_summary.setText(f"{total} faces: {', '.join(parts)}")

    # ── Row selection → 3D view ─────────────────────────────────

    def _on_table_selection_changed(self):
        if not self.obj:
            return
        try:
            import FreeCADGui
            FreeCADGui.Selection.clearSelection()
            rows = set(idx.row() for idx in self.table.selectedIndexes())
            for row in rows:
                score_item = self.table.item(row, self.COL_SCORE)
                if score_item:
                    face_idx = int(score_item.data(QtCore.Qt.UserRole))
                    FreeCADGui.Selection.addSelection(
                        self.obj, f"Face{face_idx + 1}")
        except Exception:
            pass

    # ── Hover + Double-click ──────────────────────────────────────

    def _on_hover(self, row, column):
        if not self.obj:
            return
        try:
            import FreeCADGui
            score_item = self.table.item(row, self.COL_SCORE)
            if score_item:
                face_idx = int(score_item.data(QtCore.Qt.UserRole))
                if self._prev_selection is not None:
                    FreeCADGui.Selection.removeSelection(
                        self.obj, f"Face{self._prev_selection + 1}")
                FreeCADGui.Selection.addSelection(
                    self.obj, f"Face{face_idx + 1}")
                self._prev_selection = face_idx
        except Exception:
            pass

    def _on_double_click(self, row, column):
        """Double-click a row to zoom/fit the face in 3D view."""
        if not self.obj:
            return
        try:
            import FreeCADGui
            score_item = self.table.item(row, self.COL_SCORE)
            if score_item:
                face_idx = int(score_item.data(QtCore.Qt.UserRole))
                FreeCADGui.Selection.clearSelection()
                FreeCADGui.Selection.addSelection(
                    self.obj, f"Face{face_idx + 1}")
                FreeCADGui.SendMsgToActiveView("ViewSelection")
        except Exception:
            pass

    # ── Context Menu ──────────────────────────────────────────────

    def _show_context_menu(self, pos):
        if not self.analysis:
            return
        row = self.table.rowAt(pos.y())
        if row < 0:
            return

        score_item = self.table.item(row, self.COL_SCORE)
        if not score_item:
            return
        face_idx = int(score_item.data(QtCore.Qt.UserRole))
        face_map = {fi.index: fi for fi in self.analysis.faces}
        fi = face_map.get(face_idx)
        if not fi:
            return

        menu = QtWidgets.QMenu(self)

        # Select by same type
        act_type = menu.addAction(
            f"Select all {fi.surface_type} faces")
        act_type.triggered.connect(
            lambda: self._select_by_type(fi.surface_type))

        # Select by same group
        group_text = self.table.item(row, self.COL_GROUP)
        if group_text and group_text.text() != "\u2014":
            act_group = menu.addAction(
                f"Select all in \"{group_text.text()}\"")
            act_group.triggered.connect(
                lambda g=group_text.text(): self._select_by_group(g))

        menu.addSeparator()

        # Select similar area (within 20%)
        act_area = menu.addAction("Select faces with similar area")
        act_area.triggered.connect(
            lambda: self._select_similar_area(fi.area))

        # Select similar edge count
        act_edges = menu.addAction(
            f"Select faces with {fi.edge_count} edges")
        act_edges.triggered.connect(
            lambda: self._select_by_edge_count(fi.edge_count))

        menu.addSeparator()

        # Deselect this face
        act_deselect = menu.addAction("Deselect this face")
        act_deselect.triggered.connect(
            lambda: self.table.item(row, self.COL_CHECK).setCheckState(
                QtCore.Qt.Unchecked))

        menu.exec_(self.table.mapToGlobal(pos))

    def _select_by_type(self, surface_type):
        face_map = {fi.index: fi for fi in self.analysis.faces}
        for row in range(self.table.rowCount()):
            score_item = self.table.item(row, self.COL_SCORE)
            if not score_item:
                continue
            idx = int(score_item.data(QtCore.Qt.UserRole))
            fi = face_map.get(idx)
            if fi and fi.surface_type == surface_type:
                self.table.item(row, self.COL_CHECK).setCheckState(
                    QtCore.Qt.Checked)
        self._update_summary()

    def _select_by_group(self, group_name):
        face_map = {fi.index: fi for fi in self.analysis.faces}
        for row in range(self.table.rowCount()):
            score_item = self.table.item(row, self.COL_SCORE)
            if not score_item:
                continue
            idx = int(score_item.data(QtCore.Qt.UserRole))
            fi = face_map.get(idx)
            group_item = self.table.item(row, self.COL_GROUP)
            if group_item and group_item.text() == group_name:
                self.table.item(row, self.COL_CHECK).setCheckState(
                    QtCore.Qt.Checked)
        self._update_summary()

    def _select_similar_area(self, target_area, tolerance=0.2):
        face_map = {fi.index: fi for fi in self.analysis.faces}
        for row in range(self.table.rowCount()):
            score_item = self.table.item(row, self.COL_SCORE)
            if not score_item:
                continue
            idx = int(score_item.data(QtCore.Qt.UserRole))
            fi = face_map.get(idx)
            if fi and abs(fi.area - target_area) / max(target_area, 1e-10) < tolerance:
                self.table.item(row, self.COL_CHECK).setCheckState(
                    QtCore.Qt.Checked)
        self._update_summary()

    def _select_by_edge_count(self, edge_count):
        face_map = {fi.index: fi for fi in self.analysis.faces}
        for row in range(self.table.rowCount()):
            score_item = self.table.item(row, self.COL_SCORE)
            if not score_item:
                continue
            idx = int(score_item.data(QtCore.Qt.UserRole))
            fi = face_map.get(idx)
            if fi and fi.edge_count == edge_count:
                self.table.item(row, self.COL_CHECK).setCheckState(
                    QtCore.Qt.Checked)
        self._update_summary()

    # ── Selection Actions ─────────────────────────────────────────

    def _select_all(self):
        for row in range(self.table.rowCount()):
            if not self.table.isRowHidden(row):
                self.table.item(row, self.COL_CHECK).setCheckState(
                    QtCore.Qt.Checked)
        self._update_summary()

    def _deselect_all(self):
        for row in range(self.table.rowCount()):
            self.table.item(row, self.COL_CHECK).setCheckState(
                QtCore.Qt.Unchecked)
        self._update_summary()

    def _invert_selection(self):
        for row in range(self.table.rowCount()):
            if self.table.isRowHidden(row):
                continue
            item = self.table.item(row, self.COL_CHECK)
            new_state = (QtCore.Qt.Unchecked
                        if item.checkState() == QtCore.Qt.Checked
                        else QtCore.Qt.Checked)
            item.setCheckState(new_state)
        self._update_summary()

    def _get_highlighted_rows(self):
        """Get unique row indices from the table's current selection."""
        return sorted(set(idx.row() for idx in self.table.selectedIndexes()))

    def _check_highlighted(self):
        for row in self._get_highlighted_rows():
            self.table.item(row, self.COL_CHECK).setCheckState(
                QtCore.Qt.Checked)
        self._update_summary()

    def _uncheck_highlighted(self):
        for row in self._get_highlighted_rows():
            self.table.item(row, self.COL_CHECK).setCheckState(
                QtCore.Qt.Unchecked)
        self._update_summary()

    def _toggle_highlighted(self):
        for row in self._get_highlighted_rows():
            item = self.table.item(row, self.COL_CHECK)
            new_state = (QtCore.Qt.Unchecked
                        if item.checkState() == QtCore.Qt.Checked
                        else QtCore.Qt.Checked)
            item.setCheckState(new_state)
        self._update_summary()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Space and self._get_highlighted_rows():
            self._toggle_highlighted()
            return
        super().keyPressEvent(event)

    def _select_ai_recommended(self):
        if not self.analysis:
            return
        recommended = {fi.index for fi in self.analysis.faces
                      if fi.ai_recommended}
        if not recommended:
            self._set_status("No AI recommendations available yet", "#e67e22")
            return
        for row in range(self.table.rowCount()):
            score_item = self.table.item(row, self.COL_SCORE)
            if score_item:
                idx = int(score_item.data(QtCore.Qt.UserRole))
                state = (QtCore.Qt.Checked if idx in recommended
                        else QtCore.Qt.Unchecked)
                self.table.item(row, self.COL_CHECK).setCheckState(state)
        self._update_summary()
        self._set_status(
            f"Selected {len(recommended)} AI-recommended face(s)", "#27ae60")

    def _apply_threshold(self, value):
        if not self.analysis:
            return
        for row in range(self.table.rowCount()):
            score_item = self.table.item(row, self.COL_SCORE)
            if score_item:
                score = int(score_item.data(QtCore.Qt.DisplayRole))
                state = (QtCore.Qt.Checked if score >= value
                        else QtCore.Qt.Unchecked)
                self.table.item(row, self.COL_CHECK).setCheckState(state)
        self._update_summary()

    def _reanalyze(self):
        prefs = get_preferences()
        prefs["enabled"] = self.chk_ai.isChecked()
        save_preferences(prefs)
        self._update_model_badge(prefs)
        self._run_analysis()

    # ── Result ────────────────────────────────────────────────────

    def get_selected_faces(self):
        selected = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, self.COL_CHECK)
            if item and item.checkState() == QtCore.Qt.Checked:
                score_item = self.table.item(row, self.COL_SCORE)
                if score_item:
                    selected.append(int(score_item.data(QtCore.Qt.UserRole)))
        return selected
