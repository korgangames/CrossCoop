"""
Nucleus Co-op Local Installed Handlers Tab.
Manages handlers present in the local nucleus_coop/handlers directory,
supports importing loose/unofficial community handlers from local files,
and converts them into PartyDeck.
"""

import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QGroupBox, QPlainTextEdit, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal

from crosscoop.core.nucleus_manager import NucleusManager
from crosscoop.core.converter import parse_nucleus_js, import_handler_file

class NucleusInstalledTab(QWidget):
    handler_converted_signal = pyqtSignal()

    def __init__(self, nucleus_mgr, partydeck_mgr, parent=None):
        super().__init__(parent)
        self.nucleus_mgr = nucleus_mgr
        self.partydeck_mgr = partydeck_mgr
        self.handlers = []
        self.selected_item = None

        self.sort_column = 0
        self.sort_order = Qt.SortOrder.AscendingOrder

        self.setup_ui()
        self.refresh_list()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        header_bar = QHBoxLayout()
        self.count_lbl = QLabel("Installed in Nucleus Co-op (0 files)")
        self.count_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #818cf8;")
        header_bar.addWidget(self.count_lbl)

        header_bar.addStretch()

        import_btn = QPushButton("📥 Import Local / Downloaded Handler...")
        import_btn.setObjectName("primaryBtn")
        import_btn.setToolTip("Import unofficial or manually downloaded community handlers (.js, .zip, .nc, .json)")
        import_btn.clicked.connect(self.on_import_handler)
        header_bar.addWidget(import_btn)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_list)
        header_bar.addWidget(refresh_btn)

        main_layout.addLayout(header_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Table of installed Nucleus handlers
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Handler File ⬍", "Format ⬍", "Size ⬍"])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self.on_header_clicked)

        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        splitter.addWidget(self.table)

        # Right Inspector Panel
        inspector = QGroupBox("Handler Code Inspector & PartyDeck Converter")
        insp_layout = QVBoxLayout(inspector)

        self.details_lbl = QLabel("Select a handler file")
        self.details_lbl.setStyleSheet("font-weight: bold; color: #ffffff;")
        insp_layout.addWidget(self.details_lbl)

        self.code_editor = QPlainTextEdit()
        self.code_editor.setStyleSheet("font-family: monospace; background-color: #12131a; border: 1px solid #232533; border-radius: 6px;")
        insp_layout.addWidget(self.code_editor, stretch=1)

        # Action Buttons
        btn_layout = QVBoxLayout()
        self.convert_pd_btn = QPushButton("🔄 Convert & Install to PartyDeck")
        self.convert_pd_btn.setObjectName("primaryBtn")
        self.convert_pd_btn.setFixedHeight(36)
        self.convert_pd_btn.setEnabled(False)
        self.convert_pd_btn.clicked.connect(self.on_convert_to_partydeck)
        btn_layout.addWidget(self.convert_pd_btn)

        row_btns = QHBoxLayout()
        self.save_code_btn = QPushButton("💾 Save Changes")
        self.save_code_btn.setEnabled(False)
        self.save_code_btn.clicked.connect(self.on_save_code)
        row_btns.addWidget(self.save_code_btn)

        self.open_folder_btn = QPushButton("📁 Open Handlers Folder")
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
        splitter.setSizes([500, 480])
        main_layout.addWidget(splitter, stretch=1)

    def on_open_folder(self):
        folder = str(self.nucleus_mgr.handlers_dir)
        subprocess.Popen(["xdg-open", folder])

    def on_import_handler(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Import Downloaded / Unofficial Handlers",
            "",
            "Handler Files (*.js *.zip *.nc *.json *.txt);;All Files (*)"
        )
        if not file_paths:
            return

        imported_count = 0
        for fpath in file_paths:
            try:
                # 1. Parse leniently using import_handler_file
                result = import_handler_file(fpath)
                pd_data = result["partydeck_data"]
                features = result["detected_features"]
                features_str = "\n".join(f"• {f}" for f in features) if features else "Standard parameters"

                # 2. Copy file into local nucleus handlers directory
                dest_path = self.nucleus_mgr.import_external_handler(fpath)

                # 3. Prompt user to immediately convert & install into PartyDeck
                game_title = pd_data.get("name", Path(fpath).stem)
                ans = QMessageBox.question(
                    self,
                    "Handler Imported",
                    f"Successfully imported handler file:\n{Path(fpath).name}\n\n"
                    f"🎮 Game: {game_title}\n"
                    f"⚙️ Executable: {pd_data.get('exec')}\n"
                    f"🔍 Detected Features:\n{features_str}\n\n"
                    f"Do you want to immediately convert & install this handler into PartyDeck as well?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )

                if ans == QMessageBox.StandardButton.Yes:
                    self.partydeck_mgr.save_handler(pd_data["name"], pd_data)
                    self.handler_converted_signal.emit()

                imported_count += 1
            except Exception as e:
                QMessageBox.critical(self, "Import Error", f"Failed to import '{Path(fpath).name}':\n{e}")

        if imported_count > 0:
            self.refresh_list()

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

    def refresh_list(self):
        self.handlers = self.nucleus_mgr.get_installed_handlers()
        self.count_lbl.setText(f"Installed in Nucleus Co-op ({len(self.handlers)} files)")
        self.apply_sorting_and_render()

    def apply_sorting_and_render(self):
        is_reverse = (self.sort_order == Qt.SortOrder.DescendingOrder)

        def get_sort_key(item):
            if self.sort_column == 0:
                return item["file_name"].lower()
            elif self.sort_column == 1:
                return "Archive" if item["is_archive"] else "JavaScript"
            elif self.sort_column == 2:
                return item["size"]
            return ""

        self.handlers.sort(key=get_sort_key, reverse=is_reverse)
        self.render_rows()

    def render_rows(self):
        self.table.setRowCount(len(self.handlers))

        for row, item in enumerate(self.handlers):
            fmt = "📦 Package (.zip/.nc)" if item["is_archive"] else "📜 Script (.js)"
            size_kb = f"{item['size'] / 1024:.1f} KB"

            self.table.setItem(row, 0, QTableWidgetItem(item["file_name"]))
            self.table.setItem(row, 1, QTableWidgetItem(fmt))
            self.table.setItem(row, 2, QTableWidgetItem(size_kb))

        if self.handlers:
            self.table.selectRow(0)
        else:
            self.details_lbl.setText("No handlers found in nucleus_coop/handlers")
            self.code_editor.clear()
            self.convert_pd_btn.setEnabled(False)
            self.save_code_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)

    def on_selection_changed(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            self.selected_item = None
            return

        row = selected_rows[0].row()
        self.selected_item = self.handlers[row]
        path = self.selected_item["path"]
        name = self.selected_item["file_name"]

        self.details_lbl.setText(f"Handler File: {name}")
        code = self.nucleus_mgr.read_handler_code(path)
        self.code_editor.setPlainText(code)

        self.convert_pd_btn.setEnabled(True)
        self.save_code_btn.setEnabled(not self.selected_item["is_archive"])
        self.delete_btn.setEnabled(True)

    def on_save_code(self):
        if not self.selected_item or self.selected_item["is_archive"]:
            return
        code = self.code_editor.toPlainText()
        if self.nucleus_mgr.save_handler_code(self.selected_item["path"], code):
            QMessageBox.information(self, "Saved", "Handler script saved successfully!")

    def on_delete_handler(self):
        if not self.selected_item:
            return
        name = self.selected_item["file_name"]
        ans = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete '{name}' from Nucleus handlers?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ans == QMessageBox.StandardButton.Yes:
            self.nucleus_mgr.delete_handler(self.selected_item["path"])
            self.refresh_list()

    def on_convert_to_partydeck(self):
        if not self.selected_item:
            return
        code = self.code_editor.toPlainText()
        try:
            pd_data = parse_nucleus_js(code, meta={"gameName": Path(self.selected_item["file_name"]).stem})
            self.partydeck_mgr.save_handler(pd_data["name"], pd_data)
            features = pd_data.get("_detected_features", [])
            f_str = f"\n\nFeatures detected:\n" + "\n".join(f"• {f}" for f in features) if features else ""
            QMessageBox.information(
                self, "Converted",
                f"Handler '{pd_data['name']}' has been converted and installed into PartyDeck!{f_str}"
            )
            self.handler_converted_signal.emit()
        except Exception as e:
            QMessageBox.critical(self, "Conversion Failed", f"Could not parse handler:\n{e}")
