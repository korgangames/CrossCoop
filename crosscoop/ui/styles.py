"""
Modern dark styling for CrossCoop application.
"""

DARK_THEME_QSS = """
QMainWindow {
    background-color: #0f1015;
    color: #f3f4f6;
    font-family: 'Segoe UI', 'Ubuntu', 'Inter', -apple-system, sans-serif;
}

QWidget {
    color: #e5e7eb;
    font-size: 13px;
}

/* Header Banner */
#headerFrame {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a1b24, stop:1 #13141a);
    border-bottom: 1px solid #272838;
    padding: 12px;
}

#titleLabel {
    font-size: 20px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: 0.5px;
}

#subtitleLabel {
    font-size: 12px;
    color: #9ca3af;
}

/* Tabs */
QTabWidget::pane {
    border: none;
    background-color: #0f1015;
}

QTabBar::tab {
    background-color: #161720;
    color: #9ca3af;
    padding: 10px 20px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background-color: #232533;
    color: #818cf8;
    border-bottom: 2px solid #6366f1;
}

QTabBar::tab:hover:!selected {
    background-color: #1e1f2b;
    color: #d1d5db;
}

/* Cards & Panels */
QGroupBox, .cardPanel {
    background-color: #15161f;
    border: 1px solid #232533;
    border-radius: 10px;
    padding: 16px;
    margin-top: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #818cf8;
    font-weight: bold;
}

/* Inputs */
QLineEdit, QComboBox, QSpinBox, QPlainTextEdit {
    background-color: #1a1b26;
    border: 1px solid #2d3042;
    border-radius: 6px;
    padding: 8px 12px;
    color: #ffffff;
    selection-background-color: #4f46e5;
}

QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus {
    border: 1px solid #6366f1;
    background-color: #1e1f2e;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

/* Buttons */
QPushButton {
    background-color: #232533;
    border: 1px solid #33364a;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
    color: #e5e7eb;
}

QPushButton:hover {
    background-color: #2d3045;
    border-color: #4f46e5;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #1a1b26;
}

QPushButton:disabled {
    background-color: #161720;
    border-color: #20222e;
    color: #4b5563;
}

QPushButton#primaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #6366f1);
    color: #ffffff;
    border: none;
}

QPushButton#primaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338ca, stop:1 #4f46e5);
}

QPushButton#successBtn {
    background-color: #059669;
    color: #ffffff;
    border: none;
}

QPushButton#successBtn:hover {
    background-color: #047857;
}

QPushButton#dangerBtn {
    background-color: #dc2626;
    color: #ffffff;
    border: none;
}

QPushButton#dangerBtn:hover {
    background-color: #b91c1c;
}

/* Tables */
QTableWidget {
    background-color: #15161f;
    border: 1px solid #232533;
    border-radius: 8px;
    gridline-color: #1e202d;
    selection-background-color: #2d3045;
    selection-color: #ffffff;
}

QHeaderView::section {
    background-color: #1a1b26;
    color: #9ca3af;
    font-weight: 600;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #2e3144;
}

QTableWidget::item {
    padding: 6px 8px;
    border-bottom: 1px solid #1a1b24;
}

QTableWidget::item:selected {
    background-color: #2b2e42;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #101117;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #2b2d3d;
    min-height: 25px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #434760;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Status Badges */
.badge-installed {
    background-color: #064e3b;
    color: #34d399;
    border-radius: 4px;
    padding: 2px 6px;
    font-weight: 600;
}
"""
