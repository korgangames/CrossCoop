"""
System Status, Settings, and Launcher Tab.
"""

import os
import shutil
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QGridLayout, QMessageBox, QTextBrowser
)
from PyQt6.QtCore import Qt

class SettingsTab(QWidget):
    def __init__(self, partydeck_mgr, parent=None):
        super().__init__(parent)
        self.partydeck_mgr = partydeck_mgr
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # System Integration Status
        sys_group = QGroupBox("Nobara Linux System & Runtime Environment")
        grid = QGridLayout(sys_group)
        grid.setSpacing(10)

        # Check tools
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

        # PartyDeck Launcher & Folders
        pd_group = QGroupBox("PartyDeck Integration")
        pd_layout = QVBoxLayout(pd_group)

        pd_exe = self.partydeck_mgr.find_partydeck_executable()
        pd_status_lbl = QLabel(f"Executable: <code>{pd_exe}</code>" if pd_exe else "Executable: Not found")
        pd_layout.addWidget(pd_status_lbl)

        h_dir = str(self.partydeck_mgr.handlers_dir)
        h_dir_lbl = QLabel(f"Handlers Directory: <code>{h_dir}</code>")
        pd_layout.addWidget(h_dir_lbl)

        btn_row = QHBoxLayout()
        launch_pd_btn = QPushButton("🚀 Launch PartyDeck")
        launch_pd_btn.setObjectName("primaryBtn")
        launch_pd_btn.setFixedHeight(36)
        launch_pd_btn.clicked.connect(self.on_launch_partydeck)
        btn_row.addWidget(launch_pd_btn)

        open_hdir_btn = QPushButton("📁 Open Handlers Folder")
        open_hdir_btn.setFixedHeight(36)
        open_hdir_btn.clicked.connect(lambda: subprocess.Popen(["xdg-open", h_dir]))
        btn_row.addWidget(open_hdir_btn)

        pd_layout.addLayout(btn_row)
        main_layout.addWidget(pd_group)

        # Knowledge Base / Architectural Notes
        info_group = QGroupBox("How CrossCoop Works Under the Hood")
        info_layout = QVBoxLayout(info_group)
        info_browser = QTextBrowser()
        info_browser.setStyleSheet("background-color: #12131a; border: 1px solid #232533; border-radius: 6px;")
        info_browser.setHtml("""
        <p><b>Bridging the Gap:</b></p>
        <ul>
          <li><b>Nucleus Co-op (Windows):</b> Relies on <i>ProtoInput</i>, <i>EasyHook</i>, and <i>x360ce</i> DLL injections into Windows processes to capture raw input and fake window focus, alongside Win32 API window border tiling.</li>
          <li><b>PartyDeck (Linux):</b> Replaces all of those fragile Windows DLL hooks with native Linux kernel sandboxing:
            <ul>
              <li><b>Input Isolation:</b> Uses <code>bwrap</code> to mask <code>/dev/input/event*</code> nodes, so each game instance physically only sees its own controller.</li>
              <li><b>Window Placement:</b> Uses <code>gamescope</code> to render instances side-by-side without border bugs.</li>
              <li><b>Steam Emulation:</b> Uses the Goldberg emulator with UMU/Proton-GE for seamless LAN play.</li>
            </ul>
          </li>
          <li><b>CrossCoop Translation:</b> Takes the vast community knowledge from 895 Nucleus handlers (exact executables, App IDs, launch flags, Goldberg requirements) and translates them into clean, declarative manifests that PartyDeck executes natively on Nobara!</li>
        </ul>
        """)
        info_layout.addWidget(info_browser)
        main_layout.addWidget(info_group, stretch=1)

    def on_launch_partydeck(self):
        success, msg = self.partydeck_mgr.launch_partydeck()
        if success:
            QMessageBox.information(self, "PartyDeck Launched", f"Launched PartyDeck:\n{msg}")
        else:
            QMessageBox.warning(self, "Launch Error", msg)
