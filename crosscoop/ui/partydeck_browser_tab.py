"""
PartyDeck Community Handlers Browser Tab.
Allows users to browse PartyDeck community handlers just like the Nucleus Co-op Hub,
with two-way 1-click install:
- Install to PartyDeck (Linux / SteamOS)
- Convert & install to Nucleus Co-op (Windows / Wine)
- Export to either format (.js, .zip, .json, .pd2)
plus clickable header filtering (Title, Category, Author, Status).
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QGroupBox, QTextBrowser, QMessageBox, QProgressBar, QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor
from pathlib import Path
import json

from crosscoop.core.nucleus_manager import NucleusManager
from crosscoop.core.partydeck_community import PartyDeckCommunityClient
from crosscoop.core.converter import partydeck_to_nucleus_js, export_nucleus_package, export_partydeck_package

class LiveFetchWorker(QThread):
    finished_signal = pyqtSignal(list)

    def __init__(self, community_client):
        super().__init__()
        self.community_client = community_client

    def run(self):
        updated = self.community_client.fetch_live_issues()
        self.finished_signal.emit(updated)


class PartyDeckBrowserTab(QWidget):
    handler_installed_signal = pyqtSignal()
    nucleus_handler_installed_signal = pyqtSignal()

    def __init__(self, partydeck_mgr, nucleus_mgr=None, parent=None):
        super().__init__(parent)
        self.partydeck_mgr = partydeck_mgr
        self.nucleus_mgr = nucleus_mgr if nucleus_mgr else NucleusManager()
        self.community_client = PartyDeckCommunityClient()
        self.filtered_handlers = []
        self.selected_handler = None
        self.worker = None

        # Sorting state: default column 0 (Title), Ascending
        self.sort_column = 0
        self.sort_order = Qt.SortOrder.AscendingOrder

        self.setup_ui()
        self.refresh_table()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Filters Bar
        filter_bar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search PartyDeck community handlers...")
        self.search_input.textChanged.connect(self.refresh_table)
        filter_bar.addWidget(self.search_input, stretch=3)

        self.cat_combo = QComboBox()
        self.cat_combo.addItem("All Categories")
        for cat in self.community_client.get_categories():
            self.cat_combo.addItem(cat)
        self.cat_combo.currentTextChanged.connect(self.refresh_table)
        filter_bar.addWidget(self.cat_combo, stretch=1)

        self.fetch_btn = QPushButton("🔄 Sync GitHub Issues")
        self.fetch_btn.setToolTip("Query partydeck/partydeck GitHub issues for live community submissions")
        self.fetch_btn.clicked.connect(self.on_sync_github)
        filter_bar.addWidget(self.fetch_btn)

        main_layout.addLayout(filter_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Table of Handlers
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Game Title ⬍", "Category ⬍", "Author ⬍", "Status ⬍"])
        
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
        self.table.setAlternatingRowColors(True)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        splitter.addWidget(self.table)

        # Right Inspector Panel
        inspector = QGroupBox("Two-Way Handler Inspector")
        insp_layout = QVBoxLayout(inspector)

        self.title_lbl = QLabel("Select a handler to view details")
        self.title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #818cf8;")
        self.title_lbl.setWordWrap(True)
        insp_layout.addWidget(self.title_lbl)

        self.meta_lbl = QLabel("")
        self.meta_lbl.setStyleSheet("color: #9ca3af; font-size: 11px;")
        insp_layout.addWidget(self.meta_lbl)

        self.desc_browser = QTextBrowser()
        self.desc_browser.setOpenExternalLinks(True)
        self.desc_browser.setStyleSheet("background-color: #12131a; border: 1px solid #232533; border-radius: 6px;")
        insp_layout.addWidget(self.desc_browser, stretch=1)

        # Progress bar
        self.prog_bar = QProgressBar()
        self.prog_bar.setRange(0, 0)
        self.prog_bar.setFixedHeight(16)
        self.prog_bar.hide()
        insp_layout.addWidget(self.prog_bar)

        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("font-weight: 600;")
        insp_layout.addWidget(self.status_lbl)

        # Action Buttons Layout (Both Ways)
        btn_layout = QVBoxLayout()

        # Primary Download Row: PartyDeck and Nucleus Co-op
        primary_row = QHBoxLayout()
        self.install_pd_btn = QPushButton("🐧 Install to PartyDeck")
        self.install_pd_btn.setObjectName("primaryBtn")
        self.install_pd_btn.setStyleSheet("background-color: #9333ea; color: #ffffff; font-weight: 600; padding: 9px 12px; border-radius: 6px;")
        self.install_pd_btn.setFixedHeight(38)
        self.install_pd_btn.setEnabled(False)
        self.install_pd_btn.clicked.connect(self.on_install_partydeck_clicked)
        primary_row.addWidget(self.install_pd_btn)

        self.install_nc_btn = QPushButton("🪟 Convert & Install to Nucleus")
        self.install_nc_btn.setStyleSheet("background-color: #2563eb; color: #ffffff; font-weight: 600; padding: 9px 12px; border-radius: 6px;")
        self.install_nc_btn.setFixedHeight(38)
        self.install_nc_btn.setEnabled(False)
        self.install_nc_btn.clicked.connect(self.on_install_nucleus_clicked)
        primary_row.addWidget(self.install_nc_btn)
        btn_layout.addLayout(primary_row)

        # Secondary Export Row
        secondary_row = QHBoxLayout()
        self.export_pd_btn = QPushButton("📦 Export PartyDeck (.json)")
        self.export_pd_btn.setEnabled(False)
        self.export_pd_btn.clicked.connect(self.on_export_partydeck_clicked)
        secondary_row.addWidget(self.export_pd_btn)

        self.export_nc_btn = QPushButton("💾 Export Nucleus (.js)")
        self.export_nc_btn.setEnabled(False)
        self.export_nc_btn.clicked.connect(self.on_export_nucleus_clicked)
        secondary_row.addWidget(self.export_nc_btn)
        btn_layout.addLayout(secondary_row)

        insp_layout.addLayout(btn_layout)

        splitter.addWidget(inspector)
        splitter.setSizes([580, 420])
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

        def get_sort_key(h):
            if self.sort_column == 0:
                return h.get("name", "").lower()
            elif self.sort_column == 1:
                return h.get("category", "").lower()
            elif self.sort_column == 2:
                return h.get("author", "").lower()
            elif self.sort_column == 3:
                name = h.get("name", "")
                is_nc = self.nucleus_mgr.is_installed(name)
                is_pd = self.partydeck_mgr.is_installed(name)
                if is_nc and is_pd: return 3
                if is_nc: return 2
                if is_pd: return 1
                return 0
            return ""

        self.filtered_handlers.sort(key=get_sort_key, reverse=is_reverse)
        self.render_table_rows()

    def refresh_table(self):
        q = self.search_input.text()
        cat = self.cat_combo.currentText()
        self.filtered_handlers = self.community_client.search(query=q, category=cat)
        self.apply_sorting_and_render()

    def render_table_rows(self):
        self.table.setRowCount(len(self.filtered_handlers))

        for row, h in enumerate(self.filtered_handlers):
            name = h.get("name", "Unknown")
            cat = h.get("category", "General")
            author = h.get("author", "Community")

            is_nc = self.nucleus_mgr.is_installed(name)
            is_pd = self.partydeck_mgr.is_installed(name)

            if is_nc and is_pd:
                status_text = "✅ Both Ready"
                status_color = "#34d399"
            elif is_nc:
                status_text = "🪟 In Nucleus"
                status_color = "#60a5fa"
            elif is_pd:
                status_text = "🐧 In PartyDeck"
                status_color = "#c084fc"
            else:
                status_text = "Available"
                status_color = "#9ca3af"

            item_title = QTableWidgetItem(name)
            item_cat = QTableWidgetItem(cat)
            item_author = QTableWidgetItem(author)
            item_status = QTableWidgetItem(status_text)
            item_status.setForeground(QColor(status_color))

            self.table.setItem(row, 0, item_title)
            self.table.setItem(row, 1, item_cat)
            self.table.setItem(row, 2, item_author)
            self.table.setItem(row, 3, item_status)

        if self.filtered_handlers:
            self.table.selectRow(0)

    def on_selection_changed(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            self.selected_handler = None
            self.install_pd_btn.setEnabled(False)
            self.install_nc_btn.setEnabled(False)
            self.export_pd_btn.setEnabled(False)
            self.export_nc_btn.setEnabled(False)
            return

        row = selected_rows[0].row()
        h = self.filtered_handlers[row]
        self.selected_handler = h

        name = h.get("name", "Unknown")
        author = h.get("author", "Community")
        category = h.get("category", "General")
        desc = h.get("description", "No details available.")
        source = h.get("source", "")

        self.title_lbl.setText(name)
        self.meta_lbl.setText(f"Author: @{author} | Category: {category} | Max Players: {h.get('max_players', 4)}")

        source_link = f"<p><b>Source Discussion:</b> <a href='{source}'>{source}</a></p>" if source.startswith("http") else f"<p><b>Source:</b> {source}</p>"
        html = f"""
        <p><b>Configuration Overview:</b></p>
        <ul>
          <li><b>Executable:</b> <code>{h.get('exec', 'Game.exe')}</code></li>
          <li><b>Steam AppID:</b> <code>{h.get('steam_appid') or 'None'}</code></li>
          <li><b>Runtime:</b> <code>{h.get('runtime', 'umu')}</code></li>
          <li><b>LAN Emulation:</b> <code>{'Goldberg' if h.get('use_goldberg') else 'Native LAN'}</code></li>
          <li><b>Arguments:</b> <code>{h.get('args', 'None')}</code></li>
          <li><b>Environment:</b> <code>{h.get('env', 'None')}</code></li>
        </ul>
        <hr>
        <p><b>Description & Setup Guide:</b></p>
        <p>{desc.replace(chr(10), '<br>')}</p>
        {source_link}
        """
        self.desc_browser.setHtml(html)

        self.install_pd_btn.setEnabled(True)
        self.install_nc_btn.setEnabled(True)
        self.export_pd_btn.setEnabled(True)
        self.export_nc_btn.setEnabled(True)

        is_nc = self.nucleus_mgr.is_installed(name)
        is_pd = self.partydeck_mgr.is_installed(name)

        if is_nc and is_pd:
            self.status_lbl.setText("Status: Ready in both Nucleus Co-op and PartyDeck")
            self.status_lbl.setStyleSheet("color: #34d399;")
        elif is_nc:
            self.status_lbl.setText("Status: Installed in Nucleus Co-op handlers")
            self.status_lbl.setStyleSheet("color: #60a5fa;")
        elif is_pd:
            self.status_lbl.setText("Status: Installed in PartyDeck handlers")
            self.status_lbl.setStyleSheet("color: #c084fc;")
        else:
            self.status_lbl.setText("Status: Ready for 1-click download to either platform")
            self.status_lbl.setStyleSheet("color: #9ca3af;")

    def on_install_partydeck_clicked(self):
        """Install handler directly to PartyDeck."""
        if not self.selected_handler:
            return
        h = self.selected_handler
        clean_name = h.get("name", "Game").strip()
        pd_data = {
            "name": clean_name,
            "author": h.get("author", "Community"),
            "version": "1.0",
            "info": h.get("description", ""),
            "spec_ver": 3,
            "path_gameroot": "",
            "runtime": h.get("runtime", "umu"),
            "exec": h.get("exec", "Game.exe"),
            "args": h.get("args", ""),
            "env": h.get("env", ""),
            "sdl2_override": "No",
            "pause_between_starts": 5.0,
            "use_mangohud": False,
            "use_goldberg": h.get("use_goldberg", True),
            "ps_xinput": True,
            "steam_appid": h.get("steam_appid"),
            "game_null_paths": [],
            "overrides": {}
        }
        self.partydeck_mgr.save_handler(clean_name, pd_data)
        QMessageBox.information(self, "Installed", f"Handler '{clean_name}' has been installed to PartyDeck!")
        self.refresh_table()
        self.handler_installed_signal.emit()

    def on_install_nucleus_clicked(self):
        """Convert PartyDeck handler and install directly to Nucleus Co-op."""
        if not self.selected_handler:
            return
        h = self.selected_handler
        clean_name = h.get("name", "Game").strip()
        js_code = partydeck_to_nucleus_js(h)
        dest_path = self.nucleus_mgr.save_handler_js(clean_name, js_code)
        QMessageBox.information(
            self, "Installed to Nucleus",
            f"Successfully converted and installed '{clean_name}' to Nucleus Co-op handlers!\nSaved to:\n{dest_path}"
        )
        self.refresh_table()
        self.nucleus_handler_installed_signal.emit()

    def on_export_nucleus_clicked(self):
        """Export handler directly to .js for Nucleus Co-op."""
        if not self.selected_handler:
            return
        h = self.selected_handler
        js_code = partydeck_to_nucleus_js(h)
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Nucleus Handler", f"{h['name']}.js", "JavaScript (*.js)"
        )
        if file_path:
            Path(file_path).write_text(js_code, encoding="utf-8")
            QMessageBox.information(self, "Export Complete", f"Generated Nucleus Co-op handler for '{h['name']}'!\nSaved to:\n{file_path}")

    def on_export_partydeck_clicked(self):
        """Export PartyDeck JSON or package."""
        if not self.selected_handler:
            return
        h = self.selected_handler
        clean_name = h.get("name", "Game").strip()
        pd_data = {
            "name": clean_name,
            "author": h.get("author", "Community"),
            "version": "1.0",
            "info": h.get("description", ""),
            "spec_ver": 3,
            "path_gameroot": "",
            "runtime": h.get("runtime", "umu"),
            "exec": h.get("exec", "Game.exe"),
            "args": h.get("args", ""),
            "env": h.get("env", ""),
            "sdl2_override": "No",
            "pause_between_starts": 5.0,
            "use_mangohud": False,
            "use_goldberg": h.get("use_goldberg", True),
            "ps_xinput": True,
            "steam_appid": h.get("steam_appid"),
            "game_null_paths": [],
            "overrides": {}
        }
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save PartyDeck Handler", f"{clean_name}.json", "JSON (*.json);;PartyDeck Package (*.pd2)"
        )
        if file_path:
            if file_path.endswith(".pd2"):
                export_partydeck_package(pd_data, file_path)
            else:
                Path(file_path).write_text(json.dumps(pd_data, indent=2), encoding="utf-8")
            QMessageBox.information(self, "Export Complete", f"Saved PartyDeck handler for '{clean_name}'!\nSaved to:\n{file_path}")

    def on_sync_github(self):
        self.prog_bar.show()
        self.fetch_btn.setEnabled(False)
        self.worker = LiveFetchWorker(self.community_client)
        self.worker.finished_signal.connect(self.on_sync_finished)
        self.worker.start()

    def on_sync_finished(self, updated_list):
        self.prog_bar.hide()
        self.fetch_btn.setEnabled(True)
        self.cat_combo.clear()
        self.cat_combo.addItem("All Categories")
        for cat in self.community_client.get_categories():
            self.cat_combo.addItem(cat)
        self.refresh_table()
        QMessageBox.information(self, "Sync Complete", f"Successfully synced {len(updated_list)} community handlers from GitHub!")
