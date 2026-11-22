"""
PartyDeck Community Handlers Browser Tab.
Allows users to browse PartyDeck community handlers just like the Nucleus Co-op Hub,
with 1-click install into PartyDeck or export to Nucleus Co-op format.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QGroupBox, QTextBrowser, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from crosscoop.core.partydeck_community import PartyDeckCommunityClient
from crosscoop.core.converter import partydeck_to_nucleus_js, export_nucleus_package

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

    def __init__(self, partydeck_mgr, parent=None):
        super().__init__(parent)
        self.partydeck_mgr = partydeck_mgr
        self.community_client = PartyDeckCommunityClient()
        self.filtered_handlers = []
        self.selected_handler = None
        self.worker = None

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

        self.fetch_btn = QPushButton("🔄 Sync Latest from GitHub")
        self.fetch_btn.setToolTip("Fetch newly posted [Handler Release] issues from partydeck/partydeck")
        self.fetch_btn.clicked.connect(self.on_sync_github)
        filter_bar.addWidget(self.fetch_btn)

        main_layout.addLayout(filter_bar)

        self.prog_bar = QProgressBar()
        self.prog_bar.setRange(0, 0)
        self.prog_bar.setFixedHeight(14)
        self.prog_bar.hide()
        main_layout.addWidget(self.prog_bar)

        # Splitter: Table Left, Details Right
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Games Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Game Title", "Category", "Author", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        splitter.addWidget(self.table)

        # Right Inspector Panel
        inspector = QGroupBox("PartyDeck Handler Details & Actions")
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

        # Buttons
        btn_layout = QVBoxLayout()
        self.install_btn = QPushButton("⚡ Install to PartyDeck")
        self.install_btn.setObjectName("primaryBtn")
        self.install_btn.setFixedHeight(36)
        self.install_btn.setEnabled(False)
        self.install_btn.clicked.connect(self.on_install_clicked)
        btn_layout.addWidget(self.install_btn)

        self.export_nucleus_btn = QPushButton("🔄 Convert to Nucleus Co-op Handler (.js)")
        self.export_nucleus_btn.setEnabled(False)
        self.export_nucleus_btn.clicked.connect(self.on_export_nucleus_clicked)
        btn_layout.addWidget(self.export_nucleus_btn)

        insp_layout.addLayout(btn_layout)

        splitter.addWidget(inspector)
        splitter.setSizes([580, 400])
        main_layout.addWidget(splitter, stretch=1)

    def refresh_table(self):
        q = self.search_input.text()
        cat = self.cat_combo.currentText()
        if cat == "All Categories":
            cat = "All"

        self.filtered_handlers = self.community_client.search(query=q, category=cat)
        self.table.setRowCount(len(self.filtered_handlers))

        for row, h in enumerate(self.filtered_handlers):
            name = h.get("name", "Unknown")
            category = h.get("category", "General")
            author = h.get("author", "Community")
            is_inst = self.partydeck_mgr.is_installed(name)
            status_text = "✅ Installed" if is_inst else "Available"

            item_name = QTableWidgetItem(name)
            item_cat = QTableWidgetItem(category)
            item_author = QTableWidgetItem(author)
            item_status = QTableWidgetItem(status_text)
            
            if is_inst:
                item_status.setForeground(QColor("#34d399"))
            else:
                item_status.setForeground(QColor("#9ca3af"))

            self.table.setItem(row, 0, item_name)
            self.table.setItem(row, 1, item_cat)
            self.table.setItem(row, 2, item_author)
            self.table.setItem(row, 3, item_status)

        if self.filtered_handlers:
            self.table.selectRow(0)

    def on_selection_changed(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            self.selected_handler = None
            self.install_btn.setEnabled(False)
            self.export_nucleus_btn.setEnabled(False)
            return

        row = selected_rows[0].row()
        self.selected_handler = self.filtered_handlers[row]
        h = self.selected_handler

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

        self.install_btn.setEnabled(True)
        self.export_nucleus_btn.setEnabled(True)

        is_inst = self.partydeck_mgr.is_installed(name)
        if is_inst:
            self.install_btn.setText("🔄 Update / Re-install Handler")
        else:
            self.install_btn.setText("⚡ Install to PartyDeck")

    def on_install_clicked(self):
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

    def on_export_nucleus_clicked(self):
        if not self.selected_handler:
            return
        h = self.selected_handler
        from PyQt6.QtWidgets import QFileDialog
        
        js_code = partydeck_to_nucleus_js(h)
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Nucleus Handler", f"{h['name']}.js", "JavaScript (*.js)"
        )
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(js_code)
            QMessageBox.information(self, "Export Complete", f"Generated Nucleus Co-op handler for '{h['name']}'!\nSaved to:\n{file_path}")

    def on_sync_github(self):
        self.prog_bar.show()
        self.fetch_btn.setEnabled(False)
        self.worker = LiveFetchWorker(self.community_client)
        self.worker.finished_signal.connect(self.on_sync_finished)
        self.worker.start()

    def on_sync_finished(self, updated_list):
        self.prog_bar.hide()
        self.fetch_btn.setEnabled(True)
        # Refresh category filter
        self.cat_combo.clear()
        self.cat_combo.addItem("All Categories")
        for cat in self.community_client.get_categories():
            self.cat_combo.addItem(cat)
        self.refresh_table()
        QMessageBox.information(self, "Sync Complete", f"Successfully synced {len(updated_list)} community handlers from GitHub!")
