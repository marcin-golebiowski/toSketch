# SPDX-License-Identifier: GPL-2.0-or-later
"""Dedicated Ollama configuration dialog for toSketch workbench."""
import threading

from PySide import QtCore, QtGui
try:
    from PySide import QtWidgets
except ImportError:
    QtWidgets = QtGui

from .ollamaClient import (
    get_preferences, save_preferences, _DEFAULTS,
    check_ollama_available, list_ollama_models, get_model_info,
    query_ollama,
)


class OllamaConfigDialog(QtWidgets.QDialog):
    """Full configuration dialog for Ollama AI integration."""

    _sig_connection_result = QtCore.Signal(bool, int)
    _sig_models_loaded = QtCore.Signal(list)
    _sig_model_info_loaded = QtCore.Signal(dict)
    _sig_test_result = QtCore.Signal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ollama AI Configuration")
        self.setMinimumSize(600, 520)
        self._model_details = {}
        self._model_details_lock = threading.Lock()
        self._sig_connection_result.connect(self._on_connection_result)
        self._sig_models_loaded.connect(self._on_models_loaded)
        self._sig_model_info_loaded.connect(self._on_model_info_loaded)
        self._sig_test_result.connect(self._on_test_result)
        self._build_ui()
        self._load_preferences()
        self._check_connection()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # ── Connection ────────────────────────────────────────────
        conn_group = QtWidgets.QGroupBox("Connection")
        conn_group.setStyleSheet(
            "QGroupBox { font-weight: bold; padding-top: 16px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 8px; }")
        conn_layout = QtWidgets.QGridLayout(conn_group)
        conn_layout.setSpacing(8)

        # Status indicator
        self.lbl_status_icon = QtWidgets.QLabel()
        self.lbl_status_icon.setFixedSize(16, 16)
        self.lbl_status_text = QtWidgets.QLabel("Checking...")
        self.lbl_status_text.setStyleSheet("font-size: 12px;")
        status_row = QtWidgets.QHBoxLayout()
        status_row.addWidget(self.lbl_status_icon)
        status_row.addWidget(self.lbl_status_text)
        status_row.addStretch()

        btn_test = QtWidgets.QPushButton("Test Connection")
        btn_test.setStyleSheet(
            "QPushButton { padding: 4px 12px; }")
        btn_test.clicked.connect(self._check_connection)
        status_row.addWidget(btn_test)
        conn_layout.addLayout(status_row, 0, 0, 1, 2)

        # URL
        conn_layout.addWidget(QtWidgets.QLabel("Server URL:"), 1, 0)
        self.txt_url = QtWidgets.QLineEdit()
        self.txt_url.setPlaceholderText("http://localhost:11434")
        conn_layout.addWidget(self.txt_url, 1, 1)

        # Timeout
        conn_layout.addWidget(QtWidgets.QLabel("Timeout (seconds):"), 2, 0)
        self.spin_timeout = QtWidgets.QSpinBox()
        self.spin_timeout.setRange(10, 600)
        self.spin_timeout.setSuffix("s")
        self.spin_timeout.setToolTip(
            "Maximum time to wait for Ollama response")
        conn_layout.addWidget(self.spin_timeout, 2, 1)

        # Enable AI
        self.chk_enabled = QtWidgets.QCheckBox(
            "Enable AI-assisted analysis")
        self.chk_enabled.setToolTip(
            "When disabled, Smart Face Selection uses algorithmic scoring only")
        conn_layout.addWidget(self.chk_enabled, 3, 0, 1, 2)

        layout.addWidget(conn_group)

        # ── Model ─────────────────────────────────────────────────
        model_group = QtWidgets.QGroupBox("Model")
        model_group.setStyleSheet(
            "QGroupBox { font-weight: bold; padding-top: 16px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 8px; }")
        model_layout = QtWidgets.QGridLayout(model_group)
        model_layout.setSpacing(8)

        model_layout.addWidget(QtWidgets.QLabel("Model:"), 0, 0)
        model_row = QtWidgets.QHBoxLayout()
        self.combo_model = QtWidgets.QComboBox()
        self.combo_model.setEditable(True)
        self.combo_model.setMinimumWidth(200)
        self.combo_model.currentTextChanged.connect(self._on_model_changed)
        model_row.addWidget(self.combo_model)

        btn_refresh = QtWidgets.QPushButton("Refresh")
        btn_refresh.setToolTip("Reload available models from Ollama")
        btn_refresh.clicked.connect(self._refresh_models)
        model_row.addWidget(btn_refresh)
        model_row.addStretch()
        model_layout.addLayout(model_row, 0, 1)

        # Model details card
        self.lbl_model_info = QtWidgets.QLabel("")
        self.lbl_model_info.setStyleSheet(
            "background: #f8f9fa; border: 1px solid #dee2e6; "
            "border-radius: 4px; padding: 8px; color: #495057; "
            "font-size: 11px;")
        self.lbl_model_info.setWordWrap(True)
        self.lbl_model_info.setMinimumHeight(40)
        model_layout.addWidget(self.lbl_model_info, 1, 0, 1, 2)

        # Temperature
        model_layout.addWidget(QtWidgets.QLabel("Temperature:"), 2, 0)
        temp_row = QtWidgets.QHBoxLayout()
        self.slider_temp = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_temp.setRange(0, 100)  # 0.0 to 1.0 in steps of 0.01
        self.slider_temp.setStyleSheet(
            "QSlider::groove:horizontal { height: 6px; background: #ddd; "
            "border-radius: 3px; }"
            "QSlider::handle:horizontal { width: 14px; margin: -4px 0; "
            "background: #3498db; border-radius: 7px; }"
            "QSlider::sub-page:horizontal { background: qlineargradient("
            "x1:0, y1:0, x2:1, y2:0, stop:0 #3498db, stop:1 #e74c3c); "
            "border-radius: 3px; }")
        self.slider_temp.valueChanged.connect(self._on_temp_slider_changed)
        temp_row.addWidget(self.slider_temp)

        self.spin_temp = QtWidgets.QDoubleSpinBox()
        self.spin_temp.setRange(0.0, 1.0)
        self.spin_temp.setSingleStep(0.05)
        self.spin_temp.setDecimals(2)
        self.spin_temp.setFixedWidth(70)
        self.spin_temp.valueChanged.connect(self._on_temp_spin_changed)
        temp_row.addWidget(self.spin_temp)
        model_layout.addLayout(temp_row, 2, 1)

        self.lbl_temp_hint = QtWidgets.QLabel("")
        self.lbl_temp_hint.setStyleSheet("color: #888; font-size: 10px;")
        model_layout.addWidget(self.lbl_temp_hint, 3, 1)

        layout.addWidget(model_group)

        # ── System Prompt ─────────────────────────────────────────
        prompt_group = QtWidgets.QGroupBox("System Prompt")
        prompt_group.setStyleSheet(
            "QGroupBox { font-weight: bold; padding-top: 16px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 8px; }")
        prompt_layout = QtWidgets.QVBoxLayout(prompt_group)

        prompt_hint = QtWidgets.QLabel(
            "Instructions sent to the model before face data. "
            "Customize to change how the AI analyzes your parts.")
        prompt_hint.setStyleSheet("color: #666; font-size: 11px;")
        prompt_hint.setWordWrap(True)
        prompt_layout.addWidget(prompt_hint)

        self.txt_system_prompt = QtWidgets.QPlainTextEdit()
        self.txt_system_prompt.setMaximumHeight(90)
        self.txt_system_prompt.setStyleSheet(
            "QPlainTextEdit { font-family: monospace; font-size: 11px; "
            "border: 1px solid #ccc; border-radius: 3px; padding: 4px; }")
        prompt_layout.addWidget(self.txt_system_prompt)

        prompt_btns = QtWidgets.QHBoxLayout()
        btn_reset_prompt = QtWidgets.QPushButton("Reset to Default")
        btn_reset_prompt.clicked.connect(self._reset_system_prompt)
        prompt_btns.addWidget(btn_reset_prompt)

        btn_test_prompt = QtWidgets.QPushButton("Test Prompt")
        btn_test_prompt.setToolTip(
            "Send a small test query to Ollama to verify settings")
        btn_test_prompt.clicked.connect(self._test_prompt)
        prompt_btns.addWidget(btn_test_prompt)

        self.lbl_test_result = QtWidgets.QLabel("")
        self.lbl_test_result.setStyleSheet("font-size: 11px;")
        prompt_btns.addWidget(self.lbl_test_result)

        self.btn_retry = QtWidgets.QPushButton("Retry")
        self.btn_retry.setFixedWidth(60)
        self.btn_retry.setVisible(False)
        self.btn_retry.clicked.connect(self._test_prompt)
        prompt_btns.addWidget(self.btn_retry)
        prompt_btns.addStretch()
        prompt_layout.addLayout(prompt_btns)

        layout.addWidget(prompt_group)

        # ── Dialog Buttons ────────────────────────────────────────
        btn_box = QtWidgets.QHBoxLayout()
        btn_box.addStretch()

        btn_save = QtWidgets.QPushButton("Save")
        btn_save.setDefault(True)
        btn_save.setStyleSheet(
            "QPushButton { background: #27ae60; color: white; padding: 6px 20px; "
            "border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background: #2ecc71; }")
        btn_save.clicked.connect(self._save_and_close)
        btn_box.addWidget(btn_save)

        btn_cancel = QtWidgets.QPushButton("Cancel")
        btn_cancel.setStyleSheet("QPushButton { padding: 6px 16px; }")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        layout.addLayout(btn_box)

    # ── Load / Save ───────────────────────────────────────────────

    def _load_preferences(self):
        prefs = get_preferences()
        self.txt_url.setText(prefs["url"])
        self.spin_timeout.setValue(prefs["timeout"])
        self.chk_enabled.setChecked(prefs["enabled"])
        self.combo_model.addItem(prefs["model"])
        self.spin_temp.setValue(prefs["temperature"])
        self.slider_temp.setValue(int(prefs["temperature"] * 100))
        self.txt_system_prompt.setPlainText(prefs["system_prompt"])
        self._update_temp_hint(prefs["temperature"])
        self._refresh_models()

    def _save_and_close(self):
        prefs = {
            "url": self.txt_url.text().strip(),
            "model": self.combo_model.currentText().strip(),
            "timeout": self.spin_timeout.value(),
            "enabled": self.chk_enabled.isChecked(),
            "temperature": self.spin_temp.value(),
            "system_prompt": self.txt_system_prompt.toPlainText().strip(),
        }
        save_preferences(prefs)
        self.accept()

    # ── Connection ────────────────────────────────────────────────

    def _check_connection(self):
        self._set_connection_status("checking", "Checking...")

        def _check():
            prefs = {"url": self.txt_url.text().strip() or _DEFAULTS["url"]}
            ok = check_ollama_available(prefs)
            models = list_ollama_models(prefs) if ok else []
            self._sig_connection_result.emit(ok, len(models))

        t = threading.Thread(target=_check, daemon=True)
        t.start()

    def _on_connection_result(self, ok, model_count):
        if ok:
            self._set_connection_status(
                "online",
                f"Connected ({model_count} model{'s' if model_count != 1 else ''} available)")
        else:
            self._set_connection_status(
                "offline",
                "Cannot reach Ollama. Is it running?")

    def _set_connection_status(self, state, text):
        colors = {
            "online": ("#27ae60", "\u25cf"),
            "offline": ("#e74c3c", "\u25cf"),
            "checking": ("#f39c12", "\u25cb"),
        }
        color, icon = colors.get(state, ("#888", "\u25cb"))
        self.lbl_status_icon.setText(icon)
        self.lbl_status_icon.setStyleSheet(
            f"color: {color}; font-size: 16px;")
        self.lbl_status_text.setText(text)
        self.lbl_status_text.setStyleSheet(
            f"color: {color}; font-size: 12px;")

    # ── Models ────────────────────────────────────────────────────

    def _refresh_models(self):
        def _load():
            prefs = {"url": self.txt_url.text().strip() or _DEFAULTS["url"]}
            models = list_ollama_models(prefs)
            self._sig_models_loaded.emit(models)

        t = threading.Thread(target=_load, daemon=True)
        t.start()

    def _on_models_loaded(self, models):
        current = self.combo_model.currentText()
        self.combo_model.clear()
        if models:
            for m in models:
                self.combo_model.addItem(m)
            idx = self.combo_model.findText(current)
            if idx >= 0:
                self.combo_model.setCurrentIndex(idx)
            else:
                self.combo_model.addItem(current)
                self.combo_model.setCurrentIndex(self.combo_model.count() - 1)
        else:
            self.combo_model.addItem(current or _DEFAULTS["model"])
            self.lbl_model_info.setText(
                "No models found. Install models with: ollama pull llama3.2")

    def _on_model_changed(self, model_name):
        if not model_name:
            return
        # Check cache first
        with self._model_details_lock:
            if model_name in self._model_details:
                self._show_model_info(self._model_details[model_name])
                return

        self.lbl_model_info.setText("Loading model info...")

        def _load():
            prefs = {"url": self.txt_url.text().strip() or _DEFAULTS["url"]}
            info = get_model_info(model_name, prefs)
            with self._model_details_lock:
                self._model_details[model_name] = info
            self._sig_model_info_loaded.emit(info)

        t = threading.Thread(target=_load, daemon=True)
        t.start()

    def _on_model_info_loaded(self, info):
        self._show_model_info(info)

    def _show_model_info(self, info):
        if not info or not info.get("name"):
            self.lbl_model_info.setText("Model info unavailable")
            return
        parts = []
        if info.get("family"):
            parts.append(f"Family: {info['family']}")
        if info.get("parameter_size"):
            parts.append(f"Parameters: {info['parameter_size']}")
        if info.get("quantization"):
            parts.append(f"Quantization: {info['quantization']}")
        if info.get("format"):
            parts.append(f"Format: {info['format']}")
        self.lbl_model_info.setText(
            " \u2022 ".join(parts) if parts else info.get("name", ""))

    # ── Temperature ───────────────────────────────────────────────

    def _on_temp_slider_changed(self, value):
        temp = value / 100.0
        self.spin_temp.blockSignals(True)
        self.spin_temp.setValue(temp)
        self.spin_temp.blockSignals(False)
        self._update_temp_hint(temp)

    def _on_temp_spin_changed(self, value):
        self.slider_temp.blockSignals(True)
        self.slider_temp.setValue(int(value * 100))
        self.slider_temp.blockSignals(False)
        self._update_temp_hint(value)

    def _update_temp_hint(self, temp):
        if temp <= 0.1:
            hint = "Very deterministic — most consistent results"
        elif temp <= 0.3:
            hint = "Low creativity — good for structured JSON output"
        elif temp <= 0.6:
            hint = "Balanced — moderate variation in responses"
        elif temp <= 0.8:
            hint = "Creative — more diverse naming and descriptions"
        else:
            hint = "High creativity — unpredictable, may break JSON format"
        self.lbl_temp_hint.setText(hint)

    # ── System Prompt ─────────────────────────────────────────────

    def _reset_system_prompt(self):
        self.txt_system_prompt.setPlainText(_DEFAULTS["system_prompt"])

    def _test_prompt(self):
        self.btn_retry.setVisible(False)
        self.lbl_test_result.setText("Testing...")
        self.lbl_test_result.setStyleSheet(
            "color: #f39c12; font-size: 11px;")

        def _run():
            prefs = {
                "url": self.txt_url.text().strip() or _DEFAULTS["url"],
                "model": self.combo_model.currentText().strip(),
                "timeout": self.spin_timeout.value(),
                "enabled": True,
                "temperature": self.spin_temp.value(),
                "system_prompt": self.txt_system_prompt.toPlainText().strip(),
            }
            test_prompt = (
                'Respond with this exact JSON: '
                '{"status": "ok", "model": "' + prefs["model"] + '"}'
            )
            result = query_ollama(test_prompt, prefs)
            success = result is not None and isinstance(result, dict)
            self._sig_test_result.emit(success, str(result) if result else "No response")

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def _on_test_result(self, success, detail):
        if success:
            self.lbl_test_result.setText("OK — model responds correctly")
            self.lbl_test_result.setStyleSheet(
                "color: #27ae60; font-size: 11px;")
            self.btn_retry.setVisible(False)
        else:
            self.lbl_test_result.setText(f"Failed: {detail[:60]}")
            self.lbl_test_result.setStyleSheet(
                "color: #e74c3c; font-size: 11px;")
            self.btn_retry.setVisible(True)
