import sys
from PySide6.QtWidgets import QApplication
from src.main_window import UniversifyPlayer


def main():
    app = QApplication(sys.argv)
    window = UniversifyPlayer()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
