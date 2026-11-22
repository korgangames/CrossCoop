"""
Nucleus Co-op Section: Combines Hub Browser and Local Installed Handlers.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from crosscoop.ui.hub_tab import HubTab
from crosscoop.ui.nucleus_installed_tab import NucleusInstalledTab

class NucleusSection(QWidget):
    def __init__(self, hub_client, partydeck_mgr, nucleus_mgr, parent=None):
        super().__init__(parent)
        self.hub_client = hub_client
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
                color: #38bdf8;
                border-bottom: 2px solid #0284c7;
            }
        """)

        self.hub_tab = HubTab(self.hub_client, self.partydeck_mgr)
        self.installed_tab = NucleusInstalledTab(self.nucleus_mgr, self.partydeck_mgr)

        self.sub_tabs.addTab(self.hub_tab, "🌐 SplitScreen.Me Hub (895 Games)")
        self.sub_tabs.addTab(self.installed_tab, "💾 Local Installed Handlers")

        layout.addWidget(self.sub_tabs)
