import sys
from PySide6.QtWidgets import QApplication
from fb_hunter.ui.main_window import MainWindow
from fb_hunter.config import ensure_app_dirs

def main():
    ensure_app_dirs()
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
