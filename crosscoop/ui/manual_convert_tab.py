"""
Manual File & Code Converter Tab.
Bidirectional conversion for local files or pasted code snippets.
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
from PyQt6.QtCore import Qt

from crosscoop.core.converter import (
    parse_nucleus_js, partydeck_to_nucleus_js,
    export_partydeck_package, export_nucleus_package
)

class ManualConvertTab(QWidget):
    def __init__(self, partydeck_mgr, parent=None):
        super().__init__(parent)
        self.partydeck_mgr = partydeck_mgr
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

        open_file_btn = QPushButton("📂 Open Local File...")
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

        # Bottom export buttons
        btn_bar = QHBoxLayout()
        self.save_btn = QPushButton("💾 Save Result to File...")
        self.save_btn.clicked.connect(self.on_save_file)
        btn_bar.addWidget(self.save_btn)

        self.install_partydeck_btn = QPushButton("🚀 Install directly to PartyDeck")
        self.install_partydeck_btn.setObjectName("successBtn")
        self.install_partydeck_btn.clicked.connect(self.on_install_partydeck)
        btn_bar.addWidget(self.install_partydeck_btn)

        out_layout.addLayout(btn_bar)
        splitter.addWidget(output_group)

        splitter.setSizes([500, 500])
        main_layout.addWidget(splitter, stretch=1)

    def on_mode_changed(self):
        idx = self.mode_combo.currentIndex()
        if idx == 0:
            self.input_edit.setPlaceholderText("// Paste Nucleus handler.js code...")
            self.install_partydeck_btn.show()
        else:
            self.input_edit.setPlaceholderText('// Paste PartyDeck handler.json code...')
            self.install_partydeck_btn.hide()

    def on_open_file(self):
        idx = self.mode_combo.currentIndex()
        if idx == 0:
            filt = "Nucleus Files (*.js *.zip *.nc);;All Files (*)"
        else:
            filt = "PartyDeck Files (*.json *.pd2);;All Files (*)"

        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", filt)
        if not file_path:
            return

        try:
            if file_path.endswith(".zip") or file_path.endswith(".nc") or file_path.endswith(".pd2"):
                with zipfile.ZipFile(file_path, "r") as zf:
                    target_file = None
                    for name in zf.namelist():
                        if name.endswith("handler.js") or name.endswith("handler.json"):
                            target_file = name
                            break
                    if target_file:
                        content = zf.read(target_file).decode("utf-8", errors="ignore")
                        self.input_edit.setPlainText(content)
                    else:
                        QMessageBox.warning(self, "Invalid Archive", "No handler.js or handler.json found in archive.")
                        return
            else:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    self.input_edit.setPlainText(f.read())

            self.do_convert()
        except Exception as e:
            QMessageBox.critical(self, "File Read Error", f"Could not read file:\n{e}")

    def do_convert(self):
        code = self.input_edit.toPlainText().strip()
        if not code:
            return

        idx = self.mode_combo.currentIndex()
        try:
            if idx == 0:
                # Nucleus -> PartyDeck
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
        text = self.output_edit.toPlainText().strip()
        if not text:
            return
        try:
            pd_data = json.loads(text)
            self.partydeck_mgr.save_handler(pd_data["name"], pd_data)
            QMessageBox.information(self, "Installed", f"Handler '{pd_data['name']}' has been installed to PartyDeck!")
        except Exception as e:
            QMessageBox.critical(self, "Install Error", f"Could not install handler:\n{e}")
