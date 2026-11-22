"""
PartyDeck Section: Combines Community Browser and Local Installed Handlers.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from crosscoop.ui.partydeck_browser_tab import PartyDeckBrowserTab
from crosscoop.ui.installed_tab import InstalledTab

class PartyDeckSection(QWidget):
    def __init__(self, partydeck_mgr, nucleus_mgr=None, parent=None):
        super().__init__(parent)
        self.partydeck_mgr = partydeck_mgr
        self.nucleus_mgr = nucleus_mgr

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.sub_tabs = QTabWidget()
        self.sub_tabs.setStyleSheet("""
            QTabBar::tab {
                background-color: #12131c;
                color: #94a3b8;
                padding: 7px 16px;
                font-size: 12px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background-color: #1f2233;
                color: #a855f7;
                border-bottom: 2px solid #9333ea;
            }
        """)

        self.pd_browser_tab = PartyDeckBrowserTab(self.partydeck_mgr, self.nucleus_mgr)
        self.installed_tab = InstalledTab(self.partydeck_mgr, self.nucleus_mgr)

        self.sub_tabs.addTab(self.pd_browser_tab, "🌐 PartyDeck Community Browser")
        self.sub_tabs.addTab(self.installed_tab, "💾 Local Installed in PartyDeck")

        layout.addWidget(self.sub_tabs)
