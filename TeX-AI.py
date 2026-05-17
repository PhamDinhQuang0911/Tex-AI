#!/usr/bin/env python3
import sys
import os

# Thêm src vào path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.main_window import LatexEditor
from PyQt6.QtWidgets import QApplication


def main():
    os.environ["QT_MAC_WANTS_LAYER"] = "1"
    app = QApplication(sys.argv)
    window = LatexEditor()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
