"""
Main Window for CrossCoop Application.
Features brand-grouped tabs (Nucleus Co-op and PartyDeck), dual launching,
full two-way cross-download and conversion, pre-flight stability audit, and customizable bootables.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTabWidget, QPushButton, QStatusBar, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from pathlib import Path

from crosscoop.core.hub_client import HubClient
from crosscoop.core.partydeck_manager import PartyDeckManager
from crosscoop.core.nucleus_manager import NucleusManager
from crosscoop.ui.nucleus_section import NucleusSection
from crosscoop.ui.partydeck_section import PartyDeckSection
from crosscoop.ui.audit_tab import AuditTab
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

        icon_path = Path(__file__).resolve().parent.parent / "assets" / "icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # Core managers
        self.hub_client = HubClient()
        self.partydeck_mgr = PartyDeckManager()
        self.nucleus_mgr = NucleusManager()

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
        subtitle_lbl = QLabel("True Two-Way Downloading, Cross-Conversion & Pre-Flight Stability Audit")
        subtitle_lbl.setObjectName("subtitleLabel")
        title_box.addWidget(title_lbl)
        title_box.addWidget(subtitle_lbl)
        h_layout.addLayout(title_box)

        h_layout.addStretch()

        # Database Count Pill
        db_count = len(self.hub_client.games)
        self.pill_db = QLabel(f"📦 Hub Library: {db_count} Games")
        self.pill_db.setStyleSheet("background-color: #232533; border: 1px solid #33364a; border-radius: 6px; padding: 6px 12px; font-weight: 600; color: #a5b4fc;")
        h_layout.addWidget(self.pill_db)

        # Dual Launch Buttons in Header Bar
        launch_pd_btn = QPushButton("🚀 Run PartyDeck")
        launch_pd_btn.setObjectName("primaryBtn")
        launch_pd_btn.setStyleSheet("background-color: #9333ea; color: #ffffff; font-weight: 600; padding: 8px 16px; border-radius: 6px;")
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
        
        # Primary Brand Sections
        self.nucleus_section = NucleusSection(self.hub_client, self.partydeck_mgr, self.nucleus_mgr)
        self.partydeck_section = PartyDeckSection(self.partydeck_mgr, self.nucleus_mgr)
        
        # Shared Tools & Settings
        self.audit_tab = AuditTab(self.partydeck_mgr, self.hub_client)
        self.manual_tab = ManualConvertTab(self.partydeck_mgr, self.nucleus_mgr)
        self.settings_tab = SettingsTab(self.partydeck_mgr)

        # ---------------------------------------------------------------------
        # Full Two-Way Update Signals Wiring
        # ---------------------------------------------------------------------

        # 1. From Nucleus Hub (SplitScreen.Me)
        # -> Install to PartyDeck:
        self.nucleus_section.hub_tab.handler_installed_signal.connect(
            self.partydeck_section.installed_tab.refresh_list
        )
        self.nucleus_section.hub_tab.handler_installed_signal.connect(
            self.audit_tab.populate_handler_selector
        )
        self.nucleus_section.hub_tab.handler_installed_signal.connect(
            self.partydeck_section.pd_browser_tab.refresh_table
        )
        # -> Download to Nucleus Co-op:
        self.nucleus_section.hub_tab.nucleus_handler_installed_signal.connect(
            self.nucleus_section.installed_tab.refresh_list
        )
        self.nucleus_section.hub_tab.nucleus_handler_installed_signal.connect(
            self.partydeck_section.pd_browser_tab.refresh_table
        )
        # -> Database Sync count:
        self.nucleus_section.hub_tab.database_synced_signal.connect(
            lambda cnt: self.pill_db.setText(f"📦 Hub Library: {cnt} Games")
        )

        # 2. From Nucleus Local Handlers Tab
        self.nucleus_section.installed_tab.handler_converted_signal.connect(
            self.partydeck_section.installed_tab.refresh_list
        )
        self.nucleus_section.installed_tab.handler_converted_signal.connect(
            self.audit_tab.populate_handler_selector
        )
        self.nucleus_section.installed_tab.handler_converted_signal.connect(
            self.nucleus_section.hub_tab.refresh_table
        )
        self.nucleus_section.installed_tab.handler_converted_signal.connect(
            self.partydeck_section.pd_browser_tab.refresh_table
        )

        # 3. From PartyDeck Community Browser
        # -> Install to PartyDeck:
        self.partydeck_section.pd_browser_tab.handler_installed_signal.connect(
            self.partydeck_section.installed_tab.refresh_list
        )
        self.partydeck_section.pd_browser_tab.handler_installed_signal.connect(
            self.audit_tab.populate_handler_selector
        )
        self.partydeck_section.pd_browser_tab.handler_installed_signal.connect(
            self.nucleus_section.hub_tab.refresh_table
        )
        # -> Install to Nucleus Co-op:
        self.partydeck_section.pd_browser_tab.nucleus_handler_installed_signal.connect(
            self.nucleus_section.installed_tab.refresh_list
        )
        self.partydeck_section.pd_browser_tab.nucleus_handler_installed_signal.connect(
            self.nucleus_section.hub_tab.refresh_table
        )

        # 4. From PartyDeck Local Installed Tab
        # -> Edits / Deletions:
        self.partydeck_section.installed_tab.handler_changed_signal.connect(
            self.nucleus_section.hub_tab.refresh_table
        )
        self.partydeck_section.installed_tab.handler_changed_signal.connect(
            self.partydeck_section.pd_browser_tab.refresh_table
        )
        self.partydeck_section.installed_tab.handler_changed_signal.connect(
            self.audit_tab.populate_handler_selector
        )
        # -> Install direct to Nucleus:
        self.partydeck_section.installed_tab.handler_converted_to_nucleus_signal.connect(
            self.nucleus_section.installed_tab.refresh_list
        )
        self.partydeck_section.installed_tab.handler_converted_to_nucleus_signal.connect(
            self.nucleus_section.hub_tab.refresh_table
        )

        # 5. From Manual Two-Way Converter Tab
        self.manual_tab.nucleus_installed_signal.connect(
            self.nucleus_section.installed_tab.refresh_list
        )
        self.manual_tab.nucleus_installed_signal.connect(
            self.nucleus_section.hub_tab.refresh_table
        )
        self.manual_tab.partydeck_installed_signal.connect(
            self.partydeck_section.installed_tab.refresh_list
        )
        self.manual_tab.partydeck_installed_signal.connect(
            self.audit_tab.populate_handler_selector
        )

        # Add top-level tabs
        self.tabs.addTab(self.nucleus_section, "🪟 Nucleus Co-op")
        self.tabs.addTab(self.partydeck_section, "🐧 PartyDeck")
        self.tabs.addTab(self.audit_tab, "🛡️ Pre-Flight Stability Audit")
        self.tabs.addTab(self.manual_tab, "🔄 Two-Way Converter")
        self.tabs.addTab(self.settings_tab, "⚙️ Bootables & Settings")

        main_layout.addWidget(self.tabs, stretch=1)

        # Status Bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("background-color: #12131a; color: #9ca3af; border-top: 1px solid #232533;")
        self.status_bar.showMessage("Ready. Download and convert handlers in both directions for Nucleus Co-op and PartyDeck.")
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
