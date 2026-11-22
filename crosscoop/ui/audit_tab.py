"""
Pre-Flight Stability Audit & Diagnostic Tab.
Runs 7 comprehensive checks to ensure split-screen handlers are stable before game launch.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QTextBrowser, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from crosscoop.core.diagnostics import PreFlightAuditor

class AuditWorker(QThread):
    finished_signal = pyqtSignal(list)

    def __init__(self, auditor, handler_data, player_count):
        super().__init__()
        self.auditor = auditor
        self.handler_data = handler_data
        self.player_count = player_count

    def run(self):
        results = self.auditor.run_full_audit(self.handler_data, self.player_count)
        self.finished_signal.emit(results)


class AuditTab(QWidget):
    def __init__(self, partydeck_mgr, hub_client, parent=None):
        super().__init__(parent)
        self.partydeck_mgr = partydeck_mgr
        self.hub_client = hub_client
        self.auditor = PreFlightAuditor(partydeck_mgr)
        self.current_results = []
        self.worker = None

        self.setup_ui()
        self.populate_handler_selector()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header Description
        header_box = QVBoxLayout()
        title = QLabel("🛡️ Pre-Flight Stability Audit & Handler Diagnostics")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #818cf8;")
        desc = QLabel("Conducts 7 intensive verification phases (binary paths, controller enumeration, sandbox isolation, port collision, Gamescope geometry, and Steam LAN integrity) before launching.")
        desc.setStyleSheet("color: #9ca3af; font-size: 12px;")
        desc.setWordWrap(True)
        header_box.addWidget(title)
        header_box.addWidget(desc)
        main_layout.addLayout(header_box)

        # Controls Bar
        ctrl_group = QGroupBox("Target Configuration & Audit Parameters")
        ctrl_layout = QHBoxLayout(ctrl_group)

        ctrl_layout.addWidget(QLabel("Select Handler:"))
        self.handler_combo = QComboBox()
        self.handler_combo.setMinimumWidth(260)
        self.handler_combo.currentIndexChanged.connect(self.on_handler_selected)
        ctrl_layout.addWidget(self.handler_combo, stretch=2)

        refresh_btn = QPushButton("🔄")
        refresh_btn.setToolTip("Refresh Handler List")
        refresh_btn.clicked.connect(self.populate_handler_selector)
        ctrl_layout.addWidget(refresh_btn)

        ctrl_layout.addWidget(QLabel("Player Count:"))
        self.player_spin = QSpinBox()
        self.player_spin.setRange(2, 8)
        self.player_spin.setValue(2)
        ctrl_layout.addWidget(self.player_spin)

        self.run_btn = QPushButton("🚀 Run Intensive Stability Audit")
        self.run_btn.setObjectName("primaryBtn")
        self.run_btn.setFixedHeight(36)
        self.run_btn.clicked.connect(self.run_audit)
        ctrl_layout.addWidget(self.run_btn, stretch=1)

        main_layout.addWidget(ctrl_group)

        # Progress bar
        self.prog_bar = QProgressBar()
        self.prog_bar.setRange(0, 0)
        self.prog_bar.setFixedHeight(14)
        self.prog_bar.hide()
        main_layout.addWidget(self.prog_bar)

        # Results Table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["Test Phase", "Status", "Diagnostic Summary"])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.results_table.itemSelectionChanged.connect(self.on_result_selected)
        main_layout.addWidget(self.results_table, stretch=2)

        # Details Browser
        self.details_browser = QTextBrowser()
        self.details_browser.setStyleSheet("background-color: #12131a; border: 1px solid #232533; border-radius: 6px;")
        self.details_browser.setMaximumHeight(140)
        self.details_browser.setPlaceholderText("Select any test row above to view technical details, failure traces, or automated remediation recommendations.")
        main_layout.addWidget(self.details_browser, stretch=1)

    def populate_handler_selector(self):
        self.handler_combo.clear()
        installed = self.partydeck_mgr.get_installed_handlers()
        for h in installed:
            name = h["data"].get("name", h["folder_name"])
            self.handler_combo.addItem(f"🐧 PartyDeck: {name}", h["data"])

        # Also add sample popular games from Nucleus
        for hid, h in list(self.hub_client.games.items())[:20]:
            name = h.get("gameName", "Unknown")
            meta = {
                "name": name,
                "exec": f"{name.replace(' ', '')}.exe",
                "steam_appid": 1000,
                "use_goldberg": True,
                "runtime": "umu",
                "args": "-windowed"
            }
            self.handler_combo.addItem(f"📦 Nucleus Hub: {name}", meta)

    def on_handler_selected(self):
        pass

    def run_audit(self):
        idx = self.handler_combo.currentIndex()
        if idx < 0:
            return

        handler_data = self.handler_combo.currentData()
        players = self.player_spin.value()

        self.prog_bar.show()
        self.run_btn.setEnabled(False)

        self.worker = AuditWorker(self.auditor, handler_data, players)
        self.worker.finished_signal.connect(self.on_audit_finished)
        self.worker.start()

    def on_audit_finished(self, results):
        self.prog_bar.hide()
        self.run_btn.setEnabled(True)
        self.current_results = results

        self.results_table.setRowCount(len(results))
        pass_count = sum(1 for r in results if r.status == "PASS")
        warn_count = sum(1 for r in results if r.status == "WARN")
        fail_count = sum(1 for r in results if r.status == "FAIL")

        for row, res in enumerate(results):
            phase_item = QTableWidgetItem(res.title)
            
            # Status badge item
            if res.status == "PASS":
                status_item = QTableWidgetItem("🟢 PASS")
                status_item.setForeground(QColor("#34d399"))
            elif res.status == "WARN":
                status_item = QTableWidgetItem("🟡 WARN")
                status_item.setForeground(QColor("#fbbf24"))
            else:
                status_item = QTableWidgetItem("🔴 FAIL")
                status_item.setForeground(QColor("#f87171"))
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            msg_item = QTableWidgetItem(res.message)

            self.results_table.setItem(row, 0, phase_item)
            self.results_table.setItem(row, 1, status_item)
            self.results_table.setItem(row, 2, msg_item)

        if results:
            self.results_table.selectRow(0)

        # Show summary alert
        if fail_count > 0:
            QMessageBox.warning(
                self, "Stability Audit: Action Required",
                f"Audit completed with {fail_count} failure(s) and {warn_count} warning(s).\nReview the highlighted items before launching the game to prevent crashes or input bleed."
            )
        else:
            QMessageBox.information(
                self, "Stability Audit: High Confidence",
                f"Audit completed! All critical checks passed ({pass_count} passed, {warn_count} warning(s)).\nThe handler is structurally stable and ready for split-screen play!"
            )

    def on_result_selected(self):
        selected_rows = self.results_table.selectionModel().selectedRows()
        if not selected_rows:
            self.details_browser.clear()
            return

        row = selected_rows[0].row()
        res = self.current_results[row]

        color = "#34d399" if res.status == "PASS" else ("#fbbf24" if res.status == "WARN" else "#f87171")
        html = f"""
        <h4 style="margin: 0; color: {color};">[{res.status}] {res.title}</h4>
        <p><b>Summary:</b> {res.message}</p>
        <p><b>Technical Trace & Details:</b><br>
        <code>{res.details.replace(chr(10), '<br>')}</code></p>
        """
        self.details_browser.setHtml(html)
