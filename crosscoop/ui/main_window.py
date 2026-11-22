"""
Main Window for CrossCoop Application.
Features dual launching for both PartyDeck and Nucleus Co-op with customizable bootables.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTabWidget, QPushButton, QStatusBar, QMessageBox
)
from PyQt6.QtCore import Qt

from crosscoop.core.hub_client import HubClient
from crosscoop.core.partydeck_manager import PartyDeckManager
from crosscoop.ui.hub_tab import HubTab
from crosscoop.ui.partydeck_browser_tab import PartyDeckBrowserTab
from crosscoop.ui.audit_tab import AuditTab
from crosscoop.ui.installed_tab import InstalledTab
from crosscoop.ui.manual_convert_tab import ManualConvertTab
from crosscoop.ui.settings_tab import SettingsTab
from crosscoop.ui.styles import DARK_THEME_QSS

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CrossCoop — Universal Split-Screen Bridge (Nucleus Co-op ⟷ PartyDeck)")
        self.resize(1200, 780)
        self.setMinimumSize(1000, 640)
        self.setStyleSheet(DARK_THEME_QSS)

        # Core managers
        self.hub_client = HubClient()
        self.partydeck_mgr = PartyDeckManager()

        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header Frame
        header = QWidget()
        header.setObjectName("headerFrame")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(16, 12, 16, 12)

        # Title and Subtitle
        title_box = QVBoxLayout()
        title_lbl = QLabel("🎮 CrossCoop Universal Bridge")
        title_lbl.setObjectName("titleLabel")
        subtitle_lbl = QLabel("Double-Sided Conversion, Pre-Flight Stability Audit & Dual Launcher")
        subtitle_lbl.setObjectName("subtitleLabel")
        title_box.addWidget(title_lbl)
        title_box.addWidget(subtitle_lbl)
        h_layout.addLayout(title_box)

        h_layout.addStretch()

        # Database Count Pill
        db_count = len(self.hub_client.games)
        self.pill_db = QLabel(f"📦 Nucleus Hub: {db_count} Games")
        self.pill_db.setStyleSheet("background-color: #232533; border: 1px solid #33364a; border-radius: 6px; padding: 6px 12px; font-weight: 600; color: #a5b4fc;")
        h_layout.addWidget(self.pill_db)

        # Dual Launch Buttons in Header Bar
        launch_pd_btn = QPushButton("🚀 Run PartyDeck")
        launch_pd_btn.setObjectName("primaryBtn")
        launch_pd_btn.setToolTip("Launch your configured PartyDeck bootable directly")
        launch_pd_btn.clicked.connect(self.on_launch_partydeck)
        h_layout.addWidget(launch_pd_btn)

        launch_nc_btn = QPushButton("🪟 Run Nucleus Co-op")
        launch_nc_btn.setStyleSheet("background-color: #2563eb; color: #ffffff; font-weight: 600; border-radius: 6px; padding: 8px 16px;")
        launch_nc_btn.setToolTip("Launch your configured Nucleus Co-op executable or runner script")
        launch_nc_btn.clicked.connect(self.on_launch_nucleus)
        h_layout.addWidget(launch_nc_btn)

        main_layout.addWidget(header)

        # Tab Widget
        self.tabs = QTabWidget()
        
        self.hub_tab = HubTab(self.hub_client, self.partydeck_mgr)
        self.pd_browser_tab = PartyDeckBrowserTab(self.partydeck_mgr)
        self.audit_tab = AuditTab(self.partydeck_mgr, self.hub_client)
        self.installed_tab = InstalledTab(self.partydeck_mgr)
        self.manual_tab = ManualConvertTab(self.partydeck_mgr)
        self.settings_tab = SettingsTab(self.partydeck_mgr)

        # Wire up update signals across tabs
        self.hub_tab.handler_installed_signal.connect(self.installed_tab.refresh_list)
        self.hub_tab.handler_installed_signal.connect(self.audit_tab.populate_handler_selector)
        self.hub_tab.database_synced_signal.connect(lambda cnt: self.pill_db.setText(f"📦 Nucleus Hub: {cnt} Games"))
        self.pd_browser_tab.handler_installed_signal.connect(self.installed_tab.refresh_list)
        self.pd_browser_tab.handler_installed_signal.connect(self.audit_tab.populate_handler_selector)
        self.installed_tab.handler_changed_signal.connect(self.hub_tab.refresh_table)
        self.installed_tab.handler_changed_signal.connect(self.pd_browser_tab.refresh_table)
        self.installed_tab.handler_changed_signal.connect(self.audit_tab.populate_handler_selector)

        self.tabs.addTab(self.hub_tab, "🎮 Browse Nucleus Hub (895 Games)")
        self.tabs.addTab(self.pd_browser_tab, "🐧 Browse PartyDeck Handlers")
        self.tabs.addTab(self.audit_tab, "🛡️ Pre-Flight Stability Audit")
        self.tabs.addTab(self.installed_tab, "💾 Installed in PartyDeck")
        self.tabs.addTab(self.manual_tab, "🔄 Two-Way Converter")
        self.tabs.addTab(self.settings_tab, "⚙️ Bootables & Settings")

        main_layout.addWidget(self.tabs, stretch=1)

        # Status Bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("background-color: #12131a; color: #9ca3af; border-top: 1px solid #232533;")
        self.status_bar.showMessage("Ready. Launch either program or customize your bootables in Settings.")
        self.setStatusBar(self.status_bar)

    def on_launch_partydeck(self):
        success, msg = self.settings_tab.settings_mgr.launch_partydeck()
        if success:
            QMessageBox.information(self, "PartyDeck Launched", msg)
        else:
            QMessageBox.warning(self, "Launch Error", msg)

    def on_launch_nucleus(self):
        success, msg = self.settings_tab.settings_mgr.launch_nucleus()
        if success:
            QMessageBox.information(self, "Nucleus Co-op Launched", msg)
        else:
            QMessageBox.warning(self, "Launch Error", msg)
