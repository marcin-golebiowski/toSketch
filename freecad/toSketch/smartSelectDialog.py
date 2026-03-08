# SPDX-License-Identifier: GPL-2.0-or-later
"""PySide2 dialog for AI-assisted smart face selection."""
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


class OllamaWorker(QtCore.QThread):
    """Background thread for Ollama queries."""
    finished = QtCore.Signal(object)  # dict or None
    error = QtCore.Signal(str)

    def __init__(self, prompt, prefs, parent=None):
        super().__init__(parent)
        self.prompt = prompt
        self.prefs = prefs

    def run(self):
        try:
            result = query_ollama(self.prompt, self.prefs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class SmartSelectDialog(QtWidgets.QDialog):
    """Dialog for AI-assisted face selection from STEP shapes."""

    def __init__(self, shape, obj=None, parent=None):
        super().__init__(parent)
        self.shape = shape
        self.obj = obj  # FreeCAD object for 3D highlighting
        self.analysis = None
        self.worker = None
        self._prev_selection = None

        self.setWindowTitle("Smart Face Selection")
        self.setMinimumSize(900, 650)
        self._build_ui()
        self._run_analysis()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # ── AI Analysis Panel ──
        ai_group = QtWidgets.QGroupBox("AI Analysis")
        ai_layout = QtWidgets.QVBoxLayout(ai_group)

        self.lbl_description = QtWidgets.QLabel("Part: (analyzing...)")
        self.lbl_strategy = QtWidgets.QLabel("Strategy: —")
        self.lbl_status = QtWidgets.QLabel("Status: checking Ollama...")

        ai_layout.addWidget(self.lbl_description)
        ai_layout.addWidget(self.lbl_strategy)
        ai_layout.addWidget(self.lbl_status)
        layout.addWidget(ai_group)

        # ── Face Table ──
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "", "Score", "AI Name", "Group", "Type", "Area", "Edges"
        ])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.cellEntered.connect(self._on_hover)
        self.table.setMouseTracking(True)
        layout.addWidget(self.table)

        # ── Button Row ──
        btn_layout = QtWidgets.QHBoxLayout()

        btn_all = QtWidgets.QPushButton("Select All")
        btn_all.clicked.connect(self._select_all)
        btn_layout.addWidget(btn_all)

        btn_none = QtWidgets.QPushButton("Deselect All")
        btn_none.clicked.connect(self._deselect_all)
        btn_layout.addWidget(btn_none)

        btn_ai = QtWidgets.QPushButton("AI Recommended")
        btn_ai.clicked.connect(self._select_ai_recommended)
        btn_layout.addWidget(btn_ai)

        btn_layout.addWidget(QtWidgets.QLabel("Threshold:"))
        self.spin_threshold = QtWidgets.QSpinBox()
        self.spin_threshold.setRange(0, 100)
        self.spin_threshold.setValue(60)
        self.spin_threshold.valueChanged.connect(self._apply_threshold)
        btn_layout.addWidget(self.spin_threshold)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # ── Settings Panel ──
        settings_group = QtWidgets.QGroupBox("Settings")
        settings_layout = QtWidgets.QHBoxLayout(settings_group)

        settings_layout.addWidget(QtWidgets.QLabel("Ollama Model:"))
        self.combo_model = QtWidgets.QComboBox()
        self.combo_model.setEditable(True)
        self.combo_model.setMinimumWidth(150)
        settings_layout.addWidget(self.combo_model)

        settings_layout.addWidget(QtWidgets.QLabel("URL:"))
        self.txt_url = QtWidgets.QLineEdit()
        self.txt_url.setMinimumWidth(200)
        settings_layout.addWidget(self.txt_url)

        self.chk_ai = QtWidgets.QCheckBox("Enable AI")
        settings_layout.addWidget(self.chk_ai)

        btn_reanalyze = QtWidgets.QPushButton("Re-analyze")
        btn_reanalyze.clicked.connect(self._reanalyze)
        settings_layout.addWidget(btn_reanalyze)

        settings_layout.addStretch()
        layout.addWidget(settings_group)

        # ── Progress Bar ──
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 0)  # indeterminate
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # ── Dialog Buttons ──
        dialog_btns = QtWidgets.QHBoxLayout()
        dialog_btns.addStretch()

        btn_create = QtWidgets.QPushButton("Create Sketches")
        btn_create.setDefault(True)
        btn_create.clicked.connect(self.accept)
        dialog_btns.addWidget(btn_create)

        btn_cancel = QtWidgets.QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        dialog_btns.addWidget(btn_cancel)

        layout.addLayout(dialog_btns)

        # Load preferences
        prefs = get_preferences()
        self.txt_url.setText(prefs["url"])
        self.combo_model.addItem(prefs["model"])
        self.chk_ai.setChecked(prefs["enabled"])

        # Populate model list in background
        self._load_models_async(prefs)

    def _load_models_async(self, prefs):
        """Load available Ollama models in a background thread."""
        def _load():
            models = list_ollama_models(prefs)
            if models:
                # Schedule UI update on main thread
                QtCore.QMetaObject.invokeMethod(
                    self, "_update_model_list",
                    QtCore.Qt.QueuedConnection,
                    QtCore.Q_ARG(list, models))
        t = threading.Thread(target=_load, daemon=True)
        t.start()

    @QtCore.Slot(list)
    def _update_model_list(self, models):
        current = self.combo_model.currentText()
        self.combo_model.clear()
        for m in models:
            self.combo_model.addItem(m)
        idx = self.combo_model.findText(current)
        if idx >= 0:
            self.combo_model.setCurrentIndex(idx)
        else:
            self.combo_model.addItem(current)
            self.combo_model.setCurrentIndex(self.combo_model.count() - 1)

    def _run_analysis(self):
        """Run algorithmic analysis, then optionally query Ollama."""
        self.analysis = full_analysis(self.shape)
        self._populate_table()
        self._apply_threshold(self.spin_threshold.value())

        if self.chk_ai.isChecked():
            self._start_ollama_query()
        else:
            self.lbl_status.setText("Status: AI disabled")

    def _start_ollama_query(self):
        """Query Ollama in a background thread."""
        prefs = {
            "url": self.txt_url.text(),
            "model": self.combo_model.currentText(),
            "timeout": get_preferences().get("timeout", 60),
            "enabled": True,
        }

        if not check_ollama_available(prefs):
            self.lbl_status.setText(
                "Status: Ollama unavailable (algorithmic results only)")
            return

        self.lbl_status.setText(
            f"Status: Querying Ollama ({prefs['model']})...")
        self.progress.setVisible(True)

        prompt = build_prompt(self.analysis.faces, self.analysis.groups)
        self.worker = OllamaWorker(prompt, prefs)
        self.worker.finished.connect(self._on_ollama_finished)
        self.worker.error.connect(self._on_ollama_error)
        self.worker.start()

    def _on_ollama_finished(self, result):
        self.progress.setVisible(False)
        if result:
            strategy = apply_ollama_annotations(
                self.analysis.faces, result)
            self.analysis.ai_description = result.get(
                "part_description", "")
            self.analysis.ai_strategy = strategy

            self.lbl_description.setText(
                f"Part: {self.analysis.ai_description}")
            self.lbl_strategy.setText(
                f"Strategy: {strategy}")
            self.lbl_status.setText(
                f"Status: Ollama analysis complete "
                f"({self.combo_model.currentText()})")

            self._populate_table()
            self._apply_threshold(self.spin_threshold.value())
        else:
            self.lbl_status.setText(
                "Status: Ollama returned no results")

    def _on_ollama_error(self, error_msg):
        self.progress.setVisible(False)
        self.lbl_status.setText(f"Status: Ollama error — {error_msg}")

    def _populate_table(self):
        """Fill the table from self.analysis.faces."""
        if not self.analysis:
            return

        # Save checkbox states before repopulating
        checked = set()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.checkState() == QtCore.Qt.Checked:
                idx_item = self.table.item(row, 1)
                if idx_item:
                    checked.add(int(idx_item.data(QtCore.Qt.UserRole)))

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.analysis.faces))

        for row, fi in enumerate(self.analysis.faces):
            # Checkbox column
            chk = QtWidgets.QTableWidgetItem()
            chk.setFlags(chk.flags() | QtCore.Qt.ItemIsUserCheckable)
            if fi.index in checked:
                chk.setCheckState(QtCore.Qt.Checked)
            else:
                chk.setCheckState(QtCore.Qt.Unchecked)
            self.table.setItem(row, 0, chk)

            # Score (sortable as number)
            score_item = QtWidgets.QTableWidgetItem()
            score_item.setData(QtCore.Qt.DisplayRole, int(fi.algo_score))
            score_item.setData(QtCore.Qt.UserRole, fi.index)
            self.table.setItem(row, 1, score_item)

            # AI Name
            self.table.setItem(row, 2,
                QtWidgets.QTableWidgetItem(fi.ai_name or "—"))

            # Group
            self.table.setItem(row, 3,
                QtWidgets.QTableWidgetItem(fi.ai_group or "—"))

            # Surface type
            self.table.setItem(row, 4,
                QtWidgets.QTableWidgetItem(fi.surface_type))

            # Area
            area_item = QtWidgets.QTableWidgetItem()
            area_item.setData(QtCore.Qt.DisplayRole, round(fi.area, 1))
            self.table.setItem(row, 5, area_item)

            # Edge count
            edge_item = QtWidgets.QTableWidgetItem()
            edge_item.setData(QtCore.Qt.DisplayRole, fi.edge_count)
            self.table.setItem(row, 6, edge_item)

        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()

    def _on_hover(self, row, column):
        """Highlight face in 3D view on hover."""
        if not self.obj:
            return
        try:
            import FreeCADGui
            score_item = self.table.item(row, 1)
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

    def _select_all(self):
        for row in range(self.table.rowCount()):
            self.table.item(row, 0).setCheckState(QtCore.Qt.Checked)

    def _deselect_all(self):
        for row in range(self.table.rowCount()):
            self.table.item(row, 0).setCheckState(QtCore.Qt.Unchecked)

    def _select_ai_recommended(self):
        """Check only faces that Ollama recommended."""
        if not self.analysis:
            return
        recommended = {fi.index for fi in self.analysis.faces
                      if fi.ai_recommended}
        for row in range(self.table.rowCount()):
            score_item = self.table.item(row, 1)
            if score_item:
                idx = int(score_item.data(QtCore.Qt.UserRole))
                state = (QtCore.Qt.Checked if idx in recommended
                        else QtCore.Qt.Unchecked)
                self.table.item(row, 0).setCheckState(state)

    def _apply_threshold(self, value):
        """Check faces with score >= threshold, uncheck others."""
        if not self.analysis:
            return
        for row in range(self.table.rowCount()):
            score_item = self.table.item(row, 1)
            if score_item:
                score = int(score_item.data(QtCore.Qt.DisplayRole))
                state = (QtCore.Qt.Checked if score >= value
                        else QtCore.Qt.Unchecked)
                self.table.item(row, 0).setCheckState(state)

    def _reanalyze(self):
        """Re-run analysis with current settings."""
        # Save preferences
        prefs = {
            "url": self.txt_url.text(),
            "model": self.combo_model.currentText(),
            "enabled": self.chk_ai.isChecked(),
        }
        save_preferences(prefs)
        self._run_analysis()

    def get_selected_faces(self):
        """Return list of face indices that are checked."""
        selected = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.checkState() == QtCore.Qt.Checked:
                score_item = self.table.item(row, 1)
                if score_item:
                    selected.append(int(score_item.data(QtCore.Qt.UserRole)))
        return selected
