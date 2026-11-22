"""
Entry point for CrossCoop application.
"""

import sys
import os

# Ensure package root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from crosscoop.ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("CrossCoop")
    app.setOrganizationName("SplitScreenCommunity")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
