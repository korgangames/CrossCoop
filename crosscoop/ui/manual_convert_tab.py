"""
Manual File & Code Converter Tab.
Bidirectional conversion for local files or pasted code snippets,
with two-way 1-click install directly to PartyDeck or Nucleus Co-op.
"""

import os
import json
import zipfile
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QPlainTextEdit, QSplitter, QGroupBox,
    QComboBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from crosscoop.core.nucleus_manager import NucleusManager
from crosscoop.core.converter import (
    parse_nucleus_js, parse_lenient_handler, partydeck_to_nucleus_js,
    export_partydeck_package, export_nucleus_package, import_handler_file
)

class ManualConvertTab(QWidget):
    nucleus_installed_signal = pyqtSignal()
    partydeck_installed_signal = pyqtSignal()

    def __init__(self, partydeck_mgr, nucleus_mgr=None, parent=None):
        super().__init__(parent)
        self.partydeck_mgr = partydeck_mgr
        self.nucleus_mgr = nucleus_mgr if nucleus_mgr else NucleusManager()
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Top Bar: Mode selector & file opener
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Conversion Mode:"))

        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "Nucleus Co-op (.js / .zip) ➜ PartyDeck (.json / .pd2)",
            "PartyDeck (.json / .pd2) ➜ Nucleus Co-op (.js / .zip)"
        ])
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        top_bar.addWidget(self.mode_combo, stretch=2)

        open_file_btn = QPushButton("📂 Open Local File / Package...")
        open_file_btn.setToolTip("Open official or unofficial handler files (.js, .zip, .nc, .json, .txt)")
        open_file_btn.clicked.connect(self.on_open_file)
        top_bar.addWidget(open_file_btn)

        convert_btn = QPushButton("⚡ Convert Code")
        convert_btn.setObjectName("primaryBtn")
        convert_btn.clicked.connect(self.do_convert)
        top_bar.addWidget(convert_btn)

        main_layout.addLayout(top_bar)

        # Splitter: Input on Left, Output on Right
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Input Editor
        input_group = QGroupBox("Input Source (File Content or Paste Below)")
        in_layout = QVBoxLayout(input_group)
        self.input_edit = QPlainTextEdit()
        self.input_edit.setPlaceholderText("// Paste Nucleus handler.js code or load a file...")
        self.input_edit.setStyleSheet("font-family: monospace; background-color: #12131a; border: 1px solid #232533; border-radius: 6px;")
        in_layout.addWidget(self.input_edit)
        splitter.addWidget(input_group)

        # Right: Output Preview
        output_group = QGroupBox("Converted Output Preview")
        out_layout = QVBoxLayout(output_group)
        self.output_edit = QPlainTextEdit()
        self.output_edit.setPlaceholderText("// Converted result will appear here...")
        self.output_edit.setStyleSheet("font-family: monospace; background-color: #12131a; border: 1px solid #232533; border-radius: 6px;")
        out_layout.addWidget(self.output_edit)

        # Bottom export & direct install buttons (both ways)
        btn_bar = QHBoxLayout()
        self.save_btn = QPushButton("💾 Save Result to File...")
        self.save_btn.clicked.connect(self.on_save_file)
        btn_bar.addWidget(self.save_btn)

        btn_bar.addStretch()

        self.install_nc_btn = QPushButton("🪟 Install to Nucleus Co-op")
        self.install_nc_btn.setStyleSheet("background-color: #2563eb; color: #ffffff; font-weight: 600; padding: 8px 14px; border-radius: 6px;")
        self.install_nc_btn.clicked.connect(self.on_install_nucleus)
        btn_bar.addWidget(self.install_nc_btn)

        self.install_pd_btn = QPushButton("🐧 Install to PartyDeck")
        self.install_pd_btn.setStyleSheet("background-color: #9333ea; color: #ffffff; font-weight: 600; padding: 8px 14px; border-radius: 6px;")
        self.install_pd_btn.clicked.connect(self.on_install_partydeck)
        btn_bar.addWidget(self.install_pd_btn)

        out_layout.addLayout(btn_bar)
        splitter.addWidget(output_group)

        splitter.setSizes([500, 500])
        main_layout.addWidget(splitter, stretch=1)

    def on_mode_changed(self):
        idx = self.mode_combo.currentIndex()
        if idx == 0:
            self.input_edit.setPlaceholderText("// Paste Nucleus handler.js code...")
        else:
            self.input_edit.setPlaceholderText('// Paste PartyDeck handler.json code...')

    def on_open_file(self):
        idx = self.mode_combo.currentIndex()
        filt = "All Supported Handlers (*.js *.zip *.nc *.json *.pd2 *.txt);;Nucleus Files (*.js *.zip *.nc);;PartyDeck Files (*.json *.pd2);;All Files (*)"

        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", filt)
        if not file_path:
            return

        try:
            res = import_handler_file(file_path)
            raw_code = res["raw_code"]
            pd_data = res["partydeck_data"]
            features = res.get("detected_features", [])

            if idx == 0:
                # Nucleus -> PartyDeck
                self.input_edit.setPlainText(raw_code)
                self.output_edit.setPlainText(json.dumps(pd_data, indent=2))
            else:
                # PartyDeck -> Nucleus
                if res.get("source_type") in ["json", "archive_json"]:
                    self.input_edit.setPlainText(raw_code)
                    self.output_edit.setPlainText(partydeck_to_nucleus_js(pd_data))
                else:
                    self.input_edit.setPlainText(raw_code)
                    self.output_edit.setPlainText(json.dumps(pd_data, indent=2))

            if features:
                msg = f"Imported '{Path(file_path).name}' successfully!\n\nDetected Features:\n" + "\n".join(f"• {f}" for f in features)
                QMessageBox.information(self, "File Imported", msg)

        except Exception as e:
            QMessageBox.critical(self, "File Read Error", f"Could not read/parse file:\n{e}")

    def do_convert(self):
        code = self.input_edit.toPlainText().strip()
        if not code:
            return

        idx = self.mode_combo.currentIndex()
        try:
            if idx == 0:
                # Nucleus -> PartyDeck (uses lenient parsing)
                pd_data = parse_nucleus_js(code)
                out_str = json.dumps(pd_data, indent=2)
                self.output_edit.setPlainText(out_str)
            else:
                # PartyDeck -> Nucleus
                pd_data = json.loads(code)
                js_code = partydeck_to_nucleus_js(pd_data)
                self.output_edit.setPlainText(js_code)
        except Exception as e:
            QMessageBox.critical(self, "Conversion Error", f"Failed to parse input:\n{e}")

    def on_save_file(self):
        text = self.output_edit.toPlainText().strip()
        if not text:
            return

        idx = self.mode_combo.currentIndex()
        if idx == 0:
            out_file, _ = QFileDialog.getSaveFileName(self, "Save PartyDeck Handler", "handler.json", "JSON (*.json);;PartyDeck Package (*.pd2)")
            if out_file:
                if out_file.endswith(".pd2"):
                    pd_data = json.loads(text)
                    export_partydeck_package(pd_data, out_file)
                else:
                    with open(out_file, "w", encoding="utf-8") as f:
                        f.write(text)
                QMessageBox.information(self, "Saved", f"Saved successfully to:\n{out_file}")
        else:
            out_file, _ = QFileDialog.getSaveFileName(self, "Save Nucleus Handler", "handler.js", "JavaScript (*.js);;Nucleus Package (*.zip)")
            if out_file:
                if out_file.endswith(".zip") or out_file.endswith(".nc"):
                    export_nucleus_package(text, out_file)
                else:
                    with open(out_file, "w", encoding="utf-8") as f:
                        f.write(text)
                QMessageBox.information(self, "Saved", f"Saved successfully to:\n{out_file}")

    def on_install_partydeck(self):
        idx = self.mode_combo.currentIndex()
        try:
            if idx == 0:
                text = self.output_edit.toPlainText().strip()
                if not text:
                    self.do_convert()
                    text = self.output_edit.toPlainText().strip()
                pd_data = json.loads(text)
            else:
                text = self.input_edit.toPlainText().strip()
                pd_data = json.loads(text)

            self.partydeck_mgr.save_handler(pd_data["name"], pd_data)
            QMessageBox.information(self, "Installed", f"Handler '{pd_data['name']}' has been installed to PartyDeck!")
            self.partydeck_installed_signal.emit()
        except Exception as e:
            QMessageBox.critical(self, "Install Error", f"Could not install handler to PartyDeck:\n{e}")

    def on_install_nucleus(self):
        idx = self.mode_combo.currentIndex()
        try:
            if idx == 0:
                # In mode 0: Input edit contains Nucleus JS code
                js_code = self.input_edit.toPlainText().strip()
                if not js_code:
                    return
                parsed = parse_lenient_handler(js_code)
                name = parsed.get("name", "CustomGame")
            else:
                # In mode 1: Output edit contains generated Nucleus JS code
                js_code = self.output_edit.toPlainText().strip()
                if not js_code:
                    self.do_convert()
                    js_code = self.output_edit.toPlainText().strip()
                in_json = json.loads(self.input_edit.toPlainText())
                name = in_json.get("name", "CustomGame")

            dest = self.nucleus_mgr.save_handler_js(name, js_code)
            QMessageBox.information(self, "Installed to Nucleus", f"Installed handler '{name}' to Nucleus Co-op directory:\n{dest}")
            self.nucleus_installed_signal.emit()
        except Exception as e:
            QMessageBox.critical(self, "Install Error", f"Could not install handler to Nucleus:\n{e}")
