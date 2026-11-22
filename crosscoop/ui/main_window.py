"""
Main Window for CrossCoop Application.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTabWidget, QPushButton, QStatusBar
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
        self.resize(1180, 760)
        self.setMinimumSize(980, 620)
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
        subtitle_lbl = QLabel("Double-Sided Conversion, Pre-Flight Stability Audit & Handler Browser")
        subtitle_lbl.setObjectName("subtitleLabel")
        title_box.addWidget(title_lbl)
        title_box.addWidget(subtitle_lbl)
        h_layout.addLayout(title_box)

        h_layout.addStretch()

        # Status pills & Quick launch
        db_count = len(self.hub_client.games)
        pill_db = QLabel(f"📦 Nucleus Hub: {db_count} Games")
        pill_db.setStyleSheet("background-color: #232533; border: 1px solid #33364a; border-radius: 6px; padding: 6px 12px; font-weight: 600; color: #a5b4fc;")
        h_layout.addWidget(pill_db)

        pd_exe = self.partydeck_mgr.find_partydeck_executable()
        pill_pd = QLabel("🐧 PartyDeck: Ready" if pd_exe else "⚠️ PartyDeck: Not Found")
        pill_pd.setStyleSheet("background-color: #064e3b; border: 1px solid #059669; border-radius: 6px; padding: 6px 12px; font-weight: 600; color: #34d399;" if pd_exe else "background-color: #450a0a; border: 1px solid #dc2626; border-radius: 6px; padding: 6px 12px; font-weight: 600; color: #f87171;")
        h_layout.addWidget(pill_pd)

        launch_btn = QPushButton("🚀 Run PartyDeck")
        launch_btn.setObjectName("primaryBtn")
        launch_btn.clicked.connect(self.partydeck_mgr.launch_partydeck)
        h_layout.addWidget(launch_btn)

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
        self.tabs.addTab(self.settings_tab, "⚙️ System & Settings")

        main_layout.addWidget(self.tabs, stretch=1)

        # Status Bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("background-color: #12131a; color: #9ca3af; border-top: 1px solid #232533;")
        self.status_bar.showMessage("Ready. Select any game to convert, audit pre-flight stability, or install.")
        self.setStatusBar(self.status_bar)
