"""
System Status, Settings, and Dual Program Bootable Customization Tab.
"""

import os
import shutil
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QGridLayout, QMessageBox, QTextBrowser, QLineEdit,
    QFileDialog, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal

from crosscoop.core.settings_manager import SettingsManager

class SettingsTab(QWidget):
    settings_updated_signal = pyqtSignal()

    def __init__(self, partydeck_mgr, parent=None):
        super().__init__(parent)
        self.partydeck_mgr = partydeck_mgr
        self.settings_mgr = SettingsManager()
        self.setup_ui()

    def setup_ui(self):
        # Outer scroll area so all options fit comfortably on any screen size
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # -------------------------------------------------------------
        # Section 1: Connect Custom Bootables / Executables
        # -------------------------------------------------------------
        bootable_group = QGroupBox("🎮 Connect Bootables & Executables (Dual Launcher Setup)")
        boot_layout = QVBoxLayout(bootable_group)
        boot_layout.setSpacing(12)

        desc_lbl = QLabel(
            "Customize the exact paths to your PartyDeck and Nucleus Co-op executables or runner scripts. "
            "CrossCoop can launch both programs directly with your custom settings."
        )
        desc_lbl.setStyleSheet("color: #9ca3af; font-size: 12px;")
        desc_lbl.setWordWrap(True)
        boot_layout.addWidget(desc_lbl)

        # 1. PartyDeck Bootable
        pd_box = QGroupBox("🐧 PartyDeck Bootable (Linux Native)")
        pd_box_layout = QVBoxLayout(pd_box)
        
        pd_row = QHBoxLayout()
        self.pd_path_edit = QLineEdit(self.settings_mgr.settings.get("partydeck_path", ""))
        self.pd_path_edit.setPlaceholderText("/path/to/partydeck.AppImage or binary")
        self.pd_path_edit.textChanged.connect(self.update_status_labels)
        pd_row.addWidget(self.pd_path_edit, stretch=3)

        pd_browse_btn = QPushButton("📂 Browse...")
        pd_browse_btn.clicked.connect(self.on_browse_partydeck)
        pd_row.addWidget(pd_browse_btn)

        self.pd_test_btn = QPushButton("🚀 Run PartyDeck")
        self.pd_test_btn.setObjectName("primaryBtn")
        self.pd_test_btn.clicked.connect(self.on_launch_partydeck)
        pd_row.addWidget(self.pd_test_btn)
        pd_box_layout.addLayout(pd_row)

        self.pd_status_lbl = QLabel("")
        self.pd_status_lbl.setStyleSheet("font-size: 11px;")
        pd_box_layout.addWidget(self.pd_status_lbl)
        boot_layout.addWidget(pd_box)

        # 2. Nucleus Co-op Bootable
        nc_box = QGroupBox("🪟 Nucleus Co-op Bootable (Windows / Wine)")
        nc_box_layout = QVBoxLayout(nc_box)

        nc_row = QHBoxLayout()
        self.nc_path_edit = QLineEdit(self.settings_mgr.settings.get("nucleus_path", ""))
        self.nc_path_edit.setPlaceholderText("/path/to/NucleusCoop.exe or run_nucleus.sh")
        self.nc_path_edit.textChanged.connect(self.update_status_labels)
        nc_row.addWidget(self.nc_path_edit, stretch=3)

        nc_browse_btn = QPushButton("📂 Browse...")
        nc_browse_btn.clicked.connect(self.on_browse_nucleus)
        nc_row.addWidget(nc_browse_btn)

        self.nc_test_btn = QPushButton("🪟 Run Nucleus Co-op")
        self.nc_test_btn.setStyleSheet("background-color: #2563eb; color: #ffffff;")
        self.nc_test_btn.clicked.connect(self.on_launch_nucleus)
        nc_row.addWidget(self.nc_test_btn)
        nc_box_layout.addLayout(nc_row)

        self.nc_status_lbl = QLabel("")
        self.nc_status_lbl.setStyleSheet("font-size: 11px;")
        nc_box_layout.addWidget(self.nc_status_lbl)
        boot_layout.addWidget(nc_box)

        # 3. Wine / Compatibility Runner for Nucleus
        wine_box = QGroupBox("🍷 Wine Runner & Prefix Configuration")
        wine_box_layout = QGridLayout(wine_box)

        wine_box_layout.addWidget(QLabel("Wine Binary:"), 0, 0)
        self.wine_path_edit = QLineEdit(self.settings_mgr.settings.get("wine_path", "/usr/bin/wine"))
        wine_box_layout.addWidget(self.wine_path_edit, 0, 1)
        wine_browse_btn = QPushButton("Browse...")
        wine_browse_btn.clicked.connect(self.on_browse_wine)
        wine_box_layout.addWidget(wine_browse_btn, 0, 2)

        wine_box_layout.addWidget(QLabel("WINEPREFIX:"), 1, 0)
        self.prefix_path_edit = QLineEdit(self.settings_mgr.settings.get("wine_prefix", str(Path.home() / ".wine")))
        wine_box_layout.addWidget(self.prefix_path_edit, 1, 1)
        prefix_browse_btn = QPushButton("Browse Folder...")
        prefix_browse_btn.clicked.connect(self.on_browse_prefix)
        wine_box_layout.addWidget(prefix_browse_btn, 1, 2)

        boot_layout.addWidget(wine_box)

        # Save & Reset Buttons
        action_row = QHBoxLayout()
        save_btn = QPushButton("💾 Save Bootable Settings")
        save_btn.setObjectName("successBtn")
        save_btn.setFixedHeight(36)
        save_btn.clicked.connect(self.on_save_settings)
        action_row.addWidget(save_btn, stretch=2)

        reset_btn = QPushButton("🔄 Reset to Defaults")
        reset_btn.setFixedHeight(36)
        reset_btn.clicked.connect(self.on_reset_defaults)
        action_row.addWidget(reset_btn, stretch=1)
        boot_layout.addLayout(action_row)

        main_layout.addWidget(bootable_group)

        # -------------------------------------------------------------
        # Section 2: Nobara System Runtime Environment Status
        # -------------------------------------------------------------
        sys_group = QGroupBox("Nobara Linux System Tools Status")
        grid = QGridLayout(sys_group)
        grid.setSpacing(10)

        tools = [
            ("Gamescope (Window Tiler & Compositor)", "gamescope", shutil.which("gamescope")),
            ("Bubblewrap (Input & Controller Sandbox)", "bwrap", shutil.which("bwrap")),
            ("UMU Launcher / Proton Runner", "umu-run", shutil.which("umu-run")),
            ("Wine (Windows Compatibility Layer)", "wine", shutil.which("wine")),
        ]

        for i, (name, cmd, path) in enumerate(tools):
            grid.addWidget(QLabel(f"<b>{name}:</b>"), i, 0)
            status_lbl = QLabel(f"✅ Found ({path})" if path else "⚠️ Not in PATH")
            status_lbl.setStyleSheet("color: #34d399;" if path else "color: #f87171;")
            grid.addWidget(status_lbl, i, 1)

        main_layout.addWidget(sys_group)

        # -------------------------------------------------------------
        # Section 3: Architecture Info Browser
        # -------------------------------------------------------------
        info_group = QGroupBox("How CrossCoop Bridges Both Programs")
        info_layout = QVBoxLayout(info_group)
        info_browser = QTextBrowser()
        info_browser.setStyleSheet("background-color: #12131a; border: 1px solid #232533; border-radius: 6px;")
        info_browser.setMaximumHeight(160)
        info_browser.setHtml("""
        <p><b>Unified Launch Architecture:</b></p>
        <ul>
          <li><b>PartyDeck Native Launch:</b> CrossCoop launches PartyDeck in an isolated session, applying Gamescope and Bubblewrap sandbox parameters.</li>
          <li><b>Nucleus Co-op Wine Launch:</b> CrossCoop can trigger your configured Wine runner to start Nucleus Co-op directly.</li>
          <li><b>Custom Bootables:</b> You can point PartyDeck to custom builds, development AppImages, or upstream wrappers without reinstalling.</li>
        </ul>
        """)
        info_layout.addWidget(info_browser)
        main_layout.addWidget(info_group)

        scroll.setWidget(container)
        outer_layout.addWidget(scroll)

        self.update_status_labels()

    def update_status_labels(self):
        # PartyDeck check
        pd_path = self.pd_path_edit.text().strip()
        if pd_path and Path(pd_path).exists():
            self.pd_status_lbl.setText(f"✅ Bootable verified: {pd_path}")
            self.pd_status_lbl.setStyleSheet("color: #34d399;")
            self.pd_test_btn.setEnabled(True)
        else:
            self.pd_status_lbl.setText("⚠️ File does not exist at this path.")
            self.pd_status_lbl.setStyleSheet("color: #f87171;")
            self.pd_test_btn.setEnabled(False)

        # Nucleus check
        nc_path = self.nc_path_edit.text().strip()
        if nc_path and Path(nc_path).exists():
            self.nc_status_lbl.setText(f"✅ Bootable verified: {nc_path}")
            self.nc_status_lbl.setStyleSheet("color: #34d399;")
            self.nc_test_btn.setEnabled(True)
        else:
            self.nc_status_lbl.setText("⚠️ File does not exist at this path.")
            self.nc_status_lbl.setStyleSheet("color: #f87171;")
            self.nc_test_btn.setEnabled(False)

    def on_browse_partydeck(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Select PartyDeck Bootable / AppImage",
            self.pd_path_edit.text() or str(Path.home()),
            "PartyDeck AppImage / Binary (*.AppImage partydeck*);;All Files (*)"
        )
        if f:
            self.pd_path_edit.setText(f)

    def on_browse_nucleus(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Select Nucleus Co-op Bootable / Script",
            self.nc_path_edit.text() or str(Path.home()),
            "Executable / Runner (*.exe *.sh);;All Files (*)"
        )
        if f:
            self.nc_path_edit.setText(f)

    def on_browse_wine(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Select Wine Binary",
            self.wine_path_edit.text() or "/usr/bin",
            "Wine Binary (wine*);;All Files (*)"
        )
        if f:
            self.wine_path_edit.setText(f)

    def on_browse_prefix(self):
        d = QFileDialog.getExistingDirectory(
            self, "Select WINEPREFIX Directory",
            self.prefix_path_edit.text() or str(Path.home())
        )
        if d:
            self.prefix_path_edit.setText(d)

    def on_save_settings(self):
        new_data = {
            "partydeck_path": self.pd_path_edit.text().strip(),
            "nucleus_path": self.nc_path_edit.text().strip(),
            "wine_path": self.wine_path_edit.text().strip(),
            "wine_prefix": self.prefix_path_edit.text().strip()
        }
        self.settings_mgr.save_settings(new_data)
        QMessageBox.information(self, "Settings Saved", "Custom bootable paths have been saved successfully!")
        self.settings_updated_signal.emit()

    def on_reset_defaults(self):
        defaults = self.settings_mgr.get_default_settings()
        self.pd_path_edit.setText(defaults.get("partydeck_path", ""))
        self.nc_path_edit.setText(defaults.get("nucleus_path", ""))
        self.wine_path_edit.setText(defaults.get("wine_path", "/usr/bin/wine"))
        self.prefix_path_edit.setText(defaults.get("wine_prefix", str(Path.home() / ".wine")))
        self.update_status_labels()

    def on_launch_partydeck(self):
        self.on_save_settings()
        success, msg = self.settings_mgr.launch_partydeck()
        if success:
            QMessageBox.information(self, "PartyDeck Launched", msg)
        else:
            QMessageBox.warning(self, "Launch Error", msg)

    def on_launch_nucleus(self):
        self.on_save_settings()
        success, msg = self.settings_mgr.launch_nucleus()
        if success:
            QMessageBox.information(self, "Nucleus Co-op Launched", msg)
        else:
            QMessageBox.warning(self, "Launch Error", msg)
