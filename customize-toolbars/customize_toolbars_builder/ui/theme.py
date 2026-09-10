"""Dark palette in the family of the LP markers / deformer tools."""

BUILDER_QSS = """
QWidget {
    background-color: #0b1326;
    color: #e6eeff;
    font-family: "Segoe UI", "Hanken Grotesk", sans-serif;
    font-size: 13px;
}
QMainWindow::separator { background: #1c2740; width: 3px; height: 3px; }
QLabel, QCheckBox { background: transparent; }
QLabel[role="hint"] { color: #8c98b8; font-size: 12px; }
QLabel[role="warn"] { color: #f6c667; }
QLabel[role="ok"]   { color: #6fd08c; }

QGroupBox {
    border: 1px solid #2b3550;
    border-radius: 8px;
    margin-top: 16px;
    padding: 8px 8px 4px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: #c2c6d6;
    font-family: "Consolas", monospace;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
}

QLineEdit, QPlainTextEdit, QComboBox, QSpinBox {
    background-color: #131d33;
    border: 1px solid #2b3550;
    border-radius: 6px;
    padding: 4px 6px;
    selection-background-color: #2f4d7a;
}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus { border-color: #3d63a8; }
QComboBox::drop-down { border: none; width: 18px; }

QListWidget, QTreeWidget {
    background-color: #0e1830;
    border: 1px solid #2b3550;
    border-radius: 6px;
    outline: 0;
}
QListWidget::item, QTreeWidget::item { padding: 4px 6px; border-radius: 4px; }
QListWidget::item:selected, QTreeWidget::item:selected { background-color: #2f4d7a; }
QListWidget::item:hover, QTreeWidget::item:hover { background-color: #1b2c4a; }

QPushButton, QToolButton {
    background-color: #1e2942;
    border: 1px solid #33406a;
    border-radius: 7px;
    padding: 6px 12px;
    font-weight: 600;
}
QPushButton:hover, QToolButton:hover { background-color: #273454; }
QPushButton:pressed, QToolButton:pressed { background-color: #182238; }
QPushButton:disabled, QToolButton:disabled { color: #5b678a; background-color: #141d31; border-color: #212c46; }
QPushButton[accent="true"], QToolButton[accent="true"] { background-color: #2f5bd0; border-color: #3f6ce0; color: #eef3ff; }
QPushButton[accent="true"]:hover, QToolButton[accent="true"]:hover { background-color: #366ae6; }
QToolButton::menu-button { border: none; width: 16px; border-top-right-radius: 7px; border-bottom-right-radius: 7px; }
QToolButton::menu-arrow { image: none; }

QMenuBar { background: #0b1326; }
QMenuBar::item:selected { background: #1e2942; }
QMenu { background: #131d33; border: 1px solid #2b3550; }
QMenu::item:selected { background: #2f4d7a; }

QStatusBar { background: #0e1830; color: #9fb0d6; }
QScrollBar:vertical { background: #0b1326; width: 12px; }
QScrollBar::handle:vertical { background: #2b3550; border-radius: 6px; min-height: 24px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
QSplitter::handle { background: #1c2740; }
"""
