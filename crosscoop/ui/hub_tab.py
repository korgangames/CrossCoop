"""
Nucleus Co-op Hub Browser Tab (896 Games).
Allows searching, previewing, and two-way downloading:
- Directly download to Nucleus Co-op (Windows / Wine)
- Convert & install into PartyDeck (Linux / SteamOS)
- Export to either format (.js, .zip, .pd2, .json)
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QGroupBox, QTextBrowser, QMessageBox, QProgressBar,
    QDialog, QFormLayout, QDialogButtonBox, QSpinBox, QCheckBox, QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from pathlib import Path

from crosscoop.core.nucleus_manager import NucleusManager
from crosscoop.core.converter import parse_nucleus_js, export_partydeck_package, export_nucleus_package

class HubSyncWorker(QThread):
    finished_signal = pyqtSignal(int, int)
    progress_signal = pyqtSignal(str)

    def __init__(self, hub_client):
        super().__init__()
        self.hub_client = hub_client

    def run(self):
        new_cnt, upd_cnt = self.hub_client.sync_from_live_hub(lambda msg: self.progress_signal.emit(msg))
        self.finished_signal.emit(new_cnt, upd_cnt)


class ConvertPartyDeckWorker(QThread):
    finished_signal = pyqtSignal(bool, str, dict)
    progress_signal = pyqtSignal(str)

    def __init__(self, hub_client, partydeck_mgr, handler_id, handler_meta, custom_params=None):
        super().__init__()
        self.hub_client = hub_client
        self.partydeck_mgr = partydeck_mgr
        self.handler_id = handler_id
        self.handler_meta = handler_meta
        self.custom_params = custom_params

    def run(self):
        try:
            self.progress_signal.emit("Downloading Nucleus handler package...")
            pkg_id = self.handler_meta.get("currentPackage")
            if not pkg_id:
                self.finished_signal.emit(False, "No package ID found for this game.", {})
                return

            js_code = self.hub_client.extract_handler_js(pkg_id)
            if not js_code:
                self.finished_signal.emit(False, "Could not extract handler.js from package.", {})
                return

            self.progress_signal.emit("Parsing parameters and generating PartyDeck manifest...")
            pd_data = parse_nucleus_js(js_code, self.handler_meta)

            if self.custom_params:
                pd_data.update(self.custom_params)

            self.progress_signal.emit("Installing handler to PartyDeck...")
            self.partydeck_mgr.save_handler(pd_data["name"], pd_data)

            self.finished_signal.emit(True, f"Successfully installed '{pd_data['name']}' to PartyDeck!", pd_data)
        except Exception as e:
            self.finished_signal.emit(False, f"Error during conversion: {str(e)}", {})


class DownloadNucleusWorker(QThread):
    finished_signal = pyqtSignal(bool, str)
    progress_signal = pyqtSignal(str)

    def __init__(self, hub_client, nucleus_mgr, handler_meta):
        super().__init__()
        self.hub_client = hub_client
        self.nucleus_mgr = nucleus_mgr
        self.handler_meta = handler_meta

    def run(self):
        try:
            self.progress_signal.emit("Downloading official Nucleus Co-op package...")
            pkg_id = self.handler_meta.get("currentPackage")
            if not pkg_id:
                self.finished_signal.emit(False, "No package ID found for this game.")
                return

            pkg_bytes = self.hub_client.fetch_handler_package(pkg_id)
            gname = self.handler_meta.get("gameName", "Unknown Game")

            self.progress_signal.emit("Saving package to Nucleus Co-op handlers...")
            # Save package zip
            self.nucleus_mgr.save_handler_package(gname, pkg_bytes)

            # Also extract and save readable .js file
            js_code = self.hub_client.extract_handler_js(pkg_id)
            if js_code:
                self.nucleus_mgr.save_handler_js(gname, js_code)

            self.finished_signal.emit(True, f"Downloaded and installed '{gname}' to Nucleus Co-op handlers directory!")
        except Exception as e:
            self.finished_signal.emit(False, f"Download error: {str(e)}")


class CustomizeDialog(QDialog):
    def __init__(self, pd_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Customize Handler: {pd_data['name']}")
        self.setMinimumWidth(450)
        self.pd_data = dict(pd_data)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit(self.pd_data.get("name", ""))
        self.exec_edit = QLineEdit(self.pd_data.get("exec", ""))
        self.appid_edit = QSpinBox()
        self.appid_edit.setMaximum(99999999)
        self.appid_edit.setValue(self.pd_data.get("steam_appid") or 0)
        self.args_edit = QLineEdit(self.pd_data.get("args", ""))
        self.runtime_cb = QComboBox()
        self.runtime_cb.addItems(["umu", "native", "proton"])
        self.runtime_cb.setCurrentText(self.pd_data.get("runtime", "umu"))
        self.goldberg_chk = QCheckBox("Enable Goldberg Steam LAN Emulation")
        self.goldberg_chk.setChecked(self.pd_data.get("use_goldberg", True))
        self.pause_spin = QSpinBox()
        self.pause_spin.setValue(int(self.pd_data.get("pause_between_starts", 5)))

        form.addRow("Game Name:", self.name_edit)
        form.addRow("Executable:", self.exec_edit)
        form.addRow("Steam AppID:", self.appid_edit)
        form.addRow("Start Arguments:", self.args_edit)
        form.addRow("Runtime:", self.runtime_cb)
        form.addRow("LAN Emulation:", self.goldberg_chk)
        form.addRow("Pause (seconds):", self.pause_spin)

        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_custom_data(self):
        appid = self.appid_edit.value()
        return {
            "name": self.name_edit.text().strip(),
            "exec": self.exec_edit.text().strip(),
            "steam_appid": appid if appid > 0 else None,
            "args": self.args_edit.text().strip(),
            "runtime": self.runtime_cb.currentText(),
            "use_goldberg": self.goldberg_chk.isChecked(),
            "pause_between_starts": float(self.pause_spin.value())
        }


class HubTab(QWidget):
    handler_installed_signal = pyqtSignal()
    nucleus_handler_installed_signal = pyqtSignal()
    database_synced_signal = pyqtSignal(int)

    def __init__(self, hub_client, partydeck_mgr, nucleus_mgr=None, parent=None):
        super().__init__(parent)
        self.hub_client = hub_client
        self.partydeck_mgr = partydeck_mgr
        self.nucleus_mgr = nucleus_mgr if nucleus_mgr else NucleusManager()
        self.selected_handler = None
        self.filtered_results = []
        self.worker_pd = None
        self.worker_nc = None
        self.sync_worker = None

        # Default sort: Downloads descending
        self.sort_column = 3
        self.sort_order = Qt.SortOrder.DescendingOrder

        self.setup_ui()
        self.refresh_table()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Filters Row
        filter_bar = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(f"🔍 Search {len(self.hub_client.games)} Nucleus Co-op games by title...")
        self.search_input.textChanged.connect(self.refresh_table)
        filter_bar.addWidget(self.search_input, stretch=3)

        self.genre_combo = QComboBox()
        self.genre_combo.addItem("All Genres")
        for g in self.hub_client.get_all_genres():
            self.genre_combo.addItem(g)
        self.genre_combo.currentTextChanged.connect(self.refresh_table)
        filter_bar.addWidget(self.genre_combo, stretch=1)

        self.players_combo = QComboBox()
        self.players_combo.addItems(["Any Players", "2+ Players", "4+ Players", "8+ Players"])
        self.players_combo.currentIndexChanged.connect(self.refresh_table)
        filter_bar.addWidget(self.players_combo, stretch=1)

        self.sync_btn = QPushButton("🔄 Sync Hub")
        self.sync_btn.setToolTip("Poll the live SplitScreen.Me Hub to fetch newly published games and updates")
        self.sync_btn.clicked.connect(self.on_sync_hub)
        filter_bar.addWidget(self.sync_btn)

        main_layout.addLayout(filter_bar)

        # Main horizontal splitter (Catalog Table on Left, Inspector on Right)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Games Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Game Title ⬍", "Players ⬍", "Input ⬍", "Downloads ⬍", "Status ⬍"
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
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
        inspector = QGroupBox("Two-Way Game & Handler Inspector")
        insp_layout = QVBoxLayout(inspector)

        self.title_lbl = QLabel("Select a game to inspect")
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
        self.prog_bar.setTextVisible(True)
        self.prog_bar.setFixedHeight(18)
        self.prog_bar.hide()
        insp_layout.addWidget(self.prog_bar)

        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("font-weight: 600;")
        insp_layout.addWidget(self.status_lbl)

        # Action Buttons Layout (Both Ways)
        btn_layout = QVBoxLayout()

        # Primary Download Row: Nucleus and PartyDeck
        primary_row = QHBoxLayout()
        self.install_nc_btn = QPushButton("🪟 Download to Nucleus Co-op")
        self.install_nc_btn.setStyleSheet("background-color: #2563eb; color: #ffffff; font-weight: 600; padding: 9px 12px; border-radius: 6px;")
        self.install_nc_btn.setEnabled(False)
        self.install_nc_btn.clicked.connect(self.on_download_nucleus_clicked)
        primary_row.addWidget(self.install_nc_btn)

        self.install_pd_btn = QPushButton("🐧 Convert & Install to PartyDeck")
        self.install_pd_btn.setObjectName("primaryBtn")
        self.install_pd_btn.setStyleSheet("background-color: #9333ea; color: #ffffff; font-weight: 600; padding: 9px 12px; border-radius: 6px;")
        self.install_pd_btn.setFixedHeight(38)
        self.install_pd_btn.setEnabled(False)
        self.install_pd_btn.clicked.connect(self.on_convert_partydeck_clicked)
        primary_row.addWidget(self.install_pd_btn)
        btn_layout.addLayout(primary_row)

        # Secondary Export Row
        secondary_btns = QHBoxLayout()
        self.custom_btn = QPushButton("⚙️ Customize...")
        self.custom_btn.setEnabled(False)
        self.custom_btn.clicked.connect(self.on_customize_clicked)
        secondary_btns.addWidget(self.custom_btn)

        self.export_nc_btn = QPushButton("💾 Export Nucleus (.js)")
        self.export_nc_btn.setEnabled(False)
        self.export_nc_btn.clicked.connect(self.on_export_nucleus_clicked)
        secondary_btns.addWidget(self.export_nc_btn)

        self.export_pd_btn = QPushButton("📦 Export PartyDeck (.pd2)")
        self.export_pd_btn.setEnabled(False)
        self.export_pd_btn.clicked.connect(self.on_export_partydeck_clicked)
        secondary_btns.addWidget(self.export_pd_btn)

        btn_layout.addLayout(secondary_btns)
        insp_layout.addLayout(btn_layout)

        splitter.addWidget(inspector)
        splitter.setSizes([600, 420])
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
            if logical_index in [1, 3]:
                self.sort_order = Qt.SortOrder.DescendingOrder
            else:
                self.sort_order = Qt.SortOrder.AscendingOrder

        self.table.horizontalHeader().setSortIndicator(self.sort_column, self.sort_order)
        self.apply_sorting_and_render()

    def apply_sorting_and_render(self):
        is_reverse = (self.sort_order == Qt.SortOrder.DescendingOrder)

        def get_sort_key(item):
            hid, h = item
            if self.sort_column == 0:
                return h.get("gameName", "").lower()
            elif self.sort_column == 1:
                p = h.get("maxPlayers", 0)
                return int(p) if isinstance(p, int) else 0
            elif self.sort_column == 2:
                c = 1 if h.get("playableControllers") else 0
                k = 1 if h.get("playableMouseKeyboard") else 0
                return (c * 2 + k)
            elif self.sort_column == 3:
                d = h.get("downloadCount", 0)
                return int(d) if isinstance(d, int) else 0
            elif self.sort_column == 4:
                gname = h.get("gameName", "")
                is_nc = self.nucleus_mgr.is_installed(gname)
                is_pd = self.partydeck_mgr.is_installed(gname)
                if is_nc and is_pd: return 3
                if is_nc: return 2
                if is_pd: return 1
                return 0
            return ""

        self.filtered_results.sort(key=get_sort_key, reverse=is_reverse)
        self.render_table_rows()

    def refresh_table(self):
        query = self.search_input.text()
        genre = self.genre_combo.currentText()
        if genre == "All Genres":
            genre = "All"
        
        min_p = 0
        p_idx = self.players_combo.currentIndex()
        if p_idx == 1: min_p = 2
        elif p_idx == 2: min_p = 4
        elif p_idx == 3: min_p = 8

        self.filtered_results = self.hub_client.search(query=query, genre=genre, min_players=min_p)
        self.apply_sorting_and_render()

    def render_table_rows(self):
        self.table.setRowCount(len(self.filtered_results))

        for row, (hid, h) in enumerate(self.filtered_results):
            gname = h.get("gameName", "Unknown")
            players = str(h.get("maxPlayers", "-"))
            
            inputs = []
            if h.get("playableControllers"): inputs.append("🎮")
            if h.get("playableMouseKeyboard"): inputs.append("⌨️")
            input_str = " ".join(inputs)

            downloads = f"{h.get('downloadCount', 0):,}"
            
            is_nc = self.nucleus_mgr.is_installed(gname)
            is_pd = self.partydeck_mgr.is_installed(gname)

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

            item_title = QTableWidgetItem(gname)
            item_players = QTableWidgetItem(players)
            item_players.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_input = QTableWidgetItem(input_str)
            item_input.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_dl = QTableWidgetItem(downloads)
            item_dl.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_status = QTableWidgetItem(status_text)
            item_status.setForeground(QColor(status_color))

            self.table.setItem(row, 0, item_title)
            self.table.setItem(row, 1, item_players)
            self.table.setItem(row, 2, item_input)
            self.table.setItem(row, 3, item_dl)
            self.table.setItem(row, 4, item_status)

        if self.filtered_results:
            self.table.selectRow(0)

    def on_selection_changed(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            self.selected_handler = None
            self.install_nc_btn.setEnabled(False)
            self.install_pd_btn.setEnabled(False)
            self.custom_btn.setEnabled(False)
            self.export_nc_btn.setEnabled(False)
            self.export_pd_btn.setEnabled(False)
            return

        row = selected_rows[0].row()
        hid, h = self.filtered_results[row]
        self.selected_handler = (hid, h)

        gname = h.get("gameName", "Unknown")
        author = h.get("ownerName", "Unknown")
        stars = h.get("stars", 0)
        dls = h.get("downloadCount", 0)
        genres = ", ".join(h.get("genres", []))
        desc = h.get("description", "No description provided.")

        self.title_lbl.setText(gname)
        self.meta_lbl.setText(f"Author: {author} | ⭐ {stars} | ⬇️ {dls:,} downloads\nGenres: {genres}")
        
        html = f"""
        <p><b>Description / Handler Guide:</b></p>
        <p>{desc.replace(chr(10), '<br>')}</p>
        <hr>
        <p><b>Max Players:</b> {h.get('maxPlayers', 4)}</p>
        <p><b>Hub ID:</b> {hid} | <b>Package:</b> {h.get('currentPackage')}</p>
        """
        self.desc_browser.setHtml(html)

        self.install_nc_btn.setEnabled(True)
        self.install_pd_btn.setEnabled(True)
        self.custom_btn.setEnabled(True)
        self.export_nc_btn.setEnabled(True)
        self.export_pd_btn.setEnabled(True)

        is_nc = self.nucleus_mgr.is_installed(gname)
        is_pd = self.partydeck_mgr.is_installed(gname)

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

    def on_sync_hub(self):
        self.prog_bar.setRange(0, 0)
        self.prog_bar.show()
        self.sync_btn.setEnabled(False)
        self.status_lbl.setText("Polling live SplitScreen.Me Hub...")

        self.sync_worker = HubSyncWorker(self.hub_client)
        self.sync_worker.progress_signal.connect(lambda msg: self.status_lbl.setText(msg))
        self.sync_worker.finished_signal.connect(self.on_sync_hub_finished)
        self.sync_worker.start()

    def on_sync_hub_finished(self, new_cnt, upd_cnt):
        self.prog_bar.hide()
        self.sync_btn.setEnabled(True)
        total = len(self.hub_client.games)
        self.search_input.setPlaceholderText(f"🔍 Search {total} Nucleus Co-op games by title...")
        self.refresh_table()
        self.database_synced_signal.emit(total)

        msg = f"Hub synchronization finished!\n\n• Total Games in Library: {total}\n• New Handlers Added: {new_cnt}\n• Handlers Updated: {upd_cnt}"
        QMessageBox.information(self, "Live Hub Synchronized", msg)

    def on_download_nucleus_clicked(self):
        """Direct 1-click download to Nucleus Co-op handlers."""
        if not self.selected_handler:
            return

        hid, h = self.selected_handler
        self.prog_bar.setRange(0, 0)
        self.prog_bar.show()
        self.install_nc_btn.setEnabled(False)

        self.worker_nc = DownloadNucleusWorker(self.hub_client, self.nucleus_mgr, h)
        self.worker_nc.progress_signal.connect(lambda msg: self.status_lbl.setText(msg))
        self.worker_nc.finished_signal.connect(self.on_download_nucleus_finished)
        self.worker_nc.start()

    def on_download_nucleus_finished(self, success, message):
        self.prog_bar.hide()
        self.install_nc_btn.setEnabled(True)
        if success:
            self.status_lbl.setText("Downloaded to Nucleus Co-op!")
            self.status_lbl.setStyleSheet("color: #60a5fa;")
            QMessageBox.information(self, "Nucleus Download Complete", message)
            self.refresh_table()
            self.nucleus_handler_installed_signal.emit()
        else:
            self.status_lbl.setText("Download failed.")
            self.status_lbl.setStyleSheet("color: #f87171;")
            QMessageBox.warning(self, "Download Failed", message)

    def on_convert_partydeck_clicked(self, custom_params=None):
        """Direct 1-click convert and install to PartyDeck."""
        if not self.selected_handler:
            return

        hid, h = self.selected_handler
        self.prog_bar.setRange(0, 0)
        self.prog_bar.show()
        self.install_pd_btn.setEnabled(False)

        self.worker_pd = ConvertPartyDeckWorker(self.hub_client, self.partydeck_mgr, hid, h, custom_params)
        self.worker_pd.progress_signal.connect(lambda msg: self.status_lbl.setText(msg))
        self.worker_pd.finished_signal.connect(self.on_convert_partydeck_finished)
        self.worker_pd.start()

    def on_convert_partydeck_finished(self, success, message, pd_data):
        self.prog_bar.hide()
        self.install_pd_btn.setEnabled(True)
        if success:
            self.status_lbl.setText("Installed to PartyDeck!")
            self.status_lbl.setStyleSheet("color: #34d399;")
            QMessageBox.information(self, "PartyDeck Install Complete", message)
            self.refresh_table()
            self.handler_installed_signal.emit()
        else:
            self.status_lbl.setText("PartyDeck conversion failed.")
            self.status_lbl.setStyleSheet("color: #f87171;")
            QMessageBox.warning(self, "Conversion Failed", message)

    def on_customize_clicked(self):
        if not self.selected_handler:
            return
        hid, h = self.selected_handler
        pkg_id = h.get("currentPackage")
        if not pkg_id:
            return

        js = self.hub_client.extract_handler_js(pkg_id)
        pd_data = parse_nucleus_js(js, h)

        dlg = CustomizeDialog(pd_data, self)
        if dlg.exec():
            custom = dlg.get_custom_data()
            self.on_convert_partydeck_clicked(custom_params=custom)

    def on_export_nucleus_clicked(self):
        """Export handler directly to .js or package for Nucleus Co-op."""
        if not self.selected_handler:
            return
        hid, h = self.selected_handler
        pkg_id = h.get("currentPackage")
        js_code = self.hub_client.extract_handler_js(pkg_id)
        gname = h.get("gameName", "CustomGame")

        out_file, _ = QFileDialog.getSaveFileName(
            self, "Export Nucleus Co-op Handler",
            f"{gname}.js", "JavaScript Handler (*.js);;Nucleus Package (*.zip)"
        )
        if out_file:
            if out_file.endswith(".zip") or out_file.endswith(".nc"):
                export_nucleus_package(js_code, out_file)
            else:
                Path(out_file).write_text(js_code, encoding="utf-8")
            QMessageBox.information(self, "Exported", f"Successfully exported Nucleus handler to:\n{out_file}")

    def on_export_partydeck_clicked(self):
        """Export converted PartyDeck package."""
        if not self.selected_handler:
            return
        hid, h = self.selected_handler
        pkg_id = h.get("currentPackage")
        js = self.hub_client.extract_handler_js(pkg_id)
        pd_data = parse_nucleus_js(js, h)

        out_file, _ = QFileDialog.getSaveFileName(
            self, "Export PartyDeck Package (.pd2)",
            f"{pd_data['name']}.pd2", "PartyDeck Package (*.pd2);;JSON Manifest (*.json)"
        )
        if out_file:
            if out_file.endswith(".pd2"):
                export_partydeck_package(pd_data, out_file)
            else:
                import json
                Path(out_file).write_text(json.dumps(pd_data, indent=2), encoding="utf-8")
            QMessageBox.information(self, "Exported", f"Successfully exported PartyDeck package to:\n{out_file}")
