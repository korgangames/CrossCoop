"""
PartyDeck Installed Handlers Tab.
Manages games currently installed in PartyDeck and allows two-way actions:
- 1-Click install directly into Nucleus Co-op handlers directory
- Reverse export to Nucleus Co-op package/script (.js / .zip)
- Edit JSON parameters, open folder, or delete
with clickable header sorting.
"""

import os
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QGroupBox, QTextEdit, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from crosscoop.core.nucleus_manager import NucleusManager
from crosscoop.core.converter import partydeck_to_nucleus_js, export_nucleus_package

class InstalledTab(QWidget):
    handler_changed_signal = pyqtSignal()
    handler_converted_to_nucleus_signal = pyqtSignal()

    def __init__(self, partydeck_mgr, nucleus_mgr=None, parent=None):
        super().__init__(parent)
        self.partydeck_mgr = partydeck_mgr
        self.nucleus_mgr = nucleus_mgr if nucleus_mgr else NucleusManager()
        self.installed_handlers = []
        self.selected_item = None

        self.sort_column = 0
        self.sort_order = Qt.SortOrder.AscendingOrder

        self.setup_ui()
        self.refresh_list()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Header info
        header_bar = QHBoxLayout()
        self.count_lbl = QLabel("Installed in PartyDeck (0 games)")
        self.count_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #818cf8;")
        header_bar.addWidget(self.count_lbl)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_list)
        header_bar.addWidget(refresh_btn)

        main_layout.addLayout(header_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Table of installed handlers
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Game Name ⬍", "Executable ⬍", "Steam AppID ⬍", "LAN Emu ⬍"])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)
        header.setSortIndicator(self.sort_column, self.sort_order)
        header.sectionClicked.connect(self.on_header_clicked)

        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        splitter.addWidget(self.table)

        # Right Inspector Panel
        inspector = QGroupBox("PartyDeck Handler Details & Two-Way Nucleus Bridge")
        insp_layout = QVBoxLayout(inspector)

        self.details_lbl = QLabel("Select an installed handler")
        self.details_lbl.setStyleSheet("font-weight: bold; color: #ffffff;")
        insp_layout.addWidget(self.details_lbl)

        self.json_editor = QTextEdit()
        self.json_editor.setStyleSheet("font-family: monospace; background-color: #12131a; border: 1px solid #232533; border-radius: 6px;")
        insp_layout.addWidget(self.json_editor, stretch=1)

        # Action Buttons
        btn_layout = QVBoxLayout()

        # Two-way install & export row
        nucleus_actions = QHBoxLayout()
        self.install_nucleus_btn = QPushButton("🪟 Install directly to Nucleus Co-op")
        self.install_nucleus_btn.setStyleSheet("background-color: #2563eb; color: #ffffff; font-weight: 600; padding: 8px 12px; border-radius: 6px;")
        self.install_nucleus_btn.setEnabled(False)
        self.install_nucleus_btn.clicked.connect(self.on_install_to_nucleus)
        nucleus_actions.addWidget(self.install_nucleus_btn)

        self.export_nucleus_btn = QPushButton("💾 Export to File (.js / .zip)")
        self.export_nucleus_btn.setEnabled(False)
        self.export_nucleus_btn.clicked.connect(self.on_export_to_nucleus)
        nucleus_actions.addWidget(self.export_nucleus_btn)
        btn_layout.addLayout(nucleus_actions)

        row_btns = QHBoxLayout()
        self.save_edits_btn = QPushButton("💾 Save JSON Changes")
        self.save_edits_btn.setEnabled(False)
        self.save_edits_btn.clicked.connect(self.on_save_edits)
        row_btns.addWidget(self.save_edits_btn)

        self.open_folder_btn = QPushButton("📁 Open Folder")
        self.open_folder_btn.setEnabled(False)
        self.open_folder_btn.clicked.connect(self.on_open_folder)
        row_btns.addWidget(self.open_folder_btn)

        self.delete_btn = QPushButton("🗑️ Delete")
        self.delete_btn.setObjectName("dangerBtn")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self.on_delete_handler)
        row_btns.addWidget(self.delete_btn)

        btn_layout.addLayout(row_btns)
        insp_layout.addLayout(btn_layout)

        splitter.addWidget(inspector)
        splitter.setSizes([550, 450])
        main_layout.addWidget(splitter, stretch=1)

    def on_header_clicked(self, logical_index):
        if logical_index == self.sort_column:
            self.sort_order = (
                Qt.SortOrder.AscendingOrder
                if self.sort_order == Qt.SortOrder.DescendingOrder
                else Qt.SortOrder.DescendingOrder
            )
        else:
            self.sort_column = logical_index
            self.sort_order = Qt.SortOrder.AscendingOrder

        self.table.horizontalHeader().setSortIndicator(self.sort_column, self.sort_order)
        self.apply_sorting_and_render()

    def apply_sorting_and_render(self):
        is_reverse = (self.sort_order == Qt.SortOrder.DescendingOrder)

        def get_sort_key(item):
            d = item["data"]
            if self.sort_column == 0:
                return d.get("name", item["folder_name"]).lower()
            elif self.sort_column == 1:
                return d.get("exec", "").lower()
            elif self.sort_column == 2:
                appid = d.get("steam_appid")
                return int(appid) if isinstance(appid, int) else 0
            elif self.sort_column == 3:
                return 1 if d.get("use_goldberg") else 0
            return ""

        self.installed_handlers.sort(key=get_sort_key, reverse=is_reverse)
        self.render_rows()

    def refresh_list(self):
        self.installed_handlers = self.partydeck_mgr.get_installed_handlers()
        self.count_lbl.setText(f"Installed in PartyDeck ({len(self.installed_handlers)} games)")
        self.apply_sorting_and_render()

    def render_rows(self):
        self.table.setRowCount(len(self.installed_handlers))

        for row, item in enumerate(self.installed_handlers):
            d = item["data"]
            name = d.get("name", item["folder_name"])
            exe = d.get("exec", "-")
            appid = str(d.get("steam_appid") or "-")
            goldberg = "✅ Goldberg" if d.get("use_goldberg") else "❌ None"

            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(exe))
            self.table.setItem(row, 2, QTableWidgetItem(appid))
            self.table.setItem(row, 3, QTableWidgetItem(goldberg))

        if self.installed_handlers:
            self.table.selectRow(0)
        else:
            self.details_lbl.setText("No handlers found in PartyDeck")
            self.json_editor.clear()
            self.install_nucleus_btn.setEnabled(False)
            self.export_nucleus_btn.setEnabled(False)
            self.save_edits_btn.setEnabled(False)
            self.open_folder_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)

    def on_selection_changed(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            self.selected_item = None
            return

        row = selected_rows[0].row()
        self.selected_item = self.installed_handlers[row]
        d = self.selected_item["data"]
        name = d.get("name", self.selected_item["folder_name"])

        self.details_lbl.setText(f"Handler: {name} (Folder: {self.selected_item['folder_name']})")
        
        import json
        self.json_editor.setText(json.dumps(d, indent=2))

        self.install_nucleus_btn.setEnabled(True)
        self.export_nucleus_btn.setEnabled(True)
        self.save_edits_btn.setEnabled(True)
        self.open_folder_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)

    def on_save_edits(self):
        if not self.selected_item:
            return
        import json
        try:
            new_data = json.loads(self.json_editor.toPlainText())
            self.partydeck_mgr.save_handler(self.selected_item["folder_name"], new_data)
            QMessageBox.information(self, "Saved", "Handler JSON updated successfully!")
            self.refresh_list()
            self.handler_changed_signal.emit()
        except Exception as e:
            QMessageBox.critical(self, "Invalid JSON", f"Could not parse JSON:\n{e}")

    def on_open_folder(self):
        if not self.selected_item:
            return
        path = self.selected_item["path"]
        subprocess.Popen(["xdg-open", path])

    def on_delete_handler(self):
        if not self.selected_item:
            return
        name = self.selected_item["data"].get("name", self.selected_item["folder_name"])
        ans = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to remove '{name}' from PartyDeck?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ans == QMessageBox.StandardButton.Yes:
            self.partydeck_mgr.delete_handler(self.selected_item["folder_name"])
            self.refresh_list()
            self.handler_changed_signal.emit()

    def on_install_to_nucleus(self):
        """1-Click direct install to Nucleus Co-op handler directory."""
        if not self.selected_item:
            return
        d = self.selected_item["data"]
        name = d.get("name", self.selected_item["folder_name"])
        js_code = partydeck_to_nucleus_js(d)
        dest_path = self.nucleus_mgr.save_handler_js(name, js_code)
        QMessageBox.information(
            self, "Installed to Nucleus",
            f"Successfully converted and installed '{name}' directly into Nucleus Co-op!\nSaved to:\n{dest_path}"
        )
        self.handler_converted_to_nucleus_signal.emit()

    def on_export_to_nucleus(self):
        if not self.selected_item:
            return
        d = self.selected_item["data"]
        name = d.get("name", "CustomGame")
        
        js_code = partydeck_to_nucleus_js(d)

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Nucleus Co-op Handler",
            f"{name}.js", "Nucleus Handler (*.js);;Nucleus Package (*.zip)"
        )
        if file_path:
            if file_path.endswith(".zip") or file_path.endswith(".nc"):
                export_nucleus_package(js_code, file_path)
            else:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(js_code)
            
            QMessageBox.information(
                self, "Export Successful",
                f"Generated Nucleus Co-op handler for '{name}'!\nSaved to:\n{file_path}\n\nYou can now drop this file directly into Nucleus Co-op on Windows."
            )
